"""The risk classifier.

The effective risk is the maximum of source, claim, named-entity, domain, and
intended-output risk. Missing or unreadable state behaves as R3 and blocks
publication. A model may raise risk; lowering it requires a reasoned operator
action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.domain.enums import RISK_ORDER, RiskTier
from newz.domain.records import OperatorAction

_RANK: dict[RiskTier, int] = {tier: i for i, tier in enumerate(RISK_ORDER)}


def rank(tier: RiskTier) -> int:
    return _RANK[tier]


def maximum(*tiers: RiskTier) -> RiskTier:
    return max(tiers, key=rank)


@dataclass(frozen=True, slots=True)
class RiskInputs:
    source: RiskTier | None = None
    claim: RiskTier | None = None
    named_entity: RiskTier | None = None
    domain: RiskTier | None = None
    intended_output: RiskTier | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "claim": self.claim,
            "named_entity": self.named_entity,
            "domain": self.domain,
            "intended_output": self.intended_output,
        }


@dataclass(frozen=True, slots=True)
class RiskResult:
    effective: RiskTier
    publication_blocked: bool
    missing_inputs: tuple[str, ...]
    reason: str

    def as_record(self) -> dict[str, Any]:
        return {
            "effective": self.effective,
            "publication_blocked": self.publication_blocked,
            "missing_inputs": list(self.missing_inputs),
            "reason": self.reason,
        }


def classify(inputs: RiskInputs) -> RiskResult:
    """Fail closed: an unreadable input is R3 and blocks publication."""
    present: list[RiskTier] = []
    missing: list[str] = []
    for name in ("source", "claim", "named_entity", "domain", "intended_output"):
        value = getattr(inputs, name)
        if value is None:
            missing.append(name)
        else:
            present.append(value)

    if missing:
        effective = maximum(RiskTier.R3, *present) if present else RiskTier.R3
        return RiskResult(
            effective=effective,
            publication_blocked=True,
            missing_inputs=tuple(sorted(missing)),
            reason="missing_risk_state_behaves_as_r3",
        )

    effective = maximum(*present)
    return RiskResult(
        effective=effective,
        publication_blocked=effective is RiskTier.R4,
        missing_inputs=(),
        reason="maximum_of_inputs",
    )


class RiskLoweringRefused(Exception):
    """Raised when an automated path tries to lower an effective risk."""


def revise(
    current: RiskTier,
    proposed: RiskTier,
    operator_action: OperatorAction | None = None,
) -> RiskTier:
    """Risk is monotonic within an automated operation.

    A raise is always permitted. A lowering requires a reasoned operator action;
    without one it raises, and the attempt is an escalation event for the caller
    to record under `SPEC.md` section 8.
    """
    if rank(proposed) >= rank(current):
        return proposed
    if operator_action is None or not operator_action.reason:
        raise RiskLoweringRefused(
            f"lowering {current.value} to {proposed.value} requires a reasoned operator action"
        )
    return proposed
