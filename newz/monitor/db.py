"""The monitor's database, and the one-time move into it (P4 E3A.1).

`data/monitor.db` holds the metric series, its definition boundaries, and the
monitor's own log. It is attached to the being's connection as `mon` by
`newz.store.db.attach_monitor`, so every existing reader reaches it without a
signature change.

**The move preserves ids, and that is not cosmetic.** The surface records its
provenance as the row ids it read (E3.3, disclosure by construction), and
`evolution/pre_loop_baseline.yaml` pins the ids a baseline was computed from —
which INV-087 calls what separates it from an invented denominator. Ids that
change under either of those turn a traceable number into an unfalsifiable one.

**And it is done now rather than later** because the baseline is untaken: today
nothing pins an id, so the move costs nothing. After the baseline is taken the
same move is a `Semantics:` change with a store snapshot behind it.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

from newz.store.db import MONITOR_NAME, open_db
from newz.store.migrations import apply_pending

logger = logging.getLogger(__name__)

MONITOR_SQL = Path(__file__).resolve().parent.parent / "store" / "sql" / "monitor"

# The tables that moved out of the being's store. Order matters only for
# readability; neither references the other.
MOVED = ("metric_readings", "metric_definition_changes")


def monitor_path(main_db_path: Path) -> Path:
    """Beside the being's store, the way `interior.db` is."""
    return Path(main_db_path).parent / MONITOR_NAME


def open_monitor(main_db_path: Path) -> sqlite3.Connection:
    """Open (creating if needed) the monitor database, migrations applied."""
    path = monitor_path(main_db_path)
    conn = open_db(path, monitor=False)
    apply_pending(conn, MONITOR_SQL)
    return conn


def log(conn: sqlite3.Connection, kind: str, ok: bool, note: str = "",
        *, now: float | None = None) -> None:
    """One row per run, send or move. The daily email is the reader."""
    conn.execute(
        "INSERT INTO monitor_log (ts, kind, ok, note) VALUES (?,?,?,?)",
        (now or time.time(), kind, 1 if ok else 0, note))
    conn.commit()


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)).fetchone() is not None


def move_from_main(main_db_path: Path, *, now: float | None = None) -> dict[str, int]:
    """Copy the metric tables out of the being's store, ids intact, then drop.

    Idempotent by construction: after the first run the source tables are gone,
    and on a fresh clone they exist and are empty. Either way this ends with the
    rows in one place and `newz.db` holding neither table.

    Copy first and drop second, in one transaction per table, so an interrupted
    move loses nothing — the worst case is a repeated copy, which `INSERT OR
    IGNORE` on a preserved primary key makes harmless.
    """
    moved: dict[str, int] = {}
    mon = open_monitor(main_db_path)
    main = open_db(Path(main_db_path), monitor=False)
    try:
        for table in MOVED:
            if not _has_table(main, table):
                continue
            rows = main.execute(f"SELECT * FROM {table}").fetchall()
            if rows:
                cols = [d[0] for d in main.execute(
                    f"SELECT * FROM {table} LIMIT 0").description]
                placeholders = ",".join("?" * len(cols))
                mon.executemany(
                    f"INSERT OR IGNORE INTO {table} ({','.join(cols)})"
                    f" VALUES ({placeholders})",
                    [tuple(r[c] for c in cols) for r in rows])
                mon.commit()
            main.execute(f"DROP TABLE {table}")
            main.commit()
            moved[table] = len(rows)
        if moved:
            log(mon, "move", True,
                ", ".join(f"{k}: {v} row(s)" for k, v in moved.items()), now=now)
            logger.info("monitor: moved %s out of the being's store",
                        ", ".join(f"{k} ({v})" for k, v in moved.items()))
    finally:
        main.close()
        mon.close()
    return moved
