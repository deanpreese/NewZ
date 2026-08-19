"""The orientation pass (P3 epic E1.0) — a map, not a feed.

`data/feeds.yaml` carries an 18-entry `web` section that no code has ever
loaded: `load_feeds()` is called once in production and always with the default
`kind="rss"`. Fifteen of those entries are Wikipedia discipline overviews —
philosophy, history, mathematics, literature, religion, psychology, sociology,
anthropology, music, science, technology, economics, politics — and 16 of the
18 are non-financial, against a diet that came out 43% financial.

**They are not feeds and must not be wired as feeds.** They are static articles:
no items, no dates, nothing to watermark, nothing for `parse_feed()` to parse. A
feed of one unchanging article is a feed that reads the same thing forever.

What they are is a curriculum. The being has a map of market microstructure and
no map of anything else; this reads the overviews once, at abstract depth, so
there is a scaffold in fields it has never touched. It is a scaffold and not a
source: the value is whether concerns opened from it survive, which is the
week-one review's question, not this module's.

Logged under its own outlet. Wikipedia is already the being's largest read
source at 95 directed lookups through the research adapter, and if browsing
logged as lookup the coverage audit and the category shares would both be
corrupted — the project would congratulate itself on breadth it had not gained.

The three Reddit entries are excluded by default. User-generated content is the
injection surface INV-011 and INV-042 exist for, and scraping subreddit HTML
raises robots and terms questions the sovereign-adapter discipline has not
answered. `--include-social` is the operator's override, not a default.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

OUTLET = "wikipedia-orientation"

# Read once. A discipline overview is not news, and re-reading it would add
# nothing but tokens and a duplicate episode.
_ALREADY = (
    "SELECT 1 FROM episodes WHERE kind='reading' AND source_ref=? LIMIT 1"
)


@dataclass
class OrientationReport:
    read: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    opened: list[str] = field(default_factory=list)

    def render(self) -> str:
        return (f"orientation: read {len(self.read)}, already had "
                f"{len(self.skipped)}, failed {len(self.failed)}, "
                f"opened {len(self.opened)} question(s)")


def orientation_targets(feeds_path: Path, *, include_social: bool = False):
    """The `web` section, minus what this pass deliberately declines."""
    import yaml

    data = yaml.safe_load(Path(feeds_path).read_text()) or {}
    out = []
    for e in data.get("web") or []:
        if not e.get("url") or not e.get("enabled", True):
            continue
        if not include_social and e.get("category") == "social":
            continue
        out.append((str(e.get("name") or e["url"]), str(e["url"]),
                    str(e.get("category") or "")))
    return out


def _read_in_chunks(client, text: str, source: str):
    """Chunk before extracting, the way research does.

    Measured live 2026-08-18, and the reason this function exists: passing a
    6,000-char encyclopaedia article to `extract_claims` in one call blew the
    900-token output cap on 7 of 14 articles, and extraction fails CLOSED on
    truncation because `<manipulation>` is the last element of the schema and
    a cut response could carry claims with the safety signal amputated. The
    failure was correct; feeding it a whole article was not.

    INV-042 is honoured as research honours it: any hostile chunk quarantines
    the WHOLE document and returns immediately, because a page whose halves
    split an instruction across a boundary would otherwise contribute the
    claims from its clean chunks.
    """
    from newz.world.document import chunk
    from newz.world.extract import extract_claims

    claims: list[tuple[str, float]] = []
    seen: set[str] = set()
    quarantined = 0
    for piece in chunk(text):
        ex = extract_claims(client, piece, source=source)
        if ex.looks_hostile:
            return [], ex.quarantined, (ex.manipulation or "manipulation")
        quarantined += ex.quarantined
        for claim_text, conf in ex.claims:
            # chunk() overlaps by design, so a claim can repeat across a
            # boundary.
            if claim_text not in seen:
                seen.add(claim_text)
                claims.append((claim_text, conf))
    return claims, quarantined, ""


def run_orientation(client, conn: sqlite3.Connection, feeds_path: Path, *,
                    fetcher=None, include_social: bool = False,
                    limit: int | None = None) -> OrientationReport:
    """Read each discipline overview once, at abstract depth.

    Failure is per-article: an unreachable page costs that article and never
    the pass, the same rule the harvest applies to a bad feed.
    """
    from newz.store.episodes import write_episode
    from newz.world.diet import record_read
    from newz.world.document import fetch_document
    from newz.world.sources import Fetcher

    fetcher = fetcher or Fetcher()
    out = OrientationReport()

    for name, url, category in orientation_targets(
            feeds_path, include_social=include_social)[:limit]:
        if conn.execute(_ALREADY, (url,)).fetchone():
            out.skipped.append(name)
            continue
        # fetch_document returns None on EVERY failure — robots, timeout, PDF,
        # stub, unreducible page — and never raises; that collapse is INV-040's
        # strictly-additive rule, where a failed read costs the read and
        # nothing else. So there is one failure branch here, not two, and the
        # reason is in the document log rather than in this report.
        text = fetch_document(url, fetcher)
        if not text:
            out.failed.append(f"{name}: nothing readable")
            logger.info("orientation: %s yielded nothing readable", name)
            continue

        source = f"{OUTLET}:{url}"
        claims, quarantined, hostile = _read_in_chunks(client, text, source)
        record_read(conn, source=source, query=None, concern_id=None,
                    claims_kept=len(claims), quarantined=quarantined)
        # orientation=1: the row belongs here — the coverage audit and the
        # Wikipedia-as-adapter split both need it — but a curriculum read once
        # is not stream diet, and category_shares excludes it from the menu
        # ordering for that reason (0022).
        conn.execute(
            "INSERT INTO harvest_log (ts, feed, category, title, url,"
            " on_menu, was_read, orientation) VALUES (?, ?, ?, ?, ?, 1, ?, 1)",
            (time.time(), name, category, name, url, 1 if claims else 0))
        if hostile:
            out.failed.append(f"{name}: quarantined ({hostile})")
            conn.commit()
            continue
        if not claims:
            out.failed.append(f"{name}: no claims")
            conn.commit()
            continue
        extraction_claims = claims

        write_episode(
            conn, kind="reading", provenance=f"world:{OUTLET}",
            summary=(f"I read an overview of {category or name} ({name}) to "
                     f"orient myself in a field I had no map of. It asserts: "
                     + "; ".join(t for t, _ in extraction_claims[:4])),
            content={"title": name, "url": url, "feed": name,
                     "category": category, "orientation": True,
                     "claims": [t for t, _ in extraction_claims]},
            source_ref=url)
        conn.commit()
        out.read.append(name)
    return out
