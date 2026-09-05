"""Local-day accounting and the protected lane reserves.

`SPEC.md` section 5.2. Ten retained full reads per local day, split three
discovery, five verification, two correction, and the split is a policy rather
than a preference: discovery opens claims faster than verification closes them,
so a discovery-heavy budget accumulates unresolved claims instead of settling
them.

Borrowing runs one way. Unused correction capacity may serve verification within
the same local day; verification never returns capacity to discovery, and
discovery never touches the protected reserve. The asymmetry is the point — a
budget that lends in both directions is one number wearing three names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.domain.enums import ReadLane


@dataclass(frozen=True, slots=True)
class DailyBudget:
    discovery: int = 3
    verification: int = 5
    correction: int = 2

    @property
    def total(self) -> int:
        return self.discovery + self.verification + self.correction

    def of(self, lane: ReadLane) -> int:
        return {
            ReadLane.DISCOVERY: self.discovery,
            ReadLane.VERIFICATION: self.verification,
            ReadLane.CORRECTION: self.correction,
        }[lane]

    def problems(self) -> list[str]:
        out = []
        for name in ("discovery", "verification", "correction"):
            if getattr(self, name) < 0:
                out.append(f"{name} capacity cannot be negative")
        if self.verification < self.discovery:
            out.append(
                "verification capacity below discovery inverts the rule that closing "
                "claims outpaces opening them"
            )
        return out

    def as_record(self) -> dict[str, Any]:
        return {
            "discovery": self.discovery,
            "verification": self.verification,
            "correction": self.correction,
        }


#: `SPEC.md` section 13. Ceilings, not targets.
MONTHLY_REQUEST_CEILING = 1_500
MONTHLY_STORAGE_CEILING_BYTES = 20 * 1024**3


@dataclass(frozen=True, slots=True)
class LaneAvailability:
    lane: ReadLane
    own_remaining: int
    borrowable: int
    borrowed_from: ReadLane | None

    @property
    def available(self) -> bool:
        return self.own_remaining > 0 or self.borrowable > 0


def availability(
    lane: ReadLane, used: dict[ReadLane, int], budget: DailyBudget
) -> LaneAvailability:
    """What this lane may take right now, and from where.

    The only permitted borrow is correction to verification. It is written as a
    single named case rather than a general rule, so that adding a second one has
    to be a decision somebody makes on purpose.
    """
    own = budget.of(lane) - used.get(lane, 0)
    borrowable = 0
    borrowed_from: ReadLane | None = None

    if lane is ReadLane.VERIFICATION and own <= 0:
        spare = budget.correction - used.get(ReadLane.CORRECTION, 0)
        if spare > 0:
            borrowable = spare
            borrowed_from = ReadLane.CORRECTION

    return LaneAvailability(
        lane=lane,
        own_remaining=max(own, 0),
        borrowable=borrowable,
        borrowed_from=borrowed_from,
    )
