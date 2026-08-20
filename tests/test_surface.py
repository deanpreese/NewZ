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

import pytest

from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.surface.generate import generate

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
REPO = Path(__file__).resolve().parent.parent
DAY = 86400.0


@pytest.fixture
def store(tmp_path):
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

    assert {p.name for p in out.iterdir()} == {
        "index.html", "questions.html", "errors.html", "commitments.html",
        "manifest.json"}
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
    """Behavior: commitments arrive with E4.1. The page is generated from a
    table that does not exist and says which — an absent capability rendering
    as a blank page is indistinguishable from a broken one."""
    out, _ = _generate(store, tmp_path)

    text = (out / "commitments.html").read_text()
    assert "not built yet" in text
    assert "says so rather than appearing empty" in text


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
