"""The resolver pass (P3 epic E1.3).

The one place in the system where something other than the being or the
operator can say no. Its whole design is refusal to guess: the claim is only
settled by material that says so, and the being must be able to quote the
words. Everything else leaves it open.
"""

from __future__ import annotations

import time

import pytest

from newz.resolutions.model import Claim
from newz.resolutions.resolver import (
    MAX_ATTEMPTS, RETRY_AFTER_HOURS, resolve_claim, resolve_due_claims,
    workable_claims,
)
from newz.resolutions.store import get_claim, open_claim
from newz.world.research import ResearchOutcome
from newz.world.sources import SearchResult

from tests.conftest import FakeLLM

DAY = 86400.0
QUOTE = ("Aggregate open interest stood at 412,000 contracts, 14% below the"
         " exchange's published figure for the same date.")


def _open(store, **kw) -> int:
    base = dict(
        id=None,
        claim="The COT report will show open interest at least 10% below the"
              " exchange's published figure.",
        resolution_condition="The COT release is published and the two figures"
                             " are compared.",
        resolver="CFTC Commitments of Traders weekly report",
        due_at=time.time() - DAY, provenance="concern:7")
    base.update(kw)
    return open_claim(store, Claim(**base), models=set())


def _found(*claims: str) -> ResearchOutcome:
    out = ResearchOutcome(query="q")
    out.claims = [(c, 0.9) for c in claims]
    out.results = [SearchResult(title="COT release", summary="weekly report",
                                url="https://cftc.gov/cot/2026-09-04",
                                source="cftc")]
    return out


def _verdict(settled="yes", outcome="contradicted", quote=QUOTE,
             source="https://cftc.gov/cot/2026-09-04", why_not="") -> str:
    return (f"<verdict><settled>{settled}</settled><outcome>{outcome}</outcome>"
            f"<quote>{quote}</quote><source>{source}</source>"
            f"<why_not>{why_not}</why_not></verdict>")


@pytest.fixture
def world(monkeypatch):
    """Patch the world in one place; each test says what came back."""
    box = {"outcome": _found(QUOTE), "gaps": [], "gap_causes": []}

    def fake_research(client, query, **kw):
        box["query"] = query
        return box["outcome"]

    def fake_gap(conn, *, concern_id, query, gap, outcome=None):
        box["gaps"].append(gap)
        box["gap_causes"].append(outcome.cause if outcome else None)

    monkeypatch.setattr("newz.world.research.research", fake_research)
    monkeypatch.setattr("newz.world.research.record_gap", fake_gap)
    return box


def _resolve(store, claim_id, llm):
    from newz.resolutions.store import get_claim as g
    return resolve_claim(store, llm, g(store, claim_id), log_path=None)


def test_a_due_claim_is_settled_from_a_world_source(store, world):
    """E1.3's done-when, first half."""
    cid = _open(store)

    out = _resolve(store, cid, FakeLLM([("DEEP", _verdict())]))

    assert out.settled and out.outcome == "contradicted"
    claim = get_claim(store, cid)
    assert claim.went_against_me
    assert claim.settled_by.startswith("https://cftc.gov")
    assert QUOTE[:30] in claim.settled_note


def test_being_contradicted_reaches_sleep_as_an_episode(store, world):
    """Whichever way it goes. This is the single read P3 says the plan turns
    on, and an episode is how it gets into the Perspective at all."""
    cid = _open(store)

    _resolve(store, cid, FakeLLM([("DEEP", _verdict())]))

    row = store.execute("SELECT kind, provenance, summary FROM episodes"
                        " WHERE kind='resolution'").fetchone()
    assert row["provenance"] == "world"
    assert "contradicted a claim I made" in row["summary"]
    assert str(cid) in str(store.execute(
        "SELECT content_json FROM episodes WHERE kind='resolution'").fetchone()[0])


def test_a_verdict_it_cannot_quote_settles_nothing(store, world):
    """v1's Stanford CRU lesson applied to being right: a verdict the material
    does not contain is the model's opinion wearing the world's clothes, and
    Rule 4 forbids exactly that."""
    cid = _open(store)

    out = _resolve(store, cid, FakeLLM([("DEEP", _verdict(
        quote="The report clearly vindicates the position."))]))

    assert not out.settled and "not in the material" in out.failure
    claim = get_claim(store, cid)
    assert claim.is_open and claim.outcome is None
    assert "not in the material" in claim.last_failure


def test_an_unreadable_source_leaves_it_open_with_the_failure_logged(store, world):
    """E1.3's done-when, second half."""
    world["outcome"] = ResearchOutcome(query="q", gap="nothing usable")
    cid = _open(store)

    out = _resolve(store, cid, FakeLLM([]))       # no model call is reached

    assert not out.settled
    claim = get_claim(store, cid)
    assert claim.is_open and claim.attempts == 1
    assert "nothing came back" in claim.last_failure
    # And the reach that found nothing is what names the sources worth adding.
    assert world["gaps"] and f"claim {cid}" in world["gaps"][0]


def test_an_unreadable_verdict_leaves_it_open(store, world):
    cid = _open(store)

    out = _resolve(store, cid, FakeLLM([("DEEP", "<verdict><settled>yes")]))

    assert not out.settled and "unreadable" in out.failure
    assert get_claim(store, cid).is_open


def test_material_that_does_not_answer_is_the_ordinary_outcome(store, world):
    """Sources are slow, partial and often adjacent. Not settling must be
    cheap and honest, or the resolver will start reaching."""
    cid = _open(store)

    out = _resolve(store, cid, FakeLLM([("DEEP", _verdict(
        settled="no", outcome="", quote="",
        why_not="The release covers August, not the September contract."))]))

    assert not out.settled
    assert "September contract" in get_claim(store, cid).last_failure


def test_a_verdict_with_no_outcome_settles_nothing(store, world):
    cid = _open(store)

    out = _resolve(store, cid, FakeLLM([("DEEP", _verdict(outcome="unclear"))]))

    assert not out.settled and "no outcome" in out.failure
    assert get_claim(store, cid).is_open


def test_the_attempt_is_booked_before_any_spending(store, world):
    """R-18's discipline: a claim whose source never answers cannot be retried
    without limit, and a crash mid-resolution cannot loop."""
    cid = _open(store)

    _resolve(store, cid, FakeLLM([("DEEP", _verdict(settled="no", quote=""))]))

    claim = get_claim(store, cid)
    assert claim.attempts == 1 and claim.last_attempt_at


def test_a_paused_diet_does_not_charge_the_claim(store, world):
    """The being is not charged an attempt for its own budget ceiling."""
    world["outcome"] = ResearchOutcome(query="q", paused="ingest share exceeded")
    cid = _open(store)

    out = _resolve(store, cid, FakeLLM([]))

    assert not out.settled and "paused" in out.failure
    assert get_claim(store, cid).attempts == 0


def test_a_claim_just_tried_is_not_tried_again_this_cycle(store, world):
    cid = _open(store)
    _resolve(store, cid, FakeLLM([("DEEP", _verdict(settled="no", quote=""))]))

    assert workable_claims(store) == []
    assert [c.id for c in workable_claims(
        store, now=time.time() + (RETRY_AFTER_HOURS + 1) * 3600)] == [cid]


def test_a_claim_that_keeps_failing_stops_costing_the_diet(store, world):
    """It stays OPEN and unsettled — not closed, not ambiguous. Nothing
    happened, and INV-044 says an unmeasured thing reports itself as
    unmeasured rather than as a compliant zero."""
    cid = _open(store)
    now = time.time()
    for i in range(MAX_ATTEMPTS):
        resolve_claim(store, FakeLLM([("DEEP", _verdict(settled="no", quote=""))]),
                      get_claim(store, cid), log_path=None,
                      now=now + i * (RETRY_AFTER_HOURS + 1) * 3600)

    later = now + 400 * DAY
    assert workable_claims(store, now=later) == []
    claim = get_claim(store, cid)
    assert claim.is_open and claim.outcome is None and claim.attempts == MAX_ATTEMPTS


def test_a_claim_not_yet_due_is_left_alone(store, world):
    _open(store, due_at=time.time() + 30 * DAY)

    assert workable_claims(store) == []
    assert resolve_due_claims(store, FakeLLM([]), log_path=None) == []
