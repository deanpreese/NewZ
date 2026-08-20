#!/usr/bin/env python3
"""Judge stalled concerns that today's rules would not have stalled.

    python tools/closure_sweep.py --dry-run      # who is eligible, no calls
    python tools/closure_sweep.py                # judge 5, close at most 2
    python tools/closure_sweep.py --limit 10 --max-closures 3

Closure was reachable only from the moment after an advance, so a concern with
nothing left to move could never be asked whether it was already finished. This
is the second caller of the same act (`closure.attempt_closure`), not a second
implementation of it.

The caps are the point rather than a courtesy. Every closure sends a position
to the next sleep, and sleep is the only writer to the Perspective (INV-009):
positions entering identity is the least reversible thing this system does, and
a fixed backlog has no reason to be drained fast.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.concerns.sweep import DEFAULT_LIMIT, DEFAULT_MAX_CLOSURES, eligible, sweep
from newz.config import load
from newz.llm.client import LLMClient
from newz.store.db import open_db


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help="how many concerns to judge this run")
    ap.add_argument("--max-closures", type=int, default=DEFAULT_MAX_CLOSURES,
                    help="stop after this many closures (one sleep's worth)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list who is eligible; make no model calls")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    cfg = load()
    conn = open_db(cfg.main_db_path)
    conn.row_factory = sqlite3.Row

    ids = eligible(conn, limit=args.limit)
    total = len(eligible(conn, limit=1_000_000))
    if not ids:
        print("nothing eligible: no stalled concern is below both limits and "
              "outside its judging cooldown")
        return 0

    print(f"{total} concern(s) stalled below both limits — a state the current "
          f"rules would not produce.\nThis run would judge {len(ids)}:\n")
    for i in ids:
        r = conn.execute(
            "SELECT statement, advance_count, stall_count, blocked_count"
            " FROM concerns WHERE id=?", (i,)).fetchone()
        print(f"  c{i:<4} adv={r['advance_count']} "
              f"stalls={r['stall_count']}/{r['blocked_count']}  "
              f"{r['statement'][:88]}")

    if args.dry_run:
        print("\n--dry-run: nothing judged, nothing written")
        return 0

    print(f"\njudging (closing at most {args.max_closures})...\n")
    result = sweep(conn, LLMClient(cfg, timeout=600),
                   limit=args.limit, max_closures=args.max_closures)
    print(f"\n{result}")
    if result.closed:
        print("\nEach closure yields a position to the next sleep, which is the "
              "only writer to the Perspective (INV-009).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
