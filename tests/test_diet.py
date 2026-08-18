import time

from newz.world.diet import (
    MAX_OUTLET_SHARE,
    citation_rate,
    MIN_ITEMS_FOR_CAP,
    apply_share_caps,
    outlet_of,
    over_share,
    record_read,
    shares,
)
from newz.world.robots import RobotsCache


def _read(store, outlet_url, n=1, age_days=0.0):
    for i in range(n):
        store.execute(
            "INSERT INTO ingest_log (ts, outlet, source, query, claims_kept)"
            " VALUES (?,?,?,?,1)",
            (time.time() - age_days * 86400, outlet_of(outlet_url),
             f"{outlet_url}/{i}", "q"))
    store.commit()


# ── the share-cap unit ───────────────────────────────────────────────────

def test_multi_feed_outlets_count_as_one_outlet():
    # REVIEW.md D4: Bloomberg is three feeds, BBC three, NYT two. Counting
    # feeds instead of outlets would under-count every concentration.
    assert outlet_of("https://feeds.bloomberg.com/markets/news.rss") == "bloomberg.com"
    assert outlet_of("https://feeds.bloomberg.com/economics/news.rss") == "bloomberg.com"
    assert outlet_of("https://www.bbc.co.uk/news") == "bbc.co.uk"
    assert outlet_of("https://feeds.bbci.co.uk/news/rss.xml") == "bbci.co.uk"


def test_adapter_results_are_keyed_by_adapter():
    assert outlet_of("arxiv:https://arxiv.org/abs/1234") == "arxiv"
    assert outlet_of("openalex:https://doi.org/10.1/x") == "openalex"


# ── the cap ──────────────────────────────────────────────────────────────

def test_a_small_sample_is_not_a_concentration(store):
    _read(store, "https://one.example", n=5)
    assert not over_share(store, "one.example")     # 100% of five is not a problem


def test_an_over_represented_outlet_is_capped(store):
    # 20 from one outlet, 5 each from four others: the hog is 50% of 40,
    # over its 40% fair-share-times-two threshold at five outlets.
    _read(store, "https://hog.example", n=MIN_ITEMS_FOR_CAP)
    for host in ("a", "b", "c", "d"):
        _read(store, f"https://{host}.example", n=5)
    assert over_share(store, "hog.example")
    assert not over_share(store, "a.example")


def test_the_cap_scales_with_diet_size(store):
    from newz.world.diet import effective_cap

    # S2 §13's flat 10% assumed a 61-feed diet. With five adapters an even
    # split is 20% each, so a flat cap would fire on everything at once.
    assert effective_cap(5) == 0.40      # nothing capped below dominance
    assert effective_cap(20) == 0.10     # the §13 target binds
    assert effective_cap(61) == 0.10
    # v1's anti-pattern is caught at any diet size.
    assert 0.56 > effective_cap(5) and 0.56 > effective_cap(61)


def test_an_even_split_across_few_outlets_is_not_a_concentration(store):
    for host in ("a", "b", "c", "d", "e"):
        _read(store, f"https://{host}.example", n=8)
    for host in ("a", "b", "c", "d", "e"):
        assert not over_share(store, f"{host}.example")


def test_shares_are_reported_for_review(store):
    _read(store, "https://a.example", n=30)
    _read(store, "https://b.example", n=10)
    dist = shares(store)
    assert abs(dist["a.example"] - 0.75) < 0.01
    assert dist["b.example"] < MAX_OUTLET_SHARE + 0.2


def test_old_reads_leave_the_window(store):
    _read(store, "https://old.example", n=50, age_days=60)
    _read(store, "https://new.example", n=5)
    dist = shares(store)
    assert "old.example" not in dist and "new.example" in dist


def test_the_cap_deprioritises_rather_than_bans(store):
    # A hard ban would let the cap silence the only source that can answer.
    _read(store, "https://hog.example", n=MIN_ITEMS_FOR_CAP)
    for host in ("a", "b", "c", "d"):
        _read(store, f"https://{host}.example", n=5)

    class R:
        def __init__(self, url):
            self.url, self.source = url, "feed"

    results = [R("https://hog.example/new"), R("https://fresh.example/new")]
    keep, capped = apply_share_caps(store, results, source_of=lambda r: r.url)
    assert [r.url for r in keep] == ["https://fresh.example/new"]
    assert [r.url for r in capped] == ["https://hog.example/new"]


def test_capped_reads_are_recorded_as_skipped_not_counted(store):
    record_read(store, source="https://hog.example/x", query="q", concern_id=None,
                claims_kept=0, quarantined=0, skipped="share_cap")
    assert shares(store) == {}      # a declined read is not part of the diet
    assert store.execute(
        "SELECT skipped FROM ingest_log").fetchone()["skipped"] == "share_cap"


# ── robots.txt (S2 §9.1 citizenship) ─────────────────────────────────────

def test_documented_apis_are_not_treated_as_crawlable():
    cache = RobotsCache()
    for url in ("https://export.arxiv.org/api/query?x=1",
                "https://api.openalex.org/works?search=x",
                "https://efts.sec.gov/LATEST/search-index?q=x"):
        assert cache.allows(url)


def test_a_disallowing_robots_is_obeyed(monkeypatch):
    import newz.world.robots as robots_mod

    class Resp:
        status_code = 200
        text = "User-agent: *\nDisallow: /private/"

    monkeypatch.setattr(robots_mod.httpx, "get", lambda *a, **k: Resp())
    cache = RobotsCache()
    assert not cache.allows("https://example.org/private/thing")
    assert cache.allows("https://example.org/public/thing")


def test_an_unreachable_robots_is_permissive_not_fatal(monkeypatch):
    import newz.world.robots as robots_mod

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(robots_mod.httpx, "get", boom)
    # A transient error must not look like a prohibition.
    assert RobotsCache().allows("https://example.org/anything")


def test_the_fetcher_refuses_a_disallowed_url():
    from newz.world.sources import Fetcher

    class DenyAll:
        def allows(self, url):
            return False

    try:
        Fetcher(robots=DenyAll()).get("https://example.org/x")
        raised = False
    except PermissionError:
        raised = True
    assert raised


# ── R2: the cap counts distinct sources, not reads ───────────────────────
#
# Measured 2026-08-14. shares()/over_share() counted ingest_log ROWS, and
# before R1 the research path re-fetched the same urls every cycle: 24
# non-skipped reads of which 12 were duplicates. That drove openalex to 33%
# and wikipedia to 29% against a 22% cap, so both were refused — and the
# concern that triggered the read got nothing and restated its previous
# conclusion (novelty -0.00). The cap's parameters were never wrong; its
# input was.

def _one(store, outlet, url, skipped=None):
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined, skipped) VALUES (?,?,?,NULL,NULL,1,0,?)",
        (time.time(), outlet, f"{outlet}:{url}", skipped))
    store.commit()


def test_reading_the_same_page_twice_is_not_two_items_of_diet(store):
    for _ in range(6):
        _one(store, "openalex", "https://doi.org/same")
    _one(store, "arxiv", "https://arxiv.org/abs/1")
    s = shares(store)
    # 1 distinct openalex source and 1 arxiv -> half each, not 6/7ths.
    assert s["openalex"] == 0.5 and s["arxiv"] == 0.5


def test_duplicates_cannot_manufacture_a_concentration(store):
    # 24 rows, but only 4 distinct sources: below MIN_ITEMS_FOR_CAP, so the
    # cap correctly does not fire at all. This is the exact shape of the
    # 2026-08-14 lockout.
    for i in range(4):
        for _ in range(6):
            _one(store, "openalex", f"https://doi.org/{i}")
    assert store.execute(
        "SELECT COUNT(*) FROM ingest_log").fetchone()[0] == 24
    assert not over_share(store, "openalex")


def test_a_genuine_concentration_still_fires(store):
    # 24 DISTINCT sources, 20 of them one outlet. That is a real imbalance
    # and the cap must still catch it — R2 must not disarm the guard.
    # Enough outlets that the cap is meaningful: effective_cap is
    # max(0.10, 2/n_outlets), so a two-outlet corpus has a 100% cap by
    # design (a flat cap would block every outlet at once).
    for i in range(20):
        _one(store, "openalex", f"https://doi.org/{i}")
    for n in range(10):
        _one(store, f"outlet{n}", f"https://outlet{n}.org/a")
    assert over_share(store, "openalex")      # 20 of 30, cap is 2/11
    assert not over_share(store, "outlet0")


def test_share_capped_rows_are_still_excluded(store):
    # A capped row is accounting, not reading — it was never diet.
    for i in range(20):
        _one(store, "openalex", f"https://doi.org/{i}", skipped="share_cap")
    assert shares(store) == {}


# ── did the reading change anything? (TRUE_NORTH §4.3) ───────────────────
#
# "Development matters more than activity. More reading, output, memory, or
# uptime does not matter unless experience produces justified change." §10
# names output volume among what will NOT be mistaken for success.
#
# v1's damning number was never its 84,793 stored claims — it was that
# 0.066% were ever cited. That was uncomputable in v2 until C1 let an advance
# cite what it had read. Baseline at the moment this shipped: 0 of 20.

def _advance_citing(store, concern_id, refs):
    import json as _json
    store.execute(
        "INSERT OR IGNORE INTO concerns (id, opened_at, kind, statement,"
        " why_open, closing_condition, status, salience, origin)"
        " VALUES (?,0,'inquiry','q','w','c','open',0.5,'curiosity')", (concern_id,))
    store.execute(
        "INSERT INTO concern_advances (concern_id, ts, kind, summary,"
        " evidence_json, source_ref) VALUES (?,?,'evidence','s',?,'deliberation')",
        (concern_id, time.time(), _json.dumps(refs)))
    store.commit()


def test_a_source_no_advance_ever_used_is_uncited(store):
    _one(store, "openalex", "https://doi.org/a")
    r = citation_rate(store)
    assert (r.read, r.cited) == (1, 0)
    assert r.rate == 0.0
    assert "openalex:https://doi.org/a" in r.uncited


def test_a_source_cited_by_its_src_label_counts(store):
    _one(store, "openalex", "https://doi.org/a")
    row_id = store.execute("SELECT id FROM ingest_log").fetchone()[0]
    _advance_citing(store, 111, [f"src-{row_id}"])
    r = citation_rate(store)
    assert (r.read, r.cited) == (1, 1) and r.rate == 1.0


def test_a_source_cited_by_its_url_also_counts(store):
    # A model will use either label, so both are accepted (C1).
    _one(store, "openalex", "https://doi.org/a")
    _advance_citing(store, 111, ["https://doi.org/a"])
    assert citation_rate(store).cited == 1


def test_a_setback_does_not_count_as_using_a_source(store):
    # An advance that was rejected changed nothing, which is the whole point
    # of measuring citation rather than reading.
    _one(store, "openalex", "https://doi.org/a")
    store.execute(
        "INSERT OR IGNORE INTO concerns (id, opened_at, kind, statement,"
        " why_open, closing_condition, status, salience, origin)"
        " VALUES (111,0,'inquiry','q','w','c','open',0.5,'curiosity')")
    store.execute(
        "INSERT INTO concern_setbacks (concern_id, ts, kind, brief, source_ref)"
        " VALUES (111,?,'restated','restates an earlier advance','deliberation')",
        (time.time(),))
    store.commit()
    assert citation_rate(store).cited == 0


def test_duplicate_reads_do_not_inflate_the_denominator(store):
    # Same discipline as R2: reading a page six times is one source.
    for _ in range(6):
        _one(store, "openalex", "https://doi.org/a")
    assert citation_rate(store).read == 1


def test_capped_reads_are_not_in_the_denominator(store):
    # The being never saw them, so they cannot have failed to be useful.
    _one(store, "openalex", "https://doi.org/a", skipped="share_cap")
    assert citation_rate(store).read == 0
    assert "nothing read" in citation_rate(store).render()


# ── the cap never returns nothing (2026-08-15) ───────────────────────────
#
# Measured overnight 2026-08-14: concern 102 reached for the world seven
# times and touched nothing, concern 59 once and touched nothing — every
# candidate over-cap, every cycle booked as "I could not move this". S2 §13
# specifies a *target* reviewed "at source-add/remove time", and TRUE_NORTH
# §8 says "do not manufacture balance after the fact". Refusing the only
# source able to answer is exactly that.


def test_when_every_candidate_is_over_cap_the_best_one_is_read_anyway(store):
    _read(store, "https://hog.example", n=MIN_ITEMS_FOR_CAP)
    for host in ("a", "b", "c", "d"):
        _read(store, f"https://{host}.example", n=5)

    class R:
        def __init__(self, url):
            self.url, self.source = url, "feed"

    # Both from the over-represented outlet: there is no alternative to prefer.
    results = [R("https://hog.example/first"), R("https://hog.example/second")]
    keep, capped = apply_share_caps(store, results, source_of=lambda r: r.url)
    assert [r.url for r in keep] == ["https://hog.example/first"]
    assert [r.url for r in capped] == ["https://hog.example/second"]


def test_only_one_over_cap_read_is_promoted(store):
    # Not a repeal. 29 capped reads at ~2,600 ingest tokens each would take
    # ingest from 96,366 to ~172,000 against earning of 96,089 — a permanent
    # §9.1 breach, which stops ALL reading rather than some of it.
    _read(store, "https://hog.example", n=MIN_ITEMS_FOR_CAP)
    for host in ("a", "b", "c", "d"):
        _read(store, f"https://{host}.example", n=5)

    class R:
        def __init__(self, url):
            self.url, self.source = url, "feed"

    results = [R(f"https://hog.example/{i}") for i in range(6)]
    keep, capped = apply_share_caps(store, results, source_of=lambda r: r.url)
    assert len(keep) == 1 and len(capped) == 5


def test_an_available_alternative_still_wins_outright(store):
    # The pressure survives the promotion: nothing over-cap is read while an
    # under-represented source can answer.
    _read(store, "https://hog.example", n=MIN_ITEMS_FOR_CAP)
    for host in ("a", "b", "c", "d"):
        _read(store, f"https://{host}.example", n=5)

    class R:
        def __init__(self, url):
            self.url, self.source = url, "feed"

    results = [R("https://hog.example/new"), R("https://fresh.example/new")]
    keep, capped = apply_share_caps(store, results, source_of=lambda r: r.url)
    assert [r.url for r in keep] == ["https://fresh.example/new"]
    assert [r.url for r in capped] == ["https://hog.example/new"]


def test_nothing_to_promote_when_nothing_was_capped(store):
    class R:
        def __init__(self, url):
            self.url, self.source = url, "feed"

    results = [R("https://fresh.example/a")]
    keep, capped = apply_share_caps(store, results, source_of=lambda r: r.url)
    assert len(keep) == 1 and capped == []
