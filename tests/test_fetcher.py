"""The safe fetcher against hostile input.

Every ceiling is asserted against a response that actually breaches it, not
against a header that claims to.
"""

from __future__ import annotations

import gzip

import pytest

from newz.acquisition.fetcher import FetchPolicy, fetch, normalize_mime
from newz.acquisition.urlpolicy import UrlPolicy
from newz.domain.enums import AttemptOutcome, FetchRefusal
from tests.transport import FixtureTransport, Reply

URL = "https://example.org/article"


@pytest.fixture
def wire():
    return FixtureTransport()


def test_an_ordinary_page_is_retained_with_its_hash(wire):
    wire.serve_html(URL, "<html><body><p>a paragraph</p></body></html>")
    result = fetch(URL, wire)
    assert result.outcome is AttemptOutcome.RETAINED
    assert result.normalized_mime == "text/html"
    assert result.content_hash and len(result.content_hash) == 64
    assert b"a paragraph" in result.body


@pytest.mark.parametrize(
    ("url", "refusal"),
    [
        ("ftp://example.org/x", FetchRefusal.SCHEME_NOT_ALLOWED),
        ("file:///etc/passwd", FetchRefusal.SCHEME_NOT_ALLOWED),
        ("https://user:secret@example.org/", FetchRefusal.CREDENTIALS_IN_URL),
        ("https://example.org:9200/", FetchRefusal.PORT_NOT_ALLOWED),
        ("gopher://example.org/", FetchRefusal.SCHEME_NOT_ALLOWED),
        ("://malformed", FetchRefusal.URL_MALFORMED),
    ],
)
def test_url_attacks_are_refused_before_anything_is_opened(wire, url, refusal):
    result = fetch(url, wire)
    assert result.refusal is refusal
    assert wire.requested == []


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "::ffff:127.0.0.1"],
)
def test_a_name_resolving_inside_the_house_is_refused(wire, address):
    wire.addresses["example.org"] = (address,)
    wire.serve_html(URL, "<html>x</html>")
    result = fetch(URL, wire)
    assert result.refusal is FetchRefusal.NON_PUBLIC_ADDRESS
    assert wire.requested == []


def test_every_answer_must_be_public_not_merely_the_first(wire):
    """The rebinding case: one good address and one bad one is a bad name."""
    wire.addresses["example.org"] = ("93.184.216.34", "127.0.0.1")
    wire.serve_html(URL, "<html>x</html>")
    assert fetch(URL, wire).refusal is FetchRefusal.NON_PUBLIC_ADDRESS


def test_a_name_that_does_not_resolve_is_refused(wire):
    wire.addresses["example.org"] = ()
    assert fetch(URL, wire).refusal is FetchRefusal.HOST_NOT_RESOLVABLE


def test_redirects_are_followed_within_the_limit_and_recorded(wire):
    wire.serve_redirect(URL, "https://example.org/second")
    wire.serve_redirect("https://example.org/second", "https://example.org/third")
    wire.serve_html("https://example.org/third", "<html>arrived</html>")
    result = fetch(URL, wire)
    assert result.outcome is AttemptOutcome.RETAINED
    assert result.final_url == "https://example.org/third"
    assert result.redirects == ("https://example.org/second", "https://example.org/third")


def test_a_redirect_chain_past_the_limit_is_refused(wire):
    for index in range(8):
        wire.serve_redirect(f"https://example.org/{index}", f"https://example.org/{index + 1}")
    result = fetch("https://example.org/0", wire)
    assert result.refusal is FetchRefusal.REDIRECT_LIMIT


def test_a_redirect_may_not_downgrade_https_to_http(wire):
    wire.serve_redirect(URL, "http://example.org/plain")
    assert fetch(URL, wire).refusal is FetchRefusal.REDIRECT_SCHEME_DOWNGRADE


def test_a_redirect_off_policy_is_refused(wire):
    wire.serve_redirect(URL, "file:///etc/passwd")
    assert fetch(URL, wire).refusal is FetchRefusal.REDIRECT_OFF_POLICY


def test_a_redirect_into_the_house_is_refused(wire):
    wire.addresses["internal.example"] = ("169.254.169.254",)
    wire.serve_redirect(URL, "https://internal.example/latest/meta-data/")
    assert fetch(URL, wire).refusal is FetchRefusal.NON_PUBLIC_ADDRESS


def test_an_oversized_body_is_refused_while_it_is_being_read(wire):
    """The header is not believed either way: the ceiling holds when it lies."""
    body = b"x" * 20_000
    wire.serve(
        URL,
        Reply(headers={"Content-Type": "text/plain", "Content-Length": "10"}, body=body),
    )
    result = fetch(URL, wire, FetchPolicy(max_bytes=4_096))
    assert result.refusal is FetchRefusal.RESPONSE_TOO_LARGE
    assert result.bytes_read > 4_096


def test_an_honestly_declared_oversized_body_is_refused_before_reading(wire):
    wire.serve(
        URL,
        Reply(
            headers={"Content-Type": "text/plain", "Content-Length": "999999999"},
            body=b"x" * 100,
        ),
    )
    result = fetch(URL, wire, FetchPolicy(max_bytes=4_096))
    assert result.refusal is FetchRefusal.RESPONSE_TOO_LARGE
    assert result.body == b""


def test_a_slow_body_times_out_rather_than_hanging(wire):
    wire.serve(URL, Reply(headers={"Content-Type": "text/plain"}, body=b"x" * 100, slow=True))
    result = fetch(URL, wire)
    assert result.refusal is FetchRefusal.TIMEOUT


def test_a_compressed_body_is_decompressed_within_its_ceiling(wire):
    wire.serve_gzip(URL, b"a modest document")
    result = fetch(URL, wire)
    assert result.outcome is AttemptOutcome.RETAINED
    assert result.body == b"a modest document"


def test_a_decompression_bomb_is_refused(wire):
    payload = gzip.compress(b"\0" * 5_000_000)
    wire.serve(
        URL,
        Reply(
            headers={"Content-Type": "text/plain", "Content-Encoding": "gzip"},
            body=payload,
        ),
    )
    result = fetch(URL, wire, FetchPolicy(max_decompressed_bytes=64_000))
    assert result.refusal is FetchRefusal.DECOMPRESSION_LIMIT


def test_an_unknown_content_encoding_is_refused(wire):
    wire.serve(
        URL,
        Reply(headers={"Content-Type": "text/plain", "Content-Encoding": "br"}, body=b"x"),
    )
    assert fetch(URL, wire).refusal is FetchRefusal.CONTENT_TYPE_NOT_ALLOWED


@pytest.mark.parametrize(
    ("declared", "normalized"),
    [
        ("text/html; charset=utf-8", "text/html"),
        ("application/xhtml+xml", "text/html"),
        ("APPLICATION/PDF", "application/pdf"),
        ("application/rss+xml", "application/xml"),
        ("application/octet-stream", ""),
        ("", ""),
    ],
)
def test_content_types_normalize_or_are_refused(declared, normalized):
    assert normalize_mime(declared) == normalized


def test_an_unroutable_content_type_is_refused_rather_than_guessed_at(wire):
    wire.serve_bytes(URL, b"\x00\x01", "application/octet-stream")
    result = fetch(URL, wire)
    assert result.refusal is FetchRefusal.CONTENT_TYPE_NOT_ALLOWED


def test_a_mislabeled_body_is_refused(wire):
    """A body that says it is a PDF and does not begin like one."""
    wire.serve_bytes(URL, b"<html>not a pdf at all</html>", "application/pdf")
    result = fetch(URL, wire)
    assert result.refusal is FetchRefusal.CONTENT_TYPE_NOT_ALLOWED
    assert "does not begin like one" in result.detail


def test_a_rate_limit_is_a_refusal_with_its_retry_after(wire):
    wire.serve(URL, Reply(status=429, headers={"Retry-After": "120"}))
    result = fetch(URL, wire)
    assert result.refusal is FetchRefusal.RATE_LIMITED
    assert result.detail == "120"


def test_a_server_error_is_an_error_and_not_a_refusal(wire):
    wire.serve(URL, Reply(status=503, headers={"Content-Type": "text/html"}))
    result = fetch(URL, wire)
    assert result.outcome is AttemptOutcome.ERROR
    assert result.refusal is None


def test_an_unreachable_host_is_an_error(wire):
    wire.serve(URL, Reply(unreachable=True))
    assert fetch(URL, wire).outcome is AttemptOutcome.ERROR


def test_a_host_outside_the_catalog_allowlist_is_refused(wire):
    policy = FetchPolicy(url=UrlPolicy(allowed_hosts=frozenset({"allowed.example"})))
    wire.serve_html(URL, "<html>x</html>")
    assert fetch(URL, wire, policy).refusal is FetchRefusal.HOST_NOT_IN_CATALOG
