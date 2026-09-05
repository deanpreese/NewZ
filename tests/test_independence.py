"""Properties of basis counting.

These are exhaustive rather than sampled: the interesting space is subsets of a
small basis set, which is enumerable, and an enumerated proof is worth more than
a generated sample of the same space (ADR-0003).
"""

from __future__ import annotations

from itertools import combinations

import pytest

from newz.domain.enums import AssessmentState, EdgeRelation, IndependenceJustification
from newz.policy.independence import count_independent_bases, justification_holds
from newz.policy.promotion import assess
from tests import builders as b

BASES = {f"basis:b{i}": b.basis(f"basis:b{i}") for i in range(1, 5)}


def _all_pairs_justified(ids):
    return [b.independence(x, y) for x, y in combinations(sorted(ids), 2)]


@pytest.mark.parametrize("size", [1, 2, 3, 4])
def test_fully_justified_sets_count_once_per_basis(size):
    ids = sorted(BASES)[:size]
    count, groups = count_independent_bases(ids, BASES, _all_pairs_justified(ids))
    assert count == size
    assert sum(len(g) for g in groups) == size


@pytest.mark.parametrize("size", [1, 2, 3, 4])
def test_repetition_of_one_basis_never_increases_strength(size):
    """SPEC 7.3 rule 6. The same basis cited many times is one basis."""
    repeated = ["basis:b1"] * size
    count, _ = count_independent_bases(repeated, BASES, [])
    assert count == 1


@pytest.mark.parametrize("size", [2, 3, 4])
def test_unjustified_independence_collapses_the_whole_set(size):
    ids = sorted(BASES)[:size]
    count, groups = count_independent_bases(ids, BASES, [])
    assert count == 1
    assert groups == (tuple(ids),)


def test_collapse_is_transitive():
    """D-011: a chain of partially justified pairs is not a fully distinct set."""
    ids = ["basis:b1", "basis:b2", "basis:b3"]
    count, _ = count_independent_bases(
        ids, BASES, [b.independence("basis:b1", "basis:b2")]
    )
    assert count == 1


def test_counting_does_not_depend_on_input_order():
    ids = sorted(BASES)
    justified = _all_pairs_justified(ids)
    forward = count_independent_bases(ids, BASES, justified)
    backward = count_independent_bases(list(reversed(ids)), BASES, list(reversed(justified)))
    assert forward == backward


def test_unknown_independence_does_not_invalidate_an_edge():
    """It takes away the count, not the evidence."""
    claim = b.claim()
    a1 = b.assertion("assertion:a1")
    a2 = b.assertion("assertion:a2")
    result = assess(
        b.inputs(
            claim,
            b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1"),
            b.edge("edge:e2", a2, claim, EdgeRelation.SUPPORTS, "basis:b2"),
            assertions={a.id: a for a in (a1, a2)},
            bases=BASES,
        )
    )
    assert result.supporting_bases == 1
    assert result.countable_edge_ids == ("edge:e1", "edge:e2")
    assert result.state is AssessmentState.PROVISIONAL_SUPPORT


def test_an_unresolved_basis_is_not_counted_and_its_edge_is_refused():
    unresolved = {"basis:b1": b.basis("basis:b1", resolved=False)}
    claim = b.claim()
    a1 = b.assertion("assertion:a1")
    result = assess(
        b.inputs(
            claim,
            b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1"),
            assertions={a1.id: a1},
            bases=unresolved,
        )
    )
    assert result.supporting_bases == 0
    assert result.countable_edge_ids == ()


def test_shared_independence_group_blocks_every_justification():
    """D-012, including the operator-verified one. Membership never establishes."""
    grouped = {
        "basis:b1": b.basis("basis:b1", group="grp:one"),
        "basis:b2": b.basis("basis:b2", group="grp:one"),
    }
    for justification in IndependenceJustification:
        claim = b.independence(
            "basis:b1",
            "basis:b2",
            justification=justification,
            actor="operator:dean",
            reason="reviewed by hand",
        )
        holds, why = justification_holds(claim, grouped)
        assert not holds
        assert why == "shared_independence_group"


def test_a_mechanical_justification_without_evidence_does_not_hold():
    claim = b.independence("basis:b1", "basis:b2", evidence="")
    holds, why = justification_holds(claim, BASES)
    assert not holds
    assert why == "justification_without_evidence"


def test_an_operator_justification_needs_an_actor_and_a_reason():
    incomplete = b.independence(
        "basis:b1",
        "basis:b2",
        justification=IndependenceJustification.OPERATOR_VERIFIED,
        actor="operator:dean",
        reason=None,
    )
    holds, why = justification_holds(incomplete, BASES)
    assert not holds
    assert why == "operator_action_incomplete"
