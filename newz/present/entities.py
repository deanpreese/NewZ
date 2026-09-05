"""The entity card: what the record holds about one named party.

`SPEC.md` section 10.1, and the whole section is one idea — **a person is an
address in the graph, never a dossier in it.** So this module computes and
returns; it never stores. There is no `entity_cards` table, and the entity
record itself holds only what disambiguation requires, so no dossier exists at
rest to leak, to compel, or to outlive the sources it was drawn from.

The failure specific to this projection is aggregation: accurate attribution,
item by item, adding up to an implication nothing supports. Three rules answer
it. Basis independence is shown across the whole set, so ten claims resting on
one origin display as one basis rather than as a pattern. Every claim carries
its current state and its material counterevidence, so no bare allegation
appears. And when nothing shown has been established, the card says so first,
because a list of unestablished reports is the form in which this view most
easily misleads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from newz.domain.enums import RISK_ORDER, AssessmentState, EdgeRelation, RiskTier
from newz.evidence.assess import current_assessment
from newz.evidence.bases import load_bases, load_independence
from newz.evidence.edges import load_edges
from newz.policy.independence import count_independent_bases
from newz.store.db import Store

ESTABLISHED = frozenset(
    {AssessmentState.SUPPORTED, AssessmentState.REFUTED, AssessmentState.CONTESTED}
)


@dataclass(frozen=True, slots=True)
class EntityClaim:
    claim_id: str
    wording: str
    state: str
    risk: str
    counterevidence: tuple[str, ...]
    bases: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "wording": self.wording,
            "state": self.state,
            "risk": self.risk,
            "counterevidence": list(self.counterevidence),
            "bases": list(self.bases),
        }


@dataclass(frozen=True, slots=True)
class EntityCard:
    entity_id: str
    name: str
    kind: str
    disambiguation: str
    claims: tuple[EntityClaim, ...]
    #: Across the whole set, not per claim. This is the aggregation control.
    independent_bases: int
    distinct_basis_citations: int
    effective_risk: str
    nothing_established: bool
    notice: str
    publishable: bool
    refusal: str = ""
    access_logged: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "kind": self.kind,
            "disambiguation": self.disambiguation,
            "claims": [claim.as_record() for claim in self.claims],
            "independent_bases": self.independent_bases,
            "distinct_basis_citations": self.distinct_basis_citations,
            "effective_risk": self.effective_risk,
            "nothing_established": self.nothing_established,
            "notice": self.notice,
            "publishable": self.publishable,
            "refusal": self.refusal,
        }


def _claims_naming(store: Store, entity_id: str) -> tuple[str, ...]:
    """Claims whose edges rest on an assertion that named this entity."""
    return tuple(
        row["claim_id"]
        for row in store.query(
            "SELECT DISTINCT e.claim_id FROM assertion_entities ae "
            "JOIN edge_events e ON e.assertion_id = ae.assertion_id "
            "WHERE ae.entity_id = ? AND e.live = 1 ORDER BY e.claim_id",
            entity_id,
        )
    )


def entity_card(
    store: Store,
    entity_id: str,
    *,
    actor: str = "",
    reason: str = "",
    living_person: bool = False,
) -> EntityCard:
    """Compute the card. Nothing is stored except, where required, the access.

    An access to a card naming a living person at R2 or above is logged with
    actor, time and reason. That log is the only thing this function writes, and
    it records the reading rather than the person.
    """
    entity = store.one("SELECT * FROM entities WHERE id = ?", entity_id)
    if entity is None:
        raise KeyError(entity_id)

    bases = load_bases(store)
    independence = load_independence(store)

    entries: list[EntityClaim] = []
    all_basis_ids: list[str] = []
    risk = RiskTier.R0

    for claim_id in _claims_naming(store, entity_id):
        claim = store.one("SELECT * FROM claims WHERE id = ?", claim_id)
        assessment = current_assessment(store, claim_id)
        if claim is None or assessment is None:
            # A claim with no assessment has no state to show, and showing a
            # bare allegation is the thing this card may not do.
            continue
        edges = load_edges(store, claim_id)
        counterevidence = tuple(
            sorted(
                {
                    edge.id
                    for edge in edges
                    if edge.relation is EdgeRelation.CONTRADICTS
                }
            )
        )
        claim_bases = tuple(sorted({edge.basis_id for edge in edges}))
        all_basis_ids.extend(claim_bases)
        claim_risk = RiskTier(claim["risk"]) if claim["risk"] else RiskTier.R3
        risk = max(risk, claim_risk, key=RISK_ORDER.index)
        entries.append(
            EntityClaim(
                claim_id=claim_id,
                wording=claim["wording"],
                state=assessment.state.value,
                risk=claim_risk.value,
                counterevidence=counterevidence,
                bases=claim_bases,
            )
        )

    independent, _ = count_independent_bases(all_basis_ids, bases, independence)
    distinct = len(set(all_basis_ids))
    nothing_established = not any(
        AssessmentState(entry.state) in ESTABLISHED for entry in entries
    )

    notice = ""
    if not entries:
        notice = "The record holds no assessed claim naming this entity."
    elif nothing_established:
        notice = (
            "Nothing shown here has been established. Every claim below is an "
            "unestablished report, and a list of them is not a pattern."
        )
    elif independent < distinct:
        notice = (
            f"The {distinct} citations below rest on {independent} independent "
            f"basis{'' if independent == 1 else 'es'}."
        )

    publishable = risk is not RiskTier.R3 and risk is not RiskTier.R4
    refusal = "" if publishable else f"an entity card at {risk.value} is not published"

    logged = False
    if living_person and RISK_ORDER.index(risk) >= RISK_ORDER.index(RiskTier.R2):
        if not actor or not reason:
            raise ValueError(
                "an entity card naming a living person at R2 or above logs actor and reason"
            )
        with store.write() as connection:
            connection.execute(
                "INSERT INTO entity_card_access (id, entity_id, actor, reason, risk, "
                "claims_shown, accessed_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    f"access:{entity_id.split(':')[-1]}-"
                    + str(
                        store.one(
                            "SELECT COUNT(*) AS n FROM entity_card_access WHERE entity_id = ?",
                            entity_id,
                        )["n"]
                    ),
                    entity_id,
                    actor,
                    reason,
                    risk.value,
                    len(entries),
                ),
            )
        logged = True

    return EntityCard(
        entity_id=entity_id,
        name=entity["name"],
        kind=entity["kind"],
        disambiguation=entity["disambiguation"],
        claims=tuple(entries),
        independent_bases=independent,
        distinct_basis_citations=distinct,
        effective_risk=risk.value,
        nothing_established=nothing_established,
        notice=notice,
        publishable=publishable,
        refusal=refusal,
        access_logged=logged,
    )
