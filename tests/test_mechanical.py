"""The mechanical set (P4 epic E2.9).

**Mechanical means no model judgment anywhere between the world and the
number.** That is the whole qualification for a figure that may carry a
decision (Rule 4), and it is why these are the metrics P4 Phase 8's gate is
allowed to consist of.

Done-when: each reports through E2.7 with a baseline, and S2-E is read off them
rather than assembled by hand.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.evidence import mechanical as M
from newz.evidence.baseline import baselined_metrics, record_all
from newz.evidence.grades import grade_of
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
DAY = 86400.0


@pytest.fixture
def store(tmp_path):
    # E3A.1: the metric series lives in the monitor's own database,
    # attached as `mon`. It is created before the connection is opened,
    # because `open_db` attaches it only if the file is already there.
    from newz.monitor.db import open_monitor

    open_monitor(tmp_path / "m.db").close()
    conn = open_db(tmp_path / "m.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def test_nights_slept_counts_perspective_versions(store):
    """kill:nights-slept's instrument. P4 Phase 8: development is measured in
    nights, not commits, and a loop that costs sleep is subtracting."""
    now = time.time()
    for i in range(3):
        store.execute("INSERT INTO perspective (version, ts, content,"
                      " token_count, writer) VALUES (?,?,?,?,?)",
                      (i + 1, now - i * DAY, "...", 3, "sleep"))
    store.commit()

    assert M.nights_slept(store, since=now - 7 * DAY).value == 3.0
    assert M.hours_since_last_sleep(store, now=now).value == pytest.approx(0, abs=0.1)


def test_hours_since_last_sleep_is_unreadable_before_the_first_night(store):
    """INV-044: no Perspective has ever been written is not zero hours."""
    v = M.hours_since_last_sleep(store, now=time.time())

    assert v.value is None and "ever been written" in v.unreadable


def test_pieces_revisions_and_retractions_are_counted_with_their_causes(store):
    """S2-E's own figures. Behavior: the cause is the being's reason at the time,
    read and never re-derived."""
    now = time.time()
    store.execute(
        "INSERT INTO works (ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (now, "concern", 1, "q", "because", "t", "b", 1, "m", 1))
    for kind, reason in (("revised", "the base effect was mine, not the market's"),
                         ("retracted", "its central claim does not survive")):
        store.execute(
            "INSERT INTO work_revisions (ts, work_id, kind, reason, prior_title,"
            " prior_body, prior_word_count) VALUES (?,?,?,?,?,?,?)",
            (now, 1, kind, reason, "t", "b", 1))
    store.commit()

    assert M.pieces_written(store, since=now - DAY).value == 1.0
    assert M.works_revised(store, since=now - DAY).value == 1.0
    assert M.works_retracted(store, since=now - DAY).value == 1.0
    causes = M.revision_causes(store, since=now - DAY)
    assert ("retracted", "its central claim does not survive") in causes


def test_a_table_the_store_has_not_migrated_reads_unmeasured(store, monkeypatch):
    """INV-044 reaches further than anyone expects. Behavior: an instrument run
    against a store mid-upgrade reports that it could not read, rather than
    answering 0 and asserting a fact it never saw."""
    store.execute("DROP TABLE work_revisions")

    v = M.works_revised(store, since=time.time() - DAY)

    assert v.value is None
    assert "has not taken this migration" in v.unreadable


def test_every_mechanical_metric_is_graded_mechanical_or_says_why_not():
    """Rule 7 against E2.9's own claim. Behavior: the set is mechanical except
    where the audit found otherwise, and those exceptions are stated rather
    than reconciled away."""
    for name in ("nights_slept", "hours_since_last_sleep", "pieces_written",
                 "works_revised", "works_retracted", "source_gaps_open",
                 "deliberation_token_share"):
        assert grade_of(name) == "mechanical", name

    # P4's E2.9 lists both among "all graded mechanical"; the audit disagreed.
    assert grade_of("single_source_positions") == "known-biased"
    assert grade_of("feeds_contributing_a_read") == "model-graded"


def test_every_metric_in_the_set_reports_through_the_baseline_layer(store, tmp_path):
    """E2.9's Done-when. Behavior: the mechanical set is written by the same
    cadence as everything else, so each one carries a series."""
    readings = record_all(store, tmp_path)
    produced = {r.metric for r in readings}

    assert produced == set(baselined_metrics())
    for name in ("nights_slept", "pieces_written", "works_retracted"):
        assert name in produced


def test_the_single_source_flag_is_a_share_of_positions_not_of_episodes(store):
    """INV-033's flag, counted per position — v1's 56%-from-two-outlets
    anti-pattern made visible where a position lives rather than across a
    corpus average that hides it."""
    v = M.single_source_positions(store)

    assert v.value is None and "ever been written" in v.unreadable
