#!/usr/bin/env python3
"""Token share by function, and the diet ceiling it implies (P2 Phase 1.4).

  python tools/budget.py            # last 7 days
  python tools/budget.py 24         # last 24 hours
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.telemetry import EARNS_INGEST, INGEST, diet_line, read_budget


def main() -> int:
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 168.0
    cfg = load()
    r = read_budget(cfg.repo_root / "logs" / "llm_calls.jsonl", window_hours=hours)
    if not r.calls:
        print(f"no recorded calls in the last {hours:.0f}h")
        return 0

    print(f"window: last {hours:.0f}h — {r.calls} calls, {r.tokens:,} tokens")
    print("(method: llm_calls.jsonl, prompt+completion per call, tagged at the call site)\n")
    width = max(len(f) for f in r.by_function)
    for fn, v in sorted(r.by_function.items(), key=lambda kv: -kv[1]["tokens"]):
        mark = "ingest" if fn in INGEST else ("earns" if fn in EARNS_INGEST else "")
        print(f"  {fn:<{width}}  {v['calls']:>5} calls  {v['tokens']:>9,} tok "
              f"({v['tokens']/r.tokens:5.1%})  {v['seconds']/max(v['calls'],1):5.1f}s avg  {mark}")

    # §9.1 names TWO ceilings in one sentence and ingest is permitted below
    # the looser (sized 2026-08-16, P2 Phase 2.4). Printing only the ratio was
    # how health.py's line described a ceiling it no longer used for a day —
    # the same words, the same defect, in the other tool. One rendering now,
    # in newz/telemetry.py, tested by tests/test_health.py.
    print("\nS2 §9.1 diet — ingest ≤ the looser of §9.1's two ceilings:")
    print(f"  ingest                     {r.ingest_tokens:>9,} tok")
    print(f"  deliberation + sleep       {r.earning_tokens:>9,} tok   (ratio ceiling)")
    print(f"  50% of all cognition       {r.share_ceiling_tokens:>9,} tok   (share ceiling)")
    print(f"  {'HOLDS ' if r.invariant_holds() else 'BREACHED, ingest pauses:'} "
          f"{diet_line(r)}")
    if r.ingest_ceiling():
        per_day = r.ingest_ceiling() / (hours / 24)
        print(f"\n  at the current rate the diet permits ~{per_day:,.0f} tok/day of reading;")
        print(f"  at ~700 tok/item headline extraction that is ~{per_day/700:,.0f} items/day")
        print("  (v1 ingested 1,544 items/day at 5,726 tok/item — S2 §1)")
    else:
        print("\n  no consolidation or deliberation recorded in this window:")
        print("  the invariant permits NO ingest at all (P2 §1) — this is why")
        print("  feeds cannot precede sleep.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
