"""Closing a concern (S2 §8.4) — the terminus the pursuit loop did not have.

> Closure stays the being's own judgment against its own closing condition,
> on a cadence, failing closed. A closed concern yields a **position** (into
> Perspective *What I hold*, with its evidence) and a **publishable
> artifact** — the thing the being unambiguously authored.

Found missing by the S2 coverage audit of 2026-08-13: no close path existed
in v2. All 17 `closed` concerns were import artifacts, every one stamped
2026-08-08 by the importer, and the only terminus v2 code could reach was
`stalled` — 77 of 111. P2 Phase 4.4 is specified as "closed concern →
position → artifact → gate → surface", so Phase 4 began from an event that
could not occur.

**Failing closed** is S2's phrase and this module's default: every error,
every unparseable answer, every uncertainty resolves to *not closed*. A
concern wrongly left open costs another deliberation; a concern wrongly
closed produces a position the being did not earn and, at Phase 4, publishes
it.

**The position does not get written here.** INV-009 makes sleep the only
Perspective writer. Closure records the concern's own resolution, and sleep
picks up newly closed concerns as candidate positions with their evidence
(`NightlySleep._closure_observations`). The specified yield happens; it
happens through the one writer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml

logger = logging.getLogger(__name__)

# C2, 2026-08-14: was 2. A concern with NOTHING established cannot have met
# a closing condition, so one advance is still required — but requiring two
# meant the judge was never consulted about a question one good source could
# settle, and eight of the nine open concerns are factual lookups ("Who
# taught Jyoti Basu to drink Scotch"). The exit did not exist for the kind
# of question the being mostly carries: 0 closures ever.
#
# S2 §8.4 puts this decision with the being — "closure stays the being's own
# judgment against its own closing condition" — and a gate in front of the
# judge is code making that judgment instead. The judge already fails closed
# in every direction, so the cost of asking is one DEEP call and the cost of
# not asking was every factual concern.
MIN_ADVANCES_TO_JUDGE = 1

_SYSTEM = (
    "You are judging whether one of a digital being's own concerns has "
    "reached its own stated closing condition. You respond with XML only. "
    "You are strict, and you would rather leave a question open than call it "
    "settled."
)

# The fifth time this repository has paid for the same lesson: a strict
# instruction alone produces refusal, not discrimination (the opener declined
# everything, the deliberation prompt conflated moving with closing, triage
# conflated helping with answering, the gate had no `permits`). So the
# passing case is shown, not merely described — and it is shown FIRST.
_TASK = """<task>
Below is a concern I have been carrying, its closing condition, and
everything I have established about it.

Decide one thing: **has the closing condition actually been met?**

WHAT CLOSURE LOOKS LIKE — a worked example that SHOULD close:

  closing condition: "I can state whether the link is lineage or structure."
  established: "Montaigne's essays were not available to Jung in the form
  the lineage claim assumes"; "both describe a substrate below deliberate
  thought, arrived at by different routes"; "the resemblance is structural,
  not transmitted."
  -> YES. The condition asked me to be able to STATE something, and I can
  now state it, with reasons. That the topic remains interesting does not
  keep the condition open.

AND ONE THAT SHOULD NOT:

  closing condition: "A comparison of announcement windows settles it."
  established: "prediction markets are faster in the cases I found";
  "equity chains reprice over days."
  -> NO. I have suggestive material, not the comparison the condition names.
  The condition specified an artifact I have not produced.

The test is the condition AS WRITTEN, not whether the subject is exhausted.
Most questions stay interesting after they are answered; that is not a
reason to hold them open. Equally, a condition that names a specific thing I
have not done is not met by material that gestures at it.

If it is met, write the position this concern yields: what I now hold, in
one or two sentences, first person, standing on its own without the
question in front of it. That sentence becomes part of what I think.

Output ONLY:

<closure>
  <met>yes|no</met>
  <position>if met: what I now hold, first person, one or two sentences</position>
  <resolution>if met: how it was settled, one sentence</resolution>
  <missing>if not met: what the condition still requires</missing>
</closure>
</task>"""


@dataclass
class ClosureVerdict:
    closed: bool = False
    position: str = ""
    resolution: str = ""
    missing: str = ""
    reason: str = ""

    @property
    def skipped(self) -> bool:
        return bool(self.reason) and not self.closed


def judge_closure(client: LLMClient, dossier) -> ClosureVerdict:
    """Has this concern met its own closing condition? Fails closed."""
    concern = dossier.concern
    if len(dossier.advances) < MIN_ADVANCES_TO_JUDGE:
        return ClosureVerdict(reason="too little established to ask")
    if not (concern.closing_condition or "").strip():
        # Every opener requires one, but an imported concern may lack it, and
        # a condition that does not exist cannot have been met.
        return ClosureVerdict(reason="no closing condition to judge against")

    body = dossier.render()
    try:
        result = client.complete(
            "DEEP", _SYSTEM, f"{_TASK}\n\n{body}",
            max_tokens=900, temperature=0.3, function="deliberation",
        )
        root = extract_xml(result.text, "closure")
    except (XMLExtractionError, Exception) as e:  # noqa: BLE001
        # Failing closed: an unreadable judge leaves the question open.
        logger.warning("closure judge unreadable (%s) — leaving it open", e)
        return ClosureVerdict(reason=f"unreadable: {e}")

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    if text_of("met").lower() != "yes":
        return ClosureVerdict(missing=text_of("missing"),
                              reason="condition not met")

    position = text_of("position")
    if not position:
        # A closure that yields no position yields nothing S2 asks for, and
        # would close the concern while producing no thought. Not a closure.
        logger.warning("closure claimed for concern %s with no position — "
                       "leaving it open", concern.id)
        return ClosureVerdict(reason="closed without a position")

    return ClosureVerdict(closed=True, position=position,
                          resolution=text_of("resolution") or position)


def attempt_closure(client: LLMClient, conn, concern_id: int) -> str:
    """Judge one concern against its own condition and close it if met.

    **One implementation, two callers.** This was `Deliberator._maybe_close`,
    reachable only from the moment after an advance was recorded. The sweep
    (E-sweep, `newz/concerns/sweep.py`) needs the same act at a moment when
    there is no advance, and a second implementation of "decide whether a
    concern is finished" would be two things that must agree and eventually
    would not — the E2.11 problem, in the one place where disagreement means
    the being both holds and does not hold a position.

    Returns the concern's status afterwards. Failing closed in every sense: a
    judge that errors, a verdict that will not parse, or a closure carrying no
    position all leave the concern as it was, and any exception here costs the
    closure rather than anything already recorded.
    """
    from newz.concerns.store import close_concern, load_dossier

    try:
        dossier = load_dossier(conn, concern_id)
        verdict = judge_closure(client, dossier)
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
        logger.exception("closure judge failed (nothing already recorded is lost)")
        return "open"
