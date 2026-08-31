"""The claim door (P3 epic E1.2).

One validated way in. The concern opener's discipline applied one level down:
a concern needs a closing condition or it is not pursuable (INV-034); a claim
needs a resolution condition, a named resolver and a date, or it is not
refusable — and a being that cannot be refused cannot be corrected by the
world, which is the whole of Phase 1.
"""

from __future__ import annotations

import time
import inspect
from datetime import datetime, timedelta

from newz.resolutions.door import (
    MAX_HORIZON_DAYS, MAX_OPENED_PER_DAY, MAX_OPEN_CLAIMS, _resolver_history,
    open_claims_count, propose_claim,
)
from newz.resolutions.model import Claim
from newz.resolutions.store import claims_by_status, get_claim, open_claim

from tests.conftest import FakeLLM

ESTABLISHED = ("Exchange-reported open interest overstates collateralised"
               " positions, because netting conventions differ between venues.")
CONCERN = ("Does the disparity between open interest and volume indicate the"
           " market's apparent depth is illusory?")


def _due(days: int = 40) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def _proposal(**kw) -> str:
    f = dict(
        worth_claiming="yes",
        statement="The CFTC Commitments of Traders report for the September"
                  " contract will show open interest at least 10% below the"
                  " exchange's published figure for the same date.",
        settles_when="The COT release for that week is published and the two"
                     " figures compared.",
        resolver="CFTC Commitments of Traders weekly report",
        could_be_wrong="the COT figure comes in at or below the exchange's own,"
                       " showing the netting gap I claimed is not there",
        due="40",
        tag="due_in_days",
    )
    f.update(kw)
    return (f"<claim><worth_claiming>{f['worth_claiming']}</worth_claiming>"
            f"<statement>{f['statement']}</statement>"
            f"<settles_when>{f['settles_when']}</settles_when>"
            f"<resolver>{f['resolver']}</resolver>"
            f"<could_be_wrong>{f['could_be_wrong']}</could_be_wrong>"
            f"<{f['tag']}>{f['due']}</{f['tag']}></claim>")


def _refusals(store) -> list[tuple[str, str]]:
    return [(r["reason"], r["claim"]) for r in store.execute(
        "SELECT reason, claim FROM claim_refusals ORDER BY id")]


def _ask(store, response: str):
    return propose_claim(store, FakeLLM([("DEEP", response)]),
                         established=ESTABLISHED, concern_statement=CONCERN,
                         concern_id=7)


def test_deliberation_opens_a_claim_it_can_state_a_resolver_for(store):
    """E1.2's done-when, second half."""
    verdict = _ask(store, _proposal())

    assert verdict.opened and not verdict.refused
    claim = claims_by_status(store)[0]
    assert claim.resolver == "CFTC Commitments of Traders weekly report"
    assert claim.provenance == "concern:7"
    assert claim.due_at > time.time()
    assert _refusals(store) == []


def test_a_claim_with_no_settleable_condition_is_refused_and_recorded(store):
    """E1.2's done-when, first half. The refusal is the point: an empty
    resolutions table otherwise cannot distinguish "makes no falsifiable
    claims" from "the door rejects them all", and those need opposite fixes."""
    verdict = _ask(store, _proposal(settles_when=""))

    assert verdict.refused and not verdict.opened
    assert claims_by_status(store) == []
    reason, claim = _refusals(store)[0]
    assert "resolution condition" in reason
    assert claim.startswith("The CFTC")     # what it tried to claim is kept


def test_declining_is_not_a_refusal(store):
    """"Nothing here is worth claiming" is the ordinary answer, like triage
    keeping nothing. Recording it as a refusal would make the door look
    strict when the being was simply honest."""
    verdict = _ask(store, _proposal(worth_claiming="no", statement=""))

    assert verdict.declined and not verdict.refused
    assert _refusals(store) == []


def test_a_resolver_that_names_no_source_is_refused(store):
    verdict = _ask(store, _proposal(resolver="time will tell"))

    assert verdict.refused and "no source" in verdict.refused
    assert claims_by_status(store) == []


def test_the_being_may_not_resolve_its_own_claim(store):
    """Rule 4 reaches the door through the store, and the refusal is recorded
    like any other rather than raising into deliberation."""
    verdict = _ask(store, _proposal(resolver="my own judgment when I revisit this"))

    assert verdict.refused and "Rule 4" in verdict.refused
    assert _refusals(store)


def test_a_claim_with_no_readable_horizon_is_refused(store):
    verdict = _ask(store, _proposal(due="soon"))

    assert verdict.refused and "horizon" in verdict.refused
    assert claims_by_status(store) == []


def test_a_date_already_past_is_a_retrodiction_now(store):
    """Changed by E1.9, 2026-08-28, and it is the epic rather than a slip.

    A past date used to be refused as "not a prediction". It is not a
    prediction, and it is still a claim the being does not grade: what makes a
    claim a test is that something outside it settles the answer, not that the
    answer is in the future. What the old rule was really protecting against —
    claiming what is already in the dossier — is now checked directly by
    `already_in_the_dossier`, which is exact where a date was a proxy.
    """
    verdict = _ask(store, _proposal(due=_due(-3), tag="due"))

    assert verdict.claim_id, verdict.refused
    assert get_claim(store, verdict.claim_id).kind == "retrodiction"


def test_a_horizon_under_two_days_is_still_refused(store):
    """The floor did not go: only zero and below became a different kind.

    A claim due tomorrow is the bad case the floor was written for — too soon
    for a source to have spoken, too late to be about what already happened —
    and it is neither a forecast that can fail nor a retrodiction that can be
    checked against the dossier.
    """
    verdict = _ask(store, _proposal(due="1", tag="due"))

    assert verdict.refused and "already happened" in verdict.refused


def test_a_date_beyond_the_horizon_costs_nothing(store):
    """S1-E needs a position to change BECAUSE the world contradicted it. A
    claim due in three years cannot do that within the life of the project."""
    verdict = _ask(store, _proposal(due="900"))

    assert verdict.refused and "beyond" in verdict.refused


def test_an_unreadable_proposal_is_not_held_against_the_being(store):
    """Nothing was claimed, so there is nothing to refuse. The being is not
    charged for the model's malformed XML."""
    verdict = _ask(store, "<claim><worth_claiming>yes")

    assert verdict.declined and not verdict.refused
    assert _refusals(store) == []


def test_the_daily_rate_limit_stops_the_door_before_it_spends(store):
    now = time.time()
    for i in range(MAX_OPENED_PER_DAY):
        open_claim(store, Claim(
            id=None, claim=f"claim {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=now + 30 * 86400,
            provenance="concern:1", opened_at=now), models=set())

    # No response is scripted: a FakeLLM call here would raise IndexError.
    verdict = propose_claim(store, FakeLLM([]), established=ESTABLISHED,
                            concern_statement=CONCERN, concern_id=7)

    # E1.9 deliberately leaves the DAILY cap a silent decline. It is a rate
    # limit that is expected to bind on a productive day and says nothing about
    # the being's supply of claims; a row every time it fired would be noise.
    # The carrying cap below is the one that was lying, and it is the one that
    # now writes.
    assert verdict.declined
    assert store.execute("SELECT COUNT(*) FROM claim_refusals").fetchone()[0] == 0


def test_the_carrying_cap_refuses_a_forecast_and_says_so(store):
    """Distinct from the rate limit: claims opened long ago still count while
    they are open, so the store cannot fill with commitments nobody reads.

    **It no longer stops the door BEFORE it spends, and that is E1.9 rather
    than a regression.** A full forecast pool leaves the retrodictive route
    open, so the door has to ask before it knows which route this proposal
    takes — the kind is derived from the horizon the model returns. The call is
    spent only when something could still have opened; when neither route can,
    the cap is still evaluated first and nothing is spent.
    """
    # Opened long ago and dated 30 days after that — a lawful horizon, so
    # these are inventory. Before 2026-08-31 the due date here was 30 days
    # from NOW, which recorded a 120-day horizon: claims the current door
    # would refuse, which no longer fill a cap they could not pass.
    old = time.time() - 90 * 86400
    for i in range(MAX_OPEN_CLAIMS):
        open_claim(store, Claim(
            id=None, claim=f"old claim {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=old + 30 * 86400,
            provenance="concern:1", opened_at=old), models=set())

    verdict = _ask(store, _proposal())

    # E1.9: a full pool is a REFUSAL, not a silent decline. Declining writes
    # nothing and reads as "it had nothing to claim"; the truth here is "it was
    # not allowed to", and the row is what tells those apart.
    assert verdict.refused and "pool is full" in verdict.refused
    row = store.execute(
        "SELECT reason FROM claim_refusals ORDER BY id DESC LIMIT 1").fetchone()
    assert row and "pool is full" in row[0]


def test_the_door_asks_for_a_horizon_and_tells_the_being_what_day_it_is():
    """R-31. Consumer: newz/resolutions/door.py's prompt body. Behavior: the
    model is never asked for a fact it has disclaimed.

    Asked directly, every role answers "I do not have access to real-time
    information, so I cannot provide today's date." The door used to require
    <due>YYYY-MM-DD</due> anyway, so a `yes` verdict filled it from the
    training prior — 2024-12-31 against a real date of 2026-08-19 — and every
    well-formed claim was refused for being ~600 days past. The schema, not
    the model, was the fault.
    """
    from newz.resolutions import door

    assert "<due_in_days>" in door._TASK
    assert "YYYY-MM-DD" not in door._TASK
    # Derived, not spelled: this read "2 and 365" and went stale the moment the
    # ceiling moved to 45. A test that hardcodes a bound it is checking is a
    # second place to remember.
    assert (f"{door.MIN_HORIZON_DAYS} and {door.MAX_HORIZON_DAYS}"
            in door._TASK)                        # the bounds are stated, not guessed
    assert "<today>" in inspect.getsource(door.propose_claim)


def test_a_horizon_in_days_opens_a_claim_dated_from_today(store):
    """Consumer: tools/claims.py. Behavior: due_at lands `days` from now, so a
    claim the being makes is settleable within the life of the project."""
    verdict = _ask(store, _proposal(due="30"))

    assert verdict.claim_id, verdict.refused
    claim = claims_by_status(store)[0]
    assert 29 * 86400 < claim.due_at - time.time() < 31 * 86400


def test_a_date_still_works_when_the_model_gives_one_anyway(store):
    """A local model asked for a number will sometimes answer with a date. One
    genuinely in range is not thrown away; one in the past is still refused."""
    verdict = _ask(store, _proposal(due=_due(40), tag="due"))

    assert verdict.claim_id, verdict.refused


def test_a_claim_naming_nothing_searchable_is_refused_and_recorded(store):
    """R-35. Consumer: newz/resolutions/resolver.py. Behavior: a claim the
    resolver could never key a search on is refused at the door rather than
    admitted and left open forever.

    Measured 2026-08-19: the door admitted "the official agency's final
    published figure for the wildfire acreage will differ from the prediction
    market's resolved value by more than 5%" — no agency, no fire, no market,
    no year. The resolver ran, read a document in full, and reported it could
    not find the specific figures "for the specific event in question".
    Settleable in grammar, unsettleable in fact.
    """
    verdict = _ask(store, _proposal(
        statement="The official agency's final published figure will differ from"
                  " the prediction market's resolved value by more than 5%."))

    assert verdict.refused and "names nothing" in verdict.refused
    assert _refusals(store)


def test_a_claim_whose_other_outcome_cannot_be_stated_is_refused(store):
    """R-35. Consumer: the claim door's own standard. Behavior: the prompt has
    always said "if nothing would surprise me, there is no claim here" and never
    asked for the judgment; now it does, and a claim without it is refused.

    Nothing in the system could previously tell a prediction from a formality.
    """
    verdict = _ask(store, _proposal(could_be_wrong=""))

    assert verdict.refused and "being wrong would look like" in verdict.refused


def test_the_alternative_is_stored_with_the_claim(store):
    """Consumer: tools/claims.py. Behavior: what the being said the other
    outcome looks like survives to the moment the claim is settled, so a
    resolution can be read against what was actually predicted."""
    verdict = _ask(store, _proposal())

    assert verdict.claim_id, verdict.refused
    row = store.execute("SELECT could_be_wrong FROM resolutions WHERE id=?",
                        (verdict.claim_id,)).fetchone()
    assert row[0] and "below" in row[0]


# ── the horizon, and why it is 45 (2026-08-22) ──────────────────────────────

def test_a_horizon_beyond_the_ceiling_is_refused_and_says_why(store):
    """Measured 2026-08-22: every claim the being had ever written was 120-365
    days out, `claim_refusals` held zero rows, and so nothing below the door had
    executed ONCE in life. Behavior: a horizon past the ceiling is refused and
    the refusal names the ceiling, so the record distinguishes "it committed to
    nothing" from "it committed too far out to learn from".
    """
    v = propose_claim(store, FakeLLM([("DEEP", _proposal(due="180"))]),
                      established=ESTABLISHED, concern_statement=CONCERN,
                      concern_id=1)

    assert not v.opened and v.refused
    assert f"beyond {MAX_HORIZON_DAYS}" in v.refused
    row = store.execute("SELECT reason, due_text FROM claim_refusals").fetchone()
    assert "beyond" in row["reason"] and row["due_text"] == "180"


def test_the_cap_and_the_prompt_never_ship_apart(store):
    """The red team's first objection, made structural. The door refuses an
    out-of-range horizon and does NOT ask again, so a cap on its own converts a
    180-day claim into a refusal rather than a 45-day one — it is the prompt
    that produces short claims and the cap only enforces them.

    Behavior: the instruction that does the work is present, so the two cannot
    drift apart silently the way the stated bound did.
    """
    from newz.resolutions import door

    assert "nearest source that will have spoken" in door._TASK
    assert "Claim the nearest one" in door._TASK
    # And declining stays free, or the prompt trades long claims for bad ones.
    assert "declining costs nothing" in door._TASK


def test_a_claim_inside_the_window_still_opens(store):
    """The other direction. Behavior: the ceiling moved and nothing else did —
    a well-formed claim at a reachable horizon opens exactly as before.
    """
    v = propose_claim(store, FakeLLM([("DEEP", _proposal(due="30"))]),
                      established=ESTABLISHED, concern_statement=CONCERN,
                      concern_id=1)

    assert v.opened
    claim = claims_by_status(store, "open")[0]
    assert 29 <= (claim.due_at - time.time()) / 86400.0 <= 31


# ── the horizon's second night: compression, not shortening (2026-08-23) ────

def test_a_quarterly_source_cannot_have_spoken_in_thirty_days(store):
    """The defect the first night produced. Measured 2026-08-23:

        claim 10  120d  "Meta's Quarterly Transparency Report"
        claim 14   30d  "Meta's Quarterly Transparency Report"

    Same resolver, and claim 10 even named the quarter it settled in. Nothing
    about Meta changed; the ceiling did, and the being filled the field to fit
    — R-31's failure one layer up. Behavior: a source that says how often it
    publishes is refused when the horizon is shorter than that, so the being
    cannot satisfy the range by misdating.
    """
    v = propose_claim(
        store, FakeLLM([("DEEP", _proposal(
            resolver="Meta's Quarterly Transparency Report", due="30"))]),
        established=ESTABLISHED, concern_statement=CONCERN, concern_id=1)

    assert not v.opened
    assert "quarterly source cannot have spoken in 30 days" in v.refused
    assert "moving the date does not move the source" in v.refused
    row = store.execute("SELECT reason FROM claim_refusals").fetchone()
    assert "45-day ceiling" in row["reason"]      # the read that sizes the cap


def test_an_annual_source_is_unclaimable_and_that_is_the_finding(store):
    """Deliberate. An annual source cannot settle inside a 45-day ceiling at
    all, so the refusal is recorded and becomes the evidence for whether 45 is
    too tight for what this being thinks about — the read the proposal's
    falsifier 2 asked for and could not produce while misdating was available.
    """
    v = propose_claim(
        store, FakeLLM([("DEEP", _proposal(
            resolver="the company's annual report", due="40"))]),
        established=ESTABLISHED, concern_statement=CONCERN, concern_id=1)

    assert not v.opened and "annual source" in v.refused


def test_a_weekly_source_inside_the_window_still_opens(store):
    """The check must not refuse the claims the change exists to produce."""
    v = propose_claim(
        store, FakeLLM([("DEEP", _proposal(
            resolver="CFTC Commitments of Traders weekly report", due="21"))]),
        established=ESTABLISHED, concern_statement=CONCERN, concern_id=1)

    assert v.opened, v.refused


def test_a_resolver_that_is_not_a_document_yet_is_refused(store):
    """R-35 pointed at the RESOLVER. `_names_something` checks the statement,
    so a well-named statement carried an unnamed resolver straight through —
    "(EU) 2023/XXXX" and "title to be identified upon release" both opened on
    the first night under the new ceiling.
    """
    for bad in ("European Commission Implementing Regulation (EU) 2023/XXXX",
                "The specific industry report (title to be identified upon release)",
                "the forthcoming paper, TBD"):
        v = propose_claim(
            store, FakeLLM([("DEEP", _proposal(resolver=bad, due="30"))]),
            established=ESTABLISHED, concern_statement=CONCERN, concern_id=1)
        assert not v.opened, bad
        assert "not a document yet" in v.refused, bad


def test_the_prompt_says_what_the_door_now_refuses(store):
    """A door that refuses what it never warned about teaches the being to
    guess. Both new refusals are stated in the task."""
    from newz.resolutions import door

    assert "Moving the date does not move the source" in door._TASK
    assert "Name a document that exists" in door._TASK


# ── the door's own record (2026-08-31) ───────────────────────────────────

def _claim_row(store, *, resolver, attempts, status="open", outcome=None,
               failure=None, kind="forecast", horizon_days=10.0):
    now = time.time()
    store.execute(
        "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
        " resolver, due_at, provenance, status, outcome, settled_at, attempts,"
        " last_failure, kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (now, "a claim", "a condition", resolver, now + horizon_days * 86400.0,
         "concern:1", status, outcome, now if status == "resolved" else None,
         attempts, failure, kind))
    store.commit()


def test_the_door_is_shown_what_its_resolvers_returned(store):
    """22 attempts had reached the being through no channel at all."""
    _claim_row(store, resolver="League of Nations Statistical Yearbook",
               attempts=3, failure="The material contains no industrial "
                                   "production data for the UK or France.")

    body = _resolver_history(store)

    assert "what_my_resolvers_did" in body
    assert "League of Nations Statistical Yearbook" in body
    assert "3 attempt(s), not settled" in body
    assert "contains no industrial production data" in body


def test_a_settled_claim_is_reported_as_the_store_has_it(store):
    """The door reports the store and editorialises nothing."""
    _claim_row(store, resolver="Wikipedia", attempts=3, status="resolved",
               outcome="held", failure="an earlier failure")

    body = _resolver_history(store)

    assert "settled held" in body
    # The failure that preceded a settlement is not what came back.
    assert "an earlier failure" not in body


def test_nothing_attempted_shows_no_history_at_all(store):
    _claim_row(store, resolver="Federal Reserve H.4.1", attempts=0)

    assert _resolver_history(store) == ""


def test_resolvers_are_not_merged_by_similarity(store):
    """Rule 4: whether two sources are the same source is the being's call."""
    _claim_row(store, resolver="League of Nations, Statistical Yearbook 1933",
               attempts=3, failure="no data")
    _claim_row(store, resolver="League of Nations Statistical Yearbook (1939)",
               attempts=2, failure="no data")

    body = _resolver_history(store)

    assert "Statistical Yearbook 1933" in body
    assert "Yearbook (1939)" in body
    assert body.count("attempt(s)") == 2


# ── the cap counts live inventory (2026-08-31) ───────────────────────────

def test_a_claim_the_resolver_gave_up_on_is_not_inventory(store):
    from newz.resolutions.resolver import MAX_ATTEMPTS

    _claim_row(store, resolver="a source", attempts=MAX_ATTEMPTS)

    assert open_claims_count(store) == 0


def test_a_claim_the_current_door_would_refuse_is_not_inventory(store):
    """Twelve claims made under a 365-day ceiling held 31% of the pool."""
    _claim_row(store, resolver="a source", attempts=0,
               horizon_days=MAX_HORIZON_DAYS + 1)

    assert open_claims_count(store) == 0


def test_an_ordinary_open_forecast_still_counts(store):
    _claim_row(store, resolver="a source", attempts=1,
               horizon_days=MAX_HORIZON_DAYS - 1)

    assert open_claims_count(store) == 1


def test_a_retrodiction_still_never_counts(store):
    _claim_row(store, resolver="a source", attempts=0, kind="retrodiction",
               horizon_days=0.0)

    assert open_claims_count(store) == 0
