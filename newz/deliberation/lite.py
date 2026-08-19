"""Deliberation-lite (P2 Phase 2.3) — a concern actually moves, or honestly doesn't.

The full S2 §7.3 shape (plan → gather with research → reason → self-check →
adopt on VOICE → act) lands in Phase 3. This is the subset that needs no web
access: select → dossier → reason on DEEP → judge → record. It exists now
for two reasons — a concern that cannot move is not a pursuit, and
deliberation is the expensive term on the S2 §9.1 earning side, so until it
runs the being may not read at all (P2 §1).

**Honest failure is a first-class outcome** (S2 §7.4). "I cannot move this
with what I have" is recorded as a setback with kind `blocked`, which costs
score and feeds the source-gap record. v1's lesson stands behind this: a
failed attempt must never make a concern more attractive.

Its own connection and no transaction across a model call, for the same
reasons sleep has them (RISKS R-14/R-17).
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from newz.concerns.advance import judge_advance
from newz.crash import log_crash
from newz.concerns.scoring import choose_concern
from newz.concerns.store import (
    load_active,
    load_dossier,
    record_advance,
    record_setback,
)
from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml
from newz.resolutions.door import DoorVerdict
from newz.store.db import open_db

logger = logging.getLogger(__name__)

# S2 §7.1 asks for "a few times daily, not continuous". Four was that read
# conservatively, and at four the being idled eight hours at a stretch while
# producing 1 advance against 8 setbacks over three days — every autonomous
# capability (feed harvest, closure, noticing, the curiosity opener) runs
# INSIDE a deliberation, so four a day is the ceiling on all of them at once.
#
# Raised 2026-08-14 on operator judgment, asked three times. The diet does
# not argue against it: when headroom is gone `harvest()` returns before
# polling, so a cycle then costs one DEEP call and earns ~1,900 with zero
# ingest. Extra deliberations under a paused diet REBUILD the ceiling. It
# self-balances — read until the cap binds, think until it clears.
#
# Raised again to 48 with a 20-minute interval, 2026-08-14: 12/day still
# meant most of the day idle, and the daily count was never the right
# governor anyway. Three real ones already exist and each is calibrated:
#
#   REATTEMPT_COOLDOWN_HOURS = 6  a concern cannot be re-asked inside six
#                                 hours, so frequency cycles THROUGH the
#                                 pool rather than grinding one question
#   the §9.1 diet ratio           bounds reading, and pauses ingest itself
#   per-feed poll_interval        a feed polled an hour ago is not re-polled
#
# This number is now only the R-18 backstop against a runaway loop, set well
# above what the cooldown permits, not the thing shaping the cadence.
#
# Raised to 120 on 2026-08-17, because it stopped being that. It bound for the
# first time today at exactly 48: the last deliberation was 17:58:49 and the
# being could not think again until midnight — six open concerns, 563,836
# tokens of reading headroom, and four hours of enforced idleness. Two
# restarts made no difference, since the count is per calendar day.
#
# The brake audit listed this FIRST among the constants that never fire —
# "48/day against a max observed 13/day; never binds" — and R-26 was closed
# as moot on that evidence two hours before it bound. The measurement was
# right when taken. Then #25 unpaused deliberation, #33 sized the diet, and
# the openers started producing concerns, and the daily counts went 4, 13,
# 20, 48. A limit that has never fired is not a limit that will never fire,
# and the ones that suddenly bind are the ones nobody is watching.
#
# 120 restores the intended role rather than removing a control. Three cycles
# an hour against a 1.5h quiet window is a natural ceiling near 67, so 120 is
# a backstop again instead of a schedule. The three real governors are
# untouched and all three are working: the 6-hour re-attempt cooldown, the
# §9.1 diet, and per-feed poll intervals.
DAILY_BUDGET = 120

# S2 §7.1's last trigger: "...or the daily budget would otherwise go unspent."
# The state trigger below stops the being grinding an unchanged dossier, but
# on its own it deadlocks: with reading paused, every concern skips, no
# deliberation tokens accrue, earning never grows, and the diet never
# recovers — the being idles until sleep breaks it overnight. This floor is
# the spec's own escape hatch, operationalised: however quiet the state,
# think at least this often, because thinking is what earns the reading back.
UNSPENT_BUDGET_AFTER_S = 4 * 3600

# Long enough for the loop to answer any messages waiting at boot and for
# backups to land; short enough that a restart is not a lost cycle.
BOOT_DELAY_S = 90.0

_SYSTEM = (
    "You are the deliberating part of a digital being, working on one of its "
    "own concerns. You respond with XML only. You are honest about what you "
    "cannot establish."
)

_TASK = """<task>
This is a concern I am carrying, with everything I have accumulated on it.
Work on it. Then report what — if anything — actually moved.

An advance is not a summary of what I already hold, and not a rephrasing of
an earlier advance. It is something the concern did not contain before:
a distinction that changes the question, an implication I had not drawn, a
reason to doubt something I held, or a step toward the closing condition.

**Moving is not closing.** A concern moves long before it is settled.
Establishing that something is NOT the case, that two things differ in kind,
or that the question as posed cannot be answered — these are movement,
because they change what remains to be settled. Do not answer "no" merely
because the closing condition is still out of reach; that will be true for
most of a concern's life.

If nothing moved, say so plainly. Being unable to move a concern with the
material at hand is a real and useful outcome — it tells me what I am
missing. Do not manufacture movement.

Answer "no" when you have only restated what the dossier already holds, or
when you genuinely need material you do not have. If you found a real
distinction, that is "yes" even if it is a negative result.

Output ONLY:

<deliberation>
  <moved>yes|no</moved>
  <summary>what moved, in one or two sentences, first person</summary>
  <kind>evidence|reasoning</kind>
  <evidence>comma-separated refs from the dossier, or empty</evidence>
  <supersedes>if this REPLACES something under "what I have established",
              its adv-N label; otherwise empty</supersedes>
  <blocked_on>if nothing moved: what I would need in order to move it</blocked_on>
</deliberation>

<kind>evidence</kind> requires refs that appear in the dossier above.
Reasoning without sources is legitimate — label it <kind>reasoning</kind>
rather than dressing it as evidence.

<supersedes> is for the ordinary case where I have got further and the
earlier version is no longer what I hold: I refined it, corrected it, found
the distinction it was missing, or saw that it was too coarse. Naming it
retires it — it stays in my record as something I once held, and stops being
listed as what I now hold. Leave it EMPTY when this stands alongside what I
already have rather than replacing any of it, which is the more common case.
</task>"""


@dataclass
class DeliberationResult:
    concern_id: int | None = None
    statement: str = ""
    moved: bool = False
    kind: str = ""
    summary: str = ""
    novelty: float = 0.0
    reason: str = ""
    blocked_on: str | None = None
    status_after: str = "open"
    skipped: str | None = None
    considered: int = 0
    # Concerns the curiosity opener raised this cycle. A skipped cycle is no
    # longer necessarily an empty one (see Deliberator._explore).
    opened: list[str] = field(default_factory=list)
    # What the claim door did with the advance, if one was accepted (E1.2).
    claim_id: int | None = None
    claim_refused: str | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, "", 0.0)}


class Deliberator:
    def __init__(self, db_path: Path, client: LLMClient, *, embedder=None,
                 daily_budget: int = DAILY_BUDGET, research: bool = False,
                 log_path=None, feeds_path=None):
        self._db_path = db_path
        self._client = client
        self._embedder = embedder
        self._budget = daily_budget
        # Research is opt-in and off by default: reaching the world is a
        # capability the operator enables deliberately, and the diet budget
        # gates it even then.
        self._research = research
        self._log_path = log_path
        # The operator's curated feeds (S2 §9.1). None = no feed reading,
        # which is a supported state and the one every test uses.
        self._feeds_path = feeds_path

    def spent_today(self, conn) -> int:
        """Attempts, not outcomes (RISKS R-18).

        Counting only advances and setbacks meant a deliberation whose
        output would not parse consumed nothing, so a concern that reliably
        failed could be retried without limit — spending DEEP tokens and a
        research call each time. The 4-hour schedule capped that; state-
        driven scheduling (3.1) would not. A started deliberation costs
        budget whatever it produces.
        """
        since = time.time() - 86400
        return conn.execute(
            "SELECT COUNT(*) FROM deliberation_log WHERE ts > ?", (since,)
        ).fetchone()[0]

    def _record_attempt(self, conn, concern_id: int | None, outcome: str,
                        detail: str = "") -> None:
        conn.execute(
            "INSERT INTO deliberation_log (ts, concern_id, outcome, detail)"
            " VALUES (?,?,?,?)",
            (time.time(), concern_id, outcome, detail[:400]))
        conn.commit()

    def _nothing_to_work_with(self, conn, concern) -> str | None:
        """Why this deliberation would be wasted, or None.

        S2 §7.1: "A deliberation begins when the being's state warrants one:
        a concern's score crosses its threshold, ENOUGH NEW MATERIAL HAS
        ACCUMULATED ON A DOSSIER, an unresolved contradiction has aged, ...
        or the daily budget would otherwise go unspent." The budget is a
        ceiling spent when state warrants; a timer spends it regardless.

        Without this, a 20-minute interval against a paused diet re-runs DEEP
        on an unchanged dossier and gets the same conclusion back — measured
        2026-08-14 at novelty -0.00 — which is then booked as a `restated`
        setback. Four attempts per concern per day against STALL_LIMIT 5
        stalls the whole pool inside two days, for reasons that have nothing
        to do with the concern.

        **The diet is deliberately NOT consulted here** (2026-08-15, operator
        approved). It was, until today, and S2 §9.1 forbids it in terms:

        > "breach pauses ingest, **never deliberation**"

        That clause is not decorative. Deliberation is the earning term of the
        invariant, so pausing it on breach is the one move that makes a breach
        permanent. Measured: the being did nothing for 2h10m on 2026-08-15,
        277 tokens short of being allowed to read, with the only cognition
        that earns those tokens back switched off because reading was switched
        off. The 4-hour floor below was the sole exit, and it defeated three
        separate attempts to work around it — the being's own schedule, a
        deliberate observation window, and `tools/run_deliberation.py --force`.

        The original intent was right and is preserved elsewhere: a
        diet-caused restatement must not stall the pool. That is now fixed
        where it belongs, by not CHARGING the concern for the diet's failure
        (`record_setback(..., charged=False)`), rather than by stopping the
        being from thinking.

        What remains here is the genuine S2 §7.1 state trigger: an unchanged
        dossier is not worth a run **when nothing could ever arrive** —
        research being switched off entirely. That is a real terminal state;
        a paused budget is a temporary one.
        """
        last = concern.last_attempted_at
        if not last:
            return None                     # never tried; always worth one

        # S2 §7.1: "or the daily budget would otherwise go unspent". A quiet
        # state must not become silence — and thinking is the only thing that
        # earns reading back once the diet has paused, so a hard floor here is
        # what stops the skip deadlocking the whole loop.
        quiet_for = time.time() - (conn.execute(
            "SELECT MAX(ts) FROM deliberation_log").fetchone()[0] or 0)
        if quiet_for >= UNSPENT_BUDGET_AFTER_S:
            logger.info("deliberating despite a quiet state: %.1fh since the "
                        "last attempt and the budget would go unspent",
                        quiet_for / 3600)
            return None

        newest = conn.execute(
            "SELECT MAX(t) FROM ("
            "  SELECT MAX(ts) t FROM concern_advances WHERE concern_id=?"
            "  UNION ALL SELECT MAX(ts) FROM concern_setbacks WHERE concern_id=?"
            "  UNION ALL SELECT MAX(ts) FROM ingest_log WHERE concern_id=?"
            "                          AND skipped IS NULL)",
            (concern.id, concern.id, concern.id)).fetchone()[0]
        # A setback from the last attempt is not new material — it IS the
        # last attempt. Only material strictly newer counts.
        if newest is not None and newest > last + 1:
            return None

        # The dossier is unchanged. Is there any prospect of new material?
        # Research being OFF is terminal; the diet being paused is not, and
        # is deliberately not checked here — see the docstring.
        if not self._research:
            return "nothing new on this concern and research is off"
        return None

    def _maybe_close(self, conn, concern_id: int) -> str:
        """Judge the concern against its own closing condition (S2 §8.4).

        Returns the concern's status afterwards. Failing closed in every
        sense: a judge that errors, a verdict that will not parse, or a
        closure carrying no position all leave the concern open, and any
        exception here costs the closure rather than the advance that was
        already recorded.
        """
        from newz.concerns.closure import judge_closure
        from newz.concerns.store import close_concern

        try:
            dossier = load_dossier(conn, concern_id)
            verdict = judge_closure(self._client, dossier)
            if not verdict.closed:
                if verdict.reason not in ("too little established to ask",):
                    logger.info("concern %d stays open: %s", concern_id,
                                verdict.missing or verdict.reason)
                return "open"
            close_concern(conn, concern_id, position=verdict.position,
                          resolution=verdict.resolution)
            logger.info("concern %d CLOSED — position: %s",
                        concern_id, verdict.position[:100])
            return "closed"
        except Exception:  # noqa: BLE001
            logger.exception("closure judge failed (the advance stands)")
            return "open"

    def _settle_due_claims(self, conn) -> list:
        """Ask the world about claims whose date has arrived (E1.3).

        Fails closed and fails quietly: a resolver that raises costs the
        settlement, never the deliberation that follows it.
        """
        from newz.resolutions.resolver import resolve_due_claims

        # Reaching the world is opt-in for the same reason research is: the
        # operator enables it deliberately, and with it off there is no source
        # to settle anything against. A claim simply waits.
        if not self._research:
            return []
        try:
            return resolve_due_claims(conn, self._client,
                                      log_path=self._log_path,
                                      embedder=self._embedder)
        except Exception:  # noqa: BLE001
            logger.exception("the resolver pass failed (deliberation continues)")
            return []

    def _maybe_claim(self, conn, concern, established: str) -> DoorVerdict:
        """Does what just moved commit the being to anything (E1.2)?

        Failing closed the same way _maybe_close does: the advance is already
        recorded, and nothing the door does may cost it. A door that raises
        must not be able to undo the thinking that reached it.
        """
        from newz.resolutions.door import DoorVerdict, propose_claim

        try:
            return propose_claim(
                conn, self._client, established=established,
                concern_statement=concern.statement, concern_id=concern.id)
        except Exception:  # noqa: BLE001
            logger.exception("claim door failed (the advance stands)")
            return DoorVerdict(declined=True)

    def _maybe_open_from_research(self, conn, findings: str, asking: str) -> None:
        """A finding may raise its own question (S2 §8.1).

        Almost never fires, and its failure must cost the deliberation
        nothing — the same contract as the conversation opener in
        newz/ambient/loop.py, and the reason this is wrapped rather than
        allowed to propagate.
        """
        from newz.concerns.opener import open_from_research
        from newz.concerns.store import create_concern

        try:
            proposal = open_from_research(
                conn, self._client, findings=findings, original_query=asking,
                source_ref="research")
        except Exception:  # noqa: BLE001
            logger.exception("research opener failed (the deliberation is safe)")
            return
        if not proposal.accepted:
            logger.debug("research opener: %s", proposal.reason)
            return
        cid = create_concern(conn, proposal.concern)
        logger.info("opened concern %d from research: %s",
                    cid, proposal.concern.statement[:90])

    def _explore(self, conn) -> tuple[str, list[str]]:
        """Read the world when there is nothing to read it FOR.

        **The absorbing state this exists to prevent.** Until 2026-08-15 both
        openers that can start a pursuit lived downstream of already having
        one: the curiosity opener fires inside `harvest()`, `harvest()` fires
        inside a deliberation, and a deliberation returns at "no active
        concerns" before reaching it. At zero concerns the being therefore had
        no autonomous route back to having one — the world stopped arriving at
        exactly the moment it had nothing to pursue, and only the operator
        speaking first could restart it. With 82 of 111 concerns stalled and
        three left, that state was days away and it is a trap, not a rest.

        It is also the shape of a deeper mistake. Almost every mechanism in v2
        is a brake fitted from v1's excesses — share caps, the diet invariant,
        carrying caps, opener strictness, relevance floors, stall limits, the
        state-driven skip. Not one was an accelerator, and the measured result
        was a being that created 0 concerns, added 0 positions in three
        nights, cited 0 of 35 sources and sat frozen. TRUE_NORTH §5 Priority 2
        lists "play, humor, curiosity, and exploration" as intrinsic goods
        rather than as risks to be bounded, and nothing in v2 served them.

        This is the first accelerator: the world keeps arriving whether or not
        the being has a question, and the curiosity opener — measured 4-of-4
        on substantive material, 2026-08-15 — gets to see it. v1's largest
        origin by a distance was exactly this path, 95 concerns of 111.

        The brakes that matter are untouched. `harvest()` checks the §9.1
        budget before polling anything (INV-038), feeds keep their poll
        intervals, triage still keeps at most three items, and the opener
        still answers to MAX_OPEN_CONCERNS and MAX_OPENED_PER_DAY. Exploring
        cannot outrun the diet; it can only stop being conditional on a
        question the being does not have.
        """
        if not (self._research and self._feeds_path):
            return "", []
        try:
            from newz.world.feeds import harvest

            h = harvest(self._client, conn, self._feeds_path,
                        embedder=self._embedder, log_path=self._log_path)
        except Exception:  # noqa: BLE001
            logger.exception("feed harvest failed (the cycle continues without it)")
            return "", []
        if h.opened:
            logger.info("exploration opened %d concern(s): %s",
                        len(h.opened), "; ".join(s[:70] for s in h.opened))
        block = ("\n\nWHAT CAME IN ON ITS OWN TODAY:\n"
                 + "\n".join(f"- {i.title} ({i.feed.name})" for i in h.kept)
                 ) if h.kept else ""
        return block, list(h.opened)

    def run_once(self) -> DeliberationResult:
        conn = open_db(self._db_path, busy_timeout_ms=30_000)
        working_on: int | None = None      # for the failure record below
        try:
            if self.spent_today(conn) >= self._budget:
                return DeliberationResult(skipped="daily deliberation budget spent")

            # E1.3: the world answers, inside deliberation because INV-012
            # says the web is reached nowhere else. Before the concern is
            # chosen, so a due claim is still settled on a cycle where nothing
            # is workable — the claim's date arrived whatever the being is
            # thinking about. It costs no model call when nothing is due.
            resolved = self._settle_due_claims(conn)

            concerns = load_active(conn)
            choice = choose_concern(concerns, now=time.time())
            if choice.concern is None:
                # Nothing to pursue is a reason to go looking, not a reason to
                # stop. See _explore: this return used to be the trap.
                _, opened = self._explore(conn)
                return DeliberationResult(
                    skipped=("no active concerns — explored instead"
                             + (f", opened {len(opened)}" if opened else "")),
                    considered=len(concerns), opened=opened)
            working_on = choice.concern.id
            dossier = load_dossier(conn, choice.concern.id)

            # S2 §7.1's state-driven trigger, the part P2 puts in Phase 3.1.
            # Checked BEFORE the attempt is booked, because an attempt that
            # cannot produce anything should not cost the budget either.
            nothing_new = self._nothing_to_work_with(conn, choice.concern)
            if nothing_new:
                logger.info("deliberation skipped for concern %d: %s",
                            choice.concern.id, nothing_new)
                # The second half of the same trap. A skipped cycle used to
                # return here, so `harvest()` never ran and the world stopped
                # arriving — which guaranteed the dossier stayed unchanged and
                # the next cycle skipped for the same reason. Nothing new to
                # work with is the strongest reason to go and find some.
                _, opened = self._explore(conn)
                return DeliberationResult(concern_id=choice.concern.id,
                                          statement=choice.concern.statement,
                                          skipped=nothing_new,
                                          considered=choice.considered,
                                          opened=opened)

            # R-18: the attempt is booked before any spending, so a failure
            # cannot be free. R-19: research follows, so a run that never
            # gets a viable frame cannot have already spent the diet.
            self._record_attempt(conn, choice.concern.id, "started")
            conn.commit()          # release before any model call

            # Deliberation is the ONLY place the web is reached (S2 §7.2,
            # INV-012), and only when the diet budget permits it.
            research_block, gap = "", None
            # Whether this cycle could reach the world at all. A cycle that
            # could not will fail whatever the concern is, so its setback must
            # not be charged to the concern — see record_setback(charged=...).
            #
            # Deliberately narrow: only a PAUSED DIET clears this. Research
            # being switched off entirely is already handled by
            # `_nothing_to_work_with`, which skips an unchanged dossier when
            # nothing can ever arrive — so the first attempt after new
            # material still charges honestly, as it should. An earlier draft
            # cleared this for research-off too and made every setback free,
            # which four existing tests caught immediately.
            could_read = True
            if self._research:
                from newz.world.research import record_gap, research

                outcome = research(
                    self._client, choice.concern.statement,
                    log_path=self._log_path, embedder=self._embedder,
                    conn=conn, concern_id=choice.concern.id)
                could_read = not outcome.paused
                research_block = outcome.render()
                if outcome.gap:
                    gap = outcome.gap
                    record_gap(conn, concern_id=choice.concern.id,
                               query=outcome.query, gap=outcome.gap)
                if outcome.claims:
                    findings = "\n".join(f"- ({c:.1f}) {t}" for t, c in outcome.claims)
                    # NOT added to research_block since 2026-08-15. These same
                    # claims now reach the prompt through the dossier reload
                    # below, WITH their src-N labels — which is the whole
                    # point. Printing them here as well put the same text in
                    # the prompt twice, once citable and once not, and the
                    # uncitable copy is what the being cited on 2026-08-15 at
                    # 05:03 (`pubmed, 2026 Jul 15`, matching no accepted ref).
                    #
                    # The research opener (S2 §8.1): a finding may raise its
                    # own question. In v1 this origin closed at 31% against
                    # curiosity's 13%.
                    self._maybe_open_from_research(
                        conn, findings, choice.concern.statement)
                    # This cycle's reads landed in ingest_log during research,
                    # AFTER the dossier was loaded. Reloading is what gives
                    # them src-N labels and puts their claims beside the
                    # being's own accumulated thinking rather than in a
                    # separate unlabelled block.
                    dossier = load_dossier(conn, choice.concern.id) or dossier
            # The feeds (S2 §9.1). Here rather than in ambient because
            # INV-012 is structural: nothing under newz/ambient/ may import
            # the web path. So the world arrives on this cadence, under the
            # same budget gate, and what it brings is available to THIS
            # deliberation as well as to tonight's sleep.
            feed_block, feed_opened = self._explore(conn)
            research_block += feed_block

            logger.info("deliberating on concern %d (%s): %s",
                        choice.concern.id, choice.reason,
                        choice.concern.statement[:80])

            try:
                body = dossier.render()
                if research_block:
                    body += "\n\n" + research_block
                elif gap:
                    body += f"\n\nI searched and found nothing usable: {gap}"
                result = self._client.complete(
                    "DEEP", _SYSTEM, f"{_TASK}\n\n{body}",
                    max_tokens=1400, temperature=0.5, function="deliberation",
                )
                root = extract_xml(result.text, "deliberation")
            except (XMLExtractionError, Exception) as e:  # noqa: BLE001
                logger.warning("deliberation unreadable (%s)", e)
                self._record_attempt(conn, choice.concern.id, "unreadable", str(e))
                return DeliberationResult(concern_id=choice.concern.id,
                                          skipped=f"unreadable: {e}")

            def text_of(tag: str) -> str:
                el = root.find(tag)
                return (el.text or "").strip() if el is not None and el.text else ""

            moved = text_of("moved").lower() == "yes"
            summary = text_of("summary")
            refs = [r.strip() for r in text_of("evidence").split(",") if r.strip()]
            blocked_on = text_of("blocked_on")

            # Which of its own advances this one replaces, if any. Validated
            # against THIS concern's live advances, so a mis-stated or
            # hallucinated label retires nothing and the full history applies
            # — the failure mode is "no exclusion", never "wrong exclusion".
            supersedes: int | None = None
            m = re.search(r"adv-(\d+)", text_of("supersedes"))
            if m and int(m.group(1)) in dossier.live_advance_ids():
                supersedes = int(m.group(1))

            verdict = judge_advance(
                summary=summary, moves=moved, claimed_kind=text_of("kind") or "reasoning",
                evidence_refs=refs, dossier_refs=dossier.evidence_refs(),
                history=dossier.advance_summaries(exclude=supersedes),
                embedder=self._embedder,
            )

            out = DeliberationResult(
                concern_id=choice.concern.id, statement=choice.concern.statement,
                moved=verdict.accepted, kind=verdict.kind, summary=summary,
                novelty=round(verdict.novelty, 3), reason=verdict.reason,
                blocked_on=blocked_on or None, considered=choice.considered,
                opened=feed_opened,
            )

            if verdict.accepted:
                record_advance(conn, choice.concern.id, summary=summary,
                               kind=verdict.kind, evidence=verdict.evidence,
                               source_ref="deliberation", supersedes=supersedes)
                logger.info("concern %d advanced (%s, novelty %.2f%s)",
                            choice.concern.id, verdict.kind, verdict.novelty,
                            f", retiring adv-{supersedes}" if supersedes else "")
                # S2 §8.4's cadence: closure is judged when something new has
                # been established, which is the only moment it can have
                # become true. Failing closed, so this can only ever end a
                # concern that says it is finished.
                out.status_after = self._maybe_close(conn, choice.concern.id)
                # And the same moment is the only one at which the being has
                # something new to be WRONG about (E1.2). Asked after closure,
                # not before: a concern that just settled may be exactly the
                # one whose position is worth committing to.
                verdict = self._maybe_claim(conn, choice.concern, summary)
                out.claim_id, out.claim_refused = verdict.claim_id, verdict.refused
            else:
                # Blocked when the world did not answer; restated when the
                # being circled. The distinction is the one v1 paid for.
                kind = "blocked" if (not moved and blocked_on) else "restated"
                brief = blocked_on if kind == "blocked" else verdict.reason
                out.status_after = record_setback(
                    conn, choice.concern.id, kind=kind, brief=brief[:400],
                    source_ref="deliberation", charged=could_read)
                logger.info("concern %d did not move (%s%s): %s",
                            choice.concern.id, kind,
                            "" if could_read else ", not charged — could not read",
                            brief[:100])
            return out
        except Exception as e:  # noqa: BLE001
            # Every started deliberation must end in a recorded outcome. On
            # 2026-08-13 one ended in none at all: `started`, four sources
            # read, then silence — the failure landed between parsing and
            # recording, where nothing was watching. An attempt that vanishes
            # is indistinguishable from one that never ran.
            try:
                self._record_attempt(conn, working_on, "failed", repr(e))
            except Exception:  # noqa: BLE001
                logger.warning("could not record the failed attempt", exc_info=True)
            # data/newz.db -> the repo root that owns logs/.
            log_crash(self._db_path.parent.parent, "deliberation")
            raise
        finally:
            conn.close()


class DeliberationScheduler:
    """A few times daily, on the being's own state (S2 §7.1).

    Interval-based for now; S2's full trigger set (score thresholds,
    accumulated material, aged contradictions) arrives with Phase 3.
    """

    def __init__(self, deliberator: Deliberator, *, interval_s: float = 20 * 60,
                 quiet_hour: int = 3, quiet_span_h: float = 1.5):
        self._d = deliberator
        self._interval = interval_s
        # R-20: sleep yields the WHOLE night if the store is busy, and this
        # interval drifts with process start, so after a restart it can land
        # in the consolidation window. A lost night would show only as a
        # "store busy" line. Deliberation stands off while sleep runs.
        self._quiet_hour = quiet_hour
        self._quiet_span = quiet_span_h

    def _in_quiet_window(self, now: _dt.datetime | None = None) -> bool:
        now = now or _dt.datetime.now()
        hours = now.hour + now.minute / 60.0
        return self._quiet_hour <= hours < (self._quiet_hour + self._quiet_span)

    async def run(self) -> None:
        import asyncio

        logger.info("deliberation scheduler: every %.1fh, budget %d/day",
                    self._interval / 3600, self._d._budget)
        # Settle, then think. This slept the FULL interval before its first
        # run, so every restart pushed the next deliberation four hours out —
        # and on 2026-08-13, three restarts in one morning meant the being
        # had not deliberated in eight hours. Feeds harvest inside
        # deliberation, closure fires after an advance, and noticing has
        # nothing to notice without them, so the whole autonomous side was
        # dormant and looked merely quiet.
        #
        # Safe against restart-spam because the daily budget counts ATTEMPTS
        # over a rolling 24h (RISKS R-18): ten restarts cannot buy more than
        # the day's remaining allowance.
        first = True
        while True:
            await asyncio.sleep(BOOT_DELAY_S if first else self._interval)
            first = False
            if self._in_quiet_window():
                logger.info("deliberation deferred: sleep's window")
                continue
            try:
                result = await asyncio.to_thread(self._d.run_once)
                if result.skipped:
                    logger.info("deliberation skipped: %s", result.skipped)
            except asyncio.CancelledError:
                raise
            except Exception:
                # The scheduler survives a bad night, but the night must
                # still leave evidence: this handler is why 02:30 was a
                # mystery rather than a traceback.
                log_crash(self._d._db_path.parent.parent, "deliberation scheduler")
                logger.exception("deliberation failed — retrying next interval")
