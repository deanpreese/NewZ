"""The concern — the unit of pursuit (S2 §8).

Kept from v1 with its shape intact, because the shape is what made pursuit,
attention, and development checkable: a pursuable question with a mandatory
closing condition, carrying its own history of advances and setbacks.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

ACTIVE_STATUSES = ("open",)
# v1's limits, paid for: a concern that keeps failing eventually gets let go,
# and abandonment is a real loss rather than tidy-up.
STALL_LIMIT = 5
BLOCKED_LIMIT = 8


@dataclass
class Concern:
    id: int | None
    statement: str
    why_open: str
    closing_condition: str
    kind: str = "inquiry"          # inquiry | watch | tension
    status: str = "open"           # open | stalled | closed | abandoned
    salience: float = 0.5
    origin: str = "curiosity"      # curiosity | research | conversation
    origin_ref: str | None = None
    opened_at: float = 0.0
    last_advanced_at: float | None = None
    last_attempted_at: float | None = None
    advance_count: int = 0
    stall_count: int = 0
    blocked_count: int = 0
    closed_at: float | None = None
    resolution: str | None = None
    opening_evidence: str | None = None
    opening_citations: list[str] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    def hours_since_touched(self, now: float) -> float:
        """Hours since it last MOVED — not since it was last thought about.

        v1's lesson: keying this on attention lets a concern circled ten
        times without progress look fresh.
        """
        ref = self.last_advanced_at or self.opened_at or now
        return max(0.0, (now - ref) / 3600.0)

    def hours_since_attempted(self, now: float) -> float:
        if not self.last_attempted_at:
            return float("inf")
        return max(0.0, (now - self.last_attempted_at) / 3600.0)

    def render_for_prompt(self) -> str:
        return (
            f"[{self.kind}] {self.statement} "
            f"(closes when: {self.closing_condition}; "
            f"{self.advance_count} advances, {self.stall_count} stalls)"
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Concern":
        try:
            cites = json.loads(row["opening_citations_json"] or "[]")
        except (json.JSONDecodeError, IndexError, KeyError):
            cites = []
        return cls(
            id=row["id"], statement=row["statement"], why_open=row["why_open"],
            closing_condition=row["closing_condition"], kind=row["kind"],
            status=row["status"], salience=row["salience"], origin=row["origin"],
            origin_ref=row["origin_ref"], opened_at=row["opened_at"],
            last_advanced_at=row["last_advanced_at"],
            last_attempted_at=row["last_attempted_at"],
            advance_count=row["advance_count"], stall_count=row["stall_count"],
            blocked_count=row["blocked_count"], closed_at=row["closed_at"],
            resolution=row["resolution"],
            opening_evidence=row["opening_evidence"],
            opening_citations=cites,
        )
