"""Proposals in, candidates out.

The model proposes; this package decides what survives. Nothing here trusts the
proposal's prose: a quotation that does not verify byte-exact against a retained
segment is dropped with a reason, and there is no field in the proposal shape
through which a model could grant capability even if it asked.
"""

from newz.extract.proposal import (
    Proposal,
    ProposedAssertion,
    ProposedClaim,
    Refusal,
    ValidatedExtraction,
    parse_proposal,
    validate,
)

__all__ = [
    "Proposal",
    "ProposedAssertion",
    "ProposedClaim",
    "Refusal",
    "ValidatedExtraction",
    "parse_proposal",
    "validate",
]
