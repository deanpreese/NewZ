#!/usr/bin/env python3
"""The operator journal (P2 Rule 3). List entries, or add one from the CLI.

  python tools/journal.py                 # list all entries
  python tools/journal.py add <entry...>  # add (prefix 'v1:' to tag old system)
"""

from __future__ import annotations

import datetime
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.db import open_db


def main() -> int:
    cfg = load()
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        entry = " ".join(sys.argv[2:]).strip()
        if not entry:
            print("usage: journal.py add <entry...>", file=sys.stderr)
            return 1
        tag = "v2"
        for prefix in ("v1:", "v2:"):
            if entry.lower().startswith(prefix):
                tag = prefix[:2]
                entry = entry[len(prefix):].strip()
        conn = open_db(cfg.main_db_path)
        conn.execute(
            "INSERT INTO journal (ts, day, system_tag, entry) VALUES (?,?,?,?)",
            (time.time(), datetime.date.today().isoformat(), tag, entry),
        )
        conn.commit()
        conn.close()
        print(f"noted ({tag})")
        return 0

    conn = open_db(cfg.main_db_path, read_only=True)
    rows = conn.execute(
        "SELECT day, system_tag, entry FROM journal ORDER BY ts"
    ).fetchall()
    if not rows:
        print("journal is empty — day one is today")
        return 0
    for r in rows:
        print(f"{r['day']} [{r['system_tag']}] {r['entry']}")
    days = len({r["day"] for r in rows})
    print(f"\n{len(rows)} entries over {days} day(s)")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
