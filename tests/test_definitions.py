"""Metric revision without silent breakage (P4 epic E2.8).

Done-when, both halves: no delta is ever computed across a definition boundary,
and a definition change is visible in the record.

The hook is a fault that already happened. "Novelty" named two quantities in
this codebase — the Perspective development share and `novelty_against_history`'s
embedding cosine — and both were reported, because a metric's meaning lived only
in the head of whoever last read the code.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from newz.evidence import definitions as D
from newz.evidence.baseline import OK, peek, take
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
DAY = 86400.0
W = 168.0
M = "claims_opened"


@pytest.fixture
def store(tmp_path):
    # E3A.1: the metric series lives in the monitor's own database,
    # attached as `mon`. It is created before the connection is opened,
    # because `open_db` attaches it only if the file is already there.
    from newz.monitor.db import open_monitor

    open_monitor(tmp_path / "d.db").close()
    conn = open_db(tmp_path / "d.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def _redefine(monkeypatch, metric: str, version: int, why: str | None):
    """Pin a different definition, as the registry would."""
    entry = {"version": version, "why": why} if why else {"version": version}
    monkeypatch.setattr(D, "version_of", lambda m, _v=version, _t=metric:
                        _v if m == _t else 1)
    monkeypatch.setattr(D, "reason_for", lambda m, v, _e=entry, _t=metric:
                        (_e.get("why") or "") if (m == _t and v == version)
                        else ("the original definition" if v <= 1 else ""))


def test_every_metric_pins_a_definition_version():
    """Behavior: the meaning is recorded rather than remembered."""
    assert D.version_of(M) >= 1
    assert D.reason_for(M, 1) == "the original definition"


def test_no_delta_is_computed_across_a_definition_boundary(store, monkeypatch):
    """Done-when, first half. Behavior: a figure computed one way is not
    subtracted from a figure computed another way and called a change."""
    now = time.time()
    take(store, M, 10.0, window_hours=W, now=now - 10 * DAY)
    assert peek(store, M, 4.0, window_hours=W, now=now).delta == -6.0

    _redefine(monkeypatch, M, 2, "counts refused claims too")

    r = peek(store, M, 4.0, window_hours=W, now=now)

    assert r.measured
    assert r.baseline is None, "the old series is not a baseline for the new one"
    assert r.delta is None


def test_the_prior_series_is_retained_and_stays_labelled(store, monkeypatch):
    """Done-when, second half. Behavior: readings taken under the old
    definition are kept and keep their version, so the seam is legible instead
    of the old numbers vanishing."""
    now = time.time()
    take(store, M, 10.0, window_hours=W, now=now - 10 * DAY)

    _redefine(monkeypatch, M, 2, "counts refused claims too")
    take(store, M, 4.0, window_hours=W, now=now)

    rows = store.execute(
        "SELECT value, definition_version FROM mon.metric_readings WHERE metric=?"
        " ORDER BY ts", (M,)).fetchall()

    assert [(r["value"], r["definition_version"]) for r in rows] == [(10.0, 1), (4.0, 2)]


def test_a_definition_change_is_recorded_with_its_reason(store, monkeypatch):
    """Behavior: the seam says why it exists, so a later reader knows the old
    baseline stopped meaning something rather than guessing."""
    now = time.time()
    take(store, M, 10.0, window_hours=W, now=now - 10 * DAY)

    _redefine(monkeypatch, M, 2, "counts refused claims too")

    assert D.sync(store, M, now=now) is True
    change = D.changes(store, M)[0]
    assert (change["from_version"], change["to_version"]) == (1, 2)
    assert change["reason"] == "counts refused claims too"


def test_a_version_bump_with_no_reason_is_refused(store, monkeypatch):
    """The failure this epic is named for, wearing a smaller hat: resetting a
    baseline without saying why the old one stopped meaning anything."""
    take(store, M, 10.0, window_hours=W, now=time.time() - 10 * DAY)

    _redefine(monkeypatch, M, 2, None)

    with pytest.raises(D.UnexplainedRevision, match="gives no reason"):
        D.sync(store, M)


def test_a_definition_does_not_go_backwards(store, monkeypatch):
    take(store, M, 10.0, window_hours=W, now=time.time() - 10 * DAY)
    _redefine(monkeypatch, M, 3, "widened")
    D.sync(store, M)

    _redefine(monkeypatch, M, 2, "narrowed again")

    with pytest.raises(D.UnexplainedRevision, match="does not go backwards"):
        D.sync(store, M)


def test_syncing_an_unchanged_definition_records_nothing(store):
    take(store, M, 10.0, window_hours=W, now=time.time() - 10 * DAY)

    assert D.sync(store, M) is False
    assert D.changes(store, M) == []


def test_a_definition_change_cannot_be_deleted(store, monkeypatch):
    """Consumer: 0035's trigger. Behavior: the seam is part of the record — it
    is why a delta stops at a particular date."""
    import sqlite3

    take(store, M, 10.0, window_hours=W, now=time.time() - 10 * DAY)
    _redefine(monkeypatch, M, 2, "counts refused claims too")
    D.sync(store, M)

    with pytest.raises(sqlite3.IntegrityError, match="why the series has a seam"):
        store.execute("DELETE FROM mon.metric_definition_changes")
