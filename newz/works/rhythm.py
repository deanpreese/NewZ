"""Writing as a rhythm (P4 epic E2.1).

**Rule 5: production is a rhythm; only judgment is an initiative.** The being
does not decide to write. It writes on cadence, the way it sleeps on cadence,
and the only judgment in the loop is which subject it picks. P4's Rule 5 says
why: measured initiative is weak — 91 noticings, 18 surfaced, 49 still pending,
and a conversation opener that had never fired in life — so a design waiting for
the being to *choose* to produce will idle.

**The ceiling counts starts, never products (R-25).** An outcome-based budget
pays for success and charges nothing for failure, so a session that dies
mid-composition costs nothing and can be retried without limit; a restart loop
then becomes unbounded spend. The attempt row is therefore committed *before*
the first model call. Deliberation learned this as R-18 — "a started
deliberation costs budget whatever it produces" — and this is the same rule for
writing.

**A lost session costs that session and nothing else.** Nothing partial is
stored: `write_work` runs once, at the end, or not at all. A process killed
mid-composition leaves one `started` row, the day's allowance one lower, and no
half-piece anywhere. The next cadence tick simply picks a subject and begins.
"""

from __future__ import annotations

import datetime as _dt
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from newz.works.compose import (
    Piece,
    candidate_subjects,
    choose_subject,
    compose_piece,
    write_work,
)

logger = logging.getLogger(__name__)

DAY = 86400.0
# Two starts a day against a ~3,000-token piece. Deliberate and low: the being
# has 123 concerns and a Perspective to write about, and the constraint worth
# respecting is not how much it can produce but whether anything reads what it
# produced. Raise it when there is a reader, not before.
# A piece every six hours, which is four a day *(operator, 2026-08-22)*.
# **The interval and the ceiling now say the same thing.** They were 4h and 2,
# so the cadence promised a turn every four hours while the cap allowed two —
# the ceiling was the real rhythm and the interval was decoration. Six and four
# agree, and they agree with the surface: PublishScheduler regenerates every
# six hours, so a piece is written and visible inside one cycle rather than
# waiting on the next.
#
# **Back to two a day, 2026-08-24, because the reader arrived.** The paragraph
# above this one has always said what governs: *"the constraint worth
# respecting is not how much it can produce but whether anything reads what it
# produced. Raise it when there is a reader, not before."* It was raised to
# four on 2026-08-22 while there was still no reader. Appraisal (0044) makes
# the operator one, and four a day is 28 pieces a week — nobody reads and
# judges 28 essays a week, so the appraisal queue would diverge from the day it
# was built and most pieces would never be judged at all. The field would exist
# and the loop it closes would not, defeated by arithmetic rather than by
# design.
#
# Two also puts production at parity with the re-read ceiling, so the being can
# review what it makes instead of falling permanently behind itself. If seven a
# week is still more than the operator reads, this constant is the one to
# change and nothing else moves with it.
MAX_STARTS_PER_DAY = 2
# Cadence. Checked often enough that a restart does not lose the day, rarely
# enough that the ceiling rather than the clock is what binds. Twelve and two
# agree, for the reason six and four did.
INTERVAL_S = 12 * 3600.0
BOOT_DELAY_S = 180.0


@dataclass
class RhythmResult:
    started: bool = False
    work_id: int | None = None
    subject: str = ""
    skipped: str = ""

    @property
    def wrote(self) -> bool:
        return self.work_id is not None


def starts_today(conn: sqlite3.Connection, *, now: float | None = None) -> int:
    """Writing attempts in the rolling 24h — what R-25 caps.

    **It counted every kind, and re-reads share the table.** `work_attempts`
    grew a `kind` column when the re-read rhythm arrived; `reread.starts_today`
    filters on it and this one did not, so a re-read turn spent the writing
    day's allowance. Two of them are enough: on 2026-08-22 the being wrote
    nothing for 25 hours because one write and two re-reads sat in the window
    against a cap of two — and **two of those three re-reads did nothing at
    all**, they were `nothing_due` turns. A ceiling on one rhythm must not be
    consumed by another, least of all by a turn that found no work.

    **A turn that found nothing did not start anything.** R-25's ceiling is on
    what is *started* — "deliberations started per day, not completed" — and a
    `no_subject` row is the record of a turn that found no work. It is written
    on purpose, so a rhythm with nothing to do is visible rather than looking
    like one that never ran, but counting it spends the day's allowance on
    having looked.
    """
    return conn.execute(
        "SELECT COUNT(*) FROM work_attempts WHERE kind='write'"
        " AND outcome NOT IN ('no_subject', 'nothing_due') AND ts > ?",
        ((now or time.time()) - DAY,)).fetchone()[0]


def _record(conn: sqlite3.Connection, outcome: str, *, subject=None,
            work_id: int | None = None, note: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO work_attempts (ts, kind, outcome, subject_kind, subject_ref,"
        " work_id, note) VALUES (?,'write',?,?,?,?,?)",
        (time.time(), outcome,
         subject.kind if subject else None,
         subject.ref if subject else None,
         work_id, note[:400]))
    conn.commit()
    return int(cur.lastrowid)


def close_subject(conn: sqlite3.Connection, piece: Piece, work_id: int) -> str:
    """Writing about a concern ends it *(operator, 2026-08-21)*.

    **The loop this breaks.** `score_concern` keys staleness on
    `last_advanced_at` and takes drag only from stalls and blocks, so an
    accepted advance resets the clock and costs nothing — a concern that keeps
    advancing is never dragged and stays at the top of the queue. Concern 112
    reached 44 advances with a stall count of 1 and never closed. And the only
    closure path that does not need an advance, `sweep.eligible`, selects
    `status='stalled'`, so it is structurally blind to exactly the concerns
    that circle. Nothing had ever judged one: `last_judged_at` was NULL on all
    125 rows.

    So this is a third exit, and the only one that asks no model anything:
    **the being has said its piece.** An essay is a more considered engagement
    with a question than any number of advances, and when it exists the concern
    is finished whether or not a judge would agree.

    **It carries no position, deliberately.** `judge_closure`'s closure writes a
    first-person sentence that sleep may admit into the Perspective. Taking one
    from the essay would make a work evidence for a position, which is exactly
    the self-echo trap E2.3 and R-24 exist to prevent. The position on this
    question *is* the piece — signed, stamped with the constitution and
    Perspective version that wrote it. The resolution names it and stops there.

    Returns the status afterwards. **The piece is never lost to this**: a
    failure here is logged and the work stands, because the work is the
    artifact and the closure is a consequence of it.
    """
    if piece.subject.kind != "concern":
        return ""
    from newz.concerns.store import close_concern

    # `close_concern` is an UPDATE with no rowcount check, so a subject that is
    # gone or already closed would report success and write a `concern_closed`
    # episode about it — a record that says something happened to a concern
    # that was not there. Read the status first and act only on a live one.
    row = conn.execute(
        "SELECT status FROM concerns WHERE id=?", (piece.subject.ref,)).fetchone()
    if row is None:
        logger.warning("work %d names concern %s, which does not exist",
                       work_id, piece.subject.ref)
        return "open"
    if row["status"] != "open":
        logger.info("concern %s was already %s when work %d landed",
                    piece.subject.ref, row["status"], work_id)
        return str(row["status"])

    try:
        close_concern(
            conn, int(piece.subject.ref), position="",
            resolution=f"said its piece — work {work_id}: {piece.title}")
    except Exception:  # noqa: BLE001
        logger.exception("concern %s stayed open; work %d stands",
                         piece.subject.ref, work_id)
        return "open"
    logger.info("concern %s closed by work %d", piece.subject.ref, work_id)
    return "closed"


def write_once(conn: sqlite3.Connection, client, *,
               max_starts: int = MAX_STARTS_PER_DAY,
               now: float | None = None) -> RhythmResult:
    """One turn of the rhythm. Charges the attempt before it spends anything."""
    if starts_today(conn, now=now) >= max_starts:
        return RhythmResult(skipped=f"already started {max_starts} today")

    subjects = candidate_subjects(conn)
    if not subjects:
        # Not a failure and not free: choosing nothing is still a turn, and a
        # rhythm with nothing left to write about should be visible in the
        # record rather than looking like a rhythm that never ran.
        _record(conn, "no_subject", note="nothing unwritten to write about")
        return RhythmResult(skipped="no unwritten subject")

    # Charged here, before the first model call. Everything after this point
    # may fail, and the day's allowance is already one lower.
    attempt = _record(conn, "started")

    try:
        subject, because = choose_subject(client, conn, subjects)
        piece = compose_piece(client, conn, subject, because)
        work_id = write_work(conn, piece)
        # The being has said its piece, so the question is finished — the third
        # exit, and the only one that asks no model anything. Inside the try
        # because a piece whose subject is gone is a broken record; the function
        # itself never raises, so a closure failure leaves the work standing.
        close_subject(conn, piece, work_id)
    except Exception as e:  # noqa: BLE001
        conn.execute("UPDATE work_attempts SET outcome='failed', note=?"
                     " WHERE id=?", (f"{type(e).__name__}: {e}"[:400], attempt))
        conn.commit()
        raise

    # A new piece changes what is distinctive across the corpus, so the tags
    # are a property of the corpus and not of the piece (E2.4). Recomputed
    # here rather than on read, so the reader stays a reader.
    try:
        from newz.works.subjects import recompute
        recompute(conn)
    except Exception:  # noqa: BLE001 — tags are a read, never the point
        logger.exception("tag recompute failed; the piece stands")

    conn.execute(
        "UPDATE work_attempts SET outcome='wrote', subject_kind=?,"
        " subject_ref=?, work_id=? WHERE id=?",
        (subject.kind, subject.ref, work_id, attempt))
    conn.commit()
    logger.info("wrote work %d on %s %d: %s", work_id, subject.kind,
                subject.ref, piece.title[:70])
    return RhythmResult(started=True, work_id=work_id,
                        subject=f"{subject.kind}:{subject.ref}")


class WritingScheduler:
    """The cadence. Stands off sleep's window, exactly as deliberation does."""

    def __init__(self, db_path: Path, client, *, interval_s: float = INTERVAL_S,
                 max_starts: int = MAX_STARTS_PER_DAY, quiet_hour: int = 3,
                 quiet_span_h: float = 1.5):
        self._db_path = db_path
        self._client = client
        self._interval = interval_s
        self._max_starts = max_starts
        self._quiet_hour = quiet_hour
        self._quiet_span = quiet_span_h

    def _in_quiet_window(self, now: _dt.datetime | None = None) -> bool:
        now = now or _dt.datetime.now()
        hours = now.hour + now.minute / 60.0
        return self._quiet_hour <= hours < (self._quiet_hour + self._quiet_span)

    def _turn(self) -> RhythmResult:
        from newz.store.db import open_db

        conn = open_db(self._db_path)
        try:
            return write_once(conn, self._client, max_starts=self._max_starts)
        finally:
            conn.close()

    async def run(self) -> None:
        import asyncio

        from newz.crash import log_crash

        logger.info("writing rhythm: every %.1fh, at most %d starts/day",
                    self._interval / 3600, self._max_starts)
        first = True
        while True:
            # Settle before the first turn, then run on cadence. Restart-spam
            # is safe because the ceiling counts attempts over a rolling 24h,
            # so ten restarts cannot buy more than the day's remainder.
            await asyncio.sleep(BOOT_DELAY_S if first else self._interval)
            first = False
            if self._in_quiet_window():
                logger.info("writing deferred: sleep's window")
                continue
            try:
                r = await asyncio.to_thread(self._turn)
                if r.skipped:
                    logger.info("writing skipped: %s", r.skipped)
            except asyncio.CancelledError:
                raise
            except Exception:
                # The rhythm survives a bad turn, and the turn still leaves
                # evidence — the attempt row is already 'failed' with its
                # reason by the time this runs.
                log_crash(self._db_path.parent.parent, "writing rhythm")
                logger.exception("writing failed — retrying next cadence")
