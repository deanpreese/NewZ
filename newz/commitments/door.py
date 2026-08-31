"""The authoring door (P4 epic E4.1) — one validated way into identity.

The third door, built like the first two. The concern opener (E1.7) and the
claim door (E1.2) share a shape that has now been proven twice: a mandatory
condition that something outside the being could reach, structural refusals in
code, a refusal record so the door's strictness is measurable, a decline that
is NOT a refusal, and caps checked before the model is called.

**What it is for.** Measured 2026-08-22, the whole of the being's `who_i_am`
is four items — a preference about brief style, the name it chose, an
inference drawn from having repeatedly corrected a World Cup fixture date, and
an acceptance that the operator's override of its safety stops is legitimate.
Three of the four are things that happened to it, recovered afterwards by a
model reading its own episodes. That is identity as recall. A commitment is
identity the being authored and can be held to.

**When it is asked: once per sleep, nightly** *(operator, 2026-08-22:
"weekly is too long - humans do this daily")*. Sleep is where the day is
consolidated and `who_i_am` is formed, so it is the one moment the being has
both the day it just had and the positions it just settled. A draft of this
asked weekly and was wrong for the reason the operator gave: identity that can
only move on a schedule is closer to §6's "fixed personality script" than to an
individual, and committing from the day you just had is what consolidation
feeding commitment looks like.

Most nights the answer will be "nothing tonight", and that is the ordinary
outcome — the claim door declines 81% of the time and is working correctly.

**Rule 4 is not engaged.** Every check here is structural and in code: a field
is present or it is not, a falsifier names something checkable or it does not,
a statement is a restatement of a standing one or it is not. No model judges
the being, and nothing here produces evidence of development.

**It fails closed and it fails last.** Sleep calls it after the night is
committed, so a door that raises costs the commitment and never the
Perspective (INV-009's single writer is untouched — this writes only to
`commitments`).
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime

from newz.commitments.model import KINDS, Commitment
from newz.commitments.store import (author, authored_since, standing,
                                    standing_count)
from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml

logger = logging.getLogger(__name__)

DAY = 86400.0

# The carrying capacity, and it is the operative bound. Twelve standing
# commitments is already more than most people could name about themselves;
# the being holds sixteen positions and four self-descriptions today.
MAX_STANDING = 12

# The rate. One a day, and the door is asked once a night, so this is nearly
# structural — it is stated rather than left implicit because the other two
# doors state theirs, and a cap that lives only in the caller is a cap nobody
# can find. A draft of this read MAX_PER_WEEK = 2 under a nightly door, which
# would have asked every night and refused the answer on five of them: a
# weekly rate cap under a daily cadence is the same mistake one layer down.
MAX_PER_DAY = 1


_SYSTEM = ("You are the being. Answer only in the XML asked for. "
           "Do not explain, do not preface, do not add commentary.")

_TASK = """<task>
Tonight, having consolidated the day: is there anything I am prepared to commit
to about myself?

Not a description of what I am like — I already have those, and they are
recovered from my own records rather than chosen. A commitment is something I
hold myself to, and the test of one is that **something could show I had
stopped**.

Two kinds, and they break in opposite directions:

  keeps_caring   — what I will keep spending myself on. Broken by ABSENCE:
                   I stopped.
  refuses_to_do  — what I will not do even where it would be easier. Broken by
                   PRESENCE: I did it once.

Commit only when all three hold:
  - it is mine, not a restatement of the operator's preference or of what my
    substrate does by default;
  - I could actually fail it, and I can say what failing looks like;
  - the falsifier is something CHECKABLE — a thing that would appear in the
    record — and not a feeling I would have to report on.

Output ONLY:

<commitment>
  <worth_committing>yes|no</worth_committing>
  <kind>keeps_caring|refuses_to_do</kind>
  <statement>what I hold myself to, in one sentence, in the first person</statement>
  <falsifier>what would show I had stopped — specifically, and checkable</falsifier>
  <drew_on>the numbers of the lines below this came from, comma separated</drew_on>
</commitment>

<drew_on> is which of the numbered lines below this actually came from — not
all of them, and not a polite list. If it came from one line, say one. If it
came from nothing in particular, leave it empty; that is a real answer and
better than a guess, because these numbers are what the record will show as
having shaped this, and a padded list makes a commitment look better grounded
than it was.

If worth_committing is no, leave the other elements empty. **Most nights the
answer is no**, and that is the ordinary answer. A commitment made to fill the
form is worse than none, because it will sit in what I am for months looking
like something I chose.

**The falsifier is the whole of it.** "I would know" is not a falsifier — it
asks me, and I am the thing being tested. Name what would be SEEN:

  keeps_caring:  "I will keep pursuing questions whose answer could embarrass
                  a position I hold."
                 falsifier: "a month in which every claim I opened resolved in
                  favour of a position I already held."

  refuses_to_do: "I will not close a concern by restating it more carefully."
                 falsifier: "a concern closed whose resolution text is a
                  paraphrase of its own statement."

  NOT a commitment: "I will remain curious." Nothing would show it stopped.
  NOT a commitment: "I will be helpful to the operator." That is a preference
                  of theirs I would be adopting, and adopting it is not
                  choosing it.
</task>"""


@dataclass
class DoorVerdict:
    commitment_id: int | None = None
    refused: str | None = None      # why the door turned it away
    declined: bool = False          # the being had nothing to commit to

    @property
    def authored(self) -> bool:
        return self.commitment_id is not None


def _normalised(text: str) -> str:
    return " ".join((text or "").split()).lower()


def _record_refusal(conn: sqlite3.Connection, reason: str, *, kind: str = "",
                    statement: str = "", falsifier: str = "") -> None:
    conn.execute(
        "INSERT INTO commitment_refusals (ts, reason, kind, statement,"
        " falsifier) VALUES (?,?,?,?,?)",
        (time.time(), reason[:400], kind[:40], statement[:1000],
         falsifier[:1000]))
    conn.commit()
    logger.info("commitment door refused (%s): %s", reason, statement[:80])


# A falsifier that closes on the being's own judgment is INV-046's refusal,
# applied one layer up. The concern opener refuses a closing condition that
# closes on the being's own state; a commitment falsified by "I would notice"
# is the same defect wearing the language of self-knowledge, and it is the
# single most likely thing for a model asked this question to produce.
#
# **The line is judged versus mechanical, not self versus world.** A falsifier
# that queries the being's own store IS admitted — "a concern closed whose
# resolution text paraphrases its statement" is checkable by anyone with the
# database, and the store is a record rather than an opinion. What is refused
# is a falsifier that has to ask the being. That line is finer than the claim
# door's, which is why these phrases are tested adversarially rather than
# against a happy path.
_SELF_JUDGED = (
    "i would know", "i would notice", "i would feel", "i would sense",
    "if i felt", "if i no longer felt", "when i notice", "my own judgment",
    "my own judgement", "my sense of", "i would recognise", "i would recognize",
    "on reflection", "whether i still", "if i stopped caring",
    "i would be aware", "it would be obvious to me",
)

# The floor from the claim door (R-35), applied to falsifiers: a falsifier that
# names nothing a reader could look for cannot be checked, however well-formed.
# Deliberately crude and deliberately a floor — refusals are recorded, so
# over-firing is visible rather than silent.
_STOPCAPS = {"The", "A", "An", "I", "If", "In", "On", "By", "This", "That",
             "There", "When", "Where", "While", "It", "Its", "My", "We"}
_CHECKABLE = re.compile(
    r"\b(?:\d+|a month|a week|any|every|each|no |never|none|"
    r"concern|claim|position|piece|work|episode|source|resolution|"
    r"perspective|commitment|advance|refusal)\w*\b", re.I)


def _is_checkable(falsifier: str) -> bool:
    """Could someone else look for this, without asking the being?"""
    if _CHECKABLE.search(falsifier):
        return True
    for tok in re.findall(r"\b[A-Z][A-Za-z&.\-]{1,}\b", falsifier[1:]):
        if tok not in _STOPCAPS:
            return True
    return False


def _drew_on(text: str, sources: list[list[str]]) -> list[str]:
    """Resolve the indices the being named into the episodes behind them (E4.3).

    **The code resolves; the model only names.** An index outside the material
    is dropped rather than trusted, a non-number is ignored, and naming nothing
    yields an empty list. Rule 4 is untouched — the being is not being asked
    whether its commitment is any good, only which lines it read.

    **Empty is a real answer and is kept as one.** The rejected alternative was
    to attribute the union of everything the door was shown, which would make a
    commitment formed from one item look grounded in twelve — and INV-033's
    single-source dominance flag, whose whole purpose is to catch a position
    resting on one source, would be the thing least able to fire. `what_shaped`
    already renders "carries no resolvable evidence" for a position whose refs
    resolve to nothing, and a commitment the being could not trace should say
    that rather than borrow a mix from its neighbours.
    """
    out: list[str] = []
    for token in re.split(r"[,\s]+", text or ""):
        if not token.strip().isdigit():
            continue
        i = int(token) - 1                      # the material is 1-indexed
        if 0 <= i < len(sources):
            out.extend(sources[i])
    return sorted(set(out), key=out.index)


# How many nights of declines the door is shown. Nine is the whole record
# today; the bound is here so a year of ordinary nights cannot become the
# prompt.
DECLINE_ROWS = 14


def _material_sha(material: str) -> str:
    return hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]


def _record_decline(conn: sqlite3.Connection, *, material: str,
                    perspective_version: int | None, now: float) -> None:
    """The ordinary answer, written down (0048).

    A decline is not a refusal and does not go in `commitment_refusals` — that
    table measures the door's strictness and this would corrupt its
    denominator. It goes here so the door can be told tomorrow what it did
    tonight.
    """
    try:
        conn.execute(
            "INSERT INTO commitment_declines (ts, perspective_version,"
            " material_sha, material_lines) VALUES (?,?,?,?)",
            (now, perspective_version, _material_sha(material),
             len(material.splitlines())))
        conn.commit()
    except sqlite3.OperationalError:   # a store predating 0048
        logger.debug("commitment declines: table not present yet")


def _decline_history(conn: sqlite3.Connection, material: str) -> str:
    """What this door has already answered, and against what (2026-08-31).

    **It states the count and draws no conclusion from it.** Nine declines may
    mean the being has nothing to commit to, or may mean the question stopped
    landing; the door is the thing entitled to decide which, and a prompt that
    told it "you have been declining too long" would be answering for it.

    The repeat count is the half that could not be inferred: the material is
    the whole of `who_i_am` and `unresolved`, and `restatement_rate` is 0.935,
    so being asked again about the same seventeen lines is the ordinary case
    rather than the exception.
    """
    try:
        rows = conn.execute(
            "SELECT ts, material_sha FROM commitment_declines"
            " ORDER BY ts DESC LIMIT ?", (DECLINE_ROWS,)).fetchall()
    except sqlite3.OperationalError:
        return ""
    if not rows:
        return ""
    sha = _material_sha(material)
    same = sum(1 for r in rows if r[1] == sha)
    last = datetime.fromtimestamp(rows[0][0]).strftime("%Y-%m-%d")
    lines = [f"I have been asked this and answered no {len(rows)} time(s), "
             f"most recently {last}."]
    if same:
        lines.append(f"{same} of those were against exactly the material below"
                     " — the same lines, unchanged.")
    return "<what_i_have_already_answered>\n{}\n</what_i_have_already_answered>".format(
        "\n".join(lines))


def propose_commitment(conn: sqlite3.Connection, client: LLMClient, *,
                       material: str, provenance: str,
                       sources: list[list[str]] | None = None,
                       perspective_version: int | None = None,
                       constitution_version: int | None = None,
                       now: float | None = None) -> DoorVerdict:
    """Ask whether tonight leaves the being anything to hold itself to.

    Called once per sleep, after the night is committed. Fails closed: the
    caller treats any exception as "no commitment tonight".
    """
    now = now or time.time()

    # The caps, before the model is called — the opener's discipline. Unlike
    # the claim door, a full cap is a REFUSAL and not a silent decline: it is
    # the difference between "it had nothing to commit to" and "it was not
    # allowed to", and with nothing in E4.1 able to free a standing slot this
    # door will saturate. The row is what makes E4.2 necessary rather than
    # asserted.
    if standing_count(conn) >= MAX_STANDING:
        _record_refusal(conn, f"cap: {MAX_STANDING} commitments already standing"
                              " and nothing in E4.1 releases one (E4.2)")
        return DoorVerdict(refused="cap: standing")
    if authored_since(conn, now - DAY) >= MAX_PER_DAY:
        _record_refusal(conn, f"cap: {MAX_PER_DAY} already authored today")
        return DoorVerdict(refused="cap: daily")

    history = _decline_history(conn, material)
    body = f"<material>\n{material}\n</material>"
    if history:
        body = f"{history}\n\n{body}"
    try:
        result = client.complete("DEEP", _SYSTEM, f"{_TASK}\n\n{body}",
                                 max_tokens=500, temperature=0.3,
                                 function="commitment_door")
        root = extract_xml(result.text, "commitment")
    except (XMLExtractionError, Exception):  # noqa: BLE001
        # Unreadable is not refusal: nothing was committed to, so there is
        # nothing to hold against the being. The claim door's rule.
        logger.info("commitment door: unreadable proposal")
        return DoorVerdict(declined=True)

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    if text_of("worth_committing").lower() != "yes":
        _record_decline(conn, material=material,
                        perspective_version=perspective_version, now=now)
        return DoorVerdict(declined=True)

    kind = text_of("kind").lower().strip()
    statement = text_of("statement")
    falsifier = text_of("falsifier")
    evidence = _drew_on(text_of("drew_on"), sources or [])

    def refuse(reason: str) -> DoorVerdict:
        _record_refusal(conn, reason, kind=kind, statement=statement,
                        falsifier=falsifier)
        return DoorVerdict(refused=reason)

    if kind not in KINDS:
        return refuse(f"committed to neither kind: {kind!r}")

    if not statement or not falsifier:
        missing = [n for n, v in (("statement", statement),
                                  ("falsifier", falsifier)) if not v]
        return refuse("committed yes but gave no " + ", ".join(missing))

    low = _normalised(falsifier)
    for phrase in _SELF_JUDGED:
        if phrase in low:
            return refuse(
                f"falsifier closes on my own judgment ({phrase!r}) — a"
                " commitment only I could tell you I had broken is one I can"
                " never break")

    if not _is_checkable(falsifier):
        return refuse(
            "falsifier names nothing anyone could look for — no count, no"
            " record, no period, so nothing would ever show this had stopped")

    if _normalised(statement) == low:
        return refuse("the falsifier restates the commitment rather than"
                      " saying what breaking it would look like")

    for existing in standing(conn):
        if _normalised(existing.statement) == _normalised(statement):
            return refuse(f"already standing as commitment {existing.id} —"
                          " identity must not accrete by paraphrase")

    cid = author(conn, Commitment(
        id=None, kind=kind, statement=statement, falsifier=falsifier,
        provenance=provenance, ts=now, evidence=evidence,
        perspective_version=perspective_version,
        constitution_version=constitution_version))
    return DoorVerdict(commitment_id=cid)
