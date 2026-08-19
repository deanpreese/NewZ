"""Claims the world can settle (P3 epic E1.1).

The store object Phase 1 is built on. Its whole job is to make a claim
judgeable: what was asserted, what would settle it, who settles it, and when.
A claim missing any of those cannot be wrong, and a claim that cannot be wrong
is not what the phase is for.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from newz.resolutions.model import Claim
from newz.resolutions.store import (
    UnsettleableClaim, check_resolver, claims_by_status, contradicted_claims,
    due_claims, get_claim, open_claim, settle_claim,
)

DAY = 86400
NO_MODELS: set[str] = set()


def _claim(**kw) -> Claim:
    base = dict(
        id=None,
        claim="US crude inventories will draw by more than 2 million barrels.",
        resolution_condition="The EIA weekly petroleum status report for the"
                             " week ending 2026-08-28 shows a draw > 2 Mbbl.",
        resolver="EIA weekly petroleum status report",
        due_at=time.time() + 10 * DAY,
        provenance="concern:42",
    )
    base.update(kw)
    return Claim(**base)


def test_a_claim_round_trips_with_its_condition_and_resolver(store):
    """E1.1's done-when, first half."""
    cid = open_claim(store, _claim(), models=NO_MODELS)

    back = get_claim(store, cid)
    assert back.claim.startswith("US crude inventories")
    assert back.resolution_condition.startswith("The EIA weekly")
    assert back.resolver == "EIA weekly petroleum status report"
    assert back.provenance == "concern:42"
    assert back.is_open and back.outcome is None


@pytest.mark.parametrize("missing", ["claim", "resolution_condition", "resolver"])
def test_the_schema_refuses_a_claim_that_nothing_could_settle(store, missing):
    """E1.1's done-when, second half. A claim with no condition sits open
    forever looking like work — INV-034's discipline, applied to claims."""
    with pytest.raises(UnsettleableClaim):
        open_claim(store, _claim(**{missing: "   "}), models=NO_MODELS)

    assert claims_by_status(store) == []


def test_the_schema_refuses_a_claim_with_no_date(store):
    """"I was right eventually" is how an unfalsifiable claim survives."""
    with pytest.raises(UnsettleableClaim):
        open_claim(store, _claim(due_at=0), models=NO_MODELS)


def test_the_resolver_may_not_be_the_being(store):
    """Rule 4. A claim the substrate settles by opinion launders the being's
    own view into the world's verdict — the exact failure Phase 1 corrects."""
    with pytest.raises(UnsettleableClaim, match="Rule 4"):
        open_claim(store, _claim(resolver="my own judgment in two weeks"),
                   models=NO_MODELS)

    with pytest.raises(UnsettleableClaim, match="substrate"):
        open_claim(store, _claim(resolver="asking qwen3.6-35b-a3b again"),
                   models={"qwen/qwen3.6-35b-a3b"})

    assert claims_by_status(store) == []


def test_the_resolver_check_does_not_refuse_a_claim_about_a_model(store):
    """Deliberately narrow: over-broad matching teaches the being to phrase
    around the check rather than to name a source. A claim ABOUT a model is
    ordinary; a claim resolved BY the being's model is not."""
    check_resolver("the model card published with the release",
                   models={"qwen/qwen3.6-35b-a3b"})

    cid = open_claim(store, _claim(
        claim="A successor to qwen3.6 will be released before October.",
        resolver="the vendor's published release notes"), models=NO_MODELS)
    assert get_claim(store, cid) is not None


def test_a_claim_is_settled_once_and_the_world_is_named(store):
    cid = open_claim(store, _claim(), models=NO_MODELS)

    settle_claim(store, cid, outcome="contradicted",
                 settled_by="https://ir.eia.gov/wpsr/2026-08-28",
                 note="Build of 1.4 Mbbl. The draw did not happen.")

    back = get_claim(store, cid)
    assert back.went_against_me
    assert back.settled_by.endswith("2026-08-28")
    assert back.settled_at
    assert [c.id for c in contradicted_claims(store)] == [cid]


def test_a_settled_claim_is_not_re_settled(store):
    """E1.5 starts here: there is no unsettle. A record of error that can be
    revised is not a record of error."""
    cid = open_claim(store, _claim(), models=NO_MODELS)
    settle_claim(store, cid, outcome="contradicted", settled_by="the EIA report")

    with pytest.raises(UnsettleableClaim):
        settle_claim(store, cid, outcome="held", settled_by="on reflection")

    assert get_claim(store, cid).outcome == "contradicted"


def test_an_outcome_the_world_did_not_give_is_refused(store):
    """There is no `ambiguous`. E1.3 fails closed by leaving the claim OPEN;
    a third outcome would be a way to close a claim without the world having
    said anything."""
    cid = open_claim(store, _claim(), models=NO_MODELS)

    with pytest.raises(ValueError):
        settle_claim(store, cid, outcome="ambiguous", settled_by="the report")
    with pytest.raises(ValueError):
        settle_claim(store, cid, outcome="held", settled_by="  ")

    assert get_claim(store, cid).is_open


def test_a_resolved_claim_cannot_lose_its_outcome(store):
    """The schema, not the writer: nothing may mark a claim done without
    saying which way it went."""
    cid = open_claim(store, _claim(), models=NO_MODELS)
    settle_claim(store, cid, outcome="held", settled_by="the EIA report")

    with pytest.raises(sqlite3.IntegrityError):
        store.execute("UPDATE resolutions SET outcome=NULL WHERE id=?", (cid,))


def test_due_claims_are_the_worklist_oldest_first(store):
    now = time.time()
    late = open_claim(store, _claim(due_at=now - 5 * DAY), models=NO_MODELS)
    recent = open_claim(store, _claim(due_at=now - DAY), models=NO_MODELS)
    open_claim(store, _claim(due_at=now + 30 * DAY), models=NO_MODELS)

    assert [c.id for c in due_claims(store, now=now)] == [late, recent]


def test_a_settled_claim_leaves_the_worklist(store):
    now = time.time()
    cid = open_claim(store, _claim(due_at=now - DAY), models=NO_MODELS)

    settle_claim(store, cid, outcome="held", settled_by="the EIA report")

    assert due_claims(store, now=now) == []
