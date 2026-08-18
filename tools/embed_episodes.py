#!/usr/bin/env python3
"""Embed episodes for retrieval (P2 Phase 1.3).

Embeds anything digest-eligible that has no vector from the current model.
Safe to re-run and safe alongside the live loop: it commits in small batches
and skips whatever is already done.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.memory.embeddings import Embedder, pack
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
CHUNK = 128


def main() -> int:
    cfg = load()
    conn = open_db(cfg.main_db_path, busy_timeout_ms=30_000)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        print(f"migrations applied: {applied}")

    embedder = Embedder(cfg)
    todo = conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE digest_eligible=1"
        " AND LENGTH(summary) > 0"
        " AND (embedding IS NULL OR embedding_model IS NOT ?)", (embedder.model,)
    ).fetchone()[0]
    print(f"embedding {todo} episodes with {embedder.model}")
    if not todo:
        return 0

    done, started = 0, time.monotonic()
    while True:
        rows = conn.execute(
            "SELECT id, summary FROM episodes WHERE digest_eligible=1"
            " AND LENGTH(summary) > 0"
            " AND (embedding IS NULL OR embedding_model IS NOT ?)"
            " LIMIT ?", (embedder.model, CHUNK)
        ).fetchall()
        if not rows:
            break
        vectors = embedder.embed([r["summary"] for r in rows])
        conn.executemany(
            "UPDATE episodes SET embedding=?, embedding_model=? WHERE id=?",
            [(pack(v), embedder.model, r["id"]) for r, v in zip(rows, vectors)],
        )
        conn.commit()          # small transactions: the loop keeps writing
        done += len(rows)
        rate = done / max(time.monotonic() - started, 0.001)
        print(f"  {done}/{todo}  ({rate:.0f}/s)", flush=True)

    dim = len(conn.execute(
        "SELECT embedding FROM episodes WHERE embedding IS NOT NULL LIMIT 1"
    ).fetchone()["embedding"]) // 4
    print(f"done: {done} episodes embedded, dim={dim}, "
          f"{time.monotonic() - started:.0f}s")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
