"""The evidence packet: what an investigator needs to decide what to do next.

Deliberately not a claim card. A card is for a reader and shows what the record
establishes; a packet is for the system and shows where the record is thin — the
strongest thing on each side, how many distinct origins are actually under them,
which lanes have not reported, and what the risk tier makes necessary.

The one thing it must not do is average. `SPEC.md` 7.3 rule 9 keeps opposing
evidence as opposing evidence, so the packet shows both sides at full strength
and no net anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.domain.enums import EdgeRelation, EvidenceLane, RiskTier
from newz.evidence.assess import current_assessment, evidence_input
from newz.policy import lanes as lane_policy
from newz.policy.independence import count_independent_bases
from newz.policy.promotion import lane_statuses
from newz.store.db import Store


@dataclass(frozen=True, slots=True)
class Side:
    edges: int
    independent_bases: int
    strongest_edge_id: str = ""
    strongest_quote: str = ""
    strongest_role: str = ""
    strongest_locator: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "edges": self.edges,
            "independent_bases": self.independent_bases,
            "strongest_edge_id": self.strongest_edge_id,
            "strongest_quote": self.strongest_quote,
            "strongest_role": self.strongest_role,
            "strongest_locator": self.strongest_locator,
        }


@dataclass(frozen=True, slots=True)
class EvidencePacket:
    claim_id: str
    state: str
    risk: str
    support: Side
    contradiction: Side
    missing_lanes: tuple[str, ...]
    blocked_lanes: tuple[tuple[str, str, str], ...]
    unknown_independence: bool
    what_would_change_it: str

    def as_record(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "state": self.state,
            "risk": self.risk,
            "support": self.support.as_record(),
            "contradiction": self.contradiction.as_record(),
            "missing_lanes": list(self.missing_lanes),
            "blocked_lanes": [list(entry) for entry in self.blocked_lanes],
            "unknown_independence": self.unknown_independence,
            "what_would_change_it": self.what_would_change_it,
        }


#: The roles whose evidence is strongest under the thresholds, in order. Used
#: only to pick what to show first; it grants nothing.
_ROLE_RANK = {
    "adjudicator": 5,
    "primary_record": 4,
    "empirical_study": 3,
    "skeptical_investigation": 2,
    "firsthand_witness": 1,
    "claimant": 0,
}


def _side(store: Store, inputs, relation: EdgeRelation) -> Side:
    edges = [edge for edge in inputs.edges if edge.relation is relation]
    admitted = [
        edge
        for edge in edges
        if edge.id in {e.id for e in inputs.edges}
    ]
    countable_ids = set(
        (current_assessment(store, inputs.claim.id).countable_edge_ids)
        if current_assessment(store, inputs.claim.id)
        else []
    )
    counted = [edge for edge in admitted if edge.id in countable_ids] or admitted
    count, _ = count_independent_bases(
        [edge.basis_id for edge in counted], inputs.bases, inputs.independence
    )
    if not counted:
        return Side(edges=0, independent_bases=0)

    strongest = max(counted, key=lambda edge: (_ROLE_RANK.get(edge.role.value, 0), edge.id))
    assertion = inputs.assertions.get(strongest.assertion_id)
    span = assertion.spans[0] if assertion and assertion.spans else None
    return Side(
        edges=len(counted),
        independent_bases=count,
        strongest_edge_id=strongest.id,
        strongest_quote=span.quote if span else "",
        strongest_role=strongest.role.value,
        strongest_locator=span.locator if span else "",
    )


def evidence_packet(store: Store, claim_id: str) -> EvidencePacket:
    inputs = evidence_input(store, claim_id)
    assessment = current_assessment(store, claim_id)
    statuses = lane_statuses(inputs.claim, inputs.tasks)

    required = lane_policy.required(inputs.claim.kind)
    reported = {status.lane for status in statuses if status.settled_competent}
    missing = tuple(
        sorted(lane.value for lane in required if lane not in reported)
    )
    blocked = tuple(
        (status.lane.value, status.state.value if status.state else "", status.reason)
        for status in statuses
        if status.blocked
    )

    support = _side(store, inputs, EdgeRelation.SUPPORTS)
    contradiction = _side(store, inputs, EdgeRelation.CONTRADICTS)

    # The unknown-independence indicator SPEC 13 asks the pilot to report: a
    # claim held below promotion by nothing but uncounted distinctness.
    held_by_independence = (
        support.edges > support.independent_bases
        or contradiction.edges > contradiction.independent_bases
    )

    risk = (inputs.claim.risk or RiskTier.R3).value
    return EvidencePacket(
        claim_id=claim_id,
        state=assessment.state.value if assessment else "unassessed",
        risk=risk,
        support=support,
        contradiction=contradiction,
        missing_lanes=missing,
        blocked_lanes=blocked,
        unknown_independence=held_by_independence,
        what_would_change_it=_what_would_change_it(
            inputs.claim.kind, support, contradiction, missing, risk
        ),
    )


def _what_would_change_it(kind, support: Side, contradiction: Side, missing, risk: str) -> str:
    """The condition on the claim card, computed rather than written by a model."""
    if missing:
        return f"an answer from the {missing[0]} lane"
    if support.independent_bases and contradiction.independent_bases:
        return "a basis that resolves the disagreement rather than adding to it"
    if support.edges and support.edges > support.independent_bases:
        return "a justification that two of the supporting bases are distinct"
    if support.independent_bases == 1:
        return "a second independent basis, at least one of them a primary, empirical or adjudicative record"
    if not support.edges and not contradiction.edges:
        return "any countable evidence in either direction"
    return "a contradicting basis, held to the same standard"


def lane_gaps(store: Store, claim_id: str) -> tuple[EvidenceLane, ...]:
    """Required lanes with nothing to show for them yet."""
    packet = evidence_packet(store, claim_id)
    return tuple(EvidenceLane(lane) for lane in packet.missing_lanes)
