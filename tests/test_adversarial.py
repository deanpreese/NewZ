"""Admitting a source class to R2, and what makes a review adversarial."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.control.adversarial import (
    REVIEW_MONTHS,
    ReviewRefused,
    add_member,
    class_of_source,
    live_review,
    r2_admission_refusal,
    report,
    review_class,
    unreviewed_r2_sources,
    withdraw_review,
)
from newz.domain.enums import (
    EdgeRelation,
    IndependenceJustification,
    RiskTier,
)
from newz.evidence.assess import assess_claim
from newz.evidence.bases import record_basis, record_independence
from newz.evidence.edges import admit_edge
from newz.present.cards import build_card
from newz.publish.clearance import clear, refusal_conditions
from tests import world as world_module

NOW = datetime(2026, 9, 5, 12, 0, 0)
LATER = NOW + timedelta(days=365)
OPERATOR = "operator:dean"
CLASS = "national_science_publisher"


def _review(store, **overrides):
    fields = {
        "review_id": "review:r1",
        "source_class": CLASS,
        "reviewer": OPERATOR,
        "trusted_for": "papers it published, and the fact that it published them",
        "case_against": (
            "it reports on institutions that fund it, so a story it declines to run "
            "is invisible to us and reads as an absence of evidence"
        ),
        "answer": (
            "admitted for what it published and never for what it did not; the "
            "counterpart lane must find a second basis before anything promotes"
        ),
        "disqualifiers": (
            "a retraction it declined to publish, or a change of ownership to a party "
            "we would be reporting on"
        ),
        "expires_at": LATER,
    }
    fields.update(overrides)
    return review_class(store, **fields)


@pytest.fixture
def world(store):
    return world_module.build(store)


# ---------------------------------------------------------------------------
# What makes a review a review
# ---------------------------------------------------------------------------


def test_a_review_is_a_persons(store):
    with pytest.raises(ReviewRefused, match="a person's"):
        _review(store, reviewer="system")


@pytest.mark.parametrize("field", ["trusted_for", "case_against", "answer", "disqualifiers"])
def test_a_review_without_all_four_parts_is_not_adversarial(store, field):
    """A reviewer, a date and a verdict is the same shape either way.

    That record looks identical whether somebody argued about the class or
    nobody did, which is exactly the thing a review is meant to distinguish.
    """
    with pytest.raises(ReviewRefused, match=field):
        _review(store, **{field: "   "})


def test_an_answer_that_restates_the_case_against_does_not_meet_it(store):
    with pytest.raises(ReviewRefused, match="restates the case against"):
        _review(store, case_against="it is funded by the state", answer="it is funded by the state")


def test_a_recorded_review_keeps_its_reasoning(store):
    _review(store)
    with pytest.raises(Exception, match="withdraw it and record another"), store.write() as conn:
        conn.execute("UPDATE r2_class_reviews SET case_against = 'nothing much'")


def test_a_review_holds_until_it_expires_or_is_withdrawn(store):
    _review(store)
    assert live_review(store, CLASS, NOW) is not None
    assert live_review(store, CLASS, LATER + timedelta(days=1)) is None

    withdraw_review(store, "review:r1", "the ownership change in the disqualifiers", NOW)
    assert live_review(store, CLASS, NOW) is None


def test_withdrawing_a_review_records_why(store):
    _review(store)
    with pytest.raises(ValueError, match="records why"):
        withdraw_review(store, "review:r1", "  ", NOW)


# ---------------------------------------------------------------------------
# Membership is declared, never inferred
# ---------------------------------------------------------------------------


def test_the_system_cannot_widen_a_reviewed_class(store, world):
    """Otherwise the review covers whatever the system later decides to include."""
    revision = world.sources["kettleby"].revision.id
    with pytest.raises(ReviewRefused, match="declared by an operator"):
        add_member(store, CLASS, revision, "system")

    add_member(store, CLASS, revision, OPERATOR)
    assert class_of_source(store, revision) == CLASS


def test_a_source_in_no_class_belongs_to_no_review(store, world):
    assert class_of_source(store, world.sources["ardenne"].revision.id) == ""


# ---------------------------------------------------------------------------
# Where it bites: publication
# ---------------------------------------------------------------------------


@pytest.fixture
def r2_card(store, world):
    """A contested R2 claim carried to a rendered card."""
    with store.write() as connection:
        record_basis(connection, "basis:proto-4471", "experiment", "protocol:PROTO-4471", True)
        record_basis(connection, "basis:proto-5520", "experiment", "protocol:PROTO-5520", True)
        record_independence(
            connection,
            "independence:labs",
            "basis:proto-4471",
            "basis:proto-5520",
            IndependenceJustification.DISTINCT_EXPERIMENT,
            evidence="different laboratories",
        )
    claim = world.claim("kettleby", "signature")
    admit_edge(
        store,
        edge_id="edge:sup",
        assertion_id=world.assertion("kettleby", "effect"),
        claim_id=claim,
        relation=EdgeRelation.SUPPORTS,
        basis_id="basis:proto-4471",
        risk=RiskTier.R2,
    )
    admit_edge(
        store,
        edge_id="edge:con",
        assertion_id=world.assertion("ardenne", "no_effect"),
        claim_id=claim,
        relation=EdgeRelation.CONTRADICTS,
        basis_id="basis:proto-5520",
        risk=RiskTier.R2,
    )
    with store.write() as connection:
        connection.execute("UPDATE claims SET risk = 'R2' WHERE id = ?", (claim,))
    assess_claim(store, claim, "assessment:a1")
    revision, _ = build_card(store, claim, "card:r1")
    return claim, revision


def test_r2_output_is_refused_while_its_sources_are_unadmitted(store, world, r2_card):
    _claim, revision = r2_card
    refusals = {r.condition: r.detail for r in refusal_conditions(store, revision)}
    assert "r2_source_class_unreviewed" in refusals
    assert "in no reviewed class" in refusals["r2_source_class_unreviewed"]
    assert not clear(store, revision, "clearance:c1").granted


def test_admitting_every_source_behind_it_clears_the_refusal(store, world, r2_card):
    claim, revision = r2_card
    _review(store)
    for key in ("kettleby", "ardenne"):
        add_member(store, CLASS, world.sources[key].revision.id, OPERATOR)

    assert unreviewed_r2_sources(store, claim, NOW) == ()
    refusals = {r.condition for r in refusal_conditions(store, revision)}
    assert "r2_source_class_unreviewed" not in refusals


def test_one_unadmitted_source_is_enough_to_refuse(store, world, r2_card):
    """The claim rests on both, so admitting one admits half of it."""
    claim, _revision = r2_card
    _review(store)
    add_member(store, CLASS, world.sources["kettleby"].revision.id, OPERATOR)

    unreviewed = unreviewed_r2_sources(store, claim, NOW)
    assert len(unreviewed) == 1
    assert world.sources["ardenne"].revision.id in unreviewed[0]


def test_an_expired_review_stops_admitting(store, world, r2_card):
    claim, _revision = r2_card
    _review(store)
    for key in ("kettleby", "ardenne"):
        add_member(store, CLASS, world.sources[key].revision.id, OPERATOR)

    assert unreviewed_r2_sources(store, claim, NOW) == ()
    stale = unreviewed_r2_sources(store, claim, LATER + timedelta(days=1))
    assert len(stale) == 2
    assert all("no live review" in entry for entry in stale)


def test_the_rule_applies_at_r2_and_not_below(store, world, r2_card):
    claim, _revision = r2_card
    assert r2_admission_refusal(store, claim, RiskTier.R2.value, NOW)
    assert r2_admission_refusal(store, claim, RiskTier.R1.value, NOW) == ""
    assert r2_admission_refusal(store, claim, RiskTier.R0.value, NOW) == ""


def test_a_withdrawn_review_takes_its_class_out_again(store, world, r2_card):
    claim, _revision = r2_card
    _review(store)
    for key in ("kettleby", "ardenne"):
        add_member(store, CLASS, world.sources[key].revision.id, OPERATOR)
    assert unreviewed_r2_sources(store, claim, NOW) == ()

    withdraw_review(store, "review:r1", "it was bought by a party we report on", NOW)
    assert len(unreviewed_r2_sources(store, claim, NOW)) == 2


# ---------------------------------------------------------------------------
# The operator's view
# ---------------------------------------------------------------------------


def test_the_report_separates_what_holds_from_what_has_lapsed(store, world):
    _review(store)
    _review(store, review_id="review:r2", source_class="lapsed_class", expires_at=NOW - timedelta(days=1))
    add_member(store, CLASS, world.sources["kettleby"].revision.id, OPERATOR)

    figures = report(store, NOW)
    assert figures["live_classes"] == [CLASS]
    assert figures["expired_or_withdrawn"] == ["lapsed_class"]
    assert figures["members"] == {CLASS: 1}
    assert figures["review_months"] == REVIEW_MONTHS
    assert len(figures["reviews"]) == 2
