"""Candidates for the three open slots: surveyed, and not chosen."""

from __future__ import annotations

import collections

import pytest

from newz.acquisition.fetcher import FetchPolicy
from newz.acquisition.urlpolicy import inspect_url
from newz.pilot import openings, seeds


def test_the_three_slots_this_surveyed_are_now_filled():
    assert seeds.gaps()["open_slots"]["slots"] == []
    assert set(openings.recommended()) == set(openings.SLOTS)


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


def test_each_recommendation_holds_exactly_one_slot():
    """A second slot from a publisher already read is not an independent basis."""
    held = collections.Counter(seed.publisher for seed in seeds.SEEDS)
    for candidate in openings.recommended().values():
        assert held[candidate.publisher] == 1, candidate.publisher


def test_only_the_recommended_candidates_reached_the_slate():
    """The alternatives stay as the record of what was considered."""
    urls = {seed.url for seed in seeds.SEEDS}
    taken = {c.url for c in openings.CANDIDATES if c.url in urls}
    assert taken == {c.url for c in openings.recommended().values()}


def test_the_report_says_the_approved_sources_still_have_unread_terms():
    report = openings.report()
    assert report["approved"] == "2026-09-05"
    assert "retention terms are still unread" in report["note"]
    assert any("cannot carry a contradiction" in f for f in report["findings"])


def test_the_report_says_what_declined_and_what_was_a_bad_guess():
    report = openings.report()
    assert report["declined"] and report["wrong_path"]
    assert report["reached"] == len(openings.reachable())
    assert any("our error" in finding for finding in report["findings"])
