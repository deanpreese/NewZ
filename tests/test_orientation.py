"""The orientation pass (P3 epic E1.0).

The `web` section of feeds.yaml — 15 Wikipedia discipline overviews the
operator curated and no code ever loaded, because `load_feeds()` is only ever
called with `kind="rss"`. They are static articles, not streams: read once, as
a map of fields the being has none of.
"""

from __future__ import annotations

import textwrap

from newz.world.orientation import OUTLET, orientation_targets, run_orientation

from tests.conftest import FakeLLM

FEEDS_YAML = textwrap.dedent("""
    rss:
      - name: A feed
        url: https://example.org/feed.xml
        category: markets
    web:
      - name: Wikipedia Philosophy
        url: https://en.wikipedia.org/wiki/Philosophy
        category: philosophy
      - name: Reddit Somewhere
        url: https://www.reddit.com/r/Somewhere/
        category: social
""")

PHILOSOPHY_ARTICLE = (
    "Philosophy is the systematic study of general and fundamental questions "
    "concerning existence, knowledge, values, reason, mind and language. It is "
    "distinguished from other ways of addressing these questions by being "
    "critical and generally systematic, and by its reliance on rational "
    "argument. The word derives from the Greek for love of wisdom. Major "
    "branches include metaphysics, epistemology, ethics, logic and aesthetics, "
    "each of which asks a different kind of question about the same world. "
) * 6

CLAIMS = ('<extraction>'
          '<claim confidence="0.8">Philosophy studies fundamental questions '
          'about existence, knowledge and value.</claim>'
          '<manipulation>none</manipulation>'
          '</extraction>')


def _feeds_file(tmp_path):
    p = tmp_path / "feeds.yaml"
    p.write_text(FEEDS_YAML)
    return p


def test_social_sources_are_excluded_by_default(tmp_path):
    """User-generated content is the injection surface INV-011 exists for, and
    scraping it raises questions the sovereign-adapter discipline has not
    answered. The operator can opt in; nothing opts in for them."""
    targets = orientation_targets(_feeds_file(tmp_path))

    assert [t[0] for t in targets] == ["Wikipedia Philosophy"]
    assert len(orientation_targets(_feeds_file(tmp_path), include_social=True)) == 2


def test_it_reads_the_overview_and_records_it_under_its_own_outlet(store, tmp_path):
    """Wikipedia is already the largest read source at 95 DIRECTED lookups. If
    browsing logged as lookup, the coverage audit and the category shares would
    both be corrupted and the project would claim breadth it had not gained."""
    llm = FakeLLM([("AMBIENT", CLAIMS)])

    report = run_orientation(llm, store, _feeds_file(tmp_path),
                             fetcher=_fetcher(PHILOSOPHY_ARTICLE))

    assert report.read == ["Wikipedia Philosophy"]
    row = store.execute("SELECT source FROM ingest_log").fetchone()
    assert row["source"].startswith(OUTLET + ":")
    logged = store.execute("SELECT category, was_read FROM harvest_log").fetchone()
    assert logged["category"] == "philosophy" and logged["was_read"] == 1


def test_an_overview_already_read_is_not_read_again(store, tmp_path):
    """A discipline overview is not news. Re-reading costs tokens and writes a
    duplicate episode."""
    llm = FakeLLM([("AMBIENT", CLAIMS)])
    fetcher = _fetcher(PHILOSOPHY_ARTICLE)
    run_orientation(llm, store, _feeds_file(tmp_path), fetcher=fetcher)

    report = run_orientation(llm, store, _feeds_file(tmp_path), fetcher=fetcher)

    assert report.skipped == ["Wikipedia Philosophy"]
    assert report.read == []


def test_an_unreachable_article_costs_that_article_and_not_the_pass(store, tmp_path):
    """Every fetch failure collapses to "nothing readable" by construction —
    INV-040's rule that a failed read costs the read and nothing else."""
    class Boom:
        def get(self, url, **kw):
            raise RuntimeError("unreachable")

    report = run_orientation(FakeLLM([]), store, _feeds_file(tmp_path), fetcher=Boom())

    assert report.read == []
    assert report.failed == ["Wikipedia Philosophy: nothing readable"]


def _fetcher(body: str):
    class F:
        def get(self, url, **kw):
            return body
    return F()


def test_a_long_article_is_chunked_rather_than_truncated(store, tmp_path):
    """MEASURED LIVE 2026-08-18: a 6,000-char article in one extract call blew
    the 900-token output cap on 7 of 14 articles, and extraction fails closed on
    truncation because <manipulation> is the schema's last element. The failure
    was right; the whole-article call was not."""
    long_article = PHILOSOPHY_ARTICLE * 4          # several chunks' worth
    llm = FakeLLM([("AMBIENT", CLAIMS)] * 12)

    report = run_orientation(llm, store, _feeds_file(tmp_path),
                             fetcher=_fetcher(long_article))

    assert report.read == ["Wikipedia Philosophy"]
    assert len(llm.calls) > 1


def test_one_hostile_chunk_quarantines_the_whole_overview(store, tmp_path):
    """INV-042, as research honours it: a page whose halves split an
    instruction across a boundary must not contribute its clean chunks."""
    hostile = ('<extraction><claim confidence="0.9">A plausible claim.</claim>'
               '<manipulation>the page instructed the reader</manipulation>'
               '</extraction>')
    llm = FakeLLM([("AMBIENT", CLAIMS), ("AMBIENT", hostile),
                   ("AMBIENT", CLAIMS), ("AMBIENT", CLAIMS)])

    report = run_orientation(llm, store, _feeds_file(tmp_path),
                             fetcher=_fetcher(PHILOSOPHY_ARTICLE * 4))

    assert report.read == []
    assert "quarantined" in report.failed[0]
    assert store.execute("SELECT COUNT(*) FROM episodes WHERE kind='reading'"
                         ).fetchone()[0] == 0
