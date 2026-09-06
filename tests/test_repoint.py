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


def test_a_guess_is_labelled_a_guess():
    """The failure this prevents: a plausible URL read as a checked one."""
    assert repoint.needs_checking(), "some of these are guesses and say so"
    for proposal in repoint.needs_checking():
        assert proposal.confidence == repoint.GUESS
        assert proposal.changed, "an unchanged URL is not a guess about anything"


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


def test_the_report_does_not_present_proposals_as_findings():
    report = repoint.report()
    assert "Proposals, not findings" in report["note"]
    assert report["changed"] + report["unchanged"] == len(repoint.PROPOSALS)
    assert set(report["guesses"]) == {
        proposal.publisher for proposal in repoint.needs_checking()
    }


def test_the_slate_is_not_changed_by_a_proposal():
    """Approving these is the operator's; drafting them is not."""
    current = {seed.url for seed in seeds.SEEDS}
    changed = {proposal.now for proposal in repoint.changes()}
    assert not (changed & current), "a proposal that already applied itself is not a proposal"
