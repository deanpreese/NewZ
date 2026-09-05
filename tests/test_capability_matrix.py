"""Exhaustive allow/deny over the capability matrix.

The matrix is 2,016 cells derived from about ten stated principles, so the tests
here are exhaustive rather than sampled: every cell is decided, every rule
fires, and the cells the specification names by hand are checked by hand.
"""

from __future__ import annotations

import pytest

from newz.domain.enums import (
    COUNTABLE_RELATIONS,
    AssertionKind,
    ClaimKind,
    EdgeRelation,
    RefusalReason,
    SourceRole,
)
from newz.policy import rules
from newz.policy.decisions import BY_ID as DECISIONS
from newz.policy.matrix import MATRIX, all_cells


def test_the_matrix_covers_every_tuple_exactly_once():
    cells = all_cells()
    assert len(cells) == len(set(cells)) == 2016
    assert len(MATRIX) == 2016
    assert len(SourceRole) * len(ClaimKind) * len(AssertionKind) * len(EdgeRelation) == 2016


def test_every_cell_is_decided_by_a_named_rule():
    for entry in MATRIX.entries():
        assert entry.rule_id in rules.BY_ID
        if not entry.admitted:
            assert entry.reason is not None, entry


def test_every_rule_decides_at_least_one_cell():
    """A rule that decides nothing is either dead or wrong, and both are defects."""
    fired = {entry.rule_id for entry in MATRIX.entries()}
    assert fired == {rule.id for rule in rules.RULES}


def test_every_judgment_call_names_its_recorded_decision():
    for rule in rules.RULES:
        if rule.decision_id is not None:
            assert rule.decision_id in DECISIONS
            decision = DECISIONS[rule.decision_id]
            assert decision.reasoning and decision.cost


def test_deny_by_default_is_the_last_word():
    assert rules.RULES[-1].id == "R-13"
    entry = MATRIX.lookup(
        SourceRole.EMPIRICAL_STUDY,
        ClaimKind.ATTRIBUTION,
        AssertionKind.MEASUREMENT,
        EdgeRelation.SUPPORTS,
    )
    assert not entry.admitted
    assert entry.reason is RefusalReason.ROLE_LACKS_CAPABILITY


@pytest.mark.parametrize("relation", [EdgeRelation.CLAIMANT_SAYS, EdgeRelation.CONTEXTUALIZES])
def test_uncountable_relations_are_admitted_everywhere(relation):
    """They establish what a source says and what surrounds it, and count for nothing."""
    for cell in all_cells():
        if cell.relation is relation:
            assert MATRIX.lookup(*cell).admitted, cell


def test_no_countable_edge_reaches_a_normative_proposition():
    for cell in all_cells():
        if cell.claim_kind is ClaimKind.NORMATIVE_PROPOSITION and cell.relation in (
            COUNTABLE_RELATIONS
        ):
            entry = MATRIX.lookup(*cell)
            assert not entry.admitted
            assert entry.reason is RefusalReason.NORMATIVE_ADMITS_NO_EVIDENCE


#: The kinds that could otherwise carry evidence. The other three — inference,
#: prediction, allegation — are refused earlier by a rule that no role escapes,
#: so a test about roles must not assert a reason over them.
EVIDENCE_CAPABLE = (
    AssertionKind.OBSERVATION,
    AssertionKind.TESTIMONY,
    AssertionKind.MEASUREMENT,
    AssertionKind.DOCUMENTED_EVENT,
)


def test_claimant_material_establishes_attribution_and_nothing_else():
    for cell in all_cells():
        if cell.role is not SourceRole.CLAIMANT or cell.relation not in COUNTABLE_RELATIONS:
            continue
        entry = MATRIX.lookup(*cell)
        if cell.claim_kind is ClaimKind.ATTRIBUTION:
            expected = cell.assertion_kind not in (
                AssertionKind.INFERENCE,
                AssertionKind.PREDICTION,
            )
            assert entry.admitted is expected, cell
        else:
            assert not entry.admitted, cell
            if cell.assertion_kind in EVIDENCE_CAPABLE and cell.claim_kind not in (
                ClaimKind.NORMATIVE_PROPOSITION,
                ClaimKind.CAPABILITY_OR_PERFORMANCE,
                ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION,
            ):
                assert entry.reason is RefusalReason.CLAIMANT_ESTABLISHES_ATTRIBUTION_ONLY, cell


def test_a_patent_cannot_support_a_performance_claim():
    """SPEC 7.3 rule 3, generalized by D-003: a performance claim needs a measurement."""
    for kind in AssertionKind:
        for relation in COUNTABLE_RELATIONS:
            entry = MATRIX.lookup(
                SourceRole.PRIMARY_RECORD,
                ClaimKind.CAPABILITY_OR_PERFORMANCE,
                kind,
                relation,
            )
            if kind is AssertionKind.MEASUREMENT:
                assert entry.admitted
            else:
                assert not entry.admitted
                if kind in EVIDENCE_CAPABLE:
                    assert entry.reason is RefusalReason.FILING_IS_NOT_PERFORMANCE, kind


def test_an_allegation_reaches_attribution_and_no_other_claim_kind():
    for cell in all_cells():
        if cell.assertion_kind is not AssertionKind.ALLEGATION:
            continue
        if cell.relation not in COUNTABLE_RELATIONS:
            continue
        entry = MATRIX.lookup(*cell)
        if cell.claim_kind is ClaimKind.ATTRIBUTION:
            assert entry.admitted is (
                cell.role
                in (SourceRole.CLAIMANT, SourceRole.FIRSTHAND_WITNESS)
            ), cell
        else:
            assert not entry.admitted, cell


def test_wrongdoing_claims_admit_only_a_documented_finding_of_record():
    for cell in all_cells():
        if cell.claim_kind is not ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION:
            continue
        if cell.relation not in COUNTABLE_RELATIONS:
            continue
        entry = MATRIX.lookup(*cell)
        allowed = (
            cell.role in rules.DIRECT_RECORD_ROLES
            and cell.assertion_kind is AssertionKind.DOCUMENTED_EVENT
        )
        assert entry.admitted is allowed, cell


def test_testimony_reaches_attribution_and_event_claims_only():
    for cell in all_cells():
        if cell.assertion_kind is not AssertionKind.TESTIMONY:
            continue
        if cell.relation not in COUNTABLE_RELATIONS:
            continue
        entry = MATRIX.lookup(*cell)
        if cell.claim_kind not in (ClaimKind.ATTRIBUTION, ClaimKind.EVENT_OR_OBSERVATION):
            assert not entry.admitted, cell


def test_inference_and_prediction_are_never_countable():
    for cell in all_cells():
        if cell.relation not in COUNTABLE_RELATIONS:
            continue
        if cell.claim_kind is ClaimKind.NORMATIVE_PROPOSITION:
            # Refused one rule earlier, for a reason about the claim rather than
            # the assertion. Still refused, which is what matters here.
            assert not MATRIX.lookup(*cell).admitted
            continue
        if cell.assertion_kind is AssertionKind.INFERENCE:
            assert MATRIX.lookup(*cell).reason is RefusalReason.INFERENCE_IS_NOT_EVIDENCE
        if cell.assertion_kind is AssertionKind.PREDICTION:
            assert MATRIX.lookup(*cell).reason is RefusalReason.PREDICTION_IS_NOT_EVIDENCE


def test_context_roles_carry_no_countable_evidence():
    for cell in all_cells():
        if cell.role not in rules.CONTEXT_ONLY_ROLES:
            continue
        if cell.relation in COUNTABLE_RELATIONS:
            assert not MATRIX.lookup(*cell).admitted, cell
        else:
            assert MATRIX.lookup(*cell).admitted, cell
