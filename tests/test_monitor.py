"""The monitor — hourly readings, its own database, the daily state (Phase 3A).

Each test closes a clause of an epic's `Done when`, and several of them would
have passed before the change they are asserting: the ones that matter are the
ones that would not.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.config import Config, LLMRole
from newz.monitor import db as mdb
from newz.monitor.run import turn
from newz.store.db import MONITOR_NAME, monitor_attached, open_db
from newz.store.migrations import apply_pending

REPO = Path(__file__).resolve().parent.parent
MAIN_SQL = REPO / "newz" / "store" / "sql" / "main"
HOUR = 3600.0


def _cfg(tmp_path, **kw) -> Config:
    return Config(
        repo_root=REPO,
        data_dir=tmp_path,
        main_db_path=tmp_path / "newz.db",
        interior_db_path=tmp_path / "interior.db",
        monitor_db_path=tmp_path / MONITOR_NAME,
        backups_dir=tmp_path / "backups",
        roles={"AMBIENT": LLMRole("AMBIENT", "http://localhost:9", "m")},
        monitor_send_hour=kw.pop("send_hour", 5),
        gmail_user="a@b", gmail_password="p", gmail_to="c@d",
        **kw,
    )


@pytest.fixture
def being(tmp_path):
    """A store with the metric tables where they used to be — pre-move."""
    conn = open_db(tmp_path / "newz.db", monitor=False)
    apply_pending(conn, MAIN_SQL)
    conn.execute(
        "INSERT INTO perspective (version, ts, content, diff_json, token_count)"
        " VALUES (1, ?, '# P', '{}', 1)", (time.time() - 4 * HOUR,))
    conn.commit()
    yield conn
    conn.close()


# ── E3A.1: the database, and the move ───────────────────────────────────

def test_the_move_carries_the_ids_and_leaves_the_being_s_store_without_them(being, tmp_path):
    """E3A.1's Done-when, and the reason it is not cosmetic: the surface records
    its provenance as the row ids it read (E3.3) and the pre-loop baseline pins
    the ids its median came from (INV-087). Behavior: the rows arrive with the
    ids they had, and `newz.db` holds neither table afterwards."""
    for i in (1, 2, 3):
        being.execute(
            "INSERT INTO metric_readings (id, ts, metric, status, value,"
            " window_hours, note, definition_version) VALUES (?,?,?,?,?,?,?,?)",
            (i * 7, 1000.0 + i, "nights_slept", "ok", float(i), 168.0, "", 1))
    being.commit()

    moved = mdb.move_from_main(tmp_path / "newz.db")

    assert moved["metric_readings"] == 3
    mon = mdb.open_monitor(tmp_path / "newz.db")
    assert [r[0] for r in mon.execute(
        "SELECT id FROM metric_readings ORDER BY id")] == [7, 14, 21]
    assert being.execute(
        "SELECT name FROM sqlite_master WHERE name='metric_readings'").fetchone() is None
    mon.close()


def test_moving_twice_is_the_same_as_moving_once(being, tmp_path):
    """Behavior: the move runs at the top of every hour, so it has to be safe
    to run when there is nothing to move — on a fresh clone the tables exist
    and are empty, and after the first move they are gone."""
    being.execute(
        "INSERT INTO metric_readings (ts, metric, status, value, window_hours,"
        " note, definition_version) VALUES (1.0,'nights_slept','ok',7.0,168.0,'',1)")
    being.commit()

    mdb.move_from_main(tmp_path / "newz.db")
    mdb.move_from_main(tmp_path / "newz.db")

    mon = mdb.open_monitor(tmp_path / "newz.db")
    assert mon.execute("SELECT COUNT(*) FROM metric_readings").fetchone()[0] == 1
    mon.close()


def test_a_reader_can_tell_an_absent_monitor_from_an_empty_one(being, tmp_path):
    """The distinction E3.5's rebuild turns on. A restore that did not bring the
    monitor database renders "no readings" — a page that looks correct and is
    wrong (INV-044). Behavior: `monitor_attached` answers which it is."""
    assert monitor_attached(being) is False

    mdb.open_monitor(tmp_path / "newz.db").close()
    with_mon = open_db(tmp_path / "newz.db")
    try:
        assert monitor_attached(with_mon) is True
    finally:
        with_mon.close()


def test_the_read_page_says_the_database_is_missing_rather_than_that_there_are_no_readings(being):
    """E3A.1's falsifier, made a test. Behavior: the two states render
    differently, because one is a fact about the restore and the other a fact
    about the being."""
    from newz.surface.generate import Manifest, _read

    text = _read(being, Manifest(generated_at=0.0))

    assert "monitor database is not attached" in text
    assert "No readings yet" not in text


# ── E3A.2: the readings, hourly, from outside ───────────────────────────

def test_a_turn_needs_nothing_of_the_being_but_its_store(being, tmp_path):
    """The monitor runs inside the being's process *(operator, 2026-08-21)*, so
    a dead being sends no report — silence is the alarm, and that is accepted.
    What a turn must NOT depend on is any of the being's live machinery:
    behavior — no scheduler, no client, no model, just the store on disk."""
    cfg = _cfg(tmp_path)
    being.close()

    t = turn(cfg, now=time.time(), transport=lambda m: None)

    assert t.readings > 0
    mon = mdb.open_monitor(cfg.main_db_path)
    assert mon.execute(
        "SELECT COUNT(*) FROM monitor_log WHERE kind='reading' AND ok=1"
    ).fetchone()[0] == 1
    mon.close()


def test_the_same_clock_hour_is_read_once(being, tmp_path):
    """Behavior: the cadence is the top of the hour, not every invocation. A
    second run inside the hour skips rather than doubling the series."""
    cfg = _cfg(tmp_path)
    now = time.time()

    first = turn(cfg, now=now, transport=lambda m: None)
    second = turn(cfg, now=now + 60.0, transport=lambda m: None)
    third = turn(cfg, now=now + HOUR + 60.0, transport=lambda m: None)

    assert first.readings > 0
    assert second.skipped and second.readings == 0
    assert third.readings > 0


def test_liveness_comes_from_rows_the_being_writes(being, tmp_path):
    """E3A.2's falsifier. Once the monitor writes the readings, the readings
    arrive forever — including for a being that stopped a week ago. Behavior:
    every liveness signal is a row only the being writes, so a stopped being
    ages visibly while the series keeps filling."""
    from newz.monitor.liveness import read

    now = time.time()
    signals = {s.name: s for s in read(being, tmp_path / "backups", now=now)}

    assert set(signals) == {"last sleep", "last episode", "last verified backup"}
    assert 3.9 < signals["last sleep"].age_h(now) < 4.1
    assert signals["last episode"].at is None          # the being recorded none
    assert signals["last verified backup"].unreadable  # and took no backup


def test_the_baseline_counts_days_and_not_readings(being, tmp_path):
    """P4 E3A.2, and the guard that would have degraded silently. `MIN_READINGS
    = 7` meant seven nights under the old cadence and seven HOURS under this
    one, while the comment explaining it still said a week. Behavior: seven
    hours of readings is not a baseline; seven days is — and the ids recorded
    are one per day, not one per hour."""
    from newz.evidence import pre_loop as P

    mdb.open_monitor(tmp_path / "newz.db").close()
    conn = open_db(tmp_path / "newz.db")
    now = time.time()
    try:
        for h in range(8):                       # eight readings, one day
            conn.execute(
                "INSERT INTO mon.metric_readings (ts, metric, status, value,"
                " window_hours, note, definition_version)"
                " VALUES (?,?,?,?,?,?,?)",
                (now - h * HOUR, "nights_slept", "ok", 7.0, 168.0, "", 1))
        conn.commit()
        one_day = P.propose(conn, ["nights_slept"], now=now)
        assert "unreadable" in one_day["nights_slept"]

        for d in range(1, 9):                     # eight days, 24 readings each
            for h in range(24):
                conn.execute(
                    "INSERT INTO mon.metric_readings (ts, metric, status, value,"
                    " window_hours, note, definition_version)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (now - d * 24 * HOUR - h * HOUR, "nights_slept", "ok",
                     7.0, 168.0, "", 1))
        conn.commit()
        eight_days = P.propose(conn, ["nights_slept"], now=now)
        total = conn.execute(
            "SELECT COUNT(*) FROM mon.metric_readings").fetchone()[0]
        days = conn.execute(
            "SELECT COUNT(DISTINCT date(ts,'unixepoch','localtime'))"
            " FROM mon.metric_readings").fetchone()[0]
    finally:
        conn.close()

    row = eight_days["nights_slept"]
    assert "unreadable" not in row
    assert total == 200, "the fixture did not write what this test assumes"
    assert row["readings"] == len(row["reading_ids"]) == days, \
        "the baseline recorded a reading per hour rather than a reading per day"


# ── E3A.3: the daily state ──────────────────────────────────────────────

def test_a_day_the_being_never_ran_still_produces_an_email_that_says_so(being, tmp_path):
    """E3A.3's Done-when, and the defect it replaced: firing the email on a
    Perspective row dated today meant no email at all on the night sleep was
    skipped — the ordinary failure, not the catastrophic one. Behavior: the
    send is on the clock, and the body reports the silence."""
    cfg = _cfg(tmp_path, send_hour=0)
    being.execute("DELETE FROM perspective")
    being.commit()
    being.close()
    sent: list = []

    t = turn(cfg, now=time.time(), transport=sent.append)

    assert t.sent and len(sent) == 1
    body = sent[0].get_content()
    assert "last sleep" in body and "never" in body


def test_the_day_is_not_sent_twice(being, tmp_path):
    cfg = _cfg(tmp_path, send_hour=0)
    now = time.time()
    sent: list = []

    turn(cfg, now=now, transport=sent.append)
    turn(cfg, now=now + 2 * HOUR, transport=sent.append)

    assert len(sent) == 1


def test_a_failed_send_is_recorded_and_not_raised(being, tmp_path):
    """Behavior: a monitor that stops because its mail server did is the failure
    this phase exists to avoid. The error is recorded, the turn returns, and the
    next hourly run tries again."""
    cfg = _cfg(tmp_path, send_hour=0)

    def unreachable(msg):
        raise OSError("no route to host")

    t = turn(cfg, now=time.time(), transport=unreachable)

    assert not t.sent
    assert "no route to host" in t.send_error
    mon = mdb.open_monitor(cfg.main_db_path)
    assert mon.execute(
        "SELECT COUNT(*) FROM monitor_log WHERE kind='send' AND ok=0"
    ).fetchone()[0] == 1
    mon.close()


def test_a_send_that_failed_is_tried_again_on_the_next_hour(being, tmp_path):
    """Behavior: `_sent_today` reads successful sends only, so a failed day is
    not a sent day."""
    cfg = _cfg(tmp_path, send_hour=0)
    now = time.time()

    def unreachable(msg):
        raise OSError("down")

    turn(cfg, now=now, transport=unreachable)
    sent: list = []
    second = turn(cfg, now=now + HOUR, transport=sent.append)

    assert second.sent and len(sent) == 1


def test_nothing_in_the_email_is_a_sentence_the_monitor_wrote(being, tmp_path):
    """R-R1, in its strongest form. The SEL ordered the loop's prose last and
    marked it unverified because a page of fluent reasoning is the worst
    available drift detector. Behavior: there is no prose to order — every line
    is a number, its method, or a heading."""
    from newz.monitor.report import compose

    mdb.open_monitor(tmp_path / "newz.db").close()
    conn = open_db(tmp_path / "newz.db")
    mon = mdb.open_monitor(tmp_path / "newz.db")
    try:
        body = compose(conn, mon, REPO, tmp_path / "backups", now=time.time())
    finally:
        conn.close()
        mon.close()

    # The header states the rules the page is written under; every other line
    # is a heading, a rule, a figure or a reason an instrument could not read.
    banned = ("I think", "suggests", "appears to", "we should", "recommend")
    for phrase in banned:
        assert phrase not in body, f"the monitor authored a judgment: {phrase!r}"
    assert "UNREADABLE" in body


def test_no_model_is_called_anywhere_in_a_turn(being, tmp_path, monkeypatch):
    """Rule 4 is untouched because nothing here judges. Behavior: a turn that
    reached an LLM would fail this, whatever it did with the answer."""
    import newz.llm.client as client

    def refuse(*a, **k):
        raise AssertionError("the monitor called a model")

    monkeypatch.setattr(client.LLMClient, "complete", refuse, raising=False)
    turn(_cfg(tmp_path), now=time.time(), transport=lambda m: None)


# ── the rhythm belongs to the being ─────────────────────────────────────

def test_the_monitor_is_a_scheduler_in_the_beings_process():
    """*(operator, 2026-08-21)* — one process to start. Behavior: the being
    launches the monitor among its background tasks, and `tools/monitor.py` is
    a one-shot for a reading between hours rather than a second rhythm."""
    from newz.monitor.run import MonitorScheduler

    runner = (REPO / "tools" / "run_newz.py").read_text()
    assert "MonitorScheduler(cfg)" in runner
    assert "monitor.run()" in runner

    tool = (REPO / "tools" / "monitor.py").read_text()
    assert "loop(" not in tool, "the tool must not start a second rhythm"


def test_the_scheduler_never_raises_into_the_ambient_loop(tmp_path, monkeypatch):
    """A reading that cannot be taken is a hole in the series; a monitor that
    raises into the being's task group is an outage. Behavior: the turn's
    failure is logged and the scheduler keeps its rhythm."""
    import asyncio

    from newz.monitor.run import MonitorScheduler

    calls: list[int] = []

    def explode(cfg, **kw):
        calls.append(1)
        raise RuntimeError("the store is gone")

    monkeypatch.setattr("newz.monitor.run.turn", explode)
    sched = MonitorScheduler(_cfg(tmp_path), check_interval_s=0.01)

    async def drive():
        task = asyncio.create_task(sched.run())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(drive())
    assert len(calls) > 1, "the scheduler stopped at the first failure"
