"""The machine-readable capability matrix.

Every combination of role, claim kind, assertion kind, and relation is
materialized with the rule that decided it and, where the rule rests on a
judgment call, the decision that settled it. `SPEC.md` section 5.1 keeps
declared scope out of the tuple: it is recorded audit context, not a policy
dimension.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.domain.enums import AssertionKind, ClaimKind, EdgeRelation, RefusalReason, SourceRole
from newz.policy import rules
from newz.policy.decisions import BY_ID as DECISIONS_BY_ID
from newz.policy.rules import Cell


@dataclass(frozen=True, slots=True)
class MatrixEntry:
    cell: Cell
    admitted: bool
    rule_id: str
    reason: RefusalReason | None
    decision_id: str | None

    def as_record(self) -> dict[str, Any]:
        return {
            "role": self.cell.role,
            "claim_kind": self.cell.claim_kind,
            "assertion_kind": self.cell.assertion_kind,
            "relation": self.cell.relation,
            "admitted": self.admitted,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "decision_id": self.decision_id,
        }


def all_cells() -> tuple[Cell, ...]:
    """Every cell, in a fixed order that does not depend on set iteration."""
    return tuple(
        Cell(role, claim_kind, assertion_kind, relation)
        for role in SourceRole
        for claim_kind in ClaimKind
        for assertion_kind in AssertionKind
        for relation in EdgeRelation
    )


class CapabilityMatrix:
    """The materialized matrix, queried by tuple."""

    def __init__(self) -> None:
        entries: dict[Cell, MatrixEntry] = {}
        for cell in all_cells():
            verdict = rules.decide(cell)
            rule = rules.BY_ID[verdict.rule_id]
            entries[cell] = MatrixEntry(
                cell=cell,
                admitted=verdict.admitted,
                rule_id=verdict.rule_id,
                reason=verdict.reason,
                decision_id=rule.decision_id,
            )
        self._entries = entries

    def __len__(self) -> int:
        return len(self._entries)

    def lookup(
        self,
        role: SourceRole,
        claim_kind: ClaimKind,
        assertion_kind: AssertionKind,
        relation: EdgeRelation,
    ) -> MatrixEntry:
        return self._entries[Cell(role, claim_kind, assertion_kind, relation)]

    def permits(
        self,
        role: SourceRole,
        claim_kind: ClaimKind,
        assertion_kind: AssertionKind,
        relation: EdgeRelation,
    ) -> bool:
        return self.lookup(role, claim_kind, assertion_kind, relation).admitted

    def entries(self) -> tuple[MatrixEntry, ...]:
        return tuple(self._entries[cell] for cell in all_cells())

    def as_record(self) -> dict[str, Any]:
        return {
            "cells": [entry.as_record() for entry in self.entries()],
            "rules": [
                {
                    "id": rule.id,
                    "description": rule.description,
                    "spec_ref": rule.spec_ref,
                    "decision_id": rule.decision_id,
                }
                for rule in rules.RULES
            ],
            "decisions": [
                DECISIONS_BY_ID[rule.decision_id].as_record()
                for rule in rules.RULES
                if rule.decision_id is not None
            ],
        }


MATRIX = CapabilityMatrix()
