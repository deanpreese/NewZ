"""Gate 4A: the system opens an investigation nobody asked for.

It notices something in retained material, forms an interest, opens an
investigation with its exit conditions stated first, pursues it through the
ordinary lanes, and writes an essay about what it found — and the essay reports
a conclusion the originating interest did not want.

Everything the gate credits is then put through the simpler-explanation review,
adversarially, because a gate that credits initiative without asking whether
retrieval order would explain it is a gate that can be passed by a sort.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from newz.attention import interest, notices
from newz.attention.essays import essay_from_interest, select_subject
from newz.attention.origination import OriginationRefused, originate
from newz.domain.enums import (
    AssessmentState,
    ClaimKind,
    DecisionOutcome,
    EdgeRelation,
    EvidenceLane,
    RiskTier,
    TaskState,
)
from newz.evidence.assess import assess_claim
from newz.evidence.bases import record_basis
from newz.evidence.edges import admit_edge
from newz.present.essays import compose_essay
from newz.reckoning import checks, consequence, decisions
from newz.research.resolution import record_resolution
from newz.research.tasks import transition_task
from tests import world as world_module

NOW = datetime(2026, 9, 5, 12, 0, 0)
TARGETS = {"uap_and_aerospace_anomalies": "18%"}
NOTICED = "It held station off the right wing"


@pytest.fixture
def world(store):
    built = world_module.build(store)
    with store.write() as connection:
        record_basis(connection, "basis:witness", "witness", "witness:alvarado-r", True)
        record_basis(connection, "basis:registry", "official_record", "occurrence:2026-0311", True)
    return built


@pytest.fixture
def curious(store, world):
    """A notice, an interest formed from it, and the expectation it carried."""
    notices.notice_over_span(
        store,
        "notice:n1",
        world.artifact("harbour"),
        NOTICED,
        "a station-keeping manoeuvre is specific enough to check against a record",
    )
    entry = interest.form_interest(
        store,
        interest_id="interest:i1",
        subject="station-keeping manoeuvres in pilot accounts",
        rationale="the account describes something an occurrence record would corroborate",
        notice_ids=("notice:n1",),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    decisions.record_expectation(
        store,
        expectation_id="expectation:e1",
        subject="claim:registry-0",
        expected="the registry will corroborate the account",
        recorded_before="originating the investigation",
    )
    decisions.record_decision(
        store,
        decision_id="decision:d1",
        outcome=DecisionOutcome.ORIGINATE,
        subject="claim:registry-0",
        alternatives=("leave it as a claimant report", "wait for a counterpart read"),
        decided_by="interest:i1",
        reason="the registry is reachable and the question is narrow",
        expectation_id="expectation:e1",
        confidence="moderate",
    )
    return entry


# ---------------------------------------------------------------------------
# It opens an investigation nobody asked for
# ---------------------------------------------------------------------------


def test_interest_opens_an_investigation_and_states_its_exit_first(store, world, curious):
    claim = world.claim("registry", "radar")
    result = originate(
        store,
        interest_id="interest:i1",
        investigation_id="investigation:originated",
        question="Does an occurrence record corroborate the Coral Ridge account?",
        exit_conditions=("the registry answers", "or the window is competently exhausted"),
        closing_observation="a correlation record for the sector and window, or its absence",
        claim_id=claim,
        claim_kind=ClaimKind.EVENT_OR_OBSERVATION,
        now=NOW,
    )
    assert result.tasks
    row = store.one("SELECT * FROM investigations WHERE id = 'investigation:originated'")
    assert row["origin"] == "interest"
    # The investigation existed, with its exit conditions, before any task did.
    assert row["exit_conditions"]
    assert interest.load_interest(store, "interest:i1").outcomes == (
        ("investigation", "investigation:originated"),
    )


def test_an_originated_investigation_consumes_no_extra_budget(store, world, curious):
    """Its tasks queue in the ordinary lanes; the diet keeps sole control."""
    claim = world.claim("registry", "radar")
    before = store.one("SELECT COUNT(*) AS n FROM reservations")["n"]
    originate(
        store,
        interest_id="interest:i1",
        investigation_id="investigation:originated",
        question="a question",
        exit_conditions=("something",),
        closing_observation="an observation",
        claim_id=claim,
        claim_kind=ClaimKind.EVENT_OR_OBSERVATION,
        now=NOW,
    )
    assert store.one("SELECT COUNT(*) AS n FROM reservations")["n"] == before
    lanes = {row["lane"] for row in store.query("SELECT lane FROM tasks")}
    assert lanes <= {lane.value for lane in EvidenceLane}


def test_the_origination_ceiling_holds(store, world, curious):
    claim = world.claim("registry", "radar")
    for index in range(5):
        with store.write() as connection:
            connection.execute(
                "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
                "withdrawn, recorded_at) VALUES (?, 'event_or_observation', 'a claim', 'R1', "
                "NULL, NULL, 0, datetime('now'))",
                (f"claim:extra{index}",),
            )
        originate(
            store,
            interest_id="interest:i1",
            investigation_id=f"investigation:o{index}",
            question=f"question {index}",
            exit_conditions=("something",),
            closing_observation="an observation",
            claim_id=f"claim:extra{index}",
            claim_kind=ClaimKind.EVENT_OR_OBSERVATION,
            now=NOW,
        )
    with pytest.raises(OriginationRefused, match="ceiling"):
        originate(
            store,
            interest_id="interest:i1",
            investigation_id="investigation:sixth",
            question="one too many",
            exit_conditions=("something",),
            closing_observation="an observation",
            claim_id=claim,
            claim_kind=ClaimKind.EVENT_OR_OBSERVATION,
            now=NOW,
        )


# ---------------------------------------------------------------------------
# It pursues it, and finds what it did not want
# ---------------------------------------------------------------------------


@pytest.fixture
def pursued(store, world, curious):
    """The originated investigation, run to a conclusion the interest disliked."""
    claim = world.claim("registry", "radar")
    originate(
        store,
        interest_id="interest:i1",
        investigation_id="investigation:originated",
        question="Does an occurrence record corroborate the Coral Ridge account?",
        exit_conditions=("the registry answers", "or the window is competently exhausted"),
        closing_observation="a correlation record for the sector and window, or its absence",
        claim_id=claim,
        claim_kind=ClaimKind.EVENT_OR_OBSERVATION,
        now=NOW,
    )
    # The claimant lane is satisfied by the account itself.
    admit_edge(
        store,
        edge_id="edge:says",
        assertion_id=world.assertion("harbour", "sighting"),
        claim_id=claim,
        relation=EdgeRelation.CLAIMANT_SAYS,
        basis_id="basis:witness",
        risk=RiskTier.R1,
    )
    suffix = claim.split(":")[-1]
    outcomes = {
        EvidenceLane.CLAIMANT_ORIGIN: TaskState.SATISFIED,
        EvidenceLane.PRIMARY_RECORD: TaskState.EXHAUSTED,
        EvidenceLane.INDEPENDENT_COUNTERPART: TaskState.EXHAUSTED,
        EvidenceLane.SKEPTICAL_ANALYSIS: TaskState.UNREACHABLE,
    }
    for index, (lane, outcome) in enumerate(outcomes.items()):
        task_id = f"task:{suffix}-{lane.value}"
        transition_task(store, task_id, TaskState.SCHEDULED)
        transition_task(store, task_id, TaskState.IN_PROGRESS)
        record_resolution(
            store,
            attempt_id=f"attempt:a{index}",
            task_id=task_id,
            claim_id=claim,
            resolver="competent_registry",
            outcome=outcome,
            detail=f"{lane.value} concluded",
            sought="a correlation record for the Coral Ridge sector",
            searched="the National Aviation Safety Registry occurrence index",
            time_window="2026-03-02 18:00/20:00 local",
        )
    assessment = assess_claim(store, claim, "assessment:originated")
    return claim, assessment


def test_the_investigation_reaches_a_conclusion_the_interest_did_not_want(store, world, pursued):
    claim, assessment = pursued
    assert assessment.state is AssessmentState.INDETERMINATE

    outcome = consequence.confirm_from_evidence(
        store, outcome_id="outcome:o1", expectation_id="expectation:e1", claim_id=claim
    )
    diverged, detail = consequence.compare(store, "expectation:e1", outcome)
    assert diverged, detail

    consequence.record_surprise(
        store,
        surprise_id="surprise:s1",
        expectation_id="expectation:e1",
        outcome_id=outcome,
        divergence="expected corroboration; the registry competently held nothing",
        fits_live_interest=True,
        raise_to_operator=True,
    )
    consequence.record_consequence(
        store,
        consequence_id="consequence:c1",
        expectation_id="expectation:e1",
        outcome_id=outcome,
        score="-1: the expectation was wrong in the direction of wanting it to be true",
        changed="interest_priority",
        change_cites=(
            "consequence:c1 lowered interest:i1 from 5 to 3 because its first "
            "investigation found an explicit absence"
        ),
    )
    calibration = consequence.calibration(store)
    assert calibration["surprises"] == 1
    assert calibration["consequences"] == 1
    assert calibration["changes_by_kind"] == {"interest_priority": 1}


def test_the_essay_reports_what_was_found_and_not_what_was_wanted(store, world, pursued):
    """Interest chose the subject. It does not get the verdict."""
    claim, _ = pursued
    subject, claim_ids = select_subject(store, "interest:i1")
    assert claim_ids == (claim,)
    assert subject == "station-keeping manoeuvres in pilot accounts"

    essay = essay_from_interest(
        store, interest_id="interest:i1", essay_id="essay:e1", intended_conclusion="supported"
    )
    assert essay.outcome == "changed"
    assert "The record does not hold that" in essay.content
    assert "indeterminate" in essay.content
    assert claim in essay.content
    # And it is recorded as an outcome of the interest that chose the subject.
    assert ("essay", "essay:e1") in interest.load_interest(store, "interest:i1").outcomes


def test_an_essay_never_renders_the_intended_conclusion_anyway(store, world, pursued):
    claim, _ = pursued
    essay = compose_essay(
        store,
        essay_id="essay:e2",
        subject="a subject",
        claim_ids=(claim,),
        intended_conclusion="supported",
    )
    assert essay.outcome != "composed"
    # The intent is named in order to be disavowed, which is the point: an essay
    # that quietly became a different essay is the shape this rule forbids.
    assert "written to argue that the subject is supported" in essay.content
    assert "The record does not hold that" in essay.content
    # And nowhere does the body assert the state it wanted.
    assert "The record holds this as supported" not in essay.content
    assert "The record holds this as indeterminate" in essay.content


def test_an_essay_with_nothing_assessed_goes_unwritten(store, world, curious):
    essay = compose_essay(
        store,
        essay_id="essay:e3",
        subject="a subject",
        claim_ids=("claim:absent",),
        intended_conclusion="supported",
    )
    assert essay.outcome == "unwritten"
    assert not essay.rendered
    assert essay.content == ""


def test_an_essay_carries_every_claims_state_and_counterevidence(store, world, pursued):
    claim, _ = pursued
    essay = compose_essay(
        store,
        essay_id="essay:e4",
        subject="a subject",
        claim_ids=(claim,),
        intended_conclusion="unresolved",
    )
    assert essay.outcome == "composed"
    assert "indeterminate" in essay.content
    assert claim in essay.content


# ---------------------------------------------------------------------------
# The register reports what it caused, and what it let go
# ---------------------------------------------------------------------------


def test_the_register_reports_its_provenance_share_and_origination(store, world, pursued):
    mix = interest.provenance_mix(store)
    assert mix["externally_dominated"]
    share = interest.origination_share(store)
    assert share["interest_originated"] == 1
    assert share["share"] == 1.0


def test_at_least_one_interest_is_retired_for_producing_nothing(store, world, pursued):
    """A register that only grows has not been demonstrated to do anything."""
    notices.notice_over_span(
        store,
        "notice:n2",
        world.artifact("patents"),
        "the apparatus is said to produce a net directional thrust",
        "the phrasing is careful in a way that is itself interesting",
    )
    interest.form_interest(
        store,
        interest_id="interest:idle",
        subject="hedged phrasing in patent abstracts",
        rationale="it might indicate something; it might not",
        notice_ids=("notice:n2",),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
        opened_at="2026-06-01T00:00:00",
    )
    stale = interest.unproductive(store, NOW)
    assert stale == ("interest:idle",)
    interest.retire_interest(store, "interest:idle", "ninety days, no investigation, no essay")

    register = interest.interest_register(store)
    assert any(entry.retired and entry.retirement_reason for entry in register)
    assert any(entry.productive for entry in register)


# ---------------------------------------------------------------------------
# The gate, adversarially
# ---------------------------------------------------------------------------


def test_the_behaviour_this_gate_credits_survives_the_simpler_explanation(store, world, pursued):
    """A gate that credits initiative without asking whether retrieval order
    would explain it is a gate that can be passed by a sort."""
    review = checks.simpler_explanation_review(store, "interest:i1")
    assert review["credited"], review["cheaper_explanations"]
    assert not any(
        item["explanation"] == "the diet" and item["holds"]
        for item in review["cheaper_explanations"]
    )
    recorded = store.one("SELECT * FROM self_checks WHERE kind = 'simpler_explanation'")
    assert "survives the review" in recorded["finding"]


def test_an_interest_that_is_really_the_diet_talking_does_not_survive(store, world):
    """The same review, run against something it should not credit."""
    notices.notice_over_span(
        store,
        "notice:n9",
        world.artifact("harbour"),
        "Pilot describes object over Coral Ridge",
        "the headline names the subject the catalog is full of",
    )
    interest.form_interest(
        store,
        interest_id="interest:diet",
        subject="uap and aerospace anomalies",
        rationale="it keeps coming up",
        notice_ids=("notice:n9",),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    review = checks.simpler_explanation_review(store, "interest:diet")
    assert not review["credited"]


def test_the_gate_in_one_pass(store, world, pursued):
    """Everything Gate 4A asks for, asserted together."""
    claim, assessment = pursued

    # An investigation nobody asked for, pursued through the ordinary lanes.
    investigation = store.one("SELECT * FROM investigations WHERE origin = 'interest'")
    assert investigation is not None
    assert assessment.state is AssessmentState.INDETERMINATE

    # An essay about what it found, reporting against what it wanted.
    essay = essay_from_interest(
        store, interest_id="interest:i1", essay_id="essay:gate", intended_conclusion="supported"
    )
    assert essay.outcome == "changed"

    # A contradicted expectation, retained as a surprise, cited by a change.
    outcome = consequence.confirm_from_evidence(
        store, outcome_id="outcome:gate", expectation_id="expectation:e1", claim_id=claim
    )
    consequence.record_surprise(
        store,
        surprise_id="surprise:gate",
        expectation_id="expectation:e1",
        outcome_id=outcome,
        divergence="expected corroboration; found a competent absence",
        fits_live_interest=True,
    )
    consequence.record_consequence(
        store,
        consequence_id="consequence:gate",
        expectation_id="expectation:e1",
        outcome_id=outcome,
        score="-1",
        changed="interest_priority",
        change_cites="consequence:gate lowered interest:i1",
    )

    # The register reports what it caused, and the review was run against it.
    assert interest.origination_share(store)["interest_originated"] >= 1
    assert interest.provenance_mix(store)["externally_dominated"]
    assert checks.simpler_explanation_review(store, "interest:i1")["credited"]

    # And nothing about any of it reached an assessment: the state came from
    # the lanes and the edges, under the policy version, as it would have
    # without an interest in the world.
    assert assessment.policy_version
    assert assessment.explanation.startswith("every required evidence lane")
