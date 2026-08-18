#!/usr/bin/env python3
"""Run the v1 → v2 import (P2 Phase 0.2) against ../NGBeing.

Idempotence guard: refuses to run if the destination already contains an
import run — a re-import into a lived-in store would duplicate identity.
Delete the v2 data files deliberately if a clean re-import is intended.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.importer.v1_import import run_import
from newz.store.db import boot_checkpoint, open_db
from newz.store.migrations import apply_pending

V1_REPO = Path(__file__).resolve().parent.parent.parent / "NGBeing"
MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def main() -> int:
    cfg = load()
    v1_main = V1_REPO / "data" / "main.db"
    v1_interior = V1_REPO / "data" / "interior.db"
    if not v1_main.exists():
        print(f"v1 main DB not found: {v1_main}", file=sys.stderr)
        return 1

    dest = open_db(cfg.main_db_path)
    apply_pending(dest, MAIN_SQL)
    boot_checkpoint(dest)

    existing = dest.execute("SELECT COUNT(DISTINCT run_id) FROM import_record").fetchone()[0]
    if existing:
        print(f"refusing: {existing} import run(s) already recorded in {cfg.main_db_path}",
              file=sys.stderr)
        return 1

    character_files = {}
    for name in ("v0", "v1"):
        p = V1_REPO / "ngbeing" / "character" / f"{name}.md"
        if p.exists():
            character_files[name] = p

    with tempfile.TemporaryDirectory(prefix="newz-import-") as scratch:
        report = run_import(
            v1_repo=V1_REPO,
            v1_main_db=v1_main,
            v1_interior_db=v1_interior,
            dest_main=dest,
            dest_interior_path=cfg.interior_db_path,
            scratch_dir=Path(scratch),
            character_files=character_files,
        )

    print(f"run_id: {report.run_id}")
    print(f"v1: {report.v1_repo} @ {report.v1_commit}")
    width = max(len(t) for t in report.tables)
    for table, (v1_count, imported) in report.tables.items():
        flag = "OK " if v1_count == imported else "MISMATCH"
        print(f"  {table:<{width}}  v1={v1_count:>6}  imported={imported:>6}  {flag}")
    for note in report.notes:
        print(f"  note: {note}")
    print("VERIFIED" if report.ok() else "MISMATCHES PRESENT")
    dest.close()
    return 0 if report.ok() else 2


if __name__ == "__main__":
    sys.exit(main())
