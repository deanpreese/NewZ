"""Projections: what the record looks like to somebody reading it.

Everything here is derived. A card is a view of the graph at a moment, and the
graph is the thing that is true; when they disagree the card is stale and the
validator says so rather than the card being believed.
"""

from newz.present.cards import build_card, claim_card, render_card
from newz.present.dependencies import invalidate_dependents, validate_dependencies
from newz.present.entities import entity_card

__all__ = [
    "build_card",
    "claim_card",
    "entity_card",
    "invalidate_dependents",
    "render_card",
    "validate_dependencies",
]
