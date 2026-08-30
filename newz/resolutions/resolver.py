"""The resolver pass (P3 epic E1.3) — the world answers.

A scheduled pass inside deliberation that takes claims whose date has arrived,
goes and looks, and records what the world said. It is the only place in the
system where something other than the being or the operator can say "no".

**It fails closed, in every sense INV-034 means it.** An unreadable source, a
search that finds nothing, a verdict that will not parse, or a quote the being
cannot produce from the material all leave the claim OPEN. Nothing here guesses,
and the reason is specific rather than decorative: a resolver that settles a
claim on a plausible-sounding summary would manufacture the one signal Phase 1
exists to produce, and S1-E would then be measuring the model's agreeableness
instead of the world's verdict.

**Rule 4, concretely.** The model is a reader here, never a judge of the being.
It is given material fetched from the world and asked one question: does this
material settle the claim, and where does it say so. The verdict is only
accepted if the quote it gives back occurs VERBATIM in what was fetched —
v1's Stanford CRU lesson, applied to being right instead of to opening
questions. A verdict the material does not contain is discarded and the claim
stays open.

**INV-012.** The web is reached only inside deliberation, so this runs there
and nowhere else — never in the ambient loop, never on a timer of its own.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import time
from dataclasses import dataclass

from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml
from newz.resolutions.model import Claim
from newz.resolutions.store import settle_claim
from newz.store.episodes import write_episode

logger = logging.getLogger(__name__)

DAY = 86400.0
# One per cycle. The pass competes with deliberation for the same §9.1 ingest
# budget, and a claim that waited a week can wait one more cycle; a burst that
# starved the thinking to settle a backlog would be the wrong trade.
CLAIMS_PER_CYCLE = 1
# A source that has not answered in a day will usually not answer in an hour.
RETRY_AFTER_HOURS = 20
# After this many honest failures the claim stops being retried. It stays OPEN
# and unsettled — not closed, not ambiguous — because nothing happened.
MAX_ATTEMPTS = 4

_SYSTEM = (
    "You are checking a claim against material fetched from the world. You "
    "report only what the material says, quoting it. You respond with XML "
    "only. Material that does not settle the claim is the ordinary case."
)

_TASK = """<task>
I committed to a claim, and named what would settle it. Below is what was
fetched from the world today. Does this material settle the claim — either way?

Answer `no` unless the material actually says. Not settling is the ordinary
outcome: sources are slow, partial, and often about something adjacent. A
claim left open costs nothing; a claim settled on material that did not say
so destroys the only record of my being wrong that I have.

You are not judging whether the claim is reasonable, or whether I argued it
well. Only whether this material shows what happened.

Output ONLY:

<verdict>
  <settled>yes|no</settled>
  <outcome>held|contradicted</outcome>
  <quote>a VERBATIM phrase from the material below that shows it</quote>
  <source>the url or source name the quote came from</source>
  <why_not>if not settled: what the material was missing</why_not>
</verdict>

`held` means the world showed what I claimed would be observed.
`contradicted` means the world showed otherwise. If the material is about the
right subject but does not answer, that is `no` — say what was missing.

The quote must be copied EXACTLY from the material. If you cannot quote the
words that settle it, the material does not settle it and the answer is no.
</task>"""


@dataclass
class ResolveOutcome:
    claim_id: int
    settled: bool = False
    outcome: str | None = None          # held | contradicted
    failure: str | None = None          # why it is still open
    source: str | None = None


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def workable_claims(conn: sqlite3.Connection, *, now: float | None = None,
                    limit: int = CLAIMS_PER_CYCLE) -> list[Claim]:
    """Due claims that are worth another attempt.

    Not the same as `due_claims`: this excludes what was tried recently and
    what has exhausted its attempts. Those are still open and still visible —
    they are simply not worth spending the diet on again this cycle.
    """
    now = now or time.time()
    rows = conn.execute(
        "SELECT id, opened_at, claim, resolution_condition, resolver, due_at,"
        " provenance, status, outcome, settled_at, settled_by, settled_note"
        " FROM resolutions WHERE status='open' AND due_at <= ?"
        " AND attempts < ? AND (last_attempt_at IS NULL OR last_attempt_at < ?)"
        " ORDER BY due_at LIMIT ?",
        (now, MAX_ATTEMPTS, now - RETRY_AFTER_HOURS * 3600, limit)).fetchall()
    return [Claim(
        id=r["id"], claim=r["claim"],
        resolution_condition=r["resolution_condition"], resolver=r["resolver"],
        due_at=r["due_at"], provenance=r["provenance"], opened_at=r["opened_at"],
        status=r["status"], outcome=r["outcome"], settled_at=r["settled_at"],
        settled_by=r["settled_by"], settled_note=r["settled_note"]) for r in rows]


def _book_attempt(conn: sqlite3.Connection, claim_id: int,
                  now: float | None = None) -> None:
    """R-18's discipline: booked BEFORE any spending, so failure is never free
    and a claim whose source never answers cannot be retried without limit."""
    conn.execute(
        "UPDATE resolutions SET attempts = attempts + 1, last_attempt_at = ?"
        " WHERE id = ?", (now or time.time(), claim_id))
    conn.commit()


def _record_failure(conn: sqlite3.Connection, claim_id: int, why: str) -> None:
    conn.execute("UPDATE resolutions SET last_failure = ? WHERE id = ?",
                 (why[:400], claim_id))
    conn.commit()
    logger.info("claim %d not settled: %s", claim_id, why[:120])


def _resolution_adapters(conn: sqlite3.Connection, adapters):
    """The harvest first, then the ordinary set (E1.8).

    The being subscribes to 61 feeds and `default_adapters()` indexes none of
    them, so before this the one mechanism that can tell the being it was
    wrong could not see the documents its own feeds had already delivered.
    Measured 2026-08-28: claim 22 names *"Federal Open Market Committee (FOMC)
    Statement or Meeting Minutes"* as its resolver, and those minutes were in
    `harvest_log` from 2026-08-19, offered and unread, while the resolution
    pass returned Wikipedia's article about the release.

    **First, because order is what it changes.** `research()` walks adapters
    in order and dedupes by url, so putting the harvest ahead means the
    being's own subscribed source is the one that survives when two adapters
    return the same document. Nothing is refused by being later; everything
    still passes the relevance floor, triage, the share caps and INV-047.

    `adapters` given explicitly is honoured untouched — the probes and the
    tests pass stubs, and a caller that named its sources meant them.
    """
    if adapters is not None:
        return adapters
    from newz.world.harvest import HarvestAdapter
    from newz.world.sources import default_adapters

    ordinary = default_adapters()
    fetcher = next((getattr(a, "_f", None) for a in ordinary
                    if getattr(a, "_f", None) is not None), None)
    return [HarvestAdapter(conn, fetcher), *ordinary]


def resolve_claim(conn: sqlite3.Connection, client: LLMClient, claim: Claim, *,
                  log_path, adapters=None, embedder=None,
                  now: float | None = None) -> ResolveOutcome:
    """Go and look, once. Returns what happened; the claim is only ever
    settled by material that says so."""
    from newz.world.research import record_gap, research

    now = now or time.time()
    out = ResolveOutcome(claim_id=claim.id)
    _book_attempt(conn, claim.id, now)

    # The resolver names the source; the claim names what to look for. Both
    # go into the query, because searching for the claim alone finds
    # commentary and searching for the source alone finds its front page.
    query = f"{claim.resolver}: {claim.claim}"
    # **`as_experience=False`**: this pass records what it read and writes no
    # reading episodes. The one episode a resolution produces is the
    # `resolution` episode below, which is what E1.3 says and what reusing
    # `research()` had quietly stopped being true — 52 corpus entries from ten
    # attempts, none of them something the being chose to read.
    found = research(client, query, log_path=log_path,
                     adapters=_resolution_adapters(conn, adapters),
                     embedder=embedder, conn=conn, concern_id=None,
                     as_experience=False)

    if found.paused:
        # Not a failure of the claim — the diet said no. Give back the
        # attempt: the being should not be charged for its own budget.
        conn.execute("UPDATE resolutions SET attempts = attempts - 1 WHERE id=?",
                     (claim.id,))
        conn.commit()
        out.failure = f"ingest paused: {found.paused}"
        return out

    material = "\n".join(f"- {t}" for t, _ in found.claims)
    if not material:
        out.failure = "nothing came back from the source"
        _record_failure(conn, claim.id, out.failure)
        # The being reached for the world and the world was not there. That is
        # what source_gaps is for, and it is how §9.1 learns which sources to
        # add — a resolver nobody can reach is a curation problem.
        record_gap(conn, concern_id=None, query=query,
                   gap=f"claim {claim.id}: {found.gap or 'no usable material'}",
                   outcome=found)
        return out

    body = (f"<claim>{claim.claim}</claim>\n"
            f"<settles_when>{claim.resolution_condition}</settles_when>\n"
            f"<resolver>{claim.resolver}</resolver>\n"
            f"<material>\n{material}\n</material>\n"
            f"{found.render()}")
    try:
        result = client.complete("DEEP", _SYSTEM, f"{_TASK}\n\n{body}",
                                 max_tokens=700, temperature=0.2,
                                 function="claim_resolver")
        root = extract_xml(result.text, "verdict")
    except (XMLExtractionError, Exception) as e:  # noqa: BLE001
        out.failure = f"verdict unreadable: {e}"
        _record_failure(conn, claim.id, out.failure)
        return out

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    if text_of("settled").lower() != "yes":
        out.failure = text_of("why_not") or "the material did not settle it"
        _record_failure(conn, claim.id, out.failure)
        return out

    outcome = text_of("outcome").lower()
    if outcome not in ("held", "contradicted"):
        out.failure = f"verdict named no outcome ({outcome!r})"
        _record_failure(conn, claim.id, out.failure)
        return out

    quote = text_of("quote")
    if not quote or _normalise(quote) not in _normalise(material):
        # The Stanford CRU lesson, applied to being right. A verdict the
        # material does not contain is the model's opinion wearing the
        # world's clothes, and Rule 4 forbids exactly that.
        out.failure = "verdict quote is not in the material (unsupported)"
        _record_failure(conn, claim.id, out.failure)
        return out

    source = text_of("source") or claim.resolver
    settle_claim(conn, claim.id, outcome=outcome, settled_by=source,
                 note=quote[:500], now=now)
    out.settled, out.outcome, out.source = True, outcome, source

    # The one episode this phase writes. A claim resolved against the being is
    # the world contradicting it — the single thing P3 says the whole plan
    # turns on — and sleep must see it whichever way it went.
    write_episode(
        conn, kind="resolution", provenance="world",
        summary=(f"The world {'contradicted' if outcome == 'contradicted' else 'confirmed'}"
                 f" a claim I made: \"{claim.claim}\" — {claim.resolver} showed:"
                 f" {quote[:200]}"),
        content={"claim_id": claim.id, "claim": claim.claim, "outcome": outcome,
                 "resolver": claim.resolver, "source": source, "quote": quote,
                 "provenance": claim.provenance},
        source_ref=source)
    logger.info("claim %d %s by %s", claim.id, outcome, source[:80])
    return out


def resolve_due_claims(conn: sqlite3.Connection, client: LLMClient, *,
                       log_path, adapters=None, embedder=None,
                       now: float | None = None) -> list[ResolveOutcome]:
    """The pass. Called from deliberation, never from the ambient loop."""
    out: list[ResolveOutcome] = []
    for claim in workable_claims(conn, now=now):
        try:
            out.append(resolve_claim(conn, client, claim, log_path=log_path,
                                     adapters=adapters, embedder=embedder,
                                     now=now))
        except Exception:  # noqa: BLE001
            # A claim that blows up must not take the deliberation with it:
            # the attempt is already booked, so this cannot loop.
            logger.exception("resolving claim %d failed (the cycle continues)",
                             claim.id)
            _record_failure(conn, claim.id, "resolver crashed")
    return out
