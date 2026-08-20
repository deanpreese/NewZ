"""What a measurement is allowed to do (P4 epic E3.8, Rule 7).

Rule 7 says every measurement carries its grade. This says what a grade
*permits*, which is the half that does any work:

  **may halt** — every metric, whatever its grade. Halting is stopping to look,
  and a figure that is merely suspect is reason enough to stop. Requiring
  certainty before halting would mean the weakest signals — precisely the ones
  §10 names — could never raise an alarm.

  **may justify** — mechanical only. Justifying is acting on a number: opening a
  plan change, closing an epic, widening the loop's autonomy. A model-graded
  figure cannot do that, because drift in the model's judging would be
  indistinguishable from change in the world (§12.6, Rule 4).

**The asymmetry is the design.** Cheap to stop, expensive to act. It is what
lets `operator_disagreement_rate` exist at all: a metric about whether the being
defers to the operator, judged by a model the operator configures, is exactly
the kind of number that must be able to raise an alarm and must never be able
to settle one.
"""

from __future__ import annotations

from newz.evidence.grades import grade_of

JUSTIFYING_GRADES = ("mechanical",)


class MayNotJustify(PermissionError):
    """Something tried to act on a figure that may only raise a question."""


def may_halt(metric: str) -> bool:
    """Any graded metric may stop the loop to look. Ungraded ones raise."""
    grade_of(metric)          # unregistered metrics cannot be cited at all
    return True


def may_justify(metric: str) -> bool:
    """Only a mechanical metric may carry a decision."""
    return grade_of(metric) in JUSTIFYING_GRADES


def justify(metric: str, what: str) -> str:
    """Use a metric as the reason for an action, or refuse and say why."""
    if not may_justify(metric):
        raise MayNotJustify(
            f"{metric!r} is {grade_of(metric)} and cannot justify {what}. It may "
            "halt — stopping to look costs a look — but acting on it would let "
            "drift in a model's judging pass as change in the world (Rule 4, "
            "§12.6). Find a mechanical premise that moved, or halt and ask.")
    return metric
