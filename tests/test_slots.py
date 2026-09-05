"""Surveying candidates and solving the pilot slate.

Everything here runs offline through the fixture transport, so the survey path
exercises the real fetcher, the real parsers and the real constraint solver
without touching a network.
"""

from __future__ import annotations

import pytest

from newz.domain.enums import RetentionPolicy, SourceRole
from newz.pilot import catalog_review, slots
from newz.pilot.slots import Candidate, add_candidates, probes, render, solve, survey
from tests.transport import FixtureTransport, Reply

TOPICS = list(catalog_review.REQUIRED_TOPICS)


def _html(title: str, body: str) -> bytes:
    return (
        f"<html><head><title>{title}</title></head><body>"
        + "".join(f"<p>{line}</p>" for line in body.split("|"))
        + "</body></html>"
    ).encode()


@pytest.fixture
def wire():
    return FixtureTransport()


def _serve(wire, url: str, title: str, body: str, content_type: str = "text/html") -> None:
    wire.serve_bytes(url, _html(title, body), content_type)


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


def test_a_candidate_is_cheap_to_add(store):
    added = add_candidates(
        store,
        [
            Candidate(
                id="candidate:c1",
                url="https://registry.example/occurrences",
                publisher="A Registry",
                topic=TOPICS[0],
            )
        ],
        added_by="operator:dean",
    )
    assert added == 1
    assert slots.candidates(store)[0].url == "https://registry.example/occurrences"


def test_a_candidate_the_fetcher_would_refuse_is_never_recorded(store):
    """A slate built around a place the system can never go is a slate of work
    that can never be done."""
    added = add_candidates(
        store,
        [
            Candidate(id="candidate:bad1", url="file:///etc/passwd", publisher="p", topic=TOPICS[0]),
            Candidate(
                id="candidate:bad2",
                url="https://user:pw@example.org/",
                publisher="p",
                topic=TOPICS[0],
            ),
            Candidate(
                id="candidate:good", url="https://ok.example/x", publisher="p", topic=TOPICS[0]
            ),
        ],
        added_by="operator:dean",
    )
    assert added == 1
    assert [c.id for c in slots.candidates(store)] == ["candidate:good"]


# ---------------------------------------------------------------------------
# Surveying
# ---------------------------------------------------------------------------


def test_a_survey_records_what_the_source_actually_serves(store, wire):
    _serve(
        wire,
        "https://registry.example/occurrences",
        "Occurrence registry",
        "The registry holds occurrence records for the national sector.|"
        "Each filing is indexed by case number.|"
        "Records are published under a public domain dedication.|"
        "See creativecommons.org/publicdomain for terms.",
    )
    add_candidates(
        store,
        [
            Candidate(
                id="candidate:c1",
                url="https://registry.example/occurrences",
                publisher="A Registry",
                topic=TOPICS[0],
            )
        ],
        added_by="operator:dean",
    )
    probe = survey(store, wire)[0]

    assert probe.reachable
    assert probe.observed_mime == "text/html"
    assert probe.full_text_capable
    assert probe.segment_count >= 3
    assert probe.proposed_role is SourceRole.PRIMARY_RECORD
    assert any("registry" in item for item in probe.role_evidence)
    assert any("public-domain" in signal for signal in probe.retention_signals)


def test_an_unreachable_candidate_is_recorded_as_refused_not_dropped(store, wire):
    wire.serve("https://gone.example/x", Reply(status=503, headers={"Content-Type": "text/html"}))
    add_candidates(
        store,
        [Candidate(id="candidate:c1", url="https://gone.example/x", publisher="p", topic=TOPICS[0])],
        added_by="operator:dean",
    )
    probe = survey(store, wire)[0]
    assert not probe.reachable
    assert probe.refusal
    assert probes(store)["candidate:c1"].refusal


def test_a_landing_page_is_not_full_text_capable(store, wire):
    _serve(wire, "https://thin.example/x", "Subscribe", "Subscribe to read this article.")
    add_candidates(
        store,
        [Candidate(id="candidate:c1", url="https://thin.example/x", publisher="p", topic=TOPICS[0])],
        added_by="operator:dean",
    )
    probe = survey(store, wire)[0]
    assert probe.reachable
    assert not probe.full_text_capable
    assert probe.segment_count < 3


def test_the_survey_gathers_terms_signals_and_draws_no_conclusion(store, wire):
    """What a source says about its own terms is evidence. Whether that permits
    retention is a judgment with legal weight, and it is not automated."""
    _serve(
        wire,
        "https://strict.example/x",
        "An article",
        "Some content here.|More content.|All rights reserved.|See our terms of use.",
    )
    add_candidates(
        store,
        [Candidate(id="candidate:c1", url="https://strict.example/x", publisher="p", topic=TOPICS[0])],
        added_by="operator:dean",
    )
    probe = survey(store, wire)[0]
    assert "the document asserts all rights reserved" in probe.retention_signals
    assert "the document links terms of use" in probe.retention_signals
    # No field anywhere says whether retention is permitted.
    assert not hasattr(probe, "retention_permitted")


def test_evenly_split_role_evidence_proposes_nothing(store, wire):
    """An even split is exactly the case a person should look at."""
    _serve(
        wire,
        "https://mixed.example/x",
        "Mixed",
        "This registry holds filings.|We also publish replication studies with a doi:10.1/x.|"
        "Contents follow.",
    )
    add_candidates(
        store,
        [Candidate(id="candidate:c1", url="https://mixed.example/x", publisher="p", topic=TOPICS[0])],
        added_by="operator:dean",
    )
    probe = survey(store, wire)[0]
    assert probe.proposed_role is None
    assert any("evenly split" in item for item in probe.role_evidence)


def test_surveying_twice_does_not_refetch(store, wire):
    _serve(wire, "https://once.example/x", "t", "a|b|c|d")
    add_candidates(
        store,
        [Candidate(id="candidate:c1", url="https://once.example/x", publisher="p", topic=TOPICS[0])],
        added_by="operator:dean",
    )
    assert len(survey(store, wire)) == 1
    requests = len(wire.requested)
    assert survey(store, wire) == ()
    assert len(wire.requested) == requests


# ---------------------------------------------------------------------------
# Solving
# ---------------------------------------------------------------------------

#: Body text that makes each bucket's role evidence unambiguous.
BODIES = {
    "claimant_or_firsthand": "I saw the object myself.|I witnessed it from the ridge.|My account follows.|More detail.",
    "primary_or_adjudicative": "This registry indexes filings.|Each filing is numbered.|Records follow.|More records.",
    "empirical_or_replication": "Methods are described below.|A replication is reported.|Results follow.|doi:10.1/x",
    "skeptical_or_forensic": "A skeptic writes here.|The forensic analysis follows.|Methods shown.|More.",
    "historical_or_general_context": "This archive holds background.|Chronology follows.|Context.|More context.",
}

#: Most real sources say something about their terms. A source that says nothing
#: is the interesting case, and it gets its own test.
TERMS_LINE = "Published under creativecommons.org/licenses/by/4.0."


def _slate_world(store, wire, publishers_per_bucket: int = 6, with_terms: bool = True) -> None:
    """Enough surveyed candidates that the solver has real choices to make."""
    index = 0
    entries = []
    for kind, body in BODIES.items():
        for n in range(publishers_per_bucket):
            url = f"https://{kind.replace('_', '-')}-{n}.example/x"
            _serve(wire, url, kind, body + (f"|{TERMS_LINE}" if with_terms else ""))
            entries.append(
                Candidate(
                    id=f"candidate:{kind}-{n}",
                    url=url,
                    publisher=f"publisher:{kind}-{n}",
                    topic=TOPICS[index % len(TOPICS)],
                )
            )
            index += 1
    add_candidates(store, entries, added_by="operator:dean")
    survey(store, wire)


def test_the_solver_fills_every_bucket_and_covers_every_topic(store, wire):
    _slate_world(store, wire)
    slate = solve(store)
    assert slate.acceptable, slate.review.problems
    assert len(slate.slots) == 20
    assert slate.review.by_kind() == dict(catalog_review.REQUIRED_SLOTS)
    assert set(catalog_review.REQUIRED_TOPICS) <= {slot.topic for slot in slate.slots}


def test_the_solver_respects_the_publisher_cap(store, wire):
    _slate_world(store, wire)
    with store.write() as connection:
        connection.execute("UPDATE slot_candidates SET publisher = 'publisher:one'")
    slate = solve(store, "slate:capped")
    assert not slate.acceptable
    # It stops rather than overfilling: at most two from the one publisher.
    assert len(slate.slots) <= 2


def test_the_solver_reports_a_shortfall_rather_than_a_partial_slate(store, wire):
    _slate_world(store, wire, publishers_per_bucket=2)
    slate = solve(store, "slate:short")
    assert not slate.acceptable
    assert slate.shortfall
    assert any("required" in problem for problem in slate.review.problems)


def test_a_candidate_with_no_proposed_role_is_left_unplaced(store, wire):
    _slate_world(store, wire)
    _serve(wire, "https://ambiguous.example/x", "?", "Nothing identifying at all.|More.|Still more.")
    add_candidates(
        store,
        [
            Candidate(
                id="candidate:ambiguous",
                url="https://ambiguous.example/x",
                publisher="publisher:amb",
                topic=TOPICS[0],
            )
        ],
        added_by="operator:dean",
    )
    survey(store, wire)
    slate = solve(store, "slate:amb")
    assert "candidate:ambiguous" in slate.unplaced


def test_a_source_without_usable_full_text_is_proposed_as_lead_only(store, wire):
    _serve(wire, "https://thin.example/x", "Subscribe", "This registry is subscription only.")
    add_candidates(
        store,
        [
            Candidate(
                id="candidate:thin",
                url="https://thin.example/x",
                publisher="publisher:thin",
                topic=TOPICS[0],
            )
        ],
        added_by="operator:dean",
    )
    survey(store, wire)
    slate = solve(store, "slate:thin")
    thin = [slot for slot in slate.slots if slot.source_id == "candidate:thin"]
    if thin:
        assert thin[0].retention_policy is RetentionPolicy.LEAD_ONLY


# ---------------------------------------------------------------------------
# What it hands to the operator
# ---------------------------------------------------------------------------


def test_the_rendering_says_what_it_did_not_decide(store, wire):
    _slate_world(store, wire)
    slate = solve(store)
    text = render(slate, store)
    assert "role proposed:" in text
    assert "retention signals:" in text
    assert "does not enable anything" in text
    assert "reading them is a person's job" in text


def test_a_slate_with_no_retention_signals_is_refused_by_the_review(store, wire):
    """The survey can find nothing, and then the slot cannot say its terms.

    This is the boundary working rather than failing: the solver placed every
    slot and the review still refuses, because a source that publishes nothing
    about its terms is a source somebody has to go and read.
    """
    _slate_world(store, wire, with_terms=False)
    slate = solve(store, "slate:noterms")
    assert len(slate.slots) == 20
    assert not slate.acceptable
    assert any("retention rights not established" in p for p in slate.review.problems)


def test_accepting_a_slate_records_who_accepted_it_and_enables_nothing(store, wire):
    _slate_world(store, wire)
    solve(store, "slate:s1")
    with pytest.raises(ValueError, match="records who accepted it"):
        slots.accept(store, "slate:s1", "")
    slots.accept(store, "slate:s1", "operator:dean")

    row = store.one("SELECT * FROM slate_proposals WHERE id = 'slate:s1'")
    assert row["accepted_by"] == "operator:dean"
    # Nothing was enabled: no epoch, no source revision.
    assert store.one("SELECT COUNT(*) AS n FROM diet_epochs")["n"] == 0
    assert store.one("SELECT COUNT(*) AS n FROM source_revisions")["n"] == 0
