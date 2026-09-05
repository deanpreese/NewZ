"""Decisions and expectations.

Declining and deferring are first-class outcomes recorded with their reasons,
not absences in the record. Every decision records the alternatives considered,
what decided it, the expected outcome and the confidence — because a decision
nobody can re-examine against what later happened is not a decision; it is an
action with a timestamp.

An expectation is recorded **before** acting. The table refuses updates for that
reason: an expectation revised after the outcome is a recollection, and
comparing an outcome to a recollection of the expectation measures nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from newz.domain.enums import DecisionOutcome
from newz.store.db import Store


@dataclass(frozen=True, slots=True)
class RecordedDecision:
    id: str
    outcome: DecisionOutcome
    subject: str
    alternatives: tuple[str, ...]
    reason: str
    expectation_id: str | None

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "outcome": self.outcome.value,
            "subject": self.subject,
            "alternatives": list(self.alternatives),
            "reason": self.reason,
            "expectation_id": self.expectation_id,
        }


def record_expectation(
    store: Store, *, expectation_id: str, subject: str, expected: str, recorded_before: str
) -> str:
    """State what is expected, before the thing it is expected of happens."""
    if not expected.strip():
        raise ValueError("an expectation says what is expected")
    if not recorded_before.strip():
        raise ValueError("an expectation names the act it precedes")
    with store.write() as connection:
        connection.execute(
            "INSERT INTO expectations (id, subject, expected, recorded_before, at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (expectation_id, subject, expected, recorded_before),
        )
    return expectation_id


def record_decision(
    store: Store,
    *,
    decision_id: str,
    outcome: DecisionOutcome,
    subject: str,
    alternatives: tuple[str, ...],
    decided_by: str,
    reason: str,
    expectation_id: str | None = None,
    confidence: str = "",
    re_raise_condition: str = "",
) -> RecordedDecision:
    """Record a decision with what else was on the table.

    A deferral must say what would bring it back. "Later" is not a re-raise
    condition; it is a way of never deciding while appearing to have decided.
    """
    if not alternatives:
        raise ValueError(
            "a decision records the alternatives considered; one option is not a decision"
        )
    if not reason.strip():
        raise ValueError("a decision records what decided it")
    if outcome is DecisionOutcome.DEFER and not re_raise_condition.strip():
        raise ValueError("a deferral records what would bring it back")

    with store.write() as connection:
        connection.execute(
            "INSERT INTO decisions (id, outcome, subject, alternatives_json, decided_by, reason, "
            "expectation_id, confidence, re_raise_condition, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                decision_id,
                outcome.value,
                subject,
                json.dumps(list(alternatives)),
                decided_by,
                reason,
                expectation_id,
                confidence,
                re_raise_condition,
            ),
        )
    return RecordedDecision(
        id=decision_id,
        outcome=outcome,
        subject=subject,
        alternatives=tuple(alternatives),
        reason=reason,
        expectation_id=expectation_id,
    )


def decisions(store: Store, subject: str = "") -> tuple[dict[str, Any], ...]:
    rows = (
        store.query("SELECT * FROM decisions WHERE subject = ? ORDER BY id", subject)
        if subject
        else store.query("SELECT * FROM decisions ORDER BY id")
    )
    return tuple(
        {**dict(row), "alternatives": json.loads(row["alternatives_json"])} for row in rows
    )


def declined_and_deferred(store: Store) -> tuple[dict[str, Any], ...]:
    """The outcomes that would otherwise be absences in the record."""
    return tuple(
        {**dict(row), "alternatives": json.loads(row["alternatives_json"])}
        for row in store.query(
            "SELECT * FROM decisions WHERE outcome IN ('decline', 'defer') ORDER BY id"
        )
    )
