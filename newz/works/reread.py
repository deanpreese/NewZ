"""Re-reading, revision and retraction (P4 epic E2.2).

**Why this is the part that matters under one operator.** P4's Phase 2 intent:
*"give the being a body of work that accretes, and — the part that matters most
under one operator — let it encounter its own past self as an external
object."* With no readers, re-reading what it wrote in March and finding it
wrong is the cheapest genuine outcome it did not grade at the time it wrote it.

**A retraction is a first-class outcome, not a deletion.** The prior text is
kept and neither the revision record nor the piece can be removed (0031's
triggers) — E1.5's rule at the claim layer, applied to the work. A being that
can quietly unwrite a piece has no body of work, only a current opinion.

**Standing is the ordinary answer.** A re-read that revises everything is not
judgment, it is churn, and P4's Phase 2 decision rule reads the opposite failure
too: *"produces on rhythm but never revises → the re-read is decorative."* Both
are visible in the record, because standing is recorded as its own outcome.
"""

from __future__ import annotations

import datetime as _dt
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from newz.llm.xml_parser import XMLExtractionError, extract_xml, optional_text, require_text
from newz.works.appraisal import (MAX_DELIVERY_FAILS, deliverable,
                                  mark_delivery_failed, render)
from newz.works.compose import PIECE_TOKEN_BUDGET, _system_prompt

logger = logging.getLogger(__name__)

DAY = 86400.0
# A piece is re-read no sooner than this. Re-reading yesterday's work is
# proofreading; the point is to meet it as something written by someone else.
MIN_AGE_S = 3 * DAY
MAX_STARTS_PER_DAY = 2
INTERVAL_S = 6 * 3600.0
BOOT_DELAY_S = 300.0
REVIEW_TOKEN_BUDGET = 600


@dataclass
class Verdict:
    kind: str                 # stands | revised | retracted
    reason: str = ""
    title: str = ""
    body: str = ""


@dataclass
class RereadResult:
    work_id: int | None = None
    kind: str = ""
    skipped: str = ""
    notes_delivered: int = 0


def starts_today(conn: sqlite3.Connection, *, now: float | None = None) -> int:
    """Re-reads STARTED in the rolling 24h — what R-25 caps.

    **A turn that found nothing did not start anything.** R-25's ceiling is on
    what is *started* — "deliberations started per day, not completed" — and
    `no_subject` / `nothing_due` rows are the record of a turn that found no
    work. They are written on purpose, so a rhythm with nothing to do is
    visible rather than looking like one that never ran, but counting them
    spends the day's allowance on having looked. Measured 2026-08-22: two
    `nothing_due` re-reads and one failure filled a cap of two, and the re-read
    rhythm sat out three consecutive turns for it.
    """
    return conn.execute(
        "SELECT COUNT(*) FROM work_attempts WHERE kind='reread'"
        " AND outcome NOT IN ('no_subject', 'nothing_due') AND ts > ?",
        ((now or time.time()) - DAY,)).fetchone()[0]


def _record(conn: sqlite3.Connection, outcome: str, *, work_id=None,
            note: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO work_attempts (ts, kind, outcome, work_id, note)"
        " VALUES (?, 'reread', ?, ?, ?)",
        (time.time(), outcome, work_id, note[:400]))
    conn.commit()
    return int(cur.lastrowid)


def due_for_reread(conn: sqlite3.Connection, *, min_age_s: float = MIN_AGE_S,
                   now: float | None = None):
    """The oldest standing piece nobody has looked at recently.

    **A piece carrying an undelivered note goes first.** Sixteen pieces at two
    re-reads a day is an eight-day cycle, and a critique delivered eight days
    late is a critique of a self the being has already moved past. The jump is
    bounded twice: a note delivers once, so the piece rejoins the ordinary
    rotation immediately afterwards, and a note whose turns keep failing stops
    jumping after `MAX_DELIVERY_FAILS` rather than holding the front of the
    queue while charging the day's ceiling.

    **The age gate still binds.** A fresh piece with a note waits until it is
    old enough, because meeting the work as a stranger is the point of the
    three days and prompt delivery is not worth spending it.
    """
    now = now or time.time()
    args = (now - min_age_s, now - min_age_s)
    try:
        return conn.execute(
            "SELECT * FROM works WHERE status='standing' AND ts <= ?"
            " AND (last_reviewed_at IS NULL OR last_reviewed_at <= ?)"
            " ORDER BY (SELECT COUNT(*) FROM work_appraisals a"
            "           WHERE a.work_id = works.id"
            "             AND a.delivered_at IS NULL"
            f"             AND a.deliver_fails < {MAX_DELIVERY_FAILS}) > 0 DESC,"
            "          COALESCE(last_reviewed_at, ts) ASC LIMIT 1",
            args).fetchone()
    except sqlite3.OperationalError:
        # A store that has not taken 0044 yet. The rhythm predates appraisal
        # and must not stop for the absence of it.
        return conn.execute(
            "SELECT * FROM works WHERE status='standing' AND ts <= ?"
            " AND (last_reviewed_at IS NULL OR last_reviewed_at <= ?)"
            " ORDER BY COALESCE(last_reviewed_at, ts) ASC LIMIT 1",
            args).fetchone()


def review(client, conn: sqlite3.Connection, work, *, notes=()) -> Verdict:
    """Read it as a stranger would, and say what it is now worth.

    **`notes` are the operator's, and they arrive here and nowhere else.** An
    appraisal is retrospective — it is about this piece, which already exists.
    The same sentence in the composition prompt would be an instruction about
    how to write the next one, which is how a being learns to write for its
    operator, so `compose.py` is never given them.

    They are placed AFTER the piece and BEFORE the question, reported as what a
    person said rather than as a fact about the text. The being is free to
    leave standing something its operator would not publish; the prompt does
    not adjudicate that disagreement.
    """
    system = _system_prompt(conn) + (
        "\n\n## Right now\n"
        "You are re-reading something you wrote a while ago. Read it as if "
        "someone else wrote it. You are not being asked to improve it."
    )
    user = (
        f"You wrote this on {_dt.datetime.fromtimestamp(work['ts']):%Y-%m-%d}, "
        f"about: {work['subject_text']}\n"
        f"At the time you chose it because: {work['chosen_because']}\n\n"
        f"# {work['title']}\n\n{work['body']}\n\n"
        "---\n\n"
        + (render(notes) + "\n\n---\n\n" if notes else "")
        + "Does this still hold?\n\n"
        "  stands   — you would still put your name to it. This is the ordinary\n"
        "             answer and needs no defence.\n"
        "  revise   — part of it is wrong or has been overtaken, and you can say\n"
        "             what and write it again properly.\n"
        "  retract  — its central claim does not survive. Retracting is not a\n"
        "             failure; it is the only honest thing to do with a piece\n"
        "             you no longer believe, and the old text is kept either way.\n\n"
        "Do not revise for style, length or polish. Something must be WRONG.\n\n"
        "Reply with XML only:\n"
        "<review><verdict>stands|revise|retract</verdict>"
        "<reason>what changed your mind, or why it still holds</reason>"
        "<title>if revising: the new title</title>"
        "<body>if revising: the whole piece, rewritten</body></review>"
    )
    # **One retry, then fail loudly** — the pattern `compose_piece` and
    # `choose_subject` already use in this subsystem, and which this call was
    # the only one to lack.
    #
    # Measured 2026-08-22 by replaying this prompt against all seven works,
    # 17 samples: **15 parsed, 2 failed — 11.8%**. The failures are independent
    # draws, not a property of the input: work 1, the piece whose review died
    # in life on 2026-08-21, parsed **4 of 5** on replay. One retry takes ~12%
    # to roughly 1.4%.
    #
    # Both failures carried the identical signature — `<body>` opened and
    # closed with `</reason>`, the tag last used on a long prose field. It is a
    # decoy and not a distance problem: work 4 is 494 words and failed, while
    # `compose` emits a 7,034-character body in the same shape and parsed 6 of
    # 6. Renaming or reordering the fields is the fix for the mechanism; this
    # is the fix for the cost of it, and it is the one the evidence supports.
    last_error: Exception | None = None
    for attempt in (1, 2):
        result = client.complete("VOICE", system, user,
                                 max_tokens=PIECE_TOKEN_BUDGET, temperature=0.7,
                                 function="reread")
        try:
            el = extract_xml(result.text, "review")
            break
        except XMLExtractionError as exc:
            last_error = exc
            logger.warning("review XML unparseable (%s); retrying once", exc)
    else:
        raise XMLExtractionError(
            f"could not extract a review from two attempts: {last_error}")
    verdict = require_text(el, "verdict").strip().lower()
    reason = optional_text(el, "reason").strip()
    if verdict.startswith("retract"):
        return Verdict("retracted", reason)
    if verdict.startswith("revis"):
        body = optional_text(el, "body").strip()
        title = optional_text(el, "title").strip() or work["title"]
        if not body:
            # A revision that rewrites nothing is a verdict it could not act
            # on. Recorded as standing rather than silently applied, so the
            # decision rule reads the truth: it did not revise.
            logger.info("work %d: revise with no new body — recorded as standing",
                        work["id"])
            return Verdict("stands", reason or "said revise, wrote nothing")
        return Verdict("revised", reason, title, body)
    return Verdict("stands", reason)


def apply_verdict(conn: sqlite3.Connection, work, v: Verdict, *,
                  notes=(), commit: bool = True) -> None:
    """Keep what it used to say, then change what it says now.

    **The signature moves with the text (0044).** This wrote `title` and `body`
    and left `signature` alone, so the first revision of a signed piece would
    have made `read_works.py --verify` report it ALTERED — "edited since it was
    written", which for a body of work is precisely what a signature exists to
    catch. It never fired because the only two pieces ever revised, works 1 and
    4, predate E3.1 and are unsigned, while every piece from 6 on is signed.
    Appraisal exists to cause revisions, so it is the trigger as much as the
    fix. The prior signature is kept on the revision row beside the prior title
    and body it attested to: a revised piece is the same piece saying something
    new, its signature attests to what it says now, and the chain back to what
    it said before is unbroken.

    **`notes` are stamped here or not at all.** Delivery is recorded in the same
    transaction as the verdict, so a turn that dies after the model call
    redelivers rather than swallowing. An unsigned piece keeps `NULL` — a
    signature computed now would attest to the row rather than to what was
    written, which is the reason those five were never backfilled.
    """
    from newz.works.appraisal import mark_delivered

    now = time.time()
    if v.kind == "stands":
        conn.execute("UPDATE works SET last_reviewed_at=? WHERE id=?",
                     (now, work["id"]))
        mark_delivered(conn, notes, now=now)
        if commit:
            conn.commit()
        return

    keys = work.keys()
    prior_sig = work["signature"] if "signature" in keys else None
    try:
        conn.execute(
            "INSERT INTO work_revisions (ts, work_id, kind, reason, prior_title,"
            " prior_body, prior_word_count, prior_signature)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (now, work["id"], v.kind, v.reason or "(no reason given)",
             work["title"], work["body"], work["word_count"], prior_sig))
    except sqlite3.OperationalError:
        # A store that has not taken 0044. Recording the revision matters more
        # than recording what it superseded.
        conn.execute(
            "INSERT INTO work_revisions (ts, work_id, kind, reason, prior_title,"
            " prior_body, prior_word_count) VALUES (?,?,?,?,?,?,?)",
            (now, work["id"], v.kind, v.reason or "(no reason given)",
             work["title"], work["body"], work["word_count"]))

    if v.kind == "retracted":
        conn.execute("UPDATE works SET status='retracted', last_reviewed_at=?"
                     " WHERE id=?", (now, work["id"]))
    else:
        from newz.works.compose import signature_of

        new_sig = None if prior_sig is None else signature_of(
            work["subject_kind"], work["subject_ref"], v.title, v.body)
        conn.execute(
            "UPDATE works SET title=?, body=?, word_count=?, status='standing',"
            " last_reviewed_at=?, signature=COALESCE(?, signature) WHERE id=?",
            (v.title, v.body, len(v.body.split()), now, new_sig, work["id"]))
    mark_delivered(conn, notes, now=now)
    if commit:
        conn.commit()


def reread_once(conn: sqlite3.Connection, client, *,
                max_starts: int = MAX_STARTS_PER_DAY,
                min_age_s: float = MIN_AGE_S,
                now: float | None = None) -> RereadResult:
    """One turn. The attempt is charged before anything is spent (R-25)."""
    if starts_today(conn, now=now) >= max_starts:
        return RereadResult(skipped=f"already re-read {max_starts} today")

    work = due_for_reread(conn, min_age_s=min_age_s, now=now)
    if work is None:
        _record(conn, "nothing_due", note="no standing piece is old enough")
        return RereadResult(skipped="nothing old enough to re-read")

    notes = deliverable(conn, work["id"])
    attempt = _record(conn, "started", work_id=work["id"])
    try:
        v = review(client, conn, work, notes=notes)
        # `commit=False`: the verdict, the delivery stamp and the outcome are
        # one transaction. A note is consumed only by a turn that finished.
        apply_verdict(conn, work, v, notes=notes, commit=False)
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        mark_delivery_failed(conn, notes)
        conn.execute("UPDATE work_attempts SET outcome='failed', note=?"
                     " WHERE id=?", (f"{type(e).__name__}: {e}"[:400], attempt))
        conn.commit()
        raise

    conn.execute("UPDATE work_attempts SET outcome=? WHERE id=?",
                 (v.kind, attempt))
    conn.commit()
    if notes:
        logger.info("work %d: delivered %d operator note(s)",
                    work["id"], len(notes))
    logger.info("work %d re-read: %s — %s", work["id"], v.kind, v.reason[:80])
    return RereadResult(work_id=work["id"], kind=v.kind,
                        notes_delivered=len(notes))


class RereadScheduler:
    """The cadence, standing off sleep's window as the others do (R-20)."""

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

    def _turn(self) -> RereadResult:
        from newz.store.db import open_db

        conn = open_db(self._db_path)
        try:
            return reread_once(conn, self._client, max_starts=self._max_starts)
        finally:
            conn.close()

    async def run(self) -> None:
        import asyncio

        from newz.crash import log_crash

        logger.info("re-reading rhythm: every %.1fh, at most %d/day, pieces "
                    "older than %.0f days", self._interval / 3600,
                    self._max_starts, MIN_AGE_S / DAY)
        first = True
        while True:
            await asyncio.sleep(BOOT_DELAY_S if first else self._interval)
            first = False
            if self._in_quiet_window():
                continue
            try:
                r = await asyncio.to_thread(self._turn)
                if r.skipped:
                    logger.info("re-read skipped: %s", r.skipped)
            except asyncio.CancelledError:
                raise
            except Exception:
                log_crash(self._db_path.parent.parent, "re-reading rhythm")
                logger.exception("re-read failed — retrying next cadence")
