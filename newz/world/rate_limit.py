"""Per-domain rate limiting for the sovereign adapters.

Ported with review from v1 (`ngbeing/research/rate_limit.py`, S2 §16
allowlist). Verbatim in substance; the reasoning is kept because it is the
kind of thing a later reader deletes as ceremony:

Being a good citizen of free, keyless, publicly-funded APIs is not
incidental politeness. These sources are what make substrate sovereignty
possible without a vendor — getting the being blocked from them would cost
the project the very thing it chose them for. v1 learned this when arXiv
started returning 429s and research, its only route to acquiring a concern,
silently degraded.

A minimum interval rather than a token bucket, deliberately: these APIs
publish sustained-rate guidance rather than burst allowances, and a bucket
permits exactly the opening burst that trips a 429 on a cold start.

Review change: sync rather than async, matching v2's research path, which
runs inside deliberation on a worker thread.
"""

from __future__ import annotations

import logging
import threading
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Published guidance per host, in seconds between requests.
DEFAULT_MIN_INTERVALS: dict[str, float] = {
    "export.arxiv.org": 3.0,      # asks ~1 req/3s and enforces it with 429s
    "arxiv.org": 3.0,
    "eutils.ncbi.nlm.nih.gov": 0.4,   # 3 req/s without a key; 0.4 is under
    "api.openalex.org": 0.2,          # permissive in the polite pool
    "api.crossref.org": 0.2,
    "en.wikipedia.org": 0.2,
    # Measured 2026-08-11: GDELT 429'd on the very first request at the 1.0s
    # fallback. Its DOC API is generous on volume but strict on cadence.
    "api.gdeltproject.org": 5.0,
    # SEC asks for no more than 10 req/s and blocks anonymous clients
    # outright; the descriptive User-Agent above is what keeps it working.
    "efts.sec.gov": 0.5,
    "www.sec.gov": 0.5,
    "data.sec.gov": 0.5,
}

# Any host not named above. Conservative on purpose: adding an adapter must
# not be able to introduce an unthrottled path by omission.
FALLBACK_MIN_INTERVAL = 1.0

# Identify ourselves. The polite pools require it, and an anonymous client
# is the first thing these services throttle.
#
# Wikipedia's User-Agent policy is stricter than the others and wants a
# contact URL or address; without one its API returns 403 (observed
# 2026-08-11). Set NEWZ_USER_AGENT to something like
#   newz-being/2.0 (https://your.domain/; you@your.domain)
# once the operator domain exists (P2 §Decisions #2). The default below is
# honest about what it is rather than fabricating a contact.
_cached_ua: str | None = None


def user_agent() -> str:
    """Read once, from the config that owns .env.

    Was `os.environ.get` at import time, which never saw NEWZ_USER_AGENT
    because .env is loaded by newz.config and not exported to the process
    environment — so the contact string was set and silently ignored
    (2026-08-12).
    """
    global _cached_ua
    if _cached_ua is None:
        try:
            from newz.config import load

            _cached_ua = load().user_agent
        except Exception:  # noqa: BLE001
            from newz.config import DEFAULT_USER_AGENT

            _cached_ua = DEFAULT_USER_AGENT
    return _cached_ua


class DomainRateLimiter:
    """Minimum gap between requests to the same host.

    One lock per host, so a slow source never blocks a fast one and one
    greedy source cannot starve the others.
    """

    def __init__(self, intervals: dict[str, float] | None = None,
                 fallback: float = FALLBACK_MIN_INTERVAL):
        self._intervals = dict(intervals or DEFAULT_MIN_INTERVALS)
        self._fallback = fallback
        self._last: dict[str, float] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def interval_for(self, host: str) -> float:
        return self._intervals.get(host, self._fallback)

    def _lock_for(self, host: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(host, threading.Lock())

    def wait(self, url: str, *, sleep=time.sleep, now=time.monotonic) -> float:
        """Block until this host may be called again. Returns seconds waited."""
        host = (urlparse(url).hostname or "unknown").lower()
        gap = self.interval_for(host)
        with self._lock_for(host):
            last = self._last.get(host)
            waited = 0.0
            if last is not None:
                remaining = gap - (now() - last)
                if remaining > 0:
                    logger.debug("rate limit: waiting %.2fs for %s", remaining, host)
                    sleep(remaining)
                    waited = remaining
            self._last[host] = now()
            return waited
