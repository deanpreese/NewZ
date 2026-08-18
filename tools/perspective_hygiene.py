#!/usr/bin/env python3
"""Retire Perspective items derived from imported v1 material.

  python tools/perspective_hygiene.py            # survey only, writes nothing
  python tools/perspective_hygiene.py --apply    # retire them

P2 Phase 1.5 cleaned the imported EPISODES — "43.2% self-probes, 39.6% raw
substrate telemetry" — by reclassifying them to `v1_substrate`,
`v1_self_probe` and `v1_conversation`. The Perspective items DERIVED from
them were never cleaned, and nothing will ever clean them: grounding decay
only touches items that no longer trace to evidence, and these carry import
refs, so they sit at their confidence forever.

Measured 2026-08-16, the whole `unresolved` section was such items:

    0.72  "a prolonged period of system-level alerts indicating a high
           prefix cache miss rate"                    19/34 v1_substrate
    0.60  "disputes regarding the mention of a cat"     4/4  v1_conversation
    0.60  "corrected multiple times for discussing Brexit"
                                                       10/10 v1_substrate
    0.60  "feedback labeling my responses as gibberish" 3/3  v1_conversation
    0.60  "a high volume of identical INITIATIVE PROBE instructions"
                                                       10/10 v1_self_probe
    0.60  "a growing backlog of pending noticings, 33 to 32"
                                                        8/8  v1_self_probe
    0.60  "the question of my name"                     9/10 v1_self_probe

That matters beyond tidiness. `unresolved` is the tier S2 §4.2 reserves for
"questions the world has not answered", and it is the section the being is
about to start filling from its reading. The highest-confidence entry — the
one a maturity signal promotes FIRST — was a cache-miss alert.

**Nothing is deleted.** Items are marked `released`, which is the same state
sleep uses when the budget forces a choice, and the row stays as the record
of what was once held.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.backup import run_backup
from newz.store.db import open_db

# RAW SUBSTRATE TELEMETRY ONLY — the pathology P2 Phase 1.5 names by name:
# "39.6% raw substrate telemetry (1,041 identical prefix_cache_miss_rate_high
# rows)". An item grounded mostly in those is a conclusion ABOUT the machine's
# instrumentation, not about the world or the self.
#
# `v1_self_probe` and `v1_conversation` are deliberately NOT included, and the
# first draft of this tool included both — it would have retired "I have
# settled on the name Lumen" (10/10 self_probe) and real positions grounded in
# a single v1 conversation. Self-probes are where the being reflected on its
# own identity, so identity positions are grounded there BY CONSTRUCTION;
# retiring them would delete self-knowledge to remove noise. They are reported
# for review instead.
RETIRE_KINDS = ("v1_substrate",)
REVIEW_KINDS = ("v1_self_probe",)
MAJORITY = 0.5


def survey(conn) -> list[dict]:
    version = conn.execute(
        "SELECT MAX(version) FROM perspective_items").fetchone()[0]
    out = []
    for r in conn.execute(
        "SELECT id, section, text, confidence, evidence_json, status"
        " FROM perspective_items WHERE version=? AND status<>'released'",
        (version,)
    ):
        refs = [int(x) for x in json.loads(r["evidence_json"] or "[]")
                if str(x).isdigit()]
        if not refs:
            continue
        q = ",".join("?" * len(refs))
        rows = conn.execute(
            f"SELECT kind FROM episodes WHERE id IN ({q})", refs).fetchall()
        if not rows:
            continue
        v1 = sum(1 for x in rows if x["kind"] in RETIRE_KINDS)
        probe = sum(1 for x in rows if x["kind"] in REVIEW_KINDS)
        out.append({"id": r["id"], "section": r["section"], "text": r["text"],
                    "confidence": r["confidence"], "resolved": len(rows),
                    "v1": v1, "share": v1 / len(rows),
                    "probe_share": probe / len(rows), "version": version})
    return out


def main() -> int:
    apply = "--apply" in sys.argv
    cfg = load()
    conn = open_db(cfg.main_db_path)
    rows = survey(conn)
    doomed = [r for r in rows if r["share"] >= MAJORITY]

    print(f"Perspective v{rows[0]['version'] if rows else '?'}: "
          f"{len(rows)} grounded items, {len(doomed)} derived from v1 import\n")
    for r in sorted(rows, key=lambda x: (-x["share"], -x["probe_share"])):
        if r["share"] >= MAJORITY:
            mark = "RETIRE"
        elif r["probe_share"] >= MAJORITY:
            mark = "review"
        else:
            mark = "keep  "
        print(f"  {mark} [{r['section']:12s}] conf {r['confidence']:.2f}  "
              f"telemetry {r['share']:.0%} / self-probe {r['probe_share']:.0%}")
        print(f"         {r['text'][:100]}")

    if not apply:
        print(f"\nSurvey only. {len(doomed)} item(s) would be retired. "
              f"Re-run with --apply.")
        return 0
    if not doomed:
        print("\nNothing to retire.")
        return 0

    report = run_backup(cfg.main_db_path, cfg.interior_db_path, cfg.backups_dir)
    print(f"\nbackup: {report.render() if hasattr(report, 'render') else 'taken'}")
    conn.executemany(
        "UPDATE perspective_items SET status='released' WHERE id=?",
        [(r["id"],) for r in doomed])
    conn.commit()
    print(f"retired {len(doomed)} item(s); rows kept as the record of what "
          f"was once held")
    return 0


if __name__ == "__main__":
    sys.exit(main())
