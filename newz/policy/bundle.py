"""The versioned policy bundle.

Everything an assessment was derived under, in one hashable object: the
capability matrix, the required evidence lanes, the promotion thresholds, the
independence justifications, and the task-state classification. `SPEC.md`
section 9 item 8 makes a change to any of them a policy version change, which is
why they travel together and are hashed together.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.canonical import digest
from newz.domain.enums import (
    LIVE_TASK_STATES,
    TERMINAL_COMPETENT_STATES,
    TERMINAL_INCOMPLETE_STATES,
    IndependenceJustification,
    RiskTier,
)
from newz.policy import lanes
from newz.policy.decisions import DECISIONS
from newz.policy.matrix import MATRIX, CapabilityMatrix
from newz.policy.rules import DIRECT_RECORD_ROLES, STRONG_PROVENANCE_ROLES
from newz.version import CODE_VERSION, POLICY_VERSION

#: The promotion thresholds, stated as data so a change to them is visibly a
#: policy change rather than an edit to a branch.
THRESHOLDS: dict[str, dict[str, Any]] = {
    RiskTier.R0.value: {
        "independent_bases": 2,
        "strong_provenance_bases": 1,
        "decision": "SPEC 7.3",
    },
    RiskTier.R1.value: {
        "independent_bases": 2,
        "strong_provenance_bases": 1,
        "decision": "SPEC 7.3",
    },
    RiskTier.R2.value: {
        "independent_bases": 2,
        "strong_provenance_bases": 2,
        "decision": "D-009",
    },
    RiskTier.R3.value: {
        "independent_bases": 2,
        "direct_record_bases": 1,
        "decision": "D-010",
    },
    RiskTier.R4.value: {"never_promotes": True, "decision": "D-015"},
}


#: `SPEC.md` section 10. Clearance is what may publish at all; reach is where it
#: lands, and the two are separate axes. R3 is not a default that could be
#: flipped: `TRUE_NORTH.md` forbids autonomously publishing high-risk claims
#: about living people.
PUBLICATION_DISPOSITION: dict[str, str] = {
    RiskTier.R0.value: "publishes_on_checks_and_appraisal",
    RiskTier.R1.value: "publishes_on_checks_and_appraisal",
    RiskTier.R2.value: "publishes_on_checks_and_appraisal_with_evidence_preconditions",
    RiskTier.R3.value: "operator_approval_of_the_exact_revision",
    RiskTier.R4.value: "never",
}


@dataclass(frozen=True, slots=True)
class PolicyBundle:
    version: str
    code_version: str
    matrix: CapabilityMatrix

    def as_record(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "code_version": self.code_version,
            "capability_matrix": self.matrix.as_record(),
            "required_evidence_lanes": lanes.as_record(),
            "thresholds": THRESHOLDS,
            "publication_disposition": PUBLICATION_DISPOSITION,
            "strong_provenance_roles": sorted(r.value for r in STRONG_PROVENANCE_ROLES),
            "direct_record_roles": sorted(r.value for r in DIRECT_RECORD_ROLES),
            "independence_justifications": sorted(j.value for j in IndependenceJustification),
            "task_states": {
                "live": sorted(s.value for s in LIVE_TASK_STATES),
                "terminal_competent": sorted(s.value for s in TERMINAL_COMPETENT_STATES),
                "terminal_incomplete": sorted(s.value for s in TERMINAL_INCOMPLETE_STATES),
            },
            "decisions": [d.as_record() for d in DECISIONS],
        }

    @property
    def digest(self) -> str:
        return digest(self.as_record())


BUNDLE = PolicyBundle(version=POLICY_VERSION, code_version=CODE_VERSION, matrix=MATRIX)
