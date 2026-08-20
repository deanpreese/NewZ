"""S1-E — did the world contradict it? (P4 epic E1.6)

P4's Phase 1 decision rule turns on one read: **at least one position changed
because the world contradicted it**, distinct from the operator contradicting it
and from the being contradicting itself. Until this module existed there was no
reader for it. `tools/claims.py` rendered claims and their costs and computed no
rate, no latency, and no count of positions changed — so "the being never
commits" and "the door was never called" were indistinguishable in the store,
and telling them apart meant grepping a gitignored call log by hand.

**Three grades, per P4 Rule 7, and they are not equal.**

  mechanical   the door's counts and the world column. `claim_costs` records
               exactly which Perspective items a refutation charged, traced
               rather than judged (INV-048), so "changed by the world" is a
               count and not an inference.
  mixed        the operator and self columns. A Perspective item that was
               revised or released is attributed by the dominant provenance of
               its supporting episodes — which is a derivation, not a
               measurement, and is labelled so. R-15 also applies: imported v1
               episodes are uniformly `provenance='self'`, so the self column
               is overstated for anything grounded in the import.
  unreadable   declines. INV-046 records refusals and deliberately not
               declines, so the store cannot see them; only the tagged call log
               can, and it is gitignored (INV-044). Absent, this reports itself
               unmeasured rather than zero.

The difference between the mechanical and mixed columns is the whole point of
the read. The world column is the one S1-E turns on, and it is the one that is
exact.
"""

from __future__ import annotations

import json
import re
import sqlite3
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from newz.memory.provenance import what_shaped

CALL_LOG = Path("logs") / "llm_calls.jsonl"
DAY = 86400.0


@dataclass
class DoorRead:
    advances: int = 0
    opened: int = 0
    refused: int = 0
    refusal_reasons: dict[str, int] = field(default_factory=dict)
    declined: int | None = None          # None = unreadable
    unreadable: str | None = None

    @property
    def per_advance(self) -> float | None:
        return self.opened / self.advances if self.advances else None


@dataclass
class ResolutionRead:
    due: int = 0
    settled: int = 0
    unsettled: int = 0
    upheld: int = 0
    contradicted: int = 0
    median_latency_days: float | None = None


@dataclass
class PositionsChanged:
    by_world: int = 0                    # mechanical — claim_costs rows
    by_operator: int = 0                 # mixed — dominant provenance human:*
    by_self: int = 0                     # mixed — dominant provenance self
    unattributed: int = 0

    @property
    def total(self) -> int:
        return self.by_world + self.by_operator + self.by_self + self.unattributed


@dataclass
class Consequence:
    window_hours: float
    door: DoorRead
    resolution: ResolutionRead
    positions: PositionsChanged

    @property
    def met(self) -> bool:
        """S1-E. One position changed because the WORLD contradicted it."""
        return self.positions.by_world > 0


def _declines(repo_root: Path, since: float) -> tuple[int | None, str | None]:
    """Declines are invisible in the store by design (INV-046); only the call
    log sees them. Absent, this is unmeasured and says so (INV-044)."""
    path = repo_root / CALL_LOG
    if not path.exists():
        return None, (f"no call log at {path} — declines are not recorded in the "
                      "store by design (INV-046), so without it 'the being "
                      "commits to nothing' and 'the door was never called' are "
                      "the same reading")
    n = 0
    with path.open() as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if (r.get("ts") or 0) < since or r.get("function") != "claim_door":
                continue
            if "<worth_claiming>no" in str(r.get("response") or ""):
                n += 1
    return n, None


def _positions(conn: sqlite3.Connection, since: float) -> PositionsChanged:
    p = PositionsChanged()
    p.by_world = conn.execute(
        "SELECT COUNT(*) FROM claim_costs WHERE ts >= ?", (since,)).fetchone()[0]

    rows = conn.execute(
        "SELECT id FROM perspective_items"
        " WHERE ts >= ? AND (status IN ('revised','released') OR prior_item_id IS NOT NULL)",
        (since,)).fetchall()
    for row in rows:
        inf = what_shaped(conn, row[0])
        if inf is None or not inf.by_provenance:
            p.unattributed += 1
            continue
        if inf.share("human:") > inf.share("self") and inf.share("human:") > inf.share("world:"):
            p.by_operator += 1
        elif inf.share("self") >= inf.share("world:"):
            p.by_self += 1
        else:
            p.unattributed += 1
    return p


def read(conn: sqlite3.Connection, repo_root: Path, *, now: float,
         hours: float = 168.0) -> Consequence:
    since = now - hours * 3600.0

    door = DoorRead()
    door.advances = conn.execute(
        "SELECT COUNT(*) FROM concern_advances WHERE ts >= ?", (since,)).fetchone()[0]
    door.opened = conn.execute(
        "SELECT COUNT(*) FROM resolutions WHERE opened_at >= ?", (since,)).fetchone()[0]
    refusals = conn.execute(
        "SELECT reason FROM claim_refusals WHERE ts >= ?", (since,)).fetchall()
    door.refused = len(refusals)
    for (reason,) in refusals:
        head = re.split(r"[:—-]", reason or "", 1)[0].strip()[:48] or "?"
        door.refusal_reasons[head] = door.refusal_reasons.get(head, 0) + 1
    door.declined, door.unreadable = _declines(repo_root, since)

    res = ResolutionRead()
    res.due = conn.execute(
        "SELECT COUNT(*) FROM resolutions WHERE due_at <= ? AND status='open'",
        (now,)).fetchone()[0]
    settled = conn.execute(
        "SELECT outcome, opened_at, settled_at FROM resolutions"
        " WHERE settled_at IS NOT NULL AND settled_at >= ?", (since,)).fetchall()
    res.settled = len(settled)
    res.unsettled = conn.execute(
        "SELECT COUNT(*) FROM resolutions WHERE status='open'").fetchone()[0]
    lat = []
    for outcome, opened_at, settled_at in settled:
        if (outcome or "").lower().startswith("upheld"):
            res.upheld += 1
        else:
            res.contradicted += 1
        if opened_at and settled_at:
            lat.append((settled_at - opened_at) / DAY)
    res.median_latency_days = statistics.median(lat) if lat else None

    return Consequence(hours, door, res, _positions(conn, since))
