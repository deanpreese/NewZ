"""Crash evidence — a failure must say why (RISKS R-21).

Extracted from tools/run_newz.py (then run_ambient.py), which learned this
on 2026-08-11: the
ambient loop stopped between two health checks and the only evidence was a
gap in the backup cadence, leaving the cause to be inferred.

The same blindness existed one layer down and cost a night. On 2026-08-13 at
02:30 a deliberation logged `started`, read four sources, and then recorded
no advance, no setback, and no `unreadable` row — it threw between parsing
and recording, into a `logger.exception` whose output goes to a stdout
nobody keeps. A background task that swallows its own death is the same
defect wherever it sits, so the remedy lives here rather than in one caller.
"""

from __future__ import annotations

import datetime as _dt
import logging
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)


def log_crash(repo_root: Path, what: str) -> None:
    """Append a timestamped traceback to logs/crash.log. Never raises.

    Called from an exception handler, so it must not be able to replace the
    failure it is recording with one of its own.
    """
    logger.critical("%s died", what, exc_info=True)
    try:
        crash = Path(repo_root) / "logs" / "crash.log"
        crash.parent.mkdir(parents=True, exist_ok=True)
        with open(crash, "a") as fh:
            fh.write(f"\n===== {_dt.datetime.now():%Y-%m-%d %H:%M:%S} "
                     f"— {what} =====\n")
            traceback.print_exc(file=fh)
    except Exception:  # noqa: BLE001
        logger.warning("could not write crash.log", exc_info=True)
