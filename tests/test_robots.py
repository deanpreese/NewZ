"""robots.txt: the parser, and the fetcher honouring what it says."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.acquisition.fetcher import FetchPolicy, fetch
from newz.acquisition.robots import CACHE_HOURS, RobotsCache, parse, path_of
from newz.domain.enums import AttemptOutcome, FetchRefusal
from tests.transport import FixtureTransport, Reply

NOW = datetime(2026, 9, 5, 12, 0, 0)
URL = "https://example.org/article"


@pytest.fixture
def wire():
    return FixtureTransport()


# ---------------------------------------------------------------------------
# The parser
# ---------------------------------------------------------------------------


def test_a_group_named_for_this_agent_beats_the_wildcard():
    """A site that wrote a rule about us meant it."""
    body = "User-agent: *\nDisallow:\n\nUser-agent: newz-being\nDisallow: /\n"
    ours = parse(body, "newz-being/2.0 (contact)")
    theirs = parse(body, "some-other-agent/1.0")
    assert not ours.allows("/anything")
    assert theirs.allows("/anything")


def test_the_longest_matching_rule_decides():
    body = "User-agent: *\nDisallow: /private/\nAllow: /private/public/\n"
    robots = parse(body, "newz")
    assert robots.allows("/open")
    assert not robots.allows("/private/secret")
    assert robots.allows("/private/public/page")


def test_allow_beats_disallow_on_an_equal_length_match():
    """A stricter reading would refuse paths sites deliberately opened."""
    body = "User-agent: *\nDisallow: /x\nAllow: /x\n"
    assert parse(body, "newz").allows("/x")


def test_wildcards_and_end_anchors_are_honoured():
    body = "User-agent: *\nDisallow: /*.pdf$\nDisallow: /tmp/*/cache\n"
    robots = parse(body, "newz")
    assert not robots.allows("/reports/annual.pdf")
    assert robots.allows("/reports/annual.pdf.html")
    assert not robots.allows("/tmp/a/cache")
    assert robots.allows("/tmp/a/keep")


def test_comments_and_blank_lines_are_ignored():
    body = "# a comment\nUser-agent: *   # trailing\nDisallow: /x  # here too\n"
    assert not parse(body, "newz").allows("/x")


def test_an_empty_robots_permits_everything():
    assert parse("", "newz").allows("/anything")


def test_a_crawl_delay_is_read():
    body = "User-agent: *\nCrawl-delay: 12\nDisallow:\n"
    assert parse(body, "newz").crawl_delay == 12.0


def test_a_path_carries_its_query():
    assert path_of("https://x.example/a?b=1") == "/a?b=1"
    assert path_of("https://x.example") == "/"


# ---------------------------------------------------------------------------
# The fetcher
# ---------------------------------------------------------------------------


def test_a_disallowed_path_is_refused_before_it_is_fetched(wire):
    wire.serve_robots("example.org", "User-agent: *\nDisallow: /article\n")
    wire.serve_html(URL, "<html><body><p>content</p></body></html>")

    result = fetch(URL, wire, now=NOW)
    assert result.refusal is FetchRefusal.ROBOTS_DISALLOWED
    assert "disallows /article" in result.detail
    # The page itself was never requested.
    assert URL not in wire.requested


def test_an_allowed_path_is_fetched(wire):
    wire.serve_robots("example.org", "User-agent: *\nDisallow: /private/\n")
    wire.serve_html(URL, "<html><body><p>content</p></body></html>")
    assert fetch(URL, wire, now=NOW).outcome is AttemptOutcome.RETAINED


def test_no_robots_file_means_ordinary_use_applies(wire):
    """RFC 9309: unavailable is not the same answer as unreachable."""
    wire.serve_html(URL, "<html><body><p>content</p></body></html>")
    assert fetch(URL, wire, now=NOW).outcome is AttemptOutcome.RETAINED


def test_a_server_error_on_robots_disallows_rather_than_assuming_consent(wire):
    wire.serve(
        "https://example.org/robots.txt",
        Reply(status=503, headers={"Content-Type": "text/plain"}),
    )
    wire.serve_html(URL, "<html><body><p>content</p></body></html>")

    result = fetch(URL, wire, now=NOW)
    assert result.refusal is FetchRefusal.ROBOTS_UNREACHABLE
    assert URL not in wire.requested


def test_an_unreachable_host_on_robots_disallows(wire):
    wire.serve("https://example.org/robots.txt", Reply(unreachable=True))
    wire.serve_html(URL, "<html><body><p>content</p></body></html>")
    assert fetch(URL, wire, now=NOW).refusal is FetchRefusal.ROBOTS_UNREACHABLE


def test_every_redirect_hop_is_checked_not_only_the_first(wire):
    """A redirect that lands somewhere the site disallows is somewhere the site
    disallows, whatever door it was reached through."""
    wire.serve_robots("example.org", "User-agent: *\nDisallow:\n")
    wire.serve_robots("elsewhere.example", "User-agent: *\nDisallow: /secret/\n")
    wire.serve_redirect(URL, "https://elsewhere.example/secret/page")
    wire.serve_html("https://elsewhere.example/secret/page", "<html><p>x</p></html>")

    result = fetch(URL, wire, now=NOW)
    assert result.refusal is FetchRefusal.ROBOTS_DISALLOWED
    assert "elsewhere.example" in result.detail


def test_robots_is_asked_once_per_host_and_then_cached(wire):
    wire.serve_robots("example.org", "User-agent: *\nDisallow:\n")
    for path in ("/a", "/b", "/c"):
        wire.serve_html(f"https://example.org{path}", "<html><p>x</p></html>")

    cache = RobotsCache()
    for path in ("/a", "/b", "/c"):
        fetch(f"https://example.org{path}", wire, robots_cache=cache, now=NOW)

    assert wire.requested.count("https://example.org/robots.txt") == 1
    assert cache.get("example.org", NOW) is not None


def test_a_cached_answer_expires_and_is_asked_again(wire):
    wire.serve_robots("example.org", "User-agent: *\nDisallow:\n")
    wire.serve_html(URL, "<html><p>x</p></html>")

    cache = RobotsCache()
    fetch(URL, wire, robots_cache=cache, now=NOW)
    later = NOW + timedelta(hours=CACHE_HOURS + 1)
    assert cache.get("example.org", later) is None
    fetch(URL, wire, robots_cache=cache, now=later)
    assert wire.requested.count("https://example.org/robots.txt") == 2


def test_the_check_can_be_switched_off_only_deliberately(wire):
    """Off where there is nothing to ask — an offline harness — and nowhere else."""
    wire.serve_robots("example.org", "User-agent: *\nDisallow: /\n")
    wire.serve_html(URL, "<html><p>x</p></html>")

    assert fetch(URL, wire, now=NOW).refusal is FetchRefusal.ROBOTS_DISALLOWED
    permissive = FetchPolicy(respect_robots=False)
    assert fetch(URL, wire, permissive, now=NOW).outcome is AttemptOutcome.RETAINED


def test_the_agent_the_site_sees_is_the_agent_the_rules_are_read_for(wire):
    """A rule naming us must be found, so the same string has to be used for both."""
    wire.user_agent = "newz-being/2.0 (contact)"
    wire.serve_robots("example.org", "User-agent: newz-being\nDisallow: /article\n")
    wire.serve_html(URL, "<html><p>x</p></html>")
    assert fetch(URL, wire, now=NOW).refusal is FetchRefusal.ROBOTS_DISALLOWED


# ---------------------------------------------------------------------------
# The two defects the live run found
# ---------------------------------------------------------------------------


def test_a_gzipped_robots_is_read_rather_than_parsed_as_binary(wire):
    """The first version read the socket directly, and because the transport asks
    for gzip it parsed compressed bytes, found no directives, and allowed
    everything. A safety check that fails open while appearing to work is worse
    than not having one."""
    import gzip as gziplib

    wire.serve(
        "https://example.org/robots.txt",
        Reply(
            headers={"Content-Type": "text/plain", "Content-Encoding": "gzip"},
            body=gziplib.compress(b"User-agent: *\nDisallow: /article\n"),
        ),
    )
    wire.serve_html(URL, "<html><p>x</p></html>")
    assert fetch(URL, wire, now=NOW).refusal is FetchRefusal.ROBOTS_DISALLOWED


def test_a_malformed_response_is_an_error_and_not_a_crash(wire):
    """A real site answered with a malformed status line. The transport owns the
    protocol, so it translates protocol failures into the error contract the
    fetcher handles — the fetcher cannot catch an exception from a module it is
    not allowed to import."""
    import http.client

    class Broken(FixtureTransport):
        def open(self, **kwargs):
            raise OSError("BadStatusLine:  2 ")

    broken = Broken()
    result = fetch(URL, broken, now=NOW)
    assert result.refusal is FetchRefusal.ROBOTS_UNREACHABLE
    assert "unreachable" in result.detail
    assert issubclass(http.client.HTTPException, Exception)


def test_a_longer_crawl_delay_is_honoured_over_our_own_floor():
    """One real source asks for two minutes, four times the floor."""
    from newz.control.retry import RetryPolicy, effective_interval

    policy = RetryPolicy(min_host_interval_seconds=30)
    assert effective_interval(policy, 120.0) == 120.0
    assert effective_interval(policy, 5.0) == 30.0
    assert effective_interval(policy, None) == 30.0
