"""The being's own harvest, searchable when a claim is settled (P4 epic E1.8).

The defect this closes, measured 2026-08-28: `default_adapters()` indexes
Wikipedia, arXiv, OpenAlex, PubMed and SEC EDGAR, none of which is an RSS feed,
and nothing on the resolution path read `harvest_log`. Claim 22 named *"Federal
Open Market Committee (FOMC) Statement or Meeting Minutes"* as its resolver and
those minutes were in the harvest from 2026-08-19 — offered, unread, and
invisible to the one mechanism that exists to tell the being it was wrong.

Both directions are asserted: the harvest is reached on a resolution pass, and
it is reached on no other path.
"""

from __future__ import annotations

import time

from newz.world.harvest import MIN_SHARED_TERMS, WINDOW_DAYS, HarvestAdapter

DAY = 86400.0


def _harvest(store, title, *, feed="Federal Reserve press releases",
             url="https://federalreserve.gov/x", age_days=1.0):
    store.execute(
        "INSERT INTO harvest_log (ts, feed, category, title, url, on_menu,"
        " was_read) VALUES (?,?,?,?,?,1,0)",
        (time.time() - age_days * DAY, feed, "macro", title, url))
    store.commit()


# ── it finds what the feed actually delivered ────────────────────────────

def test_the_document_the_resolver_named_is_found(store):
    """The measured case, as a test: claim 22's resolver against the item."""
    _harvest(store, "Minutes of the Federal Open Market Committee, July 28-29")

    found = HarvestAdapter(store).search(
        "Federal Open Market Committee (FOMC) Statement or Meeting Minutes:"
        " the September statement will retain the tightening bias")

    assert len(found) == 1
    assert found[0].title.startswith("Minutes of the Federal Open Market")
    assert found[0].url == "https://federalreserve.gov/x"
    # The feed is the provenance, not the adapter — a read from here is a read
    # from the Federal Reserve, and `record_read` files it under that outlet.
    assert found[0].source == "Federal Reserve press releases"


def test_the_feed_name_can_carry_the_match(store):
    """The resolver names the publisher; the headline need not repeat it."""
    _harvest(store, "H.4.1 for the week ending August 27")

    found = HarvestAdapter(store).search(
        "Federal Reserve press releases: reserve balances will fall")

    assert len(found) == 1


# ── and it refuses coincidence ───────────────────────────────────────────

def test_one_shared_term_is_not_a_match(store):
    """`MIN_SHARED_TERMS` is what stops every claim matching every headline."""
    _harvest(store, "Committee on climate adaptation publishes guidance",
             feed="Aeon Essays", url="https://aeon.co/x")

    assert HarvestAdapter(store).search(
        "Federal Open Market Committee: rates will hold") == []


def test_document_nouns_alone_never_match(store):
    """"report", "release", "quarterly" describe every feed item there is.

    Without the structural set a resolver reading "quarterly report" matches
    every quarterly report ever harvested, which is the failure that makes an
    overlap score useless rather than merely noisy.
    """
    _harvest(store, "Quarterly report published", feed="Some Outlet",
             url="https://example.com/x")

    assert HarvestAdapter(store).search(
        "The quarterly report: earnings will fall") == []


def test_a_headline_match_without_the_publisher_is_refused(store):
    """The resolver names a publisher, so the publisher has to match.

    Measured 2026-08-28: without this, claims 21 and 31 — whose resolver is the
    Federal Reserve's own H.4.1 release — ranked a Bloomberg Opinion column
    above the Federal Reserve's feed. A headline elsewhere sharing two words
    with the resolver is commentary about the source, not the source.
    """
    _harvest(store, "Federal Reserve Chair must raise rates, says columnist",
             feed="Bloomberg Opinion", url="https://bloomberg.com/x")

    assert HarvestAdapter(store).search(
        "Federal Reserve press releases: reserve balances will fall") == []


def test_function_words_are_not_a_publisher_match(store):
    """"The Hindu" shares "the" with almost every resolver ever written.

    Measured 2026-08-28: it matched eight of the thirty-one open claims that
    way, and the harvest offered Indian domestic politics as the source that
    would settle a European Commission regulation.
    """
    _harvest(store, "Union Bank of India raises $600 mn via bonds",
             feed="The Hindu", url="https://thehindu.com/x")

    assert HarvestAdapter(store).search(
        "Official Journal of the European Union: the regulation is published") == []


def test_items_outside_the_window_are_not_offered(store):
    """A claim is settled by what published near its date (WINDOW_DAYS)."""
    _harvest(store, "Minutes of the Federal Open Market Committee, March",
             age_days=WINDOW_DAYS + 5)

    assert HarvestAdapter(store).search(
        "Federal Open Market Committee Minutes: the bias holds") == []


def test_an_item_with_no_url_is_not_offered(store):
    """`read_document` fetches the url; an item without one cannot be read."""
    _harvest(store, "Minutes of the Federal Open Market Committee", url="")

    assert HarvestAdapter(store).search(
        "Federal Open Market Committee Minutes: the bias holds") == []


def test_ranking_prefers_more_shared_terms_then_recency(store):
    _harvest(store, "Committee Market note", age_days=1,
             url="https://federalreserve.gov/weak")
    _harvest(store, "Minutes of the Federal Open Market Committee, July",
             age_days=3, url="https://federalreserve.gov/strong")

    found = HarvestAdapter(store).search(
        "Federal Open Market Committee Minutes: the bias holds", limit=2)

    assert [r.url for r in found] == ["https://federalreserve.gov/strong",
                                      "https://federalreserve.gov/weak"]


def test_a_missing_table_is_not_a_resolution_failure(store):
    """The harvest adds a place to look. It may never be why a pass fails."""
    store.execute("DROP TABLE harvest_log")
    store.commit()

    assert HarvestAdapter(store).search("Federal Reserve: anything") == []


# ── wired where it belongs, and nowhere else ─────────────────────────────

def test_the_resolution_pass_puts_the_harvest_first(store):
    """Order is what this epic changes: `research()` dedupes by url in adapter
    order, so the being's own subscribed source is the one that survives."""
    from newz.resolutions.resolver import _resolution_adapters

    got = _resolution_adapters(store, None)

    assert got[0].name == "harvest"
    assert [a.name for a in got[1:]] == [
        a.name for a in __import__(
            "newz.world.sources", fromlist=["x"]).default_adapters()]


def test_explicit_adapters_are_honoured_untouched(store):
    """Probes and tests pass stubs; a caller that named its sources meant them."""
    from newz.resolutions.resolver import _resolution_adapters

    stub = [object()]
    assert _resolution_adapters(store, stub) is stub


def test_ordinary_research_does_not_reach_the_harvest(store):
    """A feed item already reaches the being through E1.0's menu.

    Offering it on the research path too would hand the same item through two
    doors and count it twice against §9.1's diet. The harvest is asked whether
    something settles a claim, never offered as something to read.
    """
    import inspect

    import newz.world.research as research

    src = inspect.getsource(research)
    assert "harvest" not in src.lower()
