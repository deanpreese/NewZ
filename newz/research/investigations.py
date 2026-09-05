"""Investigations: bounded, with an exit condition stated before any work starts.

`SPEC.md` section 9.1 requires an originated investigation to state its question,
its exit conditions and the observation that would close it *before any task is
created*. That ordering is the whole discipline: an investigation that decides
afterwards what would have settled it can always find that something did.

The same requirement is applied here to every investigation, not only the
self-originated ones. An operator-opened investigation with no stated exit is a
standing interest wearing a different word.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from newz.control import audit
from newz.store.db import Store

OPEN = "open"
CLOSED = "closed"
ABANDONED = "abandoned"

ORIGINS = frozenset({"operator", "assessment", "interest"})


@dataclass(frozen=True, slots=True)
class Investigation:
    id: str
    question: str
    rationale: str
    priority: int
    exit_conditions: tuple[str, ...]
    closing_observation: str
    origin: str
    state: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "rationale": self.rationale,
            "priority": self.priority,
            "exit_conditions": list(self.exit_conditions),
            "closing_observation": self.closing_observation,
            "origin": self.origin,
            "state": self.state,
        }


def open_investigation(
    store: Store,
    *,
    investigation_id: str,
    question: str,
    rationale: str,
    exit_conditions: tuple[str, ...],
    closing_observation: str,
    origin: str,
    priority: int = 5,
    claim_ids: tuple[str, ...] = (),
    actor: str = "system",
) -> Investigation:
    """Open one, refusing anything that cannot say what would close it."""
    problems = []
    if not question.strip():
        problems.append("an investigation states its question")
    if not exit_conditions:
        problems.append("an investigation states what would end it")
    if not closing_observation.strip():
        problems.append("an investigation states the observation that would close it")
    if origin not in ORIGINS:
        problems.append(f"origin must be one of {sorted(ORIGINS)}")
    if problems:
        raise ValueError("; ".join(problems))

    with store.write() as connection:
        connection.execute(
            "INSERT INTO investigations (id, question, rationale, priority, exit_conditions, "
            "closing_observation, origin, state, opened_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                investigation_id,
                question,
                rationale,
                priority,
                json.dumps(list(exit_conditions)),
                closing_observation,
                origin,
                OPEN,
            ),
        )
        for claim_id in claim_ids:
            connection.execute(
                "INSERT OR IGNORE INTO investigation_claims (investigation_id, claim_id, added_at) "
                "VALUES (?, ?, datetime('now'))",
                (investigation_id, claim_id),
            )
        audit.record(
            connection,
            actor=actor,
            action="open_investigation",
            target=investigation_id,
            reason=rationale,
            preimage=json.dumps({"origin": origin, "claims": list(claim_ids)}, sort_keys=True),
            result=question,
        )

    return Investigation(
        id=investigation_id,
        question=question,
        rationale=rationale,
        priority=priority,
        exit_conditions=tuple(exit_conditions),
        closing_observation=closing_observation,
        origin=origin,
        state=OPEN,
    )


def add_claim_to_investigation(store: Store, investigation_id: str, claim_id: str) -> None:
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO investigation_claims (investigation_id, claim_id, added_at) "
            "VALUES (?, ?, datetime('now'))",
            (investigation_id, claim_id),
        )


def close_investigation(
    store: Store, investigation_id: str, reason: str, actor: str = "system", abandoned: bool = False
) -> None:
    """Close it with a reason. The operator may close any investigation at any time."""
    if not reason.strip():
        raise ValueError("closing an investigation records why")
    with store.write() as connection:
        cursor = connection.execute(
            "UPDATE investigations SET state = ?, closed_at = datetime('now'), closed_reason = ? "
            "WHERE id = ? AND state = ?",
            (ABANDONED if abandoned else CLOSED, reason, investigation_id, OPEN),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"{investigation_id} is not open")
        audit.record(
            connection,
            actor=actor,
            action="close_investigation",
            target=investigation_id,
            reason=reason,
            preimage=OPEN,
            result=ABANDONED if abandoned else CLOSED,
        )


def load(store: Store, investigation_id: str) -> Investigation | None:
    row = store.one("SELECT * FROM investigations WHERE id = ?", investigation_id)
    if row is None:
        return None
    return Investigation(
        id=row["id"],
        question=row["question"],
        rationale=row["rationale"],
        priority=row["priority"],
        exit_conditions=tuple(json.loads(row["exit_conditions"])),
        closing_observation=row["closing_observation"],
        origin=row["origin"],
        state=row["state"],
    )


def claims_of(store: Store, investigation_id: str) -> tuple[str, ...]:
    return tuple(
        row["claim_id"]
        for row in store.query(
            "SELECT claim_id FROM investigation_claims WHERE investigation_id = ? "
            "ORDER BY claim_id",
            investigation_id,
        )
    )


def open_investigations(store: Store) -> tuple[Investigation, ...]:
    return tuple(
        Investigation(
            id=row["id"],
            question=row["question"],
            rationale=row["rationale"],
            priority=row["priority"],
            exit_conditions=tuple(json.loads(row["exit_conditions"])),
            closing_observation=row["closing_observation"],
            origin=row["origin"],
            state=row["state"],
        )
        for row in store.query(
            "SELECT * FROM investigations WHERE state = ? ORDER BY priority DESC, id", OPEN
        )
    )
