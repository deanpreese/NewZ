"""Basis identity and basis independence, kept apart.

Identity is a property of one edge: the upstream origin it rests on is nameable
and stable. Independence is a pairwise property between two already-resolved
bases, consulted only when counting toward a threshold. Conflating them is how
ten publications of one witness become ten bases.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from newz.domain.enums import IndependenceJustification
from newz.domain.records import Basis, IndependenceClaim


def justification_holds(
    claim: IndependenceClaim, bases: dict[str, Basis]
) -> tuple[bool, str]:
    """Whether one recorded justification actually establishes distinctness."""
    a = bases.get(claim.basis_a)
    b = bases.get(claim.basis_b)
    if a is None or b is None:
        return False, "unknown_basis"
    if not (a.resolved and b.resolved):
        return False, "unresolved_basis"
    # D-012: independence-group membership blocks independence and never
    # establishes it, and it outranks any recorded justification.
    if (
        a.independence_group is not None
        and a.independence_group == b.independence_group
    ):
        return False, "shared_independence_group"
    if claim.justification is IndependenceJustification.OPERATOR_VERIFIED:
        if not (claim.operator_actor and claim.operator_reason):
            return False, "operator_action_incomplete"
        return True, "operator_verified"
    if not claim.evidence:
        return False, "justification_without_evidence"
    return True, claim.justification.value


def count_independent_bases(
    basis_ids: Iterable[str],
    bases: dict[str, Basis],
    independence: Sequence[IndependenceClaim],
) -> tuple[int, tuple[tuple[str, ...], ...]]:
    """Group bases for counting and return the group count and the groups.

    Two bases count separately only under a justification that holds. Unknown or
    unjustified independence collapses them (D-011), and the collapse is
    transitive, so a chain of partially-justified pairs cannot be counted as
    fully distinct.
    """
    ids = sorted({b for b in basis_ids if b in bases and bases[b].resolved})
    if not ids:
        return 0, ()

    justified: set[frozenset[str]] = set()
    for claim in independence:
        holds, _ = justification_holds(claim, bases)
        if holds:
            justified.add(frozenset({claim.basis_a, claim.basis_b}))

    parent = {b: b for b in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            # Sorted so the representative does not depend on input order.
            lo, hi = sorted((rx, ry))
            parent[hi] = lo

    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if frozenset({a, b}) not in justified:
                union(a, b)

    groups: dict[str, list[str]] = {}
    for b in ids:
        groups.setdefault(find(b), []).append(b)
    ordered = tuple(tuple(sorted(members)) for members in groups.values())
    return len(ordered), tuple(sorted(ordered))
