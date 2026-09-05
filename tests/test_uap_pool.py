"""The reviewed UAP pool: does the review hold together, and does it fit."""

from __future__ import annotations

import collections

import pytest

from newz.pilot import uap_pool
from newz.pilot.catalog_review import REQUIRED_SLOTS
from newz.pilot.prescription import prescribe
from newz.pilot.seeds import PINS


def test_every_entry_reaches_a_verdict_and_says_why():
    for entry in uap_pool.REVIEW:
        assert entry.verdict in (uap_pool.CANDIDATE, uap_pool.LEAD_ONLY, uap_pool.DECLINED)
        assert entry.note or entry.verdict == uap_pool.CANDIDATE
        if entry.verdict == uap_pool.CANDIDATE:
            assert entry.bucket in REQUIRED_SLOTS, entry.name
            assert entry.note, entry.name


def test_a_candidate_carries_a_url_to_survey():
    """A candidate with no endpoint cannot be checked, so it is not a candidate."""
    for entry in uap_pool.REVIEW:
        if entry.verdict == uap_pool.CANDIDATE and entry.url:
            assert entry.url.startswith("http"), entry.name


def test_the_pool_is_competing_for_four_slots(store):
    uap_slots = [
        spec for spec in prescribe(pins=PINS) if spec.topic == "uap_and_aerospace_anomalies"
    ]
    assert len(uap_slots) == 4
    assert uap_pool.summary()["uap_slots_available"] == 4
    assert uap_pool.summary()["candidates"] > 4  # a selection problem, not an inclusion one


def test_one_editorial_act_is_one_source():
    """MUFON's case system and a map rendering it would count one report twice."""
    grouped = collections.Counter(
        entry.independence_group for entry in uap_pool.REVIEW if entry.independence_group
    )
    assert grouped[uap_pool.GROUP_MUFON] >= 2
    stalker = next(e for e in uap_pool.REVIEW if e.name == "UFO Stalker")
    assert stalker.verdict == uap_pool.DECLINED
    assert stalker.independence_group == uap_pool.GROUP_MUFON
    mufon = next(e for e in uap_pool.REVIEW if e.name == "MUFON")
    assert mufon.independence_group == uap_pool.GROUP_MUFON


def test_a_shared_upstream_document_is_a_derivation_not_a_group():
    """Three archives holding one Blue Book document are three publications of one
    record. Grouping the archives would be wrong: they hold distinct originals too."""
    archives = [e for e in uap_pool.REVIEW if e.name in ("NICAP", "CUFOS", "Project 1947")]
    assert len(archives) == 3
    assert all(entry.independence_group is None for entry in archives)
    assert all(entry.upstream for entry in archives)
    assert "derivation link" in uap_pool.summary()["derivation_note"]


def test_aggregators_are_leads_rather_than_sources():
    """Every basis under an aggregator belongs to somebody else."""
    for name in ("UFO Casebook", "UFO Info", "StealthSkater Archives", "UFOevidence"):
        entry = next(e for e in uap_pool.REVIEW if e.name == name)
        assert entry.verdict in (uap_pool.LEAD_ONLY, uap_pool.DECLINED), name


def test_the_skeptical_entries_survive_at_the_highest_rate():
    """The finding worth arguing with: this list's most extractable material is
    the analysis that names its sources, not the case reports."""
    by_bucket = uap_pool.summary()["candidates_by_bucket"]
    assert len(by_bucket["skeptical_or_forensic"]) >= 4
    # And a skeptical entry that only argues is still refused.
    argument = next(e for e in uap_pool.REVIEW if e.name == "UFO Skeptic")
    assert argument.verdict == uap_pool.LEAD_ONLY
    assert "inference" in argument.note


def test_journalism_is_secondary_by_construction():
    for name in ("The War Zone", "The Debrief", "Open Minds"):
        entry = next(e for e in uap_pool.REVIEW if e.name == name)
        assert entry.verdict == uap_pool.LEAD_ONLY, name
    war_zone = next(e for e in uap_pool.REVIEW if e.name == "The War Zone")
    # Named as good, and still a lead. The quality is not the question.
    assert "best-sourced" in war_zone.note


def test_advocacy_is_recorded_as_a_claimant_rather_than_dismissed(store):
    """TRUE_NORTH asks for a claimant's strongest actual position, not a caricature."""
    for name in ("Paradigm Research Group", "To the Stars... Academy (TTSA)"):
        entry = next(e for e in uap_pool.REVIEW if e.name == name)
        assert entry.bucket == "claimant_or_firsthand", name
        assert entry.verdict != uap_pool.DECLINED, name


@pytest.mark.parametrize(
    "name", ["Montalk.net", "UAP Theory", "The Mind Sublime", "UFOs as wildlife"]
)
def test_speculation_is_declined_with_a_reason_rather_than_ignored(name):
    entry = next(e for e in uap_pool.REVIEW if e.name == name)
    assert entry.verdict == uap_pool.DECLINED
    assert entry.note


# ---------------------------------------------------------------------------
# What the live survey found
# ---------------------------------------------------------------------------


def test_the_survey_findings_are_recorded_against_the_review():
    """The review was written from memory; the survey is what checked it."""
    findings = uap_pool.SURVEY_FINDINGS
    assert findings["surveyed"] == 18
    assert findings["reachable"] + findings["refused"] == findings["surveyed"]
    assert len(findings["findings"]) == 4


def test_a_403_is_recorded_as_an_answer_rather_than_retried():
    """Rotating an agent until a site relents is evading a stated policy."""
    findings = uap_pool.SURVEY_FINDINGS
    assert findings["declined_the_agent"]
    assert any("asking is the way" in item for item in findings["findings"])

    import inspect

    from newz.pilot import slots

    source = inspect.getsource(slots.survey_candidate)
    assert "403 is an answer" in source
    assert "does not get to make an exception for the sources it wants most" in source


def test_the_role_proposal_disagreed_with_the_review_and_that_is_recorded():
    """Two in ten. The heuristic was reading front doors."""
    findings = uap_pool.SURVEY_FINDINGS
    assert findings["role_proposal_agreed_with_review"] == 2
    assert any("point at the material" in item for item in findings["findings"])


def test_most_sources_publish_nothing_about_their_terms():
    findings = uap_pool.SURVEY_FINDINGS["terms_published"]
    assert findings["nothing_found"] == 7
    assert "MUFON" in findings["all_rights_reserved"]
