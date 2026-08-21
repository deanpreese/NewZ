"""Storage layer — SQLite WAL, main + interior as separate database files.

S2 §16: SQLite WAL, main + interior (keyed, 0600); WAL checkpoint at boot.
S2 §15.3: interior is a separate keyed store — separation is structural
(different file, different connection, 0600), not a table prefix.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


MONITOR_NAME = "monitor.db"
MONITOR_SCHEMA = "mon"


def attach_monitor(conn: sqlite3.Connection, path: Path, *,
                   read_only: bool = False) -> bool:
    """ATTACH the monitor database beside `path` as `mon`. False if absent.

    **The monitor is a sibling by construction** (P4 E3A.1), the way
    `interior.db` is: `config.load` puts all three in one data directory. So
    every existing caller of `open_db` reaches the readings with no signature
    change, and the clean room reaches them by restoring the monitor backup
    into the room under this name.

    Absent is not an error here. `monitor_attached()` is what a reader asks
    when it needs to tell *the monitor database is not here* from *there are no
    readings* — INV-044, and the difference between a fact about the restore
    and a fact about the being.
    """
    sibling = path.parent / MONITOR_NAME
    if path.name == MONITOR_NAME or not sibling.exists():
        return False
    # URI filenames in ATTACH are honoured only when the connection itself was
    # opened with them, which is exactly the read-only case here. The
    # read-write connection is opened on a plain path and must attach one.
    target = f"file:{sibling}?mode=ro" if read_only else str(sibling)
    conn.execute(f"ATTACH DATABASE ? AS {MONITOR_SCHEMA}", (target,))
    return True


def monitor_attached(conn: sqlite3.Connection) -> bool:
    """Is the monitor database on this connection?"""
    return any(r[1] == MONITOR_SCHEMA for r in conn.execute("PRAGMA database_list"))


def open_db(
    path: Path,
    *,
    interior: bool = False,
    read_only: bool = False,
    busy_timeout_ms: int = 5000,
    monitor: bool = True,
) -> sqlite3.Connection:
    # check_same_thread=False: the ambient loop hands LLM-bound work to
    # worker threads (asyncio.to_thread) that read/write through the shared
    # connection. Safe because this build's sqlite3.threadsafety == 3
    # (serialized — SQLite's own mutexes serialize per-connection calls),
    # asserted below so a rebuilt env fails loudly instead of corrupting.
    assert sqlite3.threadsafety == 3, "sqlite3 must be built in serialized mode"
    if read_only:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if monitor and not interior:
            attach_monitor(conn, path, read_only=True)
        return conn
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, uri=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
    if interior:
        os.chmod(path, 0o600)
    if monitor and not interior:
        attach_monitor(conn, path)
    return conn


def boot_checkpoint(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
