"""The hourly turn, and the daily send (P4 E3A.2, E3A.3).

One function does both, because they are one rhythm: every hour the
instrumentation is read and saved, and on the first run at or after the send
hour the day's state goes out.

**The send is on the clock, never on sleep completing.** `SleepScheduler`
yields the night when the store is busy and simply tries again, so a report
triggered by a Perspective row is silent on exactly the night sleep was
skipped — the ordinary failure, not the catastrophic one. Sleep is reported,
not awaited.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from newz.monitor import db as mdb

logger = logging.getLogger(__name__)


@dataclass
class Turn:
    readings: int = 0
    unmeasured: int = 0
    sent: bool = False
    send_error: str = ""
    skipped: str = ""


def _hour_taken(mon, now: float) -> bool:
    """Has this clock hour already been read? The cadence's idempotence."""
    row = mon.execute(
        "SELECT MAX(ts) FROM monitor_log WHERE kind='reading' AND ok=1").fetchone()
    last = row[0] if row else None
    if last is None:
        return False
    return (time.localtime(last)[:4]) == (time.localtime(now)[:4])


def _sent_today(mon, now: float) -> bool:
    row = mon.execute(
        "SELECT MAX(ts) FROM monitor_log WHERE kind='send' AND ok=1").fetchone()
    last = row[0] if row else None
    if last is None:
        return False
    return time.localtime(last)[:3] == time.localtime(now)[:3]


def turn(cfg, *, now: float | None = None, transport=None) -> Turn:
    """One hour's work: read, save, and send if the day's send is due."""
    from newz.evidence.baseline import record_all
    from newz.monitor.mail import send
    from newz.monitor.report import compose
    from newz.store.db import open_db

    now = now or time.time()
    t = Turn()
    mdb.move_from_main(cfg.main_db_path, now=now)
    mon = mdb.open_monitor(cfg.main_db_path)
    conn = open_db(cfg.main_db_path)
    try:
        if _hour_taken(mon, now):
            t.skipped = "this hour already read"
        else:
            try:
                readings = record_all(conn, cfg.repo_root, now=now)
                t.readings = len(readings)
                t.unmeasured = len([r for r in readings if not r.measured])
                mdb.log(mon, "reading", True,
                        f"{t.readings} reading(s), {t.unmeasured} unmeasured",
                        now=now)
            except Exception as e:                       # noqa: BLE001
                mdb.log(mon, "reading", False, f"{type(e).__name__}: {e}", now=now)
                logger.exception("monitor: reading failed")

        due = time.localtime(now).tm_hour >= cfg.monitor_send_hour
        if due and not _sent_today(mon, now):
            try:
                body = compose(conn, mon, cfg.repo_root, cfg.backups_dir, now=now)
                subject = "NewZ — " + time.strftime(
                    "%Y-%m-%d", time.localtime(now))
                t.send_error = send(subject, body, user=cfg.gmail_user,
                                    password=cfg.gmail_password, to=cfg.gmail_to,
                                    transport=transport)
            except Exception as e:                       # noqa: BLE001
                # `send` catches what SMTP raises; this catches everything the
                # report could raise while composing. Either way the monitor
                # keeps its rhythm — a monitor that stops because one number
                # could not be read is the failure this phase exists to avoid.
                t.send_error = f"{type(e).__name__}: {e}"
            t.sent = not t.send_error
            mdb.log(mon, "send", t.sent, t.send_error, now=now)
            if t.send_error:
                # Recorded and retried on the next hourly run. A monitor that
                # stops because its mail server did is the failure this phase
                # exists to avoid.
                logger.warning("monitor: send failed — %s", t.send_error)
    finally:
        conn.close()
        mon.close()
    return t


class MonitorScheduler:
    """Hourly, inside the being's process *(operator, 2026-08-21)*.

    An earlier design ran this as a second command beside the being, so that a
    dead being still produced a report saying so. The operator's decision is one
    process, and it carries a cost worth stating rather than burying: **if the
    being's process dies there is no email at all**, and silence is the alarm.
    Every partial failure is still reported — a skipped night, a stalled
    scheduler, a backup that no longer restores — because the send is on the
    clock and the liveness lines read rows the being writes rather than the
    readings themselves.

    `turn` is idempotent per clock hour and per day, so the check interval only
    has to be finer than an hour; it is not the cadence.
    """

    def __init__(self, cfg, *, check_interval_s: float = 900.0):
        self._cfg = cfg
        self._interval = check_interval_s

    async def run(self) -> None:
        import asyncio

        from newz.crash import log_crash

        logger.info("monitor: hourly, sending at or after %02d:00",
                    self._cfg.monitor_send_hour)
        while True:
            try:
                t = await asyncio.to_thread(turn, self._cfg)
                if t.readings:
                    logger.info("monitor: %d reading(s), %d unmeasured%s",
                                t.readings, t.unmeasured,
                                ", sent" if t.sent else "")
            except asyncio.CancelledError:
                raise
            except Exception:
                # The monitor must never take the being down with it. A reading
                # that cannot be taken is a hole in the series; a monitor that
                # raises into the ambient loop is an outage.
                log_crash(self._cfg.repo_root, "monitor")
                logger.exception("monitor: turn failed — retrying next check")
            await asyncio.sleep(self._interval)
