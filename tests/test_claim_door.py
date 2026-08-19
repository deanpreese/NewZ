"""The claim door (P3 epic E1.2).

One validated way in. The concern opener's discipline applied one level down:
a concern needs a closing condition or it is not pursuable (INV-034); a claim
needs a resolution condition, a named resolver and a date, or it is not
refusable — and a being that cannot be refused cannot be corrected by the
world, which is the whole of Phase 1.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from newz.resolutions.door import (
    MAX_OPENED_PER_DAY, MAX_OPEN_CLAIMS, propose_claim,
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
        due=_due(),
    )
    f.update(kw)
    return (f"<claim><worth_claiming>{f['worth_claiming']}</worth_claiming>"
            f"<statement>{f['statement']}</statement>"
            f"<settles_when>{f['settles_when']}</settles_when>"
            f"<resolver>{f['resolver']}</resolver>"
            f"<due>{f['due']}</due></claim>")


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


def test_a_claim_with_no_readable_date_is_refused(store):
    verdict = _ask(store, _proposal(due="soon"))

    assert verdict.refused and "date" in verdict.refused
    assert claims_by_status(store) == []


def test_a_date_already_past_is_not_a_prediction(store):
    verdict = _ask(store, _proposal(due=_due(-3)))

    assert verdict.refused and "already happened" in verdict.refused


def test_a_date_beyond_the_horizon_costs_nothing(store):
    """S1-E needs a position to change BECAUSE the world contradicted it. A
    claim due in three years cannot do that within the life of the project."""
    verdict = _ask(store, _proposal(due=_due(900)))

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
