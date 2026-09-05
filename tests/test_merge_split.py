"""Claim identity changes are append-only.

Edges address claim identifiers, so a merge or split re-points by emitting new
events. Nothing existing is rewritten, and both preimage histories stay
reachable.
"""

from __future__ import annotations

import pytest

from newz.domain.enums import EdgeRelation
from newz.graph.merge import SplitRefused, merge, split
from tests import builders as b


def _edges():
    claim_a = b.claim(ident="claim:a")
    claim_b = b.claim(ident="claim:b")
    a1 = b.assertion("assertion:a1")
    a2 = b.assertion("assertion:a2")
    return (
        b.edge("edge:e1", a1, claim_a, EdgeRelation.SUPPORTS, "basis:b1"),
        b.edge("edge:e2", a2, claim_b, EdgeRelation.CONTRADICTS, "basis:b2"),
    )


def test_a_merge_names_both_preimages_and_rewrites_neither():
    original = _edges()
    event, moved = merge(
        ["claim:a", "claim:b"], "claim:s", original, "the same proposition", "sup:1"
    )
    assert event.preimage_claim_ids == ("claim:a", "claim:b")
    assert event.successor_claim_ids == ("claim:s",)
    assert [e.claim_id for e in original] == ["claim:a", "claim:b"]
    assert {e.claim_id for e in moved} == {"claim:s"}
    assert len(moved) == 2


def test_a_merge_preserves_every_property_of_the_edge_it_re_points():
    original = _edges()
    _, moved = merge(["claim:a"], "claim:s", original, "reason", "sup:1")
    before, after = original[0], moved[0]
    for field in ("relation", "basis_id", "role", "assertion_kind", "risk", "policy_version"):
        assert getattr(after, field) == getattr(before, field)
    assert after.id != before.id


def test_a_split_must_re_point_every_edge_explicitly():
    original = _edges()
    with pytest.raises(SplitRefused):
        split("claim:a", {}, original, "two propositions", "sup:2")


def test_a_split_re_points_each_edge_to_exactly_one_successor():
    claim = b.claim(ident="claim:a")
    a1 = b.assertion("assertion:a1")
    a2 = b.assertion("assertion:a2")
    original = (
        b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1"),
        b.edge("edge:e2", a2, claim, EdgeRelation.SUPPORTS, "basis:b2"),
    )
    event, moved = split(
        "claim:a",
        {"edge:e1": "claim:s1", "edge:e2": "claim:s2"},
        original,
        "two propositions",
        "sup:2",
    )
    assert event.successor_claim_ids == ("claim:s1", "claim:s2")
    assert {e.id: e.claim_id for e in moved} == {
        "edge:e1+s": "claim:s1",
        "edge:e2+s": "claim:s2",
    }
    assert [e.claim_id for e in original] == ["claim:a", "claim:a"]


def test_a_successor_derives_its_own_assessment_rather_than_inheriting_one():
    """Nothing in a merge carries an assessment: the successor has only edges."""
    _, moved = merge(["claim:a", "claim:b"], "claim:s", _edges(), "reason", "sup:1")
    assert all(not hasattr(e, "state") for e in moved)
