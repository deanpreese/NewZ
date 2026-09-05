"""What a policy version change obliges.

`SPEC.md` section 9 item 8: a change to the capability matrix, the promotion
thresholds, the independence justifications, the required evidence lanes, or the
task-state classification is a policy version change. It reassesses every claim
whose current assessment was derived under the superseded version and
invalidates the dependent presentations. Without this a stored assessment
silently reflects a policy that no longer exists.
"""

from __future__ import annotations

from collections.abc import Sequence

from newz.domain.records import Assessment, Presentation


def stale_assessments(
    assessments: Sequence[Assessment], current_policy_version: str
) -> tuple[Assessment, ...]:
    """The assessments derived under a superseded policy version."""
    return tuple(
        a
        for a in sorted(assessments, key=lambda a: a.claim_id)
        if a.policy_version != current_policy_version
    )


def claims_requiring_reassessment(
    assessments: Sequence[Assessment], current_policy_version: str
) -> tuple[str, ...]:
    return tuple(a.claim_id for a in stale_assessments(assessments, current_policy_version))


def invalidate(
    presentations: Sequence[Presentation],
    claim_ids: Sequence[str] = (),
    edge_ids: Sequence[str] = (),
    reason: str = "policy_version_change",
) -> tuple[Presentation, ...]:
    """Return the presentations with every dependent one marked invalid.

    A projection that depends on a reassessed claim or a withdrawn edge is not
    merely out of date; it is uncleared until it is rebuilt.
    """
    claims = set(claim_ids)
    edges = set(edge_ids)
    out: list[Presentation] = []
    for presentation in sorted(presentations, key=lambda p: p.id):
        touched = bool(set(presentation.claim_ids) & claims) or bool(
            set(presentation.edge_ids) & edges
        )
        if touched and presentation.live:
            out.append(
                Presentation(
                    id=presentation.id,
                    kind=presentation.kind,
                    claim_ids=presentation.claim_ids,
                    edge_ids=presentation.edge_ids,
                    policy_version=presentation.policy_version,
                    live=False,
                    invalidation_reason=reason,
                    metadata=dict(presentation.metadata),
                )
            )
        else:
            out.append(presentation)
    return tuple(out)
