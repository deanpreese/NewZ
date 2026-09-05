"""The evidence plane over the store.

The decisions themselves live in `newz.policy` and are pure. This package loads
records, hands them to those functions, and writes down what came back — so the
answer to "why is this claim supported" is a policy version and a row, never a
code path somebody has to re-run in their head.
"""

from newz.evidence.assess import assess_claim, current_assessment
from newz.evidence.bases import (
    correct_basis,
    load_bases,
    record_basis,
    record_derivation,
    record_independence,
)
from newz.evidence.edges import admit_edge, withdraw_edge
from newz.evidence.inspect import explain, trace_claim

__all__ = [
    "admit_edge",
    "assess_claim",
    "correct_basis",
    "current_assessment",
    "explain",
    "load_bases",
    "record_basis",
    "record_derivation",
    "record_independence",
    "trace_claim",
    "withdraw_edge",
]
