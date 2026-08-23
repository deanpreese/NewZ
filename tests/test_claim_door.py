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
    MAX_HORIZON_DAYS, MAX_OPENED_PER_DAY, MAX_OPEN_CLAIMS, propose_claim,
)
from newz.resolutions.model import Claim
from newz.resolutions.store import claims_by_status, open_claim

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


def test_a_date_already_past_is_not_a_prediction(store):
    verdict = _ask(store, _proposal(due=_due(-3), tag="due"))

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

    assert verdict.declined and not verdict.refused


def test_the_carrying_cap_stops_the_door_before_it_spends(store):
    """Distinct from the rate limit: claims opened long ago still count while
    they are open, so the store cannot fill with commitments nobody reads."""
    old = time.time() - 90 * 86400
    for i in range(MAX_OPEN_CLAIMS):
        open_claim(store, Claim(
            id=None, claim=f"old claim {i}", resolution_condition="a source says so",
            resolver="a named report", due_at=time.time() + 30 * 86400,
            provenance="concern:1", opened_at=old), models=set())

    verdict = propose_claim(store, FakeLLM([]), established=ESTABLISHED,
                            concern_statement=CONCERN, concern_id=7)

    assert verdict.declined


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
