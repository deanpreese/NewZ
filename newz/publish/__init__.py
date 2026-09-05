"""Publication: what clears, where it lands, and how it is taken back.

Two axes that must not be conflated. **Clearance** decides whether a revision
publishes at all and is approve-by-default. **Reach** decides who can see it and
is local-first. A system that publishes freely to its operator and cautiously to
everyone else is the intended posture, not a transitional one.
"""

from newz.publish.appraisal import appraise, review_debt, sample_for_review
from newz.publish.browse import search_claims, search_entities
from newz.publish.clearance import clear, refusal_conditions
from newz.publish.export import export_claims, export_corpus, verify_export
from newz.publish.publication import (
    confirm_publication,
    correct,
    overdue_revocations,
    publish,
    retract,
)
from newz.publish.reader import Reader, ReaderRefused, issue_token
from newz.publish.reports import Cited, Connective, compose

__all__ = [
    "Cited",
    "Connective",
    "Reader",
    "ReaderRefused",
    "appraise",
    "clear",
    "compose",
    "confirm_publication",
    "correct",
    "export_claims",
    "export_corpus",
    "issue_token",
    "overdue_revocations",
    "publish",
    "refusal_conditions",
    "retract",
    "review_debt",
    "sample_for_review",
    "search_claims",
    "search_entities",
    "verify_export",
]
