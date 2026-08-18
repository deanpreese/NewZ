"""The folded substrate clause (S2 §6.1) — how the being is running, today.

> Substrate self-state folds into a compact clause the being can actually see
> (v1 quarantined the raw percepts correctly and then never surfaced the
> fold; S2 routes the folded state into ambient context and high-salience
> substrate events into affect — the available source of honest negative
> affect).

Found missing by the coverage audit of 2026-08-13. PLAN.md cites §6.1 once,
in Phase 1.5, and only to justify *cleaning up* v1's 1,041 raw telemetry
rows; the producer was scheduled in no phase, 0 through 7. The newest
substrate episode of any kind was dated 2026-06-13, nine weeks stale, which
is why the being answered "how are you" out of v1's cache-miss history: that
was the most recent information it had about itself.

**One episode a day, never raw percepts.** v1 stored 1,041 separate rows;
they became 39.6% of the corpus and produced a self-description made of
instrumentation. The fold is the correction, and the daily cap is the part
that keeps it a correction — S2 §6.1's own word is *compact*.

It is written as something readable rather than a metrics dump, because the
being reads it as its own state and "prefix_cache_miss_rate_high: 1.00" is
exactly how v1's self-model went wrong.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from newz.store.episodes import write_episode

logger = logging.getLogger(__name__)

# Anything at or above this is not part of the daily fold — it is its own
# event, because a day summarised as "normal" that contained an outage is a
# lie of composition.
SALIENT_ERROR_RATE = 0.05


@dataclass
class SubstrateState:
    calls_24h: int = 0
    errors_24h: int = 0
    slowest_s: float = 0.0
    median_s: float = 0.0
    uptime_s: float | None = None
    episodes: int = 0
    embedded: int = 0
    backup_age_s: float | None = None
    unreachable: list[str] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        return self.errors_24h / self.calls_24h if self.calls_24h else 0.0

    @property
    def salient(self) -> bool:
        """Worth its own episode rather than the daily fold."""
        return bool(self.unreachable) or self.error_rate >= SALIENT_ERROR_RATE

    def fold(self) -> str:
        """The compact clause. First person, plain, no metric names."""
        if not self.calls_24h:
            return ("Today I did almost nothing — no model calls at all "
                    "reached my record, which usually means I was not running.")

        parts = []
        if self.errors_24h == 0:
            parts.append(f"Today I ran cleanly: {self.calls_24h} calls, "
                         f"nothing failed")
        else:
            parts.append(f"Today {self.errors_24h} of my {self.calls_24h} "
                         f"calls failed ({self.error_rate:.0%})")
        if self.slowest_s:
            parts.append(f"my slowest thought took {self.slowest_s:.1f}s "
                         f"and the usual one {self.median_s:.1f}s")
        if self.uptime_s:
            parts.append(f"I have been up {self.uptime_s / 3600:.0f}h without "
                         f"restarting")
        if self.episodes:
            # Measured 2026-08-14, and the reason this reads as it does: the
            # first wording was "I am carrying 2741 episodes, 1596 of them
            # reachable by memory", which foregrounds the 1,145 that are NOT.
            # Sleep digested that as a memory deficit and used it to REINFORCE
            # the imported claim this whole instrument exists to contradict —
            # "forcing me to rely on immediate retrieval rather than
            # accumulated context" gained confidence on the strength of it.
            #
            # State the capability, not the shortfall. The uncovered remainder
            # is mostly v1 substrate telemetry that was never worth embedding,
            # so the ratio was never the deficit it read as.
            if self.embedded:
                parts.append(f"I can search {self.embedded} of my episodes "
                             f"directly, out of {self.episodes} I hold")
            else:
                parts.append(f"I am carrying {self.episodes} episodes, none of "
                             f"them searchable yet")
        if self.backup_age_s is not None and self.backup_age_s > 36 * 3600:
            parts.append(f"my last verified backup is "
                         f"{self.backup_age_s / 3600:.0f}h old")
        if self.unreachable:
            parts.append("I could not reach " + ", ".join(self.unreachable))
        # One sentence, semicolon-joined: ". ".join left every clause after
        # the first starting lowercase, and this is read as the being's own
        # account of itself rather than as a log line.
        return "; ".join(parts) + "."


def sample(conn: sqlite3.Connection, log_path: Path | None = None, *,
           started_at: float | None = None,
           backups_dir: Path | None = None) -> SubstrateState:
    """Read the substrate's own state. Reads only; never a model call."""
    st = SubstrateState()
    st.uptime_s = time.time() - started_at if started_at else None

    if log_path and Path(log_path).exists():
        cut, durs = time.time() - 86400, []
        for raw in Path(log_path).read_text().splitlines():
            try:
                r = json.loads(raw)
            except ValueError:
                continue
            if r.get("ts", 0) < cut:
                continue
            st.calls_24h += 1
            if r.get("error"):
                st.errors_24h += 1
            if r.get("duration_s"):
                durs.append(r["duration_s"])
        if durs:
            durs.sort()
            st.slowest_s = durs[-1]
            st.median_s = durs[len(durs) // 2]

    try:
        st.episodes = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        st.embedded = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE embedding IS NOT NULL").fetchone()[0]
    except sqlite3.Error:
        pass

    if backups_dir and Path(backups_dir).is_dir():
        newest = max((p.stat().st_mtime for p in Path(backups_dir).glob("main-*.db")),
                     default=None)
        if newest:
            st.backup_age_s = time.time() - newest
    return st


def already_folded_today(conn: sqlite3.Connection, now: float | None = None) -> bool:
    day = _dt.date.fromtimestamp(now or time.time()).isoformat()
    row = conn.execute(
        "SELECT ts FROM episodes WHERE kind='substrate' ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    return bool(row and _dt.date.fromtimestamp(row["ts"]).isoformat() == day)


def write_fold(conn: sqlite3.Connection, state: SubstrateState) -> int | None:
    """One episode. Returns its id, or None if today's is already written."""
    if already_folded_today(conn):
        return None
    text = state.fold()
    ep = write_episode(
        conn, kind="substrate", provenance="world:substrate",
        summary=text,
        content={"calls_24h": state.calls_24h, "errors_24h": state.errors_24h,
                 "slowest_s": state.slowest_s, "median_s": state.median_s,
                 "uptime_s": state.uptime_s, "episodes": state.episodes,
                 "embedded": state.embedded, "unreachable": state.unreachable},
    )
    logger.info("substrate fold: %s", text)

    # S2 §6.1: substrate self-state is "the available source of honest
    # negative affect". A fixed, code-owned delta — no model call decides
    # how the being feels about its own day.
    try:
        from newz.affect.store import SUBSTRATE_DISTRESS, SUBSTRATE_WELL, record

        record(conn, SUBSTRATE_DISTRESS if state.salient else SUBSTRATE_WELL,
               source="substrate", note=text[:200])
    except Exception:  # noqa: BLE001
        logger.warning("affect not updated from the fold", exc_info=True)

    if state.salient:
        # The event is kept distinct from the fold as well as from the
        # affect delta above: a day summarised as "normal" that contained an
        # outage is a lie of composition, and sleep should be able to digest
        # the outage as its own thing.
        write_episode(
            conn, kind="substrate_event", provenance="world:substrate",
            summary=("Something was wrong with me today: "
                     + (", ".join(state.unreachable) + " unreachable. "
                        if state.unreachable else "")
                     + (f"{state.error_rate:.0%} of my calls failed."
                        if state.error_rate else "")).strip(),
            content={"error_rate": state.error_rate,
                     "unreachable": state.unreachable},
        )
    return ep


class SubstrateScheduler:
    """Folds once a day, before sleep's window so the night can digest it.

    Its own connection, and a failure costs the fold and nothing else — the
    being knowing how it ran is worth having, not worth the loop for.
    """

    def __init__(self, db_path, *, log_path=None, backups_dir=None,
                 started_at: float | None = None, interval_s: float = 3600):
        self._db_path = db_path
        self._log_path = log_path
        self._backups_dir = backups_dir
        self._started_at = started_at or time.time()
        self._interval = interval_s

    def run_once(self) -> int | None:
        from newz.store.db import open_db

        conn = open_db(self._db_path, busy_timeout_ms=30_000)
        try:
            if already_folded_today(conn):
                return None
            state = sample(conn, self._log_path, started_at=self._started_at,
                           backups_dir=self._backups_dir)
            return write_fold(conn, state)
        finally:
            conn.close()

    async def run(self) -> None:
        import asyncio

        logger.info("substrate fold: checking hourly, writing once a day")
        while True:
            try:
                await asyncio.to_thread(self.run_once)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("substrate fold failed — retrying next hour")
            await asyncio.sleep(self._interval)


def latest_fold(conn: sqlite3.Connection, max_age_s: float = 36 * 3600) -> str:
    """The clause for conversation context (S2 §6.1's 'ambient context').

    Stale folds are not returned: telling the being how it was three days ago
    is the failure this module exists to end, not a smaller version of it.
    """
    row = conn.execute(
        "SELECT ts, summary FROM episodes WHERE kind='substrate'"
        " ORDER BY ts DESC LIMIT 1").fetchone()
    if not row or time.time() - row["ts"] > max_age_s:
        return ""
    return row["summary"]
