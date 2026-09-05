"""Small builders for tests that are about one rule rather than one situation.

Situations belong in the controlled case files. These exist so a test about, say,
risk monotonicity does not have to describe a whole investigation to get there.
"""

from __future__ import annotations

from newz.domain.enums import (
    AssertionKind,
    ClaimKind,
    EdgeRelation,
    EvidenceLane,
    IndependenceJustification,
    RiskTier,
    SourceRole,
    TaskState,
)
from newz.domain.records import (
    Assertion,
    Basis,
    Claim,
    EdgeEvent,
    IndependenceClaim,
    Span,
    Task,
)
from newz.policy.promotion import EvidenceInput


def span(quote: str = "a quotation that exists in the artifact", verified: bool = True) -> Span:
    return Span(
        artifact_id="artifact:a1",
        segment_id="p1",
        start=0,
        end=len(quote),
        quote=quote,
        locator="paragraph 1",
        verified=verified,
    )


def assertion(
    ident: str,
    kind: AssertionKind = AssertionKind.MEASUREMENT,
    role: SourceRole = SourceRole.EMPIRICAL_STUDY,
    live: bool = True,
    spans: tuple[Span, ...] | None = None,
) -> Assertion:
    return Assertion(
        id=ident,
        kind=kind,
        spans=(span(),) if spans is None else spans,
        source_revision_id=f"srcrev:{ident.split(':')[-1]}",
        role=role,
        live=live,
    )


def basis(ident: str, resolved: bool = True, group: str | None = None) -> Basis:
    return Basis(
        id=ident,
        origin_kind="dataset",
        origin_identifier=f"origin:{ident.split(':')[-1]}",
        resolved=resolved,
        independence_group=group,
    )


def claim(
    kind: ClaimKind = ClaimKind.MEASUREMENT_OR_ASSOCIATION,
    risk: RiskTier | None = RiskTier.R1,
    ident: str = "claim:c1",
) -> Claim:
    return Claim(id=ident, kind=kind, wording="a proposition under investigation", risk=risk)


def edge(
    ident: str,
    assertion_record: Assertion,
    claim_record: Claim,
    relation: EdgeRelation = EdgeRelation.SUPPORTS,
    basis_id: str = "basis:b1",
    risk: RiskTier | None = RiskTier.R1,
    policy_version: str = "1.0.0",
    live: bool = True,
    scope_covers: bool | None = None,
) -> EdgeEvent:
    return EdgeEvent(
        id=ident,
        assertion_id=assertion_record.id,
        claim_id=claim_record.id,
        relation=relation,
        basis_id=basis_id,
        role=assertion_record.role,
        assertion_kind=assertion_record.kind,
        risk=risk,
        policy_version=policy_version,
        admitted=True,
        live=live,
        adjudicative_scope_covers_claim=scope_covers,
    )


def independence(
    a: str,
    b: str,
    justification: IndependenceJustification = (
        IndependenceJustification.DISTINCT_INSTRUMENT_OR_DATASET
    ),
    evidence: str = "different accession identifiers",
    actor: str | None = None,
    reason: str | None = None,
) -> IndependenceClaim:
    return IndependenceClaim(
        basis_a=a,
        basis_b=b,
        justification=justification,
        evidence=evidence,
        operator_actor=actor,
        operator_reason=reason,
    )


def task(
    ident: str,
    lane: EvidenceLane,
    state: TaskState,
    described: bool = True,
    state_reason: str = "",
) -> Task:
    described_fields = {
        "expected_record": "the record sought",
        "repository": "the competent repository",
        "query": "the query issued",
        "time_window": "2026-01-01/2026-04-01",
        "searched_scope": "the scope searched",
    }
    return Task(
        id=ident,
        claim_id="claim:c1",
        lane=lane,
        state=state,
        owner="worker:evidence",
        reason="test",
        due="2026-04-01T00:00:00Z",
        state_reason=state_reason,
        **(described_fields if described else {}),
    )


def inputs(claim_record: Claim, *edges: EdgeEvent, **kwargs) -> EvidenceInput:
    assertions = kwargs.pop("assertions", {})
    bases = kwargs.pop("bases", {})
    return EvidenceInput(
        claim=claim_record,
        edges=tuple(edges),
        assertions=assertions,
        bases=bases,
        independence=tuple(kwargs.pop("independence", ())),
        tasks=tuple(kwargs.pop("tasks", ())),
        horizon_reached=kwargs.pop("horizon_reached", False),
    )
