"""Diet diversity by construction (S2 §13) — per-outlet share caps.

v1's end state was 56% of all reading from two outlets. That is not merely
lopsided sourcing; S2 §13 names it a material viewpoint-shaping influence,
which makes the cap a viewpoint-non-prescription mechanism rather than
hygiene. TRUE_NORTH §8 asks that shaping influences be traceable and open to
challenge; a share cap makes one of them bounded as well.

The cap applies to what is actually READ, not what is found — reading is
where the influence enters. It is a soft cap: an outlet over its share is
deprioritised, not banned, because a hard ban would let the cap silence the
only source that can answer a question. The being reads something else if
something else will do, and records when the cap bound.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# S2 §13 target: no outlet above this share of ingested items over a month.
MAX_OUTLET_SHARE = 0.10
WINDOW_DAYS = 30
# Below this many reads in the window the share is meaningless — three items
# from one outlet is 100% of three, which is not a concentration problem.
MIN_ITEMS_FOR_CAP = 20
# Twice a fair share. S2 §13's flat 10% was written for a 61-feed diet; with
# the five sovereign adapters an even split is 20% each, so a flat cap would
# fire on every outlet at once and block the diet entirely (caught by test,
# 2026-08-11). The effective threshold is therefore the LOOSER of the two:
# a dominance test that means the same thing at any diet size — with 5
# outlets nothing is capped below 40%, with 20 outlets the 10% target binds,
# and v1's 56%-from-two-outlets would be caught under either.
FAIR_SHARE_MULTIPLE = 2.0


def effective_cap(n_outlets: int) -> float:
    if n_outlets <= 0:
        return 1.0
    return max(MAX_OUTLET_SHARE, FAIR_SHARE_MULTIPLE / n_outlets)


def outlet_of(source: str) -> str:
    """The share-cap unit.

    Adapter results arrive as 'arxiv:https://...' so the adapter is the
    outlet; feed items arrive as URLs, where the registrable host is the
    outlet — which is what makes three Bloomberg feeds count as one outlet
    rather than three (REVIEW.md D4).
    """
    if ":" in source and not source.startswith(("http://", "https://")):
        return source.split(":", 1)[0].strip().lower()
    host = (urlparse(source).hostname or source or "unknown").lower()
    host = host.removeprefix("www.")
    parts = host.split(".")
    if len(parts) > 2 and parts[-2] in ("co", "com", "org", "net", "ac", "gov"):
        return ".".join(parts[-3:])          # bbc.co.uk
    return ".".join(parts[-2:]) if len(parts) > 1 else host


def shares(conn: sqlite3.Connection, *, window_days: int = WINDOW_DAYS) -> dict[str, float]:
    """Share of the diet by outlet, counted in DISTINCT sources.

    R2, 2026-08-14: this counted rows. Reading the same page twice is not two
    items of diet, and before R1 the research path re-fetched the same urls
    every cycle — 24 non-skipped reads of which 12 were duplicates. That drove
    openalex to 33% and wikipedia to 29% against an effective cap of 22%, so
    both were refused, and the concern that had triggered the read got nothing
    and restated its previous conclusion. Counting distinct sources, the same
    corpus is 12 reads — BELOW MIN_ITEMS_FOR_CAP, where the cap correctly does
    not fire at all.

    The cap's parameters were never wrong. Its input was.
    """
    since = time.time() - window_days * 86400
    rows = conn.execute(
        "SELECT outlet, COUNT(DISTINCT source) n FROM ingest_log"
        " WHERE ts > ? AND skipped IS NULL GROUP BY outlet", (since,)).fetchall()
    total = sum(r["n"] for r in rows)
    if not total:
        return {}
    return {r["outlet"]: r["n"] / total for r in rows}


def over_share(conn: sqlite3.Connection, outlet: str, *,
               window_days: int = WINDOW_DAYS) -> bool:
    # Distinct sources throughout, for the reason in shares(): a re-read is
    # not a second item of diet, and counting it as one let duplicates
    # manufacture a concentration that then blocked real reading.
    since = time.time() - window_days * 86400
    total = conn.execute(
        "SELECT COUNT(DISTINCT source) FROM ingest_log"
        " WHERE ts > ? AND skipped IS NULL", (since,)).fetchone()[0]
    if total < MIN_ITEMS_FOR_CAP:
        return False
    n_outlets = conn.execute(
        "SELECT COUNT(DISTINCT outlet) FROM ingest_log"
        " WHERE ts > ? AND skipped IS NULL", (since,)).fetchone()[0]
    n = conn.execute(
        "SELECT COUNT(DISTINCT source) FROM ingest_log WHERE ts > ?"
        " AND skipped IS NULL AND outlet = ?", (since, outlet)).fetchone()[0]
    return (n / total) > effective_cap(n_outlets)


def record_read(conn: sqlite3.Connection, *, source: str, query: str | None,
                concern_id: int | None, claims_kept: int, quarantined: int,
                skipped: str | None = None, depth: str = "abstract",
                chunks: int = 1) -> None:
    """One read, recorded. `depth` and `chunks` say how deeply (0019).

    Without them "the retrieval slice contains only the headline" — which the
    being wrote into its own gap record eight times per concern — could not be
    confirmed from the store, and the per-read price of full text could not be
    measured against the §9.1 diet.
    """
    conn.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined, skipped, depth, chunks)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.time(), outlet_of(source), source, query, concern_id,
         claims_kept, quarantined, skipped, depth, chunks))
    conn.commit()


def apply_share_caps(conn: sqlite3.Connection, results, *, source_of) -> tuple[list, list]:
    """Split results into (readable, deprioritised-by-cap).

    Order is preserved so the caller still reads the most relevant of what
    remains, rather than the cap silently reordering by outlet.

    **The cap never returns nothing.** S2 §13 specifies a *target* — "no
    outlet >10% of ingested items over a rolling month" — and puts the
    diversity decision at source-add/remove time, not at fetch time.
    TRUE_NORTH §8 asks that shaping influences be *exposed*, and says in the
    same breath "do not manufacture balance after the fact". A rule that
    refuses the only source able to answer a question is manufacturing
    balance, and it produced exactly that on 2026-08-14: concern 102 reached
    for the world seven times overnight and touched nothing, concern 59 once
    and touched nothing.

    So when every candidate is over-cap, the best one is read anyway. The
    pressure survives — any under-represented alternative still wins outright
    — but the null outcome is gone.

    Deliberately ONE, not all of them. Measured the same day: 29 capped reads
    at ~2,600 ingest tokens each is ~76,000 tokens, which would take ingest
    from 96,366 to ~172,000 against earning of 96,089 and put the §9.1 diet
    into permanent breach. A diet breach stops ALL reading and then the
    state-driven skip turns that into four-hour silences, so removing the cap
    outright buys one busy afternoon and a much quieter week.
    """
    keep, capped = [], []
    for r in results:
        if over_share(conn, outlet_of(source_of(r))):
            capped.append(r)
        else:
            keep.append(r)
    if capped and not keep:
        promoted = capped.pop(0)
        logger.info("share cap: every candidate is over-cap — reading the best "
                    "one anyway (%s) rather than returning nothing",
                    outlet_of(source_of(promoted)))
        keep.append(promoted)
    if capped:
        logger.info("share cap: deprioritised %d result(s) from over-represented "
                    "outlets", len(capped))
    return keep, capped


# ── did the reading change anything? (TRUE_NORTH §4.3) ───────────────────


@dataclass
class CitationReport:
    """Whether reading produced justified change, or merely happened."""

    read: int = 0                       # distinct sources actually read
    cited: int = 0                      # …ever cited by an accepted advance
    window_days: float = 0.0
    uncited: list[str] = field(default_factory=list)

    @property
    def rate(self) -> float:
        return self.cited / self.read if self.read else 0.0

    def render(self) -> str:
        if not self.read:
            return "nothing read in the window"
        return (f"{self.cited}/{self.read} sources ever cited "
                f"({self.rate:.1%}) over {self.window_days:.0f}d")


def citation_rate(conn: sqlite3.Connection, *,
                  window_days: float = WINDOW_DAYS) -> CitationReport:
    """Of what the being read, how much did it ever use?

    TRUE_NORTH §4.3: *"Development matters more than activity. More reading,
    output, memory, or uptime does not matter unless experience produces
    justified change."* §10 names "activity, memory growth, or output
    volume" among the things that will not be mistaken for success.

    So the measure of a diet is not how much came in. v1's damning number
    was never its 84,793 stored claims — it was that **0.066% were ever
    cited**. That figure was uncomputable in v2 until C1 (2026-08-14) let an
    advance cite what it had read; before then the evidence check looked in
    a set that structurally could not contain any source.

    A source counts as cited when an ACCEPTED advance names it — by the
    `src-N` label the dossier renders, or by its url, since a model will use
    either. Setbacks do not count: an advance that was rejected did not
    change anything.

    This is the falsification condition for R3 (full-text reading). If the
    rate stays near zero after a week of deep reading, depth was not the
    constraint and R3 should be reverted rather than tuned — the same
    discipline as the closure rule, where an unsettled closed concern
    refutes C3 before it is built.
    """
    import json as _json

    since = time.time() - window_days * 86400
    sources = conn.execute(
        "SELECT id, source FROM ingest_log"
        " WHERE ts > ? AND skipped IS NULL", (since,)).fetchall()

    cited_refs: set[str] = set()
    for (blob,) in conn.execute(
        "SELECT evidence_json FROM concern_advances WHERE ts > ?", (since,)
    ):
        try:
            cited_refs.update(str(r) for r in _json.loads(blob or "[]"))
        except ValueError:
            continue

    report = CitationReport(window_days=window_days)
    seen: set[str] = set()
    for row in sources:
        src = row["source"] or ""
        if src in seen:
            continue                     # distinct sources, per R2
        seen.add(src)
        report.read += 1
        url = src.split(":", 1)[1] if ":" in src else src
        if f"src-{row['id']}" in cited_refs or url in cited_refs:
            report.cited += 1
        else:
            report.uncited.append(src)
    return report
