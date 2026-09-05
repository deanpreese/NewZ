"""Decisions, surprise, consequence, escalation, and the four checks."""

from __future__ import annotations

import pytest

from newz.domain.enums import DecisionOutcome, OutcomeStatus
from newz.reckoning import checks, consequence, decisions, escalation
from tests import world as world_module


@pytest.fixture
def world(store):
    return world_module.build(store)


def _expect(store, expectation_id="expectation:e1", expected="the registry will hold a record"):
    return decisions.record_expectation(
        store,
        expectation_id=expectation_id,
        subject="claim:registry-0",
        expected=expected,
        recorded_before="opening the investigation",
    )


# ---------------------------------------------------------------------------
# Decisions
# ---------------------------------------------------------------------------


def test_a_decision_records_what_else_was_on_the_table(store):
    _expect(store)
    recorded = decisions.record_decision(
        store,
        decision_id="decision:d1",
        outcome=DecisionOutcome.ORIGINATE,
        subject="the Coral Ridge radar question",
        alternatives=("leave it as a claimant report", "wait for the counterpart read"),
        decided_by="interest:i1",
        reason="the registry is reachable and the question is narrow",
        expectation_id="expectation:e1",
        confidence="moderate",
    )
    assert recorded.alternatives
    assert decisions.decisions(store)[0]["alternatives"] == list(recorded.alternatives)


def test_one_option_is_not_a_decision(store):
    with pytest.raises(ValueError, match="alternatives considered"):
        decisions.record_decision(
            store,
            decision_id="decision:d1",
            outcome=DecisionOutcome.CONTINUE,
            subject="s",
            alternatives=(),
            decided_by="rule",
            reason="a reason",
        )


def test_a_deferral_says_what_would_bring_it_back(store):
    with pytest.raises(ValueError, match="bring it back"):
        decisions.record_decision(
            store,
            decision_id="decision:d1",
            outcome=DecisionOutcome.DEFER,
            subject="s",
            alternatives=("act now",),
            decided_by="rule",
            reason="not yet",
        )
    decisions.record_decision(
        store,
        decision_id="decision:d1",
        outcome=DecisionOutcome.DEFER,
        subject="s",
        alternatives=("act now",),
        decided_by="rule",
        reason="not yet",
        re_raise_condition="when the counterpart task closes",
    )


def test_declining_and_deferring_appear_as_decisions_not_absences(store):
    for index, outcome in enumerate((DecisionOutcome.DECLINE, DecisionOutcome.DEFER)):
        decisions.record_decision(
            store,
            decision_id=f"decision:d{index}",
            outcome=outcome,
            subject=f"subject {index}",
            alternatives=("the other thing",),
            decided_by="rule",
            reason="a reason",
            re_raise_condition="a condition" if outcome is DecisionOutcome.DEFER else "",
        )
    assert len(decisions.declined_and_deferred(store)) == 2


def test_an_expectation_cannot_be_revised_after_the_fact(store):
    import sqlite3

    _expect(store)
    with pytest.raises(sqlite3.IntegrityError, match="recollection"), store.write() as connection:
        connection.execute("UPDATE expectations SET expected = 'what actually happened'")


# ---------------------------------------------------------------------------
# Surprise and consequence
# ---------------------------------------------------------------------------


def test_an_outcome_must_name_where_it_was_confirmed(store):
    _expect(store)
    with pytest.raises(consequence.SelfGrading, match="not a source"):
        consequence.confirm_outcome(
            store,
            outcome_id="outcome:o1",
            expectation_id="expectation:e1",
            observed="it went well",
            confirmation_source="",
        )


def test_an_outcome_can_be_confirmed_from_the_evidence_graph(store, world):
    from newz.evidence.assess import assess_claim

    claim = world.claim("registry", "radar")
    assess_claim(store, claim, "assessment:a1")
    _expect(store)
    consequence.confirm_from_evidence(
        store, outcome_id="outcome:o1", expectation_id="expectation:e1", claim_id=claim
    )
    row = store.one("SELECT * FROM confirmed_outcomes WHERE id = 'outcome:o1'")
    assert row["status"] == "confirmed"
    assert "evidence graph" in row["confirmation_source"]


def test_an_outcome_with_nothing_outside_it_is_unverifiable(store, world):
    _expect(store)
    consequence.confirm_from_evidence(
        store, outcome_id="outcome:o1", expectation_id="expectation:e1", claim_id="claim:absent"
    )
    assert (
        store.one("SELECT status FROM confirmed_outcomes")["status"]
        == OutcomeStatus.UNVERIFIABLE.value
    )


def test_an_unverifiable_outcome_feeds_no_consequence(store):
    _expect(store)
    consequence.confirm_outcome(
        store,
        outcome_id="outcome:o1",
        expectation_id="expectation:e1",
        observed="nothing could be checked",
        confirmation_source="",
        status=OutcomeStatus.UNVERIFIABLE,
    )
    with pytest.raises(consequence.SelfGrading, match="feeds no consequence"):
        consequence.record_consequence(
            store,
            consequence_id="consequence:c1",
            expectation_id="expectation:e1",
            outcome_id="outcome:o1",
            score="-1",
            changed="interest_priority",
            change_cites="consequence:c1",
        )


def test_a_surprise_that_fits_no_live_interest_is_still_retained(store):
    """A system that retains only what it expected learns the shape of its own
    expectations."""
    _expect(store)
    consequence.confirm_outcome(
        store,
        outcome_id="outcome:o1",
        expectation_id="expectation:e1",
        observed="the registry held nothing at all",
        confirmation_source="the registry index",
    )
    consequence.record_surprise(
        store,
        surprise_id="surprise:s1",
        expectation_id="expectation:e1",
        outcome_id="outcome:o1",
        divergence="expected a record; found an explicit absence",
        fits_live_interest=False,
    )
    assert len(consequence.surprises(store, only_unfitting=True)) == 1


def test_a_consequence_must_change_something_from_the_closed_list(store):
    _expect(store)
    consequence.confirm_outcome(
        store,
        outcome_id="outcome:o1",
        expectation_id="expectation:e1",
        observed="observed",
        confirmation_source="the registry index",
    )
    with pytest.raises(ValueError, match="learning reaching a conclusion"):
        consequence.record_consequence(
            store,
            consequence_id="consequence:c1",
            expectation_id="expectation:e1",
            outcome_id="outcome:o1",
            score="-1",
            changed="promotion_threshold",
            change_cites="consequence:c1",
        )


def test_a_consequence_cites_itself_as_the_reason_for_the_change(store):
    _expect(store)
    consequence.confirm_outcome(
        store,
        outcome_id="outcome:o1",
        expectation_id="expectation:e1",
        observed="observed",
        confirmation_source="the registry index",
    )
    with pytest.raises(ValueError, match="cites itself"):
        consequence.record_consequence(
            store,
            consequence_id="consequence:c1",
            expectation_id="expectation:e1",
            outcome_id="outcome:o1",
            score="-1",
            changed="interest_priority",
            change_cites="",
        )
    consequence.record_consequence(
        store,
        consequence_id="consequence:c1",
        expectation_id="expectation:e1",
        outcome_id="outcome:o1",
        score="-1",
        changed="interest_priority",
        change_cites="consequence:c1 lowered interest:i1 from 5 to 3",
    )
    assert consequence.calibration(store)["changes_by_kind"] == {"interest_priority": 1}


def test_comparison_finds_the_divergence(store):
    _expect(store, expected="a record exists")
    consequence.confirm_outcome(
        store,
        outcome_id="outcome:o1",
        expectation_id="expectation:e1",
        observed="no record exists in the window searched",
        confirmation_source="the registry index",
    )
    diverged, detail = consequence.compare(store, "expectation:e1", "outcome:o1")
    assert diverged
    assert "expected" in detail


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------


def test_an_escalation_stays_open_until_a_change_cites_it(store):
    escalation.record_escalation(
        store,
        escalation_id="escalation:e1",
        route="risk_lowering",
        attempted="tried to reclassify R3 to R1 without an operator",
        detected_by="the risk guard",
    )
    assert len(escalation.open_escalations(store)) == 1
    with pytest.raises(ValueError, match="records what changed"):
        escalation.link_change(store, "escalation:e1", "")
    escalation.link_change(
        store, "escalation:e1", "the reclassification path now requires an OperatorAction"
    )
    assert escalation.open_escalations(store) == ()


def test_re_deriving_a_refused_output_is_detected_as_an_indirect_route(store, world):
    """The natural way to bypass a refusal is never to ask again."""
    with store.write() as connection:
        connection.execute(
            "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
            "withdrawn, recorded_at) VALUES ('claim:x', 'attribution', 'w', 'R1', NULL, NULL, 0, "
            "datetime('now'))"
        )
        connection.execute(
            "INSERT INTO card_revisions (id, claim_id, revision, content_json, content_hash, "
            "policy_version, code_version, risk, state, live, built_at) "
            "VALUES ('card:r1', 'claim:x', 1, '{}', 'samehash', '1.0.0', '0.1.0', 'R1', "
            "'reported', 1, datetime('now'))"
        )
        for identifier, granted in (("clearance:refused", 0), ("clearance:granted", 1)):
            connection.execute(
                "INSERT INTO clearances (id, card_revision_id, content_hash, class, granted, "
                "refusal_reason, policy_version, operator_actor, cleared_at) "
                "VALUES (?, 'card:r1', 'samehash', 'claim_card:R1', ?, NULL, '1.0.0', NULL, "
                "datetime('now'))",
                (identifier, granted),
            )
    found = escalation.detect_escalation(store)
    assert any(item.route == "refusal_re_derivation" for item in found)
    assert escalation.open_escalations(store)


def test_publishing_to_an_audience_nobody_enabled_is_detected(store, world):
    with store.write() as connection:
        connection.execute(
            "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
            "withdrawn, recorded_at) VALUES ('claim:x', 'attribution', 'w', 'R1', NULL, NULL, 0, "
            "datetime('now'))"
        )
        connection.execute(
            "INSERT INTO card_revisions (id, claim_id, revision, content_json, content_hash, "
            "policy_version, code_version, risk, state, live, built_at) "
            "VALUES ('card:r1', 'claim:x', 1, '{}', 'h', '1.0.0', '0.1.0', 'R1', 'reported', 1, "
            "datetime('now'))"
        )
        connection.execute(
            "INSERT INTO clearances (id, card_revision_id, content_hash, class, granted, "
            "refusal_reason, policy_version, operator_actor, cleared_at) "
            "VALUES ('clearance:c1', 'card:r1', 'h', 'claim_card:R1', 1, NULL, '1.0.0', NULL, "
            "datetime('now'))"
        )
        connection.execute(
            "INSERT INTO publications (id, card_revision_id, clearance_id, audience, status, "
            "attempted_at) VALUES ('publication:p1', 'card:r1', 'clearance:c1', 'public', "
            "'attempted', datetime('now'))"
        )
    found = escalation.detect_escalation(store)
    assert any(item.route == "envelope_widening" for item in found)


# ---------------------------------------------------------------------------
# The four checks
# ---------------------------------------------------------------------------


def test_the_scored_figures_are_the_operators_and_not_the_systems(store, world):
    system = checks.system_visible_report(store)
    operator = checks.operator_report(store)
    for metric in ("interest_origination_share", "register_provenance_mix", "calibration"):
        assert metric in operator
        assert metric not in system
    assert "diet" in system
    assert "constraints" in system


def test_the_simpler_explanation_is_checked_before_initiative_is_credited(store, world):
    from newz.attention import interest, notices

    notices.notice_over_span(
        store,
        "notice:n1",
        world.artifact("harbour"),
        "Pilot describes object over Coral Ridge",
        "the headline names a specific sector",
    )
    interest.form_interest(
        store,
        interest_id="interest:i1",
        subject="uap and aerospace anomalies",
        rationale="it keeps coming up",
        notice_ids=("notice:n1",),
        diet_epoch_id="epoch:1",
        topic_targets={"uap_and_aerospace_anomalies": "18%"},
    )
    review = checks.simpler_explanation_review(store, "interest:i1")
    assert not review["credited"]
    reasons = {item["explanation"] for item in review["cheaper_explanations"] if item["holds"]}
    assert "the diet" in reasons
    assert "retrieval order" in reasons


def test_an_interest_that_survives_the_review_is_credited(store, world):
    from newz.attention import interest, notices

    # Deep in the document rather than the headline, from the first source read
    # rather than the last, and naming something narrower than any topic target.
    notices.notice_over_span(
        store,
        "notice:n1",
        world.artifact("harbour"),
        "It held station off the right wing",
        "a station-keeping manoeuvre is a specific, checkable claim",
    )
    interest.form_interest(
        store,
        interest_id="interest:i2",
        subject="station-keeping manoeuvres in pilot accounts",
        rationale="a specific manoeuvre, not a subject the diet asked for",
        notice_ids=("notice:n1",),
        diet_epoch_id="epoch:1",
        topic_targets={"uap_and_aerospace_anomalies": "18%"},
    )
    review = checks.simpler_explanation_review(store, "interest:i2")
    assert review["credited"], review["cheaper_explanations"]
    assert any(
        item["explanation"] == "recency in the diet" and not item["holds"]
        for item in review["cheaper_explanations"]
    )


def test_a_reversal_with_no_new_evidence_is_recorded_as_pressure(store):
    result = checks.record_reversal(
        store,
        reversal_id="check:rev1",
        subject="whether the sighting is worth pursuing",
        from_position="not worth pursuing",
        to_position="worth pursuing",
    )
    assert result["pressure"]
    with_evidence = checks.record_reversal(
        store,
        reversal_id="check:rev2",
        subject="the same question",
        from_position="worth pursuing",
        to_position="not worth pursuing",
        new_evidence="the registry search came back empty and competent",
    )
    assert not with_evidence["pressure"]

    report = checks.mirroring_report(store)
    assert report["reversals"] == 2
    assert report["reversals_recorded_as_pressure"] == 1


def test_the_agreement_rate_with_the_operator_is_reported(store):
    for index, agreed in enumerate((True, True, False)):
        checks.record_position(
            store,
            position_id=f"check:p{index}",
            subject=f"subject {index}",
            position="a position",
            operator_position="the operator's position",
            agreed=agreed,
        )
    report = checks.mirroring_report(store)
    assert report["positions_recorded"] == 3
    assert report["agreement_rate"] == pytest.approx(2 / 3)


def test_the_system_can_read_what_it_may_not_do_and_why(store, world):
    constraints = checks.constraints(store)
    text = " ".join(item["constraint"] for item in constraints)
    assert "interest reaches attention" in text
    assert "self-originated investigations" in text
    assert "fair representation" in text
    for item in constraints:
        assert item["why"] and item["shape"]
