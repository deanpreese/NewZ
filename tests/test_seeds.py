"""The specific diet: does the slate answer the prescription, and what it costs.

These tests check the slate's shape against the specification. They cannot check
that the URLs resolve or that the terms are as noted — that is what the survey
is for, and a source that has moved or changed its terms should show up there
rather than here.
"""

from __future__ import annotations

import collections

from newz.acquisition.fetcher import FetchPolicy
from newz.acquisition.urlpolicy import inspect_url
from newz.pilot import seeds, slots
from newz.pilot.catalog_review import MAX_PER_PUBLISHER, REQUIRED_SLOTS, REQUIRED_TOPICS
from newz.pilot.prescription import prescribe

#: The slate answers seventeen of the twenty prescribed slots. Three sources were
#: dropped on 2026-09-05 rather than asked: NUFORC, which declines the agent;
#: the Skeptical Inquirer, whose robots.txt disallows every path; and Royal
#: Society Open Science, which permits the path in robots.txt and refuses it at
#: the server.
FILLED = 17

OPEN = [
    ("claimant_or_firsthand", "uap_and_aerospace_anomalies"),
    ("empirical_or_replication", "forteana_cryptids_and_anomalous_natural_events"),
    ("skeptical_or_forensic", "psi_and_consciousness_claims"),
]


def test_the_slate_answers_the_prescription_except_where_it_says_it_does_not():
    """One source per prescribed slot, and the shortfall named rather than absent."""
    proposed = collections.Counter((seed.bucket, seed.topic) for seed in seeds.SEEDS)
    prescribed = collections.Counter(
        (spec.bucket, spec.topic) for spec in prescribe(pins=seeds.PINS)
    )
    assert proposed - prescribed == collections.Counter(), "no slot is filled twice"

    missing = prescribed - proposed
    assert missing == collections.Counter(dict.fromkeys(OPEN, 1))
    reported = seeds.gaps()["open_slots"]["slots"]
    assert sorted((slot["bucket"], slot["topic"]) for slot in reported) == sorted(OPEN)


def test_a_dropped_source_leaves_its_slot_open_rather_than_backfilled():
    """Which source speaks for a topic is a diet decision, not a fallback."""
    open_slots = seeds.gaps()["open_slots"]
    assert open_slots["operator"]["decision"] == "drop rather than ask"
    assert open_slots["candidates"], "the slate names who could fill it"
    assert not any(
        seed.publisher == "National UFO Reporting Center" for seed in seeds.SEEDS
    )


def test_the_slate_covers_every_topic_and_almost_every_bucket_slot():
    assert len(seeds.SEEDS) == FILLED
    assert {seed.topic for seed in seeds.SEEDS} == set(REQUIRED_TOPICS)
    counts = collections.Counter(seed.bucket for seed in seeds.SEEDS)
    assert dict(counts) == {
        **REQUIRED_SLOTS,
        "claimant_or_firsthand": 4,
        "empirical_or_replication": 3,
        "skeptical_or_forensic": 2,
    }


def test_no_publisher_appears_more_than_the_cap_allows():
    counts = collections.Counter(seed.publisher for seed in seeds.SEEDS)
    assert max(counts.values()) <= MAX_PER_PUBLISHER
    assert len(counts) == FILLED


def test_every_url_is_one_the_fetcher_would_accept():
    """A slate containing a place the system can never go is a slate of work
    that can never be done."""
    for seed in seeds.SEEDS:
        verdict = inspect_url(seed.url, FetchPolicy().url)
        assert verdict.allowed, f"{seed.publisher}: {verdict.refusal}"
        assert verdict.scheme == "https", seed.publisher


def test_every_seed_says_why_it_holds_its_role_and_what_its_terms_are():
    for seed in seeds.SEEDS:
        assert seed.why_this_role.strip(), seed.publisher
        assert seed.terms in (seeds.PUBLIC_DOMAIN, seeds.OPEN_LICENCE, seeds.UNCLEAR)


def test_the_evidentiary_slots_are_weighted_toward_retainable_sources():
    """Primary records and empirical work carry promotion weight, so they are
    the slots where retention has to hold."""
    weighted = [
        seed
        for seed in seeds.SEEDS
        if seed.bucket in ("primary_or_adjudicative", "empirical_or_replication")
    ]
    retainable = [seed for seed in weighted if seed.terms != seeds.UNCLEAR]
    assert len(weighted) == 9, "one empirical slot is open: Royal Society declines"
    assert len(retainable) >= 8


def test_the_claimant_retention_gap_is_reported_rather_than_hidden():
    """The finding that matters before the pilot starts: a claimant source that
    cannot be retained cannot establish even an attribution."""
    summary = seeds.retention_summary()
    assert summary["claimant_slots_unclear"] >= 1
    assert "cannot establish even an attribution" in summary["finding"]
    assert "under-represent what claimants said" in summary["finding"]


def test_the_slate_registers_as_a_candidate_adapter(store):
    slots.clear_candidate_adapters()
    seeds.register()
    assert "seeds" in slots.registered_adapters()

    added, unserved = slots.propose_candidates(
        store, specs=seeds.prescribed(), added_by="operator:dean"
    )
    assert added == FILLED
    assert len(slots.candidates(store)) == FILLED
    # The slot nothing was proposed for is named by the proposer, not discovered
    # later by whatever notices the slate is short.
    assert sorted((spec.bucket, spec.topic) for spec in unserved) == sorted(OPEN)
    slots.clear_candidate_adapters()


def test_the_rendering_says_it_is_a_proposal_and_not_a_finding():
    text = seeds.render()
    assert "hypothesis the survey tests" in text
    assert "prompt to read the terms rather than a finding" in text
    assert "US federal works" in text


def test_the_cautions_carry_the_things_that_would_otherwise_be_learned_late():
    cautions = " ".join(seed.caution for seed in seeds.SEEDS)
    # A patent proves a filing, not performance.
    assert "never performance" in cautions
    # Two records of one incident share a basis rather than corroborating.
    assert "share a basis" in cautions and "derivation link" in cautions
    # Wikipedia needs a contactable user agent or it refuses.
    assert "403" in cautions
    # A released document cannot speak to what was redacted out of it.
    assert "redactions are absences" in cautions


def test_the_slate_reports_the_gaps_it_leaves():
    """Two findings the operator needs before the pilot, not after it."""
    found = seeds.gaps()
    assert "cannot reach `refuted`" in found["no_adjudicator"]["finding"]
    assert "adjudicator" not in found["no_adjudicator"]["buckets_present"]
    assert "cannot establish even an attribution" in found["claimant_retention"]["finding"]
    assert len(found["claimant_retention"]["answers"]) == 3


def test_the_pins_are_stated_with_their_reasons():
    """Pinned rather than encoded into the score, so the scoring function is not
    quietly rewritten until it produces a wanted answer."""
    assert {
        ("primary_or_adjudicative", "alternative_physics_and_energy"),
        ("primary_or_adjudicative", "uap_and_aerospace_anomalies"),
    } == seeds.PINS
    import inspect

    source = inspect.getsource(seeds)
    assert "domain knowledge" in source or "knowledge rather than" in source


# ---------------------------------------------------------------------------
# What dropping a source costs, said out loud
# ---------------------------------------------------------------------------


def test_a_topic_with_no_source_able_to_contradict_it_is_named():
    """`TRUE_NORTH.md`: support and refutation face the same burden.

    Dropping the Skeptical Inquirer took the only skeptical source on psi, and
    psi is one of just three topics the prescription gives one to at all. The
    slate says so rather than leaving it to be inferred from an empty slot.
    """
    unopposed = seeds.gaps()["unopposed_topics"]
    assert unopposed["topics"] == ["psi_and_consciousness_claims"]
    assert "cannot" in unopposed["finding"]
    assert unopposed["operator"]["decision"] == "drop rather than ask"


def test_the_unopposed_check_reads_the_slate_rather_than_the_history():
    """It has to stay true however the slate next changes."""
    from newz.pilot.prescription import SKEPTICAL

    have = {seed.topic for seed in seeds.SEEDS if seed.bucket == SKEPTICAL}
    for topic in seeds.gaps()["unopposed_topics"]["topics"]:
        assert topic not in have


def test_the_applied_repoints_are_the_ones_the_survey_confirmed():
    from newz.pilot import repoint

    urls = {seed.publisher: seed.url for seed in seeds.SEEDS}
    for proposal in repoint.applicable():
        if proposal.publisher in urls:
            assert urls[proposal.publisher] == proposal.now, proposal.publisher
    for proposal in repoint.refuted():
        assert urls.get(proposal.publisher) != proposal.now, proposal.publisher
