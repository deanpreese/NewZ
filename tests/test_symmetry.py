"""Support and refutation face the same burden.

`SPEC.md` 7.3 rule 7. The test is exhaustive over the matrix and then over the
thresholds, because symmetry is the kind of property that survives review and
dies in a special case.
"""

from __future__ import annotations

from newz.domain.enums import AssessmentState, ClaimKind, EdgeRelation, RiskTier
from newz.policy.matrix import MATRIX, all_cells
from newz.policy.promotion import assess
from tests import builders as b


def test_the_matrix_treats_supports_and_contradicts_identically():
    for cell in all_cells():
        if cell.relation is not EdgeRelation.SUPPORTS:
            continue
        supporting = MATRIX.lookup(*cell)
        contradicting = MATRIX.lookup(
            cell.role, cell.claim_kind, cell.assertion_kind, EdgeRelation.CONTRADICTS
        )
        assert supporting.admitted == contradicting.admitted, cell
        assert supporting.reason == contradicting.reason, cell


def _two_bases(relation: EdgeRelation, risk: RiskTier):
    claim = b.claim(risk=risk)
    a1 = b.assertion("assertion:a1")
    a2 = b.assertion("assertion:a2")
    return b.inputs(
        claim,
        b.edge("edge:e1", a1, claim, relation, "basis:b1", risk=risk),
        b.edge("edge:e2", a2, claim, relation, "basis:b2", risk=risk),
        assertions={a.id: a for a in (a1, a2)},
        bases={"basis:b1": b.basis("basis:b1"), "basis:b2": b.basis("basis:b2")},
        independence=[b.independence("basis:b1", "basis:b2")],
    )


def test_the_same_evidence_promotes_in_either_direction():
    supported = assess(_two_bases(EdgeRelation.SUPPORTS, RiskTier.R1))
    refuted = assess(_two_bases(EdgeRelation.CONTRADICTS, RiskTier.R1))
    assert supported.state is AssessmentState.SUPPORTED
    assert refuted.state is AssessmentState.REFUTED
    assert supported.explanation == refuted.explanation
    assert supported.supporting_bases == refuted.contradicting_bases == 2


def test_the_same_shortfall_holds_in_either_direction():
    """R2 needs two strong-provenance bases (D-009); one is not enough, either way."""
    for relation, expected in (
        (EdgeRelation.SUPPORTS, AssessmentState.PROVISIONAL_SUPPORT),
        (EdgeRelation.CONTRADICTS, AssessmentState.PROVISIONAL_CONTRADICTION),
    ):
        claim = b.claim(risk=RiskTier.R2)
        strong = b.assertion("assertion:a1")
        weak = b.assertion(
            "assertion:a2",
            kind=b.AssertionKind.OBSERVATION,
            role=b.SourceRole.SKEPTICAL_INVESTIGATION,
        )
        result = assess(
            b.inputs(
                claim,
                b.edge("edge:e1", strong, claim, relation, "basis:b1", risk=RiskTier.R2),
                b.edge("edge:e2", weak, claim, relation, "basis:b2", risk=RiskTier.R2),
                assertions={a.id: a for a in (strong, weak)},
                bases={"basis:b1": b.basis("basis:b1"), "basis:b2": b.basis("basis:b2")},
                independence=[b.independence("basis:b1", "basis:b2")],
            )
        )
        assert result.state is expected
        assert "r2_needs_two_strong_provenance_bases" in result.explanation


def test_the_single_record_exception_survives_at_r2_and_r3_in_both_directions():
    """It is the only route by which a false allegation reaches `refuted`."""
    for risk in (RiskTier.R2, RiskTier.R3):
        for relation, expected in (
            (EdgeRelation.SUPPORTS, AssessmentState.SUPPORTED),
            (EdgeRelation.CONTRADICTS, AssessmentState.REFUTED),
        ):
            claim = b.claim(kind=ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION, risk=risk)
            finding = b.assertion(
                "assertion:a1",
                kind=b.AssertionKind.DOCUMENTED_EVENT,
                role=b.SourceRole.ADJUDICATOR,
            )
            result = assess(
                b.inputs(
                    claim,
                    b.edge(
                        "edge:e1",
                        finding,
                        claim,
                        relation,
                        "basis:b1",
                        risk=risk,
                        scope_covers=True,
                    ),
                    assertions={finding.id: finding},
                    bases={"basis:b1": b.basis("basis:b1")},
                )
            )
            assert result.state is expected, (risk, relation)
            assert "single_record_exception" in result.explanation


def test_an_adjudicative_record_outside_its_scope_settles_nothing():
    claim = b.claim(kind=ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION, risk=RiskTier.R3)
    finding = b.assertion(
        "assertion:a1",
        kind=b.AssertionKind.DOCUMENTED_EVENT,
        role=b.SourceRole.ADJUDICATOR,
    )
    result = assess(
        b.inputs(
            claim,
            b.edge(
                "edge:e1",
                finding,
                claim,
                EdgeRelation.CONTRADICTS,
                "basis:b1",
                risk=RiskTier.R3,
                scope_covers=None,
            ),
            assertions={finding.id: finding},
            bases={"basis:b1": b.basis("basis:b1")},
        )
    )
    assert result.state is AssessmentState.PROVISIONAL_CONTRADICTION
