"""The being's own harvest, searchable when a claim is being settled (E1.8).

**What this closes.** `resolve_claim` reaches for the world through
`research()`, which consults `default_adapters()` — Wikipedia, arXiv, OpenAlex,
PubMed, SEC EDGAR. None of them indexes an RSS feed, and nothing anywhere on
that path reads `harvest_log`. So the being's 61 subscribed feeds are invisible
to the one mechanism that exists to tell it that it was wrong.

Measured 2026-08-28, and it is the whole argument. `tools/resolver_probe.py`
ran the three claims due 2026-09-02 and all three reached H3: the resolver
executes end to end, retrieval succeeds, and the material honestly does not
settle the claim — *"the material defines what the H.4.1 report is but does not
contain the specific data values."* It had found Wikipedia's article ABOUT the
H.4.1 release, because Wikipedia is what it can search. Meanwhile:

    data/feeds.yaml:3   Federal Reserve press releases, enabled
    harvest_log         6 items, 6 offered, 0 read
                        2026-08-19  "Minutes of the Federal Open Market
                                     Committee, July 28-29"

and claim 22's resolver is, in its own words, *"Federal Open Market Committee
(FOMC) Statement or Meeting Minutes"*. **The document it needed had already
arrived.** The being does not name unreachable sources; the resolver looks
somewhere else.

**Resolution only, and that is a design decision rather than a scope cut.** A
feed item already reaches the being through the menu that E1.0 built, where it
chooses what is worth reading. Putting the harvest on the ordinary research
path too would offer the same item through two doors, count it twice against
§9.1's diet, and change the reading rhythm — which is not what a fix to the
resolver is allowed to do. Here the item is not being offered as something to
read; it is being asked whether it settles a claim the being already made.

**Matched on what the feed published, not on a mapping.** A hand-authored
table from resolver names to feeds would be a second registry to maintain and
would encode the operator's guess about which source answers what. The match is
term overlap between the claim's resolver and the item's title and feed name,
which is the same shape as every other adapter: a query in, ranked results out,
and the relevance floor and triage downstream deciding what is actually worth
reading. Rule 4 is not engaged — no model judges anything here, and matching a
resolver to a feed the operator already curated is mechanical.

**It ranks; it does not decide.** Everything this returns still passes through
the 0.35 embedding floor, the triage call, the share caps and INV-047's
verbatim check. This adds a place to look, and takes no decision away from the
mechanisms that already exist.
"""

from __future__ import annotations

import logging
import re
import sqlite3

from newz.world.sources import SearchResult, clean_query

logger = logging.getLogger(__name__)

# Below this many shared terms an overlap is a coincidence: "report", "the",
# "data" match half the corpus. Two content words is the point at which a
# resolver and a headline are talking about the same thing — "federal reserve",
# "crop production", "monetary policy" — and it is deliberately not tuned
# against the current claim set, which would fit a threshold to eight rows.
MIN_SHARED_TERMS = 2

# How far back the harvest is worth searching. Feeds are a stream and a claim
# is settled by what was published near its date; an item from six months ago
# that shares two words with the resolver is noise. 90 days covers the 45-day
# horizon ceiling twice over, so a claim's whole life is in the window.
WINDOW_DAYS = 90.0

# Terms that carry no information about which source published something.
# Derived by function rather than authored by topic: they are the words that
# appear in resolver strings AS resolver strings — the noun for "a document" —
# and excluding them is what stops every claim matching every press release.
# Nothing here names a subject, so nothing here can shape what the being is
# able to be right or wrong about.
_STRUCTURAL = frozenset("""
    report reports release releases statement statements data dataset
    publication published publishes official final version number date
    quarterly monthly weekly daily annual
""".split())

# Closed-class function words. Measured 2026-08-28 and this is why they are
# here: without them the feed "The Hindu" matched eight of the thirty-one open
# claims on the word "the" alone — "The specific report on...", "Official
# Journal of the European Union" — and the harvest offered Indian domestic
# politics as the source that would settle an EU regulation. These are
# grammatical, not topical: no subject is excluded by removing an article, so
# nothing here shapes what the being can be right or wrong about.
_FUNCTION = frozenset("""
    the and for its was are has have with from that this than then there
    into onto over under about above below between during against upon
    all any both each more most other some such only own same too very
    not nor but out off per via not
""".split())

_WORD = re.compile(r"[a-z][a-z0-9.\-']{2,}")


def _terms(text: str) -> set[str]:
    """Content terms, lowercased, function and structural words removed.

    Three characters is the floor rather than four, deliberately: `imf`, `cme`,
    `esg` and `eur` are the publishers this is matching against, and a length
    rule that discards them to catch `the` costs more than it saves.
    """
    return {w for w in _WORD.findall((text or "").lower())
            if w not in _STRUCTURAL and w not in _FUNCTION}


class HarvestAdapter:
    """The being's subscribed feeds, as a search source.

    Duck-typed to the adapter protocol in `newz/world/sources.py`: a `name`
    and `search(query, *, limit)` returning `SearchResult`. It carries a
    `Fetcher` under `_f` for the same reason the others do — `_fetcher_for`
    finds it there, so a document this returns is fetched through the polite
    machinery rather than around it.
    """

    name = "harvest"

    def __init__(self, conn: sqlite3.Connection, fetcher=None, *,
                 window_days: float = WINDOW_DAYS,
                 min_shared: int = MIN_SHARED_TERMS):
        self._conn = conn
        self._f = fetcher
        self._window = window_days
        self._min = min_shared

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        terms = _terms(clean_query(query, max_words=40))
        if not terms:
            return []
        try:
            rows = self._conn.execute(
                "SELECT ts, feed, title, url FROM harvest_log"
                " WHERE ts >= (strftime('%s','now') - ?) AND url <> ''"
                " ORDER BY ts DESC",
                (self._window * 86400.0,)).fetchall()
        except sqlite3.Error as e:  # noqa: BLE001
            # A store without the table, or mid-migration. The harvest is an
            # addition to where the resolver looks; it may never be the reason
            # a resolution pass fails.
            logger.info("harvest search unavailable: %s", e)
            return []

        scored: list[tuple[int, float, SearchResult]] = []
        for row in rows:
            ts, feed, title, url = (row[0], row[1], row[2], row[3])
            # **The resolver names a publisher, so the publisher must match.**
            # A claim says the H.4.1 release will show something, and only the
            # Federal Reserve can show it — a headline elsewhere that happens
            # to share two words is commentary, not the source. Measured
            # 2026-08-28: without this, claims 21 and 31 ranked a Bloomberg
            # Opinion column above the Federal Reserve's own feed.
            if not (terms & _terms(feed)):
                continue
            shared = terms & _terms(f"{feed} {title}")
            if len(shared) < self._min:
                continue
            scored.append((len(shared), ts, SearchResult(
                title=title,
                # The feed gave a headline and a link, never a body. Saying so
                # is better than synthesising a summary the item does not have:
                # `read_document` fetches the url and that is where the text
                # comes from (INV-044's discipline, applied to a field).
                summary=f"{feed} published this; the item itself is at the url.",
                url=url, source=feed)))

        # Most terms shared first, then most recent. A claim is settled by the
        # publication nearest its date, and two items from one feed sharing the
        # same terms are the same story told twice.
        scored.sort(key=lambda s: (-s[0], -s[1]))
        out = [r for _, _, r in scored[:limit]]
        if out:
            logger.info("harvest: %d of %d item(s) match the resolver",
                        len(out), len(rows))
        return out
