#!/usr/bin/env python3
"""One-time: recover items from the markdown-only Perspective v1 (P2 1.1).

First sleep wrote a document; nightly sleep confronts items. This parses
v1's carried sections into rows so the first nightly diff compares against
a real baseline instead of treating every held position as new.

  python tools/backfill_perspective_items.py           # show what it finds
  python tools/backfill_perspective_items.py --apply
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.sleep.perspective import parse_document, save_items
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def main() -> int:
    apply = "--apply" in sys.argv
    cfg = load()
    conn = open_db(cfg.main_db_path)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        print(f"migrations applied: {applied}")

    row = conn.execute(
        "SELECT version, content FROM perspective ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row is None:
        print("no Perspective to backfill", file=sys.stderr)
        return 1
    existing = conn.execute(
        "SELECT COUNT(*) FROM perspective_items WHERE version=?", (row["version"],)
    ).fetchone()[0]
    if existing:
        print(f"v{row['version']} already has {existing} items — nothing to do")
        return 0

    items = parse_document(row["content"])
    by_section: dict[str, int] = {}
    for i in items:
        by_section[i.section] = by_section.get(i.section, 0) + 1
    print(f"\nrecovered {len(items)} items from Perspective v{row['version']}:")
    for s, n in by_section.items():
        print(f"  {s:14s} {n:>3}")
    grounded = sum(1 for i in items if i.evidence)
    print(f"  grounded (carry episode refs): {grounded}/{len(items)}")
    print("\nsample:")
    for i in items[:3]:
        print(f"  [{i.section}] {i.text[:90]}  refs={i.evidence[:4]}")

    if not apply:
        print("\nre-run with --apply to write.")
        return 0

    save_items(conn, row["version"], items)
    conn.commit()
    print(f"\nwrote {len(items)} items for version {row['version']}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
