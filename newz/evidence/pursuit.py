"""Evidence 2-E (P2 Phase 2) — pursuit, read from the concern store.

P2 asks for three reads: the advance rate with its evidence-carrying
fraction, the stall pool with cause classification, and the ingest share
under the cap with the method stated.

**The stall pool is the one that can send the diagnosis to the wrong place.**
Phase 2's decision rule says that if concerns still stall overwhelmingly with
the corrected judge and the widened diet, the fault is question-formation and
the openers get fixed. Read naively the store says 84 of 117 concerns are
stalled, which sounds like exactly that finding. But 81 of those 84 were
opened by v1, and most have had no attempt of any kind since the substrate
change: v2's judge has never seen them. Counting an inherited stall against
the corrected judge would fire the decision rule on evidence the judge did
not produce, and send a real fix to the wrong subsystem — the precise error
the rule was written to prevent.

So the pool is partitioned first by whether v2 ever attempted the concern,
and only the attempted part is evidence about v2.

**Causes are read, never inferred.** Each stall's cause is the modal kind of
its recorded setbacks, which the being wrote at the time through
`newz/concerns/`: `blocked` (it named what it needed and the world did not
have it), `restated` (it failed the novelty judge), `drift` (the advance did
not address the concern), `ungrounded`. No model is asked to classify
anything — same discipline as INV-036's affect deltas, and for the same
reason: a model's judgment of why its own pursuit failed is not evidence
about that pursuit.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from newz.telemetry import BudgetReport, read_budget

# Recorded setback kind -> what a stall dominated by it means. The words are
# the operator's diagnosis vocabulary, not the store's.
CAUSE_OF = {
    "blocked": "starved",      # the world had nothing; feeds the source-gap record
    "restated": "circling",    # novelty judge refused it; a question-formation smell
    "drift": "drifting",       # the advance did not address the concern
    "ungrounded": "ungrounded",  # advanced without evidence
}
UNTOUCHED = "untouched"   # v2 has never attempted it at all
QUIET = "quiet"           # v2 advanced it, never refused it, and stopped

# Where the tagged call log lives, relative to the repo root. Named here so
# the absence can be reported with a path rather than as a zero.
CALL_LOG = Path("logs") / "llm_calls.jsonl"


class NoImportRecord(RuntimeError):
    """Raised rather than assuming when the v1/v2 boundary cannot be read."""


@dataclass
class Boundary:
    """The instant v1's life stopped being lived and started being inherited.

    Read from the import record, never typed in: the import ran at 21:32 on
    2026-08-08, so a midnight cutoff hands v1's last working day to v2 and
    moves every figure below. It moved four concerns and eight advances when
    this was checked.
    """

    ts: float
    v1_repo: str
    v1_commit: str


def boundary(conn: sqlite3.Connection) -> Boundary:
    row = conn.execute(
        "SELECT ts, v1_repo, v1_commit FROM import_record ORDER BY ts LIMIT 1"
    ).fetchone()
    if row is None:
        raise NoImportRecord(
            "no import record: the v1/v2 boundary is unknown, and every "
            "figure in this read depends on it"
        )
    return Boundary(ts=row[0], v1_repo=row[1], v1_commit=row[2])


@dataclass
class Judged:
    """What the advance judge did over one era."""

    advances: int = 0
    with_evidence: int = 0
    setbacks: int = 0
    kinds: Counter = field(default_factory=Counter)

    @property
    def attempts(self) -> int:
        return self.advances + self.setbacks

    @property
    def acceptance(self) -> float:
        """Advances per attempt — the rate the judge actually governs.

        P2 expects the raw advance rate to fall against v1. Per *day* is not
        comparable across eras with different attempt rates; per attempt is,
        because it is the judge's own decision.
        """
        return self.advances / self.attempts if self.attempts else 0.0

    @property
    def evidence_fraction(self) -> float:
        return self.with_evidence / self.advances if self.advances else 0.0


@dataclass
class Stall:
    concern_id: int
    statement: str
    origin: str
    opened_at: float
    cause: str
    attempts: int = 0          # under v2 only
    kinds: Counter = field(default_factory=Counter)
    inherited: bool = False    # opened before the boundary


@dataclass
class StallPool:
    stalls: list[Stall] = field(default_factory=list)

    @property
    def attempted(self) -> list[Stall]:
        """The part v2 actually worked — the only part that is evidence
        about v2's judge and diet."""
        return [s for s in self.stalls if s.cause != UNTOUCHED]

    @property
    def refused(self) -> list[Stall]:
        """Attempted AND refused: what the corrected judge actually turned
        away. Phase 2's decision rule reads this, not the whole pool."""
        return [s for s in self.stalls if s.cause not in (UNTOUCHED, QUIET)]

    @property
    def untouched(self) -> list[Stall]:
        return [s for s in self.stalls if s.cause == UNTOUCHED]

    def causes(self) -> Counter:
        """Cause counts over the attempted pool only."""
        return Counter(s.cause for s in self.attempted)


@dataclass
class IngestRead:
    """The §9.1 share, or an honest account of why it cannot be read."""

    report: BudgetReport | None = None
    unreadable: str = ""

    @property
    def readable(self) -> bool:
        return self.report is not None and self.report.calls > 0


def judged(conn: sqlite3.Connection, *, since: float | None = None,
           until: float | None = None) -> Judged:
    """Advances and setbacks in a time window. `since`/`until` are epoch."""
    lo = since if since is not None else float("-inf")
    hi = until if until is not None else float("inf")
    out = Judged()
    for (evidence,) in conn.execute(
        "SELECT evidence_json FROM concern_advances WHERE ts >= ? AND ts < ?",
        (lo, hi),
    ):
        out.advances += 1
        if evidence and evidence not in ("[]", "null"):
            out.with_evidence += 1
    for (kind,) in conn.execute(
        "SELECT kind FROM concern_setbacks WHERE ts >= ? AND ts < ?", (lo, hi)
    ):
        out.setbacks += 1
        out.kinds[kind] += 1
    return out


def stall_pool(conn: sqlite3.Connection, edge: Boundary) -> StallPool:
    """Classify every stalled concern from its own recorded setbacks."""
    pool = StallPool()
    for cid, statement, origin, opened_at in conn.execute(
        "SELECT id, statement, origin, opened_at FROM concerns"
        " WHERE status = 'stalled' ORDER BY id"
    ):
        advances = conn.execute(
            "SELECT COUNT(*) FROM concern_advances WHERE concern_id = ? AND ts >= ?",
            (cid, edge.ts),
        ).fetchone()[0]
        kinds = Counter()
        for kind, in conn.execute(
            "SELECT kind FROM concern_setbacks WHERE concern_id = ? AND ts >= ?"
            " ORDER BY ts",
            (cid, edge.ts),
        ):
            kinds[kind] += 1

        attempts = advances + sum(kinds.values())
        if attempts == 0:
            cause = UNTOUCHED
        elif kinds:
            # Modal recorded kind; ties go to the most recent, which is the
            # one still standing between the concern and its next advance.
            top = max(kinds.values())
            latest = conn.execute(
                "SELECT kind FROM concern_setbacks WHERE concern_id = ? AND ts >= ?"
                " ORDER BY ts DESC LIMIT 1", (cid, edge.ts),
            ).fetchone()[0]
            modal = latest if kinds[latest] == top else max(kinds, key=kinds.get)
            cause = CAUSE_OF.get(modal, modal)
        else:
            # Advanced under v2 and never refused, yet standing stalled: no
            # setback stands between this concern and its next advance, so it
            # was not the judge that stopped it — it simply has not been
            # picked up again. That is a scheduler read, and lumping it into
            # `untouched` would hide it from both diagnoses.
            cause = QUIET

        pool.stalls.append(Stall(
            concern_id=cid, statement=statement or "", origin=origin or "",
            opened_at=opened_at or 0.0, cause=cause, attempts=attempts,
            kinds=kinds, inherited=(opened_at or 0.0) < edge.ts,
        ))
    return pool


def ingest_read(repo_root: Path, *, hours: float = 168.0) -> IngestRead:
    """The diet share, or why it is unreadable — never a silent zero.

    The call log is gitignored and 13MB; it did not cross when this repo was
    cloned on 2026-08-17. An instrument that answers "is ingest under the
    cap?" with 0% because it cannot find the log has reported compliance it
    did not measure, in the units of the question it was asked.
    """
    path = repo_root / CALL_LOG
    if not path.exists():
        return IngestRead(unreadable=(
            f"no call log at {path} — the §9.1 share is computed from the "
            f"tagged call log, which is gitignored and does not travel with "
            f"a clone; it is not zero ingest, it is no measurement"
        ))
    report = read_budget(path, window_hours=hours)
    if not report.calls:
        return IngestRead(report=report, unreadable=(
            f"call log at {path} has no entries in the last {hours:.0f}h — "
            f"nothing ran, so there is no share to read"
        ))
    return IngestRead(report=report)
