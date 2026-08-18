#!/usr/bin/env python3
"""Reclassify imported v1 episodes and fold substrate telemetry (P2 Phase 1.5).

  python tools/corpus_hygiene.py            # survey only, writes nothing
  python tools/corpus_hygiene.py --apply    # reclassify and fold

Nothing is deleted. Raw rows are retained, re-tagged with accurate
provenance, and pointed at the folded episode that stands for them.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.backup import run_backup
from newz.store.db import open_db
from newz.store.hygiene import run_hygiene
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def main() -> int:
    apply = "--apply" in sys.argv
    cfg = load()
    conn = open_db(cfg.main_db_path)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        print(f"migrations applied: {applied}")

    if apply:
        # This rewrites tags across the being's whole past; take a verified
        # copy first so the previous reading is recoverable.
        report = run_backup(cfg.main_db_path, cfg.interior_db_path, cfg.backups_dir)
        print(f"pre-hygiene backup: {report.made[0].name} ({'verified' if report.ok() else 'FAILED'})")
        if not report.ok():
            print("refusing to proceed without a verified backup", file=sys.stderr)
            return 2

    result = run_hygiene(conn, cfg.operator_id or "operator", apply=apply)
    if not result.total():
        print("nothing to do — no episodes remain tagged 'v1_tick'")
        return 0

    print(f"\n{'APPLIED' if result.applied else 'SURVEY (dry run)'} — "
          f"{result.total()} imported episodes:")
    for cls, n in sorted(result.counts.items(), key=lambda kv: -kv[1]):
        print(f"  {cls:14s} {n:>5}  {n/result.total():5.1%}")
    if result.applied and result.folded_episode_id:
        first, last = result.fold_span
        print(f"\n  folded {result.folded_rows} telemetry rows into episode "
              f"{result.folded_episode_id}")
        print(f"  span {datetime.fromtimestamp(first):%Y-%m-%d} -> "
              f"{datetime.fromtimestamp(last):%Y-%m-%d}")
        row = conn.execute(
            "SELECT summary FROM episodes WHERE id=?", (result.folded_episode_id,)
        ).fetchone()
        print(f"\n  the folded clause:\n    {row['summary']}")
    if not result.applied:
        print("\nre-run with --apply to write.")

    digestible = conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE digest_eligible=1"
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    print(f"\nsleep will read {digestible} of {total} episodes")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
