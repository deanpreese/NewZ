#!/usr/bin/env python3
"""The monitor — the instruments, read on a rhythm (P4 Phase 3A).

    python tools/monitor.py           # one turn: read, and send if due

**The rhythm belongs to the being** *(operator, 2026-08-21)*:
`MonitorScheduler` runs inside `tools/run_newz.py`, so there is one process to
start. This is the same turn, on demand — for a reading between hours, for a
send after a failed one, and for looking at what the day's email would say.

A turn is idempotent: it reads once per clock hour and sends once per day, so
running this while the being is up costs nothing and duplicates nothing.

It writes `data/monitor.db`, never the being's store. Nothing here judges and
no model is called.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.monitor.run import turn


def main(argv: list[str]) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load()
    t = turn(cfg)
    print(f"readings   {t.readings} ({t.unmeasured} unmeasured)")
    if t.skipped:
        print(f"skipped    {t.skipped}")
    print(f"sent       {'yes' if t.sent else t.send_error or 'not due'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
