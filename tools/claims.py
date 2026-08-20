#!/usr/bin/env python3
"""Read the being's claims back (P3 Rule 2's reader for `resolutions`).

  python tools/claims.py              # open claims, soonest due first
  python tools/claims.py --due         # only what is due now — E1.3's worklist
  python tools/claims.py --resolved    # what the world has settled
  python tools/claims.py --wrong       # only where it went against the being
  python tools/claims.py --refused     # what the door turned away, and why

The last is the one that matters. S1-E asks whether at least one position
changed because the world contradicted it — not the operator, not the being
itself — and this is where that becomes countable rather than asserted.
"""

from __future__ import annotations

import sys
import time
import textwrap
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.evidence.consequence import read as read_consequence
from newz.evidence.pursuit import closing_shapes
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
    if c.attempts:
        # An open claim that has been tried and could not be settled is a
        # different thing from one whose date has not arrived, and the
        # difference is only visible here (INV-044's honesty: unmeasured
        # reports itself as unmeasured).
        out.append(f"  tried {c.attempts}×, last {_day(c.last_attempt_at)}"
                   f" — {c.last_failure or 'no reason recorded'}")
    if c.status == "resolved":
        verdict = "THE WORLD SAID NO" if c.outcome == "contradicted" else "held"
        out.append(f"  → {verdict}, {_day(c.settled_at)}, by {c.settled_by}")
        if c.settled_note:
            out.append("    " + "\n    ".join(textwrap.wrap(c.settled_note, 68)))
    return "\n".join(out)


def _cost_lines(conn, claim_id: int) -> list[str]:
    """What being wrong actually cost (E1.4). A refutation that reached no
    position says so — the being can be wrong about something it never wrote
    into its Perspective, and that is a different finding from a refutation
    nobody charged."""
    rows = conn.execute(
        "SELECT item_text, section, confidence_before, confidence_after,"
        " repeat, released FROM claim_costs WHERE claim_id=?",
        (claim_id,)).fetchall()
    if not rows:
        note = conn.execute("SELECT cost_note FROM resolutions WHERE id=?",
                            (claim_id,)).fetchone()
        return [f"  cost: {note['cost_note']}"] if note and note["cost_note"] else []
    out = []
    for r in rows:
        tail = " RELEASED" if r["released"] else ""
        again = ", again" if r["repeat"] else ""
        out.append(f"  cost: [{r['section']}] {r['confidence_before']:.2f} →"
                   f" {r['confidence_after']:.2f}{again}{tail}")
        out.append("    " + "\n    ".join(textwrap.wrap(r["item_text"], 68)))
    return out


def _refusals(conn) -> int:
    """P3's first Phase 1 diagnostic: are its claims resolvable at all?

    An empty `resolutions` table has two readings — the being commits to
    nothing checkable, or it tries and the door refuses everything — and they
    call for opposite fixes. This is how they are told apart.
    """
    rows = conn.execute(
        "SELECT ts, concern_id, reason, claim, resolver, due_text"
        " FROM claim_refusals ORDER BY ts DESC LIMIT 100").fetchall()
    if not rows:
        print("no claims refused at the door.")
        return 0
    print(f"{len(rows)} refused claims (most recent first)\n")
    for r in rows:
        print("─" * 72)
        print(f"[{_day(r['ts'])}] concern {r['concern_id']}  ·  {r['reason']}")
        if r["claim"]:
            print("\n".join(textwrap.wrap(r["claim"], 72, initial_indent="  ",
                                          subsequent_indent="  ")))
        if r["resolver"]:
            print(f"  resolver: {r['resolver']}  ·  due {r['due_text'] or '—'}")
    print("─" * 72)
    return 0


def _s1e(conn, repo_root) -> int:
    """The S1-E read (P4 E1.6). Every figure carries its grade (Rule 7)."""
    hours = 168.0
    r = read_consequence(conn, repo_root, now=time.time(), hours=hours)
    W = 70
    print(f"\nS1-E — did the world contradict it?   (window: last {hours/24:.0f} days)")
    print("─" * W)
    print("  method: direct reads off the resolutions tables and perspective_items.")
    print("  No model is consulted. Grades are P4 Rule 7's.\n")

    d = r.door
    print("  the door                                                    [mechanical]")
    print(f"    advances offered to it       {d.advances:>6}")
    print(f"    claims opened                {d.opened:>6}"
          + (f"   ({d.per_advance:.0%} of advances)" if d.per_advance is not None else ""))
    print(f"    refused at the door          {d.refused:>6}")
    for reason, n in sorted(d.refusal_reasons.items(), key=lambda kv: -kv[1]):
        print(f"        {reason:<44} {n:>3}")
    if d.declined is None:
        print(f"    declined                     UNREADABLE")
        print(f"        {d.unreadable}")
    else:
        print(f"    declined                     {d.declined:>6}   [from the call log]")

    s = r.resolution
    print("\n  resolution                                                  [mechanical]")
    print(f"    open, past due               {s.due:>6}")
    print(f"    settled in window            {s.settled:>6}"
          + (f"   median {s.median_latency_days:.0f}d to settle" if s.median_latency_days else ""))
    print(f"    still open                   {s.unsettled:>6}")
    print(f"    upheld / contradicted        {s.upheld:>6} / {s.contradicted}")

    p_ = r.positions
    print("\n  positions changed")
    print(f"    by the WORLD                 {p_.by_world:>6}   [mechanical — traced, INV-048]")
    print(f"    by the operator              {p_.by_operator:>6}   [mixed — dominant provenance]")
    print(f"    by the being itself          {p_.by_self:>6}   [mixed — dominant provenance, and R-15]")
    print(f"    unattributed                 {p_.unattributed:>6}")

    shapes = closing_shapes(conn)
    print("\n  why, upstream: can any concern be closed at all?             [mechanical]")
    print(f"    terminus the being decides   {shapes.self_terminus:>6}   'I can cite…' — self-graded (R-33)")
    print(f"    terminus nobody will reach   {shapes.commissioned:>6}   'a study correlating…' (R-33)")
    print(f"    names something that exists  {shapes.reachable:>6}")
    print(f"    no closing condition         {shapes.missing:>6}")
    print(f"    → {shapes.unreachable} of {shapes.total} concerns have a terminus nothing can reach")

    print("\n" + "─" * W)
    print(f"  S1-E: {'MET' if r.met else 'NOT MET'} — "
          + ("a position changed because the world contradicted it"
             if r.met else "no position has been changed by the world"))
    return 0


def main() -> int:
    cfg = load()
    conn = open_db(cfg.main_db_path)
    if "--read" in sys.argv:
        return _s1e(conn, cfg.repo_root)
    if "--refused" in sys.argv:
        return _refusals(conn)
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
        if c.went_against_me:
            print("\n".join(_cost_lines(conn, c.id)))
    print("─" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
