"""The evidence instruments (P2 Rule 3, Evidence 1-E and 2-E).

These are the reads that gate Phase 3, so what is tested here is not that
the arithmetic runs but that the instruments cannot flatter the system they
measure: the stall pool cannot borrow v1's failures to indict v2's judge, a
sparse night cannot outvote a full one, and a missing input reports itself
as missing rather than as compliance.
"""

from __future__ import annotations

import json

import pytest

from newz.evidence.perspective_window import read_window
from newz.evidence.pursuit import (
    QUIET,
    UNTOUCHED,
    NoImportRecord,
    boundary,
    ingest_read,
    judged,
    stall_pool,
)

BOUNDARY = 1_000.0


def _import_record(conn, ts=BOUNDARY):
    conn.execute(
        "INSERT INTO import_record (run_id, ts, v1_repo, v1_commit, table_name,"
        " v1_count, imported_count) VALUES ('r', ?, '/v1', 'abc1234', 'concerns', 1, 1)",
        (ts,),
    )


def _concern(conn, cid, *, opened_at, status="stalled"):
    conn.execute(
        "INSERT INTO concerns (id, opened_at, kind, statement, why_open,"
        " closing_condition, status, origin) VALUES (?, ?, 'question', ?, 'w',"
        " 'c', ?, 'curiosity')",
        (cid, opened_at, f"concern {cid}", status),
    )


def _setback(conn, cid, kind, ts):
    conn.execute(
        "INSERT INTO concern_setbacks (concern_id, ts, kind, brief)"
        " VALUES (?, ?, ?, '')", (cid, ts, kind),
    )


def _advance(conn, cid, ts, evidence="[]"):
    conn.execute(
        "INSERT INTO concern_advances (concern_id, ts, kind, summary, evidence_json)"
        " VALUES (?, ?, 'movement', 's', ?)", (cid, ts, evidence),
    )


def _version(conn, version, *, diff, tokens=100, items=0, grounded=0, ts=1.0):
    conn.execute(
        "INSERT INTO perspective (version, ts, content, diff_json, token_count)"
        " VALUES (?, ?, 'doc', ?, ?)", (version, ts, json.dumps(diff), tokens),
    )
    for i in range(items):
        conn.execute(
            "INSERT INTO perspective_items (version, section, text, evidence_json,"
            " status, first_seen_version, ts) VALUES (?, 'what_i_hold', ?, ?,"
            " 'carried', ?, ?)",
            (version, f"item {i}", '["7"]' if i < grounded else "[]", version, ts),
        )


# ── 2-E: the stall pool ──────────────────────────────────────────────────

def test_a_stall_v2_never_attempted_is_not_counted_against_v2s_judge(store):
    """P2 Phase 2's decision rule fires on stalls the corrected judge caused.

    Consumer: tools/evidence.py. Behavior: the cause counts report only
    concerns v2 actually attempted, and say how many it never touched — so
    the rule cannot be fired on v1's inherited pool, which would send a real
    fix to the openers when the openers are not what failed.
    """
    _import_record(store)
    _concern(store, 1, opened_at=BOUNDARY - 500)   # v1's, refused by v1 only
    _setback(store, 1, "restated", BOUNDARY - 400)
    _setback(store, 1, "restated", BOUNDARY - 300)
    _concern(store, 2, opened_at=BOUNDARY + 10)    # v2's, refused by v2
    _setback(store, 2, "restated", BOUNDARY + 20)
    store.commit()

    pool = stall_pool(store, boundary(store))

    assert len(pool.stalls) == 2
    assert [s.concern_id for s in pool.untouched] == [1]
    assert [s.concern_id for s in pool.refused] == [2]
    # The count the decision rule reads is 1, not 2 — the inherited stall is
    # visible but does not vote.
    assert pool.causes() == {"circling": 1}


def test_the_cause_is_the_modal_recorded_setback_and_no_model_is_asked(store):
    """Causes come from what the being wrote at the time (INV-043)."""
    _import_record(store)
    _concern(store, 1, opened_at=BOUNDARY + 1)
    for _ in range(3):
        _setback(store, 1, "blocked", BOUNDARY + 5)
    _setback(store, 1, "restated", BOUNDARY + 6)
    store.commit()

    pool = stall_pool(store, boundary(store))
    assert pool.stalls[0].cause == "starved"       # blocked-dominant
    assert pool.stalls[0].kinds["blocked"] == 3


def test_a_tie_goes_to_the_setback_still_standing(store):
    _import_record(store)
    _concern(store, 1, opened_at=BOUNDARY + 1)
    _setback(store, 1, "blocked", BOUNDARY + 5)
    _setback(store, 1, "restated", BOUNDARY + 9)   # later, so it stands
    store.commit()

    assert stall_pool(store, boundary(store)).stalls[0].cause == "circling"


def test_advanced_and_never_refused_is_a_scheduler_read_not_a_judge_read(store):
    """A stall with no setback was not refused by anything — it was dropped."""
    _import_record(store)
    _concern(store, 1, opened_at=BOUNDARY + 1)
    _advance(store, 1, BOUNDARY + 2)
    store.commit()

    pool = stall_pool(store, boundary(store))
    assert pool.stalls[0].cause == QUIET
    assert [s.concern_id for s in pool.refused] == []      # not the judge's
    assert [s.concern_id for s in pool.attempted] == [1]   # but v2 did touch it


def test_the_boundary_is_read_from_the_import_record_never_assumed(store):
    with pytest.raises(NoImportRecord):
        boundary(store)          # no import record: refuse rather than guess
    _import_record(store, ts=1234.5)
    store.commit()
    assert boundary(store).ts == 1234.5
    assert boundary(store).v1_commit == "abc1234"


def test_acceptance_is_per_attempt_and_separates_the_two_eras(store):
    _import_record(store)
    _concern(store, 1, opened_at=BOUNDARY - 500, status="open")
    _advance(store, 1, BOUNDARY - 100)                       # v1: 1 of 3
    _setback(store, 1, "restated", BOUNDARY - 90)
    _setback(store, 1, "restated", BOUNDARY - 80)
    _advance(store, 1, BOUNDARY + 10, evidence='["12"]')     # v2: 2 of 3
    _advance(store, 1, BOUNDARY + 20)
    _setback(store, 1, "blocked", BOUNDARY + 30)
    store.commit()

    edge = boundary(store)
    v1, v2 = judged(store, until=edge.ts), judged(store, since=edge.ts)
    assert (v1.advances, v1.setbacks) == (1, 2)
    assert (v2.advances, v2.setbacks) == (2, 1)
    assert v1.acceptance == pytest.approx(1 / 3)
    assert v2.acceptance == pytest.approx(2 / 3)
    assert v2.evidence_fraction == pytest.approx(0.5)   # 1 of v2's 2 cites


# ── 2-E: the ingest share ────────────────────────────────────────────────

def test_a_missing_call_log_reads_as_unreadable_not_as_zero_ingest(tmp_path):
    """Consumer: tools/evidence.py. Behavior: the §9.1 line says the share
    could not be measured and names the path, instead of printing 0% — which
    would report compliance the instrument never observed.

    The log is gitignored and did not travel when this repo was cloned on
    2026-08-17, so this is the live case, not a hypothetical one.
    """
    read = ingest_read(tmp_path)
    assert not read.readable
    assert "llm_calls.jsonl" in read.unreadable
    assert "not zero ingest" in read.unreadable


def test_an_empty_window_is_distinguished_from_a_missing_log(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "llm_calls.jsonl").write_text("")
    read = ingest_read(tmp_path)
    assert not read.readable
    assert "no entries" in read.unreadable


# ── 1-E: the Perspective window ──────────────────────────────────────────

def test_novelty_is_pooled_so_a_sparse_night_cannot_outvote_a_full_one(store):
    """A window figure weights nights by what they held, not one vote each.

    Consumer: tools/evidence.py. Behavior: the reported window novelty is
    total developed over total held (here 2/102 ≈ 2%), not the mean of the
    two nights' rates (which would read ~26% on the strength of the emptier
    evening).
    """
    store.execute("DELETE FROM perspective")             # drop the fixture's v1
    _version(store, 2, diff={"added": ["a"], "carried": 99}, ts=1.0)
    _version(store, 3, diff={"added": ["b"], "carried": 1}, ts=2.0)
    store.commit()

    w = read_window(store)
    assert [n.version for n in w.nights] == [2, 3]
    assert w.novelty == pytest.approx(2 / 102, abs=1e-6)
    mean_of_rates = sum(n.novelty for n in w.nights) / 2
    assert mean_of_rates > 0.25          # the number the pooled read refuses
    assert w.restatement == pytest.approx(1 - 2 / 102, abs=1e-6)


def test_the_first_sleep_is_excluded_and_the_window_says_why(store):
    store.execute("DELETE FROM perspective")
    _version(store, 1, diff={"first_sleep": True, "observations": 221}, ts=1.0)
    _version(store, 2, diff={"added": [], "carried": 10}, ts=2.0)
    store.commit()

    w = read_window(store)
    assert [n.version for n in w.nights] == [2]
    assert w.excluded and w.excluded[0][0] == 1
    assert "no prior Perspective to confront" in w.excluded[0][1]
    assert not w.meets_floor()           # one night is not seven


def test_compression_and_coverage_are_reported_as_ratios_of_real_counts(store):
    store.execute("DELETE FROM perspective")
    _version(store, 2, diff={"added": [], "carried": 10}, tokens=1000,
             items=10, grounded=5, ts=1.0)
    _version(store, 3, diff={"added": [], "carried": 8}, tokens=750,
             items=8, grounded=8, ts=2.0)
    store.commit()

    w = read_window(store)
    assert w.compression == pytest.approx(0.75)
    assert w.item_compression == pytest.approx(0.8)
    assert w.coverage == pytest.approx(1.0)        # newest night's
    assert w.nights[0].coverage == pytest.approx(0.5)


def test_a_rewritten_novelty_rate_is_caught_against_the_counts(store):
    """The artifact is checked against itself: a stored rate that no longer
    matches the item sets it claims to summarise means something other than
    compute_diff wrote it (INV-023)."""
    store.execute("DELETE FROM perspective")
    _version(store, 2, diff={"added": [], "carried": 20, "novelty_rate": 0.9},
             ts=1.0)
    store.commit()

    w = read_window(store)
    assert w.nights[0].novelty == 0.0
    assert [n.version for n in w.drifted] == [2]
