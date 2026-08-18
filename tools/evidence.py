#!/usr/bin/env python3
"""The evidence reads P2 names as gating Phase 3.

    python tools/evidence.py           # both
    python tools/evidence.py 1e        # Perspective diffs (Phase 1)
    python tools/evidence.py 2e        # pursuit (Phase 2)
    python tools/evidence.py 2e --stalls   # every stall, with its cause

Read-only, and no model is consulted. P2 Rule 0: every number here carries
its method, including the ones that cannot be produced.

Exit code 0 always — this reports, it does not judge. The decision rules in
P2 are the operator's to apply.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.evidence.perspective_window import read_window
from newz.memory.provenance import corpus_concentration
from newz.evidence.pursuit import (
    NoImportRecord,
    QUIET,
    UNTOUCHED,
    boundary,
    ingest_read,
    judged,
    stall_pool,
)
from newz.store.db import open_db

W = 78


def head(title: str) -> None:
    print(f"\n{title}\n{'─' * min(W, len(title) + 8)}")


def when(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def report_1e(conn) -> None:
    head("Evidence 1-E — Perspective diffs (P2 Phase 1)")
    w = read_window(conn)
    if not w.nights:
        print("  no nightly diffs recorded yet")
        for version, why in w.excluded:
            print(f"  v{version} excluded: {why}")
        return

    print(f"  method: direct reads off perspective.diff_json and "
          f"perspective_items.\n  No model is consulted (INV-023).\n")
    print(f"  {'ver':>4} {'night':<17} {'new':>4} {'rev':>4} {'car':>5} "
          f"{'rel':>4} {'dis':>4} {'c+':>3} {'c-':>3} {'novelty':>8} "
          f"{'tok':>6} {'cover':>6}")
    for n in w.nights:
        print(f"  {n.version:>4} {when(n.ts):<17} {n.added:>4} {n.revised:>4} "
              f"{n.carried:>5} {n.released:>4} "
              f"{n.disputed:>4} {n.contradictions_opened:>3} "
              f"{n.contradictions_closed:>3} {n.novelty:>7.1%} "
              f"{n.tokens:>6,} {n.coverage:>5.0%}")

    floor = w.meets_floor()
    print(f"\n  nights recorded          {len(w.nights)}  "
          f"({'meets' if floor else 'below'} 1-E's floor of 7)")
    for version, why in w.excluded:
        print(f"  v{version} excluded             {why}")

    dev = sum(n.developed for n in w.nights)
    held = sum(n.weighed for n in w.nights)
    print(f"\n  novelty (pooled)         {w.novelty:.1%}  "
          f"= {dev} added+revised of {held} held across the window")
    print(f"  restatement              {w.restatement:.1%}")
    print(f"  contradictions           {w.contradictions_opened} opened, "
          f"{w.contradictions_closed} closed")
    if w.compression is not None:
        first, last = w.nights[0], w.nights[-1]
        print(f"  compression              {w.compression:.2f}× tokens "
              f"({first.tokens:,} → {last.tokens:,}), "
              f"{w.item_compression:.2f}× items ({first.items} → {last.items})")
    print(f"  evidence coverage        {w.coverage:.0%} of items held now "
          f"cite at least one episode")
    print("                           (coverage, not grounding: whether the "
          "citation\n                           supports the claim is "
          "tools/what_shaped.py's read)")

    # 100% coverage says every position cites something. It does not say what.
    # A Perspective grounded entirely in the being's own episodes is the v1
    # leak wearing a citation (INV-026), and coverage alone would score it
    # perfect — so the mix is printed beside it rather than left to a second
    # tool the reader may not run.
    mix = corpus_concentration(conn)
    total = sum(mix.values())
    if total:
        parts = ", ".join(f"{prov} {n/total:.0%}" for prov, n in mix.most_common(4))
        print(f"  what grounds it          {parts}  ({total} refs)")
        self_share = sum(n for p, n in mix.items() if p == "self") / total
        if self_share > 0.5:
            print(f"  ** {self_share:.0%} of everything held is grounded in the "
                  f"being's own episodes.\n     Coverage cannot see this; "
                  f"INV-026 is about exactly this leak.")

    if w.compression is not None and w.compression < 1.0:
        print("\n  ** the document compressed across this window, so the "
              "novelty rate's\n     denominator shrank with it. Read the "
              "counts, not the trend in the rate.")
    if w.drifted:
        print("\n  ** stored novelty disagrees with the recomputed counts for "
              "version(s) "
              + ", ".join(str(n.version) for n in w.drifted)
              + " — the artifact was written by something other than the "
                "diff it records.")


def report_2e(conn, repo_root: Path, *, show_stalls: bool = False) -> None:
    head("Evidence 2-E — pursuit (P2 Phase 2)")
    try:
        edge = boundary(conn)
    except NoImportRecord as exc:
        print(f"  cannot read: {exc}")
        return

    print(f"  method: the v1/v2 boundary is the import record's own timestamp,"
          f"\n  {when(edge.ts)} — v1 @ {edge.v1_commit[:7]}. Everything before "
          f"it is inherited\n  life, not v2's. Causes are the recorded setback "
          f"kinds; no model is asked.\n")

    v1, v2 = judged(conn, until=edge.ts), judged(conn, since=edge.ts)
    print(f"  {'':<12} {'advances':>9} {'setbacks':>9} {'accept':>8} "
          f"{'w/ evidence':>12}")
    for label, era in (("v1 inherited", v1), ("v2 lived", v2)):
        print(f"  {label:<12} {era.advances:>9} {era.setbacks:>9} "
              f"{era.acceptance:>7.1%} {era.evidence_fraction:>11.1%}")
    print("\n  acceptance is advances per attempt — the decision the judge "
          "actually makes.\n  A per-day rate is not comparable across eras "
          "with different attempt rates.")
    if v2.attempts and v2.acceptance > v1.acceptance:
        print(f"\n  ** P2 expects the raw advance rate to FALL against v1 — "
              f"'if it doesn't,\n     the corrected judge is decorative'. It "
              f"rose: {v1.acceptance:.1%} → {v2.acceptance:.1%} "
              f"over {v2.attempts} attempts.\n     Small n, and v2's concerns "
              f"are young (early advances come easier), but\n     this is the "
              f"read 2-E asks for and it points the way P2 said to watch.")

    pool = stall_pool(conn, edge)
    causes = pool.causes()
    print(f"\n  stall pool               {len(pool.stalls)} concerns stand stalled")
    print(f"    untouched by v2        {len(pool.untouched):>4}  "
          f"no advance or setback since the boundary —")
    print( "                                 v2's judge has never seen these")
    print(f"    attempted by v2        {len(pool.attempted):>4}  "
          f"the only part that is evidence about v2")
    for cause, n in causes.most_common():
        gloss = {
            "starved": "named what it needed; the world had nothing",
            "circling": "refused by the novelty judge",
            "drifting": "advance did not address the concern",
            "ungrounded": "advanced without evidence",
            QUIET: "advanced, never refused, not picked up again",
        }.get(cause, "")
        print(f"      {cause:<20} {n:>4}  {gloss}")

    if pool.refused:
        print(f"\n  Phase 2's decision rule reads the REFUSED pool "
              f"({len(pool.refused)}), not all "
              f"{len(pool.stalls)}.\n  Firing it on the inherited pool would "
              f"send a real fix to the wrong\n  subsystem — the error the rule "
              f"exists to prevent.")

    ing = ingest_read(repo_root)
    print(f"\n  ingest share (§9.1)")
    if not ing.readable:
        print(f"    UNREADABLE — {ing.unreadable}")
    else:
        b = ing.report
        print(f"    method: llm_calls.jsonl over {b.window_hours:.0f}h, "
              f"prompt+completion, tagged at the call site")
        print(f"    ingest                 {b.ingest_tokens:>10,} tok "
              f"({b.share('ingest'):.1%} of all cognition)")
        print(f"    deliberation + sleep   {b.earning_tokens:>10,} tok")
        print(f"    binding ceiling        {b.binding_ceiling():>10}  "
              f"{b.ingest_ceiling():,} tok")
        print(f"    {'HOLDS' if b.invariant_holds() else 'BREACHED'}"
              f"                  headroom {b.ingest_headroom():,} tok")

    if show_stalls:
        print()
        for s in sorted(pool.stalls, key=lambda x: (x.cause, x.concern_id)):
            tag = "v1" if s.inherited else "v2"
            print(f"  [{s.cause:<10}] {tag} c{s.concern_id:<4} "
                  f"{s.attempts:>2} attempt(s)  {s.statement[:52]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("which", nargs="?", default="all", choices=["1e", "2e", "all"])
    ap.add_argument("--stalls", action="store_true",
                    help="list every stalled concern with its cause")
    args = ap.parse_args()

    cfg = load()
    conn = open_db(cfg.main_db_path, read_only=True)
    try:
        if args.which in ("1e", "all"):
            report_1e(conn)
        if args.which in ("2e", "all"):
            report_2e(conn, cfg.repo_root, show_stalls=args.stalls)
        print()
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
