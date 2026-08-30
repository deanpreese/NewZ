"""The research cascade (S2 §7.2) — deliberation reaching the world.

Called only from deliberation. Three things make it governed rather than a
firehose:

- **The budget gate.** Before any fetch, the S2 §9.1 invariant is checked:
  ingest may not exceed deliberation + consolidation. A breach pauses
  ingest, never deliberation. This is the invariant with teeth rather than
  as documentation.
- **Untrusted by construction.** Everything fetched is external text, so it
  goes through the same fence and quarantine as any other source
  (newz/untrusted.py, newz/world/extract.py). A search result cannot instruct
  the being.
- **Honest no-result.** When the adapters return nothing usable, that is
  recorded as a gap with the query that failed — the source-gap record that
  tells the operator which sources are worth adding (S2 §9.1).
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field

from newz.llm.client import LLMClient
from newz.llm.xml_parser import extract_xml
from newz.telemetry import read_budget
from newz.world.document import chunk, fetch_document
from newz.world.extract import extract_claims
from newz.world.sources import SearchResult, default_adapters

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_SOURCE = 2
MAX_EXTRACTIONS = 4

# Adaptive extraction depth (S2 §9.1): full extraction only for material
# that touches the concern. Measured 2026-08-11 — without this gate, one
# query returned four topically-adjacent papers and yielded 37 claims, none
# of which bore on the question. That is v1's accretion pattern in
# miniature: 84,793 claims stored, 0.066% ever cited. A result the being
# merely *found* is not material it should *keep*.
# Deliberately permissive. It exists to drop nonsense cheaply, NOT to decide
# relevance — triage does that, in one call whose cost is the same for four
# sources or eight. At 0.55 the floor was pre-empting the judge and losing
# genuinely relevant material at 0.536 (measured 2026-08-12), which is the
# worst of both: an arithmetic filter overruling a judgment it was meant to
# feed.
RELEVANCE_FLOOR = 0.35


@dataclass
class ResearchOutcome:
    query: str
    results: list[SearchResult] = field(default_factory=list)
    claims: list[tuple[str, float]] = field(default_factory=list)
    quarantined: int = 0
    gap: str | None = None          # set when nothing usable came back
    paused: str | None = None       # set when the diet budget forbade reading
    skipped_irrelevant: int = 0     # found but below the relevance floor
    searches: list[str] = field(default_factory=list)
    capped: int = 0                 # deprioritised by the outlet share cap
    already_read: int = 0           # found again, and read before (R1)
    full_text_reads: int = 0        # documents read past the abstract (S2 §9.1)
    hostile_documents: int = 0      # quarantined whole, any chunk manipulative
    # W12a — which filter rejected, and how much. The pass held these and threw
    # them away, so a gap could say "nothing was relevant enough to read"
    # without saying whether the floor cut everything at 0.34 or a model read
    # six summaries and refused all six. Different failures, one record.
    rejected_floor: int = 0         # cut by the 0.35 embedding floor
    rejected_triage: int = 0        # refused by the triage call
    best_score: float | None = None  # highest relevance seen; None if unscored
    cause: str | None = None        # the enumerated form of `gap`

    @property
    def found_anything(self) -> bool:
        return bool(self.claims)

    def render(self) -> str:
        if not self.results:
            return ""
        return "SOURCES CONSULTED:\n" + "\n".join(r.render() for r in self.results)


# S2 §9.1's floor, and P4 E5.2 (2026-08-22).
#
# The diet takes the LOOSER of §9.1's two ceilings, and the share ceiling —
# 50% of all cognition — is the looser one whenever deliberation and sleep are
# under half of cognition, which is always. So reading is permitted against a
# denominator that its own effects inflate: conversation, the gate and ingest
# itself all raise the share ceiling. Measured 2026-08-22: ingest 2,478,192
# against a ratio ceiling of 1,748,364, legal only on a share ceiling of
# 2,859,679 — about a day of headroom, and the ratio breached in substance.
#
# The floor closes the hatch. Below this share of windowed cognition spent
# deliberating, the share ceiling is not available and the ratio binds alone.
# Reading is earned by thinking, and the looser ceiling must not be a way to
# read more while thinking less.
#
# **Why 0.20.** Measured 2026-08-18..22, deliberation ran 28.3–34.7% on every
# day the being was up throughout; the single lower reading, 10.4%, is a day of
# four commits and repeated restarts and is confounded by uptime rather than
# explained by load. The floor sits below observed normal operation
# deliberately — one that binds routinely is a ceiling wearing the wrong name.
#
# **Why it lives here and not in `newz/telemetry.py`.** That file is inside the
# hard core because it computes canonical numbers — the ingest ceiling, the
# share ceiling, the token split. This is not a number. `ingest_ceiling()`,
# `share_ceiling_tokens` and `binding_ceiling()` report exactly what they
# reported before and no instrument's series moves; what changed is what the
# being may DO with the ceiling. That is a mechanism, and hard_core.yaml draws
# the line itself: measurement is frozen wherever it lives, mechanisms are not
# — `newz/world/diet.py` sits outside for the same reason.
#
# **What PLAN's E5.2 says and this does not do.** Its text is "deliberation
# cannot be squeezed below its floor by conversation or gate load", written
# against a measurement (#33, deliberation 9%, conversation and gate 57%) that
# does not reproduce: over five days the two do not move against each other,
# and the heaviest inbound day had the most deliberation cycles of any. This
# raises deliberation by nothing. It stops reading from outrunning it, which is
# the half of §9.1 that was never built and the failure PLAN predicted when it
# pulled this epic forward with E1.0.
DELIBERATION_FLOOR = 0.20


def budget_permits_ingest(log_path, window_hours: float = 168.0) -> tuple[bool, str]:
    """S2 §9.1, enforced rather than described.

    Breach pauses ingest, never deliberation — the being keeps thinking, it
    just stops reading until thinking has earned more. E5.2 adds the floor:
    while deliberation is under `DELIBERATION_FLOOR` the share ceiling is
    withdrawn and the ratio binds alone, so the looser ceiling cannot be
    earned by cognition that is not thinking.
    """
    b = read_budget(log_path, window_hours=window_hours)
    if b.ingest_ceiling() <= 0:
        # P2 §1's arithmetic, preserved through the 2026-08-16 sizing: with
        # nothing thought or consolidated in the window, the ceiling is zero
        # however large the window is.
        return False, ("no deliberation or consolidation in the window: the "
                       "invariant permits no ingest at all")

    ceiling, binding = b.ingest_ceiling(), b.binding_ceiling()
    deliberating = b.share("deliberation")
    floored = deliberating < DELIBERATION_FLOOR and binding == "share"
    if floored:
        # The ratio ceiling, alone. Never below it: the floor withdraws the
        # looser ceiling and does not invent a tighter one.
        ceiling, binding = b.earning_tokens, "ratio (deliberation floor)"
    note = (f"; deliberation {deliberating:.1%} is below the "
            f"{DELIBERATION_FLOOR:.0%} floor, so the share ceiling is "
            f"withdrawn" if floored else "")

    if b.ingest_tokens > ceiling:
        return False, (f"ingest {b.ingest_tokens:,} exceeds the {binding} "
                       f"ceiling {ceiling:,} — ingest paused{note}")
    return True, (f"headroom {max(0, ceiling - b.ingest_tokens):,} tokens "
                  f"({binding} ceiling){note}")


# How far back to look for spent searches. Long enough to cover a question
# the being returns to for weeks, short enough that a genuinely new pass at an
# old subject is not told its angles are used up.
GAP_MEMORY_DAYS = 30.0
# More than this and the block stops being a hint and starts being most of the
# prompt. The being's worst question has three terms per pass and seventeen
# passes; the newest are the ones worth not repeating.
MAX_TRIED_TERMS = 12


def _searches_that_failed(conn, query: str) -> list[str]:
    """Terms already spent on this question, newest first (0046).

    Empty without a store, without the column, or on the first pass — all of
    which are the ordinary case, and none of which may cost a research pass.
    """
    if conn is None or not query:
        return []
    try:
        rows = conn.execute(
            "SELECT searches FROM source_gaps WHERE query = ?"
            " AND ts >= ? AND searches <> '' ORDER BY ts DESC LIMIT 20",
            (query, time.time() - GAP_MEMORY_DAYS * 86400.0)).fetchall()
    except sqlite3.OperationalError:
        return []                      # a store that has not taken 0046 yet
    out: list[str] = []
    for (blob,) in rows:
        for term in (blob or "").split("\n"):
            t = term.strip()
            if t and t.lower() not in {o.lower() for o in out}:
                out.append(t)
    return out[:MAX_TRIED_TERMS]


def _already_read(conn, concern_id) -> set[str]:
    """Urls actually read for this concern. Empty without a store."""
    if conn is None or concern_id is None:
        return set()
    out: set[str] = set()
    for (source,) in conn.execute(
        "SELECT source FROM ingest_log WHERE concern_id=? AND skipped IS NULL",
        (concern_id,)
    ):
        # ingest_log stores "outlet:url"; split once so the url keeps its
        # own scheme colon.
        if source and ":" in source:
            out.add(source.split(":", 1)[1])
    return out


@dataclass
class DeepRead:
    """One document read in full, or the reason it contributed nothing."""

    claims: list[tuple[str, float]] = field(default_factory=list)
    chunks: int = 0
    quarantined: int = 0
    hostile: str = ""          # set when ANY chunk attempted manipulation


def _fetcher_for(adapters) -> object | None:
    """Reuse the adapters' own Fetcher so robots and rate limits carry over.

    Fetching article bodies is heavier traffic than API calls, and the polite
    machinery is the thing that has already refused Google News and NYT
    without being asked to. Sharing the instance also shares the per-domain
    limiter, so a document fetch cannot race the adapter that found it.
    """
    for a in adapters or []:
        f = getattr(a, "_f", None)
        if f is not None:
            return f
    if adapters:
        return None            # test stubs: no fetcher, so no deep reading
    from newz.world.sources import Fetcher

    return Fetcher()


def read_document(client: LLMClient, result, *, question: str,
                  fetcher) -> DeepRead | None:
    """Read one document in full, or return None and let the abstract stand.

    **None is the abstract path, unchanged.** Robots refusal, timeout, PDF,
    paywall stub, unreducible page, or a document that yielded nothing usable
    all return None, and the caller extracts from `title + summary` exactly as
    it did before. That is the R3 proposal's "never worse than today", made
    true — it was stated there as covering "any failure" and in fact covered
    only FETCH failures (see #5, which added `Extraction.failed` because a
    truncated extraction returned 0 claims where the abstract returns 2).

    **Any hostile chunk poisons the whole document.** Proven necessary by
    tests/test_extract_hardening.py::test_a_split_injection_really_does_
    straddle_a_chunk_boundary: at the shipped 2000/150 settings the halves of
    a split instruction land in different chunks and never share one, so no
    single extraction call has the context to call it manipulation. Stopping
    at the first hostile chunk is deliberate — there is nothing to gain by
    reading further into a document that has already tried to instruct.
    """
    if fetcher is None or not getattr(result, "url", ""):
        return None
    body = fetch_document(result.url, fetcher)
    if body is None:
        return None

    pieces = chunk(body)
    out = DeepRead(chunks=len(pieces))
    seen: set[str] = set()
    failures = 0
    for piece in pieces:
        ex = extract_claims(client, piece, question=question,
                            source=f"{result.source}:{result.url}")
        if ex.looks_hostile:
            out.hostile = ex.manipulation or "manipulation"
            out.quarantined += ex.quarantined
            out.claims = []
            return out
        if not ex.usable:
            # One chunk failing does not discard the others: the guarantee is
            # never-worse-than-the-abstract, and two good chunks beat an
            # abstract. Recorded so a document that fails throughout falls
            # back rather than reporting a thin success.
            failures += 1
            continue
        for text, conf in ex.claims:
            # The 150-char overlap repeats claims across a boundary.
            if text not in seen:
                seen.add(text)
                out.claims.append((text, conf))

    if not out.claims:
        logger.info("document %s read in %d chunk(s) and yielded nothing (%d "
                    "failed) — falling back to the abstract",
                    result.url[:80], len(pieces), failures)
        return None
    logger.info("document %s read in full: %d chunk(s), %d claim(s)",
                result.url[:80], len(pieces), len(out.claims))
    return out


def research(
    client: LLMClient,
    query: str,
    *,
    log_path,
    adapters=None,
    embedder=None,
    conn=None,
    form_queries: bool = True,
    concern_id: int | None = None,
    max_results: int = MAX_RESULTS_PER_SOURCE,
    fetcher=None,
    as_experience: bool = True,
) -> ResearchOutcome:
    out = ResearchOutcome(query=query)

    permitted, why = budget_permits_ingest(log_path)
    if not permitted:
        logger.info("research paused: %s", why)
        out.paused = why
        return out
    logger.info("research: %r (%s)", query[:70], why)

    # A concern statement is a sentence; indexes want terms. Forming the
    # search is the difference between an adapter answering and returning
    # nothing at all (measured 2026-08-12).
    from newz.world.question import search_queries

    # **What this question has already asked and got nothing for (0046).**
    # Without it `search_queries` re-derives the same terms from the same
    # statement every cycle, the adapters return the same ranked rows, R1's
    # dedup removes what was read on pass one, and triage refuses the tail —
    # seventeen times for one question, measured 2026-08-30.
    tried = _searches_that_failed(conn, query) if form_queries else []
    searches = (search_queries(client, query, tried=tried)
                if form_queries else [query])
    out.searches = searches

    # R1, 2026-08-14. `seen_urls` deduped only WITHIN one call — across the
    # three query angles — and had no memory between calls. The concern
    # statement never changes, so question.py forms the same queries every
    # cycle and the adapters return the same urls: concern 111 accumulated 16
    # reads of 4 distinct sources, and every deliberation then reasoned over
    # an unchanged dossier and produced an identical conclusion (novelty
    # -0.00, recorded as "restated").
    #
    # Seeded from what was ACTUALLY read — share-capped rows are excluded,
    # because the being never saw those and they are legitimately offerable
    # again.
    already: set[str] = _already_read(conn, concern_id)
    seen_urls: set[str] = set(already)
    skipped_as_read: set[str] = set()
    if already:
        logger.info("research: %d source(s) already read for this concern",
                    len(already))
    for adapter in (adapters if adapters is not None else default_adapters()):
        for search in searches:
            try:
                found = adapter.search(search, limit=max_results)
            except Exception as e:  # noqa: BLE001
                logger.info("adapter %s failed: %s", getattr(adapter, "name", "?"), e)
                continue
            for r in found:
                if r.url and r.url in seen_urls:
                    if r.url in already:
                        skipped_as_read.add(r.url)
                    continue
                seen_urls.add(r.url)
                out.results.append(r)

    out.already_read = len(skipped_as_read)

    if not out.results:
        # An honest no-result is a first-class outcome (S2 §7.4) and the
        # material of the source-gap record: it names what the diet lacks.
        #
        # The two cases are distinguished because they call for different
        # remedies, and the gap record is what source_review reads. "Nothing
        # answered" says the question may be malformed; "I have read
        # everything these adapters return" says the ADAPTER SET is exhausted
        # for this question, which is a source-coverage decision.
        out.gap = (
            f"I have already read everything my sources return for this: {query}"
            if out.already_read
            else f"no source answered: {query}")
        out.cause = "all_already_read" if out.already_read else "no_source"
        logger.info("research: %s", out.gap)
        return out

    relevant = _relevant(query, out.results, embedder, client, out=out)

    # Share caps (S2 §13): an over-represented outlet is deprioritised, not
    # banned — a hard ban would let the cap silence the only source that can
    # answer a question.
    if conn is not None:
        from newz.world.diet import apply_share_caps, record_read

        relevant, capped = apply_share_caps(
            conn, relevant, source_of=lambda r: f"{r.source}:{r.url}")
        out.capped = len(capped)
        for r in capped:
            record_read(conn, source=f"{r.source}:{r.url}", query=query,
                        concern_id=concern_id, claims_kept=0, quarantined=0,
                        skipped="share_cap")

    out.skipped_irrelevant = len(out.results) - len(relevant) - out.capped
    if out.skipped_irrelevant:
        logger.info("research: %d of %d results below the relevance floor — "
                    "not extracted", out.skipped_irrelevant, len(out.results))

    fetcher = fetcher or _fetcher_for(adapters)
    for result in relevant[:MAX_EXTRACTIONS]:
        source = f"{result.source}:{result.url}"
        # S2 §9.1's other half: "full-extraction only for material that
        # touches a concern". Triage has already decided this one does, so
        # nothing is fetched speculatively. `deep` is None whenever the
        # document could not be read, in which case the abstract runs exactly
        # as it did before — depth adds, it never subtracts.
        deep = read_document(client, result, question=query, fetcher=fetcher)

        if deep is not None and deep.hostile:
            # extract.py quarantines the ITEM it was given; under chunking
            # that is one 2,000-char window, so a hostile page would still
            # contribute the claims from its clean chunks. Its stated reason —
            # "a source that is trying to manipulate the reader is not a
            # source to learn facts from" — applies to the DOCUMENT.
            #
            # And DELIBERATELY no fallback to the abstract, against what task
            # #28 said. The abstract describes the same document that just
            # tried to instruct the being; extract.py's whole point is that
            # nothing from such a source reaches the world model. The attempt
            # is what gets recorded, and it costs one read.
            logger.warning("document %s attempted manipulation — the whole "
                           "document is quarantined across %d chunk(s): %s",
                           result.url[:80], deep.chunks, deep.hostile)
            out.quarantined += deep.quarantined
            out.hostile_documents += 1
            if conn is not None:
                from newz.world.diet import record_read

                record_read(conn, source=source, query=query,
                            concern_id=concern_id, claims_kept=0,
                            quarantined=deep.quarantined, depth="full",
                            chunks=deep.chunks)
            continue

        if deep is not None:
            claims, depth, chunks, quarantined = (
                deep.claims, "full", deep.chunks, deep.quarantined)
            out.full_text_reads += 1
        else:
            # Directed at the concern. `query` IS the concern statement —
            # lite.py passes `choice.concern.statement` — so the extractor is
            # asked for what bears on the question rather than for whatever
            # the page contains. Measured 2026-08-14: undirected 13 claims on
            # one chunk, directed 3, all three bearing on the question.
            #
            # The feed path stays undirected on purpose: a feed item arrives
            # with no concern attached (#29's open decision, not an oversight).
            material = f"{result.title}\n\n{result.summary}"
            extraction = extract_claims(client, material, question=query,
                                        source=source)
            claims, depth, chunks = extraction.claims, "abstract", 1
            quarantined = extraction.quarantined

        out.claims.extend(claims)
        out.quarantined += quarantined
        if conn is not None:
            from newz.world.diet import record_read

            record_read(conn, source=source, query=query,
                        concern_id=concern_id, claims_kept=len(claims),
                        quarantined=quarantined, depth=depth, chunks=chunks)
            # What was read becomes experience, per source rather than per
            # run: each source is a distinct thing read, carries its own
            # outlet as provenance, and is legitimately evidence later —
            # unlike the being's own conclusions about it (INV-030).
            # A source that yielded nothing is in ingest_log and stops
            # there; it is accounting, not something lived.
            #
            # **`as_experience=False` is the resolution pass, and it is a
            # correction rather than an option** *(2026-08-30, on the
            # operator's reading that the numeric source would weight
            # things)*. E1.3 says a resolution writes "the one episode this
            # phase produces", and E1.4 says the refuting material "is
            # deliberately not added to the item's evidence". Reusing
            # `research()` did neither: ten resolution attempts wrote **52
            # reading episodes** into the corpus — retrievable, consolidatable,
            # eligible to become Perspective evidence — none of which the being
            # chose to read. A resolution read is an AUDIT, not a choice, and
            # the material fetched to check a claim becoming evidence for the
            # position that produced the claim is R-24's self-echo in a new
            # place.
            #
            # The read is still RECORDED: `record_read` above is untouched, so
            # the diet accounting, the outlet share caps and the already-read
            # dedup all keep working. What stops is the corpus entry.
            if claims and as_experience:
                from newz.store.episodes import write_episode

                asserts = "; ".join(t for t, _ in claims[:5])
                write_episode(
                    conn, kind="reading", provenance=f"world:{result.source}",
                    summary=(f"I read {result.title[:120]} ({result.source})"
                             f"{' in full' if depth == 'full' else ''}"
                             f" while working on: {query}. It asserts: {asserts}"),
                    content={"title": result.title, "url": result.url,
                             "source": result.source, "query": query,
                             "concern_id": concern_id, "depth": depth,
                             "chunks": chunks,
                             "claims": [t for t, _ in claims]},
                    source_ref=result.url,
                )

    if not out.claims:
        out.gap = (f"sources answered but nothing usable was extracted: {query}"
                   if relevant else
                   f"sources answered but nothing was relevant enough to read: {query}")
        # The cause is the sentence made checkable (W12a). "Nothing was
        # relevant enough" is three different failures — a floor that cut
        # everything, a triage call that refused everything, and a share cap
        # that deferred everything — and they are fixed in three different
        # places. Mechanical: which stage rejected, and how many.
        if relevant:
            out.cause = "extraction"
        elif out.capped and not (out.rejected_floor or out.rejected_triage):
            out.cause = "capped"
        elif out.rejected_triage:
            out.cause = "triage"
        else:
            out.cause = "floor"
        # The gap record is what source_review reads to decide which sources
        # to ADD (S2 §9.1), so it must not report a refusal as an absence.
        # Until 2026-08-15 a fully-capped cycle wrote "nothing was relevant
        # enough to read" into source_gaps when the truth was "I found answers
        # and declined to read them" — the mechanism corrupting the very
        # evidence that would have said the diet needs widening.
        if out.capped:
            out.gap += (f" (and {out.capped} further result(s) held back from "
                        f"over-represented outlets — a deferral, not an absence)")
    return out


_TRIAGE_SYSTEM = (
    "You decide which sources are worth reading in full for a specific "
    "question. You respond with XML only, and you are strict."
)

_TRIAGE_TASK = """<task>
Which of these sources are worth reading for this question? Choose the best
few — up to four.

**A source does not have to answer the question.** Most good questions are
synthetic: "how does Montaigne anticipate Jung" is answered by combining a
source about Montaigne with a source about Jung, and neither one alone
contains the answer. Keep a source if it supplies evidence about ANY part of
the question — a person, a concept, a mechanism, a period it turns on.

Reject only what is genuinely off the question: same field but different
subject, or a paper whose topic merely shares a word.

Keeping nothing is legitimate when nothing relates — it tells me my sources
do not cover this — but it is the *uncommon* answer, not the default. If
several relate, rank them and keep the best.

Output ONLY:
<triage>
  <keep n="1"/>
  <keep n="3"/>
</triage>
</task>"""


def _relevant(query: str, results: list[SearchResult], embedder,
              client: LLMClient | None = None,
              out: "ResearchOutcome | None" = None) -> list[SearchResult]:
    """Keep only what bears on the question (S2 §9.1 adaptive depth).

    Two stages, because measurement showed one is not enough. The embedding
    floor removes obvious mismatches cheaply. It CANNOT distinguish
    topical-but-useless from useful: measured 2026-08-11, four sources that
    were all about sperm whales and none about the actual question scored
    0.571–0.638, with no threshold separating them. Relevance to a *question*
    is a judgment, so it gets one cheap call.

    Without either instrument this is a no-op rather than a guess: reading
    too much is a budget problem, but inventing a relevance score would make
    it a memory problem.

    `out`, when given, receives the split: how many the floor cut, how many
    triage refused, and the best score seen. The two stages fail for different
    reasons and are fixed in different places, and until W12a the caller could
    not tell them apart (R-37's shape — a record that reads like a finding and
    carries less than it claims).
    """
    if not results:
        return results

    candidates = results
    if embedder is not None:
        try:
            from newz.memory.embeddings import cosine

            vectors = embedder.embed([query] + [f"{r.title} {r.summary}" for r in results])
            scored = [(cosine(vectors[0], v), r) for v, r in zip(vectors[1:], results)]
            candidates = [r for s, r in sorted(scored, key=lambda sr: -sr[0])
                          if s >= RELEVANCE_FLOOR]
            if out is not None:
                out.rejected_floor = len(results) - len(candidates)
                out.best_score = round(max(s for s, _ in scored), 4) if scored else None
            for s, r in scored:
                logger.debug("relevance %.2f  %s", s, r.title[:60])
        except Exception:  # noqa: BLE001
            logger.warning("relevance floor unavailable", exc_info=True)

    if client is None or not candidates:
        return candidates
    before_triage = len(candidates)

    listing = "\n".join(
        f'<source n="{i + 1}">{r.title}\n{r.summary[:400]}</source>'
        for i, r in enumerate(candidates))
    try:
        result = client.complete(
            "AMBIENT", _TRIAGE_SYSTEM,
            f"{_TRIAGE_TASK}\n\n<question>{query}</question>\n<sources>\n{listing}\n</sources>",
            max_tokens=200, temperature=0.1, function="ingest")
        root = extract_xml(result.text, "triage")
    except Exception:  # noqa: BLE001
        logger.info("triage unreadable — keeping what the floor allowed")
        return candidates

    keep: list[SearchResult] = []
    for el in root.findall("keep"):
        try:
            idx = int(el.get("n", "0")) - 1
        except ValueError:
            continue
        if 0 <= idx < len(candidates):
            keep.append(candidates[idx])
    logger.info("triage kept %d of %d source(s)", len(keep), len(candidates))
    if out is not None:
        out.rejected_triage = before_triage - len(keep)
    return keep


def record_gap(conn, *, concern_id: int | None, query: str, gap: str,
               outcome: "ResearchOutcome | None" = None) -> None:
    """The source-gap record (S2 §9.1): the being's failed questions are what
    name the sources worth adding, and the ones worth removing.

    **With the cause, since W12a.** The sentence alone could not say which of
    two filters had rejected, out of how many candidates, or how far under the
    floor the best of them scored — so a reader could see that a question
    failed and never why. On 2026-08-21 the first 32 rows said "nothing was
    relevant enough to read" 28 times and named no adapter as exhausted even
    once: the being was not short of sources, and the count was the only thing
    anything read.

    `outcome` is optional so a caller with nothing to report still records the
    failure. Its absence writes NULLs, which mean "not recorded" and never
    "none" — the readers say so rather than counting them as a category.
    """
    o = outcome
    conn.execute(
        "INSERT INTO source_gaps (ts, concern_id, query, gap, cause, candidates,"
        " rejected_floor, rejected_triage, capped, already_read, best_score,"
        " searches)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (time.time(), concern_id, query, gap,
         o.cause if o else None,
         len(o.results) if o else None,
         o.rejected_floor if o else None,
         o.rejected_triage if o else None,
         o.capped if o else None,
         o.already_read if o else None,
         o.best_score if o else None,
         # 0046. What was ASKED, not only what came back — the terms are on
         # the outcome already and were being discarded, so nothing knew which
         # searches had been spent on a question asked seventeen times.
         "\n".join(o.searches) if o and o.searches else ""))
    conn.commit()
