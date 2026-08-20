"""The S1-E read (P4 epic E1.6).

P4's Phase 1 decision rule turns on one question — did a position change
because the WORLD contradicted it — and until this existed nothing could
answer it. The tests below fix the three things that make the answer
trustworthy: the world column is a count and not an inference, a missing call
log reports itself unmeasured rather than zero, and the upstream question
(can any concern be closed at all?) is read from the store.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.evidence.consequence import read
from newz.evidence.pursuit import closing_shapes
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "s1e.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def _claim(conn, *, now, outcome=None, settled=None):
    conn.execute(
        "INSERT INTO resolutions (opened_at, claim, resolution_condition, resolver,"
        " due_at, provenance, status, outcome, settled_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (now - 10 * 86400, "the index will publish a figure below 40",
         "the monthly release", "the statistical office", now + 20 * 86400,
         "concern:1", "resolved" if settled else "open", outcome, settled))
    conn.commit()
    return conn.execute("SELECT MAX(id) FROM resolutions").fetchone()[0]


def test_s1e_is_not_met_until_the_world_changes_a_position(store, tmp_path):
    """Consumer: tools/claims.py --read. Behavior: `met` is false while the
    only positions that moved were moved by the being or the operator."""
    now = time.time()
    _claim(store, now=now)

    r = read(store, tmp_path, now=now)

    assert not r.met
    assert r.positions.by_world == 0


def test_the_world_column_is_counted_and_never_inferred(store, tmp_path):
    """Consumer: tools/claims.py --read. Behavior: by_world reads claim_costs,
    which INV-048 writes by TRACING which items a refutation charged — so S1-E
    turns on a count, not on a judgment about why a position moved."""
    now = time.time()
    cid = _claim(store, now=now, outcome="contradicted", settled=now - 3600)
    store.execute(
        "INSERT INTO claim_costs (ts, claim_id, item_text, section,"
        " confidence_before, confidence_after, repeat, released)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (now - 1800, cid, "a position that cited that concern", "who_i_am",
         0.8, 0.5, 0, 0))
    store.commit()

    r = read(store, tmp_path, now=now)

    assert r.positions.by_world == 1
    assert r.met, "one position charged by a world refutation is exactly S1-E"


def test_a_missing_call_log_reports_declines_unmeasured_not_zero(store, tmp_path):
    """Consumer: tools/claims.py --read. Behavior: INV-046 keeps declines out of
    the store deliberately, so without the log 'the being commits to nothing'
    and 'the door was never called' are the same reading — and saying 0 would
    assert the first. INV-044's rule, at the door."""
    r = read(store, tmp_path, now=time.time())

    assert r.door.declined is None
    assert r.door.unreadable and "not recorded in the store" in r.door.unreadable


def test_declines_are_counted_when_the_log_is_there(store, tmp_path):
    now = time.time()
    log = tmp_path / "logs"
    log.mkdir()
    (log / "llm_calls.jsonl").write_text(
        '{"ts": %f, "function": "claim_door", "response": "<claim><worth_claiming>no</worth_claiming></claim>"}\n'
        '{"ts": %f, "function": "claim_door", "response": "<claim><worth_claiming>yes</worth_claiming></claim>"}\n'
        '{"ts": %f, "function": "gate", "response": "<claim><worth_claiming>no</worth_claiming></claim>"}\n'
        % (now - 60, now - 50, now - 40))

    r = read(store, tmp_path, now=now)

    assert r.door.declined == 1, "only claim_door calls saying no are declines"
    assert r.door.unreadable is None


def test_a_terminus_only_the_being_can_reach_is_counted_as_unreachable(store):
    """Consumer: tools/claims.py --read. Behavior: R-33's two failure shapes are
    told apart, because they call for opposite fixes — a self-graded terminus is
    a Rule 4 problem and a commissioned study is a reachability problem."""
    for cc in ("I can cite the specific metrics providers gave in earnings calls",
               "A study correlating order-splitting with slippage under stress",
               "The statistical office publishes its March release"):
        store.execute(
            "INSERT INTO concerns (opened_at, kind, statement, why_open,"
            " closing_condition, status, salience, origin)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (time.time(), "inquiry", "does x hold?", "a probe", cc, "open",
             0.5, "probe"))
    store.commit()

    s = closing_shapes(store)

    assert s.self_terminus == 1
    assert s.commissioned == 1
    assert s.reachable == 1
    assert s.unreachable == 2
