"""A source that returns numbers, consulted only when resolving a claim.

**What this closes.** Measured 2026-08-29: five retrodictions, ten resolution
attempts, zero settlements, and four of the five failures say the same thing —
*"only bibliographic citations and abstracts"*, *"no data from the League of
Nations Statistical Yearbook"*, *"it does not provide the specific industrial
production index data"*. The being kept writing claims that need a figure, and
**it had no source that returns one**: six adapters that index encyclopedia
entries and papers, and 61 feeds of news and essays. Every claim needing a
number was unsettleable by construction, including the forecasts naming the Fed
H.4.1, the NY Fed H.15 and ICE DXY.

**The precondition was tested before this was built**, and it failed the first
time for a reason no adapter could have fixed: a FRED CSV carrying a month of
daily 10-year yields is 327 characters, and `MIN_USEFUL_CHARS` discarded it as a
paywall stub. With that corrected, `tools/resolver_probe.py --settleable` settles
a numeric claim in both directions — held and contradicted — so a rendered series
does survive fetch, extraction and INV-047's verbatim quote. This module is worth
having because that was checked, not because it was assumed.

**Resolution only, and that is what makes it safe.** The being's diet is already
43% financial off a curation that is 15% financial, and FRED is macro data: on
the reading path it would deepen exactly the monoculture E1.0 exists to break.
On the resolution path it settles claims the being has already made and touches
nothing about what it chooses to read. Same design as `HarvestAdapter`, same
reason.

**No hand-authored mapping, and no scraping around robots.** A table from
keywords to series ids would be a second registry to maintain and would encode
the operator's guess about which series answers what. FRED's own search page is
`Disallow`ed in robots.txt and is therefore not an option — the API host is
allowed (`crawl-delay: 2`) and is what this uses. It needs a free key, and
without one the adapter returns nothing and says so once: honest absence rather
than a fallback that pretends.

**The window comes from the claim, mechanically.** A claim about 1931 and one
about next week need different spans of the same series, and the dates are in
the claim's own text. Years are read out of the query with a regex; nothing is
asked of a model, so Rule 4 is untouched and no judgment about the claim is made
here.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
from datetime import date, timedelta

from newz.world.sources import SearchResult, clean_query

logger = logging.getLogger(__name__)

API = "https://api.stlouisfed.org/fred/series/search"
CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# How many series a query may pull. The resolver reads at most
# MAX_EXTRACTIONS documents anyway, and a series is a heavier read than an
# abstract — each one is a table the extractor walks row by row.
MAX_SERIES = 3

# Without dates in the claim, the recent past. A claim with no year in it is
# about now, and a whole series would be truncated at MAX_DOC_CHARS from the
# OLDEST end, which is the wrong half for a claim about this month.
DEFAULT_WINDOW_DAYS = 400

# Padding around the years a claim names, so a claim about "1931 versus 1933"
# gets the run-up and the aftermath rather than exactly the endpoints.
YEAR_PAD = 1

_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")


def window_for(query: str, *, today: date | None = None) -> tuple[str, str]:
    """The span of series to fetch, read out of the claim's own text.

    Returns (start, end) as ISO dates. A claim naming years is about those
    years; one naming none is about now.
    """
    today = today or date.today()
    years = sorted({int(y) for y in _YEAR.findall(query or "")})
    # A year that is this year or later is a due date, not a subject: every
    # forecast the being writes names one, and treating it as the subject
    # would fetch a window around a date the series has not reached.
    past = [y for y in years if y < today.year]
    if not past:
        return (today - timedelta(days=DEFAULT_WINDOW_DAYS)).isoformat(), today.isoformat()
    lo, hi = min(past) - YEAR_PAD, min(max(past) + YEAR_PAD, today.year)
    return f"{lo}-01-01", f"{hi}-12-31"


class FredAdapter:
    """FRED series as documents, for the resolution pass only.

    Duck-typed to the adapter protocol in `newz/world/sources.py`: a `name`
    and `search(query, *, limit)` returning `SearchResult`. It carries the
    shared `Fetcher` under `_f` for the same reason the others do — robots and
    the per-domain rate limit apply to a data API exactly as they do to a
    news site, and FRED asks for a two-second crawl delay.
    """

    name = "fred"

    def __init__(self, fetcher, api_key: str | None, *,
                 max_series: int = MAX_SERIES):
        self._f = fetcher
        self._key = (api_key or "").strip()
        self._max = max_series
        self._warned = False

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        if not self._key:
            if not self._warned:
                # Once per adapter, not once per call: a resolution pass asks
                # three queries and three identical lines say no more than one.
                logger.info("fred: no FRED_API_KEY — the one numeric source is "
                            "unavailable, so claims needing a figure cannot be "
                            "settled from data")
                self._warned = True
            return []

        q = urllib.parse.urlencode({
            "search_text": clean_query(query), "api_key": self._key,
            "file_type": "json", "limit": min(limit, self._max),
            "order_by": "popularity", "sort_order": "desc"})
        try:
            payload = json.loads(self._f.get(f"{API}?{q}"))
        except Exception as e:  # noqa: BLE001
            # Same contract as every other adapter: a failure is one adapter
            # answering nothing, never a resolution pass that raises.
            logger.info("adapter fred FAILED: %s", e)
            return []

        cosd, coed = window_for(query)
        out: list[SearchResult] = []
        for s in (payload.get("seriess") or [])[:self._max]:
            sid = s.get("id")
            if not sid:
                continue
            url = f"{CSV}?{urllib.parse.urlencode({'id': sid, 'cosd': cosd, 'coed': coed})}"
            title = s.get("title") or sid
            out.append(SearchResult(
                title=f"{title} ({sid})",
                # The summary carries what the numbers MEAN — units, frequency,
                # span — because the rows themselves say only "date,value" and
                # a verdict quoting 4.74 needs to know it is a percent. What it
                # does not do is stand in for the data: the document is fetched.
                summary=(f"FRED series {sid}. {title}."
                         f" Units: {s.get('units') or 'unstated'}."
                         f" Frequency: {s.get('frequency') or 'unstated'}."
                         f" Seasonal adjustment: {s.get('seasonal_adjustment') or 'unstated'}."
                         f" Observations returned for {cosd} to {coed}."),
                url=url, source="fred",
                published=s.get("last_updated")))
        if out:
            logger.info("fred: %d series for %s [%s..%s]",
                        len(out), clean_query(query)[:60], cosd, coed)
        return out


def resolution_source(cfg, fetcher) -> "FredAdapter | None":
    """The adapter, or None when the project has no key configured.

    None rather than an adapter that always returns nothing, so a caller can
    say the source is absent instead of reporting an empty result as a miss.
    """
    key = getattr(cfg, "fred_api_key", None)
    return FredAdapter(fetcher, key) if key else None
