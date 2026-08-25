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

    # Asserted as a subset: an earlier version pinned the exact file set and
    # broke the hour E3.4 added robots.txt and the per-piece pages. What must
    # always be there is the manifest and the request not to be indexed —
    # neither is a page, and each carries a guarantee rather than a view.
    required = {"manifest.json", "robots.txt"}
    assert required <= {p.name for p in out.iterdir()}
    # Essay pages only (operator, 2026-08-24).
    assert not list(out.glob("*.md")), "no whole-store page survives"
    assert "On rolling over" in (out / "work" / "1.md").read_text()


def test_every_page_traces_to_store_rows(store, tmp_path):
    """Done-when, second half. Behavior: the manifest names the rows behind each
    page, so "nothing here was hand-written" is checkable and not asserted."""
    _, manifest = _generate(store, tmp_path)

    assert manifest["pages"]["work/1.md"]["works"] == [1]


def test_regenerating_produces_the_same_bytes(store, tmp_path):
    """What E3.5's byte-comparable claim rests on. Behavior: the generator is
    deterministic — no timestamps in the output, no ordering by anything
    unstable."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    generate(store, a, now=1_000_000.0)
    generate(store, b, now=2_000_000.0)

    for name in ("work/1.md", "manifest.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_there_are_no_hand_authored_pages_anywhere(store, tmp_path):
    """The epic's own words. Behavior: no page or fragment of one is a file on
    disk — every byte of the surface comes from code reading a row, so the
    manifest can trace all of it.

    **This test could not stay an extension check.** It globbed the repo for
    `*.html`, which worked while the surface was HTML and the repo had none.
    The surface is markdown now (operator, 2026-08-22) and the repo is full of
    legitimate markdown — PLAN, INVARIANTS, every proposal — so the same glob
    renamed would assert the plan does not exist. What the epic actually
    forbids is a TEMPLATE: a page whose provenance is a person rather than a
    query, sitting beside the generator, which is what this looks for now.
    """
    templates = [p for p in (REPO / "newz" / "surface").rglob("*")
                 if p.is_file() and p.suffix in {".md", ".html", ".jinja",
                                                 ".j2", ".mustache", ".tmpl"}]

    assert templates == [], f"hand-authored page content: {templates}"


def test_nothing_on_the_surface_reaches_the_network(store, tmp_path):
    """§7. Behavior: no CDN, no font, no analytics. Sovereignty is not only
    about inference — a page that fetches from someone else's host has handed
    them a record of every reader."""
    out, _ = _generate(store, tmp_path)

    for page in out.rglob("*.md"):
        text = page.read_text()
        assert not re.search(r'(src|href)\s*=\s*["\']https?://', text), page.name
        assert "<script" not in text.lower(), page.name


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
    text = (out / "work" / "1.md").read_text()

    assert "On rolling over" in text
    assert "retracted" in text
    assert "its central claim does not survive" in text
    assert manifest["pages"]["work/1.md"]["work_revisions"] == [1]


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
            g._page("t", "<p>body</p>")


def test_every_generated_page_discloses_twice(store, tmp_path):
    """Behavior: in the head, where a machine reads it, and in the body, where
    a person does. A page disclosing only in metadata discloses to crawlers."""
    out, _ = _generate(store, tmp_path)

    for page in out.rglob("*.md"):
        text = page.read_text()
        # Front matter is where the old `<meta name="disclosure">` went: the
        # place a machine reads without parsing prose.
        assert "\ndisclosure: " in text, page.name
        assert text.rstrip().endswith("*"), page.name          # the closing line
        assert "digital being" in text.rsplit("\n---\n", 1)[1], page.name


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
            g._page("t", "<p>b</p>")


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
            g._page("t", "<p>b</p>")


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

    assert (a / "work" / "1.md").read_bytes() == (b / "work" / "1.md").read_bytes()


# ── the read, rendered (E3.6) ───────────────────────────────────────────

def _body(page: Path) -> str:
    """The rendered content, without the front matter, the nav or the footer.

    Asserting against the whole document catches the furniture. While the
    surface was HTML this stripped the stylesheet — an earlier no-aggregate
    test matched a word in the CSS, and the ungraded-metric test matched
    `max-width: 42rem` while looking for the number 42. Markdown has no
    stylesheet, but the disclosure and the nav are still content that no
    assertion about the READING should see.
    """
    text = page.read_text()
    after_front = text.split("\n---\n\n", 1)[1]     # past the front matter
    _nav, _, rest = after_front.partition("\n\n")   # past the nav line
    return rest.rsplit("\n---\n\n", 1)[0]          # before the disclosure


def _reading(conn, metric, value, *, ts, status="ok", note="", window=168.0, dv=1):
    conn.execute(
        "INSERT INTO mon.metric_readings (ts, metric, status, value, window_hours,"
        " note, definition_version) VALUES (?,?,?,?,?,?,?)",
        (ts, metric, status, value, window, note, dv))
    conn.commit()


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

    # An empty store has no essays, and `publish` now counts essay pages —
    # the surface IS the essays (operator, 2026-08-24).
    assert pages == 0 and (out / "manifest.json").exists()
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
    before = {p.name: p.read_bytes() for p in out.rglob("*.md")}
    publish(db, out, now=1_787_999_999.0)

    assert {p.name: p.read_bytes() for p in out.rglob("*.md")} == before


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




# ── the operator's verdict decides what is published (0044) ─────────────

def test_an_unappraised_piece_is_published(store, tmp_path):
    """Behavior: the default does not change until the operator says
    something. A verdict nobody gave is not a verdict against."""
    out, _ = _generate(store, tmp_path)

    assert (out / "work" / "1.md").exists()


def test_a_piece_judged_not_publishable_is_withheld(store, tmp_path):
    """What the word means. Behavior: the field decides the surface, so a
    verdict does work rather than sitting in a column."""
    from newz.works.appraisal import record

    record(store, 1, False, "it restates the last three")

    out, manifest = _generate(store, tmp_path)

    assert not (out / "work" / "1.md").exists()
    assert "work/1.md" not in manifest["pages"]


def test_withholding_is_not_deletion(store, tmp_path):
    """E1.5's discipline applied to publication. Behavior: the row, the body
    and the signature are untouched, and the piece returns the moment a newer
    appraisal says so — a surface the operator can empty is not a record."""
    from newz.works.appraisal import record

    record(store, 1, False, "not yet")
    _generate(store, tmp_path)
    row = store.execute("SELECT * FROM works WHERE id=1").fetchone()
    assert row["body"] == "The index is rolling over and the reason is structural."
    assert row["status"] == "standing"

    record(store, 1, True, "the revision fixed it")
    out, _ = _generate(store, tmp_path)

    assert (out / "work" / "1.md").exists()


def test_the_newest_verdict_is_the_one_that_counts(store, tmp_path):
    """Behavior: a piece can be judged more than once and the last word is the
    operator's current one — otherwise the loop cannot close, because nothing
    the being did in response could ever change the outcome."""
    from newz.works.appraisal import current_verdict, record

    record(store, 1, True, "fine")
    record(store, 1, False, "on reflection, no")

    assert current_verdict(store, 1) == 0
    out, _ = _generate(store, tmp_path)
    assert not (out / "work" / "1.md").exists()


def test_an_essay_page_has_no_nav(store, tmp_path):
    """Behavior: the nav linked five sibling pages that no longer exist. A
    page is one essay, so there is nowhere to navigate to and a nav line would
    be five dead links on every piece."""
    out, _ = _generate(store, tmp_path)
    text = (out / "work" / "1.md").read_text()

    for gone in ("index.md", "questions.md", "errors.md",
                 "commitments.md", "read.md"):
        assert gone not in text, gone
