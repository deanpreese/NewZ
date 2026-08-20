"""The baseline-and-delta layer (P4 epic E2.7).

Done-when: every baselined metric reports through it, and **a gapped or missing
window reports as such rather than as a number**. That second clause is
INV-044 generalised — the invariant was written for one figure and every metric
has the same two failure modes.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from newz.evidence import baseline as B
from newz.evidence.baseline import INCOMPLETE, OK, UNREADABLE, peek, series, take
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
HOUR = 3600.0
DAY = 86400.0
W = 168.0


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "b.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def test_a_delta_is_measured_against_before_the_window_opened(store):
    """The point of the layer. Behavior: the baseline is the last reading from
    OUTSIDE the window, so two reads an hour apart do not compare a window to
    itself and report every delta as zero."""
    now = time.time()
    take(store, "claims_opened", 1.0, window_hours=W, now=now - 10 * DAY)

    r = peek(store, "claims_opened", 4.0, window_hours=W, now=now)

    assert r.measured and r.baseline == 1.0
    assert r.delta == 3.0


def test_the_first_reading_has_no_baseline_and_says_so(store):
    r = peek(store, "claims_opened", 4.0, window_hours=W)

    assert r.measured and r.baseline is None and r.delta is None
    assert "no baseline yet" in r.render()


def test_a_missing_input_is_unreadable_and_never_zero(store):
    """INV-044, generalised. Behavior: nothing was measured, and the read says
    that rather than reporting a compliant zero.

    The invariant exists because the §9.1 ingest share is computed from a call
    log that does not travel with a clone, and an instrument answering "is
    ingest under the cap?" with 0% has reported compliance it did not measure."""
    r = peek(store, "claims_declined", None, window_hours=W,
             unreadable="no call log; declines are not in the store by design")

    assert r.status == UNREADABLE
    assert r.value is None and r.delta is None
    assert "UNREADABLE" in r.render() and "not in the store by design" in r.render()


def test_a_window_the_input_does_not_cover_is_incomplete(store):
    """E2.7's other clause. Behavior: a seven-day rate over four days of data is
    a real number over a shorter period, and printing it as a seven-day rate is
    the same lie in a quieter voice."""
    now = time.time()

    r = peek(store, "claims_opened", 4.0, window_hours=W,
             covers_from=now - 4 * DAY, now=now)

    assert r.status == INCOMPLETE
    assert r.value is None
    assert "not the one asked for" in r.note


def test_a_reading_that_measured_nothing_is_still_kept(store):
    """Behavior: holes stay in the series, because a later reader needs to see
    them. Dropping them would make the record of a measurement look continuous
    when the measurement was not."""
    take(store, "claims_declined", None, window_hours=W, unreadable="no call log")
    take(store, "claims_declined", 3.0, window_hours=W)

    rows = series(store, "claims_declined")

    assert len(rows) == 2
    assert {r["status"] for r in rows} == {UNREADABLE, OK}


def test_an_unmeasured_reading_is_not_used_as_a_baseline(store):
    """Behavior: a hole cannot become the thing a later delta is measured
    against — otherwise "unreadable" would silently mean zero one step later."""
    now = time.time()
    take(store, "claims_opened", None, window_hours=W,
         unreadable="no log", now=now - 10 * DAY)

    r = peek(store, "claims_opened", 4.0, window_hours=W, now=now)

    assert r.baseline is None


def test_the_reader_does_not_write_the_series(store):
    """The mistake this epic nearly repeated. Behavior: `peek` writes nothing,
    because a series written whenever someone runs a tool is a record of when
    they looked, and its deltas measure attention rather than change."""
    peek(store, "claims_opened", 4.0, window_hours=W)

    assert store.execute("SELECT COUNT(*) FROM metric_readings").fetchone()[0] == 0


def test_every_baselined_metric_has_a_writer(store, tmp_path):
    """E2.7's Done-when. Behavior: a metric the registry marks `baselined` must
    be produced by record_all, so the flag cannot claim a series nobody writes."""
    readings = B.record_all(store, tmp_path)

    assert {r.metric for r in readings} == set(B.baselined_metrics())
    assert store.execute(
        "SELECT COUNT(*) FROM metric_readings").fetchone()[0] == len(readings)


def test_a_baselined_metric_with_no_writer_is_refused(store, tmp_path, monkeypatch):
    """The guard on that guarantee: marking a metric baselined without giving it
    a writer fails loudly rather than producing a silent hole in the series."""
    real = B.baselined_metrics()
    monkeypatch.setattr(B, "baselined_metrics",
                        lambda: sorted(set(real) | {"invented_metric"}))

    with pytest.raises(KeyError, match="must have a writer"):
        B.record_all(store, tmp_path)
