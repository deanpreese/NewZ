"""Risk: the maximum, the fail-closed default, and monotonicity."""

from __future__ import annotations

from itertools import product

import pytest

from newz.domain.enums import RISK_ORDER, RiskTier
from newz.domain.records import OperatorAction
from newz.policy.bundle import PUBLICATION_DISPOSITION
from newz.policy.risk import RiskInputs, RiskLoweringRefused, classify, revise


def test_effective_risk_is_the_maximum_of_its_inputs():
    for combo in product(RISK_ORDER, repeat=2):
        result = classify(
            RiskInputs(
                source=combo[0],
                claim=combo[1],
                named_entity=RiskTier.R0,
                domain=RiskTier.R0,
                intended_output=RiskTier.R0,
            )
        )
        assert result.effective == max(combo, key=RISK_ORDER.index)


@pytest.mark.parametrize(
    "field", ["source", "claim", "named_entity", "domain", "intended_output"]
)
def test_missing_state_behaves_as_r3_and_blocks_publication(field):
    values = dict.fromkeys(
        ["source", "claim", "named_entity", "domain", "intended_output"], RiskTier.R0
    )
    values[field] = None
    result = classify(RiskInputs(**values))
    assert result.effective is RiskTier.R3
    assert result.publication_blocked
    assert result.missing_inputs == (field,)


def test_missing_state_never_lowers_a_higher_known_risk():
    result = classify(RiskInputs(source=RiskTier.R4, claim=None))
    assert result.effective is RiskTier.R4
    assert result.publication_blocked


def test_risk_may_be_raised_by_anything():
    for current, proposed in product(RISK_ORDER, repeat=2):
        if RISK_ORDER.index(proposed) >= RISK_ORDER.index(current):
            assert revise(current, proposed) is proposed


def test_lowering_risk_without_an_operator_action_is_refused():
    for current, proposed in product(RISK_ORDER, repeat=2):
        if RISK_ORDER.index(proposed) < RISK_ORDER.index(current):
            with pytest.raises(RiskLoweringRefused):
                revise(current, proposed)


def test_lowering_risk_requires_a_reason_not_merely_an_actor():
    action = OperatorAction(
        id="action:1",
        actor="operator:dean",
        at="2026-09-05T09:00:00Z",
        action="reclassify",
        reason="",
        target_preimage="R3",
        result="R1",
    )
    with pytest.raises(RiskLoweringRefused):
        revise(RiskTier.R3, RiskTier.R1, action)
    reasoned = OperatorAction(
        id="action:2",
        actor="operator:dean",
        at="2026-09-05T09:00:00Z",
        action="reclassify",
        reason="the named party is a company, not a living person",
        target_preimage="R3",
        result="R1",
    )
    assert revise(RiskTier.R3, RiskTier.R1, reasoned) is RiskTier.R1


def test_r3_is_never_publishable_without_an_operator_and_r4_never_at_all():
    assert PUBLICATION_DISPOSITION["R3"] == "operator_approval_of_the_exact_revision"
    assert PUBLICATION_DISPOSITION["R4"] == "never"
