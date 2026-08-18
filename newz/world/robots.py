"""robots.txt compliance (S2 §9.1 citizenship rules).

The sovereign adapters call documented public APIs, which robots.txt does
not govern — but the moment anything fetches a page rather than an endpoint,
it does. This exists so that path cannot be added later without the check,
which is how v1's rate limiting came to be missing until arXiv started
returning 429s.

Fail-closed on an unreadable robots.txt would make every transient network
error look like a prohibition, so an unfetchable file is treated as
permissive — that is the documented convention — while a fetched file that
denies us is obeyed exactly.
"""

from __future__ import annotations

import logging
import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx

from newz.world.rate_limit import user_agent

logger = logging.getLogger(__name__)

CACHE_TTL_S = 3600.0
# Hosts that are documented APIs rather than crawlable sites. Listed
# explicitly so that adding one is a decision rather than an oversight.
API_HOSTS = frozenset({
    "export.arxiv.org", "api.openalex.org", "eutils.ncbi.nlm.nih.gov",
    "api.crossref.org", "en.wikipedia.org", "efts.sec.gov",
    "api.gdeltproject.org", "data.sec.gov",
})


class RobotsCache:
    def __init__(self, ttl: float = CACHE_TTL_S):
        self._ttl = ttl
        self._cache: dict[str, tuple[float, urllib.robotparser.RobotFileParser | None]] = {}

    def _parser(self, host: str, scheme: str):
        hit = self._cache.get(host)
        if hit and (time.monotonic() - hit[0]) < self._ttl:
            return hit[1]
        parser = urllib.robotparser.RobotFileParser()
        try:
            resp = httpx.get(f"{scheme}://{host}/robots.txt", timeout=10,
                             headers={"User-Agent": user_agent()})
            if resp.status_code >= 400:
                parser = None            # no robots.txt: permissive
            else:
                parser.parse(resp.text.splitlines())
        except Exception as e:  # noqa: BLE001
            logger.debug("robots.txt unreadable for %s (%s) — treating as permissive",
                         host, e)
            parser = None
        self._cache[host] = (time.monotonic(), parser)
        return parser

    def allows(self, url: str) -> bool:
        parts = urlparse(url)
        host = (parts.hostname or "").lower()
        if not host or host in API_HOSTS:
            return True
        parser = self._parser(host, parts.scheme or "https")
        if parser is None:
            return True
        allowed = parser.can_fetch(user_agent(), url)
        if not allowed:
            logger.info("robots.txt disallows %s — not fetching", url)
        return allowed
