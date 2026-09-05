"""A stored assessment never outlives the policy that produced it."""

from __future__ import annotations

from newz.domain.enums import AssessmentState
from newz.domain.records import Assessment, Presentation
from newz.policy.bundle import BUNDLE
from newz.policy.reassessment import claims_requiring_reassessment, invalidate, stale_assessments
from newz.version import CODE_VERSION, POLICY_VERSION


def _assessment(claim_id: str, policy_version: str) -> Assessment:
    return Assessment(
        claim_id=claim_id,
        state=AssessmentState.SUPPORTED,
        supporting_bases=2,
        contradicting_bases=0,
        policy_version=policy_version,
        code_version=CODE_VERSION,
        explanation="two_independent_bases_one_strong",
    )


def test_every_assessment_records_the_policy_version_it_was_derived_under():
    assert _assessment("claim:c1", POLICY_VERSION).policy_version == BUNDLE.version


def test_a_policy_change_reassesses_exactly_the_claims_derived_under_the_old_version():
    assessments = [
        _assessment("claim:c1", "1.0.0"),
        _assessment("claim:c2", "0.9.0"),
        _assessment("claim:c3", "0.9.0"),
    ]
    assert claims_requiring_reassessment(assessments, "1.0.0") == ("claim:c2", "claim:c3")
    assert stale_assessments(assessments, "0.9.0")[0].claim_id == "claim:c1"


def test_reassessment_invalidates_the_dependent_presentations():
    presentations = [
        Presentation(
            id="card:p1", kind="claim_card", claim_ids=("claim:c2",), edge_ids=(), policy_version="0.9.0"
        ),
        Presentation(
            id="card:p2", kind="claim_card", claim_ids=("claim:c9",), edge_ids=(), policy_version="0.9.0"
        ),
        Presentation(
            id="essay:p3", kind="essay", claim_ids=("claim:c1", "claim:c2"), edge_ids=(), policy_version="0.9.0"
        ),
    ]
    after = {p.id: p for p in invalidate(presentations, claim_ids=["claim:c2"])}
    assert not after["card:p1"].live
    assert after["card:p1"].invalidation_reason == "policy_version_change"
    assert after["card:p2"].live
    assert not after["essay:p3"].live


def test_a_withdrawn_edge_invalidates_what_cited_it():
    presentations = [
        Presentation(
            id="card:p1",
            kind="claim_card",
            claim_ids=("claim:c1",),
            edge_ids=("edge:e1", "edge:e2"),
            policy_version="1.0.0",
        )
    ]
    after = invalidate(presentations, edge_ids=["edge:e2"], reason="edge_withdrawn")
    assert not after[0].live
    assert after[0].invalidation_reason == "edge_withdrawn"


def test_the_bundle_digest_covers_every_input_a_policy_change_would_touch():
    record = BUNDLE.as_record()
    for key in (
        "capability_matrix",
        "required_evidence_lanes",
        "thresholds",
        "independence_justifications",
        "task_states",
    ):
        assert key in record, key
    assert len(BUNDLE.digest) == 64
