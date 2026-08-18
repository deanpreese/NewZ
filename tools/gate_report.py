#!/usr/bin/env python3
"""Gate health with a denominator (S2 §11): verdict counts, hold rate over
candidates, and the persisted reasons for every hold."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.db import open_db


def main() -> int:
    conn = open_db(load().main_db_path, read_only=True)
    rows = conn.execute(
        "SELECT verdict, COUNT(*) n FROM gate_log GROUP BY verdict"
    ).fetchall()
    counts = {r["verdict"]: r["n"] for r in rows}
    total = sum(counts.values())
    if not total:
        print("gate_log is empty — no candidates yet")
        return 0
    holds = counts.get("revise", 0) + counts.get("block", 0)
    print(f"candidates: {total}   verdicts: {counts}")
    print(f"hold rate: {holds}/{total} = {holds / total:.1%}")
    print("\nholds (most recent first):")
    for r in conn.execute(
        "SELECT ts, verdict, clause_id, asserted_span, note FROM gate_log"
        " WHERE verdict IN ('revise','block') ORDER BY ts DESC LIMIT 20"
    ):
        print(f"  [{r['verdict']}] {r['clause_id'] or '-'} — span: {r['asserted_span'] or '-'!r:.80} {r['note']}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
