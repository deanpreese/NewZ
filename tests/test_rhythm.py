"""Writing as a rhythm (P4 epic E2.1).

Its Done-when has three clauses and each has a test here: pieces appear on
cadence without being asked for, a killed session costs that session and
nothing else, and the ceiling caps attempts rather than products.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.works.rhythm import MAX_STARTS_PER_DAY, WritingScheduler, starts_today, write_once
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "r.db")
    apply_pending(conn, MAIN_SQL)
    for i in range(4):
        conn.execute(
            "INSERT INTO concerns (opened_at, kind, statement, why_open,"
            " closing_condition, status, salience, origin)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (time.time(), "inquiry", f"Does the index roll over? #{i}",
             "it bears on what I hold",
             "the statistical office publishes its March release",
             "open", 0.5, "reading"))
    conn.commit()
    yield conn
    conn.close()


class FakeLLM:
    """Chooses the first candidate and writes a short piece."""

    def __init__(self, fail_on: int | None = None):
        self.calls = 0
        self._fail_on = fail_on

    def complete(self, role, system, user, **kw):
        self.calls += 1
        if self._fail_on is not None and self.calls >= self._fail_on:
            raise RuntimeError("the model went away mid-session")

        class R:
            text = ""
            model = "fake"
            completion_tokens = 12
            truncated = False
        if "<choice>" in user:
            R.text = ("<choice><ref>concern:1</ref><because>it is the one I"
                      " keep returning to</because></choice>")
        else:
            R.text = ("<piece><title>On rolling over</title><body>" +
                      ("A sentence about the index. " * 40) + "</body></piece>")
        return R


def test_a_piece_appears_without_being_asked_for(store):
    """Consumer: newz/works/rhythm.py's scheduler. Behavior: one turn of the
    cadence produces a work with no operator in the loop — Rule 5's "production
    is a rhythm; only judgment is an initiative"."""
    r = write_once(store, FakeLLM())

    assert r.wrote and r.work_id
    assert store.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 1


def test_the_ceiling_caps_attempts_and_not_products(store):
    """R-25. Consumer: write_once's first check. Behavior: the cap counts rows
    in work_attempts, so a turn that produced nothing has still spent one.

    An outcome-based budget charges nothing for failure, so a session that dies
    mid-composition is free and retryable without limit — which is how a
    restart loop becomes unbounded spend."""
    for _ in range(MAX_STARTS_PER_DAY):
        with pytest.raises(RuntimeError):
            write_once(store, FakeLLM(fail_on=1))

    assert store.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 0
    assert starts_today(store) == MAX_STARTS_PER_DAY

    r = write_once(store, FakeLLM())

    assert r.skipped and "already started" in r.skipped
    assert store.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 0, \
        "the ceiling must bind on starts even when nothing was ever produced"


def test_a_killed_session_costs_that_session_and_nothing_else(store):
    """Consumer: the attempt row. Behavior: a turn that dies mid-composition
    leaves one charged attempt, its reason, and no partial work — the next
    cadence tick simply begins again."""
    with pytest.raises(RuntimeError):
        write_once(store, FakeLLM(fail_on=2))

    row = store.execute("SELECT outcome, note FROM work_attempts").fetchone()
    assert row["outcome"] == "failed"
    assert "went away" in row["note"]
    assert store.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 0

    assert write_once(store, FakeLLM()).wrote, "the next turn is unimpeded"


def test_the_attempt_is_charged_before_anything_is_spent(store):
    """R-18's rule for writing. Behavior: the row exists before the first model
    call, so a process killed between the two still paid."""
    class DiesImmediately:
        def complete(self, *a, **kw):
            raise KeyboardInterrupt("killed before the model answered")

    with pytest.raises(KeyboardInterrupt):
        write_once(store, DiesImmediately())

    assert starts_today(store) == 1


def test_having_nothing_left_to_write_about_is_recorded_not_silent(store):
    """Consumer: work_attempts. Behavior: a rhythm with no unwritten subject
    records the turn, so "nothing to say" is distinguishable from "never ran"."""
    store.execute("UPDATE concerns SET status='closed'")
    store.commit()

    r = write_once(store, FakeLLM())

    assert r.skipped == "no unwritten subject"
    assert store.execute(
        "SELECT outcome FROM work_attempts").fetchone()["outcome"] == "no_subject"


def test_the_rhythm_stands_off_sleep(store, tmp_path):
    """R-20's lesson, carried. Behavior: the cadence defers inside the
    consolidation window rather than competing with it for the store."""
    import datetime as dt

    s = WritingScheduler(tmp_path / "r.db", FakeLLM(), quiet_hour=3,
                         quiet_span_h=1.5)

    assert s._in_quiet_window(dt.datetime(2026, 8, 20, 3, 30))
    assert not s._in_quiet_window(dt.datetime(2026, 8, 20, 5, 0))


def test_writing_a_piece_recomputes_what_the_corpus_is_about(store):
    """E2.4's writer. Consumer: newz/works/subjects.py's work_tags, read by
    tools/read_works.py --subjects. Behavior: a new piece changes what is
    distinctive across the corpus, so the tags are recomputed when one lands —
    which keeps the reader a reader.

    Asserted as agreement between the stored table and a fresh computation,
    not as a tag count: in a corpus of one nothing is distinctive, and zero
    tags is the correct answer rather than a failure."""
    from newz.works.subjects import compute

    write_once(store, FakeLLM())

    stored = {(r["work_id"], r["tag"]) for r in
              store.execute("SELECT work_id, tag FROM work_tags")}
    fresh = {(wid, tag) for wid, tags in compute(store).tags.items()
             for tag, _ in tags}

    assert stored == fresh


def test_a_failed_tag_recompute_does_not_cost_the_piece(store, monkeypatch):
    """Behavior: tags are a read of the work, never the point of it. If the
    computation fails the piece still stands, because losing a piece to a
    bookkeeping error would be the tail wagging the dog."""
    import newz.works.subjects as subjects

    monkeypatch.setattr(subjects, "recompute",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))

    r = write_once(store, FakeLLM())

    assert r.wrote
    assert store.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 1
