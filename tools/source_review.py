#!/usr/bin/env python3
"""The source review (P2 Phase 2.4) — the diet, judged on evidence.

S2 §9.1: reading is "chosen by the being's failed questions. The honest-no-
result log and blocked concerns name the sources worth adding; the same
analysis names feeds worth removing." This prints that analysis. Deciding
what to add and cut is the operator's, because it shapes what the being can
come to believe (S2 §13, TRUE_NORTH §8).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.world.diet import MAX_OUTLET_SHARE, MIN_ITEMS_FOR_CAP, WINDOW_DAYS, shares

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def main() -> int:
    cfg = load()
    conn = open_db(cfg.main_db_path, busy_timeout_ms=30_000)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        print(f"migrations applied: {applied}\n")
    conn.row_factory = sqlite3.Row

    print("=== what the being read (last %d days) ===" % WINDOW_DAYS)
    dist = shares(conn)
    if not dist:
        print("  nothing ingested yet — the diet has not been exercised")
    else:
        total = conn.execute("SELECT COUNT(*) FROM ingest_log WHERE skipped IS NULL").fetchone()[0]
        for outlet, share in sorted(dist.items(), key=lambda kv: -kv[1]):
            flag = "  OVER CAP" if share > MAX_OUTLET_SHARE else ""
            print(f"  {outlet:24s} {share:6.1%}{flag}")
        print(f"  ({total} items; cap {MAX_OUTLET_SHARE:.0%} applies above "
              f"{MIN_ITEMS_FOR_CAP} items)")
        capped = conn.execute(
            "SELECT COUNT(*) FROM ingest_log WHERE skipped='share_cap'").fetchone()[0]
        if capped:
            print(f"  {capped} read(s) deprioritised by the cap")

    print("\n=== what nothing answered — sources worth ADDING ===")
    gaps = conn.execute(
        "SELECT query, gap, COUNT(*) n FROM source_gaps"
        " GROUP BY query ORDER BY n DESC, ts DESC LIMIT 25").fetchall()
    if not gaps:
        print("  no gaps recorded yet. Research has to run before the diet can")
        print("  be chosen from evidence — this is the plan's own sequencing,")
        print("  not an omission (S2 §9.1, first bullet).")
    else:
        for g in gaps:
            print(f"  [{g['n']}x] {g['query'][:88]}")
            print(f"         {g['gap'][:88]}")

    print("\n=== concerns blocked for want of material ===")
    blocked = conn.execute(
        "SELECT c.id, c.statement, c.blocked_count, s.brief FROM concerns c"
        " JOIN concern_setbacks s ON s.concern_id = c.id AND s.kind='blocked'"
        " WHERE c.blocked_count > 0 GROUP BY c.id"
        " ORDER BY c.blocked_count DESC LIMIT 12").fetchall()
    if not blocked:
        print("  none")
    for b in blocked:
        print(f"  [{b['blocked_count']}x] {b['statement'][:80]}")
        print(f"         needs: {(b['brief'] or '')[:88]}")

    print("\n=== which outlets actually contributed ===")
    rows = conn.execute(
        "SELECT outlet, COUNT(*) reads, SUM(claims_kept) kept,"
        " SUM(quarantined) quarantined FROM ingest_log"
        " WHERE skipped IS NULL GROUP BY outlet ORDER BY kept DESC").fetchall()
    if not rows:
        print("  nothing yet")
    for r in rows:
        per = (r["kept"] or 0) / max(r["reads"], 1)
        print(f"  {r['outlet']:24s} {r['reads']:>4} reads  {r['kept'] or 0:>4} claims"
              f"  {per:5.1f}/read  {r['quarantined'] or 0} quarantined")

    print("\nDecide: add sources that would answer the gaps above; cut outlets")
    print("that read a lot and contribute little. v1's anti-pattern was 56% of")
    print("all reading from two outlets (S2 §9.1).")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
