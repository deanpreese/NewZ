"""One windowed comparison, used by every metric that carries one (P4 E2.7).

**The gap this closes.** The project's deltas exist only as prose. *"Advance
acceptance rose 28.3% → 41.1% where P2 expected a fall"* was computed by hand,
once, inside an argument — and nothing has noticed it move since. A number
without a baseline is a snapshot; steering needs a series.

**INV-044, generalised.** That invariant says a measurement whose input is
missing reports itself unmeasured, never as a compliant zero. It was written for
one figure — the §9.1 ingest share, computed from a call log that does not
travel with a clone. Every metric has the same failure mode, and two of them:

  `unreadable`   the input is absent. Nothing was measured. Not zero.
  `incomplete`   the input exists and does not cover the window. A seven-day
                 rate over four days of data is not a seven-day rate, and
                 printing it as one is the same lie in a quieter voice.

**Every reading is kept, including the ones that measured nothing.** A reader
needs to see the hole; dropping those rows would make the record of a
measurement look continuous when the measurement was not.

**Readings are recorded on a cadence, never on read.** A series written when
someone happens to run a tool is a record of when they looked, and its deltas
measure attention rather than change. `record_all` is the writer and runs
nightly; `peek` is what readers use, and it writes nothing.

**A baseline is the last reading before this window opened**, not the last
reading of any kind — otherwise two reads an hour apart compare a window to
itself and every delta is zero.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass

from newz.evidence.grades import grade_of, tag

logger = logging.getLogger(__name__)

OK, INCOMPLETE, UNREADABLE = "ok", "incomplete", "unreadable"


@dataclass(frozen=True)
class Reading:
    metric: str
    status: str
    value: float | None
    window_hours: float
    note: str = ""
    baseline: float | None = None
    baseline_ts: float | None = None

    @property
    def measured(self) -> bool:
        return self.status == OK

    @property
    def delta(self) -> float | None:
        if not self.measured or self.baseline is None:
            return None
        return self.value - self.baseline

    @property
    def grade(self) -> str:
        return grade_of(self.metric)

    def render(self, *, note: str = "", width: int = 28) -> str:
        """One line: the value, what it moved from, and its grade."""
        label = self.metric.replace("_", " ")
        if not self.measured:
            return (f"    {label:<{width}} {self.status.upper():>8}   "
                    f"{tag(self.metric, note=note)}\n        {self.note}")
        shown = f"{self.value:>8.4g}"
        if self.delta is None:
            move = "  (first reading — no baseline yet)"
        elif abs(self.delta) < 1e-12:
            move = "  (unchanged)"
        else:
            move = (f"  ({self.delta:+.4g} from {self.baseline:.4g},"
                    f" {(time.time() - self.baseline_ts) / 86400:.0f}d ago)")
        return f"    {label:<{width}} {shown}   {tag(self.metric, note=note)}{move}"


def _baseline(conn: sqlite3.Connection, metric: str, *, window_hours: float,
              now: float) -> tuple[float | None, float | None]:
    """The last measured reading from before this window opened."""
    try:
        row = conn.execute(
            "SELECT ts, value FROM metric_readings WHERE metric=? AND status=?"
            " AND ts <= ? ORDER BY ts DESC LIMIT 1",
            (metric, OK, now - window_hours * 3600.0)).fetchone()
    except sqlite3.OperationalError:
        # A store that has not taken 0034 yet has no series. No baseline is
        # the honest answer, and it is not an error — the first reading of
        # anything has none either.
        return (None, None)
    return (row["value"], row["ts"]) if row else (None, None)


def peek(conn: sqlite3.Connection, metric: str, value: float | None, *,
         window_hours: float = 168.0, covers_from: float | None = None,
         unreadable: str | None = None, now: float | None = None) -> Reading:
    """Compare a value to its recorded baseline. Writes nothing.

    What every reader uses. The series is written on a cadence by `record_all`,
    because a series written whenever someone looks is a record of when they
    looked.
    """
    now = now or time.time()
    opened = now - window_hours * 3600.0

    if unreadable:
        status, value, note = UNREADABLE, None, unreadable
    elif value is None:
        status, note = UNREADABLE, "no value produced and no reason given"
    elif covers_from is not None and covers_from > opened:
        short = (covers_from - opened) / 3600.0
        status, note = INCOMPLETE, (
            f"the input begins {short:.0f}h into a {window_hours:.0f}h window; "
            "this is a real number over a shorter period, not the one asked for")
    else:
        status, note = OK, ""

    base, base_ts = _baseline(conn, metric, window_hours=window_hours, now=now)
    return Reading(metric, status, value if status == OK else None,
                   window_hours, note, base, base_ts)


def take(conn: sqlite3.Connection, metric: str, value: float | None, *,
         window_hours: float = 168.0, covers_from: float | None = None,
         unreadable: str | None = None, now: float | None = None) -> Reading:
    """`peek`, and keep it. The cadence's writer.

    `covers_from` is the earliest moment the input actually speaks for. If it
    is later than the window opened, the window has a hole and the reading is
    INCOMPLETE — the figure is real and it is not the figure that was asked for.
    """
    r = peek(conn, metric, value, window_hours=window_hours,
             covers_from=covers_from, unreadable=unreadable, now=now)
    conn.execute(
        "INSERT INTO metric_readings (ts, metric, status, value, window_hours,"
        " note) VALUES (?,?,?,?,?,?)",
        (now or time.time(), metric, r.status, r.value, window_hours, r.note))
    conn.commit()
    return r


def series(conn: sqlite3.Connection, metric: str, *, limit: int = 20) -> list[sqlite3.Row]:
    """Every reading, holes included — the point of keeping them."""
    return conn.execute(
        "SELECT ts, status, value, window_hours, note FROM metric_readings"
        " WHERE metric=? ORDER BY ts DESC LIMIT ?", (metric, limit)).fetchall()


# ── the cadence ─────────────────────────────────────────────────────────

BASELINE_WINDOW_H = 168.0


def baselined_metrics() -> list[str]:
    """Metrics the registry says carry a baseline (E2.5's `baselined:` flag)."""
    import yaml

    from newz.evidence.grades import REGISTRY

    data = yaml.safe_load(REGISTRY.read_text()) or {}
    return sorted(n for n, row in (data.get("metrics") or {}).items()
                  if (row or {}).get("baselined"))


def record_all(conn: sqlite3.Connection, repo_root, *,
               window_hours: float = BASELINE_WINDOW_H,
               now: float | None = None) -> list[Reading]:
    """Take one reading of every baselined metric. The series' only writer."""
    from newz.evidence.consequence import read as read_consequence

    now = now or time.time()
    c = read_consequence(conn, repo_root, now=now, hours=window_hours)
    values: dict[str, tuple] = {
        "advances_offered": (c.door.advances, None),
        "claims_opened": (c.door.opened, None),
        "claims_refused": (c.door.refused, None),
        "claims_declined": (c.door.declined, c.door.unreadable),
        "positions_changed_by_world": (c.positions.by_world, None),
        "positions_changed_by_operator": (c.positions.by_operator, None),
        "positions_changed_by_self": (c.positions.by_self, None),
        "concerns_refused": (c.opener.refused, None),
    }
    missing = set(baselined_metrics()) - set(values)
    if missing:
        raise KeyError(
            f"registry marks {sorted(missing)} baselined and record_all does not "
            "produce them — a metric that carries a baseline must have a writer")
    return [take(conn, name, v, window_hours=window_hours, unreadable=why, now=now)
            for name, (v, why) in values.items()]


class MetricScheduler:
    """Nightly. The cadence is the being's, not the operator's attention."""

    def __init__(self, db_path, repo_root, *, hour: int = 4,
                 check_interval_s: float = 900.0):
        self._db_path = db_path
        self._repo_root = repo_root
        self._hour = hour
        self._interval = check_interval_s

    def _due(self, conn, now: float) -> bool:
        import datetime as _dt

        if _dt.datetime.fromtimestamp(now).hour < self._hour:
            return False
        row = conn.execute(
            "SELECT MAX(ts) FROM metric_readings").fetchone()[0]
        if row is None:
            return True
        return (_dt.datetime.fromtimestamp(row).date()
                < _dt.datetime.fromtimestamp(now).date())

    def _turn(self) -> None:
        from newz.store.db import open_db

        conn = open_db(self._db_path)
        try:
            now = time.time()
            if self._due(conn, now):
                readings = record_all(conn, self._repo_root, now=now)
                holes = [r for r in readings if not r.measured]
                logger.info("metrics recorded: %d readings, %d unmeasured",
                            len(readings), len(holes))
        finally:
            conn.close()

    async def run(self) -> None:
        import asyncio

        from newz.crash import log_crash

        logger.info("metric readings: nightly at or after %02d:00", self._hour)
        while True:
            try:
                await asyncio.to_thread(self._turn)
            except asyncio.CancelledError:
                raise
            except Exception:
                log_crash(self._db_path.parent.parent, "metric readings")
                logger.exception("metric reading failed — retrying next check")
            await asyncio.sleep(self._interval)
