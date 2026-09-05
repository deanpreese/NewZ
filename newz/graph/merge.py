"""Claim merge and split.

Edges address claim identifiers, so a merge or split MUST NOT rewrite them.
Both operations emit a supersession event and re-point edges by emitting new
edge events against the successor. Neither preimage is deleted, and no existing
event is touched.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from newz.domain.records import EdgeEvent, SupersessionEvent


class SplitRefused(Exception):
    """Raised when a split would duplicate an edge across successors."""


def _repoint(edge: EdgeEvent, successor_claim_id: str, suffix: str) -> EdgeEvent:
    """A new edge event against the successor. The original remains valid."""
    return EdgeEvent(
        id=f"{edge.id}{suffix}",
        assertion_id=edge.assertion_id,
        claim_id=successor_claim_id,
        relation=edge.relation,
        basis_id=edge.basis_id,
        role=edge.role,
        assertion_kind=edge.assertion_kind,
        risk=edge.risk,
        policy_version=edge.policy_version,
        admitted=edge.admitted,
        live=edge.live,
        refusal_reason=edge.refusal_reason,
        attestations=edge.attestations,
        declared_scope=edge.declared_scope,
        topic=edge.topic,
        adjudicative_scope_covers_claim=edge.adjudicative_scope_covers_claim,
    )


def merge(
    preimage_claim_ids: Sequence[str],
    successor_claim_id: str,
    edges: Sequence[EdgeEvent],
    reason: str,
    event_id: str,
) -> tuple[SupersessionEvent, tuple[EdgeEvent, ...]]:
    """Merge several claims into one successor.

    The successor's assessment is derived afterwards from its re-pointed edges.
    It is never copied from a preimage.
    """
    preimages = tuple(sorted(preimage_claim_ids))
    moved = tuple(
        _repoint(edge, successor_claim_id, "+m")
        for edge in sorted(edges, key=lambda e: e.id)
        if edge.claim_id in set(preimages)
    )
    event = SupersessionEvent(
        id=event_id,
        kind="merge",
        preimage_claim_ids=preimages,
        successor_claim_ids=(successor_claim_id,),
        reason=reason,
    )
    return event, moved


def split(
    preimage_claim_id: str,
    assignment: Mapping[str, str],
    edges: Sequence[EdgeEvent],
    reason: str,
    event_id: str,
) -> tuple[SupersessionEvent, tuple[EdgeEvent, ...]]:
    """Split one claim into several successors.

    `assignment` maps each edge id to exactly one successor claim. An edge sent
    to more than one successor would duplicate a basis across claims, which is
    the mechanism the independence rules exist to prevent, so it is refused
    rather than resolved.
    """
    in_scope = [e for e in sorted(edges, key=lambda e: e.id) if e.claim_id == preimage_claim_id]
    missing = [e.id for e in in_scope if e.id not in assignment]
    if missing:
        raise SplitRefused(f"every edge must be re-pointed explicitly; missing: {sorted(missing)}")

    seen: dict[str, str] = {}
    for edge_id, successor in assignment.items():
        if edge_id in seen and seen[edge_id] != successor:
            raise SplitRefused(f"edge {edge_id} assigned to two successors")
        seen[edge_id] = successor

    moved = tuple(_repoint(edge, assignment[edge.id], "+s") for edge in in_scope)
    successors = tuple(sorted({assignment[e.id] for e in in_scope}))
    event = SupersessionEvent(
        id=event_id,
        kind="split",
        preimage_claim_ids=(preimage_claim_id,),
        successor_claim_ids=successors,
        reason=reason,
    )
    return event, moved
