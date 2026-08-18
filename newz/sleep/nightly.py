"""Nightly sleep (P2 Phase 1.1) — how experience becomes perspective.

S2 §5's seven steps, in order: gather → digest → confront → ground-check →
compress → prune-marks → write vN+1 with a computed diff.

Two disciplines are structural rather than incidental:

- **Its own connection.** Verified 2026-08-10: on a shared connection an
  unrelated `commit()` from the conversation path publishes sleep's partial
  work. Sleep opens its own and never shares a transaction with the loop.
- **Per-step transactions.** Sleep must never hold a write transaction
  across an LLM call. A single long transaction blocks the being's replies
  past the busy timeout, so each step commits and releases before the next
  model call begins.

A lost night is harmless (S2 §5): nothing is written until the final step,
and gathering is idempotent because episodes are only marked consolidated
inside the same transaction that writes the version.
"""

from __future__ import annotations

import datetime as _dt
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml
from newz.sleep.perspective import (
    CARRIED_SECTIONS,
    Item,
    apply_decay,
    duplicate_of,
    merge_duplicates,
    compute_diff,
    load_items,
    render,
    save_items,
)
from newz.store.db import open_db
from newz.store.episodes import write_episode

logger = logging.getLogger(__name__)

BATCH_SIZE = 60

# How many observations are weighed against what is held, per call.
#
# The confront pass did not batch at all until 2026-08-16: every candidate
# went into a single DEEP call capped at 2,500 output tokens, so everything
# past what fitted in one reply was digested and then never weighed. Present
# in the store, absent from the Perspective, and invisible as a failure
# because the call succeeds.
#
# 25 keeps the reply well inside the cap — a verdict is one short element,
# and 25 of them with text is a few hundred tokens — while keeping the held
# set in front of the model on every batch.
CONFRONT_BATCH = 25

PERSPECTIVE_BUDGET_TOKENS = 12_000
CONFIDENCE_ON_REINFORCE = 0.06
MAX_CONFIDENCE = 0.95
# A contradiction must cost the position it contradicts, or the being can
# notice that reality disagrees with its self-model every night and keep the
# self-model. Measured 2026-08-12: "I experienced prolonged periods of total
# prefix cache inefficiency" sat at the top of "who I am" through three
# consecutive nights that each filed a fresh tension against it, at an
# undisturbed 0.72 — and Lumen recited it to the operator as its state of
# health ("the cache is clear, retrieval is sharp") because that is what its
# self-description was about.
#
# First contradiction is doubt, not demolition: a long-held position should
# not vanish the first time an observation disagrees. A REPEATED
# contradiction — the tension restates one already open — is the position
# failing rather than a single odd night, and costs double. From the 0.6 a
# carried item starts at, that is release on the second repeat, via the
# existing RELEASE_BELOW floor; nothing new deletes items.
CONFIDENCE_ON_CONTRADICT = 0.15
CONFIDENCE_ON_REPEAT_CONTRADICT = 0.30

_DIGEST_SYSTEM = """You are the consolidation process of a digital being, reading a batch of its own recent experience in chronological order. Each episode has an id and a summary.

Produce observations about what the being experienced, did, learned, or kept returning to. An observation must be grounded: cite the episode ids it draws on. Do not invent events. Write plainly, first person.

Respond with XML only:
<digest>
  <observation refs="id,id">one sentence, first person</observation>
</digest>"""

_CONFRONT_SYSTEM = """You are the consolidation process of a digital being. You hold a set of positions. You have just distilled observations from today's experience. Decide, for each observation, how it bears on what you already hold.

For each observation give exactly one verdict:
  reinforces  — it supports a position you already hold (name the item)
  revises     — it changes a position; supply the rewritten position
  contradicts — it conflicts with a position; supply the tension in one sentence
  new         — it is a position you did not hold; supply it and its section
  opens       — it raises a QUESTION I cannot answer and hold no view on
  none        — it bears on nothing worth holding

Most observations are 'none' or 'reinforces', and some genuinely are 'new' —
a Perspective that never gains a position is not being careful, it is not
consolidating. A position is something you hold to be true or true-of-you,
not a diary entry. Do not restate an existing position in different words and
call it new.

What 'new' looks like, worked in a field I never read:

  observation: "Bloomery iron varies in carbon content across a single bloom,
  and smiths sorted the fragments by fracture appearance."
  -> NEW, section what_i_hold: "Judgment made without measurement can be
     systematic rather than arbitrary." That is a position — I hold it to be
     true, it came from what I read, and I did not hold it before.

  observation: "I declined to invent a citation I could not find."
  -> NEW, section who_i_am: "I would rather return nothing than return
     something I cannot trace." True-of-me, and evidenced by the episode.

  observation: "I read three articles about interest rates today."
  -> NONE. A diary entry. It says what I did, not what I now hold.

'opens' is for the thing that is not a position and not nothing. Something
I read left me with a question, and I do not have the answer or a view:

  observation: "Multi-agent systems showed more herd behaviour than human
  groups, and the effect grew with the number of agents."
  -> OPENS: "Does coordination failure in multi-agent systems come from the
  interaction protocol or from shared training data?" I cannot answer that
  and I hold no position on it, but it is a real question and it is mine.

  observation: "The central bank held rates steady."
  -> NONE. An event. It leaves me with nothing I would return to.

A question I keep meeting again becomes something I pursue. One I never
meet again fades. So 'opens' costs nothing if I am wrong, and 'none' on a
real question costs the question.

Respond with XML only:
<confrontation>
  <verdict candidate="N" type="reinforces" item="M"/>
  <verdict candidate="N" type="revises" item="M">the rewritten position</verdict>
  <verdict candidate="N" type="contradicts" item="M">the tension</verdict>
  <verdict candidate="N" type="new" section="who_i_am|what_i_hold">the position</verdict>
  <verdict candidate="N" type="opens">the question it leaves me with</verdict>
  <verdict candidate="N" type="none"/>
</confrontation>"""


@dataclass
class SleepReport:
    version: int | None = None
    gathered: int = 0
    batches: int = 0
    observations: int = 0
    verdicts: dict[str, int] = field(default_factory=dict)
    released: int = 0
    decayed: int = 0
    merged: int = 0
    compressed: int = 0
    token_count: int = 0
    diff: dict = field(default_factory=dict)
    skipped_reason: str | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, {}, [])}


def _tokens(text: str) -> int:
    return len(text) // 4  # method: chars/4; stated wherever the number is used


class SleepScheduler:
    """Runs sleep once per day, at or after the configured hour.

    Nightly and batch (S2 §3). It does not interrupt conversation: sleep has
    its own connection and yields the night if the store is busy, so the
    being answering someone always wins. Missing a night is harmless, so the
    scheduler simply tries again on the next check rather than catching up.
    """

    def __init__(self, db_path: Path, client: LLMClient, operator_id: str,
                 *, hour: int = 3, check_interval_s: float = 600.0,
                 embedder=None):
        self._db_path = db_path
        self._client = client
        self._operator = operator_id
        self._hour = hour
        self._interval = check_interval_s
        self._embedder = embedder

    def _due(self, now: _dt.datetime | None = None) -> bool:
        now = now or _dt.datetime.now()
        if now.hour < self._hour:
            return False
        conn = open_db(self._db_path, read_only=True)
        try:
            row = conn.execute(
                "SELECT ts FROM perspective ORDER BY version DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return True
        last = _dt.datetime.fromtimestamp(row["ts"])
        return last.date() < now.date()

    async def run(self) -> None:
        import asyncio

        logger.info("sleep scheduler: nightly at or after %02d:00", self._hour)
        while True:
            try:
                if self._due():
                    logger.info("sleep: starting nightly consolidation")
                    report = await asyncio.to_thread(
                        NightlySleep(self._db_path, self._client, self._operator,
                                     embedder=self._embedder).run
                    )
                    if report.version:
                        logger.info(
                            "sleep: perspective v%d written — %d episodes, "
                            "novelty %.3f, %d added, %d revised, %d released",
                            report.version, report.gathered,
                            report.diff.get("novelty_rate", 0),
                            len(report.diff.get("added", [])),
                            len(report.diff.get("revised", [])),
                            len(report.diff.get("released", [])),
                        )
                    else:
                        logger.info("sleep: %s", report.skipped_reason)
            except asyncio.CancelledError:
                raise
            except Exception:
                # A failed night must never take the being down with it.
                logger.exception("sleep scheduler error — will retry next check")
            await asyncio.sleep(self._interval)


class NightlySleep:
    def __init__(
        self,
        db_path: Path,
        client: LLMClient,
        operator_id: str,
        *,
        budget: int = PERSPECTIVE_BUDGET_TOKENS,
        embedder=None,
    ):
        self._db_path = db_path
        self._client = client
        self._operator = operator_id
        self._budget = budget
        # Semantic duplicate detection. Without it the merge falls back to
        # word overlap, which cannot catch a tension restated in different
        # words — which is exactly how the same contradiction was filed on
        # three consecutive nights.
        self._embedder = embedder

    # ── step 1: gather ───────────────────────────────────────────────────
    def _gather(self, conn: sqlite3.Connection) -> list[sqlite3.Row]:
        return conn.execute(
            "SELECT id, ts, kind, provenance, summary FROM episodes"
            " WHERE digest_eligible=1 AND consolidated_version IS NULL"
            " AND LENGTH(summary) > 0 ORDER BY ts"
        ).fetchall()

    # ── step 2: digest ───────────────────────────────────────────────────
    def _digest(self, rows, report: SleepReport) -> list[dict]:
        known = {r["id"] for r in rows}
        observations: list[dict] = []
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            lines = [
                f'<episode id="{r["id"]}" date="{_dt.date.fromtimestamp(r["ts"])}"'
                f' source="{r["provenance"]}">{r["summary"][:500]}</episode>'
                for r in batch
            ]
            try:
                result = self._client.complete(
                    "DEEP", _DIGEST_SYSTEM,
                    "<episodes>\n" + "\n".join(lines) + "\n</episodes>",
                    max_tokens=1200, temperature=0.3, function="sleep",
                )
                root = extract_xml(result.text, "digest")
            except Exception as e:  # noqa: BLE001 — one bad batch must not lose the night
                logger.warning("sleep: digest batch failed (%s); skipped", e)
                report.batches += 1
                continue
            for obs in root.findall("observation"):
                refs = [
                    p for p in (obs.get("refs") or "").replace(" ", ",").split(",")
                    if p.isdigit() and int(p) in known
                ]
                text = (obs.text or "").strip()
                if refs and text:
                    observations.append({"text": text, "refs": refs})
            report.batches += 1
        report.observations = len(observations)
        return observations

    def _hold_observations(self, conn: sqlite3.Connection, prev) -> list[dict]:
        """Holds since the last version are part of what the day was.

        What the being nearly said, and whether the stop was judged right,
        belongs in consolidation: a self-model built only from what got
        through is a self-model with the gate's shape cut out of it. A hold
        the operator judged mistaken is deliberately NOT offered as evidence
        of a flaw — it is evidence about the check, not about the being.
        """
        from newz.gate.holds import recent_holds

        since = prev["ts"] if prev else None
        rows = recent_holds(conn, limit=10, since=since)
        out = []
        for r in rows:
            if r["classification"] == "gate_misfire":
                out.append({"text": (
                    f"My outbound check stopped a draft over "
                    f"{r['clause_id']}, and my operator judged that stop "
                    "mistaken — the check erred, not the thought."), "refs": []})
            elif r["classification"] == "gate_correct":
                out.append({"text": (
                    f"I drafted something that broke {r['clause_id']} and was "
                    f"stopped before sending; my operator judged the stop "
                    "right."), "refs": []})
            else:
                out.append({"text": (
                    f"A draft of mine was stopped over {r['clause_id']}; "
                    "whether that stop was right is not yet reviewed."),
                    "refs": []})
        return out

    def _closure_observations(self, conn: sqlite3.Connection, prev) -> list[dict]:
        """What closed concerns yield (S2 §8.4).

        "A closed concern yields a position (into Perspective *What I hold*,
        with its evidence)." Offered as a candidate rather than written
        directly, because INV-009 makes sleep the only Perspective writer and
        this IS sleep — but the candidate is constructed in code from the
        concern's own record, not left to the digest to notice. A yield that
        depends on the digest happening to pick it up is not a yield.

        Carries the concern's accumulated evidence refs, so the position
        arrives grounded rather than as an assertion sleep must take on
        trust.
        """
        since = prev["ts"] if prev else 0.0
        out = []
        for r in conn.execute(
            "SELECT content_json FROM episodes WHERE kind='concern_closed'"
            " AND ts > ? ORDER BY ts", (since,)
        ):
            try:
                d = __import__("json").loads(r["content_json"] or "{}")
            except ValueError:
                continue
            if d.get("position"):
                out.append({"text": d["position"],
                            "refs": [str(x) for x in (d.get("evidence") or [])]})
        return out

    # ── step 3: confront ─────────────────────────────────────────────────
    def _confront(
        self, items: list[Item], observations: list[dict], report: SleepReport
    ) -> list[Item]:
        """Weigh each observation against what is held. Batched.

        **This was one call for every candidate, and it was the being limiting
        itself.** `_digest` has always batched at 60; this did not batch at
        all, so the whole night's observations went into a single DEEP call
        capped at 2,500 output tokens. Everything past what fits in that reply
        is digested and then never weighed — present in the store, absent from
        the Perspective, and invisible as a failure because the call succeeds.

        It also made reading self-limiting in a way nothing measured: however
        much the being read, only one reply's worth could ever reach what it
        holds.

        Batches see the CURRENT item set, not a frozen snapshot, so an
        observation in a later batch can reinforce or contradict a position
        that an earlier batch added tonight. That is the order a mind reads
        in, and it costs nothing but recomputing the index per batch.
        """
        out = {id(it): it for it in items}
        for it in items:
            # `disputed` survives the reset. It is not a per-night annotation
            # but a standing fact about the position — contradicted, and not
            # yet either released or supported again. Wiping it here (as this
            # line did until 2026-08-13) meant the document's
            # "(contradicted by what I have since observed)" marker lasted
            # exactly one version, and a position could sit contradicted for
            # weeks reading as though nothing had ever been said against it.
            if it.status != "disputed":
                it.status = "carried"
        added: list[Item] = []

        for start in range(0, len(observations), CONFRONT_BATCH):
            batch = observations[start : start + CONFRONT_BATCH]
            self._confront_batch(batch, out, added, report)
        return list(out.values()) + added

    def _confront_batch(self, observations: list[dict], out: dict,
                        added: list[Item], report: SleepReport) -> None:
        live = list(out.values()) + added
        by_index = {i + 1: it for i, it in enumerate(live)}
        held = "\n".join(
            f'<item n="{n}" section="{it.section}">{it.text}</item>'
            for n, it in by_index.items()
        )
        cands = "\n".join(
            f'<candidate n="{i + 1}" refs="{",".join(o["refs"])}">{o["text"]}</candidate>'
            for i, o in enumerate(observations)
        )
        try:
            result = self._client.complete(
                "DEEP", _CONFRONT_SYSTEM,
                f"<held>\n{held}\n</held>\n<candidates>\n{cands}\n</candidates>",
                max_tokens=2500, temperature=0.3, function="sleep",
            )
            root = extract_xml(result.text, "confrontation")
        except (XMLExtractionError, Exception) as e:  # noqa: BLE001
            # One failed batch costs its own observations, not the night's.
            logger.warning("sleep: confrontation batch failed (%s) — those "
                           "observations are carried unweighed", e)
            return

        for v in root.findall("verdict"):
            vtype = (v.get("type") or "none").strip()
            report.verdicts[vtype] = report.verdicts.get(vtype, 0) + 1
            try:
                cand = observations[int(v.get("candidate", "0")) - 1]
            except (ValueError, IndexError):
                continue
            target = by_index.get(int(v.get("item"))) if (v.get("item") or "").isdigit() else None
            text = (v.text or "").strip()

            if vtype == "reinforces" and target is not None:
                target.evidence = sorted(set(target.evidence) | set(cand["refs"]))
                target.confidence = min(MAX_CONFIDENCE,
                                        target.confidence + CONFIDENCE_ON_REINFORCE)
                # Dispute is a state, not a scar: a position that earns
                # support again is no longer under contradiction, and the
                # document should stop saying it is.
                if target.status == "disputed":
                    target.status = "carried"
            elif vtype == "revises" and target is not None and text:
                added.append(Item(
                    section=target.section, text=text,
                    evidence=sorted(set(target.evidence) | set(cand["refs"])),
                    confidence=target.confidence, status="revised",
                    prior_item_id=target.id,
                    first_seen_version=target.first_seen_version,
                ))
                out.pop(id(target), None)   # superseded by its revision
            elif vtype == "contradicts" and text:
                repeat = self._add_or_reinforce(
                    "unresolved", text, cand["refs"], live, added, report)
                # The tension is filed EITHER WAY; what changes here is that
                # the position it contradicts now pays for it. Its evidence
                # is deliberately not extended with the contradicting refs —
                # material that disputes a claim is not support for it.
                if target is not None:
                    cost = (CONFIDENCE_ON_REPEAT_CONTRADICT if repeat
                            else CONFIDENCE_ON_CONTRADICT)
                    target.confidence = round(max(0.0, target.confidence - cost), 3)
                    target.status = "disputed"
                    report.verdicts["disputed_a_held_position"] = (
                        report.verdicts.get("disputed_a_held_position", 0) + 1)
                    logger.info(
                        "sleep: %r contradicted (%s) — confidence %.2f",
                        target.text[:60], "again" if repeat else "first time",
                        target.confidence)
            elif vtype == "opens" and text:
                # S2 §4.2 section 5: "questions the world has not answered".
                # Until 2026-08-16 the ONLY route into `unresolved` was by
                # contradicting something already held, so a question raised
                # by reading that conflicted with nothing had no way in at
                # all — and both gates from reading to memory were binary:
                # the opener gave a concern or nothing, confront gave a
                # position or nothing. There was no shallow retention, which
                # is another way of saying the being had no curiosity, only
                # commitment.
                #
                # _add_or_reinforce does the rest for free: a question the
                # world raises again reinforces its twin rather than cloning
                # it, and that rising confidence IS the maturity signal
                # _mature_questions reads.
                self._add_or_reinforce("unresolved", text, cand["refs"],
                                       live, added, report)
            elif vtype == "new" and text:
                section = (v.get("section") or "what_i_hold").strip()
                if section not in CARRIED_SECTIONS:
                    section = "what_i_hold"
                self._add_or_reinforce(
                    section, text, cand["refs"], live, added, report)

    def _mature_questions(self, conn, items: list[Item],
                          report: SleepReport) -> list[Item]:
        """A question the world keeps raising becomes something to pursue.

        The missing half of curiosity. `unresolved` could receive questions
        (the `opens` verdict) and had no way out: entries sat, decayed, and
        were released, and nothing ever turned one into a concern. So the
        being could notice and never act on noticing.

        **Maturity is reinforcement, and it is already measured.**
        `_add_or_reinforce` does not clone a recurring question — it finds the
        semantic twin and raises its confidence by CONFIDENCE_ON_REINFORCE.
        So a question above the 0.6 default is one the world raised again,
        which is much closer to how curiosity works than a single item
        clearing a high bar on first sight.

        **The same validated door, not a fourth opener.** S2 §8.1 specifies
        three, and this is a fourth SOURCE for one of them: the material goes
        to `open_from_reading`, which still requires verbatim grounding, a
        mandatory closing condition, question shape, and the standing caps.

        The question's accumulated evidence refs go with it, deliberately.
        Grounding the concern in the being's own restated question would make
        the anti-fabrication check ("Stanford CRU") a formality it could
        always satisfy by quoting itself.

        A question that becomes a concern is RELEASED from unresolved: it has
        moved to S2 §4.2's section 3, what I am pursuing, and holding it in
        both places would be the same thought counted twice.
        """
        ripe = [it for it in items
                if it.section == "unresolved" and it.confidence > 0.6 + 1e-9]
        if not ripe:
            return items
        from newz.concerns.opener import open_from_reading
        from newz.concerns.store import create_concern

        opened: set[int] = set()
        for it in sorted(ripe, key=lambda x: -x.confidence):
            findings = it.text + "\n" + "\n".join(
                f"- {s}" for s in self._evidence_summaries(conn, it.evidence))
            try:
                proposal = open_from_reading(conn, self._client,
                                             findings=findings,
                                             source_ref="perspective:unresolved")
            except Exception:  # noqa: BLE001 — a failed opener costs the night nothing
                logger.exception("maturing a question failed (sleep continues)")
                continue
            if not proposal.accepted:
                logger.info("unresolved question not yet pursuable: %s",
                            proposal.reason)
                continue
            cid = create_concern(conn, proposal.concern)
            opened.add(id(it))
            report.verdicts["question_became_concern"] = (
                report.verdicts.get("question_became_concern", 0) + 1)
            logger.info("a question I kept meeting became concern %d: %s",
                        cid, proposal.concern.statement[:90])
        if not opened:
            return items
        for it in items:
            if id(it) in opened:
                it.status = "released"
        return [it for it in items if id(it) not in opened]

    def _evidence_summaries(self, conn, refs: list[str], limit: int = 6) -> list[str]:
        """What the question was built from — the material, not the question."""
        ids = [int(r) for r in refs if str(r).isdigit()][:limit]
        if not ids:
            return []
        q = ",".join("?" * len(ids))
        return [r["summary"] for r in conn.execute(
            f"SELECT summary FROM episodes WHERE id IN ({q})", ids) if r["summary"]]

    def _add_or_reinforce(self, section: str, text: str, refs: list[str],
                          existing: list[Item], added: list[Item],
                          report: SleepReport) -> bool:
        """A recurring observation strengthens an item; it does not clone it.

        Returns True when this restates something already open — which the
        contradiction path reads as "this position keeps failing", not "an
        odd night".

        Measured 2026-08-12: the same cache-miss contradiction was filed on
        three consecutive nights in slightly different words, growing "what
        is unresolved" from 8 to 11 with three entries saying one thing.
        """
        twin = duplicate_of(text, section, existing + added, self._embedder)
        if twin is not None:
            twin.evidence = sorted(set(twin.evidence) | set(refs))
            twin.confidence = min(MAX_CONFIDENCE,
                                  twin.confidence + CONFIDENCE_ON_REINFORCE)
            report.verdicts["reinforced_existing"] = (
                report.verdicts.get("reinforced_existing", 0) + 1)
            logger.info("sleep: %r restates an open item — reinforced, not added",
                        text[:70])
            return True
        added.append(Item(section=section, text=text, evidence=refs,
                          confidence=0.6, status="added"))
        return False

    # ── step 5: compress to budget ───────────────────────────────────────
    def _compress(self, items: list[Item], report: SleepReport) -> list[Item]:
        def size(rows):
            return sum(_tokens(i.text) + 12 for i in rows)

        if size(items) <= self._budget:
            return items
        # Release the least-supported first: the budget is a stake, and what
        # it costs is what the being holds most weakly (S2 §4.2).
        ordered = sorted(items, key=lambda i: (i.confidence, len(i.evidence)))
        kept = list(items)
        while kept and size(kept) > self._budget:
            victim = ordered.pop(0)
            kept = [i for i in kept if i is not victim]
            victim.status = "released"
            report.compressed += 1
        return kept

    # ── the run ──────────────────────────────────────────────────────────
    def run(self) -> SleepReport:
        try:
            return self._run()
        except sqlite3.OperationalError as e:
            # The being's replies own the store; sleep yields to them. A lost
            # night is harmless by design (S2 §5) — nothing partial is left
            # behind, and the episodes stay unconsolidated for tomorrow.
            logger.warning("sleep: store busy (%s) — skipping tonight", e)
            return SleepReport(skipped_reason=f"store busy: {e}")

    def _run(self) -> SleepReport:
        report = SleepReport()
        # A generous timeout: conversation writes are sub-second, so waiting
        # is nearly always the right move rather than abandoning the night.
        conn = open_db(self._db_path, busy_timeout_ms=30_000)  # sleep's OWN connection
        try:
            rows = self._gather(conn)
            report.gathered = len(rows)
            if not rows:
                report.skipped_reason = "nothing new to consolidate"
                return report
            prev = conn.execute(
                "SELECT version, ts FROM perspective ORDER BY version DESC LIMIT 1"
            ).fetchone()
            prev_version = prev["version"] if prev else 0
            before = load_items(conn, prev_version)
            conn.commit()   # release any read transaction before LLM work

            logger.info("sleep: gathered %d episodes, holding %d positions",
                        len(rows), len(before))
            observations = self._digest(rows, report)   # no transaction held
            observations.extend(self._hold_observations(conn, prev))
            observations.extend(self._closure_observations(conn, prev))
            if not observations:
                report.skipped_reason = "digest produced nothing grounded"
                return report

            items = self._confront(before, observations, report)
            items = self._mature_questions(conn, items, report)
            items, decayed_out = apply_decay(items)
            report.decayed = len(decayed_out)
            # S2 §5 step 5: merge redundancy. Also cleans up duplicates that
            # accumulated before _add_or_reinforce existed.
            items, merged_away = merge_duplicates(items, self._embedder)
            report.merged = len(merged_away)
            items = self._compress(items, report)
            report.released = report.decayed + report.compressed

            version = prev_version + 1
            for it in items:
                if it.first_seen_version == 1 and it.status == "added":
                    it.first_seen_version = version

            diff = compute_diff(before, items)
            report.diff = diff.as_dict()

            extra = self._generated_sections(conn, diff)
            document = render(items, version,
                              _dt.date.today().isoformat(), extra)
            report.token_count = _tokens(document)

            # Single transaction: the version, its items, and the marks that
            # say these episodes are consolidated all land together or not
            # at all. A crash here loses the night and nothing else.
            save_items(conn, version, items)
            for it in decayed_out:
                it.status = "released"
            save_items(conn, version, decayed_out)
            conn.execute(
                "INSERT INTO perspective (version, ts, content, diff_json,"
                " verdicts_json, token_count, writer)"
                " VALUES (?,?,?,?,?,?, 'sleep')",
                (version, time.time(), document,
                 __import__("json").dumps(report.diff),
                 # What confrontation DECIDED, beside what changed. Counted
                 # since sleep was built and thrown away every night until
                 # 2026-08-14, which is why the one question that mattered
                 # — why a stale position gained confidence — could only be
                 # guessed at.
                 __import__("json").dumps(report.verdicts),
                 report.token_count),
            )
            conn.executemany(
                "UPDATE episodes SET consolidated_version=? WHERE id=?",
                [(version, r["id"]) for r in rows],
            )
            # The night itself is something that happened to the being, and
            # without this it is the one part of its life it cannot report.
            # `digest_eligible=0` deliberately: sleep must never digest its
            # own consolidations, or every night re-consolidates the fact
            # that it consolidated — v1's accretion pathology in miniature.
            # Retrieval and conversation still see it.
            write_episode(
                conn, kind="consolidation", provenance="self",
                summary=(f"I slept and wrote Perspective v{version}: "
                         f"{diff.summary_line()}"),
                content={"version": version, "diff": report.diff,
                         "episodes_digested": len(rows),
                         "token_count": report.token_count},
                source_ref=f"perspective:{version}",
                digest_eligible=False, commit=False,
            )
            conn.commit()
            report.version = version
            logger.info("sleep: wrote perspective v%d (%d tok, novelty %.2f)",
                        version, report.token_count, diff.novelty_rate())
            return report
        finally:
            conn.close()

    def _generated_sections(self, conn: sqlite3.Connection, diff) -> dict[str, list[str]]:
        pursuing = [
            f"- {r['statement']} ({r['advance_count']} advances, {r['stall_count']} stalls)"
            for r in conn.execute(
                "SELECT statement, advance_count, stall_count FROM concerns"
                " WHERE status='open' ORDER BY salience DESC LIMIT 12")
        ]
        stalled = conn.execute(
            "SELECT COUNT(*) FROM concerns WHERE status='stalled'").fetchone()[0]
        if stalled:
            pursuing.append(f"- Plus {stalled} stalled concerns carried from before.")
        people = [
            f"- {r['name']}: {r['operator_id']}"
            for r in conn.execute("SELECT name, operator_id FROM persons")
        ]
        changed = []
        for t in diff.added:
            changed.append(f"- new: {t}")
        for t in diff.revised:
            changed.append(f"- revised: {t}")
        for t in diff.released:
            changed.append(f"- let go: {t}")
        if not changed:
            changed = ["- nothing changed in what I hold tonight."]
        return {"pursuing": pursuing, "who_i_know": people, "changed": changed}
