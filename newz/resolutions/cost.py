"""Being wrong costs the position (P3 epic E1.4).

INV-031's mechanism, pointed outward. It already makes a contradiction cost the
position it contradicts; until now the only thing able to contradict a position
was the being's own nightly observations, which is the loop P3 §1 measured as
50% self-grounded. A claim the world settled against the being is the first
contradiction from outside it, and it has to cost the same way or Phase 1 ends
at "the world disagreed" with nothing following.

**Who pays is traced, not judged.** A claim's provenance names the concern it
came from; every episode that concern produced carries `source_ref =
'concern:N'`; a Perspective item's evidence is a list of episode ids. The
position that pays is the one whose own grounding includes episodes from that
concern. No model chooses — Rule 4 forbids it, because the being's model
selecting which of the being's positions to punish is the being grading the
being, and it would pick whichever position the refutation was easiest to
narrate against.

**Sleep applies it.** INV-009 makes sleep the only writer of the Perspective,
and this changes confidences, so it runs inside sleep between confrontation and
decay — which is what lets the ordinary release floor (RELEASE_BELOW, INV-025)
carry a repeatedly-refuted position out the same night, through the path every
other released position takes.

**Tracing to nothing is a real outcome.** The being can be wrong about something
it never wrote into its Perspective. That is recorded on the claim rather than
left looking unprocessed, so the count of refutations that reached a position
stays honest (INV-044).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass

from newz.sleep.nightly import (
    CONFIDENCE_ON_CONTRADICT, CONFIDENCE_ON_REPEAT_CONTRADICT,
)
from newz.sleep.perspective import RELEASE_BELOW

logger = logging.getLogger(__name__)


@dataclass
class Cost:
    claim_id: int
    item_text: str
    before: float
    after: float
    repeat: bool = False
    released: bool = False


def _concern_episode_ids(conn: sqlite3.Connection, provenance: str) -> set[str]:
    """Episode ids belonging to the concern a claim came from.

    Episode ids are what a Perspective item cites as its evidence, and
    `source_ref` is what every concern episode carries. The intersection of
    the two is the trace.
    """
    if not provenance.startswith("concern:"):
        return set()
    return {str(r[0]) for r in conn.execute(
        "SELECT id FROM episodes WHERE source_ref = ?", (provenance,))}


def _refuted_before(conn: sqlite3.Connection, item_text: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM claim_costs WHERE item_text = ? LIMIT 1",
        (item_text,)).fetchone() is not None


def unpaid_refutations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, claim, provenance, resolver, settled_by FROM resolutions"
        " WHERE outcome='contradicted' AND cost_applied_at IS NULL"
        " ORDER BY settled_at").fetchall()


def apply_world_costs(conn: sqlite3.Connection, items: list) -> list[Cost]:
    """Charge every refutation the world has delivered since the last sleep.

    Mutates `items` in place — the same objects sleep is about to decay, merge
    and save, so a position taken under the floor is released by the ordinary
    path rather than by anything this module does. Returns what was charged.
    """
    charged: list[Cost] = []
    now = time.time()
    for row in unpaid_refutations(conn):
        episode_ids = _concern_episode_ids(conn, row["provenance"] or "")
        paid = [it for it in items
                if episode_ids and episode_ids & {str(e) for e in it.evidence}]

        if not paid:
            conn.execute(
                "UPDATE resolutions SET cost_applied_at=?, cost_note=?"
                " WHERE id=?",
                (now, "no position traced to this claim's concern", row["id"]))
            logger.info("claim %d was refuted and cost nothing: no position is"
                        " grounded in %s", row["id"], row["provenance"])
            continue

        for it in paid:
            repeat = _refuted_before(conn, it.text)
            cost = (CONFIDENCE_ON_REPEAT_CONTRADICT if repeat
                    else CONFIDENCE_ON_CONTRADICT)
            before = it.confidence
            it.confidence = round(max(0.0, before - cost), 3)
            # Disputed, not deleted: the release floor decides, exactly as it
            # does for a contradiction the being raised against itself.
            it.status = "disputed"
            # The refuting material is deliberately NOT added to the item's
            # evidence. Material that refutes a claim is not support for the
            # position that produced it — the same rule INV-031 already keeps.
            record = Cost(claim_id=row["id"], item_text=it.text, before=before,
                          after=it.confidence, repeat=repeat,
                          released=it.confidence < RELEASE_BELOW)
            conn.execute(
                "INSERT INTO claim_costs (ts, claim_id, item_text, section,"
                " confidence_before, confidence_after, repeat, released)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (now, row["id"], it.text, it.section, before, it.confidence,
                 int(repeat), int(record.released)))
            charged.append(record)
            logger.info("the world refuted a position%s: %.2f -> %.2f%s — %s",
                        " again" if repeat else "", before, it.confidence,
                        " (released)" if record.released else "", it.text[:70])

        conn.execute(
            "UPDATE resolutions SET cost_applied_at=?, cost_note=? WHERE id=?",
            (now, f"cost {len(paid)} position(s)", row["id"]))
    conn.commit()
    return charged
