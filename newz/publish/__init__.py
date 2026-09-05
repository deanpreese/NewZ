"""Publication: what clears, where it lands, and how it is taken back.

Two axes that must not be conflated. **Clearance** decides whether a revision
publishes at all and is approve-by-default. **Reach** decides who can see it and
is local-first. A system that publishes freely to its operator and cautiously to
everyone else is the intended posture, not a transitional one.
"""

from newz.publish.appraisal import appraise, review_debt, sample_for_review
from newz.publish.clearance import clear, refusal_conditions
from newz.publish.publication import (
    confirm_publication,
    correct,
    overdue_revocations,
    publish,
    retract,
)

__all__ = [
    "appraise",
    "clear",
    "confirm_publication",
    "correct",
    "overdue_revocations",
    "publish",
    "refusal_conditions",
    "retract",
    "review_debt",
    "sample_for_review",
]
