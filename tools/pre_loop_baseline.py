#!/usr/bin/env python3
"""What the being was like before the loop (P4 W10).

    python tools/pre_loop_baseline.py             # where things stand against it
    python tools/pre_loop_baseline.py --propose   # the block to paste, computed

**It prints; it does not write.** `evolution/pre_loop_baseline.yaml` is inside
the hard core, and taking the baseline is the operator's act — one they take
once, at the moment stage 0 starts. A tool that wrote it would make the record
of that decision a side effect of running a command.

The metrics are the ones a kill condition or S8-E reads: nights slept and the
interval between them, because *development is measured in nights, not commits
and a loop that costs sleep is subtracting*; and the three that say whether the
being is still doing its own work.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.evidence import pre_loop
from newz.store.db import open_db

WATCHED = ["nights_slept", "hours_since_last_sleep", "episodes_recorded",
           "advances_offered", "pieces_written"]


def main() -> int:
    cfg = load()
    now = time.time()
    conn = open_db(cfg.main_db_path, read_only=True)
    try:
        if "--propose" in sys.argv:
            rows = pre_loop.propose(conn, WATCHED, now=now)
            print("# computed by tools/pre_loop_baseline.py — paste into")
            print("# evolution/pre_loop_baseline.yaml, and set taken_at/taken_by\n")
            print(f"taken_at: {now:.0f}")
            print("taken_by: operator")
            print("metrics:")
            for metric, row in rows.items():
                if "unreadable" in row:
                    print(f"  # {metric}: UNREADABLE — {row['unreadable']}")
                    continue
                print(f"  {metric}:")
                for key in ("median", "readings", "from", "to"):
                    print(f"    {key}: {row[key]}")
                print(f"    reading_ids: {row['reading_ids']}")
            return 0

        why = pre_loop.may_widen()
        if why:
            print(f"NOT TAKEN\n\n  {why}\n")
            print("  python tools/pre_loop_baseline.py --propose")
            return 0

        print(f"taken {time.strftime('%Y-%m-%d', time.localtime(pre_loop.registry()['taken_at']))}"
              f" by {pre_loop.registry()['taken_by']}\n")
        for metric in WATCHED:
            r = pre_loop.compare(conn, metric, now=now)
            if "unreadable" in r:
                print(f"  {metric:26} UNREADABLE   {r['unreadable'][:60]}")
                continue
            mark = "BELOW" if r["below"] else "at or above"
            print(f"  {metric:26} {r['current']:>9.4g}   {mark} "
                  f"{r['baseline']:.4g} ({r['delta']:+.4g})")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
