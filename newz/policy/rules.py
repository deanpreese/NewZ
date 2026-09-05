"""The capability rules, in the order they are applied.

Every cell of the matrix is decided by exactly one rule, and the rule that
decided it is recorded, so a refusal can be read back to the principle or the
recorded decision that produced it. First match wins, so the order carries meaning: the unconditional refusals come
first, because a refusal nothing can change is more useful to read than one a
different source could have satisfied. An inference is not evidence whoever
makes it; a claimant source could have been a different source. The last rule is
deny-by-default, so a cell no rule reaches is refused rather than admitted.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

from newz.domain.enums import (
    COUNTABLE_RELATIONS,
    AssertionKind,
    ClaimKind,
    EdgeRelation,
    RefusalReason,
    SourceRole,
)


class Cell(NamedTuple):
    role: SourceRole
    claim_kind: ClaimKind
    assertion_kind: AssertionKind
    relation: EdgeRelation


@dataclass(frozen=True, slots=True)
class Verdict:
    admitted: bool
    rule_id: str
    reason: RefusalReason | None = None


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    description: str
    #: The clause of `SPEC.md` this rule transcribes, when it transcribes one.
    spec_ref: str
    #: The recorded decision this rule rests on, when the clause did not settle it.
    decision_id: str | None
    applies: Callable[[Cell], Verdict | None]


def _refuse(rule_id: str, reason: RefusalReason) -> Verdict:
    return Verdict(admitted=False, rule_id=rule_id, reason=reason)


def _admit(rule_id: str) -> Verdict:
    return Verdict(admitted=True, rule_id=rule_id)


# ---------------------------------------------------------------------------
# The role capability table, consulted after every stated refusal has had its
# turn. It whitelists the assertion kinds each role may carry into a countable
# relation for each claim kind. Support and refutation read the same table, so
# symmetry is structural rather than remembered.
# ---------------------------------------------------------------------------

OBS = AssertionKind.OBSERVATION
TES = AssertionKind.TESTIMONY
ALL = AssertionKind.ALLEGATION
MEA = AssertionKind.MEASUREMENT
DOC = AssertionKind.DOCUMENTED_EVENT

ROLE_CAPABILITY: dict[SourceRole, dict[ClaimKind, frozenset[AssertionKind]]] = {
    SourceRole.CLAIMANT: {
        ClaimKind.ATTRIBUTION: frozenset({OBS, TES, ALL, MEA, DOC}),
    },
    SourceRole.FIRSTHAND_WITNESS: {
        ClaimKind.ATTRIBUTION: frozenset({OBS, TES, ALL}),
        ClaimKind.EVENT_OR_OBSERVATION: frozenset({OBS, TES}),
    },
    SourceRole.PRIMARY_RECORD: {
        ClaimKind.ATTRIBUTION: frozenset({DOC}),
        ClaimKind.DOCUMENT_EXISTENCE: frozenset({DOC}),
        ClaimKind.EVENT_OR_OBSERVATION: frozenset({OBS, MEA, DOC}),
        ClaimKind.MEASUREMENT_OR_ASSOCIATION: frozenset({MEA, DOC}),
        ClaimKind.CAPABILITY_OR_PERFORMANCE: frozenset({MEA}),
        ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION: frozenset({DOC}),
        ClaimKind.FORECAST: frozenset({MEA, DOC}),
    },
    SourceRole.EMPIRICAL_STUDY: {
        ClaimKind.EVENT_OR_OBSERVATION: frozenset({OBS, MEA}),
        ClaimKind.MEASUREMENT_OR_ASSOCIATION: frozenset({OBS, MEA}),
        ClaimKind.CAUSAL_OR_MECHANISTIC: frozenset({MEA}),
        ClaimKind.CAPABILITY_OR_PERFORMANCE: frozenset({MEA}),
        ClaimKind.FORECAST: frozenset({MEA}),
    },
    SourceRole.ADJUDICATOR: {
        ClaimKind.ATTRIBUTION: frozenset({DOC}),
        ClaimKind.DOCUMENT_EXISTENCE: frozenset({DOC}),
        ClaimKind.EVENT_OR_OBSERVATION: frozenset({DOC}),
        ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION: frozenset({DOC}),
        ClaimKind.FORECAST: frozenset({DOC}),
    },
    SourceRole.SKEPTICAL_INVESTIGATION: {
        ClaimKind.ATTRIBUTION: frozenset({DOC}),
        ClaimKind.DOCUMENT_EXISTENCE: frozenset({DOC}),
        ClaimKind.EVENT_OR_OBSERVATION: frozenset({OBS, MEA, DOC}),
        ClaimKind.MEASUREMENT_OR_ASSOCIATION: frozenset({OBS, MEA}),
        ClaimKind.CAUSAL_OR_MECHANISTIC: frozenset({MEA}),
        ClaimKind.CAPABILITY_OR_PERFORMANCE: frozenset({MEA}),
        ClaimKind.FORECAST: frozenset({MEA, DOC}),
    },
    SourceRole.HISTORICAL_CONTEXT: {},
    SourceRole.GENERAL_CONTEXT: {},
}

#: Roles whose bases satisfy the strong-provenance requirement (D-009) and,
#: for the primary and adjudicative subset, the R3 requirement (D-010).
STRONG_PROVENANCE_ROLES: frozenset[SourceRole] = frozenset(
    {SourceRole.PRIMARY_RECORD, SourceRole.EMPIRICAL_STUDY, SourceRole.ADJUDICATOR}
)

DIRECT_RECORD_ROLES: frozenset[SourceRole] = frozenset(
    {SourceRole.PRIMARY_RECORD, SourceRole.ADJUDICATOR}
)

CONTEXT_ONLY_ROLES: frozenset[SourceRole] = frozenset(
    {SourceRole.HISTORICAL_CONTEXT, SourceRole.GENERAL_CONTEXT}
)


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------


def _r01(cell: Cell) -> Verdict | None:
    if cell.relation is EdgeRelation.CLAIMANT_SAYS:
        return _admit("R-01")
    return None


def _r02(cell: Cell) -> Verdict | None:
    if cell.relation is EdgeRelation.CONTEXTUALIZES:
        return _admit("R-02")
    return None


def _r03(cell: Cell) -> Verdict | None:
    if cell.claim_kind is ClaimKind.NORMATIVE_PROPOSITION:
        return _refuse("R-03", RefusalReason.NORMATIVE_ADMITS_NO_EVIDENCE)
    return None


def _r04(cell: Cell) -> Verdict | None:
    if cell.assertion_kind is AssertionKind.INFERENCE:
        return _refuse("R-04", RefusalReason.INFERENCE_IS_NOT_EVIDENCE)
    return None


def _r05(cell: Cell) -> Verdict | None:
    if cell.assertion_kind is AssertionKind.PREDICTION:
        return _refuse("R-05", RefusalReason.PREDICTION_IS_NOT_EVIDENCE)
    return None


def _r06(cell: Cell) -> Verdict | None:
    if (
        cell.assertion_kind is AssertionKind.ALLEGATION
        and cell.claim_kind is not ClaimKind.ATTRIBUTION
    ):
        return _refuse("R-06", RefusalReason.ALLEGATION_IS_NOT_PROOF)
    return None


def _r07(cell: Cell) -> Verdict | None:
    if cell.role is SourceRole.CLAIMANT and cell.claim_kind is not ClaimKind.ATTRIBUTION:
        return _refuse("R-07", RefusalReason.CLAIMANT_ESTABLISHES_ATTRIBUTION_ONLY)
    return None


def _r08(cell: Cell) -> Verdict | None:
    if cell.role in CONTEXT_ONLY_ROLES:
        return _refuse("R-08", RefusalReason.CONTEXT_ROLE_IS_CONTEXTUAL_ONLY)
    return None


def _r09(cell: Cell) -> Verdict | None:
    if cell.claim_kind is ClaimKind.CAPABILITY_OR_PERFORMANCE and (
        cell.assertion_kind is not AssertionKind.MEASUREMENT
    ):
        return _refuse("R-09", RefusalReason.FILING_IS_NOT_PERFORMANCE)
    return None


def _r10(cell: Cell) -> Verdict | None:
    if cell.claim_kind is ClaimKind.IDENTITY_OR_WRONGDOING_ALLEGATION and not (
        cell.role in DIRECT_RECORD_ROLES
        and cell.assertion_kind is AssertionKind.DOCUMENTED_EVENT
    ):
        return _refuse("R-10", RefusalReason.WRONGDOING_NEEDS_ADJUDICATION)
    return None


def _r11(cell: Cell) -> Verdict | None:
    if cell.assertion_kind is AssertionKind.TESTIMONY and cell.claim_kind not in (
        ClaimKind.ATTRIBUTION,
        ClaimKind.EVENT_OR_OBSERVATION,
    ):
        return _refuse("R-11", RefusalReason.TESTIMONY_IS_BOUNDED)
    return None


def _r12(cell: Cell) -> Verdict | None:
    allowed = ROLE_CAPABILITY.get(cell.role, {}).get(cell.claim_kind, frozenset())
    if cell.assertion_kind in allowed:
        return _admit("R-12")
    return None


def _r13(cell: Cell) -> Verdict | None:
    return _refuse("R-13", RefusalReason.ROLE_LACKS_CAPABILITY)


RULES: tuple[Rule, ...] = (
    Rule(
        id="R-01",
        description=(
            "`claimant_says` is admitted for every role, claim kind, and assertion "
            "kind: it records that a source asserts the claim and establishes nothing "
            "about the claim."
        ),
        spec_ref="7.2",
        decision_id=None,
        applies=_r01,
    ),
    Rule(
        id="R-02",
        description=(
            "`contextualizes` is admitted everywhere for the same reason: contextual "
            "material never counts toward a threshold."
        ),
        spec_ref="7.2",
        decision_id=None,
        applies=_r02,
    ),
    Rule(
        id="R-03",
        description=(
            "A normative proposition admits no `supports` or `contradicts` edge; the "
            "promotion rules cannot evaluate one."
        ),
        spec_ref="7.1",
        decision_id=None,
        applies=_r03,
    ),
    Rule(
        id="R-04",
        description="An inference is reasoning over evidence, not evidence.",
        spec_ref="7.3 rule 6",
        decision_id="D-001",
        applies=_r04,
    ),
    Rule(
        id="R-05",
        description="A prediction establishes only that it was made.",
        spec_ref="7.1",
        decision_id="D-002",
        applies=_r05,
    ),
    Rule(
        id="R-06",
        description=(
            "An allegation proves an allegation. It reaches an attribution claim and "
            "no other kind."
        ),
        spec_ref="7.3 rule 4",
        decision_id="D-008",
        applies=_r06,
    ),
    Rule(
        id="R-07",
        description=(
            "Claimant material may establish only an accurately attributed meta-claim."
        ),
        spec_ref="7.3 rule 1",
        decision_id=None,
        applies=_r07,
    ),
    Rule(
        id="R-08",
        description="The context roles supply background and carry no countable evidence.",
        spec_ref="5.1",
        decision_id="D-007",
        applies=_r08,
    ),
    Rule(
        id="R-09",
        description="A performance claim needs a measurement; a filing is not performance.",
        spec_ref="7.3 rule 3",
        decision_id="D-003",
        applies=_r09,
    ),
    Rule(
        id="R-10",
        description=(
            "A wrongdoing claim admits only a documented event from a primary record or "
            "an adjudicator. A complaint is an allegation and is already refused above."
        ),
        spec_ref="7.3 rule 4",
        decision_id="D-004",
        applies=_r10,
    ),
    Rule(
        id="R-11",
        description=(
            "Testimony reaches attribution and event claims. No quantity of it reaches "
            "a measurement, a mechanism, or a performance."
        ),
        spec_ref="7.3 rule 2",
        decision_id="D-005",
        applies=_r11,
    ),
    Rule(
        id="R-12",
        description=(
            "The role capability table: what each role may carry into a countable "
            "relation, read identically for support and for refutation."
        ),
        spec_ref="5.1",
        decision_id="D-006",
        applies=_r12,
    ),
    Rule(
        id="R-13",
        description="Deny by default. A cell no rule admits is refused.",
        spec_ref="ARCHITECTURE, evidence engine",
        decision_id=None,
        applies=_r13,
    ),
)

BY_ID: dict[str, Rule] = {r.id: r for r in RULES}


def decide(cell: Cell) -> Verdict:
    """Apply the rules in order and return the first verdict."""
    for rule in RULES:
        verdict = rule.applies(cell)
        if verdict is not None:
            return verdict
    raise AssertionError("deny-by-default rule did not fire")  # pragma: no cover


def is_countable_relation(relation: EdgeRelation) -> bool:
    return relation in COUNTABLE_RELATIONS
