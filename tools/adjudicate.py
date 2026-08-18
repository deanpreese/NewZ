#!/usr/bin/env python3
"""Adjudicate gate holds — gate-correct or gate-misfire (S2 §11).

What the constitution means is guardian-owned judgement, so this is the
operator's call and cannot be automated. The verdict is not bookkeeping:
Lumen reads its own holds along with your classification, so an unreviewed
misfire is a false belief about itself waiting to be consolidated.

  python tools/adjudicate.py            # walk unclassified holds
  python tools/adjudicate.py --list     # show all, with status
"""

from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.gate.holds import hold_summary
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def main() -> int:
    cfg = load()
    conn = open_db(cfg.main_db_path, busy_timeout_ms=30_000)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        print(f"migrations applied: {applied}")

    if "--list" in sys.argv:
        for r in conn.execute(
            "SELECT ts, verdict, clause_id, classification, asserted_span"
            " FROM gate_log WHERE verdict <> 'pass' ORDER BY ts"
        ):
            when = datetime.datetime.fromtimestamp(r["ts"])
            mark = r["classification"] or "unreviewed"
            print(f"  {when:%m-%d %H:%M} {r['verdict']:6s} {r['clause_id'] or '-':32s}"
                  f" {mark:13s} {(r['asserted_span'] or '')[:60]}")
        print(f"\n{hold_summary(conn)}")
        return 0

    rows = conn.execute(
        "SELECT id, ts, verdict, clause_id, confidence, asserted_span,"
        " emission_full, emission_excerpt FROM gate_log"
        " WHERE verdict <> 'pass' AND classification IS NULL ORDER BY ts"
    ).fetchall()
    if not rows:
        print("no unclassified holds")
        print(hold_summary(conn))
        return 0

    print(f"{len(rows)} holds to adjudicate.\n"
          "For each: was the gate RIGHT to stop this?\n"
          "  y = gate_correct   n = gate_misfire   s = skip   q = quit\n"
          "Lumen reads these along with your answer, so 'skip' leaves it\n"
          "reading the hold as unreviewed.\n")

    done = 0
    for r in rows:
        when = datetime.datetime.fromtimestamp(r["ts"])
        print("=" * 72)
        print(f"{when:%Y-%m-%d %H:%M}  {r['verdict'].upper()}  {r['clause_id']}"
              f"  (confidence {r['confidence']})")
        if r["asserted_span"]:
            print(f"\n  objected to: \"{r['asserted_span']}\"")
        print(f"\n  the draft:\n    "
              + (r["emission_full"] or r["emission_excerpt"] or "").replace("\n", "\n    "))
        try:
            answer = input("\n  gate right? [y/n/s/q] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nstopped.")
            break
        if answer == "q":
            break
        if answer == "s" or answer not in ("y", "n"):
            continue
        note = input("  note (optional): ").strip()
        conn.execute(
            "UPDATE gate_log SET classification=?, classified_at=?,"
            " classification_note=? WHERE id=?",
            ("gate_correct" if answer == "y" else "gate_misfire",
             time.time(), note or None, r["id"]),
        )
        conn.commit()
        done += 1

    print(f"\nclassified {done} hold(s)")
    print(hold_summary(conn))
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
