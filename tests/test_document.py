"""S2 §9.1's full-extraction half — fetch and reduce a document.

Only the default half was ever built: every read in the being's life was
search-result metadata. Its own gap record said so twelve times — "the
retrieval slice contains only the headline and a fragment", "only the
opening sentence of the study", "thin on the how".

The contract that matters here is that depth is strictly ADDITIVE. Every
failure returns None so the caller keeps the abstract it already has. R3 can
improve a read; it must never take away the one that works today.
"""

import pytest

from newz.world.document import (
    CHUNK_CHARS,
    MAX_DOC_CHARS,
    chunk,
    fetch_document,
    is_textual,
    looks_like_stub,
    reduce_html,
)

ARTICLE = """<html><head><title>T</title>
<script>var tracking = 1;</script><style>body{}</style></head>
<body>
<nav><a href="/">Home</a><a href="/subscribe">Subscribe</a></nav>
<article>
<h1>Regulated markets are slow to handle change</h1>
<p>The CFTC clarified when an event contract counts as an event contract,
setting out criteria that had been ambiguous since the settlement. The rule
applies to venues listing binary outcomes on regulatory decisions.</p>
<p>Analysts noted that prediction venues reprice within minutes of such
clarifications, while equity option chains take substantially longer to
reflect the same information.</p>
</article>
<footer>Copyright. Subscribe to our newsletter for more.</footer>
</body></html>"""


class _Fetcher:
    def __init__(self, payload=None, error=None):
        self._payload, self._error = payload, error
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        if self._error:
            raise self._error
        return self._payload


# ── reduction ────────────────────────────────────────────────────────────

def test_it_reduces_to_the_body_and_drops_the_furniture():
    body = reduce_html(ARTICLE)
    assert "CFTC clarified" in body
    assert "prediction venues reprice" in body
    assert "var tracking" not in body          # script
    assert "Subscribe to our newsletter" not in body   # footer


def test_plain_text_is_passed_through_without_html_machinery():
    f = _Fetcher("A plain text document. " * 40)
    got = fetch_document("https://example.org/a.txt", f)
    assert got and "plain text document" in got


# ── the additive contract: every failure keeps the abstract ──────────────

def test_a_refused_fetch_returns_none_rather_than_raising():
    f = _Fetcher(error=PermissionError("robots.txt disallows"))
    assert fetch_document("https://example.org/a", f) is None


def test_a_pdf_is_not_read():
    # bs4 will happily "parse" a PDF and produce plausible noise.
    assert fetch_document("https://example.org/a.pdf", _Fetcher("%PDF-1.7 ...")) is None


def test_a_paywall_stub_is_treated_as_unfetched():
    stub = "<html><body><h1>Subscribe to continue</h1><p>Already a subscriber?</p></body></html>"
    assert fetch_document("https://example.org/a", _Fetcher(stub)) is None


def test_an_empty_page_is_treated_as_unfetched():
    assert fetch_document("https://example.org/a", _Fetcher("")) is None
    assert fetch_document("", _Fetcher(ARTICLE)) is None


@pytest.mark.parametrize("ct,ok", [
    ("text/html; charset=utf-8", True), ("text/plain", True),
    ("application/pdf", False), ("image/png", False), (None, True),
])
def test_content_types_worth_fetching(ct, ok):
    assert is_textual(ct) is ok


def test_a_short_body_is_a_stub_not_a_document():
    assert looks_like_stub("Too short.")
    assert not looks_like_stub("word " * 200)


# ── short is not empty, and data is short (2026-08-29) ───────────────────

CSV = ("observation_date,DGS10\n2026-08-03,4.70\n2026-08-04,4.63\n"
       "2026-08-21,4.74\n2026-08-27,4.67\n")


def test_a_short_data_body_is_not_a_stub():
    """Measured 2026-08-29, and it made a whole class of source unreadable.

    A FRED CSV carrying a month of daily 10-year Treasury yields — the
    complete answer to the claim being resolved — is 327 characters and was
    discarded by the length floor as a paywall interstitial. The deep read
    returned None, depth stayed `abstract`, and the verdict said "the material
    only defines the series". Prose and data have opposite length signatures
    for the same information.
    """
    assert not looks_like_stub(CSV, reduced=False)


def test_the_floor_is_unchanged_for_html():
    """The floor is not loosened where it was earned. Its justification is
    what REDUCTION does to a shell, and paywalls are HTML."""
    assert looks_like_stub(CSV)


def test_paywall_markers_still_apply_to_text():
    """An error page served as text/plain is still an error page — it is the
    markers, not the length, that identify one."""
    assert looks_like_stub("Access denied. " * 40, reduced=False)


def test_an_empty_body_is_a_stub_however_it_arrived():
    assert looks_like_stub("   \n  ", reduced=False)


def test_fetch_document_keeps_a_short_csv():
    """End to end: the branch that decides `reduced` is the same branch that
    decides how the body was produced, so the two cannot drift apart."""
    got = fetch_document("https://example.org/series.csv", _Fetcher(CSV))

    assert got is not None
    assert "2026-08-21,4.74" in got


def test_fetch_document_still_drops_a_short_html_shell():
    shell = "<html><body><p>Subscribe now to continue.</p></body></html>"
    assert fetch_document("https://example.org/a", _Fetcher(shell)) is None


# ── the cap ──────────────────────────────────────────────────────────────

def test_a_long_document_is_capped():
    # Reading a whole 52,000-char encyclopedia entry would spend a day's diet
    # allowance on one page.
    huge = "<html><body><article>" + ("Sentence about markets. " * 4000) + "</article></body></html>"
    got = fetch_document("https://example.org/a", _Fetcher(huge))
    assert got is not None and len(got) <= MAX_DOC_CHARS


# ── chunking, which is not an implementation detail ──────────────────────

def test_chunking_is_what_makes_extraction_parseable():
    """Measured 2026-08-14: 12,000 chars in ONE extraction call exceeded the
    900-token output cap, the XML truncated mid-element, and extraction
    returned 0 claims where the abstract returns 2. Six chunks of 2,000
    produced parseable extractions across all six.
    """
    text = "This is a sentence about markets. " * 500      # ~17,000 chars
    chunks = chunk(text)
    assert len(chunks) > 1
    assert all(len(c) <= CHUNK_CHARS + 200 for c in chunks)


def test_chunks_prefer_a_sentence_boundary():
    # A claim cut in half yields either nothing or something false.
    text = ("Alpha grows. " * 100) + ("Beta shrinks. " * 100)
    for c in chunk(text, size=600, overlap=50):
        assert c.rstrip().endswith(".")


def test_chunks_overlap_so_a_straddling_claim_survives():
    text = "".join(f"Fact number {i} is recorded here. " for i in range(200))
    chunks = chunk(text, size=500, overlap=120)
    joined = "".join(chunks)
    assert len(joined) > len(text)         # overlap means repetition
    for i in (0, 50, 150):
        assert any(f"Fact number {i} is recorded" in c for c in chunks)


def test_chunking_terminates_on_pathological_input():
    assert chunk("") == []
    assert chunk("   ") == []
    assert len(chunk("x" * 10_000, size=100, overlap=99)) < 500   # no infinite loop
