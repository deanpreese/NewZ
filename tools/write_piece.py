#!/usr/bin/env python3
"""Compose one piece (P3 epics E0.1, E0.2).

The being chooses a subject from what it already carries and writes about it.
Run it three times for Phase 0's read; the unique index means it picks a
different subject each time.

  python tools/write_piece.py           # choose, write, store
  python tools/write_piece.py --dry-run # choose and write, print, store nothing
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
from newz.works.compose import (candidate_subjects, choose_subject,
                                compose_piece, write_work)
from newz.works.rhythm import close_subject


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    cfg = load()
    conn = open_db(cfg.main_db_path)
    client = LLMClient(
        cfg, timeout=600,
        recorder=CallRecorder(cfg.repo_root / "logs" / "llm_calls.jsonl"),
    )

    subjects = candidate_subjects(conn)
    if not subjects:
        log("nothing left to write about: every open concern and held position has a piece")
        return 1
    log(f"{len(subjects)} subjects on offer — {sum(s.kind == 'concern' for s in subjects)} concerns, "
        f"{sum(s.kind == 'position' for s in subjects)} positions")

    subject, because = choose_subject(client, conn, subjects)
    log(f"chose [{subject.kind}:{subject.ref}] {subject.text[:90]}")
    log(f"because: {because}")

    piece = compose_piece(client, conn, subject, because)
    log(f"wrote {piece.word_count} words ({piece.completion_tokens} completion tokens)")

    print()
    print(f"# {piece.title}")
    print()
    print(piece.body)
    print()

    if dry_run:
        log("--dry-run: nothing stored")
        return 0
    work_id = write_work(conn, piece)
    status = close_subject(conn, piece, work_id)
    log(f"stored as work {work_id} — read it back with: python tools/read_works.py {work_id}")
    if status == "closed":
        log(f"concern {piece.subject.ref} closed — the being has said its piece")
    return 0


if __name__ == "__main__":
    sys.exit(main())
