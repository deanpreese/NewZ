"""A source that returns numbers, for resolution only (E1.8 follow-on).

Measured 2026-08-29: five retrodictions, ten resolution attempts, zero
settlements, and four of five failures said the material did not contain the
data — *"only bibliographic citations and abstracts"*, *"no data from the
League of Nations Statistical Yearbook"*. The being had no source that returns
a figure, so every claim needing one was unsettleable by construction.

The precondition — can a rendered series survive extraction and INV-047's
verbatim quote — was tested before this was built, and failed the first time
for a reason no adapter could fix: `MIN_USEFUL_CHARS` discarded a 327-character
CSV as a paywall stub.
"""

from __future__ import annotations

import json
from datetime import date

from newz.world.data import FredAdapter, resolution_source, window_for

TODAY = date(2026, 8, 29)

PAYLOAD = json.dumps({"seriess": [
    {"id": "DGS10", "title": "Market Yield on U.S. Treasury Securities at "
                             "10-Year Constant Maturity",
     "units": "Percent", "frequency": "Daily",
     "seasonal_adjustment": "Not Seasonally Adjusted",
     "last_updated": "2026-08-28"},
    {"id": "RRPONTSYD", "title": "Overnight Reverse Repurchase Agreements",
     "units": "Billions of US Dollars", "frequency": "Daily",
     "seasonal_adjustment": "Not Applicable"},
]})


class _Fetcher:
    """Records what was asked for; returns one canned body."""

    def __init__(self, body: str = PAYLOAD):
        self.body, self.urls = body, []

    def get(self, url: str) -> str:
        self.urls.append(url)
        return self.body


# ── the window comes from the claim, mechanically ────────────────────────

def test_a_claim_about_the_past_gets_the_years_it_names():
    """Concern 143's claims are about 1931-33 and a recent window cannot
    settle them. The dates are in the claim; a regex reads them out, and no
    model is asked anything (Rule 4 untouched)."""
    assert window_for("gold standard suspension 1931 versus 1933 recovery",
                      today=TODAY) == ("1930-01-01", "1934-12-31")


def test_a_year_that_has_not_happened_is_a_due_date_not_a_subject():
    """Every forecast the being writes names the year it settles in. Treating
    that as the subject would fetch a window around a date the series has not
    reached."""
    assert window_for("H.4.1 for the week ending 2026-09-02", today=TODAY) \
        == ("2025-07-25", "2026-08-29")


def test_a_claim_naming_no_year_is_about_now():
    lo, hi = window_for("reverse repo facility usage", today=TODAY)
    assert hi == "2026-08-29" and lo < hi


# ── absence is configured, not silent ────────────────────────────────────

def test_without_a_key_it_returns_nothing_and_asks_for_nothing():
    f = _Fetcher()
    a = FredAdapter(f, api_key=None)

    assert a.search("10-year treasury yield") == []
    assert f.urls == [], "no key must mean no request, not a failed one"


def test_without_a_key_there_is_no_adapter_at_all():
    """None rather than an adapter that always returns nothing, so a caller
    can say the source is ABSENT instead of reporting empty as a miss."""
    class Cfg:
        fred_api_key = None

    assert resolution_source(Cfg(), _Fetcher()) is None


def test_with_a_key_the_adapter_exists():
    class Cfg:
        fred_api_key = "k"

    assert resolution_source(Cfg(), _Fetcher()) is not None


# ── what it returns is a document, not a summary standing in for one ─────

def test_each_series_becomes_a_fetchable_csv_document():
    f = _Fetcher()
    got = FredAdapter(f, api_key="k").search(
        "industrial production 1931 versus 1933")

    assert [r.source for r in got] == ["fred", "fred"]
    assert "fredgraph.csv" in got[0].url and "id=DGS10" in got[0].url
    # The window from the claim travels into the url that will be fetched.
    assert "cosd=1930-01-01" in got[0].url and "coed=1934-12-31" in got[0].url


def test_the_summary_carries_meaning_and_not_the_data():
    """The rows say only "date,value"; a verdict quoting 4.74 needs to know it
    is a percent. What the summary must NOT do is stand in for the document —
    the url is fetched and the numbers come from there."""
    got = FredAdapter(_Fetcher(), api_key="k").search("10-year treasury")

    assert "Percent" in got[0].summary and "Daily" in got[0].summary
    assert "4.74" not in got[0].summary


def test_the_key_is_sent_and_the_query_is_cleaned():
    f = _Fetcher()
    FredAdapter(f, api_key="secret").search("what is the 10-year yield?")

    assert len(f.urls) == 1
    assert "api_key=secret" in f.urls[0]
    # clean_query strips punctuation the APIs reject (measured 2026-08-11).
    assert "%3F" not in f.urls[0] and "?" not in f.urls[0].split("?", 1)[1]


def test_an_adapter_failure_is_never_a_resolution_failure():
    """Same contract as every other adapter: one source answering nothing,
    not a pass that raises."""
    class Broken:
        _f = None

        def get(self, url):
            raise RuntimeError("api down")

    assert FredAdapter(Broken(), api_key="k").search("anything") == []


# ── wired for resolution only ────────────────────────────────────────────

def test_it_is_not_on_the_ordinary_reading_path():
    """The being's diet is already 43% financial off a 15% financial
    curation. On the reading path FRED would deepen exactly the monoculture
    E1.0 exists to break; on the resolution path it settles claims the being
    has already made."""
    import inspect

    from newz.world import sources

    assert "fred" not in inspect.getsource(sources.default_adapters).lower()


def test_the_numeric_source_leads_the_resolution_order(store, monkeypatch):
    """`research()` dedupes by url in adapter order and MAX_EXTRACTIONS bounds
    how many documents are read, so order decides which source survives to be
    read — and for a claim naming a figure, the series is the only thing that
    can settle it."""
    import newz.config as config
    from newz.resolutions.resolver import _resolution_adapters

    real = config.load

    def keyed(*a, **kw):
        cfg = real(*a, **kw)
        object.__setattr__(cfg, "fred_api_key", "k")
        return cfg

    monkeypatch.setattr(config, "load", keyed)
    names = [a.name for a in _resolution_adapters(store, None)]

    assert names[0] == "fred"
    assert names[1] == "harvest"
