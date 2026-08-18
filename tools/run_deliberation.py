#!/usr/bin/env python3
"""Run one deliberation now (P2 Phase 2.3). Safe alongside the live loop."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.deliberation.lite import Deliberator
from newz.llm.client import LLMClient
from newz.llm.recorder import CallRecorder
from newz.memory.embeddings import Embedder


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s",
                        datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cfg = load()
    client = LLMClient(cfg, timeout=600,
                       recorder=CallRecorder(cfg.repo_root / "logs" / "llm_calls.jsonl"))
    try:
        embedder = Embedder(cfg)
    except Exception:
        embedder = None
    force = "--force" in sys.argv
    d = Deliberator(cfg.main_db_path, client, embedder=embedder,
                    daily_budget=999 if force else 4)
    r = d.run_once()
    print("\n=== deliberation ===")
    for k, v in r.as_dict().items():
        print(f"  {k}: {str(v)[:220]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
