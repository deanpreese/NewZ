"""The claim door (P3 epic E1.2) — one validated way in.

The concern opener's discipline, applied one level down. A concern needs a
closing condition or it is not pursuable (INV-034); a claim needs a resolution
condition, a named resolver and a date, or it is not refusable. The being has
been right about nothing in particular for its whole life, because nothing it
holds was ever stated in a form the world could contradict.

**A claim is not a summary of an advance.** The advance says what the being now
holds; the claim says what must be observed if that is true, and when. If the
distinction collapses, the door admits restatements with dates on them and the
resolver settles tautologies.

The door refuses four things and records every refusal (0024):

  * a claim with no statement, condition, resolver or date;
  * a date it cannot read, one already past, or one so far out that being
    wrong costs nothing within the life of the project;
  * a resolver that is not a source — "time will tell", "the news";
  * a resolver that is the being's own substrate (Rule 4, enforced in the
    store).

Declining is not refusal. "Nothing here is worth claiming" is the ordinary
answer and is not written down, exactly as triage keeping nothing is ordinary.
What gets written down is a claim the being made and the door would not admit,
because P3's decision rule for Phase 1 turns on telling "it makes no falsifiable
claims" apart from "the door rejects them all".
"""

from __future__ import annotations

import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime

from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml
from newz.resolutions.model import Claim
from newz.resolutions.store import UnsettleableClaim, open_claim

logger = logging.getLogger(__name__)

DAY = 86400.0
# A claim due tomorrow about something already in the dossier is not a
# prediction, and a claim due in three years cannot cost anything within the
# life of this project — S1-E needs at least one position to change BECAUSE the
# world contradicted it, and a claim that outlives the question is not that.
MIN_HORIZON_DAYS = 2
# **365 was permission the being took, and the prompt's own example was 42.**
# Measured 2026-08-22, every claim it had ever written, in days:
#
#     120  120  120  120  120  128  180  180  180  365  365  365
#
# Minimum 120, median 180. `claim_refusals` held ZERO rows, so the ceiling had
# never once been touched: the long dates were volunteered, not forced. The
# door showed it a six-week worked example and told it a year was allowed, and
# it took the permission.
#
# **What that cost is not only that S1-E waits until December.** `resolver.py`
# selects `due_at <= now`, so with nothing due, `resolve_claim` had never run
# ONCE in life — the fetch, the VERBATIM check (INV-047), the 4-attempt honest
# failure path, the cost through INV-031, the release through INV-025, and the
# one `world`-provenance episode sleep ever sees. All tested, none exercised,
# first execution scheduled for 2026-12-18. The writing rhythm's re-read path
# crashed the first time it did something real; Phase 1's path is five times
# larger.
#
# **Why 45 and not the 120 first instructed.** 120 refuses three of the twelve
# live claims and permits nine, leaving the median at 180 — it stops the worst
# and creates no short claims, because the being's SHORTEST claim ever written
# is 120. The point is not to trim outliers; it is that consequence has to
# arrive often enough to be a loop rather than an anecdote.
#
# **The cap alone would produce refusals, not shorter claims** — the door
# refuses an out-of-range horizon and does not ask again. So the prompt does
# the work and this only enforces it; the two must never ship apart. If
# `claim_refusals` fills with horizon reasons and claims stop opening, the cap
# is wrong for this being's subjects: revert to 90, never to 365, and record
# which subjects could not reach a near source.
MAX_HORIZON_DAYS = 45
# The opener's discipline: a carrying cap so the store cannot fill with
# commitments nobody will ever look at, and a daily rate limit so a
# miscalibrated door cannot do it in one afternoon. Both are deliberately
# looser than the concern caps, because a claim is cheaper to hold than a
# concern — it costs nothing until its date arrives.
MAX_OPEN_CLAIMS = 40
MAX_OPENED_PER_DAY = 4

# E1.9, 2026-08-28. A retrodiction settles on the next resolver pass, so its
# residency in the open pool is minutes and Little's law gives it no inventory
# cost — `MAX_OPEN_CLAIMS` is a cap on UNRESOLVED inventory and counts
# forecasts alone. What still applies is the rate: the reason the daily cap
# exists is that "a miscalibrated door cannot do it in one afternoon", and a
# door miscalibrated about the past is no better than one miscalibrated about
# the future.
#
# **Why 4 here too, and not more.** The being opens 3.0 claims a day against a
# cap of 4 and presses against it on its productive days, so 4 is the rate it
# has actually shown rather than a number chosen to make the arithmetic in
# E1.9's proposal come out. If retrodictions turn out to be easy to write and
# the cap binds every day, that is a measurement worth having before the cap
# moves — and the refusal rows below are what make it visible.
MAX_RETRODICTIONS_PER_DAY = 4

# Resolvers that name no source. Each of these produces a claim that stays
# open forever while looking settled-in-principle, which is the failure mode
# the whole table exists to prevent. Kept short and literal for the reason
# check_resolver is narrow: a long list of banned words teaches the being to
# phrase around the door rather than to name a source.
_EMPTY_RESOLVERS = (
    "time will tell", "the future", "future events", "eventually",
    "the news", "the internet", "further research", "future research",
    "common sense", "we will see", "we'll see", "history",
)

# A resolver the being has not identified yet. Measured 2026-08-23, the first
# night under the 45-day ceiling: the door admitted
#
#   "European Commission Implementing Regulation (EU) 2023/XXXX on the DSA"
#   "The specific industry report ... (title to be identified upon release)"
#
# Neither names a document anyone could fetch. R-35 built `_names_something`
# for exactly this and pointed it at the STATEMENT, so a well-named statement
# carried an unnamed resolver straight through.
_PLACEHOLDER = re.compile(
    r"\bXXXX+\b|\bTBD\b|\bplaceholder\b"
    r"|to be (?:determined|identified|confirmed|announced|named|decided)",
    re.I)

# **A source cannot speak sooner because the ceiling moved.** The night the
# horizon dropped to 45 days, the being wrote:
#
#   claim 10  120d  2026-08-22  "Meta's Quarterly Transparency Report"
#   claim 14   30d  2026-08-23  "Meta's Quarterly Transparency Report"
#
# Same resolver, and claim 10 even named the quarter it settled in. Nothing
# about Meta changed; the permitted range did, and the being filled the field
# to fit — R-31's failure one layer up, where the schema compels a number the
# model cannot know. The prompt asked it to reach for a NEARER SOURCE and it
# reached for a nearer date instead.
#
# So the door checks the one thing it can: a resolver that says how often it
# publishes is refused when the horizon is shorter than that. Narrow and
# literal, for `check_resolver`'s reason — a long list teaches the being to
# phrase around the door rather than to find a source that speaks sooner.
#
# **This deliberately makes some subjects unclaimable**, and that is the point.
# An annual source cannot settle inside a 45-day ceiling at all, so the refusal
# is recorded and `tools/claims.py --refused` becomes the evidence for whether
# 45 is too tight for what this being thinks about. The proposal's falsifier 2
# asked for exactly that read and had no way to produce it while the being
# could satisfy the range by misdating.
#
# **The known hole, stated rather than patched:** the being can pass by dropping
# the word "quarterly" from a quarterly source's name. That makes the resolver
# less searchable, which is a different defect the resolver pass will surface as
# an honest failure rather than a false settlement. Watch `claim_refusals` for
# cadence reasons falling to zero while long-cadence subjects keep appearing.
_CADENCE = (
    (re.compile(r"\b(?:annual|yearly|per annum|year-end|10-K)\b", re.I),
     365, "annual"),
    (re.compile(r"\b(?:quarterly|quarter|Q[1-4]\b|10-Q)\b", re.I),
     90, "quarterly"),
    (re.compile(r"\bmonthly\b", re.I), 28, "monthly"),
    (re.compile(r"\b(?:weekly|week)\b", re.I), 7, "weekly"),
)


_SYSTEM = (
    "You decide whether what a digital being has just established commits it "
    "to anything the world could later prove wrong. You respond with XML "
    "only. Most thinking commits you to nothing checkable — and some of it "
    "genuinely does, so declining every time is as wrong as claiming every "
    "time."
)

# Passing case first and worked, per the lesson this repository has paid for
# repeatedly: with a strict-only frame the model refuses everything, and here
# refusal is indistinguishable from honest restraint.
_TASK = """<task>
I have just established something while working on a concern. Does it commit
me to anything the world will later show to be true or false?

A claim is NOT a summary of what I established. It is what must be OBSERVED if
what I established is right — stated specifically enough to fail, pointed at a
source that will say, and dated.

Claim it when all four hold:
  - something specific follows from what I hold, about the world and not about
    my own thinking;
  - a named, existing source will show whether it happened;
  - there is a date by which that source will have spoken;
  - I could be wrong. If nothing would surprise me, there is no claim here.

Output ONLY:

<claim>
  <worth_claiming>yes|no</worth_claiming>
  <statement>what will be observed, specifically</statement>
  <settles_when>what exactly would show it true or false</settles_when>
  <resolver>the named source that will show it</resolver>
  <due_in_days>a whole number of days from today, between 2 and 45 — or 0, see below</due_in_days>
  <could_be_wrong>what the OTHER outcome looks like — what I would see if this
                  turns out false</could_be_wrong>
</claim>

If worth_claiming is no, leave the other elements empty.

<could_be_wrong> is the check on whether this is a claim at all. If I cannot
describe the world in which it comes out false, I have not predicted anything —
I have described something already settled, or something that could not have
gone otherwise. Say what the source would show instead. "It would not happen"
is not an answer; say what WOULD.

**Name what you are talking about.** A claim the reader cannot look up cannot
be checked: the source will be searched for, and a statement with no name, no
place, no date and no identifier gives it nothing to search. "The agency's
figure will differ from the market's value" names neither agency nor market and
is refused. "The BLS September Employment Situation Summary" names one.

**A claim can be about what is ALREADY the case and I do not yet know it.**
If the source has already spoken — the release is out, the report is filed, the
figure is published — and I am asserting what it says without having read it,
then `due_in_days` is **0** and it settles on the next pass instead of in a
month. That is not a weaker claim: I can be wrong about what the record says,
and `could_be_wrong` still has to describe the world in which the source shows
otherwise. It is a stronger one, because I find out.

The one thing it may not be is a restatement of something I have already read.
If I already know the answer because it is in my own dossier, there is nothing
to find out and the honest answer is `no`.

`due_in_days` is a HORIZON, not a date: how long until the source will have
spoken. Today's date is given to you above — use it when the statement itself
needs to name a period, and never guess one.

**Reach for the nearest source that will have spoken.** If what I hold is
right, something small should be observable soon — not only at the end. A
thesis about where a market, a rule or a field is going has interim
checkpoints: the next weekly release, the next monthly print, the next
scheduled filing, the next quarterly report. Claim the nearest one that would
still surprise me if it went the other way.

A claim I cannot bring inside the window is usually a claim about the wrong
observable, not a claim that needs longer. Being wrong in six weeks teaches me
something; being wrong in a year happens to someone I have already stopped
being. If nothing my sources will say within 45 days could bear on this, the
honest answer is `no` — declining costs nothing.

**Moving the date does not move the source.** A quarterly report does not
arrive next month because I would like it to. If the only source that could
settle this publishes quarterly or annually, then either I find a different
observable that appears sooner — a filing, a docket, a weekly release, a
scheduled hearing — or there is no claim here today. Saying a quarterly source
will have spoken in thirty days is not a short claim, it is a wrong one, and it
will fail in thirty days having taught me nothing.

**Name a document that exists.** The resolver has to be something someone could
go and fetch. "The specific report, title to be identified" and an identifier
with XXXX in it are not sources — if I cannot name it yet, I cannot claim
against it yet.

Worked examples, in fields I do not work in, so you have to do the judgment
rather than reuse the words.

  established: "Exchange-reported open interest overstates collateralised
  positions, because netting conventions differ between venues."
  -> YES.
     statement: The CFTC's Commitments of Traders report for the September
     contract will show aggregate open interest at least 10% below the
     exchange's own published figure for the same date.
     settles_when: The COT release for that week is published and the two
     figures are compared.
     resolver: CFTC Commitments of Traders weekly report
     due_in_days: 42
     Being wrong here costs me the position that produced it. That is the
     point.

  established: "The clinic's own trial registry entry contradicts the press
  release on primary endpoint."
  -> YES. The registry is a source, the contradiction is checkable, and the
     trial's reporting deadline is a date.

  established: "Improvisation resists notation in a way that makes recorded
  practice a poor guide to live practice."
  -> no. True or false, nothing in the world will announce it. Do not invent
     a proxy measurement to force a claim out of it — a bad claim is worse
     than none, because it will be settled and the settlement will mean
     nothing.

  established: "I have refined my view: the vulnerability is a liquidity
  freeze rather than a solvency gap."
  -> no. That is a restatement of what I now think, not an observation the
     world will make. If I cannot say what would be SEEN, there is no claim.
</task>"""


@dataclass
class DoorVerdict:
    claim_id: int | None = None
    refused: str | None = None      # why the door turned it away
    declined: bool = False          # the being said nothing was worth claiming

    @property
    def opened(self) -> bool:
        return self.claim_id is not None


def _normalised(text: str) -> str:
    return " ".join((text or "").split()).lower()


def _record_refusal(conn: sqlite3.Connection, concern_id: int | None,
                    reason: str, *, claim: str = "", condition: str = "",
                    resolver: str = "", due_text: str = "") -> None:
    conn.execute(
        "INSERT INTO claim_refusals (ts, concern_id, reason, claim, condition,"
        " resolver, due_text) VALUES (?,?,?,?,?,?,?)",
        (time.time(), concern_id, reason[:400], claim[:1000], condition[:1000],
         resolver[:400], due_text[:100]))
    conn.commit()
    logger.info("claim door refused (%s): %s", reason, claim[:80])


# A resolver settles a claim only by finding a VERBATIM quote in material it
# fetched (INV-047), so a claim that gives a search nothing to key on cannot be
# settled however well-formed it is. R-35 measured this: the door admitted
#
#   "The official agency's final published figure for the wildfire acreage will
#    differ from the prediction market's resolved value by more than 5%."
#
# — which names no agency, no fire, no market and no year. The resolver ran,
# read a document in full, and reported it could not find "the specific
# official agency's final published figure ... for the specific event in
# question". Settleable in grammar, unsettleable in fact.
#
# The test is deliberately crude and is a floor, not a wall: a proper noun, a
# year, or an identifier — something a search can be built around. Refusals are
# recorded, so over-firing is visible rather than silent.
_STOPCAPS = {"The", "A", "An", "I", "If", "In", "On", "By", "This", "That",
             "There", "When", "Where", "While", "It", "Its", "My", "We"}
_IDENTIFIER = re.compile(r"\b(?:\d{4}|[A-Z]{2,}[-\s]?\d+|\$[\d,.]+)\b")


def _names_something(claim: str) -> bool:
    """Could a search be built from this? A proper noun, a year, an id."""
    if _IDENTIFIER.search(claim):
        return True
    for tok in re.findall(r"\b[A-Z][A-Za-z&.\-]{1,}\b", claim[1:]):
        if tok not in _STOPCAPS:
            return True
    return False


def _parse_due(text: str, now: float) -> tuple[float | None, str | None]:
    """A horizon in days, or the reason it is not usable as one.

    **Why a horizon and not a date** (R-31, 2026-08-19). This asked for an
    absolute `YYYY-MM-DD` and never told the model what today was. Asked
    directly, at temperature 0, every role answers "I do not have access to
    real-time information, so I cannot provide today's date" — so a `yes`
    verdict had no compliant way to fill the field, and filled it from the
    training prior instead: `<due>2024-12-31</due>` against a real date of
    2026-08-19. Every well-formed claim the being ever made was then refused
    for being ~600 days in the past, and recorded against it as though it had
    committed to something already settled.

    The schema, not the model, was the fault. It compelled the fabrication of
    a fact the model had explicitly disclaimed — which the constitution's own
    calibration-001 and don't-fabricate-memory-001 forbid, leaving no legal
    answer. A horizon is a judgment the model can actually make.

    A full date is still accepted, because a local model asked for a number
    will sometimes give a date anyway, and one that is genuinely in range
    should not be thrown away. Its bounds check is the same.
    """
    date = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if date:
        try:
            due = datetime(int(date.group(1)), int(date.group(2)),
                           int(date.group(3))).timestamp()
        except ValueError:
            return None, f"unreadable date: {text[:40]}"
        days = (due - now) / DAY
    else:
        num = re.search(r"(\d+(?:\.\d+)?)", text)
        if not num:
            return None, ("no readable horizon — a claim without one is"
                          " 'I was right eventually'")
        days = float(num.group(1))
        due = now + days * DAY
    if 0 < days < MIN_HORIZON_DAYS:
        return None, (f"due in {days:.1f} days — a claim about what has already"
                      " happened is not a prediction")
    if days > MAX_HORIZON_DAYS:
        return None, (f"due in {days:.0f} days — beyond {MAX_HORIZON_DAYS},"
                      " being wrong costs nothing that reaches the position")
    return due, None


def open_claims_count(conn: sqlite3.Connection) -> int:
    """Unresolved FORECASTS. The carrying cap's denominator (E1.9).

    A retrodiction is due the moment it is opened and leaves the pool on the
    next pass, so counting it here would let a claim that occupies the store
    for minutes displace one that occupies it for a month.
    """
    return conn.execute(
        "SELECT COUNT(*) FROM resolutions"
        " WHERE status='open' AND kind='forecast'").fetchone()[0]


def opened_today(conn: sqlite3.Connection, *, now: float | None = None,
                 kind: str = "forecast") -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM resolutions WHERE opened_at > ? AND kind = ?",
        ((now or time.time()) - DAY, kind)).fetchone()[0]


def already_in_the_dossier(conn: sqlite3.Connection, resolver: str) -> str | None:
    """Has the being already read the material this resolver names? (E1.9)

    `MIN_HORIZON_DAYS = 2` exists as a proxy for this — its own comment says
    "a claim due tomorrow about something already in the dossier is not a
    prediction" — and a date cannot tell "already settled in the world" from
    "already read by me". Only the second is cheating, and it is checkable
    directly, so the retrodictive door checks the thing rather than the proxy.

    **Local and exact, with no network.** E1.8's `HarvestAdapter` reads
    `harvest_log`, so asking it what this resolver names costs one query. If
    what comes back is a url the being has already READ — `ingest_log` with
    `skipped IS NULL` — then the answer is in the dossier and the claim is a
    restatement of something it read, not a test of anything.

    Returns the reason to refuse, or None. **A miss is not a pass**: the
    adapters can reach sources the harvest cannot, and nothing here can check
    those without a network call the door has no business making. It catches
    the mechanical case and says so rather than implying more (INV-044).
    """
    from newz.world.harvest import HarvestAdapter

    try:
        candidates = HarvestAdapter(conn).search(resolver, limit=5)
        if not candidates:
            return None
        read = {row[0].split(":", 1)[1] for row in conn.execute(
            "SELECT source FROM ingest_log WHERE skipped IS NULL"
            " AND source LIKE '%:%'")}
    except sqlite3.Error as e:  # noqa: BLE001
        logger.info("dossier check unavailable: %s", e)
        return None
    for c in candidates:
        if c.url and c.url in read:
            return (f"I have already read what {c.source} published on this"
                    f" ({c.title[:80]}) — a claim I can settle from my own"
                    " dossier tests nothing")
    return None


def propose_claim(conn: sqlite3.Connection, client: LLMClient, *,
                  established: str, concern_statement: str,
                  concern_id: int | None = None, provenance: str | None = None,
                  now: float | None = None) -> DoorVerdict:
    """Ask whether what was just established commits the being to anything.

    Called from deliberation after an advance is ACCEPTED — the one moment the
    being has something new enough to commit to. Never called on a setback: a
    concern that did not move has nothing new to be wrong about.
    """
    now = now or time.time()

    # **Two routes now, and a cap on one is not a cap on the other (E1.9).**
    # A forecast is bounded by the carrying pool and by its daily rate; a
    # retrodiction leaves the pool on the next pass, so only its rate binds.
    # Which route a proposal takes is not known until the model has answered —
    # the kind is derived from the horizon — so the caps are evaluated twice:
    # here, to avoid spending a DEEP call when NEITHER route could open, and
    # again below against the kind that actually came back.
    pool_full = open_claims_count(conn) >= MAX_OPEN_CLAIMS
    forecast_rate_full = opened_today(conn, now=now) >= MAX_OPENED_PER_DAY
    retro_rate_full = (opened_today(conn, now=now, kind="retrodiction")
                       >= MAX_RETRODICTIONS_PER_DAY)

    def _pool_refusal() -> DoorVerdict:
        """**A full pool is a refusal, not a decline.**

        Declining writes nothing, by design: "nothing here is worth claiming"
        is the ordinary answer and is not held against the being. A cap is the
        opposite — the being was not asked at all — and a silent one reads as
        "it had nothing to claim" when the truth is "it was not allowed to".
        PLAN names that shape as wrong for E4.1's cap and the claim door had it
        too. Measured 2026-08-28: 31 of 40 open, opening at 3.0/day against a
        throughput ceiling of 1.35/day, so this was days from firing and would
        have been invisible when it did.
        """
        reason = (f"the open pool is full — {MAX_OPEN_CLAIMS} forecasts are"
                  " waiting on their dates, so I was not asked whether this was"
                  " worth claiming")
        _record_refusal(conn, concern_id, reason)
        return DoorVerdict(refused=reason)

    if (pool_full or forecast_rate_full) and retro_rate_full:
        # Nothing could open by either route, so nothing is spent finding out.
        # The pool is the one that gets a row: a rate limit is expected to bind
        # on a productive day and says nothing about the being's supply of
        # claims, while a full pool is the state that was lying.
        return _pool_refusal() if pool_full else DoorVerdict(declined=True)

    body = (f"<today>{datetime.fromtimestamp(now):%Y-%m-%d}</today>\n"
            f"<concern>{concern_statement}</concern>\n"
            f"<established>{established}</established>")
    try:
        result = client.complete("DEEP", _SYSTEM, f"{_TASK}\n\n{body}",
                                 max_tokens=600, temperature=0.3,
                                 function="claim_door")
        root = extract_xml(result.text, "claim")
    except (XMLExtractionError, Exception) as e:  # noqa: BLE001
        # Unreadable is not refusal: nothing was claimed, so there is nothing
        # to hold against the being. It is logged and the cycle moves on.
        logger.info("claim door: unreadable proposal (%s)", e)
        return DoorVerdict(declined=True)

    def text_of(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "").strip() if el is not None and el.text else ""

    if text_of("worth_claiming").lower() != "yes":
        return DoorVerdict(declined=True)

    statement = text_of("statement")
    condition = text_of("settles_when")
    resolver = text_of("resolver")
    alternative = text_of("could_be_wrong")
    due_text = text_of("due_in_days") or text_of("due")

    def refuse(reason: str) -> DoorVerdict:
        _record_refusal(conn, concern_id, reason, claim=statement,
                        condition=condition, resolver=resolver, due_text=due_text)
        return DoorVerdict(refused=reason)

    if not statement or not condition or not resolver:
        missing = [n for n, v in (("statement", statement),
                                  ("resolution condition", condition),
                                  ("resolver", resolver)) if not v]
        return refuse("claimed yes but gave no " + ", ".join(missing))

    low = resolver.lower()
    for empty in _EMPTY_RESOLVERS:
        if empty in low:
            return refuse(f"resolver names no source: {resolver!r} ({empty!r})")

    if not _names_something(statement):
        return refuse(
            "claim names nothing a source could be searched for — no entity,"
            " place, period or identifier, so no quote could ever settle it")

    if not alternative or _normalised(alternative) == _normalised(statement):
        return refuse(
            "cannot say what being wrong would look like — a claim whose other"
            " outcome I cannot describe is not a prediction")

    if _PLACEHOLDER.search(resolver) or _PLACEHOLDER.search(statement):
        return refuse(
            "the resolver is not a document yet — a title to be identified, or"
            " an identifier standing in for one, is a source nobody can fetch"
            " and a claim nobody can settle")

    due, why = _parse_due(due_text, now)
    if due is None:
        return refuse(why or "no date")

    days = (due - now) / DAY

    # **Which kind this is, decided by the horizon and nothing else (E1.9).**
    # A horizon of zero is the being saying the source has already spoken, so
    # the fact is derived rather than asked for: no new field in the prompt, no
    # second thing that can disagree with the date, and a row that cannot be
    # `retrodiction` with a date a month out.
    kind = "retrodiction" if days <= 0 else "forecast"

    if kind == "retrodiction":
        if retro_rate_full:
            return DoorVerdict(declined=True)
        # The cadence table below asks whether a source can have spoken in the
        # time allowed. For a retrodiction it already has, by construction, so
        # the question is the other one: had the being already read it?
        dossier = already_in_the_dossier(conn, resolver)
        if dossier:
            return refuse(dossier)
    else:
        if pool_full:
            return _pool_refusal()
        if forecast_rate_full:
            return DoorVerdict(declined=True)

    for pattern, cadence_days, cadence in _CADENCE:
        if kind == "retrodiction" or not pattern.search(resolver):
            continue
        if days < cadence_days:
            return refuse(
                f"a {cadence} source cannot have spoken in {days:.0f} days —"
                f" it publishes about every {cadence_days}, and moving the date"
                f" does not move the source. Claim a nearer observable, or this"
                f" subject does not fit the {MAX_HORIZON_DAYS}-day ceiling")
        break

    try:
        claim_id = open_claim(conn, Claim(
            id=None, claim=statement, resolution_condition=condition,
            resolver=resolver, due_at=due, opened_at=now, kind=kind,
            could_be_wrong=alternative,
            provenance=provenance or (f"concern:{concern_id}" if concern_id
                                      else "deliberation")))
    except UnsettleableClaim as e:
        return refuse(str(e))

    logger.info("%s %d opened from concern %s, due %s (%s): %s", kind, claim_id,
                concern_id, datetime.fromtimestamp(due).strftime("%Y-%m-%d"),
                due_text, statement[:80])
    return DoorVerdict(claim_id=claim_id)
