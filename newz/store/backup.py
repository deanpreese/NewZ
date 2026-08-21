"""Backups — hot, verified copies of the identity path.

Ported with review from v1 (`ngbeing/operational/backup.py` and
`backup_scheduler.py`, S2 §16 allowlist). Review changes:

- aiosqlite → sync sqlite3 taken from an async task, matching v2's storage;
- **verification is mandatory, not optional.** v1 wrote backups and never
  read one back. The project's own rule for acts (S2 §10.1: a confirmation
  that cannot fail is decorative) applies to backups: every copy is
  reopened, integrity-checked, and row-counted against the source before it
  is allowed to count as a backup. An unverified copy is deleted and the
  failure is loud.
- The interior is copied and counted, never read (INV-007 discipline): only
  `PRAGMA integrity_check` and `COUNT(*)` touch it.

No `backup_log` table: the timestamped files are the record, and a table
whose only reader would be a human reading filenames is dead schema
(P2 Rule 2).
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from newz.store.db import MONITOR_NAME

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_S = 6 * 3600
DEFAULT_KEEP = 24  # ~6 days at the default cadence; ~12MB/pair today


class BackupError(Exception):
    """Raised when a backup cannot be produced or cannot be verified."""


@dataclass
class BackupReport:
    made: list[Path] = field(default_factory=list)
    pruned: list[Path] = field(default_factory=list)
    counts: dict[str, tuple[int, int]] = field(default_factory=dict)  # name -> (src, copy)
    duration_s: float = 0.0

    def ok(self) -> bool:
        return bool(self.made) and all(s == c for s, c in self.counts.values())


def _count(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if row is None:
        return 0
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def backup_db(
    src: Path,
    dest_dir: Path,
    prefix: str,
    *,
    verify_table: str,
    interior: bool = False,
) -> tuple[Path, int, int]:
    """Hot-copy `src` into `dest_dir`, verify it, return (path, src_n, copy_n).

    Uses SQLite's online-backup API from a read-only connection, so a live
    writer in this or any process is safe — SQLite restarts the copy if the
    source changes underneath it. Raises BackupError if the copy fails
    integrity check or its row count disagrees with the source.
    """
    if not src.exists():
        raise BackupError(f"source database missing: {src}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromtimestamp(time.time()).strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{prefix}-{stamp}.db"

    try:
        source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        try:
            src_n = _count(source, verify_table)
            target = sqlite3.connect(dest)
            try:
                source.backup(target)
            finally:
                target.close()
        finally:
            source.close()
    except sqlite3.Error as e:
        # A corrupt or non-SQLite source must surface as a backup failure with
        # a clear message, not as a raw driver error inside the scheduler.
        dest.unlink(missing_ok=True)
        raise BackupError(f"{prefix} source unreadable ({src}): {e}") from e

    if interior:
        dest.chmod(0o600)

    # Verify: reopen the copy, integrity-check it, recount. A backup that has
    # not been read back is not a backup.
    check = sqlite3.connect(f"file:{dest}?mode=ro", uri=True)
    try:
        integrity = check.execute("PRAGMA quick_check").fetchone()[0]
        copy_n = _count(check, verify_table)
    finally:
        check.close()

    if integrity != "ok" or copy_n != src_n:
        dest.unlink(missing_ok=True)
        raise BackupError(
            f"{prefix} backup failed verification: integrity={integrity!r} "
            f"rows src={src_n} copy={copy_n} (copy deleted)"
        )
    return dest, src_n, copy_n


def prune(dest_dir: Path, prefix: str, keep: int) -> list[Path]:
    """Keep the newest `keep` backups for a prefix; delete the rest."""
    files = sorted(
        dest_dir.glob(f"{prefix}-*.db"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    removed = []
    for old in files[keep:]:
        old.unlink(missing_ok=True)
        removed.append(old)
    return removed


def run_backup(
    main_db: Path,
    interior_db: Path,
    dest_dir: Path,
    *,
    monitor_db: Path | None = None,
    keep: int = DEFAULT_KEEP,
) -> BackupReport:
    started = time.monotonic()
    report = BackupReport()

    path, s, c = backup_db(main_db, dest_dir, "main", verify_table="episodes")
    report.made.append(path)
    report.counts["main"] = (s, c)

    if interior_db.exists():
        path, s, c = backup_db(
            interior_db, dest_dir, "interior",
            verify_table="interior_log", interior=True,
        )
        report.made.append(path)
        report.counts["interior"] = (s, c)

    # P4 E3A.1. The monitor's database holds the metric series, and
    # `evolution/pre_loop_baseline.yaml` pins the row ids a baseline was
    # computed from — ids INV-087 calls what separates a measured baseline from
    # an invented denominator. An unbacked series is a baseline that cannot be
    # audited after a restore, so it is copied and verified like the others
    # rather than left to be discovered missing.
    monitor_db = monitor_db or (main_db.parent / MONITOR_NAME)
    if monitor_db.exists():
        path, s, c = backup_db(
            monitor_db, dest_dir, "monitor", verify_table="metric_readings")
        report.made.append(path)
        report.counts["monitor"] = (s, c)

    for prefix in ("main", "interior", "monitor"):
        report.pruned.extend(prune(dest_dir, prefix, keep))

    report.duration_s = time.monotonic() - started
    return report


class BackupScheduler:
    """Backs up at boot, then on a fixed cadence, for as long as the being runs."""

    def __init__(
        self,
        main_db: Path,
        interior_db: Path,
        dest_dir: Path,
        *,
        interval_s: float = DEFAULT_INTERVAL_S,
        keep: int = DEFAULT_KEEP,
    ):
        self._main = main_db
        self._interior = interior_db
        self._dest = dest_dir
        self._interval = interval_s
        self._keep = keep

    async def run(self) -> None:
        while True:
            try:
                report = await asyncio.to_thread(
                    run_backup, self._main, self._interior, self._dest, keep=self._keep
                )
                logger.info(
                    "backup ok: %s (%.1fs, verified %s%s)",
                    ", ".join(p.name for p in report.made),
                    report.duration_s,
                    " ".join(f"{k}={v[1]}" for k, v in report.counts.items()),
                    f", pruned {len(report.pruned)}" if report.pruned else "",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                # A failed backup must be loud but must never take the being
                # down; the next cadence tries again.
                logger.exception("BACKUP FAILED — the identity path is uncopied")
            await asyncio.sleep(self._interval)
