#!/usr/bin/env python3
"""Back up the identity path now, or list what exists.

  python tools/backup.py          # take a verified backup now
  python tools/backup.py list     # show existing backups
  python tools/backup.py restore <file>   # print the restore procedure
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.backup import run_backup


def main() -> int:
    cfg = load()
    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if arg == "list":
        files = sorted(cfg.backups_dir.glob("*.db"), key=lambda p: p.stat().st_mtime)
        if not files:
            print(f"no backups in {cfg.backups_dir}")
            return 0
        for f in files:
            st = f.stat()
            when = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {when}  {st.st_size/1e6:7.1f} MB  {f.name}")
        print(f"\n{len(files)} backups in {cfg.backups_dir}")
        return 0

    if arg == "restore":
        if len(sys.argv) < 3:
            print("usage: backup.py restore <backup-file>", file=sys.stderr)
            return 1
        src = Path(sys.argv[2])
        target = cfg.interior_db_path if "interior" in src.name else cfg.main_db_path
        print(
            "Restore is deliberately manual — it overwrites the being's store.\n"
            "Stop the ambient loop first, then:\n\n"
            f"  mv {target} {target}.pre-restore\n"
            f"  cp {src} {target}\n"
            f"  rm -f {target}-wal {target}-shm\n"
            + (f"  chmod 600 {target}\n" if target == cfg.interior_db_path else "")
            + "\nThen restart the loop; migrations reapply if the copy is older."
        )
        return 0

    report = run_backup(cfg.main_db_path, cfg.interior_db_path, cfg.backups_dir)
    for p in report.made:
        print(f"  wrote {p}")
    for name, (s, c) in report.counts.items():
        print(f"  verified {name}: {s} rows -> {c} rows  {'OK' if s == c else 'MISMATCH'}")
    if report.pruned:
        print(f"  pruned {len(report.pruned)} old backup(s)")
    print(f"{'VERIFIED' if report.ok() else 'FAILED'} in {report.duration_s:.1f}s")
    return 0 if report.ok() else 2


if __name__ == "__main__":
    sys.exit(main())
