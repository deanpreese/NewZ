"""Which evidence lanes each claim kind requires.

The set of lanes is closed by `SPEC.md` section 7.3. This mapping is the policy
decision over it (D-014), versioned with the rest of the bundle: `indeterminate`
means every lane below reached a terminal-competent state without producing a
countable edge, so the mapping decides what that result asserts.
"""

from __future__ import annotations

from typing import Any

from newz.domain.enums import ClaimKind, EvidenceLane

L = EvidenceLane

REQUIRED_LANES: dict[ClaimKind, frozenset[EvidenceLane]] = {
    # The origin artifact settles it, and nothing else bears on it.
    ClaimKind.ATTRIBUTION: frozenset({L.CLAIMANT_ORIGIN}),
    # The record either exists or it does not.
    ClaimKind.DOCUMENT_EXISTENCE: frozenset({L.PRIMARY_RECORD}),
    ClaimKind.EVENT_OR_OBSERVATION: frozenset(
        {L.CLAIMANT_ORIGIN, L.PRIMARY_RECORD, L.INDEPENDENT_COUNTERPART, L.SKEPTICAL_ANALYSIS}
    ),
    ClaimKind.MEASUREMENT_OR_ASSOCIATION: frozenset(
        {L.PRIMARY_RECORD, L.EMPIRICAL, L.INDEPENDENT_COUNTERPART, L.SKEPTICAL_ANALYSIS}
    ),
    ClaimKind.CAUSAL_OR_MECHANISTIC: frozenset(
        {L.EMPIRICAL, L.INDEPENDENT_COUNTERPART, L.SKEPTICAL_ANALYSIS}
    ),
    ClaimKind.CAPABILITY_OR_PERFORMANCE: frozenset(
        {L.PRIMARY_RECORD, L.EMPIRICAL, L.INDEPENDENT_COUNTERPART, L.SKEPTICAL_ANALYSIS}
    ),
    ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION: frozenset(
        {L.CLAIMANT_ORIGIN, L.PRIMARY_RECORD, L.RESOLVER}
    ),
    ClaimKind.FORECAST: frozenset({L.RESOLVER}),
    # It never promotes, so no lane's silence says anything about it.
    ClaimKind.NORMATIVE_PROPOSITION: frozenset(),
}


def required(claim_kind: ClaimKind) -> frozenset[EvidenceLane]:
    return REQUIRED_LANES[claim_kind]


def as_record() -> dict[str, Any]:
    return {
        kind.value: sorted(lane.value for lane in REQUIRED_LANES[kind]) for kind in ClaimKind
    }
