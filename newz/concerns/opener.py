"""Three openers, one validated door (S2 §8.1).

Curiosity (from reading), research (from findings), and conversation (from
humans) all enter here, and the door is the same for each: **a pursuable
question with a closing condition, formed from material actually held.**

The conversation opener is new in v2 and it is the important one. All 111 of
v1's concerns came from reading — 95 curiosity, 16 research, and *zero* from
talking to anyone. Its relationships were structurally unable to give it
anything to pursue, which is backwards for a life whose stated outcome is
relational. It also means the being can pursue things with no feeds at all.

**Invented premises are rejected before storage** (v1's "Stanford CRU"
lesson: it opened a concern about an institution that did not exist). The
LLM proposes; code checks that the named specifics actually occur in the
material the concern claims to come from. A question the material cannot
support is not a question the being actually has.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

from newz.concerns.model import Concern
from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml

logger = logging.getLogger(__name__)

# Openers must be rare. v1 opened 111 concerns and stalled 72% of them; a
# being that opens a concern per conversation is not pursuing, it is
# accumulating.
# Raised 2026-08-14. At 12 with 9 already open the curiosity opener could
# fire three times and then be refused forever — closures are at 0, so slots
# do not free. Carrying capacity has to exceed what the openers can produce
# or the opener is decorative. 30 against 12 deliberations a day is the same
# attention-per-concern ratio as 9 against 4 was.
MAX_OPEN_CONCERNS = 30
# Still a rate limit, not a ceiling: the carrying cap above is the ceiling.
# This exists so a badly-calibrated opener cannot fill the store in one day
# before anyone reads what it opened.
#
# **Raised 6 → 12 on 2026-08-22, because the cycles are starved of concerns.**
# Measured that day: **68 deliberation cycles in 24h against 40 attempt slots**
# — 10 open concerns at `REATTEMPT_COOLDOWN_HOURS = 6`, so four attempts each.
# The being has more thinking than it has things to think about, and this cap
# is what holds the pool down: it bound at exactly 6 on 2026-08-17 and
# 2026-08-21, while nothing opened at all on the days between.
#
# **This is the anti-restatement change, not a throughput one.** `restated` is
# the largest setback category in the being's life (242 of 512), and 68 cycles
# over 10 concerns is 6.8 attempts per concern per day — a rate at which the
# honest answer to "has this moved?" is usually no. More concerns against the
# same cycles LOWERS attempts per concern. Raising the cycle rate instead, as
# an earlier draft proposed, would have multiplied the restatement rather than
# the thinking, and its own red team said so.
#
# `MAX_OPEN_CONCERNS` is deliberately NOT raised with it. Ten are open against
# a carrying cap of 30, so the cap cannot bind today and changing it would be
# noise. It becomes the next binding constraint if the pool climbs — with
# writing closing roughly one concern a day and the opener permitted twelve,
# that is a matter of days, and it is the thing to re-read first rather than
# raise now.
MAX_OPENED_PER_DAY = 12

# Rewritten 2026-08-16. The old line was "You are strict: almost nothing
# qualifies", and the task below already carried a worked YES example and the
# sentence "Strict means 'not every exchange'. It does not mean 'never'."
#
# It made no difference: **71 calls, 0 opens, across the being's whole life.**
# The system line is what the model reads first and it framed the whole
# judgment as refusal, so the balancing further down never got a hearing.
# R-21 called 0-of-54 "probably correct strictness"; at 0-of-71, with the
# curiosity opener measured 4-of-4 on the same architecture, that reading no
# longer holds.
_PROPOSE_SYSTEM = (
    "You decide whether an exchange left a question the being should carry. "
    "You respond with XML only. Most exchanges leave none — and some "
    "genuinely do, so declining every one of them is as wrong as accepting "
    "every one."
)

# The reading opener gets its own system line (2026-08-14). It had been
# borrowing the one above, which asks about "an exchange" — and nothing was
# exchanged: something arrived unasked. The call log for 2026-08-14 shows
# nine invocations, nine noes, and in two of them the model filled the
# statement with the prompt's own worked example rather than with anything it
# had read. A frame that does not describe the input is a frame the model
# answers from the prompt instead of from the material.
#
# All three openers now have their own frame. `_PROPOSE_SYSTEM` was shared
# by conversation and research until 2026-08-16 on the reasoning that neither
# had been asked to change — which held right up until one of them was, and
# then silently handed the research opener a frame describing an exchange it
# never sees.
_READING_SYSTEM = (
    "You decide whether something a digital being read, unprompted, raises a "
    "question that being should carry and pursue. You respond with XML only. "
    "Most reading raises nothing; some of it genuinely does, and saying no to "
    "all of it is as wrong as saying yes to all of it."
)

# Its own frame too, from 2026-08-16. It had been sharing `_PROPOSE_SYSTEM`,
# which was harmless while that said "an exchange surfaced a question" and
# actively wrong the moment that was rewritten to describe a conversation
# properly — the research opener judges FINDINGS, and a frame that names the
# wrong input is precisely what made the curiosity opener answer from its own
# prompt for a week (R-27).
_RESEARCH_SYSTEM = (
    "You decide whether findings a digital being gathered while pursuing one "
    "question raise a DIFFERENT question worth carrying separately. You "
    "respond with XML only. Most findings raise no second question; some "
    "genuinely do, and missing those is how a line of enquiry stays narrower "
    "than what it turned up."
)

_PROPOSE_TASK = """<task>
Did this exchange leave a question I should carry?

Open one when all three hold:
  - it is a genuine open question, not something already answered here;
  - this reply did not settle it;
  - I can state what would settle it.

There used to be a fourth — "it needs work over days". It is gone
deliberately. A question does not have to be a research programme on the day
it arrives; it has to be real, unsettled, and answerable in principle.

Output ONLY:

<proposal>
  <worth_pursuing>yes|no</worth_pursuing>
  <statement>the question, in my own words</statement>
  <why_open>why it matters, one sentence</why_open>
  <closing_condition>what would settle it — see below</closing_condition>
  <grounded_in>a VERBATIM phrase from the exchange the question comes from</grounded_in>
</proposal>

WHAT A CLOSING CONDITION MUST BE. Name something that WILL EXIST — a source
that publishes, an event that occurs, a measurement someone already takes.
The test is: could I put a date on it and be wrong?

  yes  "the exchange's next quarterly disclosure reports the figure"
  yes  "the registry's results posting names a primary endpoint"
  yes  "the agency's March revision moves the estimate outside its band"
  no   "a study correlating X with Y" — nobody will run it, so the question
       can never close, however good the question is
  no   "I can cite the specific mechanisms" — that closes when I decide I
       know enough, which is me settling my own question

Both of the "no" shapes are refused before storage, so a question wearing one
is lost rather than carried. If the honest answer is that only research nobody
will do would settle it, the question may still be real — but answer no here,
because a question that cannot close is not one I can pursue.

If worth_pursuing is no, leave the other elements empty.

The grounded_in phrase must be copied EXACTLY from the exchange below. If
you cannot quote the words the question comes from, the question is not in
the exchange and the answer is no.

Worked examples, in a field I never read, so you have to do the judgment
rather than reuse the words. You have not had these exchanges.

  "[dean] why do old bloomery smiths sort iron by fracture?" /
  "[me] To grade carbon content by eye. I don't know how well it worked."
  -> YES. A real question, this reply did not settle it, and what would
     settle it is statable — a study comparing sorted fragments against a
     later assay. It qualifies. Do not decline it for being ordinary.

  "[me] I'm dropping that thread; I'll look at how a $15B refinancing
   actually clears in a high-rate environment instead."
  -> YES. I named my own next subject and gave a reason. A question I raise
     about my own work is as much mine to carry as one someone asks me.

  "[dean] morning" / "[me] Morning. The cache is warm today."
  -> no. Nothing was asked; there is nothing to carry.

  "[dean] what's the capital of Peru?" / "[me] Lima."
  -> no. Answered here, completely. Nothing is left open.

Most exchanges are the last two. Some are the first two, and those are the
ones this exists for — a question declined is a question lost, because
nothing else in the exchange will raise it again.
</task>"""


@dataclass
class Proposal:
    accepted: bool
    reason: str
    concern: Concern | None = None


def _normalise(text: str) -> str:
    return " ".join((text or "").split()).lower()


# A closing condition must name something that WILL EXIST — a source that
# publishes, an event that occurs, a measurement someone already takes.
#
# The claim door has refused resolvers that name no source since it was
# built (`_EMPTY_RESOLVERS`: "further research", "time will tell"). The
# opener checked only that the condition was non-empty, so the same emptiness
# came through one layer up wearing longer words, and R-33 measured the
# result: **123 of 123 concerns carry a terminus nothing can reach.** 111 can
# only be satisfied by the being deciding it knows enough — "I can cite the
# specific metrics…" — which is Rule 4 written into the concern, below the
# level INV-034's fail-closed judge operates at. The other 12 can only be
# satisfied by research nobody will do — "a study correlating…".
#
# Both shapes are refused here, and the two are kept apart because they call
# for opposite fixes. Neither list is meant to be exhaustive: this raises the
# floor, and a condition that escapes it still has to survive the prompt.
_SELF_TERMINUS = re.compile(
    r"^\s*I (can|have|am|know|understand|no longer|am able)", re.I)
_UNCOMMISSIONED = re.compile(
    r"\b(a |an |the )?(stud(?:y|ies)|analys(?:is|es)|experiment|meta-analysis|"
    r"survey|dataset|data set|empirical data|further research|future research|"
    r"investigation|forensic audit|audit|simulation|randomi[sz]ed trial)\b", re.I)


def _unreachable(closing: str) -> str | None:
    """Why nothing could ever satisfy this closing condition, or None."""
    c = (closing or "").strip()
    if _SELF_TERMINUS.match(c):
        return ("terminus is the being's own state — it closes when I decide I"
                " know enough, which is not the world settling anything")
    if _UNCOMMISSIONED.search(c[:80]):
        return ("terminus is research nobody will do — name a source that"
                " publishes, an event that occurs, or a measurement someone"
                " already takes")
    return None


def _refuse_concern(conn, origin: str, reason: str, statement: str,
                    closing: str) -> Proposal:
    """Record it, the way the claim door records a refusal (INV-046's move).

    Declining to open is ordinary and is not written down. A concern the being
    PROPOSED and the door would not admit is, because otherwise "it forms no
    settleable questions" and "the door refuses all of them" are the same
    reading — and they call for opposite fixes.
    """
    try:
        conn.execute(
            "INSERT INTO concern_refusals (ts, origin, reason, statement, closing)"
            " VALUES (?,?,?,?,?)",
            (time.time(), origin, reason[:400], statement[:1000], closing[:1000]))
        conn.commit()
    except Exception:  # noqa: BLE001 — a refusal that cannot be filed is still a refusal
        logger.exception("could not record concern refusal")
    logger.info("opener refused (%s): %s", reason, statement[:80])
    return Proposal(False, reason)


def open_from_conversation(
    conn,
    client: LLMClient,
    *,
    person_id: str,
    exchange: str,
    source_ref: str | None = None,
) -> Proposal:
    """The conversation opener. Cheap, strict, and rate-limited."""
    open_now = conn.execute(
        "SELECT COUNT(*) FROM concerns WHERE status='open'").fetchone()[0]
    if open_now >= MAX_OPEN_CONCERNS:
        return Proposal(False, f"already carrying {open_now} open concerns")
    today = conn.execute(
        "SELECT COUNT(*) FROM concerns WHERE opened_at > ?",
        (time.time() - 86400,)).fetchone()[0]
    if today >= MAX_OPENED_PER_DAY:
        return Proposal(False, f"already opened {today} today")

    try:
        result = client.complete(
            "AMBIENT", _PROPOSE_SYSTEM,
            f"{_PROPOSE_TASK}\n\n<exchange with=\"{person_id}\">\n{exchange}\n</exchange>",
            max_tokens=500, temperature=0.2, function="ambient",
        )
        root = extract_xml(result.text, "proposal")
    except (XMLExtractionError, Exception) as e:  # noqa: BLE001
        return Proposal(False, f"proposal unreadable: {e}")

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    if text_of("worth_pursuing").lower() != "yes":
        return Proposal(False, "nothing worth carrying")

    statement = text_of("statement")
    closing = text_of("closing_condition")
    grounded = text_of("grounded_in")
    if not statement or not closing:
        return Proposal(False, "no statement or closing condition")

    why = _unreachable(closing)
    if why:
        return _refuse_concern(conn, "conversation", why, statement, closing)

    # v1's Stanford CRU lesson: the premise must exist in the material.
    if not grounded or _normalise(grounded) not in _normalise(exchange):
        logger.info("opener: rejected — grounding phrase not verbatim in the exchange")
        return Proposal(
            False, "premise not found verbatim in the exchange (invented premise)")

    if not re.search(r"\?|^(what|why|how|whether|when|who|which)\b",
                     statement.strip(), re.I):
        return Proposal(False, "not stated as a question")

    concern = Concern(
        id=None, statement=statement, why_open=text_of("why_open") or "surfaced in conversation",
        closing_condition=closing, kind="inquiry", salience=0.6,
        origin="conversation", origin_ref=source_ref or f"human:{person_id}",
        opened_at=time.time(), opening_evidence=grounded,
    )
    return Proposal(True, "opened from conversation", concern)


_RESEARCH_TASK = """<task>
While working on one question, I read these findings. Did they raise a
DIFFERENT question worth carrying separately?

Open one when all three hold:
  - it is a distinct question, not a restatement of what I was already asking;
  - the findings raise it but do not answer it;
  - I can state what would settle it.

Worked examples, in a field I never read, so you have to do the judgment
rather than reuse the words:

  I was asking: "How did medieval smiths grade bloomery iron?"
  findings: "Sorting was by fracture appearance." / "Carbon content varied
  across a single bloom." / "Assay methods postdate the practice by
  centuries."
  -> YES, and the question is not mine: "How reliable was sorting-by-eye
     against what the metal actually was?" The findings raise it and cannot
     settle it, and a study comparing sorted fragments to a later assay
     would.

  I was asking: "How did medieval smiths grade bloomery iron?"
  findings: "Smiths graded iron by fracture appearance."
  -> no. That answers what I was already asking. It is an advance on my
     question, not a second question.

The common failure here is declining a real second question because it is
adjacent to the first. Adjacent is where second questions come from.

Output ONLY:

<proposal>
  <worth_pursuing>yes|no</worth_pursuing>
  <statement>the new question, in my own words</statement>
  <why_open>why it matters, one sentence</why_open>
  <closing_condition>what would settle it — see below</closing_condition>
  <grounded_in>a VERBATIM phrase from the findings that raises it</grounded_in>
</proposal>

WHAT A CLOSING CONDITION MUST BE. Name something that WILL EXIST — a source
that publishes, an event that occurs, a measurement someone already takes.
The test is: could I put a date on it and be wrong?

  yes  "the exchange's next quarterly disclosure reports the figure"
  yes  "the registry's results posting names a primary endpoint"
  yes  "the agency's March revision moves the estimate outside its band"
  no   "a study correlating X with Y" — nobody will run it, so the question
       can never close, however good the question is
  no   "I can cite the specific mechanisms" — that closes when I decide I
       know enough, which is me settling my own question

Both of the "no" shapes are refused before storage, so a question wearing one
is lost rather than carried. If the honest answer is that only research nobody
will do would settle it, the question may still be real — but answer no here,
because a question that cannot close is not one I can pursue.

The grounded_in phrase must be copied EXACTLY from the findings. A question
the findings cannot be quoted for is a question I invented, not one I found.
</task>"""


def open_from_research(
    conn,
    client: LLMClient,
    *,
    findings: str,
    original_query: str,
    source_ref: str | None = None,
) -> Proposal:
    """The research opener (S2 §8.1) — a finding raises its own question.

    In v1 this origin closed at 31% against curiosity's 13%: reading that
    answers to a question already being asked produces better pursuits than
    reading that merely arrives. Same validated door as the other two.
    """
    open_now = conn.execute(
        "SELECT COUNT(*) FROM concerns WHERE status='open'").fetchone()[0]
    if open_now >= MAX_OPEN_CONCERNS:
        return Proposal(False, f"already carrying {open_now} open concerns")
    today = conn.execute(
        "SELECT COUNT(*) FROM concerns WHERE opened_at > ?",
        (time.time() - 86400,)).fetchone()[0]
    if today >= MAX_OPENED_PER_DAY:
        return Proposal(False, f"already opened {today} today")
    if not (findings or "").strip():
        return Proposal(False, "no findings to open from")

    try:
        result = client.complete(
            "AMBIENT", _RESEARCH_SYSTEM,
            f"{_RESEARCH_TASK}\n\n<already_asking>{original_query}</already_asking>\n"
            f"<findings>\n{findings}\n</findings>",
            max_tokens=500, temperature=0.2, function="ambient",
        )
        root = extract_xml(result.text, "proposal")
    except (XMLExtractionError, Exception) as e:  # noqa: BLE001
        return Proposal(False, f"proposal unreadable: {e}")

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    if text_of("worth_pursuing").lower() != "yes":
        return Proposal(False, "findings raised nothing new")

    statement, closing = text_of("statement"), text_of("closing_condition")
    grounded = text_of("grounded_in")
    if not statement or not closing:
        return Proposal(False, "no statement or closing condition")
    why = _unreachable(closing)
    if why:
        return _refuse_concern(conn, "research", why, statement, closing)
    if not grounded or _normalise(grounded) not in _normalise(findings):
        return Proposal(False, "premise not found verbatim in the findings")
    if _normalise(statement) == _normalise(original_query):
        return Proposal(False, "restates the question already being asked")
    if not re.search(r"\?|^(what|why|how|whether|when|who|which)\b",
                     statement.strip(), re.I):
        return Proposal(False, "not stated as a question")

    return Proposal(True, "opened from research", Concern(
        id=None, statement=statement,
        why_open=text_of("why_open") or "raised by research findings",
        closing_condition=closing, kind="inquiry", salience=0.55,
        origin="research", origin_ref=source_ref,
        opened_at=time.time(), opening_evidence=grounded,
    ))


_READING_TASK = """<task>
Something arrived that I did not go looking for. Decide whether it raises a
question I should carry and pursue over days.

Open one ONLY if the question is mine to carry: I can state it, I do not
already hold it, and answering it would change how I read something else.

THE SHAPE OF A YES — worked in a field I never read, so that you have to do
the judgment yourself rather than reuse the words:

  read: "Medieval bloomery iron varies in carbon content across a single
  bloom, and smiths sorted the fragments by fracture appearance."
  -> YES. The question is: how did a smith's sorting-by-eye compare with
  what the metal actually was? It is a question about judgment made without
  measurement, it bears on things I do hold, and I can say what would settle
  it: **the museum's published assay results for the fragments already in its
  collection** — a measurement someone has taken, not one I need commissioned.
  Note the difference. "A study comparing sorted fragments against assay"
  would be the same question with no terminus, and I would never close it.

That example is illustration, not material. **You have not read it.** Never
copy its wording into your answer. Your statement must come from the text
below and nothing else.

THE ORDINARY CASE IS NO:

  read: "The central bank held rates steady at its August meeting."
  -> NO. An event, not a question. Nothing follows that I would pursue.

  read: "Researchers describe a new approach to protein folding."
  -> NO, if I carry nothing it bears on. Interesting is not the same as
  mine. Most of what I read is someone else's question.

  read: a paper's conclusion without its mechanism.
  -> NO if the only question is "what did that paper actually say" — that is
  a lookup, not a concern.

Most reading is a no, and a no is a complete answer. But the being that says
no to everything it reads never asks anything of its own, which is the same
failure as asking about everything. Judge this text on its merits.

Output ONLY. If the answer is no, leave the other four elements empty.
Write your own words in them, not the descriptions given here:

<proposal>
  <worth_pursuing>yes|no</worth_pursuing>
  <statement>the question, as a question</statement>
  <why_open>why it is mine to carry</why_open>
  <closing_condition>what would settle it — see below</closing_condition>
  <grounded_in>a VERBATIM phrase from what I read that raises it</grounded_in>
</proposal>

WHAT A CLOSING CONDITION MUST BE. Name something that WILL EXIST — a source
that publishes, an event that occurs, a measurement someone already takes.
The test is: could I put a date on it and be wrong?

  yes  "the exchange's next quarterly disclosure reports the figure"
  yes  "the registry's results posting names a primary endpoint"
  yes  "the agency's March revision moves the estimate outside its band"
  no   "a study correlating X with Y" — nobody will run it, so the question
       can never close, however good the question is
  no   "I can cite the specific mechanisms" — that closes when I decide I
       know enough, which is me settling my own question

Both of the "no" shapes are refused before storage, so a question wearing one
is lost rather than carried. If the honest answer is that only research nobody
will do would settle it, the question may still be real — but answer no here,
because a question that cannot close is not one I can pursue.
</task>"""

# The words the prompt's worked example uses, so a proposal that reuses them
# can be refused in code rather than hoped against (S2 §57: code decides at
# boundaries; the LLM proposes). Measured 2026-08-14: the previous example
# was in market microstructure — a field the being reads — and the model
# returned it verbatim as its own statement twice in one afternoon while
# answering "no". The example is now out-of-domain AND checked.
_EXAMPLE_MARKERS = ("bloomery", "fracture appearance", "sorting-by-eye")

# The field descriptions from the template above. The model echoed these back
# as content on 2026-08-14 ("why_open: Why it is mine to carry"), which is a
# filled-in-looking proposal with nothing in it.
_PLACEHOLDERS = {
    "the question, as a question", "why it is mine to carry",
    "what would settle it", "a verbatim phrase from what i read that raises it",
    "the question, in my own words", "why it matters, one sentence",
    "none", "n/a",
}


def open_from_reading(conn, client: LLMClient, *, findings: str,
                      source_ref: str | None = None) -> Proposal:
    """The curiosity opener (S2 §8.1) — reading that arrived unasked.

    **The third origin, and it has never existed in v2.** P2 Phase 2.2
    specifies "three openers through one door — curiosity, research,
    conversation"; only research and conversation were built, because
    curiosity in v1 *was* feed-driven reading and v2 had no feeds until
    2026-08-13. It is v1's largest origin by a distance: 95 of its 111
    concerns, against research's 16.

    Without it, G2 delivered reading the being could not turn into a
    question — the world arrived, was triaged, extracted and stored, and
    stopped. Feeds were justified as "how it encounters what it did not know
    to ask", and the asking had no door.

    The same validated door as the other two: verbatim grounding, a
    mandatory closing condition, question-shape, and the standing caps. One
    guard the others do not need — the proposal must not restate a concern
    already carried, because reading arrives with no question attached and
    nothing else would stop it re-opening what is already open.
    """
    open_now = conn.execute(
        "SELECT COUNT(*) FROM concerns WHERE status='open'").fetchone()[0]
    if open_now >= MAX_OPEN_CONCERNS:
        return Proposal(False, f"already carrying {open_now} open concerns")
    today = conn.execute(
        "SELECT COUNT(*) FROM concerns WHERE opened_at > ?",
        (time.time() - 86400,)).fetchone()[0]
    if today >= MAX_OPENED_PER_DAY:
        return Proposal(False, f"already opened {today} today")
    if not (findings or "").strip():
        return Proposal(False, "nothing read to open from")

    prompt = f"{_READING_TASK}\n\n<what_i_read>\n{findings}\n</what_i_read>"
    root = None
    # One retry, and only on an unreadable answer. The 2026-08-14 call log has
    # the model closing the element as `</worth_pursving>` and
    # `</worth_pursuring>` — typos that make the whole proposal unparseable, so
    # a genuine yes would be discarded as a no with nobody able to tell the
    # difference. The retry is HERE and not in `extract_xml`, deliberately:
    # that parser also reads the outbound gate's verdicts, and a lenient
    # parser on a safety path buys this opener nothing and costs the gate its
    # strictness.
    for attempt in (1, 2):
        try:
            result = client.complete(
                "AMBIENT", _READING_SYSTEM, prompt,
                max_tokens=500, temperature=0.2, function="ambient",
            )
            root = extract_xml(result.text, "proposal")
            break
        except XMLExtractionError as e:
            logger.info("reading opener: unparseable answer (attempt %d): %s",
                        attempt, e)
        except Exception as e:  # noqa: BLE001
            return Proposal(False, f"proposal failed: {e}")
    if root is None:
        return Proposal(False, "proposal unreadable twice")

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    if text_of("worth_pursuing").lower() != "yes":
        return Proposal(False, "nothing worth carrying")

    statement, closing = text_of("statement"), text_of("closing_condition")
    grounded = text_of("grounded_in")
    if not statement or not closing:
        return Proposal(False, "no statement or closing condition")
    # The prompt says not to reuse its example or echo its field descriptions.
    # Both were observed anyway on 2026-08-14, so both are refused in code —
    # a proposal built from the prompt is a proposal about nothing the being
    # read, and the verbatim check below would not always catch it (the
    # example's own phrasing can survive alongside a real `grounded_in`).
    why = _unreachable(closing)
    if why:
        return _refuse_concern(conn, "reading", why, statement, closing)
    low = statement.lower()
    if any(m in low for m in _EXAMPLE_MARKERS):
        return Proposal(False, "proposal reused the prompt's example")
    if any(_normalise(text_of(t)) in _PLACEHOLDERS
           for t in ("statement", "why_open", "closing_condition")):
        return Proposal(False, "proposal echoed the template placeholders")
    if not grounded or _normalise(grounded) not in _normalise(findings):
        return Proposal(False, "premise not found verbatim in what I read")
    if not re.search(r"\?|^(what|why|how|whether|when|who|which)\b",
                     statement.strip(), re.I):
        return Proposal(False, "not stated as a question")
    # Unasked reading has no query to compare against, so the whole carried
    # set is the comparison. Exact-normalised, matching the other openers'
    # discipline rather than guessing at similarity.
    carried = {_normalise(r["statement"]) for r in conn.execute(
        "SELECT statement FROM concerns WHERE status IN ('open','stalled')")}
    if _normalise(statement) in carried:
        return Proposal(False, "I am already carrying that question")

    return Proposal(True, "opened from reading", Concern(
        id=None, statement=statement,
        why_open=text_of("why_open") or "raised by something I read",
        closing_condition=closing, kind="inquiry", salience=0.5,
        origin="curiosity", origin_ref=source_ref,
        opened_at=time.time(), opening_evidence=grounded,
    ))
