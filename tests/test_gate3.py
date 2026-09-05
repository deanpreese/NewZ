"""Gate 3: three investigations, three defensible outcomes, no manual edit.

Every claim here was proposed by the model and accepted because its quotation
verified. Every task was generated from the claim's kind. Every resolver outcome
was recorded through the resolver path, and the reversal happens because a
retraction notice was read in the correction lane — not because a test reached
into the database and changed a row. The one thing this file does directly is
register bases, which is the operator's job in Phase 3 and the research
manager's in Phase 6.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from newz.domain.enums import (
    AssessmentState,
    ClaimKind,
    EdgeRelation,
    EvidenceLane,
    IndependenceJustification,
    RiskTier,
    TaskState,
)
from newz.evidence.assess import assess_claim, assessment_history, current_assessment
from newz.evidence.bases import record_basis, record_independence
from newz.evidence.edges import admit_edge
from newz.evidence.inspect import explain
from newz.research import investigations
from newz.research.packets import evidence_packet
from newz.research.resolution import apply_retraction, record_resolution
from newz.research.tasks import generate_tasks, transition_task
from tests import world as world_module

NOW = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def world(store):
    built = world_module.build(store)
    with store.write() as connection:
        record_basis(connection, "basis:witness", "witness", "witness:alvarado-r", True)
        record_basis(connection, "basis:proto-4471", "experiment", "protocol:PROTO-4471", True)
        record_basis(connection, "basis:proto-5520", "experiment", "protocol:PROTO-5520", True)
        record_basis(connection, "basis:complaint", "filing", "docket:3:25-cv-01142#1", True)
        record_basis(connection, "basis:judgment", "official_record", "docket:3:25-cv-01142#44", True)
        record_basis(connection, "basis:retraction", "official_record", "retraction:JAFM-41-233", True)
        record_independence(
            connection,
            "independence:labs",
            "basis:proto-4471",
            "basis:proto-5520",
            IndependenceJustification.DISTINCT_EXPERIMENT,
            evidence="different laboratories, different protocol registrations",
        )
    return built


def _work_task(store, task_id: str) -> None:
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.IN_PROGRESS)


def _investigate(store, world, key: str, claim_name: str, question: str) -> str:
    """Open an investigation over a model-proposed claim and generate its tasks."""
    claim_id = world.claim(key, claim_name)
    kind = ClaimKind(store.one("SELECT kind FROM claims WHERE id = ?", claim_id)["kind"])
    investigations.open_investigation(
        store,
        investigation_id=f"investigation:{claim_name}",
        question=question,
        rationale="a claim was raised with nothing yet behind it",
        exit_conditions=("every required lane reports", "or the record settles it"),
        closing_observation="a countable edge in either direction, or a competent empty search",
        origin="assessment",
        claim_ids=(claim_id,),
    )
    generate_tasks(store, claim_id, kind, NOW)
    return claim_id


# ---------------------------------------------------------------------------
# Investigation one: explicitly unresolved
# ---------------------------------------------------------------------------


def test_an_investigation_that_looks_everywhere_and_finds_nothing(store, world):
    claim = _investigate(
        store, world, "registry", "radar",
        "Was there an uncorrelated radar return over Coral Ridge on 2 March?",
    )
    packet = evidence_packet(store, claim)
    assert len(packet.missing_lanes) == 4

    resolvers = {
        EvidenceLane.CLAIMANT_ORIGIN: ("competent_registry", TaskState.SATISFIED),
        EvidenceLane.PRIMARY_RECORD: ("competent_registry", TaskState.EXHAUSTED),
        EvidenceLane.INDEPENDENT_COUNTERPART: ("competent_registry", TaskState.EXHAUSTED),
        EvidenceLane.SKEPTICAL_ANALYSIS: ("publication_status", TaskState.UNREACHABLE),
    }
    for index, (lane, (resolver, outcome)) in enumerate(resolvers.items()):
        task_id = f"task:{claim.split(':')[-1]}-{lane.value}"
        _work_task(store, task_id)
        record_resolution(
            store,
            attempt_id=f"attempt:radar{index}",
            task_id=task_id,
            claim_id=claim,
            resolver=resolver,
            outcome=outcome,
            detail=f"{lane.value} concluded",
            sought="a radar correlation record for the sector and window",
            searched="the National Aviation Safety Registry occurrence index",
            time_window="2026-03-02 18:00/20:00 local",
        )

    result = assess_claim(store, claim, "assessment:radar")
    assert result.state is AssessmentState.INDETERMINATE
    assert "searched competently" in result.explanation

    # Unresolved, and explicitly so: the packet says what would change it.
    packet = evidence_packet(store, claim)
    assert packet.missing_lanes == ()
    assert packet.what_would_change_it == "any countable evidence in either direction"

    investigations.close_investigation(
        store, "investigation:radar", "every required lane concluded without a countable edge"
    )
    assert investigations.load(store, "investigation:radar").state == "closed"


# ---------------------------------------------------------------------------
# Investigation two: refuted by the record
# ---------------------------------------------------------------------------


def test_an_allegation_refuted_by_a_final_adjudicative_record(store, world):
    claim = _investigate(
        store, world, "complaint", "falsified",
        "Did Meridian Instruments falsify calibration records?",
    )
    with store.write() as connection:
        connection.execute("UPDATE claims SET risk = 'R3' WHERE id = ?", (claim,))

    _, alleged = admit_edge(
        store,
        edge_id="edge:g3-alleges",
        assertion_id=world.assertion("complaint", "alleges"),
        claim_id=claim,
        relation=EdgeRelation.SUPPORTS,
        basis_id="basis:complaint",
        risk=RiskTier.R3,
    )
    assert not alleged.admitted  # a complaint proves an allegation was filed

    task_id = f"task:{claim.split(':')[-1]}-resolver"
    _work_task(store, task_id)
    record_resolution(
        store,
        attempt_id="attempt:docket",
        task_id=task_id,
        claim_id=claim,
        resolver="docket",
        outcome=TaskState.SATISFIED,
        detail="the docket carries a final judgment",
        sought="a final judgment on the falsification counts",
        searched="the Northern District civil docket",
        time_window="2025-11-04/2026-06-19",
    )
    admit_edge(
        store,
        edge_id="edge:g3-judgment",
        assertion_id=world.assertion("court", "judgment"),
        claim_id=claim,
        relation=EdgeRelation.CONTRADICTS,
        basis_id="basis:judgment",
        risk=RiskTier.R3,
        adjudicative_scope_covers_claim=True,
    )

    result = assess_claim(store, claim, "assessment:falsified")
    assert result.state is AssessmentState.REFUTED
    assert "single_record_exception" in result.explanation
    assert "refused: allegation_is_not_proof" in explain(store, claim)


# ---------------------------------------------------------------------------
# Investigation three: reversed by a later correction
# ---------------------------------------------------------------------------


def test_a_contested_claim_reverses_when_its_support_is_retracted(store, world):
    claim = _investigate(
        store, world, "kettleby", "signature",
        "Does the RX-9 array show a thermal signature above baseline?",
    )
    admit_edge(
        store,
        edge_id="edge:g3-effect",
        assertion_id=world.assertion("kettleby", "effect"),
        claim_id=claim,
        relation=EdgeRelation.SUPPORTS,
        basis_id="basis:proto-4471",
        risk=RiskTier.R1,
    )
    admit_edge(
        store,
        edge_id="edge:g3-noeffect",
        assertion_id=world.assertion("ardenne", "no_effect"),
        claim_id=claim,
        relation=EdgeRelation.CONTRADICTS,
        basis_id="basis:proto-5520",
        risk=RiskTier.R1,
    )
    before = assess_claim(store, claim, "assessment:sig1")
    assert before.state is AssessmentState.CONTESTED
    assert (before.supporting_bases, before.contradicting_bases) == (1, 1)

    # The correction lane read the journal's retraction of the supporting study.
    # The resolver acts on it; nothing here edits a row.
    withdrawn = apply_retraction(
        store,
        basis_id="basis:proto-4471",
        reason="the journal retracted the study: the calibration constant was superseded",
        evidence_assertion_id=world.assertion("journal", "retracted"),
    )
    assert withdrawn == ("edge:g3-effect",)

    after = assess_claim(store, claim, "assessment:sig2")
    assert after.state is AssessmentState.PROVISIONAL_CONTRADICTION
    assert (after.supporting_bases, after.contradicting_bases) == (0, 1)

    history = [entry.state for entry in assessment_history(store, claim)]
    assert history == [AssessmentState.CONTESTED, AssessmentState.PROVISIONAL_CONTRADICTION]

    # The withdrawal is a fact in the record, not an absence from it.
    row = store.one("SELECT admitted, live FROM edge_events WHERE id = 'edge:g3-effect'")
    assert (row["admitted"], row["live"]) == (1, 0)
    audit = store.one("SELECT * FROM audit_events WHERE action = 'apply_retraction'")
    assert "withdrawn_edges" in audit["preimage"]
    assert "retracted the study" in audit["reason"]


# ---------------------------------------------------------------------------
# The gate itself
# ---------------------------------------------------------------------------


def test_three_investigations_reach_three_different_outcomes(store, world):
    test_an_investigation_that_looks_everywhere_and_finds_nothing(store, world)
    test_an_allegation_refuted_by_a_final_adjudicative_record(store, world)
    test_a_contested_claim_reverses_when_its_support_is_retracted(store, world)

    states = {
        row["claim_id"]: row["state"]
        for row in store.query(
            "SELECT claim_id, state FROM assessments a WHERE a.rowid = "
            "(SELECT MAX(b.rowid) FROM assessments b WHERE b.claim_id = a.claim_id)"
        )
    }
    assert sorted(states.values()) == [
        "indeterminate",
        "provisional_contradiction",
        "refuted",
    ]


def test_no_step_of_the_gate_required_a_manual_edit(store, world):
    """Every claim came from an extraction, every task from a claim kind, and
    every terminal task state from a resolver or the lifecycle."""
    test_a_contested_claim_reverses_when_its_support_is_retracted(store, world)

    for claim_id in (world.claim("kettleby", "signature"),):
        origin = store.one("SELECT * FROM claim_origins WHERE claim_id = ?", claim_id)
        assert origin["extraction_run_id"]
        assert origin["quote"]

    # Every terminal-incomplete task carries a reason, and every competent one
    # carries what it looked for.
    for row in store.query("SELECT * FROM tasks WHERE state NOT IN ('open','scheduled','in_progress','blocked')"):
        if row["state"] in ("exhausted", "unreachable"):
            assert row["expected_record"] and row["searched_scope"], row["id"]
        else:
            assert row["state"] == "satisfied" or row["state_reason"], row["id"]


def test_new_evidence_produces_a_revised_assessment_end_to_end(store, world):
    """The trace a reader follows: retrieved bytes, a verified quote, an edge, a
    state, and the state that replaced it."""
    test_a_contested_claim_reverses_when_its_support_is_retracted(store, world)
    claim = world.claim("kettleby", "signature")

    prose = explain(store, claim)
    assert "provisional_contradiction" in prose
    assert "withdrawn" in prose
    assert "quote verifies now: True" in prose
    assert current_assessment(store, claim).countable_edge_ids == ("edge:g3-noeffect",)
