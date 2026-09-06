"""Growing the catalogue without losing what the twenty slots were for.

`PLAN.md` Phase 6 item 1: expand the low-risk catalogue while maintaining
topic and role coverage and concentration alerts. The prescription machinery
already derives a slate of any size from the specification's two tables, so the
arithmetic is not the problem. What this module exists for is the two ways a
larger catalogue is worse than a smaller one, both of which are invisible while
every individual addition looks reasonable.

**A larger slate can be less symmetrical than a small one.** A topic that holds
three or more slots is being read seriously enough that `TRUE_NORTH.md`'s
symmetry applies: support and refutation face the same burden, so it needs a
source that can contradict it. Section 5.1 gives skeptical and forensic work 15%
of the slate. At twenty, three topics clear the threshold and three skeptical
slots exist, and every one of them is served. At thirty, all eight topics clear
the threshold and there are four skeptical slots: half the topics carry claims
nothing in the diet can contradict. The slate does not recover until 52.

That is a property of the specification's own numbers rather than a bug in the
solver, and `_ideal` in `prescription.py` proves it: the ceiling itself drops.
An operator growing 20 to 30 would be adding ten reviewed sources and halving
the diet's capacity to refute anything.

**A catalogue can make its own read cap unsatisfiable.** Section 5.1 caps a
publisher at 20% of retained reads in Pilot and 10% in Production. A publisher
holding more than that share of the *slots* cannot be read in proportion to its
place in the diet without breaching the cap — so either the cap refuses reads
the diet asked for, or the diet is quietly not what it says. Both are worth
knowing before the sources are enabled rather than after.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from newz.control.concentration import CAPS, cap_for
from newz.pilot.modes import DeploymentMode
from newz.pilot.prescription import (
    CONTESTED_THRESHOLD,
    SKEPTICAL,
    SLATE_SIZE,
    SlotSpec,
    bucket_allocation,
    prescribe,
    prescription_report,
    topic_allocation,
)

#: How far out to look for a size that restores symmetry. Well past any
#: catalogue this system is going to read on one machine.
SEARCH_LIMIT = 200

#: The size the operator chose on 2026-09-05, to be reached at Phase 6 and not
#: before. It is the smallest slate above the pilot at which every topic the
#: diet reads seriously can still be contradicted — 20 and 51 are the only two
#: sizes up to 50 that hold, and the ones between trade refutability for reach.
TARGET_SIZE = 51


@dataclass(frozen=True, slots=True)
class Symmetry:
    """Whether a slate of this size can contradict what it takes seriously."""

    size: int
    contested: tuple[str, ...]
    skeptical_slots: int
    served: int

    @property
    def whole(self) -> bool:
        return self.served >= len(self.contested)

    @property
    def unserved(self) -> int:
        return max(0, len(self.contested) - self.served)

    def detail(self) -> str:
        if self.whole:
            return (
                f"{len(self.contested)} topic(s) at or above {CONTESTED_THRESHOLD} slots, "
                f"{self.skeptical_slots} skeptical slot(s): every one can be contradicted"
            )
        return (
            f"{self.unserved} of {len(self.contested)} topics hold {CONTESTED_THRESHOLD} or "
            f"more slots with only {self.skeptical_slots} skeptical slot(s) to go round: "
            "claims nothing in the diet can contradict"
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "contested": list(self.contested),
            "skeptical_slots": self.skeptical_slots,
            "served": self.served,
            "whole": self.whole,
            "detail": self.detail(),
        }


def symmetry(size: int) -> Symmetry:
    """Whether every topic the slate takes seriously can be contradicted."""
    allocation, _ = topic_allocation(size)
    slots, _ = bucket_allocation(size)
    contested = tuple(
        topic
        for topic, count in sorted(allocation.items())
        if count >= CONTESTED_THRESHOLD
    )
    skeptical = slots.get(SKEPTICAL, 0)
    return Symmetry(
        size=size,
        contested=contested,
        skeptical_slots=skeptical,
        served=min(len(contested), skeptical),
    )


def symmetrical_sizes(start: int = SLATE_SIZE, limit: int = SEARCH_LIMIT) -> tuple[int, ...]:
    """Every slate size from `start` up that keeps the diet able to refute."""
    return tuple(size for size in range(start, limit + 1) if symmetry(size).whole)


def nearest_symmetrical(size: int, limit: int = SEARCH_LIMIT) -> tuple[int | None, int | None]:
    """The nearest sizes below and above that do not lose symmetry."""
    below = [n for n in range(SLATE_SIZE, size) if symmetry(n).whole]
    above = [n for n in range(size + 1, limit + 1) if symmetry(n).whole]
    return (below[-1] if below else None, above[0] if above else None)


# ---------------------------------------------------------------------------
# Publisher concentration in the catalogue itself
# ---------------------------------------------------------------------------


def cap_conflicts(
    publishers_by_slot: dict[int, str], size: int, mode: DeploymentMode
) -> tuple[str, ...]:
    """Publishers whose share of the slate its own read cap cannot accommodate.

    The cap governs reads, not slots, so this refuses nothing. It reports the
    contradiction: a publisher holding a quarter of a slate that may not exceed
    a tenth of the reads is a diet that cannot be read as written.
    """
    cap = cap_for(mode)
    if cap is None or not size:
        return ()
    held: dict[str, int] = {}
    for publisher in publishers_by_slot.values():
        held[publisher] = held.get(publisher, 0) + 1
    return tuple(
        f"{publisher} holds {count} of {size} slots ({count / size:.0%}), past the "
        f"{cap:.0%} read cap in {mode.value}: reading the diet in proportion breaches it"
        for publisher, count in sorted(held.items())
        if count / size > cap
    )


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExpansionPlan:
    """What growing to this size asks for, and what it costs."""

    size: int
    from_size: int
    added: tuple[SlotSpec, ...]
    symmetry: Symmetry
    findings: tuple[str, ...] = field(default_factory=tuple)
    proven_optimal: bool = False

    @property
    def safe(self) -> bool:
        return not self.findings

    def as_record(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "from_size": self.from_size,
            "added": [spec.as_record() for spec in self.added],
            "symmetry": self.symmetry.as_record(),
            "findings": list(self.findings),
            "proven_optimal": self.proven_optimal,
            "safe": self.safe,
        }


def plan(
    size: int,
    from_size: int = SLATE_SIZE,
    pins: frozenset[tuple[str, str]] = frozenset(),
    publishers_by_slot: dict[int, str] | None = None,
    mode: DeploymentMode = DeploymentMode.PRODUCTION,
) -> ExpansionPlan:
    """What to add to reach `size`, with what it costs stated rather than implied.

    It does not refuse. Enabling a source is a diet decision and the operator's,
    and a plan that declined to describe an expansion would only mean the
    expansion happened somewhere this could not see it. What it will not do is
    hand over a larger slate without saying that the larger slate can refute
    less than the one it replaces.
    """
    if size < from_size:
        raise ValueError(f"expansion grows a slate: {size} is smaller than {from_size}")

    report = prescription_report(size, pins)
    target = prescribe(size, pins)
    added = tuple(
        SlotSpec(
            index=spec.index,
            bucket=spec.bucket,
            topic=spec.topic,
            rationale=spec.rationale,
        )
        for spec in target[from_size:]
    )

    findings: list[str] = []
    if mode is not DeploymentMode.PRODUCTION and size > SLATE_SIZE:
        # Not a refusal. Expansion is a Phase 6 deliverable and the pilot is
        # specified at twenty slots, so growing before Gate 5 would replace the
        # thing the gate is counting rather than build on it.
        findings.append(
            f"the mode is {mode.value}: SPEC 5.2 specifies a twenty-slot pilot and "
            "Gate 5 counts routes exercised over it, so a slate of "
            f"{size} replaces what the gate measures rather than growing it"
        )
    grown = symmetry(size)
    current = symmetry(from_size)
    if not grown.whole:
        below, above = nearest_symmetrical(size)
        findings.append(
            f"symmetry: {grown.detail()}"
            + (
                f" — the slate of {from_size} it replaces served all of its own"
                if current.whole
                else ""
            )
            + f". The nearest sizes that keep it whole are {below} and {above}."
        )
    if publishers_by_slot:
        findings.extend(cap_conflicts(publishers_by_slot, size, mode))

    return ExpansionPlan(
        size=size,
        from_size=from_size,
        added=added,
        symmetry=grown,
        findings=tuple(findings),
        proven_optimal=report["proven_optimal"],
    )


def survey(sizes: tuple[int, ...] = ()) -> dict[str, Any]:
    """What each candidate size costs, for an operator choosing one."""
    sizes = sizes or tuple(range(SLATE_SIZE, 61, 2))
    return {
        "contested_threshold": CONTESTED_THRESHOLD,
        "caps": {mode.value: cap for mode, cap in sorted(CAPS.items())},
        "sizes": [symmetry(size).as_record() for size in sizes],
        "symmetrical": list(symmetrical_sizes(SLATE_SIZE, max(sizes))),
    }
