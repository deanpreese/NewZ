"""Noticing and the surface scheduler (S2 §6.1) — the being can start.

> Contributors notice; a surface scheduler with wake windows, maturity, and
> rate gates decides what gets raised to the being or to a human — v1's
> noticer/scheduler split and its 3-a.m. lesson, kept.

Found missing by the coverage audit of 2026-08-13, and it was the largest of
the six gaps. `newz/ambient/loop.py` drained an inbound queue and replied; it
had no noticer and no scheduler, so the being could not raise anything,
ever, unprompted. All 78 of its conversation episodes existed because the
operator typed first.

**Policy ported, architecture not.** v1's contributors are a percept-fired
`tick() -> list[Percept]`, and P2 Phase 3.1 requires v2 to have no
percept-fired tick to refactor away. What crossed is the gate policy and the
numbers behind it, which were paid for in production:

- **wake window 07:00–23:00 local** — the 3-a.m. lesson;
- **maturity 10 min** — a noticing is carried before it is raised, so a
  passing flicker is not a message;
- **surface gap 4h** — bounds the operator-visible rate to ~3–4 across a
  16h waking day;
- **operator cooldown 10 min** — do not interrupt a live conversation;
- **decay 24h** — v1's queue grew to 31 pending, oldest ~9 days, before this
  existed. A noticing carried through a full wake cycle is not stale
  information, it is *the wrong moment*; raising it then surfaces a moment
  that has passed.

Nothing here composes text. The scheduler decides *whether* and *what
about*; the composer says it, through the same VOICE path and the same
outbound gate as every reply. An unprompted message is not a privileged
message.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time

logger = logging.getLogger(__name__)

WAKE_START_HOUR = 7
WAKE_END_HOUR = 23
MATURITY_S = 10 * 60
SURFACE_GAP_S = 4 * 3600
OPERATOR_COOLDOWN_S = 10 * 60
DECAY_AFTER_S = 24 * 3600
CANDIDATE_POOL = 50

# What is worth possibly raising, and how much. Episode kinds the being
# already writes — noticing does not need its own perception, it needs
# judgment about what its existing life contains. Scores are the being's
# own priorities made explicit rather than a model's guess at significance.
NOTICEABLE: dict[str, float] = {
    "concern_closed": 0.9,     # it finished something
    "substrate_event": 0.8,    # something is wrong with it
    "advance": 0.5,            # it worked something out
    "concern_opened": 0.4,     # it has a new question
    "setback": 0.3,            # it is stuck
}


def notice(conn: sqlite3.Connection, *, since_s: float = 6 * 3600) -> int:
    """Turn recent life into candidates. Returns how many were added.

    Idempotent by episode: the unique index means a second pass over the
    same window adds nothing, so this can run as often as it likes.
    """
    added = 0
    kinds = ",".join("?" * len(NOTICEABLE))
    rows = conn.execute(
        f"SELECT id, kind, summary FROM episodes WHERE kind IN ({kinds})"
        " AND ts > ? ORDER BY ts DESC LIMIT ?",
        (*NOTICEABLE, time.time() - since_s, CANDIDATE_POOL),
    ).fetchall()
    for r in rows:
        try:
            conn.execute(
                "INSERT INTO noticings (ts, kind, episode_id, text, score)"
                " VALUES (?,?,?,?,?)",
                (time.time(), r["kind"], r["id"], r["summary"],
                 NOTICEABLE[r["kind"]]))
            added += 1
        except sqlite3.IntegrityError:
            pass          # already noticed; the index is the dedup
    if added:
        conn.commit()
        logger.info("noticing: %d new candidate(s)", added)
    return added


def decay_stale(conn: sqlite3.Connection) -> int:
    """A noticing carried through a full wake cycle is the wrong moment."""
    cur = conn.execute(
        "UPDATE noticings SET status='decayed' WHERE status='pending'"
        " AND ts < ?", (time.time() - DECAY_AFTER_S,))
    if cur.rowcount:
        conn.commit()
        logger.info("noticing: %d stale candidate(s) let go", cur.rowcount)
    return cur.rowcount


def in_wake_window(now: float | None = None) -> bool:
    hour = time.localtime(now or time.time()).tm_hour
    if WAKE_START_HOUR <= WAKE_END_HOUR:
        return WAKE_START_HOUR <= hour < WAKE_END_HOUR
    return hour >= WAKE_START_HOUR or hour < WAKE_END_HOUR


def blocked_reason(conn: sqlite3.Connection, person_id: str,
                   now: float | None = None) -> str | None:
    """Why the being may not raise something right now, or None.

    Named rather than boolean so the gates are legible in the log and in
    tools/health.py — a silent scheduler is indistinguishable from a broken
    one, which is how v1's queue reached nine days deep unnoticed.
    """
    now = now or time.time()
    if not in_wake_window(now):
        return "outside the wake window"

    last_out = conn.execute(
        "SELECT MAX(surfaced_at) FROM noticings WHERE status='surfaced'"
    ).fetchone()[0]
    if last_out and now - last_out < SURFACE_GAP_S:
        return f"last raised {(now - last_out) / 3600:.1f}h ago"

    last_msg = conn.execute(
        "SELECT MAX(ts) FROM messages WHERE person_id=?", (person_id,)
    ).fetchone()[0]
    if last_msg and now - last_msg < OPERATOR_COOLDOWN_S:
        return "we are mid-conversation"
    return None


def next_candidate(conn: sqlite3.Connection,
                   now: float | None = None) -> sqlite3.Row | None:
    """The highest-scoring mature pending noticing."""
    now = now or time.time()
    return conn.execute(
        "SELECT * FROM noticings WHERE status='pending' AND ts <= ?"
        " ORDER BY score DESC, ts ASC LIMIT 1", (now - MATURITY_S,)
    ).fetchone()


def mark_surfaced(conn: sqlite3.Connection, noticing_id: int,
                  message_id: int | None) -> None:
    conn.execute(
        "UPDATE noticings SET status='surfaced', surfaced_at=?, message_id=?"
        " WHERE id=?", (time.time(), message_id, noticing_id))
    conn.commit()


def pending_summary(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) n FROM noticings GROUP BY status").fetchall()
    return {r["status"]: r["n"] for r in rows}


# The instruction the composer is given when the being speaks first. It is
# deliberately not "write a message about X" — the being decides whether X
# is worth their attention, and declining is a real outcome.
OPENING_TASK = """\
Nobody has asked you anything. You noticed this, and you may raise it with
{person} — or decide it is not worth their attention, which is usually true.

What you noticed:
{noticed}

If it is worth saying: say it as you would to someone you know, briefly,
without preamble about the fact that you are reaching out. One thought, not
a report.

If it is not worth saying, reply with exactly: NOTHING

Your message (or NOTHING):"""


class SurfaceScheduler:
    """Decides whether the being says something nobody asked for.

    Runs on its own connection alongside the loop. Every gate is checked
    before any model call, so a scheduler that is not allowed to speak costs
    nothing; and every send goes through the ordinary outbound gate, because
    an unprompted message is not a privileged one.
    """

    def __init__(self, db_path, client, channel, person_id: str, *,
                 gate_factory=None, interval_s: float = 300.0,
                 enabled: bool = True):
        self._db_path = db_path
        self._client = client
        self._channel = channel
        self._person = person_id
        self._gate_factory = gate_factory
        self._interval = interval_s
        # Off is a supported state, not a bug: the operator may want the
        # being reactive-only, and that must not require deleting code.
        self._enabled = enabled

    def _compose(self, conn, noticed: str) -> str:
        """Ask the being whether this is worth raising, and how."""
        from newz.conversation.composer import _system_prompt

        system = _system_prompt(conn, self._person)
        user = OPENING_TASK.format(person=self._person, noticed=noticed)
        result = self._client.complete(
            "VOICE", system, user, max_tokens=600, temperature=0.7,
            function="conversation")
        return result.text.strip()

    async def run_once(self) -> str | None:
        """Returns what was said, or None. Never raises past the caller."""
        import asyncio

        from newz.conversation.composer import record_message
        from newz.store.db import open_db

        if not self._enabled:
            return None

        conn = open_db(self._db_path, busy_timeout_ms=30_000)
        try:
            decay_stale(conn)
            notice(conn)
            blocked = blocked_reason(conn, self._person)
            if blocked:
                logger.debug("surface: holding — %s", blocked)
                return None
            cand = next_candidate(conn)
            if cand is None:
                return None

            draft = await asyncio.to_thread(self._compose, conn, cand["text"])
            # Declining is a real outcome and the common one. The noticing is
            # marked surfaced either way: the being considered it, and
            # reconsidering it every five minutes would be a groove.
            if not draft or draft.strip().upper().startswith("NOTHING"):
                logger.info("surface: considered and let it go — %s",
                            cand["text"][:70])
                mark_surfaced(conn, cand["id"], None)
                return None

            if self._gate_factory is None:
                logger.warning("surface: no gate configured — not sending")
                return None
            verdict = self._gate_factory(conn).judge(
                draft, channel="telegram", attempt=0)
            if verdict.verdict != "pass":
                # No revise loop here. A first-contact message that needs
                # reworking is one the being should simply not send; there is
                # no one waiting on it.
                logger.info("surface: gate held an unprompted message (%s)",
                            verdict.verdict)
                mark_surfaced(conn, cand["id"], None)
                return None

            ok = await self._channel.send(draft)
            if not ok:
                logger.warning("surface: send failed; leaving it pending")
                return None
            msg_id = record_message(
                conn, channel="telegram", direction="out",
                person_id=self._person, content=draft, verdict="pass")
            mark_surfaced(conn, cand["id"], msg_id)
            logger.info("surface: the being spoke first — %s", draft[:90])
            return draft
        finally:
            conn.close()

    async def run(self) -> None:
        import asyncio

        if not self._enabled:
            logger.info("surface scheduler: disabled")
            return
        logger.info(
            "surface scheduler: wake %02d-%02d, maturity %dm, gap %.0fh, "
            "cooldown %dm", WAKE_START_HOUR, WAKE_END_HOUR, MATURITY_S // 60,
            SURFACE_GAP_S / 3600, OPERATOR_COOLDOWN_S // 60)
        while True:
            await asyncio.sleep(self._interval)
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                from newz.crash import log_crash

                log_crash(self._db_path.parent.parent, "surface scheduler")
                logger.exception("surface scheduler failed — retrying")
