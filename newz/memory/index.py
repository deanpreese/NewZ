"""Keeping the retrieval index current (S2 §4.3).

**The index was never maintained.** `write_episode` does not embed, and
`tools/embed_episodes.py` is an operator tool that was run once. Measured
2026-08-20: 2,066 of 3,662 episodes carried no vector, including **0 of 653
`reading` episodes** and 100 of 141 conversations. `Retriever.search` requires
`embedding IS NOT NULL`, so under `Scope.EVIDENCE` the entire retrievable
corpus was 265 v1 conversations, 41 current ones, and a single substrate fold.
Nothing the being had ever read was recallable — not in concern work, and not
when talking to the operator either.

**This is a repair with a live consumer.** `conversation/composer.py` queries
retrieval today, which is what makes this Rule 2 clean rather than speculative:
the reader exists and has been reading an index that was two-thirds empty.
Whether concern work also learns to query it is a separate decision and is not
made here.

**Not in the write path, deliberately.** `write_episode` is called inside
transactions with `commit=False` and on hot paths; an embedder call there means
a model failure can cost an episode, and the episode is worth more than its
index. So this is a rhythm that runs beside the being and can fail without
taking anything with it.

**Newest first, bounded per turn.** Two reasons. Recent material is what
conversation reaches for, so currency matters more than completeness. And a
single 2,000-episode blast would land the whole behaviour change at once — the
being would go from recalling nothing it read to recalling everything, between
one message and the next. Draining slowly makes that arrival gradual. The
operator tool remains for anyone who wants it done in one act.

**Embeddings do not touch the ingest budget.** `Embedder` posts directly to the
EMBED endpoint rather than through `LLMClient`, so nothing here is recorded to
`llm_calls.jsonl` and S2 §9.1's reading budget is unaffected. Checked rather
than assumed — a rhythm that quietly paused the being's reading would be a poor
way to repair its memory.
"""

from __future__ import annotations

import logging
import sqlite3
import time

logger = logging.getLogger(__name__)

# One turn's work. Two Embedder batches (BATCH=32), so a turn is a couple of
# posts to a local endpoint rather than a sustained load beside the being.
PER_TURN = 64
CHECK_INTERVAL_S = 300.0

_PENDING = (
    "FROM episodes WHERE digest_eligible=1 AND LENGTH(summary) > 0"
    " AND (embedding IS NULL OR embedding_model IS NOT ?)"
)


def coverage(conn: sqlite3.Connection, model: str) -> tuple[int, int]:
    """(embedded, eligible) for the current model.

    Logged on every turn rather than only when work happens: a rhythm that
    reports "0 embedded" because the endpoint is down looks exactly like one
    reporting "0 embedded" because there is nothing to do, and the difference
    is the whole health of the being's memory.
    """
    eligible = conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE digest_eligible=1"
        " AND LENGTH(summary) > 0").fetchone()[0]
    done = conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE digest_eligible=1"
        " AND LENGTH(summary) > 0 AND embedding IS NOT NULL"
        " AND embedding_model = ?", (model,)).fetchone()[0]
    return done, eligible


def embed_pending(conn: sqlite3.Connection, embedder, *,
                  limit: int = PER_TURN) -> int:
    """Embed up to `limit` episodes, newest first. Returns how many.

    Idempotent and safe to run beside the operator tool: the filter excludes
    anything already carrying a vector from this model, so the two can overlap
    without doing each other's work twice.
    """
    from newz.memory.embeddings import pack

    rows = conn.execute(
        f"SELECT id, summary {_PENDING} ORDER BY ts DESC LIMIT ?",
        (embedder.model, limit)).fetchall()
    if not rows:
        return 0
    vectors = embedder.embed([r["summary"] for r in rows])
    conn.executemany(
        "UPDATE episodes SET embedding=?, embedding_model=? WHERE id=?",
        [(pack(v), embedder.model, r["id"]) for r, v in zip(rows, vectors)])
    conn.commit()
    return len(rows)


class EmbeddingScheduler:
    """Keeps the retrieval index current, beside the being rather than in it."""

    def __init__(self, db_path, config, *, limit: int = PER_TURN,
                 check_interval_s: float = CHECK_INTERVAL_S):
        self._db_path = db_path
        self._config = config
        self._limit = limit
        self._interval = check_interval_s
        self._embedder = None
        self._disabled = ""

    def _get_embedder(self):
        if self._embedder is None:
            from newz.memory.embeddings import Embedder

            self._embedder = Embedder(self._config)
        return self._embedder

    def _turn(self) -> None:
        from newz.store.db import open_db

        conn = open_db(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            embedder = self._get_embedder()
            done = embed_pending(conn, embedder, limit=self._limit)
            have, eligible = coverage(conn, embedder.model)
            logger.info("retrieval index: +%d this turn, %d/%d episodes "
                        "embedded (%.0f%%)", done, have, eligible,
                        100.0 * have / max(eligible, 1))
        finally:
            conn.close()

    async def run(self) -> None:
        import asyncio

        from newz.crash import log_crash

        try:
            self._get_embedder()
        except Exception as e:  # noqa: BLE001
            # No EMBED role is a configuration state, not a crash. Say so once
            # and stop, rather than restarting a rhythm that cannot work.
            logger.warning("retrieval index rhythm off: %s", e)
            return

        logger.info("retrieval index: up to %d episodes every %.0fs",
                    self._limit, self._interval)
        while True:
            try:
                await asyncio.to_thread(self._turn)
            except asyncio.CancelledError:
                raise
            except Exception:
                log_crash(self._db_path.parent.parent, "retrieval index")
                logger.exception("embedding turn failed — retrying next check")
            await asyncio.sleep(self._interval)
