#!/usr/bin/env python3
"""Read the being's commitments back (P4 Rule 2's reader for `commitments`).

  python tools/commitments.py             # what it is standing behind
  python tools/commitments.py --all       # including revised and abandoned
  python tools/commitments.py --refused   # what the door turned away, and why

**`--refused` is the one that matters**, for the reason `claims.py --refused`
matters. An empty `commitments` table has two readings that look identical from
outside — the being never commits to anything, or it tries nightly and the door
refuses every attempt — and those call for opposite fixes.

It is also where the cap shows. `MAX_STANDING` is 12 and **nothing in E4.1
releases a standing commitment** — revision on evidence and costed abandonment
are E4.2, whose Done-when needs a Phase 1 resolution and the earliest live
claim is due 2026-12-18. So this door saturates, the refusal rows say when, and
that is the measurement that makes E4.2 necessary rather than asserted.
"""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.commitments.door import MAX_PER_DAY, MAX_STANDING
from newz.commitments.store import all_commitments, standing, standing_count
from newz.config import load
from newz.store.db import open_db

_KIND = {"keeps_caring": "keeps caring", "refuses_to_do": "refuses to do"}


def _day(ts: float | None) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "—"


def _render(c) -> str:
    head = f"[{c.id}] {_KIND.get(c.kind, c.kind)}: {c.statement}"
    out = [textwrap.fill(head, 88, subsequent_indent="      ")]
    out.append(textwrap.fill(f"broken by: {c.falsifier}", 88,
                             initial_indent="      ",
                             subsequent_indent="                 "))
    tail = f"      {_day(c.ts)}  {c.status}  from {c.provenance}"
    if c.perspective_version:
        tail += f"  (perspective v{c.perspective_version})"
    out.append(tail)
    return "\n".join(out)


def main() -> int:
    argv = sys.argv[1:]
    cfg = load()
    conn = open_db(cfg.main_db_path)
    try:
        if "--refused" in argv:
            rows = conn.execute(
                "SELECT ts, reason, kind, statement, falsifier FROM"
                " commitment_refusals ORDER BY ts DESC").fetchall()
            print(f"\n  commitment refusals: {len(rows)}\n")
            for r in rows:
                print(f"  {_day(r['ts'])}  {r['reason']}")
                if r["statement"]:
                    print(textwrap.fill(r["statement"], 88,
                                        initial_indent="      ",
                                        subsequent_indent="      "))
                if r["falsifier"]:
                    print(textwrap.fill(f"falsifier: {r['falsifier']}", 88,
                                        initial_indent="      ",
                                        subsequent_indent="      "))
                print()
            if not rows:
                print("  (none — the door has turned nothing away)\n")
            return 0

        rows = all_commitments(conn) if "--all" in argv else standing(conn)
        n = standing_count(conn)
        print(f"\n  commitments: {len(rows)} shown, {n} standing"
              f" of {MAX_STANDING}, {MAX_PER_DAY} a day\n")
        for c in rows:
            print(_render(c))
            print()
        if not rows:
            print("  (none yet — the door is asked once per sleep, and most"
                  " nights the answer is no)\n")
        if n >= MAX_STANDING:
            print("  ** the carrying capacity is full, and nothing in E4.1"
                  " releases a slot. See --refused, and E4.2.\n")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
