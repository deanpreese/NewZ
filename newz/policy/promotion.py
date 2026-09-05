"""Admission and the deterministic assessor.

Two steps, kept apart. Admission decides whether one edge may count at all and
records why. Assessment derives a state from the live, admitted edges and the
independent bases beneath them. Neither step searches, fetches, defines a
threshold, or reads a clock: time arrives as an input.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from newz.domain.enums import (
    COUNTABLE_RELATIONS,
    LIVE_TASK_STATES,
    TERMINAL_COMPETENT_STATES,
    TERMINAL_INCOMPLETE_STATES,
    AdmissionPredicate,
    AssertionKind,
    AssessmentState,
    ClaimKind,
    EdgeRelation,
    EvidenceLane,
    RefusalReason,
    RiskTier,
    SourceRole,
    TaskState,
)
from newz.domain.records import (
    Assertion,
    Assessment,
    Basis,
    Claim,
    EdgeEvent,
    IndependenceClaim,
    PredicateAttestation,
    Task,
)
from newz.policy import lanes as lane_policy
from newz.policy.independence import count_independent_bases
from newz.policy.matrix import MATRIX
from newz.policy.risk import maximum
from newz.policy.rules import DIRECT_RECORD_ROLES, STRONG_PROVENANCE_ROLES
from newz.version import CODE_VERSION, POLICY_VERSION


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    admitted: bool
    reason: RefusalReason | None
    attestations: tuple[PredicateAttestation, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "reason": self.reason,
            "attestations": [a.as_record() for a in self.attestations],
        }


def _att(
    predicate: AdmissionPredicate, held: bool, **inputs: object
) -> PredicateAttestation:
    return PredicateAttestation(
        predicate=predicate,
        held=held,
        inputs=tuple(sorted((k, str(v)) for k, v in inputs.items())),
    )


def evaluate_edge(
    edge: EdgeEvent,
    claim: Claim,
    assertion: Assertion | None,
    basis: Basis | None,
) -> AdmissionResult:
    """Whether one edge may count, with an attestation per named predicate.

    Anything missing or corrupt fails closed and remains contextual material.
    Every predicate is evaluated, so the attestation set records the whole check
    and not merely the first thing that went wrong.
    """
    role: SourceRole = assertion.role if assertion is not None else edge.role
    kind: AssertionKind = assertion.kind if assertion is not None else edge.assertion_kind

    live = assertion is not None and assertion.live and edge.live
    spans = assertion.spans if assertion is not None else ()
    has_span = bool(spans) and all(s.artifact_id and s.segment_id for s in spans)
    verified = bool(spans) and all(s.verified for s in spans)
    permitted = MATRIX.permits(role, claim.kind, kind, edge.relation)
    resolved = basis is not None and basis.resolved
    risk_known = edge.risk is not None
    not_quarantined = edge.risk is not RiskTier.R4
    versioned = bool(edge.policy_version)

    attestations = (
        _att(AdmissionPredicate.ASSERTION_LIVE, live, edge_live=edge.live),
        _att(AdmissionPredicate.ARTIFACT_AND_SPAN_PRESENT, has_span, spans=len(spans)),
        _att(AdmissionPredicate.QUOTE_VERIFIED, verified, spans=len(spans)),
        _att(
            AdmissionPredicate.TUPLE_PERMITTED,
            permitted,
            role=role.value,
            claim_kind=claim.kind.value,
            assertion_kind=kind.value,
            relation=edge.relation.value,
        ),
        _att(AdmissionPredicate.BASIS_IDENTITY_RESOLVED, resolved, basis=edge.basis_id),
        _att(
            AdmissionPredicate.RISK_CLASSIFIED,
            risk_known and not_quarantined,
            risk=edge.risk.value if edge.risk else "missing",
        ),
        _att(AdmissionPredicate.POLICY_VERSION_RECORDED, versioned),
    )

    # Ordered so the refusal names the most fundamental failure, not the first
    # predicate in the tuple.
    if not live:
        reason = RefusalReason.ASSERTION_NOT_LIVE
    elif not has_span:
        reason = RefusalReason.MISSING_ARTIFACT_OR_SPAN
    elif not verified:
        reason = RefusalReason.UNVERIFIED_QUOTE
    elif not risk_known:
        reason = RefusalReason.MISSING_RISK_STATE
    elif not not_quarantined:
        reason = RefusalReason.QUARANTINED_R4
    elif not permitted:
        reason = MATRIX.lookup(role, claim.kind, kind, edge.relation).reason
    elif not resolved:
        reason = RefusalReason.UNRESOLVED_BASIS
    elif not versioned:
        reason = RefusalReason.MISSING_POLICY_VERSION
    else:
        return AdmissionResult(True, None, attestations)

    return AdmissionResult(False, reason, attestations)


@dataclass(frozen=True, slots=True)
class LaneStatus:
    lane: EvidenceLane
    settled_competent: bool
    blocked: bool
    state: TaskState | None
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceInput:
    claim: Claim
    edges: tuple[EdgeEvent, ...] = ()
    assertions: dict[str, Assertion] = field(default_factory=dict)
    bases: dict[str, Basis] = field(default_factory=dict)
    independence: tuple[IndependenceClaim, ...] = ()
    tasks: tuple[Task, ...] = ()
    #: Forecasts only. Time is an input so the derivation reproduces.
    horizon_reached: bool = False


def _absence_recorded(task: Task) -> bool:
    """`SPEC.md` 7.3 rule 8: absence counts only when the search is described."""
    if task.state is TaskState.SATISFIED:
        return True
    return all(
        (task.expected_record, task.repository, task.query, task.time_window, task.searched_scope)
    )


def lane_statuses(claim: Claim, tasks: Sequence[Task]) -> tuple[LaneStatus, ...]:
    """The status of every lane the claim's kind requires."""
    required = lane_policy.required(claim.kind)
    statuses: list[LaneStatus] = []
    for lane in sorted(required, key=lambda x: x.value):
        in_lane = [t for t in tasks if t.lane is lane]
        live = [t for t in in_lane if t.state in LIVE_TASK_STATES]
        competent = [t for t in in_lane if t.state in TERMINAL_COMPETENT_STATES]
        incomplete = [t for t in in_lane if t.state in TERMINAL_INCOMPLETE_STATES]

        if not in_lane:
            statuses.append(LaneStatus(lane, False, False, None, "no_task_created"))
            continue
        if live:
            state = sorted(live, key=lambda t: t.id)[0].state
            statuses.append(LaneStatus(lane, False, False, state, "still_open"))
            continue
        if competent:
            described = [t for t in competent if _absence_recorded(t)]
            if described:
                task = sorted(described, key=lambda t: t.id)[0]
                statuses.append(LaneStatus(lane, True, False, task.state, "searched_and_concluded"))
            else:
                task = sorted(competent, key=lambda t: t.id)[0]
                statuses.append(
                    LaneStatus(lane, False, False, task.state, "search_not_described")
                )
            continue
        task = sorted(incomplete, key=lambda t: t.id)[0]
        statuses.append(
            LaneStatus(lane, False, True, task.state, task.state_reason or "terminal_incomplete")
        )
    return tuple(statuses)


def _effective_risk(claim: Claim, edges: Sequence[EdgeEvent]) -> RiskTier:
    known = [e.risk for e in edges if e.risk is not None]
    if claim.risk is not None:
        return maximum(claim.risk, *known) if known else claim.risk
    if known:
        return maximum(*known)
    return RiskTier.R3


def _settles_alone(claim: Claim, edges: Sequence[EdgeEvent]) -> bool:
    """The single-record exception of `SPEC.md` section 7.3.

    A narrow attribution or document-existence claim is settled by the record
    that literally establishes it. So is any claim settled by a final
    adjudicative record within that adjudicator's declared scope — the exception
    survives at R2 and R3, and is the only route by which a false allegation
    about a living person reaches `refuted` under symmetrical thresholds.
    """
    if claim.kind in (ClaimKind.ATTRIBUTION, ClaimKind.DOCUMENT_EXISTENCE) and edges:
        return True
    return any(
        e.role is SourceRole.ADJUDICATOR and e.adjudicative_scope_covers_claim is True
        for e in edges
    )


def _meets_threshold(
    claim: Claim,
    edges: Sequence[EdgeEvent],
    groups: Sequence[tuple[str, ...]],
    risk: RiskTier,
) -> tuple[bool, str]:
    """The promotion threshold, read identically for support and refutation."""
    if not edges or not groups:
        return False, "no_countable_basis"
    if _settles_alone(claim, edges):
        return True, "single_record_exception"

    by_basis: dict[str, list[EdgeEvent]] = {}
    for edge in edges:
        by_basis.setdefault(edge.basis_id, []).append(edge)

    def group_roles(group: tuple[str, ...]) -> set[SourceRole]:
        return {e.role for b in group for e in by_basis.get(b, ())}

    strong = sum(1 for g in groups if group_roles(g) & STRONG_PROVENANCE_ROLES)
    direct = sum(1 for g in groups if group_roles(g) & DIRECT_RECORD_ROLES)

    if len(groups) < 2:
        return False, "one_independent_basis"

    if risk is RiskTier.R4:
        return False, "r4_never_promotes"
    if risk is RiskTier.R3:
        if direct >= 1:
            return True, "r3_direct_record_plus_independent_basis"
        return False, "r3_needs_a_direct_primary_or_adjudicative_basis"
    if risk is RiskTier.R2:
        if strong >= 2:
            return True, "r2_two_strong_provenance_bases"
        return False, "r2_needs_two_strong_provenance_bases"
    if strong >= 1:
        return True, "two_independent_bases_one_strong"
    return False, "needs_a_primary_empirical_or_adjudicative_basis"


def assess(inputs: EvidenceInput, policy_version: str = POLICY_VERSION) -> Assessment:
    """Derive the current state from live edges and independent bases."""
    claim = inputs.claim

    countable: dict[EdgeRelation, list[EdgeEvent]] = {
        EdgeRelation.SUPPORTS: [],
        EdgeRelation.CONTRADICTS: [],
    }
    countable_ids: list[str] = []
    for edge in sorted(inputs.edges, key=lambda e: e.id):
        if edge.relation not in COUNTABLE_RELATIONS:
            continue
        result = evaluate_edge(
            edge,
            claim,
            inputs.assertions.get(edge.assertion_id),
            inputs.bases.get(edge.basis_id),
        )
        if result.admitted:
            countable[edge.relation].append(edge)
            countable_ids.append(edge.id)

    supports = countable[EdgeRelation.SUPPORTS]
    contradicts = countable[EdgeRelation.CONTRADICTS]

    n_support, support_groups = count_independent_bases(
        [e.basis_id for e in supports], inputs.bases, inputs.independence
    )
    n_contra, contra_groups = count_independent_bases(
        [e.basis_id for e in contradicts], inputs.bases, inputs.independence
    )

    statuses = lane_statuses(claim, inputs.tasks)
    blocked = tuple(
        (s.lane, s.state, s.reason) for s in statuses if s.blocked and s.state is not None
    )

    def finish(state: AssessmentState, explanation: str) -> Assessment:
        return Assessment(
            claim_id=claim.id,
            state=state,
            supporting_bases=n_support,
            contradicting_bases=n_contra,
            policy_version=policy_version,
            code_version=CODE_VERSION,
            explanation=explanation,
            blocked_lanes=blocked,
            countable_edge_ids=tuple(countable_ids),
        )

    if claim.withdrawn:
        return finish(AssessmentState.WITHDRAWN, "the proposition is no longer maintained")

    if claim.kind is ClaimKind.NORMATIVE_PROPOSITION:
        return finish(
            AssessmentState.REPORTED,
            "a normative proposition admits no evidence edge and does not promote",
        )

    if claim.kind is ClaimKind.FORECAST and not inputs.horizon_reached:
        return finish(
            AssessmentState.REPORTED,
            "a forecast holds at reported until its resolution horizon, whatever edges accumulate",
        )

    if n_support and n_contra:
        return finish(
            AssessmentState.CONTESTED,
            f"countable evidence in both directions: {n_support} supporting and "
            f"{n_contra} contradicting independent bases, never netted",
        )

    risk = _effective_risk(claim, [*supports, *contradicts])

    if n_support:
        met, why = _meets_threshold(claim, supports, support_groups, risk)
        if met:
            return finish(AssessmentState.SUPPORTED, why)
        return finish(AssessmentState.PROVISIONAL_SUPPORT, why)

    if n_contra:
        met, why = _meets_threshold(claim, contradicts, contra_groups, risk)
        if met:
            return finish(AssessmentState.REFUTED, why)
        return finish(AssessmentState.PROVISIONAL_CONTRADICTION, why)

    if blocked:
        names = ", ".join(f"{lane.value}:{state.value}" for lane, state, _ in blocked)
        return finish(
            AssessmentState.REPORTED,
            f"a required lane did not search ({names}); absence is evidence only "
            "from a lane that actually looked",
        )

    if statuses and all(s.settled_competent for s in statuses):
        return finish(
            AssessmentState.INDETERMINATE,
            "every required evidence lane searched competently and produced no "
            "countable edge in either direction",
        )

    return finish(AssessmentState.REPORTED, "attributed, with evidence lanes still open")
