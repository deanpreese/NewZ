"""Fetching and reducing a document (S2 §9.1's full-extraction half).

> Extraction depth is adaptive: headline-level by default, **full-extraction
> only for material that touches a concern** or survives sleep's relevance
> pass.

Only the default half was built. Every read in the being's life until now
has been search-result metadata — `title + summary` from an adapter, or a
feed item's `<description>`. The only `fetcher.get()` calls in the codebase
went to feed XML and adapter APIs. In 24 reads it had never fetched a page,
and its own source-gap record said so twelve times without being asked:
*"the retrieval slice contains only the headline and a fragment"*, *"only
the opening sentence of the study"*, *"thin on the how"*.

Pure functions, no store, no model calls. Everything here is testable from
fixtures, which matters because the wiring that uses it (task #8) touches a
running being.

**Chunking is not an implementation detail.** Measured 2026-08-14: 12,000
characters handed to `extract_claims` in one call exceeded its 900-token
output cap, the XML truncated mid-element, and extraction returned ZERO
claims where the abstract returns two. v1 found the same thing and chunked
its canon at 1500/150; the constants here are its, widened slightly because
articles are denser than books.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# What a single extraction call can carry without truncating its own output.
# 2,000 chars produced parseable extractions across all six chunks of a test
# document; 12,000 in one call produced none.
CHUNK_CHARS = 2_000

# Enough to carry a claim that straddles a boundary, small enough that the
# duplicate claims it creates are cheap to drop. v1's value.
CHUNK_OVERLAP = 150

# The ceiling on how much of a document is read at all. Six chunks is
# already ~3-4k tokens of extraction against a diet headroom measured at
# 3,515 — reading the whole of a 52,000-char encyclopedia entry would spend
# a day's allowance on one page.
MAX_DOC_CHARS = 12_000

# Below this, whatever came back is a stub — a paywall interstitial, a
# cookie wall, a JS shell. Treated as a failed fetch so the caller keeps the
# abstract rather than extracting claims about subscription offers.
MIN_USEFUL_CHARS = 400

_PAYWALL_MARKERS = (
    "subscribe to continue", "subscribe now", "create a free account",
    "sign in to read", "already a subscriber", "this content is for",
    "enable javascript", "please enable cookies", "access denied",
)

_TEXTUAL = ("text/html", "text/plain", "application/xhtml")


def looks_like_stub(text: str) -> bool:
    """A paywall or shell rather than a document.

    Checked on the REDUCED text: a paywall page reduces to almost nothing,
    and what little survives is the pitch.
    """
    if len(text) < MIN_USEFUL_CHARS:
        return True
    head = " ".join(text[:1200].lower().split())
    return any(m in head for m in _PAYWALL_MARKERS)


def reduce_html(raw: str) -> str:
    """HTML to readable body text.

    trafilatura first because it drops nav, cookie banners, related-article
    rails and comment threads — measured, it took a 364,607-char Wikipedia
    page to 52,581 chars of body. bs4 is the fallback and is markedly
    worse: it keeps everything that is not script or style, so boilerplate
    reaches extraction and the being records claims about newsletter
    signups. Both are declared dependencies as of 2026-08-14 precisely so
    this chain does not silently degrade to the third case.
    """
    try:
        import trafilatura

        got = trafilatura.extract(raw, include_comments=False,
                                  include_tables=False)
        if got and got.strip():
            return got.strip()
    except Exception:  # noqa: BLE001
        logger.debug("trafilatura failed; falling back to bs4", exc_info=True)

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "aside"]):
            tag.decompose()
        return " ".join(soup.get_text(separator="\n").split())
    except Exception:  # noqa: BLE001
        logger.debug("bs4 failed; giving up on this document", exc_info=True)
        return ""


def chunk(text: str, *, size: int = CHUNK_CHARS,
          overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split for extraction, preferring sentence boundaries.

    A claim cut in half yields either nothing or something false, so the
    split walks back to the nearest sentence end when one is close enough.
    """
    text = (text or "").strip()
    if not text:
        return []
    # Overlap is clamped to half the chunk so the step can never collapse.
    # Caught by test 2026-08-14: size=100 with overlap=99 advances one
    # character at a time and produced 9,901 chunks of a 10,000-char input.
    # The shipped constants (2000/150) never reach this, which is exactly why
    # it would have gone unnoticed until someone tuned them.
    overlap = max(0, min(overlap, size // 2))
    out: list[str] = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        if end < len(text):
            window = text[max(i + size // 2, i):end]
            m = None
            for m in re.finditer(r"[.!?](?:\s|$)", window):
                pass                       # keep the last match in the window
            if m is not None:
                end = max(i + size // 2, i) + m.end()
        out.append(text[i:end].strip())
        if end >= len(text):
            break
        i = max(end - overlap, i + 1)
    return [c for c in out if c]


def fetch_document(url: str, fetcher, *, max_chars: int = MAX_DOC_CHARS) -> str | None:
    """Fetch and reduce one document, or None.

    None on every failure — robots, timeout, non-textual content, a stub, or
    an unreducible page. The caller keeps the abstract it already has, which
    is what makes depth strictly additive: R3 can improve a read but must
    never take away the one that works today.

    Robots and per-domain rate limits are the caller's `Fetcher`, unchanged
    and already exercised by every adapter — it has refused Google News and
    NYT on robots grounds without being asked to.
    """
    if not url:
        return None
    try:
        raw = fetcher.get(url)
    except Exception as e:  # noqa: BLE001
        logger.info("document: %s not fetched (%s)", url[:80], e)
        return None

    if not raw or not raw.strip():
        return None
    # A PDF or binary arriving as text is not reducible, and asking bs4 to
    # parse it produces plausible-looking noise.
    if raw.lstrip()[:5] == "%PDF-":
        logger.info("document: %s is a PDF — not read", url[:80])
        return None

    body = reduce_html(raw) if "<" in raw[:2000] else " ".join(raw.split())
    if not body:
        return None
    if looks_like_stub(body):
        logger.info("document: %s reduced to a stub (%d chars) — treating as "
                    "unfetched", url[:80], len(body))
        return None

    if len(body) > max_chars:
        body = body[:max_chars]
    logger.info("document: %s -> %d chars", url[:80], len(body))
    return body


def is_textual(content_type: str | None) -> bool:
    """Whether a Content-Type is worth fetching at all."""
    if not content_type:
        return True                      # unknown: try, and let reduce decide
    return any(t in content_type.lower() for t in _TEXTUAL)
