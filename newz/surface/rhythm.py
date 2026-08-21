"""The surface regenerates itself (P4 W7, R-37e).

**Phase 3 built five tools and zero rhythms.** The generator, `--check`,
`rebuild_check` and `freeze_check` all ran only when a person typed them, so the
published surface was stale from the moment the being wrote anything — and it
wrote a piece at 08:45 on the day the phase closed. `SurfaceScheduler` already
appeared in `run_newz.py` and is the *noticing* surface, which made this harder
to notice than it should have been.

It matters beyond tidiness because a page nothing refreshes shows yesterday
and is read as today; the daily read
against E3.6's page. A loop reading a page nothing refreshes is a loop reading
yesterday and reporting it as today.

**Regenerating costs nothing when nothing changed.** INV-067 keeps every
timestamp out of the output, so the same store produces the same bytes: a pass
over an unchanged store rewrites twelve identical files. That is what makes a
short interval reasonable rather than an interval chosen to be safe.
"""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)

PUBLISH_EVERY_S = 6 * 3600.0


def publish(db_path: Path, out_dir: Path, *, now: float | None = None) -> int:
    """Regenerate the whole surface. Returns the number of pages written."""
    from newz.store.db import open_db
    from newz.surface.generate import generate

    conn = open_db(db_path, read_only=True)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        for p in out_dir.iterdir():
            if p.name != ".gitkeep":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        generate(conn, out_dir, now=now or time.time())
        return len(list(out_dir.glob("*.html")))
    finally:
        conn.close()


class PublishScheduler:
    """Every six hours, and once at boot.

    Not nightly: the metrics move nightly and everything else on the page —
    what it wrote, what it is carrying, where it turned out to be wrong — moves
    during the day. Not on every write either; the surface is a whole-store
    function and regenerating it per episode would be a rebuild per read.
    """

    def __init__(self, db_path: Path, out_dir: Path, *,
                 interval_s: float = PUBLISH_EVERY_S):
        self._db_path = db_path
        self._out = out_dir
        self._interval = interval_s

    def _turn(self) -> None:
        pages = publish(self._db_path, self._out)
        logger.info("surface regenerated: %d page(s) in %s", pages, self._out)

    async def run(self) -> None:
        import asyncio

        from newz.crash import log_crash

        logger.info("surface: regenerating every %.0fh", self._interval / 3600)
        while True:
            try:
                await asyncio.to_thread(self._turn)
            except asyncio.CancelledError:
                raise
            except Exception:
                log_crash(self._db_path.parent.parent, "surface regeneration")
                logger.exception("surface regeneration failed — retrying next pass")
            await asyncio.sleep(self._interval)
