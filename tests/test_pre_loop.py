"""What the being was like before the loop (P4 W10).

PLAN uses "the pre-loop baseline" three times — the condition for holding stage
2, S8-E's read, and *nights slept falling below the pre-loop baseline*, the kill
condition Phase 8 calls the one that matters most — and nothing said what it
was, over what window, or who took it.

A halt whose threshold is a phrase fires when somebody decides it should.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from newz.evidence import pre_loop as P
from newz.store.db import open_db
from newz.store.migrations import apply_pending

REPO = Path(__file__).resolve().parent.parent
MAIN_SQL = REPO / "newz" / "store" / "sql" / "main"
DAY = 86400.0


@pytest.fixture
def store(tmp_path):
    # E3A.1: the series lives in the monitor's database, attached as `mon`.
    from newz.monitor.db import open_monitor

    open_monitor(tmp_path / "p.db").close()
    conn = open_db(tmp_path / "p.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def _readings(conn, metric: str, values, *, now: float, back: int = 0,
              per_day: int = 1):
    """Readings, oldest first, ending `back` days before `now`.

    `per_day` writes several within one day, which is what the hourly cadence
    does — the baseline must still count the day once (E3A.2).
    """
    for i, v in enumerate(values):
        day = now - (back + len(values) - i) * DAY
        for k in range(per_day):
            conn.execute(
                "INSERT INTO mon.metric_readings (ts, metric, status, value,"
                " window_hours, note, definition_version) VALUES (?,?,?,?,?,?,?)",
                (day + k * 3600.0, metric, "ok", v, 168.0, "", 1))
    conn.commit()


def test_it_is_not_taken_and_says_so(tmp_path, monkeypatch):
    """Behavior: the shape of the record is fixed while nothing is at stake,
    which is the only time it is cheap — the same order as INV-065's."""
    assert not P.taken()
    assert P.validate() == []


def test_an_untaken_baseline_is_readable_as_untaken():
    """P4 E3A.4 replaced `may_widen` — Phase 8 is struck, there are no autonomy
    stages, and a function whose only job was to gate one had no reader left
    (Rule 2). Behavior: `taken()` is what the daily email and the tool ask, and
    an untaken baseline answers plainly rather than by absence."""
    assert P.taken() is False
    assert not hasattr(P, "may_widen")


def test_nothing_to_fall_below_is_unreadable_not_a_pass(store):
    """INV-044 pointed at a kill condition. Behavior: reporting that nothing
    has fallen below nothing is a pass the measurement never made."""
    now = time.time()
    _readings(store, "nights_slept", [7], now=now)

    r = P.compare(store, "nights_slept", now=now)

    assert "unreadable" in r and "nothing to fall below" in r["unreadable"]


def test_the_proposal_is_the_median_of_the_series(store, monkeypatch):
    """Behavior: measured, never imputed — and the median rather than the mean,
    so one night the being did not sleep because it was being restarted does
    not lower the bar it is later held to."""
    now = time.time()
    _readings(store, "nights_slept", [7, 7, 6, 7, 0, 7, 7, 8], now=now)

    row = P.propose(store, ["nights_slept"], now=now)["nights_slept"]

    assert row["median"] == 7.0
    assert row["readings"] == 8 and len(row["reading_ids"]) == 8


def test_too_thin_a_series_is_refused_rather_than_averaged(store):
    """Behavior: the metrics are themselves 168-hour windows, so consecutive
    nightly readings overlap almost entirely — a handful of them describes a few
    days rather than a month, and calling that a baseline would set the bar the
    loop is judged against from noise."""
    now = time.time()
    _readings(store, "nights_slept", [7, 6, 7], now=now)

    row = P.propose(store, ["nights_slept"], now=now)["nights_slept"]

    assert "unreadable" in row and "one week seen once" in row["unreadable"]


def test_a_taken_baseline_reads_below_and_above(store, monkeypatch):
    """Behavior: the comparison the kill condition makes. Below is below."""
    now = time.time()
    monkeypatch.setattr(P, "registry", lambda: {
        "version": 1, "taken_at": now - 30 * DAY, "taken_by": "operator",
        "window_days": 28, "metrics": {"nights_slept": {"median": 7.0}}})

    _readings(store, "nights_slept", [4], now=now, back=2)
    assert P.compare(store, "nights_slept", now=now)["below"] is True

    _readings(store, "nights_slept", [9], now=now)
    assert P.compare(store, "nights_slept", now=now)["below"] is False


def test_a_baseline_that_names_no_reading_ids_is_refused(monkeypatch):
    """Behavior: the ids are what make it checkable rather than asserted — a
    median with nothing behind it is a number somebody chose."""
    monkeypatch.setattr(P, "registry", lambda: {
        "version": 1, "taken_at": 1.0, "taken_by": "operator", "window_days": 28,
        "metrics": {"nights_slept": {"median": 7.0, "readings": 8, "from": 1.0,
                                     "to": 2.0, "reading_ids": [1, 2]}}})

    assert any("ids" in e for e in P.validate())


def test_a_baseline_over_an_unregistered_metric_is_refused(monkeypatch):
    """Behavior: Rule 7 — a figure with no grade cannot be cited, and a
    threshold is a citation."""
    monkeypatch.setattr(P, "registry", lambda: {
        "version": 1, "taken_at": 1.0, "taken_by": "operator", "window_days": 28,
        "metrics": {"vibes": {"median": 7.0, "readings": 9, "from": 1.0,
                              "to": 2.0, "reading_ids": list(range(9))}}})

    assert any("not a registered metric" in e for e in P.validate())


def test_who_took_it_is_part_of_the_record(monkeypatch):
    """Behavior: a loop that takes its own baseline is not being judged by one,
    so the file records the hand as well as the number."""
    monkeypatch.setattr(P, "registry", lambda: {
        "version": 1, "taken_at": 1.0, "taken_by": None, "window_days": 28,
        "metrics": {"nights_slept": {"median": 7.0, "readings": 9, "from": 1.0,
                                     "to": 2.0, "reading_ids": list(range(9))}}})

    assert any("who took it" in e for e in P.validate())


def test_the_file_is_inside_the_hard_core():
    """Behavior: the loop reads it and can never write it."""
    from newz.evidence.hard_core import contains

    assert contains("evolution/pre_loop_baseline.yaml")


def test_the_window_is_stated_rather_than_assumed():
    reg = yaml.safe_load((REPO / "evolution" / "pre_loop_baseline.yaml").read_text())

    assert reg["window_days"] == 28
    assert reg["taken_at"] is None and reg["metrics"] == {}
