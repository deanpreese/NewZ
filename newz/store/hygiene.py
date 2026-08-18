"""Corpus hygiene (P2 Phase 1.5) — read the imported past accurately.

The imported v1 episode store arrived uniformly tagged `kind='v1_tick'`,
`provenance='self'`, because v1 never populated the fields that would have
distinguished its own activity from the operator's (percept_ref,
emission_refs: 0/2,632 each). Measured composition:

    1,137  SELF PROBE …            the being probing itself
      151  INITIATIVE PROBE …      likewise
    1,041  prefix_cache_miss_rate_high: 1.00
        1  endpoint_down: …
      265  plain prose             the operator actually talking
       37  (empty)

Two problems follow, and this module fixes both without deleting anything:

1. **Provenance is wrong**, so Phase 1.3's self-echo filter would have
   nothing to separate 265 real conversations from 1,288 self-probes.
2. **One fact is stored 1,041 times.** S2 §6.1 requires substrate state to
   reach the being as a *folded clause*; v1 stored the raw percepts, and
   sleep then read each as a separate lived moment — which is why
   Perspective v1's identity claims are partly derived from a monitoring
   log. Folding corrects the *proportion*, not the fact: the cache-miss era
   was real, and the fold says so once instead of a thousand times.

Classification is pattern-based and total — every row matches exactly one
rule, verified by count. No LLM judgment enters the being's past.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime

SUBSTRATE_RE = re.compile(r"^[a-z][a-z0-9_]*:")          # metric-style key
SELF_PROBE_RE = re.compile(r"^(SELF PROBE|INITIATIVE PROBE)\b")

# What each class becomes. `digest_eligible` governs what sleep READS.
# Self-probes stay digestible — v1's life genuinely was mostly self-probing
# and a Perspective that says so is telling the truth. They are excluded
# from *evidence* contexts by provenance, which is a different filter.
CLASSES = {
    "substrate":    dict(kind="v1_substrate",    provenance="world:substrate", digest=0),
    "self_probe":   dict(kind="v1_self_probe",   provenance="self",            digest=1),
    "conversation": dict(kind="v1_conversation", provenance="human:{op}",      digest=1),
    "empty":        dict(kind="v1_empty",        provenance="self",            digest=0),
}


def classify(summary: str | None) -> str:
    s = (summary or "").strip()
    if not s:
        return "empty"
    if SUBSTRATE_RE.match(s):
        return "substrate"
    if SELF_PROBE_RE.match(s):
        return "self_probe"
    return "conversation"


@dataclass
class HygieneReport:
    counts: dict[str, int] = field(default_factory=dict)
    folded_episode_id: int | None = None
    folded_rows: int = 0
    fold_span: tuple[float, float] | None = None
    applied: bool = False

    def total(self) -> int:
        return sum(self.counts.values())


def survey(conn: sqlite3.Connection) -> HygieneReport:
    """Classify without writing anything."""
    report = HygieneReport()
    for row in conn.execute("SELECT summary FROM episodes WHERE kind='v1_tick'"):
        cls = classify(row["summary"])
        report.counts[cls] = report.counts.get(cls, 0) + 1
    return report


def run_hygiene(
    conn: sqlite3.Connection, operator_id: str, *, apply: bool = False
) -> HygieneReport:
    """Reclassify imported episodes and fold the substrate telemetry.

    Idempotent: rows already reclassified are no longer `kind='v1_tick'`, so
    a second run finds nothing to do.
    """
    report = survey(conn)
    if not apply or not report.total():
        return report

    rows = conn.execute(
        "SELECT id, ts, summary FROM episodes WHERE kind='v1_tick'"
    ).fetchall()

    substrate_ids: list[int] = []
    substrate_ts: list[float] = []
    for r in rows:
        cls = classify(r["summary"])
        spec = CLASSES[cls]
        conn.execute(
            "UPDATE episodes SET kind=?, provenance=?, digest_eligible=? WHERE id=?",
            (spec["kind"], spec["provenance"].format(op=operator_id),
             spec["digest"], r["id"]),
        )
        if cls == "substrate":
            substrate_ids.append(r["id"])
            substrate_ts.append(r["ts"])

    # The fold (S2 §6.1): one clause the being can actually see, standing
    # for what was previously a thousand identical moments.
    if substrate_ids:
        first, last = min(substrate_ts), max(substrate_ts)
        days = (last - first) / 86400
        summary = (
            f"Across {len(substrate_ids)} recorded moments between "
            f"{datetime.fromtimestamp(first):%Y-%m-%d} and "
            f"{datetime.fromtimestamp(last):%Y-%m-%d} — about {days:.0f} days — "
            "my prefix cache missed on every request: context did not persist "
            "between turns, and each exchange began from nothing. One condition, "
            "sustained, not a thousand separate events."
        )
        cur = conn.execute(
            "INSERT INTO episodes (ts, kind, provenance, summary, content_json,"
            " digest_eligible, source_ref) VALUES (?,?,?,?,?,1,?)",
            (last, "substrate_fold", "world:substrate", summary,
             json.dumps({
                 "folded_rows": len(substrate_ids),
                 "first_ts": first, "last_ts": last,
                 "method": "pattern classification on episode summary; "
                           "metric-style prefix `^[a-z_]+:`",
                 "folded_at": time.time(),
             }),
             "hygiene:substrate_fold"),
        )
        report.folded_episode_id = cur.lastrowid
        report.folded_rows = len(substrate_ids)
        report.fold_span = (first, last)
        conn.executemany(
            "UPDATE episodes SET folded_into=? WHERE id=?",
            [(report.folded_episode_id, i) for i in substrate_ids],
        )

    conn.commit()
    report.applied = True
    return report
