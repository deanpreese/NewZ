"""One generator, no hand-authored pages (P4 epic E3.2).

Done-when: the surface regenerates into an empty directory, and every page
traces to store rows.

Both halves are structural rather than cosmetic. If anything on the surface is
not from a row, E3.3's disclosure cannot be guaranteed by construction and
E3.5's byte-comparable regeneration cannot be claimed at all.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import inspect

import pytest

from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.surface.generate import generate

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
REPO = Path(__file__).resolve().parent.parent
DAY = 86400.0


@pytest.fixture
def store(tmp_path):
    # E3A.1: the metric series lives in the monitor's own database,
    # attached as `mon`. It is created before the connection is opened,
    # because `open_db` attaches it only if the file is already there.
    from newz.monitor.db import open_monitor

    open_monitor(tmp_path / "s.db").close()
    conn = open_db(tmp_path / "s.db")
    apply_pending(conn, MAIN_SQL)
    now = time.time()
    conn.execute(
        "INSERT INTO concerns (id, opened_at, kind, statement, why_open,"
        " closing_condition, status, salience, origin) VALUES (1,?,?,?,?,?,?,?,?)",
        (now, "inquiry", "Does the index roll over?", "it bears on what I hold",
         "the statistical office publishes its March release", "open", 0.9, "reading"))
    conn.execute(
        "INSERT INTO works (id, ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (1,?,?,?,?,?,?,?,?,?,?)",
        (now - 5 * DAY, "concern", 1, "Does the index roll over?",
         "I keep returning to it", "On rolling over",
         "The index is rolling over and the reason is structural.", 9, "qwen", 200))
    conn.execute(
        "INSERT INTO resolutions (id, opened_at, claim, resolution_condition,"
        " resolver, due_at, provenance, status) VALUES (1,?,?,?,?,?,?, 'open')",
        (now, "The March release prints below 40.", "the release is published",
         "the statistical office", now + 30 * DAY, "concern:1"))
    conn.commit()
    yield conn
    conn.close()


def _generate(store, tmp_path) -> tuple[Path, dict]:
    out = tmp_path / "published"
    m = generate(store, out, now=1_000_000.0)
    return out, m.as_dict()


def test_the_surface_regenerates_into_an_empty_directory(store, tmp_path):
    """Done-when, first half. Behavior: no incremental update, no reading what
    is already there, no state outside the store."""
    out, _ = _generate(store, tmp_path)

    # The four pages the surface must always have, asserted as a subset: an
    # earlier version pinned the exact file set and broke the hour E3.4 added
    # robots.txt and the per-piece pages. A surface that is expected to grow
    # should not be asserted as a snapshot.
    required = {"index.html", "questions.html", "errors.html",
                "commitments.html", "manifest.json"}
    assert required <= {p.name for p in out.iterdir()}
    assert "On rolling over" in (out / "index.html").read_text()


def test_every_page_traces_to_store_rows(store, tmp_path):
    """Done-when, second half. Behavior: the manifest names the rows behind each
    page, so "nothing here was hand-written" is checkable and not asserted."""
    _, manifest = _generate(store, tmp_path)

    assert manifest["pages"]["index"]["works"] == [1]
    assert manifest["pages"]["questions"]["concerns"] == [1]
    assert manifest["pages"]["errors"]["resolutions"] == [1]


def test_regenerating_produces_the_same_bytes(store, tmp_path):
    """What E3.5's byte-comparable claim rests on. Behavior: the generator is
    deterministic — no timestamps in the output, no ordering by anything
    unstable."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate(store, a, now=1_000_000.0)
    generate(store, b, now=2_000_000.0)

    for name in ("index.html", "questions.html", "errors.html", "manifest.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_there_are_no_hand_authored_pages_anywhere(store, tmp_path):
    """The epic's own words. Behavior: the repository contains no HTML the
    generator did not produce — a template file checked in beside the code is a
    page whose provenance is a person, and the manifest could not trace it."""
    strays = [p for p in REPO.rglob("*.html")
              if ".git" not in p.parts and "published" not in p.parts
              and ".claude" not in p.parts]

    assert strays == [], f"hand-authored HTML: {strays}"


def test_nothing_on_the_surface_reaches_the_network(store, tmp_path):
    """§7. Behavior: no CDN, no font, no analytics. Sovereignty is not only
    about inference — a page that fetches from someone else's host has handed
    them a record of every reader."""
    out, _ = _generate(store, tmp_path)

    for page in out.glob("*.html"):
        text = page.read_text()
        assert not re.search(r'(src|href)\s*=\s*["\']https?://', text), page.name
        assert "<script" not in text.lower(), page.name


def test_a_capability_that_does_not_exist_says_so(store, tmp_path):
    """Behavior: an absent capability rendering as a blank page is
    indistinguishable from a broken one, so the page says which it is.

    **E4.1 built the table, and this branch still matters**: E3.5 rebuilds the
    surface from a VERIFIED BACKUP, and a backup taken before migration 0041
    has no `commitments` table. The clean room must render a page that says so
    rather than one that reads as "the being has committed to nothing".
    """
    store.execute("DROP TABLE commitments")
    out, _ = _generate(store, tmp_path)

    text = (out / "commitments.html").read_text()
    assert "not built yet" in text
    assert "says so rather than appearing empty" in text


def test_a_commitment_renders_with_what_would_break_it(store, tmp_path):
    """E4.1's falsifier is the thing that makes a commitment one, so it is on
    the page beside it. Behavior: a commitments page listing only statements is
    a page of slogans, which is what the mandatory falsifier exists to refuse.
    """
    store.execute(
        "INSERT INTO commitments (ts, kind, statement, falsifier, provenance)"
        " VALUES (?,?,?,?,?)",
        (time.time(), "refuses_to_do",
         "I will not close a concern by restating it more carefully.",
         "a concern closed whose resolution paraphrases its own statement",
         "perspective:14"))
    store.commit()

    out, _ = _generate(store, tmp_path)
    text = (out / "commitments.html").read_text()

    assert "restating it more carefully" in text
    assert "broken by:" in text
    assert "paraphrases its own statement" in text
    assert "refuses to do" in text


def test_a_retracted_piece_still_appears(store, tmp_path):
    """E2.2's rule carried onto the surface. Behavior: retraction is an outcome
    and never a deletion, so the piece is shown, marked, with its reason."""
    store.execute(
        "INSERT INTO work_revisions (ts, work_id, kind, reason, prior_title,"
        " prior_body, prior_word_count) VALUES (?,1,'retracted',?,?,?,?)",
        (time.time(), "its central claim does not survive", "On rolling over",
         "old body", 2))
    store.execute("UPDATE works SET status='retracted' WHERE id=1")
    store.commit()

    out, manifest = _generate(store, tmp_path)
    text = (out / "index.html").read_text()

    assert "On rolling over" in text
    assert "retracted" in text
    assert "its central claim does not survive" in text
    assert manifest["pages"]["index"]["work_revisions"] == [1]


def test_the_error_record_shows_what_being_wrong_cost(store, tmp_path):
    """Behavior: the page P4 Phase 3 exists to render — claims with dates, and
    what each cost when the world disagreed."""
    store.execute(
        "INSERT INTO claim_costs (ts, claim_id, item_text, section,"
        " confidence_before, confidence_after, repeat, released)"
        " VALUES (?,1,?,?,?,?,0,1)",
        (time.time(), "The index is rolling over.", "unresolved", 0.8, 0.3))
    store.commit()

    out, manifest = _generate(store, tmp_path)
    text = (out / "errors.html").read_text()

    assert "The March release prints below 40." in text
    assert "0.80" in text and "0.30" in text and "released" in text
    assert manifest["pages"]["errors"]["claim_costs"] == [1]


# ── disclosure by construction (E3.3) ───────────────────────────────────

def test_no_template_can_render_a_page_without_disclosure(monkeypatch):
    """E3.3's Done-when, in its strongest form. Behavior: `_page` is the only
    way this module produces HTML, and it checks the disclosure before it
    assembles anything — so a page that does not disclose is not a page the
    generator can emit.

    A default that can be blanked is a convention. §9's commitment to no
    undisclosed impersonation is not a convention."""
    import newz.surface.generate as g

    assert "disclosure" not in inspect.signature(g._page).parameters, (
        "the first version took the disclosure as a parameter so tests could "
        "vary it, which made the guard's own input the way around the guard")

    with monkeypatch.context() as m:
        m.setattr(g, "DISCLOSURE", "   \n ")
        with pytest.raises(g.DisclosureMissing, match="cannot render"):
            g._page("t", "<p>body</p>", here="index")


def test_every_generated_page_discloses_twice(store, tmp_path):
    """Behavior: in the head, where a machine reads it, and in the body, where
    a person does. A page disclosing only in metadata discloses to crawlers."""
    out, _ = _generate(store, tmp_path)

    for page in out.glob("*.html"):
        text = page.read_text()
        assert '<meta name="disclosure"' in text, page.name
        assert "<footer>" in text and "digital being" in text, page.name


def test_a_disclosure_that_denies_everything_it_must_establish_is_refused(monkeypatch):
    """R-37a, the fault that made this a pin instead of a keyword check.

    The original guard tested for the *presence* of "digital being",
    "generated" and "no human hand". This string contains all three and asserts
    the opposite of each, and it rendered. §9's commitment to no undisclosed
    impersonation is the worst place in this system for a guard that can be
    satisfied backwards.

    The assertion on `unstated_claims` is not incidental: it is the old guard's
    verdict, kept as evidence that presence is not a claim."""
    import newz.surface.generate as g

    negated = ("This page is NOT written by a digital being. It is generated "
               "by a person, and no human hand edits them is false.")

    assert g.unstated_claims(negated) == [], (
        "the keyword check finds nothing wrong with this, which is the point")

    with monkeypatch.context() as m:
        m.setattr(g, "DISCLOSURE", negated)
        with pytest.raises(g.DisclosureMissing, match="does not match its pin"):
            g._page("t", "<p>b</p>", here="index")


def test_the_wording_is_the_operators_and_changing_it_is_an_act(monkeypatch):
    """P4 Decision 1 owns "the disclosure wording they see first", and the pin
    is what makes changing it an act rather than an edit: the hash lives in
    `evolution/hard_core.yaml`, which is protected whole, so the loop cannot
    move it and the operator moving it is a tracked diff.

    `unstated_claims` survives as the checklist for that moment — a rewrite
    that drops a claim is still worth catching, by the one reader who can act
    on it."""
    import newz.surface.generate as g
    from newz.evidence import hard_core

    assert hard_core.contains("evolution/hard_core.yaml")
    assert not hard_core.contains("newz/surface/generate.py"), (
        "the pin is load-bearing precisely because the text's own file is not "
        "frozen — freezing the generator would freeze the surface's markup too")

    reworded = ("Lumen wrote this. It is a digital being rather than a person, "
                "these pages are generated from its own record, and no human "
                "hand edits them.")
    assert g.unstated_claims(reworded) == []

    for gutted in ("Written by Lumen.",
                   "Lumen is a digital being.",
                   "Generated from a store. No human hand edits them."):
        assert g.unstated_claims(gutted), gutted

    with monkeypatch.context() as m:
        m.setattr(g, "DISCLOSURE", reworded)
        with pytest.raises(g.DisclosureMissing, match="does not match its pin"):
            g._page("t", "<p>b</p>", here="index")


def test_the_disclosure_is_not_a_corporate_disclaimer():
    """The constitution's anti-ai-voice-001: "I do not sound like an AI in the
    corporate-disclaimer sense. I do not apologize for being what I am."

    TRUE_NORTH §2 requires disclosure and the constitution forbids the
    disclaimer register. They are compatible — say plainly what the page is,
    without apology — and this holds the line between them."""
    from newz.surface.generate import DISCLOSURE

    low = DISCLOSURE.lower()
    for disclaimer in ("as an ai", "as a model", "i cannot", "i'm sorry",
                       "please note", "disclaimer", "large language model"):
        assert disclaimer not in low, disclaimer
    assert "digital being" in low


def test_disclosure_survives_regeneration_byte_for_byte(store, tmp_path):
    """Behavior: the disclosure is part of what E3.5 will compare, so it cannot
    drift between runs any more than the rest of the page can."""
    a, b = tmp_path / "a", tmp_path / "b"
    generate(store, a, now=1.0)
    generate(store, b, now=2.0)

    assert (a / "index.html").read_bytes() == (b / "index.html").read_bytes()


# ── the read, rendered (E3.6) ───────────────────────────────────────────

def _body(page: Path) -> str:
    """The rendered content, without the stylesheet.

    Asserting against a whole HTML document catches the CSS: an earlier version
    of the no-aggregate test matched a word in the stylesheet, and the
    ungraded-metric test matched `max-width: 42rem` while looking for the
    number 42.
    """
    text = page.read_text()
    # After </nav>, not after <nav>: the nav marks the current page with
    # <strong>, which counts as content if the split is one tag too early.
    return text.split("</nav>", 1)[1].split("<footer>", 1)[0]


def _reading(conn, metric, value, *, ts, status="ok", note="", window=168.0, dv=1):
    conn.execute(
        "INSERT INTO mon.metric_readings (ts, metric, status, value, window_hours,"
        " note, definition_version) VALUES (?,?,?,?,?,?,?)",
        (ts, metric, status, value, window, note, dv))
    conn.commit()


def test_the_read_regenerates_from_empty_with_the_rest(store, tmp_path):
    """E3.6's Done-when. Behavior: the read is a page like any other — same
    generator, same manifest, same clean-directory rebuild."""
    _reading(store, "nights_slept", 7.0, ts=time.time())

    out, manifest = _generate(store, tmp_path)

    assert (out / "read.html").exists()
    assert manifest["pages"]["read"]["metric_readings"]
    assert "nights slept" in (out / "read.html").read_text()


def test_the_read_shows_unreadable_and_incomplete_where_they_apply(store, tmp_path):
    """E3.6's second clause, and INV-044 on the surface. Behavior: a window
    nothing measured says so; it does not appear as a number and it does not
    disappear."""
    now = time.time()
    _reading(store, "claims_declined", None, ts=now, status="unreadable",
             note="no call log; declines are not in the store by design")
    _reading(store, "pieces_written", None, ts=now, status="incomplete",
             note="the input begins 96h into a 168h window")

    out, _ = _generate(store, tmp_path)
    text = (out / "read.html").read_text()

    assert "UNREADABLE" in text and "not in the store by design" in text
    assert "INCOMPLETE" in text and "96h into a 168h window" in text


def test_the_read_computes_no_aggregate_score(store, tmp_path):
    """The hardest clause in Phase 3, and the one §10 names. Behavior: one line
    per reading and nothing that spans them.

    Metrics measure different things in different units with different grades.
    A number combining them would assert they are commensurable, and none of
    them is — which is exactly how "evidence scores disconnected from sustained
    human-quality interaction" gets built by accident."""
    now = time.time()
    for name, v in (("nights_slept", 7.0), ("pieces_written", 4.0),
                    ("claims_opened", 2.0)):
        _reading(store, name, v, ts=now)

    out, _ = _generate(store, tmp_path)
    text = _body(out / "read.html").lower()

    for word in ("score", "overall", "health:", "total:", "average",
                 "out of", "% healthy", "summary:"):
        assert word not in text, f"the read has grown an aggregate: {word!r}"
    assert text.count("<strong>") == 3, "one line per reading, and no more"


def test_an_ungraded_metric_is_not_shown_at_all(store, tmp_path):
    """Rule 7 on the surface. Behavior: a measurement nobody graded is omitted
    rather than displayed without its provenance — the page cannot be the place
    the grading discipline leaks."""
    _reading(store, "a_number_nobody_graded", 42.0, ts=time.time())

    out, _ = _generate(store, tmp_path)

    assert "42" not in _body(out / "read.html")


def test_the_read_shows_the_delta_only_within_one_definition(store, tmp_path):
    """E2.8 carried onto the surface. Behavior: a metric redefined between
    readings shows no baseline, because comparing a figure to one computed a
    different way is two numbers subtracted."""
    now = time.time()
    _reading(store, "nights_slept", 5.0, ts=now - 20 * DAY, dv=1)
    _reading(store, "nights_slept", 7.0, ts=now, dv=2)

    out, _ = _generate(store, tmp_path)
    text = _body(out / "read.html")

    assert "no baseline yet" in text
    assert "+2" not in text


def test_the_read_is_taken_from_recorded_readings_and_not_recomputed(store, tmp_path):
    """Behavior: the page renders what the nightly cadence wrote. A page that
    computed its own numbers would be a second implementation of every metric,
    drifting quietly from the one the loop steers by."""
    src = (Path(__file__).resolve().parent.parent / "newz" / "surface"
           / "generate.py").read_text()
    read_fn = src[src.index("def _read("):src.index("def _commitments(")]

    assert "metric_readings" in read_fn
    for computed in ("all_values", "read_consequence", "record_all"):
        assert computed not in read_fn, f"the read recomputes via {computed}"


# ── the surface has a rhythm (P4 W7, R-37e) ─────────────────────────────

def test_the_surface_regenerates_without_being_asked(tmp_path):
    """R-37e. Behavior: E3.2 built a generator and no rhythm, so the published
    surface was stale from the moment the being wrote anything — and the daily
    daily read is specified against it. A loop reading a page nothing refreshes
    reads yesterday and reports it as today."""
    from newz.store.db import open_db
    from newz.store.migrations import apply_pending
    from newz.surface.rhythm import PublishScheduler, publish

    db = tmp_path / "live.db"
    conn = open_db(db)
    apply_pending(conn, MAIN_SQL)
    conn.commit()
    conn.close()
    out = tmp_path / "published"

    pages = publish(db, out, now=1_787_000_000.0)

    assert pages >= 5 and (out / "read.html").exists()
    assert PublishScheduler(db, out)._interval == 6 * 3600.0


def test_regenerating_an_unchanged_store_rewrites_the_same_bytes(tmp_path):
    """Behavior: what makes a short interval reasonable. INV-067 keeps every
    timestamp out of the output, so a pass over an unchanged store is twelve
    identical files rather than churn."""
    from newz.store.db import open_db
    from newz.store.migrations import apply_pending
    from newz.surface.rhythm import publish

    db = tmp_path / "live.db"
    conn = open_db(db)
    apply_pending(conn, MAIN_SQL)
    conn.commit()
    conn.close()
    out = tmp_path / "published"

    publish(db, out, now=1_787_000_000.0)
    before = {p.name: p.read_bytes() for p in out.glob("*.html")}
    publish(db, out, now=1_787_999_999.0)

    assert {p.name: p.read_bytes() for p in out.glob("*.html")} == before


def test_a_page_removed_from_the_store_does_not_survive_a_regeneration(tmp_path):
    """Behavior: the surface is written whole, never incrementally — a stale
    file left behind is a page tracing to rows that are gone (INV-067)."""
    from newz.store.db import open_db
    from newz.store.migrations import apply_pending
    from newz.surface.rhythm import publish

    db = tmp_path / "live.db"
    conn = open_db(db)
    apply_pending(conn, MAIN_SQL)
    conn.commit()
    conn.close()
    out = tmp_path / "published"
    out.mkdir()
    (out / "leftover.html").write_text("a page from an older generation")

    publish(db, out, now=1_787_000_000.0)

    assert not (out / "leftover.html").exists()


def test_the_questions_page_carries_what_it_could_not_answer(tmp_path):
    """W12a's consumer. Behavior: 32 gaps existed and nothing read them but a
    counter — a signal the being generates at its own rate, about the world,
    with no reader at the other end. The question comes before the count
    (RT1): reading the count first invites adding sources, and the repeat
    failures may be questions no source can settle."""
    from newz.store.db import open_db
    from newz.store.migrations import apply_pending
    from newz.surface.generate import generate

    db = tmp_path / "s.db"
    conn = open_db(db)
    apply_pending(conn, MAIN_SQL)
    for i in range(3):
        conn.execute(
            "INSERT INTO source_gaps (ts, concern_id, query, gap, cause,"
            " candidates, rejected_floor, best_score) VALUES (?,?,?,?,?,?,?,?)",
            (1_787_000_000.0 + i, None, "Does open interest indicate distress?",
             "nothing was relevant enough to read", "floor", 6, 6, 0.31))
    conn.commit()
    out = tmp_path / "published"
    generate(conn, out, now=1_787_000_000.0)
    page = (out / "questions.html").read_text()
    conn.close()

    assert "Does open interest indicate distress?" in page
    assert "3 times" in page
    assert "nothing scored above the relevance floor" in page
    assert "best relevance 0.31" in page


def test_a_gap_recorded_before_the_cause_existed_is_not_a_category(tmp_path):
    """Behavior: NULL means 'written before this was recorded', never a fifth
    cause — the page says so rather than counting it as one."""
    from newz.store.db import open_db
    from newz.store.migrations import apply_pending
    from newz.surface.generate import generate

    db = tmp_path / "s.db"
    conn = open_db(db)
    apply_pending(conn, MAIN_SQL)
    conn.execute("INSERT INTO source_gaps (ts, concern_id, query, gap)"
                 " VALUES (?,?,?,?)", (1_787_000_000.0, None, "an old question",
                                       "sources answered but nothing was relevant"))
    conn.commit()
    out = tmp_path / "published"
    generate(conn, out, now=1_787_000_000.0)
    page = (out / "questions.html").read_text()
    conn.close()

    assert "recorded before the cause was" in page
