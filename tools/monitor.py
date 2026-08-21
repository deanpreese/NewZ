#!/usr/bin/env python3
"""The monitor — the instruments, read on a rhythm (P4 Phase 3A).

    python tools/monitor.py           # every hour, until stopped
    python tools/monitor.py --once    # one turn, then exit

Started by hand, beside the being rather than inside it. A monitor that lives
in the thing it monitors reports nothing at the moment that matters — and once
it writes the readings from outside, the readings stop being evidence the being
is alive, so liveness comes only from rows the being itself writes.

It writes `data/monitor.db`, never the being's store. Nothing here judges and
no model is called.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.monitor.run import loop, turn


def main(argv: list[str]) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load()
    if "--once" in argv:
        t = turn(cfg)
        print(f"readings   {t.readings} ({t.unmeasured} unmeasured)")
        if t.skipped:
            print(f"skipped    {t.skipped}")
        print(f"sent       {'yes' if t.sent else t.send_error or 'not due'}")
        return 0
    print(f"monitor: hourly, sending at or after {cfg.monitor_send_hour:02d}:00")
    loop(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
