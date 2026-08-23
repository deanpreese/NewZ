"""The asymmetry (P4 epic E4.2).

Revision on evidence is free; abandonment without cause is recorded and costs.
E4.1 made identity authorable and E4.3 made it traceable; neither held the
being to anything, because `status` never left `standing`. This is what makes
dropping a commitment an act with a consequence.
"""

from __future__ import annotations

import json
import time

from newz.commitments.asymmetry import (
    apply_change_costs, record_change, review_standing, unpaid_changes,
)
from newz.commitments.model import Commitment
from newz.commitments.store import author, standing_count
from newz.sleep.nightly import CONFIDENCE_ON_CONTRADICT
from newz.sleep.perspective import Item

from tests.conftest import FakeLLM


def _episode(store, provenance="world:arxiv") -> str:
    cur = store.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary) VALUES"
        " (?,'reading',?,'x')", (time.time(), provenance))
    store.commit()
    return str(cur.lastrowid)


def _commitment(store, evidence=()) -> int:
    return author(store, Commitment(
        id=None, kind="keeps_caring", statement="I will keep asking what I got wrong.",
        falsifier="a month with no claim resolved against me",
        provenance="perspective:14", evidence=list(evidence)))


def _settled_claim(store, outcome="contradicted") -> int:
    now = time.time()
    cur = store.execute(
        "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
        " resolver, due_at, provenance, status, outcome, settled_at)"
        " VALUES (?,?,?,?,?,?, 'resolved', ?, ?)",
        (now, "a claim", "a condition", "a source", now + 100, "concern:1",
         outcome, now))
    store.commit()
    return int(cur.lastrowid)


def _review(**kw) -> str:
    f = dict(change="abandoned", commitment="1", reason="I no longer hold it.",
             resolution="", statement="", falsifier="")
    f.update(kw)
    return (f"<review><change>{f['change']}</change>"
            f"<commitment>{f['commitment']}</commitment>"
            f"<reason>{f['reason']}</reason>"
            f"<resolution>{f['resolution']}</resolution>"
            f"<statement>{f['statement']}</statement>"
            f"<falsifier>{f['falsifier']}</falsifier></review>")


# ── the asymmetry itself ──────────────────────────────────────

def test_a_change_carried_by_a_settled_claim_costs_nothing(store):
    """E4.2's free half. The world said something, so changing your mind is
    what a mind is for."""
    cid = _commitment(store, evidence=[_episode(store)])
    rid = _settled_claim(store)

    ch = record_change(store, commitment_id=cid, kind="abandoned",
                       reason="the world settled it against me",
                       resolution_id=rid)

    assert ch.free
    assert not unpaid_changes(store)          # nothing queued to charge
    row = store.execute("SELECT resolution_id, cost_note FROM"
                        " commitment_changes").fetchone()
    assert row["resolution_id"] == rid
    assert "settled claim" in row["cost_note"]


def test_a_change_with_no_settled_claim_is_queued_to_cost(store):
    cid = _commitment(store, evidence=[_episode(store)])

    ch = record_change(store, commitment_id=cid, kind="abandoned",
                       reason="I simply do not want it any more")

    assert not ch.free
    assert len(unpaid_changes(store)) == 1


def test_citing_an_unsettled_claim_is_the_same_as_citing_nothing(store):
    """Rule 4, made a join. The being names WHICH claim settled it and the code
    checks whether that claim settled — a model asked whether an abandonment
    was justified would justify every one of them.
    """
    cid = _commitment(store, evidence=[_episode(store)])
    now = time.time()
    store.execute(
        "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
        " resolver, due_at, provenance, status) VALUES (?,?,?,?,?,?, 'open')",
        (now, "still open", "a condition", "a source", now + 100, "concern:1"))
    store.commit()
    open_id = store.execute("SELECT MAX(id) i FROM resolutions").fetchone()["i"]

    ch = record_change(store, commitment_id=cid, kind="abandoned",
                       reason="a claim I have not settled", resolution_id=open_id)

    assert not ch.free
    assert store.execute("SELECT resolution_id FROM commitment_changes"
                         ).fetchone()["resolution_id"] is None
    assert len(unpaid_changes(store)) == 1


# ── the cost ───────────────────────────────────────────────

def test_dropping_without_cause_charges_the_positions_it_rested_on(store):
    """Who pays is traced, not judged — the commitment's own evidence (E4.3)
    names the episodes it was made on the strength of."""
    e = _episode(store)
    cid = _commitment(store, evidence=[e])
    record_change(store, commitment_id=cid, kind="abandoned", reason="no reason")
    items = [Item(section="what_i_hold", text="a position", evidence=[e],
                  confidence=0.70)]

    charged = apply_change_costs(store, items)

    assert len(charged) == 1
    assert items[0].confidence == round(0.70 - CONFIDENCE_ON_CONTRADICT, 3)
    assert items[0].status == "disputed"
    assert not unpaid_changes(store)          # charged once, never twice


def test_a_commitment_grounded_in_nothing_costs_nothing_and_says_so(store):
    """INV-044. The being can drop something it never grounded, and that is a
    different finding from an abandonment nobody paid for."""
    cid = _commitment(store, evidence=[])
    record_change(store, commitment_id=cid, kind="abandoned", reason="no reason")

    charged = apply_change_costs(store, [Item(section="what_i_hold",
                                              text="unrelated", evidence=["99"])])

    assert charged == []
    note = store.execute("SELECT cost_note FROM commitment_changes").fetchone()
    assert "no position traced" in note["cost_note"]
    assert not unpaid_changes(store)


def test_the_slot_is_freed_but_the_record_is_not_deleted(store):
    """E1.5's discipline applied to identity: a record of having stopped caring
    that can be tidied away is not a record. The carrying cap frees a slot,
    which is what stops MAX_STANDING deadlocking."""
    cid = _commitment(store, evidence=[])
    assert standing_count(store) == 1

    record_change(store, commitment_id=cid, kind="abandoned", reason="done")

    assert standing_count(store) == 0
    row = store.execute("SELECT status FROM commitments WHERE id=?",
                        (cid,)).fetchone()
    assert row["status"] == "abandoned"
    prior = store.execute("SELECT prior_statement FROM commitment_changes"
                          ).fetchone()["prior_statement"]
    assert "what I got wrong" in prior


def test_a_revision_keeps_it_standing_with_new_text(store):
    cid = _commitment(store, evidence=[])
    rid = _settled_claim(store)

    record_change(store, commitment_id=cid, kind="revised",
                  reason="narrower now", resolution_id=rid,
                  statement="I will keep asking what I got wrong about markets.",
                  falsifier="a month with no market claim resolved against me")

    row = store.execute("SELECT statement, falsifier, status FROM commitments"
                        " WHERE id=?", (cid,)).fetchone()
    assert row["status"] == "standing"
    assert "about markets" in row["statement"]
    assert "market claim" in row["falsifier"]      # the falsifier moved with it


# ── the review ─────────────────────────────────────────

def test_most_nights_nothing_changes(store):
    _commitment(store, evidence=[])
    ch = review_standing(store, FakeLLM([("DEEP", _review(change="no"))]))

    assert ch is None
    assert standing_count(store) == 1
    assert not unpaid_changes(store)


def test_the_review_is_not_asked_when_nothing_stands(store):
    empty = FakeLLM([])                # would raise if the model were reached
    assert review_standing(store, empty) is None


def test_a_review_naming_something_already_gone_is_dropped(store):
    cid = _commitment(store, evidence=[])
    record_change(store, commitment_id=cid, kind="abandoned", reason="gone")

    assert record_change(store, commitment_id=cid, kind="abandoned",
                         reason="again") is None
    assert store.execute("SELECT COUNT(*) c FROM commitment_changes"
                         ).fetchone()["c"] == 1
