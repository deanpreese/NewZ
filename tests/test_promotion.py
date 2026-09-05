"""The assessor: what states are reachable, and from what.

The load-bearing test in this file is the one about lanes. `indeterminate` is
the result that most resembles a finding while being an absence, so what it is
allowed to rest on is checked exhaustively over the task states.
"""

from __future__ import annotations

import pytest

from newz.domain.enums import (
    LIVE_TASK_STATES,
    TERMINAL_COMPETENT_STATES,
    TERMINAL_INCOMPLETE_STATES,
    AssertionKind,
    AssessmentState,
    ClaimKind,
    EdgeRelation,
    EvidenceLane,
    RiskTier,
    SourceRole,
    TaskState,
)
from newz.policy import lanes
from newz.policy.promotion import assess, evaluate_edge
from tests import builders as b


def _document_existence_claim_with_lane(state: TaskState, described: bool = True):
    """One required lane (`primary_record`), so the lane rule is isolated."""
    claim = b.claim(kind=ClaimKind.DOCUMENT_EXISTENCE, risk=RiskTier.R1)
    return b.inputs(
        claim,
        tasks=[b.task("task:t1", EvidenceLane.PRIMARY_RECORD, state, described=described)],
    )


@pytest.mark.parametrize("state", sorted(TERMINAL_COMPETENT_STATES))
def test_indeterminate_rests_on_terminal_competent_state_alone(state):
    result = assess(_document_existence_claim_with_lane(state))
    assert result.state is AssessmentState.INDETERMINATE


@pytest.mark.parametrize("state", sorted(TERMINAL_INCOMPLETE_STATES))
def test_a_lane_that_did_not_search_never_produces_indeterminate(state):
    """Investigating and finding nothing is a different fact from never investigating."""
    result = assess(_document_existence_claim_with_lane(state))
    assert result.state is AssessmentState.REPORTED
    assert result.blocked_lanes
    lane, blocked_state, _ = result.blocked_lanes[0]
    assert lane is EvidenceLane.PRIMARY_RECORD
    assert blocked_state is state


@pytest.mark.parametrize("state", sorted(LIVE_TASK_STATES))
def test_an_open_lane_produces_neither(state):
    result = assess(_document_existence_claim_with_lane(state))
    assert result.state is AssessmentState.REPORTED
    assert not result.blocked_lanes


def test_absence_counts_only_when_the_search_is_described():
    """SPEC 7.3 rule 8: the expected record, repository, query, window, and scope."""
    described = assess(_document_existence_claim_with_lane(TaskState.EXHAUSTED, described=True))
    undescribed = assess(
        _document_existence_claim_with_lane(TaskState.EXHAUSTED, described=False)
    )
    assert described.state is AssessmentState.INDETERMINATE
    assert undescribed.state is AssessmentState.REPORTED


def test_a_lane_with_no_task_is_not_a_lane_that_looked():
    claim = b.claim(kind=ClaimKind.DOCUMENT_EXISTENCE)
    assert assess(b.inputs(claim)).state is AssessmentState.REPORTED


def test_every_required_lane_must_conclude():
    claim = b.claim(kind=ClaimKind.EVENT_OR_OBSERVATION)
    required = sorted(lanes.required(ClaimKind.EVENT_OR_OBSERVATION), key=lambda x: x.value)
    tasks = [
        b.task(f"task:t{i}", lane, TaskState.EXHAUSTED) for i, lane in enumerate(required[:-1])
    ]
    assert assess(b.inputs(claim, tasks=tasks)).state is AssessmentState.REPORTED
    tasks.append(b.task("task:tlast", required[-1], TaskState.EXHAUSTED))
    assert assess(b.inputs(claim, tasks=tasks)).state is AssessmentState.INDETERMINATE


def test_a_normative_proposition_refuses_evidence_edges_and_stays_reported():
    claim = b.claim(kind=ClaimKind.NORMATIVE_PROPOSITION)
    a1 = b.assertion("assertion:a1")
    edge = b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1")
    result = evaluate_edge(edge, claim, a1, b.basis("basis:b1"))
    assert not result.admitted
    assert result.reason.value == "normative_admits_no_evidence"
    assessment = assess(
        b.inputs(claim, edge, assertions={a1.id: a1}, bases={"basis:b1": b.basis("basis:b1")})
    )
    assert assessment.state is AssessmentState.REPORTED
    assert assessment.supporting_bases == 0


def test_a_forecast_refuses_promotion_before_its_horizon():
    claim = b.claim(kind=ClaimKind.FORECAST, risk=RiskTier.R1)
    a1 = b.assertion("assertion:a1", AssertionKind.DOCUMENTED_EVENT, SourceRole.PRIMARY_RECORD)
    a2 = b.assertion("assertion:a2", AssertionKind.MEASUREMENT, SourceRole.EMPIRICAL_STUDY)
    payload = dict(
        assertions={a.id: a for a in (a1, a2)},
        bases={"basis:b1": b.basis("basis:b1"), "basis:b2": b.basis("basis:b2")},
        independence=[b.independence("basis:b1", "basis:b2")],
    )
    edges = (
        b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1"),
        b.edge("edge:e2", a2, claim, EdgeRelation.SUPPORTS, "basis:b2"),
    )
    before = assess(b.inputs(claim, *edges, horizon_reached=False, **payload))
    after = assess(b.inputs(claim, *edges, horizon_reached=True, **payload))
    assert before.state is AssessmentState.REPORTED
    assert before.supporting_bases == 2
    assert after.state is AssessmentState.SUPPORTED


def test_opposing_evidence_is_contested_and_never_netted():
    claim = b.claim()
    supports = [b.assertion(f"assertion:s{i}") for i in range(3)]
    against = b.assertion("assertion:c1")
    edges = [
        b.edge(f"edge:s{i}", a, claim, EdgeRelation.SUPPORTS, f"basis:s{i}")
        for i, a in enumerate(supports)
    ]
    edges.append(b.edge("edge:c1", against, claim, EdgeRelation.CONTRADICTS, "basis:c1"))
    bases = {f"basis:s{i}": b.basis(f"basis:s{i}") for i in range(3)}
    bases["basis:c1"] = b.basis("basis:c1")
    result = assess(
        b.inputs(
            claim,
            *edges,
            assertions={a.id: a for a in [*supports, against]},
            bases=bases,
            independence=[
                b.independence("basis:s0", "basis:s1"),
                b.independence("basis:s0", "basis:s2"),
                b.independence("basis:s1", "basis:s2"),
            ],
        )
    )
    assert result.state is AssessmentState.CONTESTED
    assert (result.supporting_bases, result.contradicting_bases) == (3, 1)


def test_a_withdrawn_claim_keeps_its_history_and_stops_promoting():
    claim = b.claim().__class__(
        id="claim:c1",
        kind=ClaimKind.MEASUREMENT_OR_ASSOCIATION,
        wording="withdrawn",
        risk=RiskTier.R1,
        withdrawn=True,
    )
    assert assess(b.inputs(claim)).state is AssessmentState.WITHDRAWN


def test_an_edge_fails_closed_on_every_missing_predicate():
    claim = b.claim()
    good = b.assertion("assertion:a1")
    basis = b.basis("basis:b1")
    cases = {
        "assertion_not_live": (b.assertion("assertion:a1", live=False), basis, {}),
        "missing_artifact_or_span": (
            b.assertion("assertion:a1", spans=()),
            basis,
            {},
        ),
        "unverified_quote": (
            b.assertion("assertion:a1", spans=(b.span(verified=False),)),
            basis,
            {},
        ),
        "unresolved_basis": (good, b.basis("basis:b1", resolved=False), {}),
        "missing_risk_state": (good, basis, {"risk": None}),
        "quarantined_r4": (good, basis, {"risk": RiskTier.R4}),
        "missing_policy_version": (good, basis, {"policy_version": ""}),
    }
    for expected, (assertion_record, basis_record, overrides) in cases.items():
        edge = b.edge("edge:e1", assertion_record, claim, **overrides)
        result = evaluate_edge(edge, claim, assertion_record, basis_record)
        assert not result.admitted, expected
        assert result.reason.value == expected
        assert len(result.attestations) == 7


def test_an_admitted_edge_attests_every_predicate_held():
    claim = b.claim()
    a1 = b.assertion("assertion:a1")
    result = evaluate_edge(b.edge("edge:e1", a1, claim), claim, a1, b.basis("basis:b1"))
    assert result.admitted
    assert all(att.held for att in result.attestations)
