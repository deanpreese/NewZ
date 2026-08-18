"""Sovereign source adapters (S2 §9.1) — keyless, reputable, no vendor.

Ported with review from v1 (`ngbeing/research/sources.py`, S2 §16 allowlist),
reduced to the adapters that earned their place and made synchronous. These
are the being's route to the world that no company can revoke: Wikipedia,
arXiv, PubMed, OpenAlex. Sovereignty (TRUE_NORTH §7) is why they were chosen
over a search API, and the rate limiter is why they keep working.

Web access happens ONLY inside deliberation (S2 §15.3, INV-012). There is no
import path from ambient to this module, and the test suite asserts it.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
from xml.etree import ElementTree

import httpx

from newz.world.rate_limit import DomainRateLimiter, user_agent

logger = logging.getLogger(__name__)

TIMEOUT = 30.0
MAX_BYTES = 4_000_000
_TAG = re.compile(r"<[^>]+>")


@dataclass
class SearchResult:
    title: str
    summary: str
    url: str
    source: str
    published: str | None = None

    def render(self) -> str:
        when = f", {self.published}" if self.published else ""
        return f"[{self.source}{when}] {self.title}\n  {self.summary[:600]}\n  {self.url}"


def strip_tags(text: str) -> str:
    return " ".join(_TAG.sub(" ", text or "").split())


_QUERY_NOISE = re.compile(r"[^\w\s-]", re.UNICODE)


def clean_query(query: str, *, max_words: int = 16) -> str:
    """Search terms, not a sentence.

    Measured 2026-08-11: OpenAlex 400s on a query containing '?' and
    apostrophes. Concern statements are full questions, so every adapter
    call was carrying punctuation the APIs do not accept as a search term.
    """
    words = _QUERY_NOISE.sub(" ", query or "").split()
    return " ".join(words[:max_words])


class Fetcher:
    """Polite HTTP. Every adapter goes through this, so a new adapter is
    rate-limited by construction rather than by remembering to be."""

    def __init__(self, limiter: DomainRateLimiter | None = None,
                 timeout: float = TIMEOUT, robots=None):
        self._limiter = limiter or DomainRateLimiter()
        self._timeout = timeout
        if robots is None:
            from newz.world.robots import RobotsCache

            robots = RobotsCache()
        self._robots = robots

    def get(self, url: str) -> str:
        if not self._robots.allows(url):
            raise PermissionError(f"robots.txt disallows {url}")
        self._limiter.wait(url)
        with httpx.Client(timeout=self._timeout, follow_redirects=True,
                          headers={"User-Agent": user_agent()}) as client:
            resp = client.get(url)
            if resp.status_code == 429:
                logger.warning("429 from %s — backing off, no retry this pass", url)
                raise httpx.HTTPStatusError("rate limited", request=resp.request,
                                            response=resp)
            resp.raise_for_status()
            return resp.text[:MAX_BYTES]


class WikipediaAdapter:
    name = "wikipedia"

    def __init__(self, fetcher: Fetcher, lang: str = "en"):
        self._f = fetcher
        self._lang = lang

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        base = f"https://{self._lang}.wikipedia.org/w/api.php"
        q = urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": clean_query(query),
            "format": "json", "srlimit": limit})
        try:
            data = json.loads(self._f.get(f"{base}?{q}"))
        except Exception as e:  # noqa: BLE001
            logger.warning("adapter wikipedia FAILED: %s", e)
            return []
        out = []
        for hit in data.get("query", {}).get("search", [])[:limit]:
            title = hit.get("title", "")
            out.append(SearchResult(
                title=title, summary=strip_tags(hit.get("snippet", "")),
                url=f"https://{self._lang}.wikipedia.org/wiki/"
                    + urllib.parse.quote(title.replace(" ", "_")),
                source="wikipedia"))
        return out


class ArxivAdapter:
    name = "arxiv"

    def __init__(self, fetcher: Fetcher):
        self._f = fetcher

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        q = urllib.parse.urlencode({
            "search_query": f"all:{clean_query(query)}", "start": 0, "max_results": limit})
        try:
            xml = self._f.get(f"https://export.arxiv.org/api/query?{q}")
            root = ElementTree.fromstring(xml)
        except Exception as e:  # noqa: BLE001
            logger.warning("adapter arxiv FAILED: %s", e)
            return []
        ns = {"a": "http://www.w3.org/2005/Atom"}
        out = []
        for entry in root.findall("a:entry", ns)[:limit]:
            def text(tag):
                el = entry.find(f"a:{tag}", ns)
                return " ".join((el.text or "").split()) if el is not None else ""
            out.append(SearchResult(
                title=text("title"), summary=text("summary"), url=text("id"),
                source="arxiv", published=text("published")[:10] or None))
        return out


class OpenAlexAdapter:
    name = "openalex"

    def __init__(self, fetcher: Fetcher):
        self._f = fetcher

    @staticmethod
    def _deinvert(index: dict | None) -> str:
        if not index:
            return ""
        positions: list[tuple[int, str]] = []
        for word, spots in index.items():
            positions.extend((p, word) for p in spots)
        return " ".join(w for _, w in sorted(positions))

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        q = urllib.parse.urlencode({"search": clean_query(query), "per-page": limit})
        try:
            data = json.loads(self._f.get(f"https://api.openalex.org/works?{q}"))
        except Exception as e:  # noqa: BLE001
            logger.warning("adapter openalex FAILED: %s", e)
            return []
        out = []
        for work in data.get("results", [])[:limit]:
            summary = self._deinvert(work.get("abstract_inverted_index"))
            out.append(SearchResult(
                title=work.get("title") or work.get("display_name") or "",
                summary=summary or "(no abstract)",
                url=work.get("doi") or work.get("id") or "",
                source="openalex",
                published=str(work.get("publication_year") or "") or None))
        return out


class PubMedAdapter:
    name = "pubmed"
    _BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, fetcher: Fetcher):
        self._f = fetcher

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        q = urllib.parse.urlencode({"db": "pubmed", "retmode": "json",
                                    "retmax": limit, "term": clean_query(query)})
        try:
            ids = json.loads(self._f.get(f"{self._BASE}/esearch.fcgi?{q}")
                             ).get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []
            sq = urllib.parse.urlencode({"db": "pubmed", "retmode": "json",
                                         "id": ",".join(ids)})
            data = json.loads(self._f.get(f"{self._BASE}/esummary.fcgi?{sq}"))
        except Exception as e:  # noqa: BLE001
            logger.warning("adapter pubmed FAILED: %s", e)
            return []
        out = []
        for pmid in ids:
            rec = data.get("result", {}).get(pmid, {})
            if not rec:
                continue
            out.append(SearchResult(
                title=rec.get("title", ""),
                summary=rec.get("source", "") + " — " + rec.get("pubdate", ""),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                source="pubmed", published=rec.get("pubdate")))
        return out


class SecEdgarAdapter:
    """SEC EDGAR full-text search — S2 §9.1's "as evaluated" list.

    Primary sources rather than commentary: what companies actually filed.
    SEC requires a descriptive User-Agent and blocks anonymous clients
    outright, which the shared UA supplies.
    """

    name = "sec_edgar"

    def __init__(self, fetcher: Fetcher):
        self._f = fetcher

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        q = urllib.parse.urlencode({"q": f'"{clean_query(query)}"'})
        try:
            data = json.loads(self._f.get(f"https://efts.sec.gov/LATEST/search-index?{q}"))
        except Exception as e:  # noqa: BLE001
            logger.warning("adapter sec_edgar FAILED: %s", e)
            return []
        out = []
        for hit in (data.get("hits", {}).get("hits") or [])[:limit]:
            src = hit.get("_source", {})
            adsh = (hit.get("_id") or "").split(":")[0].replace("-", "")
            cik = (src.get("ciks") or [""])[0]
            names = src.get("display_names") or []
            out.append(SearchResult(
                title=f"{src.get('form', 'filing')} — {names[0] if names else 'filer'}",
                summary=" ".join(str(x) for x in names) or "(filing)",
                url=(f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{adsh}"
                     if cik and adsh else "https://www.sec.gov/edgar"),
                source="sec_edgar", published=src.get("file_date")))
        return out


class GdeltAdapter:
    """GDELT 2.0 DOC API — S2 §9.1's "as evaluated" list.

    **Evaluated 2026-08-11: NOT enabled by default.** Broad international
    coverage without a vendor relationship, and geographically wider than any
    curated feed list — genuinely attractive for TRUE_NORTH §8 diversity. But
    it 429s persistently at our cadence: one plain query succeeded, and
    repeat calls spaced 5–8 seconds apart were refused, with the service
    asking high-traffic users to switch to its bulk ngrams dataset instead of
    the live API. A source that fails most calls is worse than an absent one,
    because it looks like coverage while contributing nothing.

    Kept, not deleted: the adapter is correct and the limit is theirs, not
    ours. Enable it by passing it explicitly if the cadence is ever resolved,
    or replace it with the ngrams dataset, which is the path they recommend.
    """

    name = "gdelt"

    def __init__(self, fetcher: Fetcher):
        self._f = fetcher

    def search(self, query: str, *, limit: int = 3) -> list[SearchResult]:
        q = urllib.parse.urlencode({
            "clean_query(query)": clean_query(query), "mode": "artlist", "format": "json",
            "maxrecords": max(1, min(limit, 20))})
        try:
            data = json.loads(self._f.get(f"https://api.gdeltproject.org/api/v2/doc/doc?{q}"))
        except Exception as e:  # noqa: BLE001
            logger.warning("adapter gdelt FAILED: %s", e)
            return []
        out = []
        for art in (data.get("articles") or [])[:limit]:
            out.append(SearchResult(
                title=art.get("title", ""),
                summary=f"{art.get('domain', '')} ({art.get('sourcecountry', '?')})",
                url=art.get("url", ""), source="gdelt",
                published=(art.get("seendate") or "")[:8] or None))
        return out


def default_adapters(fetcher: Fetcher | None = None) -> list:
    """The evaluated, enabled set (S2 §9.1).

    GDELT is deliberately absent — see GdeltAdapter for the measurement.
    Wikipedia is present but currently 403s pending a contact address in
    NEWZ_USER_AGENT; it costs one failed call and recovers the moment the
    operator domain exists.
    """
    f = fetcher or Fetcher()
    return [WikipediaAdapter(f), ArxivAdapter(f), OpenAlexAdapter(f),
            PubMedAdapter(f), SecEdgarAdapter(f)]
