#!/usr/bin/env python3
"""Read the being's claims back (P3 Rule 2's reader for `resolutions`).

  python tools/claims.py              # open claims, soonest due first
  python tools/claims.py --due         # only what is due now — E1.3's worklist
  python tools/claims.py --resolved    # what the world has settled
  python tools/claims.py --wrong       # only where it went against the being

The last is the one that matters. S1-E asks whether at least one position
changed because the world contradicted it — not the operator, not the being
itself — and this is where that becomes countable rather than asserted.
"""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.resolutions.store import claims_by_status, contradicted_claims, due_claims
from newz.store.db import open_db


def _day(ts: float | None) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "—"


def _render(c) -> str:
    head = f"[{c.id}] {c.claim}"
    out = ["─" * 72, "\n".join(textwrap.wrap(head, 72))]
    out.append(f"  settles when : {c.resolution_condition}")
    out.append(f"  resolver     : {c.resolver}")
    out.append(f"  opened {_day(c.opened_at)}  ·  due {_day(c.due_at)}"
               f"  ·  from {c.provenance}")
    if c.status == "resolved":
        verdict = "THE WORLD SAID NO" if c.outcome == "contradicted" else "held"
        out.append(f"  → {verdict}, {_day(c.settled_at)}, by {c.settled_by}")
        if c.settled_note:
            out.append("    " + "\n    ".join(textwrap.wrap(c.settled_note, 68)))
    return "\n".join(out)


def main() -> int:
    conn = open_db(load().main_db_path)
    if "--wrong" in sys.argv:
        claims, label = contradicted_claims(conn), "claims the world contradicted"
    elif "--resolved" in sys.argv:
        claims, label = claims_by_status(conn, "resolved"), "resolved claims"
    elif "--due" in sys.argv:
        claims, label = due_claims(conn, limit=100), "claims due now"
    else:
        claims = sorted(claims_by_status(conn, "open"), key=lambda c: c.due_at)
        label = "open claims"

    if not claims:
        # Not an error, and worth saying plainly: an empty table before E1.2
        # means the door is not built yet, not that the being never commits.
        print(f"no {label}.")
        return 0
    print(f"{len(claims)} {label}\n")
    for c in claims:
        print(_render(c))
    print("─" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
