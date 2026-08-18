#!/usr/bin/env python3
"""Run first sleep (P2 Phase 0.3). --pilot digests a small slice and prints
without writing; the full run writes perspective v1 and the transition
episode (Phase 0.5), and refuses to overwrite an existing Perspective."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.sleep.first_sleep import (
    compress_if_over_budget,
    digest_episodes,
    synthesize_perspective,
    write_perspective,
    write_transition_episode,
)
from newz.store.db import open_db


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    pilot = "--pilot" in sys.argv
    cfg = load()
    conn = open_db(cfg.main_db_path)
    client = LLMClient(cfg, timeout=600)

    if not pilot:
        existing = conn.execute("SELECT COUNT(*) FROM perspective").fetchone()[0]
        if existing:
            log(f"refusing: perspective already has {existing} version(s); sleep is append-only")
            return 1

    limit = 160 if pilot else None
    log(f"first sleep {'PILOT' if pilot else 'FULL'} — digesting episodes (limit={limit})")
    observations, report = digest_episodes(client, conn, limit=limit, log=log)
    log(f"digest done: {report.observations} observations from {report.batches} batches, "
        f"{report.dropped_ungrounded} dropped ungrounded")

    content = synthesize_perspective(client, conn, observations, report, log=log)
    content = compress_if_over_budget(client, content, log=log)

    if pilot:
        conn.rollback()  # discard any claim-audit updates from the pilot
        print("\n" + "=" * 70 + "\n" + content + "\n" + "=" * 70)
        log(f"pilot complete (nothing written): {report.as_dict()}")
        return 0

    write_perspective(conn, content, report)
    write_transition_episode(conn)
    log(f"perspective v1 written: {report.as_dict()}")
    log("transition episode written (Phase 0.5)")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
