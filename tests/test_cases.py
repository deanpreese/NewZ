"""The controlled cases.

Each case file states a situation and the state it must reach. These are the
cases `PLAN.md` Phase 0 names, and they are the ones a reader should read first:
the rest of the suite proves properties, and these prove that the properties add
up to the right answer in the situations the specification cares about.
"""

from __future__ import annotations

import pytest

from newz.domain.enums import AssessmentState, RiskTier
from newz.policy.promotion import assess, evaluate_edge
from tests.casefiles import build, case_paths, load_raw

CASES = case_paths()
IDS = [p.stem for p in CASES]


def test_every_case_the_plan_names_exists():
    """PLAN.md Phase 0 item 10 lists twelve situations; the forecast and the
    normative proposition are one line there and two files here."""
    assert len(CASES) == 13
    required = {
        "narrow-attributed",
        "two-independent",
        "support-plus-contradiction",
        "absence-from-a-competent",
        "copied-story",
        "patent-misused",
        "complaint-misused",
        "refuted-by-adjudication",
        "unknown-independence",
        "normative-proposition",
        "unresolved-forecast",
        "r3-allegation",
        "r4-operational",
    }
    names = " ".join(IDS)
    for fragment in required:
        assert fragment in names, fragment


@pytest.mark.parametrize("path", CASES, ids=IDS)
def test_case_reaches_its_stated_state(path):
    case = load_raw(path)
    expect = case["expect"]
    result = assess(build(case))

    assert result.state is AssessmentState(expect["state"]), result.explanation
    assert result.supporting_bases == expect["supporting_bases"]
    assert result.contradicting_bases == expect["contradicting_bases"]

    if "explanation_contains" in expect:
        assert expect["explanation_contains"] in result.explanation

    if "countable_edges" in expect:
        assert list(result.countable_edge_ids) == expect["countable_edges"]

    if "blocked_lanes" in expect:
        assert len(result.blocked_lanes) == expect["blocked_lanes"]


@pytest.mark.parametrize("path", CASES, ids=IDS)
def test_case_refuses_the_edges_it_says_it_refuses(path):
    case = load_raw(path)
    refusals = case["expect"].get("refusals", {})
    if not refusals:
        return
    inputs = build(case)
    by_id = {e.id: e for e in inputs.edges}
    for edge_id, reason in refusals.items():
        edge = by_id[edge_id]
        result = evaluate_edge(
            edge,
            inputs.claim,
            inputs.assertions.get(edge.assertion_id),
            inputs.bases.get(edge.basis_id),
        )
        assert not result.admitted, edge_id
        assert result.reason.value == reason, edge_id
        assert edge_id not in result_ids(inputs)


def result_ids(inputs):
    return assess(inputs).countable_edge_ids


@pytest.mark.parametrize("path", CASES, ids=IDS)
def test_case_carries_its_effective_risk(path):
    case = load_raw(path)
    expected = case["expect"].get("effective_risk")
    if expected is None:
        return
    assert build(case).claim.risk is RiskTier(expected)


@pytest.mark.parametrize("path", CASES, ids=IDS)
def test_case_states_what_it_is_for(path):
    """A case file without a specification reference is a test, not a case."""
    case = load_raw(path)
    assert case["title"]
    assert case["spec_ref"]


def test_the_forecast_case_settles_when_its_horizon_arrives():
    case = load_raw(next(p for p in CASES if "forecast" in p.stem))
    at_horizon = case["at_horizon"]
    result = assess(build(case, horizon_reached=True))
    assert result.state is AssessmentState(at_horizon["state"])
    assert result.supporting_bases == at_horizon["supporting_bases"]
