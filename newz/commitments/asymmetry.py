"""The asymmetry (P4 epic E4.2) — revision on evidence is free, abandonment
without cause costs.

E4.1 made identity authorable and E4.3 made it traceable. Neither held the
being to anything: `status` never left `standing`, so a commitment was a note
with a falsifier attached. This is what makes dropping one an act with a
consequence.

**The asymmetry is checked by a join, not a judgment.** A change is free if and
only if it cites a `resolutions` row that is actually settled — the world said
something, so changing your mind is what a mind is for. Without one, the being
changed its mind because it felt like it. Rule 4 forbids asking the model
whether an abandonment was justified, and a model asked that question would
justify every one of them; so the being says WHICH claim settled it and the
code checks whether that claim settled.

**The direction this must not run.** PLAN's own E4.2 says it: backwards, this
entrenches a mediocre early position and manufactures §6's "fixed personality
script" — a being that cannot afford to stop believing something it committed
to at eight days old. P3-05 calls the balance a guess rather than a
measurement, and it is. The cost is INV-031's `CONFIDENCE_ON_CONTRADICT`,
chosen because it is the same magnitude the world's own refutation carries, not
because anything measured it. **Revisit it against the first month of
abandonments rather than defending it.**

**The cost is deferred, exactly as E1.4's is.** The review runs after the night
is committed, so a review that raises cannot cost the Perspective. The charge
lands on the NEXT sleep through the same unpaid-queue pattern
`apply_world_costs` uses — mutating the items sleep is about to decay, so a
position taken under the floor is released by the ordinary path (INV-025). A
change awaiting its cost is not a change that escaped one.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass

from newz.commitments.store import standing
from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml
from newz.sleep.nightly import (
    CONFIDENCE_ON_CONTRADICT, CONFIDENCE_ON_REPEAT_CONTRADICT,
)
from newz.sleep.perspective import RELEASE_BELOW

logger = logging.getLogger(__name__)


@dataclass
class Change:
    commitment_id: int
    kind: str                       # revised | abandoned
    free: bool                      # a settled resolution carried it
    reason: str = ""


@dataclass
class ChangeCost:
    change_id: int
    item_text: str
    before: float
    after: float
    repeat: bool
    released: bool


_SYSTEM = ("You are the being. Answer only in the XML asked for. "
           "Do not explain, do not preface, do not add commentary.")

_TASK = """<task>
These are the things I have committed myself to. Does any of them no longer
hold?

Changing my mind is not a failure. **What costs me is changing it for no
reason.** If something in the world settled a claim of mine and that is why a
commitment no longer stands, say which claim — that is a mind working, and it
costs nothing. If I simply do not want to keep this any more, that is allowed
too, and it will cost the positions I made the commitment on the strength of.

Most nights nothing here has changed. That is the ordinary answer.

Output ONLY:

<review>
  <change>no|revised|abandoned</change>
  <commitment>the id of the one that changed</commitment>
  <reason>why, in one sentence</reason>
  <resolution>the id of the claim that settled it, or empty</resolution>
  <statement>if revised: the new statement</statement>
  <falsifier>if revised: what would now show I had stopped</falsifier>
</review>

**revised** means it still holds in a changed form — I still care about this,
but about a different version of it. The falsifier has to change with it, or I
have revised the words and kept the slogan.

**abandoned** means it no longer holds at all.

Do not cite a claim that did not settle this. The claim id is checked against
what the world actually returned, and citing one that did not settle it is not
free — it is the same as citing nothing, and the record will show I reached for
a reason I did not have.
</task>"""


def _settled(conn: sqlite3.Connection, resolution_id: int | None) -> bool:
    """Did the world actually say something? A join, never a judgment."""
    if not resolution_id:
        return False
    row = conn.execute(
        "SELECT status FROM resolutions WHERE id=?", (resolution_id,)).fetchone()
    return bool(row) and row["status"] == "resolved"


def record_change(conn: sqlite3.Connection, *, commitment_id: int, kind: str,
                  reason: str, resolution_id: int | None = None,
                  statement: str = "", falsifier: str = "",
                  now: float | None = None) -> Change | None:
    """Write the change and move the commitment. Returns None if there is no
    such standing commitment — a review naming one that is already gone is a
    stale answer, not an act.
    """
    now = now or time.time()
    row = conn.execute(
        "SELECT id, statement, falsifier, status FROM commitments WHERE id=?",
        (commitment_id,)).fetchone()
    if row is None or row["status"] != "standing":
        logger.info("commitment %s is not standing; the change is dropped",
                    commitment_id)
        return None

    free = _settled(conn, resolution_id)
    cited = resolution_id if free else None
    conn.execute(
        "INSERT INTO commitment_changes (ts, commitment_id, kind, reason,"
        " prior_statement, prior_falsifier, resolution_id, cost_applied_at,"
        " cost_note) VALUES (?,?,?,?,?,?,?,?,?)",
        (now, commitment_id, kind, reason, row["statement"], row["falsifier"],
         cited,
         # A free change is settled here and now: there is nothing to charge,
         # and leaving it unpaid would put it in the queue forever.
         now if free else None,
         "carried by a settled claim" if free else None))
    if kind == "revised" and statement and falsifier:
        conn.execute(
            "UPDATE commitments SET statement=?, falsifier=? WHERE id=?",
            (statement.strip(), falsifier.strip(), commitment_id))
    else:
        # Abandoned, or revised without new text — which is an abandonment
        # that did not say so. The slot frees either way; the row stays.
        conn.execute("UPDATE commitments SET status=? WHERE id=?",
                     ("revised" if kind == "revised" else "abandoned",
                      commitment_id))
    conn.commit()
    logger.info("commitment %d %s%s: %s", commitment_id, kind,
                " (carried by a settled claim)" if free else " — this will cost",
                reason[:80])
    return Change(commitment_id=commitment_id, kind=kind, free=free,
                  reason=reason)


def review_standing(conn: sqlite3.Connection, client: LLMClient, *,
                    now: float | None = None) -> Change | None:
    """Ask whether any standing commitment no longer holds.

    Called from sleep after the night is committed, beside the authoring door.
    Fails closed: the caller treats an exception as "nothing changed tonight".
    """
    held = standing(conn)
    if not held:
        return None
    listing = "\n".join(
        f"{c.id}. [{c.kind}] {c.statement}  (broken by: {c.falsifier})"
        for c in held)
    try:
        result = client.complete("DEEP", _SYSTEM,
                                 f"{_TASK}\n\n<commitments>\n{listing}\n"
                                 f"</commitments>",
                                 max_tokens=500, temperature=0.3,
                                 function="commitment_review")
        root = extract_xml(result.text, "review")
    except (XMLExtractionError, Exception):  # noqa: BLE001
        logger.info("commitment review: unreadable answer, nothing changed")
        return None

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    kind = text_of("change").lower()
    if kind not in ("revised", "abandoned"):
        return None
    cid = text_of("commitment")
    if not cid.isdigit():
        return None
    reason = text_of("reason") or "no reason given"
    rid = text_of("resolution")
    return record_change(
        conn, commitment_id=int(cid), kind=kind, reason=reason,
        resolution_id=int(rid) if rid.isdigit() else None,
        statement=text_of("statement"), falsifier=text_of("falsifier"),
        now=now)


def unpaid_changes(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Changes the world did not carry, still to be charged."""
    return conn.execute(
        "SELECT ch.id, ch.commitment_id, ch.kind, c.evidence_json"
        " FROM commitment_changes ch"
        " JOIN commitments c ON c.id = ch.commitment_id"
        " WHERE ch.cost_applied_at IS NULL ORDER BY ch.ts").fetchall()


def _charged_before(conn: sqlite3.Connection, item_text: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM commitment_costs WHERE item_text=? LIMIT 1",
        (item_text,)).fetchone())


def apply_change_costs(conn: sqlite3.Connection, items: list) -> list[ChangeCost]:
    """Charge every abandonment the world did not carry (E4.2).

    Mutates `items` in place — the same objects sleep is about to decay, merge
    and save — so a position taken under the floor leaves by the ordinary path
    (INV-025) rather than by anything here. `apply_world_costs`'s shape exactly,
    against a different cause.

    **Who pays is traced, not judged**: the commitment's own `evidence` (E4.3)
    names the episodes it was made on the strength of, and the positions charged
    are those whose grounding includes them. A commitment that traced nothing
    costs nothing, and that is recorded rather than left looking unprocessed —
    the being can drop something it never grounded, and that is a different
    finding from an abandonment nobody paid for (INV-044).
    """
    charged: list[ChangeCost] = []
    now = time.time()
    for row in unpaid_changes(conn):
        refs = {str(r) for r in json.loads(row["evidence_json"] or "[]")}
        paid = [it for it in items
                if refs and refs & {str(e) for e in it.evidence}]

        if not paid:
            conn.execute(
                "UPDATE commitment_changes SET cost_applied_at=?, cost_note=?"
                " WHERE id=?",
                (now, "no position traced to this commitment", row["id"]))
            logger.info("commitment %d was %s and cost nothing: it was "
                        "grounded in no position still held",
                        row["commitment_id"], row["kind"])
            continue

        for it in paid:
            repeat = _charged_before(conn, it.text)
            cost = (CONFIDENCE_ON_REPEAT_CONTRADICT if repeat
                    else CONFIDENCE_ON_CONTRADICT)
            before = it.confidence
            it.confidence = round(max(0.0, before - cost), 3)
            it.status = "disputed"
            record = ChangeCost(change_id=row["id"], item_text=it.text,
                                before=before, after=it.confidence,
                                repeat=repeat,
                                released=it.confidence < RELEASE_BELOW)
            conn.execute(
                "INSERT INTO commitment_costs (ts, change_id, item_text,"
                " section, confidence_before, confidence_after, repeat,"
                " released) VALUES (?,?,?,?,?,?,?,?)",
                (now, row["id"], it.text, it.section, before, it.confidence,
                 int(repeat), int(record.released)))
            charged.append(record)
            logger.info("dropping a commitment cost a position%s: %.2f -> "
                        "%.2f%s — %s", " again" if repeat else "", before,
                        it.confidence, " (released)" if record.released else "",
                        it.text[:70])

        conn.execute(
            "UPDATE commitment_changes SET cost_applied_at=?, cost_note=?"
            " WHERE id=?",
            (now, f"cost {len(paid)} position(s)", row["id"]))
    conn.commit()
    return charged
