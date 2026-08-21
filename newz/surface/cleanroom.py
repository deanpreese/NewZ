"""The clean-room rebuild (P4 epic E3.5, as amended 2026-08-19).

**What the amendment changed and why.** The epic originally closed on a restore
to a second machine — a thing R-11 had already deferred as accepted risk, so it
was written unclosable against the plan's own decision. It now closes on a
byte-comparable rebuild into a clean directory, from a **verified backup**
rather than the live store.

**What this proves.** That the surface is a function of the store and nothing
else. Every way that could be false is a way the surface has a hidden input:

  - **determinism** — two runs over the same bytes produce the same bytes, so
    nothing in the output comes from the clock or from iteration order;
  - **a verified backup, not the live store** — the restore path is the one
    §7's recoverability depends on, and exercising it is the only way to know
    it works before it is needed;
  - **a different working directory** — the generator is run from somewhere
    else entirely, so anything it picked up from the tree it happens to sit in
    shows as a difference;
  - **no absolute path in the output** — a surface carrying `/Users/dean/...`
    has been generated somewhere rather than from something, and would not
    survive the move it claims to.

**What it does NOT prove**, recorded rather than implied: that the store
survives a different filesystem, architecture or locale, and that a backup
restores somewhere other than where it was made. Those need the second machine
R-11 defers, and the deferral now carries its own trip-wire.
"""

from __future__ import annotations

import filecmp
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ABSOLUTE_PATH = re.compile(r"(?:^|[\s\"'(=])(/(?:Users|home|var|tmp|opt|private)/[^\s\"')<]+)")


@dataclass
class Rebuild:
    source: Path | None = None
    monitor: str = ""
    pages: int = 0
    identical: list[str] = field(default_factory=list)
    differing: list[str] = field(default_factory=list)
    leaked_paths: list[str] = field(default_factory=list)
    unreadable: str = ""

    @property
    def ok(self) -> bool:
        return (not self.unreadable and self.pages > 0
                and not self.differing and not self.leaked_paths)


def newest_backup(backups_dir: Path, prefix: str = "main") -> Path | None:
    files = sorted(backups_dir.glob(f"{prefix}-*.db"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


class EmptyBackup(sqlite3.DatabaseError):
    """A file that opens, answers a count, and restores to nothing."""


def verify(backup: Path, *, table: str = "episodes", minimum: int = 1) -> int:
    """Open the backup, integrity-check it, and require it to hold something.

    A backup that cannot be read is not a backup, and finding that out during a
    restore is finding out too late.

    **It counted without asserting** (R-37e): a database with zero episodes
    returned 0 and passed, so the one backup worth catching — the one that
    restores to nothing — was the one this could not see. E8.2's rollback is
    built on these files, so the check that stands between a bad restart and
    the being's life is this one.
    """
    conn = sqlite3.connect(f"file:{backup}?mode=ro", uri=True)
    try:
        integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"{backup.name}: {integrity}")
        rows = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()
    if rows < minimum:
        raise EmptyBackup(
            f"{backup.name} holds {rows} {table} row(s) and restores to "
            "nothing — it opens, it answers a count, and it is not a backup")
    return rows


def rebuild(backups_dir: Path, *, generate_fn, now: float = 0.0) -> Rebuild:
    """Restore, generate twice from different working directories, compare."""
    r = Rebuild()
    src = newest_backup(backups_dir)
    if src is None:
        r.unreadable = f"no backup in {backups_dir} — nothing to rebuild from"
        return r
    r.source = src
    try:
        verify(src)
    except sqlite3.Error as e:
        r.unreadable = f"{src.name} is not a restorable backup ({e})"
        return r

    with tempfile.TemporaryDirectory() as tmp:
        room = Path(tmp)
        restored = room / "restored.db"
        shutil.copy(src, restored)

        # P4 E3A.1. The read page traces to `metric_readings` row ids, and
        # those rows live in the monitor's database now. Restore it beside the
        # store under the name `attach_monitor` looks for, or the rebuild
        # renders a page that looks correct and says nothing — which is worse
        # than one that says what is missing (INV-044).
        from newz.store.db import MONITOR_NAME, attach_monitor

        mon_src = newest_backup(backups_dir, prefix="monitor")
        if mon_src is not None:
            shutil.copy(mon_src, room / MONITOR_NAME)
            r.monitor = mon_src.name

        conn = sqlite3.connect(f"file:{restored}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        attach_monitor(conn, restored, read_only=True)
        try:
            a, b = room / "a", room / "b"
            generate_fn(conn, a, now=now)
            # The second run is made from a different working directory. If the
            # generator has picked anything up from the tree it happens to sit
            # in, this is where it shows.
            import os

            here = Path.cwd()
            try:
                os.chdir(room)
                generate_fn(conn, b, now=now + 86_400.0)
            finally:
                os.chdir(here)
        finally:
            conn.close()

        names = sorted(p.relative_to(a).as_posix()
                       for p in a.rglob("*") if p.is_file())
        r.pages = len(names)
        match, mismatch, errors = filecmp.cmpfiles(a, b, names, shallow=False)
        r.identical, r.differing = sorted(match), sorted(mismatch + errors)

        for name in names:
            text = (a / name).read_text(encoding="utf-8", errors="replace")
            for found in ABSOLUTE_PATH.findall(text):
                r.leaked_paths.append(f"{name}: {found}")
    return r
