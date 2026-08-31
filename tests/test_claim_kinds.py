"""The claim that is already true (P4 epic E1.9).

Every claim before this was a forecast: `MIN_HORIZON_DAYS = 2` forbade anything
settleable now. A retrodiction is a claim about what is ALREADY the case and the
being does not yet know — just as ungraded by the being, and settled on the next
resolver pass instead of in a month.

**Why the latency was the thing worth changing.** Measured 2026-08-28: 19 of the
31 open claims settle within 60 days, which is 0.317 externally-graded events a
day against 103 deliberation cycles and 50 advances. And the two caps multiply —
a 29.7-day mean horizon against `MAX_OPEN_CLAIMS = 40` puts sustainable
throughput at 40/29.7 = 1.35 a day whatever the being wants, because inventory
divided by latency is the ceiling.

Five things are asserted here, one per clause of the epic's Done-when.
"""

from __future__ import annotations

import time
from pathlib import Path

from newz.resolutions.door import (
    MAX_OPEN_CLAIMS, MAX_RETRODICTIONS_PER_DAY, already_in_the_dossier,
    open_claims_count, opened_today, propose_claim,
)
from newz.resolutions.model import Claim
from newz.resolutions.store import get_claim, open_claim

from tests.conftest import FakeLLM

DAY = 86400.0
CONCERN = "Does displayed liquidity survive a volatility shock?"
ESTABLISHED = ("Order-splitting inflates displayed depth without adding"
               " capacity to absorb a shock.")


def _proposal(due="30", resolver="the CFTC Commitments of Traders weekly report"):
    return (
        "<claim><worth_claiming>yes</worth_claiming>"
        "<statement>The CFTC report for the week ending September 4 will show"
        " open interest at least 10% below the exchange's published figure."
        "</statement>"
        "<settles_when>The release is published and the two figures are"
        " compared.</settles_when>"
        f"<resolver>{resolver}</resolver>"
        f"<due_in_days>{due}</due_in_days>"
        "<could_be_wrong>The report shows the two figures within 2% of each"
        " other.</could_be_wrong></claim>")


def _ask(store, response, **kw):
    return propose_claim(store, FakeLLM([("DEEP", response)]),
                         established=ESTABLISHED, concern_statement=CONCERN,
                         concern_id=7, **kw)


def _harvest(store, title, feed, url, *, age_days=1.0):
    store.execute(
        "INSERT INTO harvest_log (ts, feed, category, title, url, on_menu,"
        " was_read) VALUES (?,?,?,?,?,1,0)",
        (time.time() - age_days * DAY, feed, "macro", title, url))
    store.commit()


def _read(store, outlet, url):
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, claims_kept)"
        " VALUES (?,?,?,?,1)",
        (time.time(), outlet, f"{outlet}:{url}", "q"))
    store.commit()


# ── a zero horizon is admitted, and is a different kind ──────────────────

def test_a_zero_horizon_opens_a_retrodiction(store):
    verdict = _ask(store, _proposal(due="0"))

    assert verdict.claim_id, verdict.refused
    claim = get_claim(store, verdict.claim_id)
    assert claim.kind == "retrodiction"
    assert claim.is_retrodiction


def test_a_retrodiction_is_workable_on_the_next_pass(store):
    """The whole point of the kind: due the moment it is opened.

    `workable_claims` selects `due_at <= now`, so a zero horizon means the next
    deliberation cycle picks it up rather than a date in October.
    """
    from newz.resolutions.resolver import workable_claims

    verdict = _ask(store, _proposal(due="0"))

    assert [c.id for c in workable_claims(store)] == [verdict.claim_id]


def test_a_forecast_is_not_workable_yet(store):
    """The other direction, so the test above cannot pass by accident."""
    from newz.resolutions.resolver import workable_claims

    assert _ask(store, _proposal(due="30")).claim_id
    assert workable_claims(store) == []


# ── the dossier guard, which replaces the 2-day proxy ────────────────────

def test_a_source_already_read_is_refused_and_recorded(store):
    """`MIN_HORIZON_DAYS`'s own comment says a claim about something "already
    in the dossier" is not a prediction. That is now checked directly."""
    _harvest(store, "Commitments of Traders, week ending August 26",
             "CFTC press releases", "https://cftc.gov/cot/0826")
    _read(store, "CFTC press releases", "https://cftc.gov/cot/0826")

    verdict = _ask(store, _proposal(due="0", resolver="CFTC press releases"))

    assert verdict.refused and "already read" in verdict.refused
    row = store.execute(
        "SELECT reason FROM claim_refusals ORDER BY id DESC LIMIT 1").fetchone()
    assert row and "already read" in row[0]


def test_a_harvested_but_unread_source_is_admitted(store):
    """The finer half. Having the item is not having read it — an unread
    harvest row is exactly the case a retrodiction is for."""
    _harvest(store, "Commitments of Traders, week ending August 26",
             "CFTC press releases", "https://cftc.gov/cot/0826")

    verdict = _ask(store, _proposal(due="0", resolver="CFTC press releases"))

    assert verdict.claim_id, verdict.refused


def test_the_dossier_check_does_not_touch_forecasts(store):
    """A forecast is about what has not happened; reading the source before
    it speaks is ordinary research, not an answer already known."""
    _harvest(store, "Commitments of Traders, week ending August 26",
             "CFTC press releases", "https://cftc.gov/cot/0826")
    _read(store, "CFTC press releases", "https://cftc.gov/cot/0826")

    assert _ask(store, _proposal(due="30", resolver="CFTC press releases")).claim_id


def test_a_miss_is_not_a_pass(store):
    """Recorded rather than implied (INV-044): the harvest is local, the
    adapters reach further, and nothing here can check those without a network
    call the door has no business making."""
    assert already_in_the_dossier(store, "some source never harvested") is None


# ── the carrying pool, and what counts against it ────────────────────────

def test_a_retrodiction_does_not_consume_the_carrying_pool(store):
    """`MAX_OPEN_CLAIMS` caps UNRESOLVED INVENTORY. A claim that leaves on the
    next pass has a residency of minutes and no inventory cost."""
    assert _ask(store, _proposal(due="0")).claim_id

    assert open_claims_count(store) == 0
    assert opened_today(store, kind="retrodiction") == 1
    assert opened_today(store, kind="forecast") == 0


def test_a_forecast_does_consume_it(store):
    assert _ask(store, _proposal(due="30")).claim_id
    assert open_claims_count(store) == 1


def test_retrodictions_have_their_own_daily_rate(store):
    """The reason the daily cap exists — "a miscalibrated door cannot do it in
    one afternoon" — is as true of the past as of the future."""
    now = time.time()
    for i in range(MAX_RETRODICTIONS_PER_DAY):
        open_claim(store, Claim(
            id=None, claim=f"retro {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=now, provenance="concern:1",
            opened_at=now, kind="retrodiction"), models=set())

    verdict = _ask(store, _proposal(due="0"))

    assert verdict.declined and not verdict.claim_id
    # Four retrodictions in the store and the forecast pool still reads zero:
    # they are rate-limited, never carried.
    assert open_claims_count(store) == 0


def test_neither_route_open_means_nothing_is_spent(store):
    """The one case where the caps still stop the door before the model call.

    A FakeLLM with nothing scripted raises IndexError if it is reached, so this
    asserts the guard by construction rather than by inspecting a counter.
    """
    now = time.time()
    for i in range(MAX_OPEN_CLAIMS):
        open_claim(store, Claim(
            id=None, claim=f"old {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=now - 60 * DAY,
            provenance="concern:1", opened_at=now - 90 * DAY), models=set())
    for i in range(MAX_RETRODICTIONS_PER_DAY):
        open_claim(store, Claim(
            id=None, claim=f"retro {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=now, provenance="concern:1",
            opened_at=now, kind="retrodiction"), models=set())

    verdict = propose_claim(store, FakeLLM([]), established=ESTABLISHED,
                            concern_statement=CONCERN, concern_id=7)

    assert verdict.refused and "pool is full" in verdict.refused


def test_a_full_forecast_pool_no_longer_declines_in_silence(store):
    """Measured 2026-08-28: 31 of 40 open, opening at 3.0/day against a
    throughput ceiling of 1.35/day. This was days from firing, and the record
    would have read as "it had nothing to claim"."""
    now = time.time()
    for i in range(MAX_OPEN_CLAIMS):
        open_claim(store, Claim(
            id=None, claim=f"old {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=now - 60 * DAY,
            provenance="concern:1", opened_at=now - 90 * DAY), models=set())

    verdict = _ask(store, _proposal(due="30"))

    assert verdict.refused and "pool is full" in verdict.refused
    assert store.execute(
        "SELECT COUNT(*) FROM claim_refusals").fetchone()[0] == 1


def test_a_full_forecast_pool_still_lets_a_retrodiction_through(store):
    """The pool caps unresolved inventory, and a retrodiction adds none.

    This is what makes E1.9 a fix for the saturation measured 2026-08-28
    rather than a relabelling of it: when the forecast pool fills, the being
    can still be told it is wrong.
    """
    now = time.time()
    for i in range(MAX_OPEN_CLAIMS):
        open_claim(store, Claim(
            id=None, claim=f"old {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=now - 60 * DAY,
            provenance="concern:1", opened_at=now - 90 * DAY), models=set())

    verdict = _ask(store, _proposal(due="0"))

    assert verdict.claim_id, verdict.refused
    assert get_claim(store, verdict.claim_id).kind == "retrodiction"


# ── and it settles on that pass, which is the whole of the epic ──────────

def test_a_retrodiction_settles_on_the_next_pass(store, monkeypatch):
    """The Done-when's second clause, end to end.

    Admitted at the door with a zero horizon, picked up by the very next
    resolver pass, and settled by material the being did not write. Under a
    45-day forecast the same claim would have waited until October; here the
    whole loop closes inside one deliberation cycle, which is the 30-day
    latency this epic exists to remove.
    """
    import newz.resolutions.resolver as resolver_mod
    from newz.resolutions.resolver import resolve_due_claims
    from newz.world.research import ResearchOutcome
    from newz.world.sources import SearchResult

    quote = ("Open interest stood at 412,000 contracts, 14% below the"
             " exchange's published figure for the same date.")

    def fake_research(client, query, **kw):
        out = ResearchOutcome(query=query)
        out.claims = [(quote, 0.9)]
        out.results = [SearchResult(
            title="Commitments of Traders", summary="weekly",
            url="https://cftc.gov/cot/0904", source="CFTC press releases")]
        return out

    monkeypatch.setattr(resolver_mod, "research", fake_research, raising=False)
    monkeypatch.setattr("newz.world.research.research", fake_research)

    opened = _ask(store, _proposal(due="0"))
    assert opened.claim_id, opened.refused

    verdict = (f"<verdict><settled>yes</settled>"
               f"<outcome>contradicted</outcome><quote>{quote}</quote>"
               f"<source>https://cftc.gov/cot/0904</source></verdict>")
    resolve_due_claims(store, FakeLLM([("DEEP", verdict)]),
                       log_path=Path("/nonexistent/probe.jsonl"))

    claim = get_claim(store, opened.claim_id)
    assert claim.status == "resolved"
    assert claim.outcome == "contradicted"
    assert claim.kind == "retrodiction"


# ── the record says which kind, always ───────────────────────────────────

def test_every_pre_existing_row_is_a_forecast(store):
    """0045 defaults to 'forecast' because every row written under a 2-day
    floor is one in fact — a statement rather than a guess."""
    open_claim(store, Claim(
        id=None, claim="a claim", resolution_condition="a source says so",
        resolver="a named report", due_at=time.time() + 30 * DAY,
        provenance="concern:1"), models=set())

    assert store.execute(
        "SELECT kind FROM resolutions").fetchone()[0] == "forecast"


def test_the_schema_refuses_a_kind_it_does_not_know(store):
    import sqlite3

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        store.execute(
            "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
            " resolver, due_at, provenance, status, kind)"
            " VALUES (?,?,?,?,?,?,'open','someday')",
            (time.time(), "c", "cond", "a report", time.time(), "concern:1"))


# ── E1.10: the two kinds never average ───────────────────────────────────

def _settled(store, kind, n=1):
    now = time.time()
    for i in range(n):
        store.execute(
            "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
            " resolver, due_at, provenance, status, outcome, settled_at, kind)"
            " VALUES (?,?,?,?,?,?,'resolved','held',?,?)",
            (now, f"{kind} {i}", "a source says so", "a named report", now,
             "concern:1", now, kind))
    store.commit()


def test_the_two_series_never_mix(store):
    """E1.10's first clause. `claims_settled` keeps its exact meaning — every
    row before migration 0045 was a forecast in fact — and the new quantity
    gets its own series rather than being folded into the old one."""
    from newz.evidence.mechanical import claims_settled, retrodictions_settled

    _settled(store, "forecast", 2)
    _settled(store, "retrodiction", 3)
    since = time.time() - DAY

    assert claims_settled(store, since=since).value == 2
    assert retrodictions_settled(store, since=since).value == 3


def test_the_reader_shows_both(store):
    """E1.10's third clause, at the layer `tools/claims.py` renders from."""
    from pathlib import Path

    from newz.evidence.consequence import read

    _settled(store, "forecast", 2)
    _settled(store, "retrodiction", 3)

    c = read(store, Path("."), now=time.time(), hours=168.0)

    assert c.resolution.settled == 2
    assert c.resolution.settled_retrodictions == 3


def test_the_definition_change_is_recorded_with_its_reason():
    """E1.10's second clause. `consequence_rate` is the one metric whose
    meaning genuinely changed — consequence is consequence whichever kind
    produced it — so its v2 series ends and the seam carries the reason.

    A bump with no stated reason raises rather than resetting a baseline
    silently, which is what E2.8 exists to prevent.
    """
    from newz.evidence.definitions import reason_for, version_of

    assert version_of("consequence_rate") == 3
    why = reason_for("consequence_rate", 3)
    assert "BOTH kinds" in why
    assert "E1.9" in why and "E1.10" in why


def test_the_scoped_metrics_did_not_bump(store):
    """The other half of the argument, asserted rather than trusted: scoping
    to forecasts broke no series, so no version moved and no seam exists."""
    from newz.evidence.definitions import version_of

    assert version_of("claims_opened") == 1
    assert version_of("claims_settled") == 1
    assert version_of("retrodictions_opened") == 1
    assert version_of("retrodictions_settled") == 1


def test_the_dossier_guard_does_not_fire_on_a_shared_word(store):
    """Found by tools/retrodiction_probe.py on the day E1.9 shipped.

    The guard reuses E1.8's matcher, and the two need opposite things: in
    search a weak match costs one candidate triage drops, while here it refuses
    a legitimate claim and records the refusal against the being. A resolver
    reading "Grove Music Online, Oxford University Press" matched the feed
    "Associated Press Top News" on the single word `press`, and a sound claim
    about a music dictionary was turned away because the being had read a news
    story about Discord.
    """
    _harvest(store, "Brazil sues online platform Discord over child protection",
             "Associated Press Top News", "https://apnews.com/x")
    _read(store, "Associated Press Top News", "https://apnews.com/x")

    assert already_in_the_dossier(
        store, "Grove Music Online, Oxford University Press") is None


def test_the_dossier_guard_still_fires_when_the_resolver_names_the_feed(store):
    """The other direction, so the fix above cannot pass by disabling it.

    Two shared feed-name terms is the difference between naming a publisher
    and sharing a word with one: {cftc, press} against {press}.
    """
    _harvest(store, "Commitments of Traders, week ending August 26",
             "CFTC press releases", "https://cftc.gov/cot/0826")
    _read(store, "CFTC press releases", "https://cftc.gov/cot/0826")

    assert already_in_the_dossier(store, "CFTC press releases") is not None


def test_a_bracketed_placeholder_is_not_a_source(store):
    """Found by tools/retrodiction_probe.py, 2026-08-28. The door admitted a
    claim resolved by "[Case Name], [Case Number], [Court Name]" — a source
    nobody can fetch wearing the shape of one that can be. `\\bXXXX+\\b` wanted
    four X's and the being writes three; nothing looked at brackets at all."""
    for resolver in ("The docket sheet for [Case Name], [Case Number]",
                     "Commission Implementing Regulation (EU) 2024/xxx",
                     "European Commission Regulation (EU) [Number] of [Date]"):
        v = _ask(store, _proposal(due="30", resolver=resolver))
        assert v.refused and "not a document yet" in v.refused, resolver


def test_a_real_identifier_is_still_admitted(store):
    """The other direction: the check must not refuse a resolver that names
    something, or it teaches the being to phrase around it rather than to find
    a source — which is why check_resolver is deliberately narrow."""
    v = _ask(store, _proposal(
        due="30", resolver="Commission Implementing Regulation (EU) 2024/1083"))

    assert v.claim_id, v.refused
