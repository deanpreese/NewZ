"""The pilot: running against live material without opening distribution.

Phase 5 is the first phase whose gate this codebase cannot pass on its own.
Gate 5 wants thirty eligible local dates, a hundred distinct retained full
reads, twenty live routes, live claims reaching three different states, one
live correction after presentation, and the operator's approval. What is here
is the machinery that makes those countable and the violations that stop the
count — not the count itself.
"""

from newz.pilot.catalog_review import ProposedSlot, review
from newz.pilot.modes import (
    DeploymentMode,
    current_mode,
    enter_lockdown,
    transition,
)
from newz.pilot.reports import daily_report, funnel
from newz.pilot.shadow import exit_criteria, shadow_assess
from newz.pilot.slots import Candidate, add_candidates, solve, survey
from newz.pilot.violations import (
    PAUSE_CONDITIONS,
    eligible_dates,
    open_violations,
    record_violation,
    resolve_violation,
)

__all__ = [
    "PAUSE_CONDITIONS",
    "Candidate",
    "DeploymentMode",
    "ProposedSlot",
    "add_candidates",
    "current_mode",
    "daily_report",
    "eligible_dates",
    "enter_lockdown",
    "exit_criteria",
    "funnel",
    "open_violations",
    "record_violation",
    "resolve_violation",
    "review",
    "shadow_assess",
    "solve",
    "survey",
    "transition",
]
