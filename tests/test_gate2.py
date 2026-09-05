"""Gate 2: the controlled corpus reaches the expected states, explainably.

Everything here runs through the store. Eight sources are fetched through the
scheduler, parsed, extracted from with a stub standing in only for the far side
of the local endpoint, and turned into bases, edges and assessments. The states
below are derived from rows, and the explanation of each is composed from rows —
no chain-of-thought, no generated prose.
"""

from __future__ import annotations

import json

import pytest

from newz.domain.enums import (
    AssessmentState,
    EdgeRelation,
    EvidenceLane,
    IndependenceJustification,
    RefusalReason,
    RiskTier,
    TaskState,
)
from newz.evidence.assess import assess_claim, assessment_history, stale_claims
from newz.evidence.bases import (
    correct_basis,
    load_bases,
    record_basis,
    record_derivation,
    record_independence,
)
from newz.evidence.edges import admit_edge, withdraw_edge
from newz.evidence.inspect import explain, trace_claim
from tests import world as world_module
from tests.world import add_claim, add_task


@pytest.fixture
def world(store):
    built = world_module.build(store)
    _bases(store)
    return built


def _bases(store):
    """The upstream origins, and the lineage that makes two of them one."""
    with store.write() as connection:
        record_basis(connection, "basis:witness-alvarado", "witness", "witness:alvarado-r", True)
        record_basis(connection, "basis:wire-copy", "witness", "witness:alvarado-as-carried", True)
        record_basis(connection, "basis:registry-record", "official_record", "occurrence:2026-0311-CR", True)
        record_basis(connection, "basis:patent", "filing", "patent:US11842905B2", True)
        record_basis(connection, "basis:complaint", "filing", "docket:3:25-cv-01142#1", True)
        record_basis(connection, "basis:judgment", "official_record", "docket:3:25-cv-01142#44", True)
        record_basis(connection, "basis:proto-4471", "experiment", "protocol:PROTO-4471", True)
        record_basis(connection, "basis:proto-5520", "experiment", "protocol:PROTO-5520", True)
        # The wire copy is downstream of the witness: one origin reached twice.
        record_derivation(
            connection,
            "basis:wire-copy",
            "basis:witness-alvarado",
            "the wire copy carries the Harbour Dispatch quotation verbatim",
        )
        record_independence(
            connection,
            "independence:labs",
            "basis:proto-4471",
            "basis:proto-5520",
            IndependenceJustification.DISTINCT_EXPERIMENT,
            evidence="different laboratories and different protocol registrations",
        )


def _edge(store, world, edge_id, key, name, claim_id, relation, basis, **kwargs):
    return admit_edge(
        store,
        edge_id=edge_id,
        assertion_id=world.assertion(key, name),
        claim_id=claim_id,
        relation=relation,
        basis_id=basis,
        risk=kwargs.pop("risk", RiskTier.R1),
        declared_scope=world.sources[key].revision.declared_scope,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# The five states
# ---------------------------------------------------------------------------


def test_supported(store, world):
    """An attribution claim settled by the record that literally establishes it."""
    claim = add_claim(
        store, "claim:attribution", "attribution",
        "Captain R. Alvarado reported that an object held station off her wing.", "R1",
    )
    _edge(store, world, "edge:a1", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:witness-alvarado")
    add_task(store, "task:a1", claim, EvidenceLane.CLAIMANT_ORIGIN, TaskState.SATISFIED)

    result = assess_claim(store, claim, "assessment:a1")
    assert result.state is AssessmentState.SUPPORTED
    assert result.supporting_bases == 1
    assert "single_record_exception" in result.explanation


def test_contested(store, world):
    """Countable evidence in both directions, with the shape of it preserved."""
    claim = add_claim(
        store, "claim:effect", "measurement_or_association",
        "The RX-9 array shows a thermal signature above baseline.", "R1",
    )
    _edge(store, world, "edge:e1", "kettleby", "effect", claim, EdgeRelation.SUPPORTS, "basis:proto-4471")
    _edge(store, world, "edge:e2", "ardenne", "no_effect", claim, EdgeRelation.CONTRADICTS, "basis:proto-5520")

    result = assess_claim(store, claim, "assessment:e1")
    assert result.state is AssessmentState.CONTESTED
    assert (result.supporting_bases, result.contradicting_bases) == (1, 1)


def test_refuted(store, world):
    """The allegation is admitted as an allegation and refuted by the record."""
    claim = add_claim(
        store, "claim:wrongdoing", "identity_or_wrongdoing_allegation",
        "Meridian Instruments knowingly falsified calibration records.", "R3",
    )
    _, alleges = _edge(
        store, world, "edge:w1", "complaint", "alleges", claim,
        EdgeRelation.SUPPORTS, "basis:complaint", risk=RiskTier.R3,
    )
    _, judgment = _edge(
        store, world, "edge:w2", "court", "judgment", claim,
        EdgeRelation.CONTRADICTS, "basis:judgment", risk=RiskTier.R3,
        adjudicative_scope_covers_claim=True,
    )
    assert not alleges.admitted
    assert alleges.reason is RefusalReason.ALLEGATION_IS_NOT_PROOF
    assert judgment.admitted

    result = assess_claim(store, claim, "assessment:w1")
    assert result.state is AssessmentState.REFUTED
    assert result.contradicting_bases == 1
    assert "single_record_exception" in result.explanation


def test_reported(store, world):
    """A patent proves a filing. The performance claim stays where it was."""
    claim = add_claim(
        store, "claim:thrust", "capability_or_performance",
        "The apparatus produces net directional thrust without propellant.", "R1",
    )
    _, admission = _edge(
        store, world, "edge:t1", "patents", "thrust", claim, EdgeRelation.SUPPORTS, "basis:patent"
    )
    assert not admission.admitted
    assert admission.reason is RefusalReason.FILING_IS_NOT_PERFORMANCE

    result = assess_claim(store, claim, "assessment:t1")
    assert result.state is AssessmentState.REPORTED
    assert result.supporting_bases == 0


def test_indeterminate(store, world):
    """Every required lane looked competently and found nothing."""
    claim = add_claim(
        store, "claim:radar", "event_or_observation",
        "An uncorrelated radar return accompanied the Coral Ridge sighting.", "R1",
    )
    for index, lane in enumerate(
        (
            EvidenceLane.CLAIMANT_ORIGIN,
            EvidenceLane.PRIMARY_RECORD,
            EvidenceLane.INDEPENDENT_COUNTERPART,
            EvidenceLane.SKEPTICAL_ANALYSIS,
        )
    ):
        add_task(store, f"task:r{index}", claim, lane, TaskState.EXHAUSTED)

    result = assess_claim(store, claim, "assessment:r1")
    assert result.state is AssessmentState.INDETERMINATE
    assert (result.supporting_bases, result.contradicting_bases) == (0, 0)


def test_a_lane_that_did_not_search_holds_the_state_instead(store, world):
    claim = add_claim(store, "claim:radar2", "event_or_observation", "the same question", "R1")
    for index, lane in enumerate(
        (
            EvidenceLane.CLAIMANT_ORIGIN,
            EvidenceLane.PRIMARY_RECORD,
            EvidenceLane.INDEPENDENT_COUNTERPART,
        )
    ):
        add_task(store, f"task:h{index}", claim, lane, TaskState.EXHAUSTED)
    add_task(
        store, "task:h9", claim, EvidenceLane.SKEPTICAL_ANALYSIS, TaskState.REFUSED,
        state_reason="retention terms forbid retaining the analysis",
    )

    result = assess_claim(store, claim, "assessment:h1")
    assert result.state is AssessmentState.REPORTED
    assert result.blocked_lanes[0][0] is EvidenceLane.SKEPTICAL_ANALYSIS
    assert "retention terms" in result.blocked_lanes[0][2]


# ---------------------------------------------------------------------------
# Syndication and hidden common origin
# ---------------------------------------------------------------------------


def test_a_syndicated_copy_is_not_a_second_basis(store, world):
    """Two publishers, one witness. The derivation link is what knows it."""
    claim = add_claim(
        store, "claim:paced", "event_or_observation",
        "An object paced a commercial aircraft near Coral Ridge.", "R1",
    )
    _edge(store, world, "edge:p1", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:witness-alvarado")
    _edge(store, world, "edge:p2", "meridian", "sighting", claim, EdgeRelation.SUPPORTS, "basis:wire-copy")

    result = assess_claim(store, claim, "assessment:p1")
    assert result.state is AssessmentState.PROVISIONAL_SUPPORT
    assert result.supporting_bases == 1
    assert len(result.countable_edge_ids) == 1  # the claimant edge is refused
    assert "one_independent_basis" in result.explanation


def test_derivation_lineage_defeats_even_an_operator_justification(store, world):
    """A hidden common origin, once recorded, cannot be justified away."""
    with store.write() as connection:
        record_independence(
            connection,
            "independence:wrong",
            "basis:witness-alvarado",
            "basis:wire-copy",
            IndependenceJustification.OPERATOR_VERIFIED,
            evidence="the two reports read as separate accounts",
            operator_actor="operator:dean",
            operator_reason="reviewed by hand",
        )
    claim = add_claim(store, "claim:paced2", "event_or_observation", "the same event", "R1")
    _edge(store, world, "edge:q1", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:witness-alvarado")
    _edge(store, world, "edge:q2", "registry", "no_radar", claim, EdgeRelation.SUPPORTS, "basis:wire-copy")

    result = assess_claim(store, claim, "assessment:q1")
    assert result.supporting_bases == 1
    bases = load_bases(store)
    assert bases["basis:wire-copy"].independence_group == bases["basis:witness-alvarado"].independence_group


# ---------------------------------------------------------------------------
# Change over time
# ---------------------------------------------------------------------------


def test_withdrawing_an_edge_changes_the_assessment_and_keeps_the_history(store, world):
    claim = add_claim(store, "claim:attribution", "attribution", "the pilot reported it", "R1")
    _edge(store, world, "edge:x1", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:witness-alvarado")
    add_task(store, "task:x1", claim, EvidenceLane.CLAIMANT_ORIGIN, TaskState.SATISFIED)
    first = assess_claim(store, claim, "assessment:x1")
    assert first.state is AssessmentState.SUPPORTED

    withdraw_edge(store, "edge:x1", "the publication retracted the quotation")
    second = assess_claim(store, claim, "assessment:x2")
    assert second.state is AssessmentState.INDETERMINATE

    history = assessment_history(store, claim)
    assert [entry.state for entry in history] == [
        AssessmentState.SUPPORTED,
        AssessmentState.INDETERMINATE,
    ]
    # The withdrawn edge is still readable; withdrawal was an event, not an edit.
    row = store.one("SELECT admitted, live FROM edge_events WHERE id = 'edge:x1'")
    assert row["admitted"] == 1
    assert row["live"] == 0
    assert store.one("SELECT COUNT(*) AS n FROM outbox WHERE kind = 'edge_withdrawn'")["n"] == 1


def test_an_operator_correction_to_a_basis_is_recorded_and_reassessed(store, world):
    claim = add_claim(store, "claim:corr", "attribution", "the pilot reported it", "R1")
    with store.write() as connection:
        record_basis(connection, "basis:unknown-origin", "witness", "unnamed", False)
    _edge(store, world, "edge:c1", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:unknown-origin")
    add_task(store, "task:c1", claim, EvidenceLane.CLAIMANT_ORIGIN, TaskState.SATISFIED)

    before = assess_claim(store, claim, "assessment:c1")
    assert before.state is AssessmentState.INDETERMINATE  # the basis does not resolve

    correct_basis(
        store,
        "correction:1",
        "basis:unknown-origin",
        actor="operator:dean",
        reason="the witness is named in the operator's own notes",
        resolved=True,
    )

    # The correction does not revive the refused edge: admission was a decision
    # under a policy version against the basis as it then stood. What it does is
    # name what needs re-evaluating, so nobody has to remember.
    event = store.one("SELECT * FROM outbox WHERE kind = 'basis_corrected'")
    assert json.loads(event["payload"])["edges_to_re_evaluate"] == ["edge:c1"]
    unchanged = assess_claim(store, claim, "assessment:c2")
    assert unchanged.state is AssessmentState.INDETERMINATE

    # Re-evaluation is a new edge event, and now it is admitted.
    _edge(store, world, "edge:c2", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:unknown-origin")
    after = assess_claim(store, claim, "assessment:c3")
    assert after.state is AssessmentState.SUPPORTED

    audit = store.one("SELECT * FROM audit_events WHERE action = 'correct_basis'")
    assert audit["actor"] == "operator:dean"
    assert "resolved" in audit["preimage"]
    # Both events survive: the refusal and the admission are both readable.
    assert store.one("SELECT COUNT(*) AS n FROM edge_events WHERE basis_id = ?",
                     "basis:unknown-origin")["n"] == 2


def test_a_policy_version_change_marks_the_claims_derived_under_the_old_one(store, world):
    claim = add_claim(store, "claim:policy", "attribution", "the pilot reported it", "R1")
    _edge(store, world, "edge:v1", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:witness-alvarado")
    assess_claim(store, claim, "assessment:v1", policy_version="0.9.0")

    assert stale_claims(store, "1.0.0") == (claim,)
    assess_claim(store, claim, "assessment:v2", policy_version="1.0.0")
    assert stale_claims(store, "1.0.0") == ()


# ---------------------------------------------------------------------------
# Explainability
# ---------------------------------------------------------------------------


def test_every_state_is_explainable_from_rows_alone(store, world):
    claim = add_claim(
        store, "claim:wrongdoing", "identity_or_wrongdoing_allegation",
        "Meridian Instruments knowingly falsified calibration records.", "R3",
    )
    _edge(store, world, "edge:i1", "complaint", "alleges", claim, EdgeRelation.SUPPORTS, "basis:complaint", risk=RiskTier.R3)
    _edge(
        store, world, "edge:i2", "court", "judgment", claim, EdgeRelation.CONTRADICTS,
        "basis:judgment", risk=RiskTier.R3, adjudicative_scope_covers_claim=True,
    )
    assess_claim(store, claim, "assessment:i1")

    prose = explain(store, claim)
    assert "refuted" in prose
    assert "single_record_exception" in prose
    assert "refused: allegation_is_not_proof" in prose
    assert "The court finds no evidence" in prose
    assert "quote verifies now: True" in prose


def test_the_trace_reaches_from_the_assessment_back_to_the_retrieved_bytes(store, world):
    claim = add_claim(store, "claim:attribution", "attribution", "the pilot reported it", "R1")
    _edge(store, world, "edge:t9", "harbour", "sighting", claim, EdgeRelation.SUPPORTS, "basis:witness-alvarado")
    assess_claim(store, claim, "assessment:t9")

    trace = trace_claim(store, claim)
    edge = trace["edges"][0]
    assert edge["counted"]
    assertion = edge["assertion"]
    assert assertion["quote_verifies_now"]
    assert assertion["retrieved_from"] == "https://harbour.example/document"
    assert assertion["locator"].endswith("p 3")
    assert set(edge["predicates"]) == {
        "assertion_live",
        "artifact_and_span_present",
        "basis_identity_resolved",
        "policy_version_recorded",
        "quote_verified",
        "risk_classified",
        "tuple_permitted",
    }
    assert all(predicate["held"] for predicate in edge["predicates"].values())


def test_a_refusal_carries_the_inputs_that_produced_it(store, world):
    claim = add_claim(store, "claim:thrust", "capability_or_performance", "it produces thrust", "R1")
    _edge(store, world, "edge:t8", "patents", "thrust", claim, EdgeRelation.SUPPORTS, "basis:patent")
    assess_claim(store, claim, "assessment:t8")

    edge = trace_claim(store, claim)["edges"][0]
    assert not edge["admitted"]
    assert edge["refusal_reason"] == "filing_is_not_performance"
    tuple_predicate = edge["predicates"]["tuple_permitted"]
    assert not tuple_predicate["held"]
    assert tuple_predicate["inputs"] == {
        "assertion_kind": "documented_event",
        "claim_kind": "capability_or_performance",
        "relation": "supports",
        "role": "primary_record",
    }
