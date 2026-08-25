"""The operator's verdict on a piece, and its one delivery to the being.

**What this closes.** The writing loop grades itself on one axis only. The
re-read asks whether a piece is still *correct* and answers it well — two of
five completed turns produced substantive corrections of mechanism. Nothing in
the loop asks whether a piece is *worth reading*, and nothing can: `compose.py`
refuses a quality judge because a judge that is the being's own model produces
operation and never evidence (Rule 4), and TRUE_NORTH puts readiness in the
operator's judgement alone with no rubric permitted. The verdict was reserved
for a person and never collected.

**Where it is allowed to land, and where it is not.** An appraisal reaches the
being at RE-READ and never at COMPOSE. Re-reading is retrospective and about
one piece that already exists; composing is prospective, and an appraisal in
the composition prompt is an instruction about how to write next — which is how
a being learns to write for its operator. That is E3.8's `operator_agreement`
concern wearing a human face: the item most likely to move under any process
optimising for a quiet week. The restraint is the design, not an omission.

**Once, and at-least-once.** Every undelivered note for a piece is handed over
together and then stamped, so a note is a judgement about one piece rather than
a standing instruction repeated for weeks. The stamp is written with the
verdict, after `apply_verdict` has succeeded — never at prompt-build time. One
re-read in six has already failed in life, so an early stamp would consume
notes into silence, and a swallowed note is invisible because
delivered-and-lost looks exactly like delivered-and-heeded.

**The loop has to close through a person.** A piece marked not publishable is
withheld from the surface; the being reads the note and may revise on those
grounds. If the verdict could not then change, nothing the being did would
change anything, which teaches that acting on criticism is inert — a worse
teacher than silence. So a piece revised since its newest appraisal returns to
`due_for_appraisal`. It does NOT clear its own verdict by being rewritten:
that would hand the publish decision back to the being, which is exactly what
the operator asked to take out of its hands.
"""

from __future__ import annotations

import sqlite3
import time

# After this many failed re-read turns, a piece stops jumping the re-read queue
# and rejoins the ordinary rotation with its note still undelivered. Priority
# plus at-least-once livelock each other without it: a piece whose re-read
# keeps failing keeps its undelivered note, therefore keeps sorting first,
# therefore is retried every turn while charging the day's ceiling — which
# `starts_today` takes before anything is spent.
MAX_DELIVERY_FAILS = 3


def current_verdict(conn: sqlite3.Connection, work_id: int) -> int | None:
    """The newest verdict for a piece, or None if nobody has judged it.

    Newest wins because a piece can be appraised more than once and the last
    word is the operator's current one. There is no denormalised copy on
    `works`, so this query is the only place the answer lives.
    """
    row = conn.execute(
        "SELECT publishable FROM work_appraisals WHERE work_id=?"
        " ORDER BY ts DESC, id DESC LIMIT 1", (work_id,)).fetchone()
    return None if row is None else int(row[0])


def withheld(conn: sqlite3.Connection) -> set[int]:
    """Pieces whose newest verdict is no. What the surface must not write.

    Withholding is not deletion: the row, the body and the signature are
    untouched, the piece is still re-read, and it returns to the surface the
    moment a newer appraisal says so.
    """
    try:
        rows = conn.execute(
            "SELECT work_id FROM work_appraisals a WHERE publishable = 0"
            " AND ts = (SELECT MAX(ts) FROM work_appraisals b"
            "           WHERE b.work_id = a.work_id)").fetchall()
    except sqlite3.OperationalError:
        # A store mid-migration has no such table, and a generator that
        # assumes a schema renders nothing rather than what is there.
        return set()
    return {int(r[0]) for r in rows}


def undelivered(conn: sqlite3.Connection, work_id: int) -> list[sqlite3.Row]:
    """Every note the being has not been shown for this piece, oldest first."""
    try:
        return list(conn.execute(
            "SELECT * FROM work_appraisals WHERE work_id=?"
            " AND delivered_at IS NULL ORDER BY ts, id", (work_id,)))
    except sqlite3.OperationalError:
        return []


def deliverable(conn: sqlite3.Connection, work_id: int) -> list[sqlite3.Row]:
    """Undelivered notes that have not exhausted their delivery attempts."""
    return [r for r in undelivered(conn, work_id)
            if (r["deliver_fails"] or 0) < MAX_DELIVERY_FAILS]


def render(rows) -> str:
    """What the being is shown. What the operator said, never a fact.

    `holds.py::STATUS_TEXT` sets this convention for the gate — "reviewed by my
    operator: the stop was mistaken" — and it holds for the same reason. The
    being may leave a piece standing that its operator would not publish, and
    that disagreement is a better record than either verdict alone, so the
    prompt reports and does not adjudicate.

    Both verdicts travel *(operator, 2026-08-24: "the system needs to take in
    all notes")*. Showing only the criticism would be easier to defend against
    gaming and would be a partial record of what was said.
    """
    if not rows:
        return ""
    out = []
    for r in rows:
        verdict = ("judged it good enough to publish" if r["publishable"]
                   else "judged it not good enough to publish")
        line = f"My operator read this and {verdict}."
        note = (r["note"] or "").strip()
        if note:
            line += f' They said:\n"{note}"'
        out.append(line)
    return "\n\n".join(out)


def mark_delivered(conn: sqlite3.Connection, rows, *,
                   now: float | None = None) -> None:
    """Stamp notes as seen. Called with the verdict, never before it.

    No commit here: the caller commits this together with the re-read outcome,
    so a turn that dies between the model call and the outcome redelivers the
    note instead of losing it.
    """
    now = now or time.time()
    for r in rows:
        conn.execute("UPDATE work_appraisals SET delivered_at=? WHERE id=?",
                     (now, r["id"]))


def mark_delivery_failed(conn: sqlite3.Connection, rows) -> None:
    """A turn that carried these notes did not finish. Charge the attempt."""
    for r in rows:
        conn.execute(
            "UPDATE work_appraisals SET deliver_fails = deliver_fails + 1"
            " WHERE id=?", (r["id"],))


def record(conn: sqlite3.Connection, work_id: int, publishable: bool,
           note: str = "", *, now: float | None = None) -> int:
    """The operator's one supported writer.

    `publishable` is a yes/no answer and the schema refuses anything else, so
    there is no path by which this becomes a score.
    """
    cur = conn.execute(
        "INSERT INTO work_appraisals (ts, work_id, publishable, note)"
        " VALUES (?,?,?,?)",
        (now or time.time(), work_id, 1 if publishable else 0, note.strip()))
    conn.commit()
    return int(cur.lastrowid)


def due_for_appraisal(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Standing pieces waiting on the operator, oldest first.

    Two kinds, and the second is what closes the loop: a piece nobody has
    judged, and a piece the being has revised since the last time it was
    judged. Without the second, a being that acts on a note stays withheld
    forever and learns that acting on criticism changes nothing.

    Standing only. `due_for_reread` selects `status='standing'`, so a note on a
    retracted piece would have no delivery path and would sit undelivered
    forever — the dead letter is prevented by not offering the piece rather
    than by handling it later.
    """
    return list(conn.execute(
        "SELECT w.* FROM works w"
        " WHERE w.status='standing'"
        "   AND ("
        "     NOT EXISTS (SELECT 1 FROM work_appraisals a WHERE a.work_id=w.id)"
        "     OR EXISTS ("
        "       SELECT 1 FROM work_revisions r"
        "       WHERE r.work_id = w.id"
        "         AND r.ts > (SELECT MAX(a.ts) FROM work_appraisals a"
        "                     WHERE a.work_id = w.id))"
        "   )"
        " ORDER BY w.ts"))
