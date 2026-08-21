"""Is the being alive? (P4 E3A.2)

**The readings cannot answer this any more, and that is the point.** While the
being wrote its own metric series, a missing reading meant the being was down.
The monitor now writes the series from outside, so readings arrive on the hour
forever — including for a being that stopped a week ago. A signal that keeps
arriving after its subject has stopped is not a signal.

So liveness is read from rows **only the being writes**: the last episode it
recorded, the last Perspective it consolidated, the last backup it verified.
Each is reported as an age, never as a boolean, because "how long since" is the
fact and "alive" is a judgment with a threshold in it.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Signal:
    name: str
    at: float | None            # when it last happened
    unreadable: str = ""

    def age_h(self, now: float) -> float | None:
        return None if self.at is None else (now - self.at) / 3600.0

    def line(self, now: float) -> str:
        if self.unreadable:
            return f"{self.name:<24} UNREADABLE   {self.unreadable}"
        if self.at is None:
            return f"{self.name:<24} never"
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.at))
        return f"{self.name:<24} {self.age_h(now):>6.1f}h ago   {stamp}"


def _max_ts(conn: sqlite3.Connection, table: str, column: str = "ts") -> Signal:
    try:
        row = conn.execute(f"SELECT MAX({column}) FROM {table}").fetchone()
    except sqlite3.OperationalError as e:
        return Signal(table, None, unreadable=str(e))
    return Signal(table, row[0] if row else None)


def read(conn: sqlite3.Connection, backups_dir: Path,
         *, now: float | None = None) -> list[Signal]:
    """Every being-written signal, oldest fact first. Never a verdict."""
    now = now or time.time()
    out = [
        Signal("last sleep", _max_ts(conn, "perspective").at),
        Signal("last episode", _max_ts(conn, "episodes").at),
    ]
    out.append(_newest_backup(backups_dir))
    return out


def _newest_backup(backups_dir: Path) -> Signal:
    """The newest backup that actually restores — `verify`, not `glob`.

    A file that opens and answers a count is not a backup (R-37e), and the
    monitor reporting a hollow one as recent is the same class of error as
    reporting a dead being as alive.
    """
    from newz.surface.cleanroom import newest_backup, verify

    newest = newest_backup(backups_dir)
    if newest is None:
        return Signal("last verified backup", None,
                      unreadable=f"no backup in {backups_dir}")
    try:
        verify(newest)
    except sqlite3.Error as e:
        return Signal("last verified backup", None,
                      unreadable=f"{newest.name} does not restore ({e})")
    return Signal("last verified backup", newest.stat().st_mtime)
