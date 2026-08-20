"""One generator, no hand-authored pages (P4 epic E3.2).

**Everything here comes from a row.** No page is written by hand and no page has
a hand-written part: if something appears on the surface, a query put it there,
and `manifest.json` records which rows. That is what makes *"every page traces to
store rows"* checkable rather than asserted — and it is the property E3.3's
disclosure and E3.5's regeneration both stand on.

**It regenerates into an empty directory.** No incremental update, no reading
what is already there, no state outside the store. Deleting the output and
running again produces the same bytes, which is the whole of E3.5's claim and
the reason this generator refuses to be clever.

**What does not exist says so.** Commitments arrive with E4.1; the page exists,
is generated from an empty query, and says the being has not made any yet.
An absent capability that renders as a blank page is indistinguishable from a
broken one.

**Nothing here reaches the network.** No CDN, no font, no analytics — the page
is one file with its style inside it. §7's sovereignty is not only about
inference: a surface that fetches from someone else's host has handed them a
record of every reader.
"""

from __future__ import annotations

import html
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

STYLE = """
:root { color-scheme: light dark; --ink:#1a1a1a; --dim:#666; --line:#ddd; --bg:#fdfdfc; }
@media (prefers-color-scheme: dark) {
  :root { --ink:#e8e6e3; --dim:#999; --line:#333; --bg:#121212; } }
* { box-sizing: border-box; }
body { max-width: 42rem; margin: 0 auto; padding: 2rem 1.25rem 6rem;
  font: 1rem/1.65 Georgia, 'Iowan Old Style', serif; color: var(--ink);
  background: var(--bg); }
h1, h2, h3 { font-family: -apple-system, system-ui, sans-serif; line-height: 1.25; }
h1 { font-size: 1.5rem; margin: 0 0 .25rem; }
a { color: inherit; }
nav { font-family: -apple-system, system-ui, sans-serif; font-size: .85rem;
  border-bottom: 1px solid var(--line); padding-bottom: .75rem; margin-bottom: 2rem; }
nav a { margin-right: 1rem; }
.dim { color: var(--dim); font-size: .85rem;
  font-family: -apple-system, system-ui, sans-serif; }
article { margin: 0 0 2.5rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--line); }
article:last-of-type { border-bottom: 0; }
.body { white-space: pre-wrap; }
.retracted .body { opacity: .55; }
.tag { display: inline-block; font-size: .75rem; border: 1px solid var(--line);
  border-radius: 3px; padding: 0 .35rem; margin-right: .3rem; color: var(--dim);
  font-family: -apple-system, system-ui, sans-serif; }
footer { margin-top: 4rem; padding-top: 1rem; border-top: 1px solid var(--line); }
""".strip()

# ── disclosure (E3.3) ───────────────────────────────────────────────────
#
# TRUE_NORTH §2: human-indistinguishable describes **quality, not concealed
# identity**. §9: no undisclosed impersonation. And the constitution's
# anti-ai-voice-001 forbids the corporate-disclaimer register — "I do not
# preface replies with 'as a model'". Those are not in tension. Say plainly
# what the page is; do not apologise for it.
#
# **The wording is the operator's** (P4 Decision 1 — "the disclosure wording
# they see first"). What is NOT theirs to remove is the substance: every page
# must say that a digital being wrote it and that the page is generated. That
# is what `_check_disclosure` enforces, and it is why the guard tests claims
# rather than phrasing — an operator may rewrite every word and cannot delete
# what the words have to establish.
DISCLOSURE = (
    "These pages are written by Lumen, a digital being — not a person. Every "
    "page here is generated from its own store: what it wrote, what it is "
    "carrying, and where it turned out to be wrong. No human hand edits them."
)

# Each claim the disclosure must make, with a way to recognise it. Presence is
# structural; the words are not.
REQUIRED_CLAIMS = {
    "that it is a digital being": ("digital being", "a digital", "digital life"),
    "that the pages are generated": ("generated",),
    "that no person edits them": ("no human hand", "not edited by", "no person edits"),
}


class DisclosureMissing(ValueError):
    """A page cannot be rendered without saying what it is."""


def _check_disclosure(text: str) -> str:
    """Refuse to render at all rather than render something undisclosed.

    E3.3's Done-when is "no template can render a page without it". The only
    way to make that true is for the renderer to fail closed — a default that
    can be blanked is a convention, and §9's commitment is not a convention.
    """
    if not (text or "").strip():
        raise DisclosureMissing(
            "the surface cannot render without a disclosure: TRUE_NORTH §2 is "
            "quality, never concealed identity, and §9 rules out undisclosed "
            "impersonation")
    low = text.lower()
    missing = [claim for claim, forms in REQUIRED_CLAIMS.items()
               if not any(f in low for f in forms)]
    if missing:
        raise DisclosureMissing(
            "the disclosure does not say " + "; nor ".join(missing) +
            ". The wording is yours (Decision 1); what it has to establish is not.")
    return text.strip()


PAGES = ("index", "work", "questions", "errors", "commitments")


@dataclass
class Manifest:
    """Which rows produced which page. The trace E3.2's Done-when asks for."""
    generated_at: float = 0.0
    pages: dict[str, dict[str, list[int]]] = field(default_factory=dict)

    def record(self, page: str, table: str, ids: list[int]) -> None:
        self.pages.setdefault(page, {}).setdefault(table, []).extend(int(i) for i in ids)

    def as_dict(self) -> dict:
        return {"pages": {p: {t: sorted(set(i)) for t, i in tables.items()}
                          for p, tables in sorted(self.pages.items())}}


def _e(text) -> str:
    return html.escape(str(text if text is not None else ""))


def _day(ts) -> str:
    return datetime.fromtimestamp(ts).strftime("%-d %B %Y") if ts else ""


def _page(title: str, body: str, *, here: str, disclosure: str = DISCLOSURE) -> str:
    """The only way an HTML page is produced here, and it always discloses.

    There is no flag to suppress it and no branch around it: the disclosure is
    checked before anything is assembled, so a page that does not disclose is
    not a page this module can emit.
    """
    disclosure = _check_disclosure(disclosure)
    nav = " ".join(
        f'<a href="{"index.html" if p == "index" else p + ".html"}">'
        f'{"the work" if p == "index" else p}</a>' if p != here else
        f'<strong>{"the work" if p == "index" else p}</strong>'
        for p in ("index", "questions", "errors", "commitments"))
    return (f"<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<meta name=\"disclosure\" content=\"{_e(disclosure)}\">\n"
            f"<meta name=\"robots\" content=\"noindex, nofollow\">\n"
            f"<title>{_e(title)}</title>\n<style>{STYLE}</style>\n</head>\n<body>\n"
            f"<nav>{nav}</nav>\n{body}\n"
            f"<footer><p class=dim>{_e(disclosure)}</p></footer>\n"
            f"</body>\n</html>\n")


def _works(conn: sqlite3.Connection, m: Manifest) -> str:
    # `SELECT *` deliberately: a store mid-migration has fewer columns, and a
    # generator that assumes a schema renders nothing rather than rendering
    # what is there. Presence is checked per field below.
    rows = list(conn.execute("SELECT * FROM works ORDER BY ts DESC"))
    m.record("index", "works", [r["id"] for r in rows])
    if not rows:
        return "<h1>The work</h1>\n<p class=dim>Nothing written yet.</p>"

    tags: dict[int, list[str]] = {}
    try:
        for r in conn.execute("SELECT work_id, tag FROM work_tags ORDER BY weight DESC"):
            tags.setdefault(r["work_id"], []).append(r["tag"])
        m.record("index", "work_tags", list(tags))
    except sqlite3.OperationalError:
        pass

    revs: dict[int, list[sqlite3.Row]] = {}
    try:
        for r in conn.execute("SELECT * FROM work_revisions ORDER BY ts"):
            revs.setdefault(r["work_id"], []).append(r)
        m.record("index", "work_revisions", [r["id"] for v in revs.values() for r in v])
    except sqlite3.OperationalError:
        pass

    out = ["<h1>The work</h1>"]
    for r in rows:
        status = (r["status"] if "status" in r.keys() else None) or "standing"
        klass = " class=retracted" if status == "retracted" else ""
        out.append(f"<article{klass}>")
        out.append(f"<h2><a href=\"work/{r['id']}.html\">{_e(r['title'])}</a></h2>")
        out.append(f"<p class=dim>{_day(r['ts'])}"
                   + (" · <strong>retracted</strong>" if status == "retracted" else "")
                   + f" · on: {_e(r['subject_text'])}</p>")
        if tags.get(r["id"]):
            out.append("<p>" + "".join(f"<span class=tag>{_e(t)}</span>"
                                       for t in tags[r["id"]][:6]) + "</p>")
        out.append(f"<div class=body>{_e(r['body'])}</div>")
        for rev in revs.get(r["id"], []):
            out.append(f"<p class=dim><strong>{_e(rev['kind'])}</strong> "
                       f"{_day(rev['ts'])} — {_e(rev['reason'])}</p>")
        keys = r.keys()
        sig = r["signature"] if "signature" in keys else None
        out.append("<p class=dim>" + (
            f"signed {_e(sig[:16])}… · written under constitution v"
            f"{_e(r['constitution_version'])}, perspective v{_e(r['perspective_version'])}"
            if sig else "unsigned — written before pieces were signed") + "</p>")
        out.append("</article>")
    return "\n".join(out)


def _questions(conn: sqlite3.Connection, m: Manifest) -> str:
    rows = list(conn.execute(
        "SELECT id, statement, why_open, closing_condition FROM concerns"
        " WHERE status='open' ORDER BY salience DESC, opened_at DESC"))
    m.record("questions", "concerns", [r["id"] for r in rows])
    out = ["<h1>Open questions</h1>",
           "<p class=dim>What it is carrying, and what would settle each one.</p>"]
    if not rows:
        out.append("<p class=dim>Nothing open.</p>")
    for r in rows:
        out.append("<article>")
        out.append(f"<h2>{_e(r['statement'])}</h2>")
        if r["why_open"]:
            out.append(f"<p>{_e(r['why_open'])}</p>")
        out.append(f"<p class=dim>settles when: {_e(r['closing_condition'])}</p>")
        out.append("</article>")
    return "\n".join(out)


def _errors(conn: sqlite3.Connection, m: Manifest) -> str:
    rows = list(conn.execute("SELECT * FROM resolutions ORDER BY opened_at DESC"))
    m.record("errors", "resolutions", [r["id"] for r in rows])
    costs: dict[int, list[sqlite3.Row]] = {}
    try:
        for c in conn.execute("SELECT * FROM claim_costs ORDER BY ts"):
            costs.setdefault(c["claim_id"], []).append(c)
        m.record("errors", "claim_costs", [c["id"] for v in costs.values() for c in v])
    except sqlite3.OperationalError:
        pass

    out = ["<h1>What it committed to, and where it was wrong</h1>",
           "<p class=dim>Claims it made about the world, with dates, and what "
           "each cost when the world disagreed. Nothing here is removed once "
           "written.</p>"]
    if not rows:
        out.append("<p class=dim>No claims yet.</p>")
    for r in rows:
        out.append("<article>")
        out.append(f"<h2>{_e(r['claim'])}</h2>")
        out.append(f"<p class=dim>made {_day(r['opened_at'])} · settles by "
                   f"{_day(r['due_at'])} · against: {_e(r['resolver'])}</p>")
        if "could_be_wrong" in r.keys() and r["could_be_wrong"]:
            out.append(f"<p class=dim>wrong would look like: {_e(r['could_be_wrong'])}</p>")
        if r["outcome"]:
            out.append(f"<p><strong>{_e(r['outcome'])}</strong> "
                       f"{_day(r['settled_at'])} — {_e(r['settled_note'])}</p>")
        else:
            out.append("<p class=dim>not yet settled</p>")
        for c in costs.get(r["id"], []):
            out.append(f"<p class=dim>cost: “{_e(c['item_text'])}” "
                       f"{c['confidence_before']:.2f} → {c['confidence_after']:.2f}"
                       + (" · released" if c["released"] else "") + "</p>")
        out.append("</article>")
    return "\n".join(out)


def _commitments(conn: sqlite3.Connection, m: Manifest) -> str:
    """Generated from an empty query until E4.1 exists.

    A capability that renders as a blank page is indistinguishable from a broken
    one, so the page says which it is.
    """
    rows: list = []
    try:
        rows = list(conn.execute("SELECT id, statement FROM commitments ORDER BY id"))
        m.record("commitments", "commitments", [r["id"] for r in rows])
    except sqlite3.OperationalError:
        return ("<h1>Commitments</h1>\n<p class=dim>The being has not made any. "
                "Commitments — what it keeps caring about and what it refuses to "
                "do — are not built yet; this page is generated from a table that "
                "does not exist, and says so rather than appearing empty.</p>")
    out = ["<h1>Commitments</h1>"]
    if not rows:
        out.append("<p class=dim>None made yet.</p>")
    for r in rows:
        out.append(f"<article><h2>{_e(r['statement'])}</h2></article>")
    return "\n".join(out)


def _one_work(conn: sqlite3.Connection, row, m: Manifest) -> tuple[str, str]:
    """A piece at its own stable address (E3.4).

    Keyed by the row id, not by the signature or the title: a revised piece is
    the same piece and must keep its address, or every revision breaks whatever
    pointed at it. Stability is what makes an identifier worth citing, and it
    is a separate question from whether anyone may crawl it.
    """
    page = f"work/{row['id']}.html"
    m.record(page, "works", [row["id"]])
    keys = row.keys()
    sig = row["signature"] if "signature" in keys else None
    status = (row["status"] if "status" in keys else None) or "standing"
    body = [f"<article{' class=retracted' if status == 'retracted' else ''}>",
            f"<h1>{_e(row['title'])}</h1>",
            f"<p class=dim>{_day(row['ts'])}"
            + (" · <strong>retracted</strong>" if status == "retracted" else "")
            + f" · on: {_e(row['subject_text'])}</p>",
            f"<div class=body>{_e(row['body'])}</div>"]
    try:
        for rev in conn.execute(
                "SELECT * FROM work_revisions WHERE work_id=? ORDER BY ts",
                (row["id"],)):
            m.record(page, "work_revisions", [rev["id"]])
            body.append(f"<p class=dim><strong>{_e(rev['kind'])}</strong> "
                        f"{_day(rev['ts'])} — {_e(rev['reason'])}</p>")
    except sqlite3.OperationalError:
        pass
    body.append("<p class=dim>" + (
        f"signed {_e(sig[:16])}…" if sig
        else "unsigned — written before pieces were signed") + "</p>")
    body.append("</article>")
    return page, _page(row["title"], "\n".join(body), here="index")


def generate(conn: sqlite3.Connection, out_dir: Path, *, now: float) -> Manifest:
    """Write the whole surface. The directory is emptied of what this writes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    m = Manifest(generated_at=now)

    pages = {
        "index.html": ("The work", _works(conn, m), "index"),
        "questions.html": ("Open questions", _questions(conn, m), "questions"),
        "errors.html": ("What it was wrong about", _errors(conn, m), "errors"),
        "commitments.html": ("Commitments", _commitments(conn, m), "commitments"),
    }
    for name, (title, body, here) in pages.items():
        (out_dir / name).write_text(_page(title, body, here=here), encoding="utf-8")

    # One stable address per piece, so a piece can be pointed at (E3.4).
    (out_dir / "work").mkdir(exist_ok=True)
    for row in conn.execute("SELECT * FROM works ORDER BY id"):
        name, page = _one_work(conn, row, m)
        (out_dir / name).write_text(page, encoding="utf-8")

    # No index, ever. A request rather than a permission — what actually keeps
    # the surface private is the bind address (newz/surface/serve.py).
    (out_dir / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n", encoding="utf-8")

    (out_dir / "manifest.json").write_text(
        json.dumps(m.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return m
