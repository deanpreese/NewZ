"""Candidates for the three open slots: surveyed, and not chosen."""

from __future__ import annotations

import pytest

from newz.acquisition.fetcher import FetchPolicy
from newz.acquisition.urlpolicy import inspect_url
from newz.pilot import openings, seeds


def test_a_candidate_is_proposed_for_every_open_slot():
    open_slots = {
        f"{slot['bucket']}/{slot['topic']}" for slot in seeds.gaps()["open_slots"]["slots"]
    }
    assert open_slots == set(openings.SLOTS)
    assert set(openings.recommended()) == open_slots


def test_a_wrong_path_is_not_reported_as_a_publisher_declining():
    """A 404 is our error; a 403 is their answer."""
    for candidate in openings.CANDIDATES:
        if candidate.outcome == openings.WRONG_PATH:
            assert "404" in candidate.note, candidate.publisher
        if candidate.outcome == openings.DECLINED:
            assert "403" in candidate.note, candidate.publisher


def test_every_publisher_that_404d_was_reachable_somewhere():
    """The lesson: probe the root before recording a source as unreachable."""
    reached = {c.publisher for c in openings.reachable()}
    for candidate in openings.CANDIDATES:
        if candidate.outcome == openings.WRONG_PATH:
            assert candidate.publisher in reached, candidate.publisher


@pytest.mark.parametrize("candidate", openings.CANDIDATES, ids=lambda c: f"{c.publisher}-{c.outcome}")
def test_every_candidate_url_is_one_the_fetcher_would_accept(candidate):
    assert inspect_url(candidate.url, FetchPolicy().url).allowed, candidate.url


def test_the_recommendation_for_psi_states_the_trade_rather_than_hiding_it():
    """It is one author, not an institution: a narrower basis than the slot lost."""
    psi = openings.recommended()[openings.SKEPTICAL_PSI]
    assert "One author rather than an institution" in psi.note
    assert psi.segments > 0


def test_no_recommended_publisher_is_already_in_the_slate():
    """A second slot from a publisher already read is not an independent basis."""
    held = {seed.publisher for seed in seeds.SEEDS}
    for candidate in openings.recommended().values():
        assert candidate.publisher not in held, candidate.publisher


def test_nothing_here_has_been_added_to_the_slate():
    """Surveyed, not chosen. Enabling a source is a diet decision."""
    urls = {seed.url for seed in seeds.SEEDS}
    assert not (urls & {c.url for c in openings.CANDIDATES})
    assert "Surveyed, not chosen" in openings.report()["note"]


def test_the_report_says_what_declined_and_what_was_a_bad_guess():
    report = openings.report()
    assert report["declined"] and report["wrong_path"]
    assert report["reached"] == len(openings.reachable())
    assert any("our error" in finding for finding in report["findings"])
