"""Being wrong costs the position (P3 epic E1.4).

INV-031's mechanism pointed outward. The being has always been able to
contradict itself; this is the first time something outside it can, and the
cost has to land the same way or Phase 1 ends at "the world disagreed" with
nothing following.
"""

from __future__ import annotations

import json
import time

from newz.resolutions.cost import apply_world_costs
from newz.resolutions.model import Claim
from newz.resolutions.store import open_claim, settle_claim
from newz.sleep.nightly import (
    CONFIDENCE_ON_CONTRADICT, CONFIDENCE_ON_REPEAT_CONTRADICT,
)
from newz.sleep.perspective import Item, RELEASE_BELOW, apply_decay
from newz.store.episodes import write_episode

DAY = 86400.0


def _refuted_claim(store, *, concern_id: int = 7) -> int:
    cid = open_claim(store, Claim(
        id=None, claim="Open interest will print 10% below the exchange figure.",
        resolution_condition="The COT release is published and compared.",
        resolver="CFTC Commitments of Traders weekly report",
        due_at=time.time() - DAY, provenance=f"concern:{concern_id}"), models=set())
    settle_claim(store, cid, outcome="contradicted",
                 settled_by="https://cftc.gov/cot", note="It printed 3% above.")
    return cid


def _episode_for(store, concern_id: int) -> str:
    return str(write_episode(
        store, kind="advance", provenance="self",
        summary="I established that reported open interest overstates collateral.",
        content={"concern_id": concern_id}, source_ref=f"concern:{concern_id}"))


def _position(evidence, confidence=0.6, text="Reported open interest overstates"
              " collateralised positions.") -> Item:
    return Item(section="what_i_hold", text=text, evidence=list(evidence),
                confidence=confidence, status="carried", id=1,
                first_seen_version=1)


def test_a_wrong_claim_measurably_costs_its_parent_position(store):
    """E1.4's done-when, first half."""
    cid = _refuted_claim(store)
    item = _position([_episode_for(store, 7)])

    charged = apply_world_costs(store, [item])

    assert len(charged) == 1
    assert item.confidence == round(0.6 - CONFIDENCE_ON_CONTRADICT, 3)
    assert item.status == "disputed"
    row = store.execute("SELECT * FROM claim_costs").fetchone()
    assert row["claim_id"] == cid and row["confidence_before"] == 0.6


def test_who_pays_is_traced_and_never_judged(store):
    """The trace is claim -> concern -> that concern's episodes -> the items
    citing them. A position grounded in nothing from that concern is not
    charged, however much it sounds related — Rule 4 forbids the being's own
    model picking which of its positions to punish."""
    _refuted_claim(store, concern_id=7)
    mine = _position([_episode_for(store, 7)])
    someone_elses = _position([_episode_for(store, 99)],
                              text="Liquidity is a function of order-splitting.")

    apply_world_costs(store, [mine, someone_elses])

    assert mine.status == "disputed"
    assert someone_elses.confidence == 0.6 and someone_elses.status == "carried"


def test_the_refuting_source_does_not_become_the_position_s_evidence(store):
    """Material that refutes a claim is not support for the position that
    produced it — the rule INV-031 already keeps."""
    _refuted_claim(store)
    ep = _episode_for(store, 7)
    item = _position([ep])

    apply_world_costs(store, [item])

    assert item.evidence == [ep]


def test_a_position_the_world_keeps_refuting_leaves_by_the_ordinary_path(store):
    """E1.4's done-when, second half. Nothing here deletes an item: the cost
    takes it under RELEASE_BELOW and sleep's existing floor (INV-025) carries
    it out, the same way every other released position leaves."""
    ep = _episode_for(store, 7)
    item = _position([ep], confidence=0.6)

    for _ in range(3):
        _refuted_claim(store)
        apply_world_costs(store, [item])

    # 0.60 -> 0.45 (first) -> 0.15 (repeat) -> 0.00
    assert item.confidence < RELEASE_BELOW
    kept, released = apply_decay([item])
    assert kept == [] and released[0].status == "released"
    assert store.execute("SELECT COUNT(*) FROM claim_costs WHERE repeat=1"
                         ).fetchone()[0] == 2


def test_the_second_refutation_of_the_same_position_costs_double(store):
    """INV-031's own reasoning: the first is doubt, not demolition; a repeat
    is the position failing rather than one odd night."""
    ep = _episode_for(store, 7)
    item = _position([ep], confidence=0.9)

    _refuted_claim(store)
    apply_world_costs(store, [item])
    first = item.confidence
    _refuted_claim(store)
    apply_world_costs(store, [item])

    assert round(0.9 - first, 3) == CONFIDENCE_ON_CONTRADICT
    assert round(first - item.confidence, 3) == CONFIDENCE_ON_REPEAT_CONTRADICT


def test_a_refutation_that_reaches_no_position_is_recorded_as_such(store):
    """The being can be wrong about something it never wrote into its
    Perspective. INV-044: unmeasured reports itself as unmeasured, not as a
    compliant zero — and the claim is not left looking unprocessed."""
    cid = _refuted_claim(store, concern_id=7)

    charged = apply_world_costs(store, [_position([_episode_for(store, 99)])])

    assert charged == []
    row = store.execute("SELECT cost_applied_at, cost_note FROM resolutions"
                        " WHERE id=?", (cid,)).fetchone()
    assert row["cost_applied_at"] and "no position traced" in row["cost_note"]


def test_a_refutation_is_charged_once(store):
    ep = _episode_for(store, 7)
    _refuted_claim(store)

    apply_world_costs(store, [_position([ep])])
    again = apply_world_costs(store, [_position([ep])])

    assert again == []
    assert store.execute("SELECT COUNT(*) FROM claim_costs").fetchone()[0] == 1


def test_a_claim_the_world_upheld_costs_nothing(store):
    """Only being wrong costs. Being right is not a reward mechanism here —
    the position keeps whatever confidence its own grounding earned it."""
    cid = open_claim(store, Claim(
        id=None, claim="It will print below.", resolution_condition="The report says.",
        resolver="CFTC COT report", due_at=time.time() - DAY,
        provenance="concern:7"), models=set())
    settle_claim(store, cid, outcome="held", settled_by="https://cftc.gov/cot")
    item = _position([_episode_for(store, 7)])

    assert apply_world_costs(store, [item]) == []
    assert item.confidence == 0.6 and item.status == "carried"


def test_an_unsettled_claim_costs_nothing(store):
    open_claim(store, Claim(
        id=None, claim="It will print below.", resolution_condition="The report says.",
        resolver="CFTC COT report", due_at=time.time() + DAY,
        provenance="concern:7"), models=set())

    assert apply_world_costs(store, [_position([_episode_for(store, 7)])]) == []
