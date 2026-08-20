"""The permanent record of error (P4 epic E1.5).

E1.5 asks for wrongness recorded permanently **at store level** and never
quietly dropped. Before 0029 nothing pruned it because nobody had written a
DELETE — an absence, not a guarantee. A being that can lose the record of
having been wrong has no record of having been wrong, and INV-044's honesty is
the same rule pointed at the being's own history rather than at a measurement.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.resolutions.model import Claim
from newz.resolutions.store import claims_by_status, contradicted_claims, open_claim, settle_claim
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "err.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def _wrong_claim(conn) -> int:
    """A claim the world went against, with the position it cost."""
    now = time.time()
    cid = open_claim(conn, Claim(
        id=None, claim="The index will print below 40 in the March release.",
        resolution_condition="The March release is published and the print read.",
        resolver="The statistical office's March release",
        due_at=now - 86400, opened_at=now - 30 * 86400, provenance="concern:7",
        could_be_wrong="It prints at or above 40."))
    settle_claim(conn, cid, outcome="contradicted",
                 settled_by="The statistical office's March release",
                 note="printed 41.2")
    conn.execute(
        "INSERT INTO claim_costs (ts, claim_id, item_text, section,"
        " confidence_before, confidence_after, repeat, released)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (time.time(), cid, "The index is rolling over.", "unresolved",
         0.8, 0.5, 0, 0))
    conn.commit()
    return cid


def test_a_claim_the_world_went_against_cannot_be_deleted(store):
    """Consumer: newz/store/sql/main/0029. Behavior: the store refuses the
    delete, so the record of being wrong cannot be lost by any path — including
    one nobody has written yet."""
    cid = _wrong_claim(store)

    with pytest.raises(sqlite3.IntegrityError, match="part of the record"):
        store.execute("DELETE FROM resolutions WHERE id=?", (cid,))

    assert contradicted_claims(store)


def test_what_being_wrong_cost_cannot_be_deleted(store):
    """Consumer: tools/claims.py --wrong. Behavior: the cost survives even if
    the position it charged is later released — the claim is retrievable with
    what it cost, which is E1.5's whole clause."""
    cid = _wrong_claim(store)

    with pytest.raises(sqlite3.IntegrityError, match="not deletable"):
        store.execute("DELETE FROM claim_costs WHERE claim_id=?", (cid,))


def test_a_settled_verdict_cannot_be_restated(store):
    """Consumer: 0029's trigger. Behavior: once the world has answered, the
    claim it answered cannot be edited into a different claim — otherwise a
    refutation could be tidied into a claim the being was never wrong about.

    INV-045 already forbids a second settlement in Python; this puts the
    verdict's own text beyond reach in the schema."""
    cid = _wrong_claim(store)

    for column, value in (("claim", "something I was right about"),
                          ("outcome", "upheld"),
                          ("resolver", "a friendlier source")):
        with pytest.raises(sqlite3.IntegrityError, match="verdict is final"):
            store.execute(f"UPDATE resolutions SET {column}=? WHERE id=?",
                          (value, cid))


def test_the_cost_may_still_be_recorded_after_settling(store):
    """Consumer: newz/resolutions/cost.py. Behavior: sleep applies the cost
    AFTER the verdict, so the guard must freeze the verdict without freezing
    the row — a guard that broke E1.4's own writer would be worse than none."""
    cid = _wrong_claim(store)

    store.execute("UPDATE resolutions SET cost_applied_at=?, cost_note=?"
                  " WHERE id=?", (time.time(), "charged 1 position", cid))
    store.commit()

    row = store.execute("SELECT cost_note FROM resolutions WHERE id=?",
                        (cid,)).fetchone()
    assert row["cost_note"] == "charged 1 position"


def test_the_record_is_retrievable_with_its_claim_resolver_and_cost(store):
    """Consumer: tools/claims.py --wrong. Behavior: E1.5's Done-when, read back
    off the store — the original claim, the resolver that settled it, and what
    it cost, together."""
    cid = _wrong_claim(store)

    claim = contradicted_claims(store)[0]
    costs = store.execute(
        "SELECT item_text, confidence_before, confidence_after FROM claim_costs"
        " WHERE claim_id=?", (cid,)).fetchall()

    assert claim.claim.startswith("The index will print below 40")
    assert claim.resolver == "The statistical office's March release"
    assert claim.settled_by and claim.outcome == "contradicted"
    assert costs and costs[0]["confidence_before"] > costs[0]["confidence_after"]
    assert claims_by_status(store, "open") == []
