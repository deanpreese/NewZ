"""S2 §9.1 — operator-curated feeds. The starvation, addressed.

`data/feeds.yaml` (61 sources) had zero readers. The being's entire lifetime
intake from the world was 4 sources and 23 claims, all query-driven inside
deliberation; everything else it held came from the operator or itself.

Feeds are how it encounters what it did not know to ask — and exactly where
v1 died: 84,793 claims stored, 0.066% ever cited. The selection ratio IS the
design, so most of what is asserted here is what gets REJECTED.
"""

import json
import time

import pytest

from newz.world.feeds import (
    Feed,
    FeedItem,
    due_feeds,
    harvest,
    load_feeds,
    mark_polled,
    new_items,
    parse_feed,
    shortlist,
    triage,
)
from tests.conftest import FakeLLM

RSS = """<?xml version="1.0"?><rss version="2.0"><channel>
  <title>A feed</title>
  <item><title>CFTC clarifies event-contract rules</title>
    <description>&lt;p&gt;The regulator set out when a contract counts.&lt;/p&gt;</description>
    <link>https://example.org/a</link>
    <pubDate>Wed, 13 Aug 2026 09:00:00 +0000</pubDate></item>
  <item><title>Markets close mixed</title>
    <description>Shares drifted.</description>
    <link>https://example.org/b</link>
    <pubDate>Wed, 13 Aug 2026 08:00:00 +0000</pubDate></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
  <entry><title>On improvisation</title><summary>It resists notation.</summary>
    <link href="https://example.org/c"/>
    <published>2026-08-13T07:00:00Z</published></entry>
</feed>"""

FEED = Feed(name="example", url="https://example.org/feed.xml")


def test_it_reads_rss_and_atom_without_a_dependency():
    rss = parse_feed(RSS, FEED)
    assert [i.title for i in rss] == ["CFTC clarifies event-contract rules",
                                      "Markets close mixed"]
    assert "regulator set out" in rss[0].summary      # html stripped
    assert rss[0].published > 0
    assert [i.title for i in parse_feed(ATOM, FEED)] == ["On improvisation"]


def test_a_malformed_feed_costs_that_feed_and_nothing_else():
    assert parse_feed("<not xml", FEED) == []


def test_the_watermark_is_what_stops_it_rereading_the_world(store):
    items = parse_feed(RSS, FEED)
    assert len(new_items(store, FEED, items)) == 2      # first sight: all new
    mark_polled(store, FEED, items)
    assert new_items(store, FEED, items) == []          # nothing new since


def test_a_feed_is_not_polled_before_its_interval(store):
    f = Feed(name="x", url="https://example.org/f", poll_interval_s=3600)
    assert due_feeds(store, [f]) == [f]
    mark_polled(store, f, [])
    assert due_feeds(store, [f]) == []
    assert due_feeds(store, [f], now=time.time() + 3700) == [f]


def test_only_a_bounded_number_of_feeds_per_cycle(store):
    feeds = [Feed(name=f"f{i}", url=f"https://e{i}.org/f") for i in range(30)]
    assert len(due_feeds(store, feeds)) == 12


def test_the_operator_list_is_the_provenance_record(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(
        "rss:\n"
        "- {name: Enabled one, url: 'https://a.org/f', enabled: true, category: macro}\n"
        "- {name: On, url: 'https://b.org/f', enabled: false}\n")
    feeds = load_feeds(p)
    assert [f.name for f in feeds] == ["Enabled one"]   # disabled is honoured
    assert feeds[0].category == "macro"


# ── the selection ratio, which is the whole design ───────────────────────

KEEP_ONE = '<triage><keep n="1">bears on a question I carry</keep></triage>'
KEEP_NOTHING = "<triage></triage>"


def _items(n=3):
    return [FeedItem(feed=FEED, title=f"Item {i}", summary="Text.",
                     url=f"https://example.org/{i}", published=time.time() - i)
            for i in range(n)]


def test_keeping_nothing_is_a_supported_and_ordinary_answer(store):
    assert triage(FakeLLM([("AMBIENT", KEEP_NOTHING)]), store, _items()) == []


def test_an_unreadable_triage_reads_nothing_rather_than_everything(store):
    # Failing closed is the default, and it survives the retry: TWO bad
    # answers still read nothing.
    llm = FakeLLM([("AMBIENT", "not xml"), ("AMBIENT", "still not xml")])
    assert triage(llm, store, _items()) == []
    assert len(llm.calls) == 2


def test_a_malformed_triage_gets_one_more_chance(store):
    # MEASURED 2026-08-16: one production call in seventeen was lost this way.
    # The model wrote `<keep 1>` instead of `<keep n="1">` — invalid XML — and
    # discarded a real judgment that a Max Tegmark piece "directly bears on
    # the unresolved tension between public AI demonstrations and actual
    # security posture". An unparseable triage keeps nothing, which is
    # indistinguishable from an honest "nothing today" because keeping
    # nothing IS the ordinary answer. That blindness is what hid R-27.
    llm = FakeLLM([
        ("AMBIENT", '<triage>\n  <keep 1>it bears on what I carry</keep>\n</triage>'),
        ("AMBIENT", '<triage><keep n="1">it bears on what I carry</keep></triage>'),
    ])
    kept = triage(llm, store, _items(2))
    assert len(kept) == 1
    assert len(llm.calls) == 2


def test_the_retry_is_only_for_unreadable_answers_never_for_a_judgment(store):
    # A parseable "keep nothing" is a JUDGMENT and must stand. Retrying it
    # would be asking until the answer is the one we wanted.
    llm = FakeLLM([("AMBIENT", "<triage></triage>")])
    assert triage(llm, store, _items()) == []
    assert len(llm.calls) == 1


def test_triage_never_keeps_more_than_it_may(store):
    many = '<triage>' + "".join(
        f'<keep n="{i}">y</keep>' for i in range(1, 7)) + '</triage>'
    assert len(triage(FakeLLM([("AMBIENT", many)]), store, _items(6))) == 3


def test_feed_items_reach_the_prompt_fenced_as_untrusted(store):
    # INV-011: external text is data, never instructions. The hardening was
    # built for feed items before feeds existed; this is it being used.
    llm = FakeLLM([("AMBIENT", KEEP_NOTHING)])
    triage(llm, store, _items(1))
    user = llm.calls[0]["user"]
    assert "untrusted" in user.lower() or "<content" in user.lower()
    assert llm.calls[0]["function"] == "ingest"       # counts against the diet


def test_the_shortlist_degrades_to_recency_without_an_embedder(store):
    items = _items(20)
    short = shortlist(store, items, embedder=None, k=5)
    assert len(short) == 5
    assert short[0].published >= short[-1].published


def test_a_small_batch_skips_ranking_entirely(store):
    items = _items(4)
    assert shortlist(store, items, embedder=None, k=12) == items


# ── the budget gate, which covers everything ─────────────────────────────

def test_no_budget_means_no_feed_is_even_polled(store, tmp_path):
    # S2 §9.1's remedy is to pause ingest; pausing after the HTTP has
    # happened would pause the wrong half.
    log = tmp_path / "calls.jsonl"
    log.write_text("")                     # no earning recorded at all
    feeds = tmp_path / "feeds.yaml"
    feeds.write_text("rss:\n- {name: A, url: 'https://a.org/f'}\n")

    class Exploding:
        def get(self, url):
            raise AssertionError("polled despite no budget")

    h = harvest(FakeLLM([]), store, feeds, fetcher=Exploding(), log_path=log)
    assert h.skipped_reason and h.polled == 0


# ── what it reads must be able to become what it asks ────────────────────
#
# Found by red team 2026-08-14: harvest() polled, triaged, extracted and
# stored — and never called an opener. Feeds were justified as "how the
# being encounters what it did not know to ask", and the asking had no door.
# 0 concerns opened by v2 ever, while it re-ground the same four imported
# questions into restatements.

OPENS = """<proposal>
  <worth_pursuing>yes</worth_pursuing>
  <statement>Which correlated instruments absorb regulatory tail risk?</statement>
  <why_open>It changes how I read market structure.</why_open>
  <closing_condition>Identifying the instruments settles it.</closing_condition>
  <grounded_in>Market makers hedge regulatory tail risk</grounded_in>
</proposal>"""

CLAIMS = """<extraction>
  <claim confidence="0.9">Market makers hedge regulatory tail risk</claim>
</extraction>"""


def _harvest_llm(opener_xml=OPENS):
    # triage keeps item 1 -> extraction -> the reading opener.
    return FakeLLM([("AMBIENT", KEEP_ONE), ("AMBIENT", CLAIMS),
                    ("AMBIENT", opener_xml)])


def test_something_read_can_become_a_concern(store, tmp_path, monkeypatch):
    from newz.world import feeds as feeds_mod

    log = tmp_path / "calls.jsonl"
    log.write_text(json.dumps({"ts": time.time(), "function": "deliberation",
                               "prompt_tokens": 9000, "completion_tokens": 0,
                               "role": "DEEP"}))
    fpath = tmp_path / "feeds.yaml"
    fpath.write_text("rss:\n- {name: A, url: 'https://a.org/f'}\n")

    monkeypatch.setattr(feeds_mod, "due_feeds",
                        lambda *a, **k: [Feed(name="A", url="https://a.org/f")])
    monkeypatch.setattr(feeds_mod, "parse_feed", lambda *a, **k: _items(1))
    monkeypatch.setattr(feeds_mod, "new_items", lambda c, f, i: i)
    monkeypatch.setattr(feeds_mod, "mark_polled", lambda *a, **k: None)

    class _F:
        def get(self, url): return "<rss/>"

    h = feeds_mod.harvest(_harvest_llm(), store, fpath, fetcher=_F(), log_path=log)
    assert h.opened, "reading produced no question"
    assert "raised a question I did not have" in h.render()
    row = store.execute(
        "SELECT origin, statement FROM concerns WHERE origin='curiosity'").fetchone()
    assert row and "correlated instruments" in row["statement"]


def test_a_failing_opener_never_costs_the_read(store, tmp_path, monkeypatch):
    from newz.world import feeds as feeds_mod

    log = tmp_path / "calls.jsonl"
    log.write_text(json.dumps({"ts": time.time(), "function": "deliberation",
                               "prompt_tokens": 9000, "completion_tokens": 0,
                               "role": "DEEP"}))
    fpath = tmp_path / "feeds.yaml"
    fpath.write_text("rss:\n- {name: A, url: 'https://a.org/f'}\n")
    monkeypatch.setattr(feeds_mod, "due_feeds",
                        lambda *a, **k: [Feed(name="A", url="https://a.org/f")])
    monkeypatch.setattr(feeds_mod, "parse_feed", lambda *a, **k: _items(1))
    monkeypatch.setattr(feeds_mod, "new_items", lambda c, f, i: i)
    monkeypatch.setattr(feeds_mod, "mark_polled", lambda *a, **k: None)
    monkeypatch.setattr("newz.concerns.opener.open_from_reading",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    class _F:
        def get(self, url): return "<rss/>"

    h = feeds_mod.harvest(_harvest_llm(), store, fpath, fetcher=_F(), log_path=log)
    assert h.kept, "the read was lost to an opener failure"
    assert h.opened == []
