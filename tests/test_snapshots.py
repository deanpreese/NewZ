"""Canonical serialization, and the committed policy artifacts.

`SPEC.md` section 13 requires an assessment to reproduce exactly given the same
artifacts, policy version, and code version. These tests pin the serialization
that reproducibility is measured in, and check that the committed policy files
still match what the code produces.
"""

from __future__ import annotations

from pathlib import Path

from newz.canonical import digest, dumps
from newz.domain.enums import AssertionKind, ClaimKind, EdgeRelation, RiskTier
from newz.policy import emit
from newz.policy.bundle import BUNDLE
from newz.policy.promotion import assess
from tests import builders as b

ROOT = Path(__file__).resolve().parents[1]


def test_the_committed_capability_matrix_matches_the_code():
    committed = (ROOT / emit.MATRIX_PATH).read_text(encoding="utf-8")
    assert committed == emit.render_matrix()
    assert committed.count("\n") == 2016


def test_the_committed_bundle_matches_the_code():
    committed = (ROOT / emit.BUNDLE_PATH).read_text(encoding="utf-8")
    assert committed == emit.render_bundle()
    assert BUNDLE.digest in committed


def test_canonical_form_does_not_depend_on_insertion_order():
    first = {"b": 1, "a": {"d": 2, "c": [3, 2, 1]}}
    second = {"a": {"c": [3, 2, 1], "d": 2}, "b": 1}
    assert dumps(first) == dumps(second)
    assert digest(first) == digest(second)


def test_canonical_form_of_a_claim_is_stable():
    claim = b.claim(kind=ClaimKind.MEASUREMENT_OR_ASSOCIATION, risk=RiskTier.R1)
    assert dumps(claim) == (
        '{"aliases":[],"id":"claim:c1","kind":"measurement_or_association",'
        '"resolution_horizon":null,"resolver":null,"risk":"R1",'
        '"withdrawn":false,"wording":"a proposition under investigation"}'
    )


def test_canonical_form_of_an_assessment_is_stable():
    claim = b.claim()
    a1 = b.assertion("assertion:a1", AssertionKind.MEASUREMENT)
    result = assess(
        b.inputs(
            claim,
            b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1"),
            assertions={a1.id: a1},
            bases={"basis:b1": b.basis("basis:b1")},
        )
    )
    assert dumps(result) == (
        '{"blocked_lanes":[],"claim_id":"claim:c1","code_version":"0.1.0",'
        '"contradicting_bases":0,"countable_edge_ids":["edge:e1"],'
        '"explanation":"one_independent_basis","policy_version":"1.0.0",'
        '"state":"provisional_support","supporting_bases":1}'
    )


def test_the_policy_digest_moves_when_the_policy_moves():
    before = BUNDLE.digest
    record = BUNDLE.as_record()
    record["thresholds"]["R1"]["independent_bases"] = 3
    assert digest(record) != before
