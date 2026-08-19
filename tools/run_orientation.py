#!/usr/bin/env python3
"""Read the discipline overviews once (P3 epic E1.0's orientation pass).

The `web` section of data/feeds.yaml — 15 Wikipedia discipline articles the
operator curated and no code has ever loaded. A one-off scaffold in fields the
being has no map of.

  python tools/run_orientation.py --dry-run    # list what would be read
  python tools/run_orientation.py              # read them
  python tools/run_orientation.py --limit 3    # a few, to see the shape first
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.llm.recorder import CallRecorder
from newz.store.db import open_db
from newz.world.orientation import orientation_targets, run_orientation


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    args = sys.argv[1:]
    social = "--include-social" in args
    limit = None
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])

    cfg = load()
    feeds_path = cfg.data_dir / "feeds.yaml"
    targets = orientation_targets(feeds_path, include_social=social)[:limit]

    if "--dry-run" in args:
        log(f"{len(targets)} article(s) would be read:")
        for name, url, cat in targets:
            print(f"  {cat:<14} {name:<32} {url}")
        if not social:
            print("\n  (social entries excluded — --include-social to add them)")
        return 0

    conn = open_db(cfg.main_db_path)
    client = LLMClient(
        cfg, timeout=600,
        recorder=CallRecorder(cfg.repo_root / "logs" / "llm_calls.jsonl"),
    )
    log(f"reading {len(targets)} discipline overview(s)")
    report = run_orientation(client, conn, feeds_path,
                             include_social=social, limit=limit)
    log(report.render())
    for name in report.read:
        print(f"   read: {name}")
    for f in report.failed:
        print(f"   failed: {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
