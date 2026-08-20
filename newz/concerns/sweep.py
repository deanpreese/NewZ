"""The closure sweep — recognising concerns that are already finished.

**Closure was welded to progress.** `attempt_closure` had one caller, at the
moment after an advance was recorded, on the reasoning that this is "the only
moment closure can have become true". That is right for a concern still moving
and wrong for one that has stopped: a concern with nothing left to advance can
never be asked whether it is already done, however completely it answered its
own question before it stalled. Closure is not work. It is noticing, and
noticing had no path.

**What justifies this, and what does not.** Measured 2026-08-20, read-only: 8
of 23 eligible stalled concerns met their closing condition on their EXISTING
dossiers, with no retrieval — and both concerns that had closed in a retrieval
run closed identically without it. That figure is model-graded and was run
once, so under INV-073 it may halt and may never justify. It is the reason to
look.

The warrant is mechanical. 77 concerns are stalled with BOTH counters below the
limits that produce a stall (`STALL_LIMIT`, `BLOCKED_LIMIT`) — a state the
current code cannot create, so they were stalled under rules that no longer
apply. For every one of them closure is structurally unreachable. That is
checkable without asking a model anything, and it is what this is built on.

**It does not revive anything.** A swept concern is judged, not re-opened: no
`MAX_OPEN_CONCERNS` slot is taken, so nothing here competes with new curiosity,
and no counter is reset. `stall_count = 4` stays true. The being did fail to
move it; it also, it turns out, had already answered it. Those are different
facts and both are kept.

**Two caps, for two different reasons.** `limit` bounds DEEP calls per run.
`max_closures` bounds how many positions can reach ONE sleep — sleep's
`_closure_observations` collects every `concern_closed` episode since the last
one, so an uncapped sweep of the backlog would deliver the whole batch into a
single confrontation. Positions entering the Perspective is the least
reversible thing this system does (INV-009), and a backlog of fixed size has no
reason to be drained fast.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field

from newz.concerns.model import BLOCKED_LIMIT, STALL_LIMIT

logger = logging.getLogger(__name__)

# A concern that did not meet its condition will not meet it on an unchanged
# dossier. 15 of the 23 measured did not close; without this stamp they would
# be re-judged every run, one DEEP call each, forever.
JUDGE_COOLDOWN_HOURS = 168.0

DEFAULT_LIMIT = 5
DEFAULT_MAX_CLOSURES = 2


@dataclass
class SweepResult:
    judged: int = 0
    closed: list[int] = field(default_factory=list)
    stopped_early: str = ""

    def __str__(self) -> str:
        s = f"judged {self.judged}, closed {len(self.closed)}"
        if self.closed:
            s += " (" + ", ".join(f"c{i}" for i in self.closed) + ")"
        return s + (f" — stopped: {self.stopped_early}" if self.stopped_early else "")


def eligible(conn: sqlite3.Connection, *, now: float | None = None,
             limit: int = DEFAULT_LIMIT) -> list[int]:
    """Stalled concerns in a state today's rules would not produce.

    Both counters below their limits. No shape test and no advance threshold:
    an earlier draft required `advance_count >= 2`, because the first concern
    observed to close had two — and the adjacent stratum then closed 0 of 4, a
    criterion fitted to a single observation. `judge_closure` already enforces
    `MIN_ADVANCES_TO_JUDGE` and is the right place for that decision.

    Oldest-judged first, so the sweep rotates through the backlog rather than
    re-reading the head of the table every run.
    """
    now = now or time.time()
    cutoff = now - JUDGE_COOLDOWN_HOURS * 3600.0
    return [r[0] for r in conn.execute(
        "SELECT id FROM concerns"
        " WHERE status='stalled' AND stall_count < ? AND blocked_count < ?"
        "   AND (last_judged_at IS NULL OR last_judged_at < ?)"
        " ORDER BY COALESCE(last_judged_at, 0), id LIMIT ?",
        (STALL_LIMIT, BLOCKED_LIMIT, cutoff, limit))]


def sweep(conn: sqlite3.Connection, client, *, limit: int = DEFAULT_LIMIT,
          max_closures: int = DEFAULT_MAX_CLOSURES,
          now: float | None = None) -> SweepResult:
    """Judge eligible stalled concerns; close the ones that are finished.

    The stamp is written whether or not the concern closed — a judgement that
    said "not met" is exactly the one worth not repeating for a week.
    """
    from newz.concerns.closure import attempt_closure

    now = now or time.time()
    out = SweepResult()
    for concern_id in eligible(conn, now=now, limit=limit):
        if len(out.closed) >= max_closures:
            out.stopped_early = (
                f"{max_closures} closures is one sleep's worth — positions "
                "reaching the Perspective is the least reversible act here")
            break
        status = attempt_closure(client, conn, concern_id)
        out.judged += 1
        conn.execute("UPDATE concerns SET last_judged_at=? WHERE id=?",
                     (now, concern_id))
        conn.commit()
        if status == "closed":
            out.closed.append(concern_id)
    logger.info("closure sweep: %s", out)
    return out
