#!/usr/bin/env python3
"""Run one nightly sleep (P2 Phase 1.1).

Safe to run while the ambient loop is live: sleep uses its own connection,
holds no transaction across model calls, and yields the night if the store
is busy rather than blocking the being's replies.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.llm.recorder import CallRecorder
from newz.sleep.nightly import NightlySleep
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-5s %(name)s  %(message)s",
                        datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cfg = load()

    conn = open_db(cfg.main_db_path)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        logging.info("migrations applied: %s", applied)
    conn.close()

    client = LLMClient(cfg, timeout=600,
                       recorder=CallRecorder(cfg.repo_root / "logs" / "llm_calls.jsonl"))
    started = time.monotonic()
    try:
        from newz.memory.embeddings import Embedder

        embedder = Embedder(cfg)
    except Exception:
        embedder = None
    report = NightlySleep(cfg.main_db_path, client, cfg.operator_id or "operator",
                          embedder=embedder).run()
    took = time.monotonic() - started

    print(f"\n=== sleep finished in {took:.0f}s ===")
    if report.skipped_reason:
        print(f"  skipped: {report.skipped_reason}")
        return 0
    print(f"  gathered {report.gathered} episodes in {report.batches} batch(es)")
    print(f"  observations: {report.observations}")
    print(f"  verdicts: {report.verdicts}")
    d = report.diff
    print(f"\n  perspective v{report.version} — {report.token_count} est. tokens")
    print(f"  novelty rate: {d.get('novelty_rate')}  (added {len(d.get('added', []))}, "
          f"revised {len(d.get('revised', []))}, carried {d.get('carried')}, "
          f"released {len(d.get('released', []))})")
    print(f"  contradictions opened {d.get('contradictions_opened')}, "
          f"closed {d.get('contradictions_closed')}")
    for label in ("added", "revised", "released"):
        for t in d.get(label, [])[:6]:
            print(f"    [{label}] {t[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
