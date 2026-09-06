"""The proposed URLs: every one addressable, every claim about them honest."""

from __future__ import annotations

import pytest

from newz.acquisition.fetcher import FetchPolicy
from newz.acquisition.urlpolicy import inspect_url
from newz.pilot import repoint, seeds


def test_every_proposal_names_a_source_in_the_slate():
    """A proposal for a publisher nobody reads is a proposal about nothing."""
    slate = {seed.publisher for seed in seeds.SEEDS}
    proposed = {proposal.publisher for proposal in repoint.PROPOSALS}
    assert proposed == slate


def test_every_proposal_starts_from_the_url_the_slate_actually_has():
    """A `was` that drifted from the slate would make the diff a fiction."""
    current = {seed.publisher: seed.url for seed in seeds.SEEDS}
    for proposal in repoint.PROPOSALS:
        assert proposal.was == current[proposal.publisher], proposal.publisher


@pytest.mark.parametrize("proposal", repoint.PROPOSALS, ids=lambda p: p.publisher)
def test_every_proposed_url_is_one_the_fetcher_would_accept(proposal):
    verdict = inspect_url(proposal.now, FetchPolicy().url)
    assert verdict.allowed, (proposal.publisher, verdict.detail)


def test_the_survey_moved_the_labels_rather_than_the_labels_surviving_it():
    """Every changed URL was fetched, and now says what came back."""
    for proposal in repoint.changes():
        assert proposal.confidence in {repoint.OBSERVED, repoint.REFUTED}, proposal.publisher
    assert len(repoint.changes()) == repoint.SURVEY["surveyed"]
    assert len(repoint.applicable()) == repoint.SURVEY["confirmed"]
    assert len(repoint.refuted()) == repoint.SURVEY["refuted_count"]


def test_a_refuted_proposal_is_kept_rather_than_deleted():
    """A proposal that was checked and failed is more use than one that vanished."""
    assert repoint.refuted()
    for proposal in repoint.refuted():
        assert proposal.changed, "it is the change that was refuted"
        assert proposal.publisher in repoint.SURVEY["does_not"]
        assert repoint.SURVEY["does_not"][proposal.publisher]


def test_nothing_refuted_is_offered_as_applicable():
    assert not (set(repoint.applicable()) & set(repoint.refuted()))
    for proposal in repoint.applicable():
        assert proposal.publisher in repoint.SURVEY["serves_what_was_claimed"]


def test_an_unchanged_url_is_justified_rather_than_silent():
    for proposal in repoint.PROPOSALS:
        if not proposal.changed:
            assert proposal.why, proposal.publisher


def test_what_cannot_be_fixed_by_a_path_is_not_given_a_path():
    """Proposing a path that will parse to nothing is worse than saying so."""
    stuck = repoint.blocked()
    assert [proposal.publisher for proposal in stuck] == [
        "United States Patent and Trademark Office"
    ]
    for proposal in stuck:
        assert not proposal.changed
        assert "source decision rather than a URL fix" in proposal.why


def test_the_report_says_what_was_checked_and_what_failed():
    report = repoint.report()
    assert "Surveyed on 2026-09-05" in report["note"]
    assert report["changed"] + report["unchanged"] == len(repoint.PROPOSALS)
    assert set(report["refuted"]) == {p.publisher for p in repoint.refuted()}
    assert set(report["applicable"]) == {p.publisher for p in repoint.applicable()}


def test_the_slate_is_not_changed_by_a_proposal():
    """Approving these is the operator's; drafting them is not."""
    current = {seed.url for seed in seeds.SEEDS}
    changed = {proposal.now for proposal in repoint.changes()}
    assert not (changed & current), "a proposal that already applied itself is not a proposal"


# ---------------------------------------------------------------------------
# What the survey found that the proposals were not about
# ---------------------------------------------------------------------------


def test_a_source_already_in_the_slate_may_never_be_read():
    """Skeptical Inquirer disallows `/`, which is the URL the slate holds.

    It was added before the robots check existed and has never been fetched
    under it, so the slot has been effectively open the whole time.
    """
    finding = next(
        line for line in repoint.SURVEY["findings"] if "Skeptical Inquirer" in line
    )
    assert "may never read" in finding
    assert "effectively open" in finding
    current = {seed.publisher: seed.url for seed in seeds.SEEDS}
    assert current["Skeptical Inquirer (Center for Inquiry)"] == "https://skepticalinquirer.org/"


def test_stated_rules_and_enforced_ones_are_recorded_as_different_facts():
    """Royal Society: robots.txt permits the path and the server refuses it."""
    finding = next(
        line for line in repoint.SURVEY["findings"] if "Royal Society" in line
    )
    assert "robots.txt permits the path and the server refuses anyway" in finding


def test_the_role_heuristic_finding_travelled_into_a_change():
    """`TRUE_NORTH.md`: a failure is answered by a change that cites it."""
    from newz.pilot.slots import ROLE_RULES

    markers = {marker for marker, _, _ in ROLE_RULES}
    assert "archive" not in markers, "a page's organisation is not a publisher's role"
    assert {"archival record", "historical archive"} <= markers
