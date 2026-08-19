"""Feeds and canon (S2 §9.1) — the world arriving unasked.

> Sovereign adapters … **plus operator-curated feeds and canon**.

The last of the six gaps in the 2026-08-13 audit, and the one that was
actually the starvation. `data/feeds.yaml` (61 RSS sources) and
`data/canon.yaml` (curated long texts) had **zero readers**; the only path
to the world was query-driven research inside deliberation, which had
returned four sources in the being's entire life. Everything else it holds
came from the operator or from itself.

**Why this is the hard one.** Research triages a source against a concern's
*question*. A feed item arrives with no question, and that is the point —
feeds are how the being encounters what it did not know to ask. It is also
exactly where v1 died: 84,793 claims stored, 0.066% ever cited.

The selection ratio is the design. Sixty-one feeds offer on the order of
hundreds of items a day; the §9.1 budget invariant permits roughly twenty
reads a week. So this must reject ~99% of what it sees, cheaply, and it does
that in three stages of increasing cost:

1. **Watermark** — only items newer than the feed's last poll. Free.
2. **The menu** — capped per feed, round-robined across categories by how
   under-read each is, shuffled. Local, no model call, and deliberately NOT
   ranked against what the being already carries (E1.0, 2026-08-18: that
   ranking made reading a function of the questions and the questions a
   function of the reading, and 27 of 61 feeds went unread forever).
3. **One judgment call** over the menu, which is the only judgment, and costs
   the same for four candidates as for twelve.

**It runs inside deliberation, not ambient.** INV-012 is structural — the
test asserts that nothing under `newz/ambient/` can even import the web path
— so feeds arrive on the deliberation cadence and under the same budget gate
as research. That is a real constraint honoured, not a preference.
"""

from __future__ import annotations

import datetime as _dt
import logging
import sqlite3
import time
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Feeds polled per deliberation cycle. Sixty-one at once would be a burst of
# HTTP and a burst of candidates; a rolling subset keeps both flat and every
# feed still comes round within a few cycles.
FEEDS_PER_CYCLE = 12

# How many items reach the judgment call. One call either way, so this is
# bounded by prompt size and by how much the being could plausibly read, not
# by cost.
SHORTLIST = 12

# How many items any one feed may contribute to a single menu. Bloomberg
# publishes hourly and Aeon weekly; without this the menu reflects publication
# volume rather than the operator's curation, which is 15% financial while the
# diet it produced was 43% (measured 2026-08-18).
OFFERS_PER_FEED = 3

# Items with no usable date are treated as new once, then watermarked by
# poll time — a feed without dates should not replay forever.
MAX_ITEMS_PER_FEED = 25


@dataclass
class Feed:
    name: str
    url: str
    category: str = ""
    reliability: float = 0.5
    poll_interval_s: float = 3600.0
    enabled: bool = True


@dataclass
class FeedItem:
    feed: Feed
    title: str
    summary: str
    url: str
    published: float = 0.0

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.summary}".strip()


@dataclass
class FeedHarvest:
    polled: int = 0
    offered: int = 0
    shortlisted: int = 0
    kept: list[FeedItem] = field(default_factory=list)
    opened: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    skipped_reason: str = ""

    def render(self) -> str:
        if self.skipped_reason:
            return f"I did not read the feeds: {self.skipped_reason}"
        s = (f"I looked at {self.offered} new item(s) across {self.polled} "
             f"feed(s), shortlisted {self.shortlisted}, and kept "
             f"{len(self.kept)}.")
        if self.opened:
            s += f" {len(self.opened)} of them raised a question I did not have."
        return s


def load_feeds(path: Path, *, kind: str = "rss") -> list[Feed]:
    """Read the operator's curated list. The file is the provenance record."""
    import yaml

    data = yaml.safe_load(Path(path).read_text()) or {}
    out = []
    for e in data.get(kind) or []:
        if not e.get("enabled", True) or not e.get("url"):
            continue
        # str(): YAML 1.1 parses bare on/off/yes/no as booleans, so a
        # feed named "On" arrives as True and renders as "True" in the
        # being's own provenance. Coerce rather than trust the file.
        out.append(Feed(
            name=str(e.get("name") or e["url"]), url=str(e["url"]),
            category=e.get("category", ""),
            reliability=float(e.get("reliability", 0.5)),
            poll_interval_s=float(e.get("poll_interval_seconds", 3600)),
        ))
    return out


# ── parsing ──────────────────────────────────────────────────────────────

_DATE_FORMATS = ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                 "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d")


def _parse_date(raw: str | None) -> float:
    if not raw:
        return 0.0
    raw = raw.strip().replace("GMT", "+0000")
    for fmt in _DATE_FORMATS:
        try:
            return _dt.datetime.strptime(raw, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _text(el, *names: str) -> str:
    for n in names:
        found = el.find(n)
        if found is not None:
            if found.text:
                return found.text.strip()
            if found.get("href"):
                return found.get("href").strip()
    return ""


def parse_feed(xml: str, feed: Feed) -> list[FeedItem]:
    """RSS 2.0 and Atom, without a dependency.

    Deliberately tolerant: a feed that half-parses yields the items it can
    rather than nothing, because one malformed entry should not cost the
    being the whole source.
    """
    from newz.world.sources import strip_tags

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        logger.warning("feed %s did not parse: %s", feed.name, e)
        return []

    ns = "{http://www.w3.org/2005/Atom}"
    entries = root.findall(".//item") or root.findall(f".//{ns}entry")
    out: list[FeedItem] = []
    for el in entries[:MAX_ITEMS_PER_FEED]:
        title = strip_tags(_text(el, "title", f"{ns}title"))
        summary = strip_tags(_text(el, "description", "summary",
                                   f"{ns}summary", f"{ns}content"))
        url = _text(el, "link", f"{ns}link", "guid")
        if not title and not summary:
            continue
        out.append(FeedItem(
            feed=feed, title=title[:300], summary=summary[:1500], url=url,
            published=_parse_date(_text(el, "pubDate", "published",
                                        f"{ns}published", f"{ns}updated"))))
    return out


# ── watermarks ───────────────────────────────────────────────────────────

def due_feeds(conn: sqlite3.Connection, feeds: list[Feed],
              now: float | None = None, limit: int = FEEDS_PER_CYCLE) -> list[Feed]:
    """Feeds whose poll interval has elapsed, least-recently-polled first."""
    now = now or time.time()
    state = {r["url"]: r for r in conn.execute(
        "SELECT url, last_polled FROM feed_state")}
    due = [f for f in feeds
           if now - (state[f.url]["last_polled"] if f.url in state else 0)
           >= f.poll_interval_s]
    due.sort(key=lambda f: (state[f.url]["last_polled"] if f.url in state else 0))
    return due[:limit]


def new_items(conn: sqlite3.Connection, feed: Feed,
              items: list[FeedItem]) -> list[FeedItem]:
    row = conn.execute(
        "SELECT last_item_ts FROM feed_state WHERE url=?", (feed.url,)).fetchone()
    watermark = row["last_item_ts"] if row else 0.0
    # A feed with no dates at all: everything is "new" the first time and
    # nothing after, because the poll watermark moves regardless.
    return [i for i in items if i.published > watermark] if watermark else items


def mark_polled(conn: sqlite3.Connection, feed: Feed, items: list[FeedItem],
                error: str | None = None) -> None:
    now = time.time()
    newest = max((i.published for i in items), default=0.0)
    conn.execute(
        "INSERT INTO feed_state (url, name, last_polled, last_item_ts,"
        " failures, last_error) VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(url) DO UPDATE SET last_polled=excluded.last_polled,"
        " last_item_ts=MAX(feed_state.last_item_ts, excluded.last_item_ts),"
        " failures=CASE WHEN excluded.last_error IS NULL THEN 0"
        "               ELSE feed_state.failures + 1 END,"
        " last_error=excluded.last_error",
        (feed.url, feed.name, now, newest, 1 if error else 0, error))
    conn.commit()


# ── selection ────────────────────────────────────────────────────────────

_TRIAGE_SYSTEM = (
    "You are the reading judgment of a digital being deciding what, if "
    "anything, in today's feeds is worth its attention. You respond with XML "
    "only. Keeping nothing is an ordinary answer."
)

# The passing case first and worked, per the lesson this repository has now
# paid for six times. Without it a strict instruction yields refusal rather
# than discrimination — and here refusal looks like success, because keeping
# nothing is always available.
#
# What the being carries is deliberately ABSENT from this prompt (E1.0). It
# used to open with "here is what I am carrying", which rebuilt the concern
# filter inside the judgment even after the ranking was removed: an item was
# kept if it bore on an open question, and every open question was market
# microstructure. The judgment is now made cold, on the item itself.
_TRIAGE_TASK = """<task>
Some items arrived today. Decide which — if any — are worth reading properly.

Read something because it is IMPORTANT or because it is INTERESTING. Those
are different and both count. Important: it would change what someone
believes about how the world works. Interesting: it names a difficulty, a
tension, or a thing you did not know was a thing.

WORTH READING — worked examples:

  item: "A neurologist on why improvisation resists notation"
  -> KEEP. It names a tension — a practice that resists its own record —
  and that is a question worth carrying.

  item: "CFTC clarifies event-contract rules after Polymarket settlement"
  -> KEEP. A specific mechanism changed, and the change is checkable.

  item: "What the Antikythera mechanism's gearing implies about lost Greek
  engineering traditions"
  -> KEEP. You know nothing about this. That is a reason to read it, not a
  reason to skip it.

NOT WORTH READING — the ordinary case:

  item: "Markets close mixed ahead of jobs data"
  -> SKIP. An event, not a claim. Nothing would be established by reading it.

  item: "Ten things to know about the new AI rules"
  -> SKIP. A summary of a summary; it would give you nothing you could cite.

Do NOT keep an item because it is near a subject you already work on, and do
NOT skip one because it is far from everything you already work on. Being
unfamiliar is not a defect. Judge the item.

Keep at most 3.

Output ONLY:

<triage>
  <keep n="ITEM NUMBER">why this one, in one clause</keep>
</triage>
</task>"""


def build_menu(conn: sqlite3.Connection, items: list[FeedItem], *,
               k: int = SHORTLIST, per_feed: int = OFFERS_PER_FEED,
               rng: random.Random | None = None) -> list[FeedItem]:
    """Choose what the being is SHOWN. No model call, and no ranking against
    what it already carries.

    Until 2026-08-18 this ranked candidates by embedding similarity against the
    open concerns, which made the reading a function of the questions and the
    questions a function of the reading: all six open concerns were market
    microstructure, so 27 of 61 curated feeds — the whole philosophy,
    literature and long-form science wing — had been polled continuously and
    read zero times. The being cannot ask a new kind of question if it is only
    ever shown answers to the kind it already asks.

    What replaces it shapes the MENU and never refuses a read:

    - a cap per feed, because Bloomberg publishes hourly and Aeon weekly, and
      an uncapped menu is finance-heavy by publication volume alone;
    - a round-robin across categories, ordered by how under-read each category
      is in the recent diet, so breadth is offered rather than imposed;
    - a shuffle, because a long list has position bias and an unshuffled menu
      would quietly favour whichever feed sorted first.

    The target is on offers, deliberately. A cap that REFUSED a read to keep
    the mix balanced would be the fetch-time veto R-28 already diagnosed: it
    manufactures balance against S2 §13 and TRUE_NORTH §8, and it writes
    "nothing was relevant enough to read" into the very record §9.1 uses to
    decide which sources to add. Balance the menu; never refuse the meal.
    """
    rng = rng or random.Random()
    if len(items) <= k:
        out = list(items)
        rng.shuffle(out)
        return out

    by_feed: dict[str, list[FeedItem]] = {}
    for i in items:
        by_feed.setdefault(i.feed.name, []).append(i)
    pools: dict[str, list[FeedItem]] = {}
    for feed_items in by_feed.values():
        feed_items.sort(key=lambda i: -i.published)
        for i in feed_items[:per_feed]:
            pools.setdefault(i.feed.category or "uncategorised", []).append(i)

    from newz.world.diet import category_shares

    read_share = category_shares(conn)
    # Least-read categories go first, so an under-read category gets its pick
    # before a well-read one — a target, not a quota. A category absent from
    # the recent diet scores 0.0 and leads.
    order = sorted(pools, key=lambda c: (read_share.get(c, 0.0), c))
    for pool in pools.values():
        rng.shuffle(pool)

    out: list[FeedItem] = []
    while len(out) < k and any(pools[c] for c in order):
        for c in order:
            if pools[c]:
                out.append(pools[c].pop())
                if len(out) == k:
                    break
    rng.shuffle(out)
    return out


def triage(client, conn: sqlite3.Connection,
           items: list[FeedItem]) -> list[FeedItem]:
    """The one judgment. Returns what is worth reading properly."""
    from newz.llm.xml_parser import XMLExtractionError, extract_xml
    from newz.untrusted import wrap

    if not items:
        return []
    # Every feed item is untrusted external text (INV-011): fenced and
    # trust-tagged, never interpolated raw into a prompt.
    listing = "\n\n".join(
        f"ITEM {n}: " + wrap(i.text[:900], source=f"feed:{i.feed.name}",
                             trust="world").render()
        for n, i in enumerate(items, start=1))
    prompt = f"{_TRIAGE_TASK}\n\nTODAY'S ITEMS:\n{listing}"
    root = None
    # One retry, and only on an UNREADABLE answer — never on a judgment.
    #
    # An unparseable triage keeps nothing, which is indistinguishable from an
    # honest "nothing today" because keeping nothing is the ordinary answer.
    # That is the same blindness that hid R-27 for a day, and it is not
    # hypothetical here: measured 2026-08-16, one production call in
    # seventeen was lost this way. The model wrote `<keep 1>` instead of
    # `<keep n="1">` — invalid XML — discarding a real judgment that a Max
    # Tegmark piece "directly bears on the unresolved tension between public
    # AI demonstrations and actual security posture".
    #
    # Third appearance of the same class: `</worth_pursving>` in the opener,
    # `<tri>` under probe, `<keep 1>` here. The retry is HERE and not in
    # `extract_xml`, deliberately — that parser also reads the outbound
    # gate's verdicts, and a lenient parser on a safety path buys this
    # nothing and costs the gate its strictness.
    for attempt in (1, 2):
        try:
            result = client.complete(
                "AMBIENT", _TRIAGE_SYSTEM, prompt,
                max_tokens=600, temperature=0.2, function="ingest")
            root = extract_xml(result.text, "triage")
            break
        except XMLExtractionError as e:
            logger.info("feed triage unreadable (attempt %d): %s", attempt, e)
        except Exception as e:  # noqa: BLE001
            logger.warning("feed triage failed (%s) — keeping nothing", e)
            return []
    if root is None:
        # Still failing closed after the retry: an unreadable triage reads
        # nothing rather than everything.
        logger.warning("feed triage unreadable twice — keeping nothing")
        return []

    kept = []
    for el in root.findall("keep"):
        try:
            idx = int(el.get("n", "0")) - 1
        except ValueError:
            continue
        if 0 <= idx < len(items):
            kept.append(items[idx])
    logger.info("feed triage kept %d of %d", len(kept), len(items))
    return kept[:3]


def record_harvest(conn: sqlite3.Connection, offered: list[FeedItem],
                   menu: list[FeedItem]) -> None:
    """Write the menu down, not just the meal (E1.0).

    Before this, the store recorded what was read and never what was offered,
    so "is the reading narrow because the world is narrow, or because the
    filter is?" could only be argued from the absence of reads. `was_read` is
    set later, by harvest, for the items extraction actually kept.
    """
    on_menu = {id(i) for i in menu}
    now = time.time()
    conn.executemany(
        "INSERT INTO harvest_log (ts, feed, category, title, url, on_menu)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [(now, i.feed.name, i.feed.category or "", i.title[:300], i.url or "",
          1 if id(i) in on_menu else 0) for i in offered])
    conn.commit()


# ── the harvest ──────────────────────────────────────────────────────────

def harvest(client, conn: sqlite3.Connection, feeds_path: Path, *,
            embedder=None, fetcher=None, log_path: Path | None = None,
            now: float | None = None) -> FeedHarvest:
    """Poll, shortlist, triage, read. Returns what was kept.

    The budget gate comes FIRST and covers everything: if the being has not
    earned its reading, no feed is polled at all. S2 §9.1's remedy is to
    pause ingest, and pausing after the HTTP has happened would pause the
    wrong half.
    """
    from newz.world.extract import extract_claims
    from newz.world.research import budget_permits_ingest
    from newz.world.sources import Fetcher

    out = FeedHarvest()
    permitted, why = budget_permits_ingest(log_path)
    if not permitted:
        out.skipped_reason = why
        logger.info("feeds: %s", why)
        return out

    fetcher = fetcher or Fetcher()
    feeds = load_feeds(feeds_path)
    candidates: list[FeedItem] = []
    for feed in due_feeds(conn, feeds, now=now):
        out.polled += 1
        try:
            items = parse_feed(fetcher.get(feed.url), feed)
            fresh = new_items(conn, feed, items)
            candidates.extend(fresh)
            mark_polled(conn, feed, items)
        except Exception as e:  # noqa: BLE001
            # One bad feed costs that feed, never the harvest. The failure is
            # counted on the row so a source that is permanently gone becomes
            # visible in the source review rather than silently retried.
            out.failures.append(f"{feed.name}: {e}")
            mark_polled(conn, feed, [], error=str(e)[:200])
            logger.warning("feed %s failed: %s", feed.name, e)

    out.offered = len(candidates)
    if not candidates:
        return out

    menu = build_menu(conn, candidates)
    out.shortlisted = len(menu)
    record_harvest(conn, candidates, menu)
    kept = triage(client, conn, menu)

    from newz.world.diet import over_share, record_read

    for item in kept:
        source = f"{item.feed.name}:{item.url}"
        if over_share(conn, item.url or item.feed.url):
            record_read(conn, source=source, query=None, concern_id=None,
                        claims_kept=0, quarantined=0, skipped="share_cap")
            continue
        extraction = extract_claims(client, item.text, source=source)
        record_read(conn, source=source, query=None, concern_id=None,
                    claims_kept=len(extraction.claims),
                    quarantined=extraction.quarantined)
        if not extraction.claims:
            continue
        out.kept.append(item)
        conn.execute("UPDATE harvest_log SET was_read=1 WHERE url=? AND url<>''",
                     (item.url,))
        # What was read becomes experience, with the outlet as provenance —
        # the same path research uses, so sleep and retrieval see feed
        # reading exactly as they see any other reading (INV-030).
        from newz.store.episodes import write_episode

        write_episode(
            conn, kind="reading", provenance=f"world:{item.feed.name}",
            summary=(f"I read {item.title[:120]} ({item.feed.name}), which "
                     f"came in on its own. It asserts: "
                     + "; ".join(t for t, _ in extraction.claims[:4])),
            content={"title": item.title, "url": item.url,
                     "feed": item.feed.name, "category": item.feed.category,
                     "unprompted": True,
                     "claims": [t for t, _ in extraction.claims]},
            source_ref=item.url)

        # The curiosity opener (S2 §8.1). Without this the world arrives, is
        # triaged, extracted and stored — and stops. Feeds were justified as
        # how the being encounters what it did not know to ask, and until
        # 2026-08-14 the asking had no door: 0 concerns opened by v2, ever,
        # while it re-ground the same four imported questions into
        # restatements. Almost never fires, and its failure costs the read
        # nothing.
        try:
            from newz.concerns.opener import open_from_reading
            from newz.concerns.store import create_concern

            findings = "\n".join(f"- {t}" for t, _ in extraction.claims)
            proposal = open_from_reading(conn, client, findings=findings,
                                         source_ref=item.url)
            if proposal.accepted:
                cid = create_concern(conn, proposal.concern)
                out.opened.append(proposal.concern.statement)
                logger.info("opened concern %d from reading: %s",
                            cid, proposal.concern.statement[:90])
            else:
                logger.debug("reading opener: %s", proposal.reason)
        except Exception:  # noqa: BLE001
            logger.exception("reading opener failed (the read is safe)")
    logger.info("feeds: %s", out.render())
    return out
