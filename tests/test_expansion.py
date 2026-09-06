"""Growing the catalogue, and the two ways a bigger slate is a worse one."""

from __future__ import annotations

import pytest

from newz.pilot.catalog_review import REQUIRED_SLOTS
from newz.pilot.expansion import (
    TARGET_SIZE,
    cap_conflicts,
    nearest_symmetrical,
    plan,
    survey,
    symmetrical_sizes,
    symmetry,
)
from newz.pilot.modes import DeploymentMode
from newz.pilot.prescription import (
    CONTESTED_THRESHOLD,
    SKEPTICAL,
    SLATE_SIZE,
    bucket_allocation,
    prescribe,
    prescription_report,
    topic_allocation,
)

# ---------------------------------------------------------------------------
# The two tables are one distribution
# ---------------------------------------------------------------------------


def test_the_bucket_shares_reproduce_the_stated_slot_counts():
    """SPEC 5.1's percentages and 5.2's counts are the same thing said twice.

    This is what makes a slate larger than twenty derivable at all: the
    specification fixes a distribution and states one instance of it.
    """
    assert bucket_allocation(SLATE_SIZE)[0] == REQUIRED_SLOTS


def test_the_derivation_is_shown_for_both_tables():
    report = prescription_report(SLATE_SIZE)
    assert any("18% of 20 is 3.60" in line for line in report["working"])
    assert any("30% of 20 is 6.00" in line for line in report["working"])
    assert any("largest remainder" in line for line in report["working"])


def test_the_pilot_slate_is_unchanged_and_provably_best():
    report = prescription_report(SLATE_SIZE)
    assert report["proven_optimal"], report["shortfall"]
    assert report["score"] == report["ceiling"]
    assert len(prescribe(SLATE_SIZE)) == SLATE_SIZE


@pytest.mark.parametrize("size", [20, 24, 30, 40, 52, 60])
def test_every_size_serves_what_can_be_served(size):
    """The three terms that carry the specification reach their own ceiling."""
    report = prescription_report(size)
    assert report["score"][:3] == report["ceiling"][:3], report["shortfall"]
    assert len(prescribe(size)) == size


@pytest.mark.parametrize("size", [20, 30, 52])
def test_a_slate_of_any_size_covers_every_topic_and_bucket(size):
    allocation, _ = topic_allocation(size)
    slots, _ = bucket_allocation(size)
    assert all(count > 0 for count in allocation.values())
    assert all(count > 0 for count in slots.values())
    assert sum(allocation.values()) == sum(slots.values()) == size


# ---------------------------------------------------------------------------
# A larger slate can refute less
# ---------------------------------------------------------------------------


def test_twenty_can_contradict_everything_it_takes_seriously():
    whole = symmetry(20)
    assert whole.whole
    assert len(whole.contested) == whole.skeptical_slots == 3


def test_thirty_cannot_and_says_which():
    """Ten more reviewed sources, half the capacity to refute anything."""
    thin = symmetry(30)
    assert not thin.whole
    assert len(thin.contested) == 8
    assert thin.skeptical_slots == 4
    assert thin.unserved == 4
    assert "nothing in the diet can contradict" in thin.detail()


def test_the_slate_does_not_recover_until_fifty_one():
    """A property of the specification's numbers, not of the solver."""
    assert symmetrical_sizes(20, 60) == (20, *range(51, 61))
    assert nearest_symmetrical(30) == (20, 51)


def test_the_ceiling_itself_drops_rather_than_the_search_failing():
    """The proof it is the specification and not the assignment.

    If a better assignment existed, the bound would still be eight.
    """
    assert prescription_report(30)["ceiling"][1] == 4
    assert prescription_report(30)["score"][1] == 4
    assert prescription_report(20)["ceiling"][1] == 8


def test_a_topic_below_the_threshold_is_not_counted_as_unserved():
    """Symmetry applies to what the slate reads seriously."""
    allocation, _ = topic_allocation(20)
    below = {topic for topic, n in allocation.items() if n < CONTESTED_THRESHOLD}
    assert below
    assert not (below & set(symmetry(20).contested))


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


def test_growing_into_the_trough_is_planned_and_reported_rather_than_refused():
    """Enabling a source is the operator's; describing the cost is not."""
    grown = plan(30)
    assert len(grown.added) == 10
    assert not grown.safe
    assert "symmetry" in grown.findings[0]
    assert "20 and 51" in grown.findings[0]
    assert "the slate of 20 it replaces served all of its own" in grown.findings[0]


def test_growing_past_the_trough_costs_nothing():
    grown = plan(52)
    assert grown.safe, grown.findings
    assert len(grown.added) == 32
    assert grown.symmetry.whole


def test_the_recorded_target_is_the_smallest_size_that_keeps_symmetry():
    """51, chosen 2026-09-05. Nothing between 21 and 50 holds."""
    assert TARGET_SIZE == 51
    assert symmetry(TARGET_SIZE).whole
    assert symmetrical_sizes(21, 50) == ()
    assert plan(TARGET_SIZE).safe


def test_expanding_before_gate_5_is_reported_as_replacing_the_pilot():
    """Expansion is a Phase 6 deliverable; the gate counts routes over twenty."""
    early = plan(TARGET_SIZE, mode=DeploymentMode.PILOT)
    assert not early.safe
    assert any("replaces what the gate measures" in finding for finding in early.findings)
    # And staying at the pilot size says nothing, because nothing is happening.
    assert plan(SLATE_SIZE, mode=DeploymentMode.PILOT).safe


def test_the_added_slots_extend_the_slate_rather_than_replacing_it():
    grown = plan(30)
    target = prescribe(30)
    assert grown.added == target[20:]
    assert {spec.index for spec in grown.added} == set(range(20, 30))


def test_expansion_only_grows():
    with pytest.raises(ValueError, match="grows a slate"):
        plan(10, from_size=20)


# ---------------------------------------------------------------------------
# A catalogue that cannot be read as written
# ---------------------------------------------------------------------------


def test_a_publisher_holding_more_slots_than_the_read_cap_allows_is_reported():
    slate = {index: ("wide.example" if index < 8 else f"other{index}.example") for index in range(20)}
    conflicts = cap_conflicts(slate, 20, DeploymentMode.PRODUCTION)
    assert len(conflicts) == 1
    assert "wide.example holds 8 of 20 slots (40%)" in conflicts[0]
    assert "10% read cap in production" in conflicts[0]


def test_the_pilot_cap_is_looser_than_the_production_one():
    slate = {index: ("wide.example" if index < 3 else f"other{index}.example") for index in range(20)}
    assert cap_conflicts(slate, 20, DeploymentMode.PRODUCTION)  # 15% > 10%
    assert not cap_conflicts(slate, 20, DeploymentMode.PILOT)  # 15% < 20%


def test_fixture_mode_has_no_cap_to_conflict_with():
    slate = dict.fromkeys(range(20), "only.example")
    assert cap_conflicts(slate, 20, DeploymentMode.FIXTURE) == ()


def test_a_conflicting_slate_is_reported_on_the_plan():
    grown = plan(
        52,
        publishers_by_slot=dict.fromkeys(range(52), "only.example"),
        mode=DeploymentMode.PRODUCTION,
    )
    assert not grown.safe
    assert any("only.example" in finding for finding in grown.findings)


# ---------------------------------------------------------------------------
# The operator's view
# ---------------------------------------------------------------------------


def test_the_survey_shows_where_the_trough_is():
    figures = survey()
    thirty = next(row for row in figures["sizes"] if row["size"] == 30)
    assert not thirty["whole"]
    assert 20 in figures["symmetrical"]
    assert 30 not in figures["symmetrical"]
    assert figures["contested_threshold"] == CONTESTED_THRESHOLD
    assert figures["caps"]["production"] == 0.10


def test_the_skeptical_bucket_is_the_one_that_runs_out():
    slots, _ = bucket_allocation(30)
    allocation, _ = topic_allocation(30)
    assert slots[SKEPTICAL] < len(allocation)
