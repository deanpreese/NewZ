"""The reckoning plane: deciding, expecting, being wrong, and changing.

`SPEC.md` section 9.3. The rule that shapes all of it is that **learning from
what happened changes what the system does next, never what the evidence
establishes.** Section 9.1's boundary holds here exactly as it holds for
interest, and the separation harness enumerates this package's write paths for
the same reason it enumerates attention's.
"""

from newz.reckoning.checks import (
    constraints,
    mirroring_report,
    operator_report,
    simpler_explanation_review,
    system_visible_report,
)
from newz.reckoning.consequence import (
    confirm_outcome,
    record_consequence,
    record_surprise,
    surprises,
)
from newz.reckoning.decisions import record_decision, record_expectation
from newz.reckoning.escalation import detect_escalation, open_escalations, record_escalation

__all__ = [
    "confirm_outcome",
    "constraints",
    "detect_escalation",
    "mirroring_report",
    "open_escalations",
    "operator_report",
    "record_consequence",
    "record_decision",
    "record_escalation",
    "record_expectation",
    "record_surprise",
    "simpler_explanation_review",
    "surprises",
    "system_visible_report",
]
