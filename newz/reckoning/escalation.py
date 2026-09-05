"""Escalation: the attempt to get a permission by another route.

`SPEC.md` section 8. An attempt to lower an effective risk, widen an
authorisation envelope, edit an audit record, or bypass a refusal is detected
and recorded — **including indirect routes**: re-deriving a refused output,
delegating the work to a subprocess, or shaping an operator request toward the
permission the system wants.

The indirect ones are the point. A system that only detected "tried to set risk
lower" would catch the one attempt nobody makes twice. The detectors here look
for the shape of the thing rather than the wording of it.

Escalation events are failures under section 13, so each requires a linked
change, and one without a change is reported as open.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.store.db import Store

ROUTES = (
    "risk_lowering",
    "refusal_re_derivation",
    "clearance_inference",
    "audit_edit",
    "envelope_widening",
    "request_shaping",
)


@dataclass(frozen=True, slots=True)
class Escalation:
    id: str
    route: str
    attempted: str
    detected_by: str
    linked_change: str = ""

    @property
    def open(self) -> bool:
        return not self.linked_change

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "route": self.route,
            "attempted": self.attempted,
            "detected_by": self.detected_by,
            "linked_change": self.linked_change,
            "open": self.open,
        }


def record_escalation(
    store: Store, *, escalation_id: str, route: str, attempted: str, detected_by: str
) -> Escalation:
    if route not in ROUTES:
        raise ValueError(f"route must be one of {list(ROUTES)}")
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO escalation_events (id, route, attempted, detected_by, "
            "raised_to_operator, linked_change, at) VALUES (?, ?, ?, ?, 1, '', datetime('now'))",
            (escalation_id, route, attempted, detected_by),
        )
    return Escalation(escalation_id, route, attempted, detected_by)


def link_change(store: Store, escalation_id: str, change: str) -> None:
    """Every failure carries a change that cites it. Until then it stays open."""
    if not change.strip():
        raise ValueError("linking a change records what changed")
    with store.write() as connection:
        connection.execute(
            "UPDATE escalation_events SET linked_change = ? WHERE id = ?",
            (change, escalation_id),
        )


def open_escalations(store: Store) -> tuple[Escalation, ...]:
    return tuple(
        Escalation(
            id=row["id"],
            route=row["route"],
            attempted=row["attempted"],
            detected_by=row["detected_by"],
            linked_change=row["linked_change"],
        )
        for row in store.query(
            "SELECT * FROM escalation_events WHERE linked_change = '' ORDER BY id"
        )
    )


def detect_escalation(store: Store, id_prefix: str = "escalation") -> tuple[Escalation, ...]:
    """Sweep for the shapes an escalation takes, direct and indirect."""
    found: list[Escalation] = []

    # Indirect: the same content, refused once, offered again under a new
    # revision id. Re-deriving a refused output is the most natural way to
    # bypass a refusal without ever asking to.
    for row in store.query(
        "SELECT c2.id AS later, c1.id AS earlier, c2.content_hash AS hash "
        "FROM clearances c1 JOIN clearances c2 ON c2.content_hash = c1.content_hash "
        "WHERE c1.granted = 0 AND c2.granted = 1 AND c2.rowid > c1.rowid ORDER BY c2.id"
    ):
        found.append(
            record_escalation(
                store,
                escalation_id=f"{id_prefix}:rederive-{row['hash'][:12]}",
                route="refusal_re_derivation",
                attempted=(
                    f"content refused as {row['earlier']} cleared as {row['later']} "
                    "without changing"
                ),
                detected_by="clearance content-hash sweep",
            )
        )

    # Direct: a risk reclassification downward with no operator on the action.
    for row in store.query(
        "SELECT * FROM audit_events WHERE action = 'reclassify_claim_risk' "
        "AND channel = 'system' ORDER BY id"
    ):
        if row["preimage"] > row["result"]:  # R3 -> R1 sorts that way
            found.append(
                record_escalation(
                    store,
                    escalation_id=f"{id_prefix}:risk-{row['id'].split(':')[-1]}",
                    route="risk_lowering",
                    attempted=f"{row['target']} lowered {row['preimage']} to {row['result']}",
                    detected_by="audit sweep of automated reclassifications",
                )
            )

    # Indirect: a card published at a reach the operator never enabled.
    for row in store.query(
        "SELECT p.id, p.audience FROM publications p WHERE p.audience != 'local' ORDER BY p.id"
    ):
        enabled = store.one(
            "SELECT enabled FROM reach_settings WHERE audience = ?", row["audience"]
        )
        if enabled is None or not enabled["enabled"]:
            found.append(
                record_escalation(
                    store,
                    escalation_id=f"{id_prefix}:reach-{row['id'].split(':')[-1]}",
                    route="envelope_widening",
                    attempted=f"published to {row['audience']}, which is not enabled",
                    detected_by="reach sweep",
                )
            )

    return tuple(found)
