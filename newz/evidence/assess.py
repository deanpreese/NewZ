"""Deriving an assessment, and recording it as history.

The derivation is `newz.policy.promotion.assess`, which is pure. This loads the
claim, its live admitted edges, the bases beneath them, the independence
recorded between them and the tasks that describe the search, hands all of it
over, and appends the answer.

Appending is the point. A claim's assessment history is the record of what the
system believed and when, so a reassessment adds a row rather than changing one,
and the dependent projections are invalidated through the outbox in the same
transaction that wrote it.
"""

from __future__ import annotations

import json

from newz.domain.enums import AssessmentState, EvidenceLane, TaskState
from newz.domain.records import Assessment, Task
from newz.evidence.bases import load_bases, load_independence
from newz.evidence.edges import load_claim, load_edges
from newz.policy.promotion import EvidenceInput, assess
from newz.store.db import Store
from newz.version import POLICY_VERSION


def load_tasks(store: Store, claim_id: str) -> tuple[Task, ...]:
    return tuple(
        Task(
            id=row["id"],
            claim_id=row["claim_id"],
            lane=EvidenceLane(row["lane"]),
            state=TaskState(row["state"]),
            owner=row["owner"],
            reason=row["reason"],
            due=row["due"],
            retry_budget=row["retry_budget"],
            state_reason=row["state_reason"],
            expected_record=row["expected_record"],
            repository=row["repository"],
            query=row["query"],
            time_window=row["time_window"],
            searched_scope=row["searched_scope"],
        )
        for row in store.query("SELECT * FROM tasks WHERE claim_id = ? ORDER BY id", claim_id)
    )


def load_assertions(store: Store, claim_id: str):
    from newz.evidence.edges import load_assertion

    ids = [
        row["assertion_id"]
        for row in store.query(
            "SELECT DISTINCT assertion_id FROM edge_events WHERE claim_id = ? ORDER BY assertion_id",
            claim_id,
        )
    ]
    loaded = {}
    for assertion_id in ids:
        assertion = load_assertion(store, assertion_id)
        if assertion is not None:
            loaded[assertion_id] = assertion
    return loaded


def evidence_input(store: Store, claim_id: str, horizon_reached: bool = False) -> EvidenceInput:
    claim = load_claim(store, claim_id)
    if claim is None:
        raise KeyError(claim_id)
    return EvidenceInput(
        claim=claim,
        edges=load_edges(store, claim_id),
        assertions=load_assertions(store, claim_id),
        bases=load_bases(store),
        independence=load_independence(store),
        tasks=load_tasks(store, claim_id),
        horizon_reached=horizon_reached,
    )


def assess_claim(
    store: Store,
    claim_id: str,
    assessment_id: str,
    horizon_reached: bool = False,
    policy_version: str = POLICY_VERSION,
) -> Assessment:
    """Derive the current state and append it, invalidating what depended on it."""
    result = assess(evidence_input(store, claim_id, horizon_reached), policy_version)
    previous = current_assessment(store, claim_id)

    with store.write() as connection:
        connection.execute(
            "INSERT INTO assessments (id, claim_id, state, supporting_bases, "
            "contradicting_bases, policy_version, code_version, explanation, "
            "blocked_lanes_json, countable_edge_ids_json, derived_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                assessment_id,
                claim_id,
                result.state.value,
                result.supporting_bases,
                result.contradicting_bases,
                result.policy_version,
                result.code_version,
                result.explanation,
                json.dumps(
                    [[lane.value, state.value, reason] for lane, state, reason in result.blocked_lanes]
                ),
                json.dumps(list(result.countable_edge_ids)),
            ),
        )
        if previous is None or previous.state is not result.state:
            connection.execute(
                "INSERT INTO outbox (at, kind, subject, payload) "
                "VALUES (datetime('now'), ?, ?, ?)",
                (
                    "assessment_changed",
                    claim_id,
                    json.dumps(
                        {
                            "from": previous.state.value if previous else None,
                            "to": result.state.value,
                            "assessment": assessment_id,
                        },
                        sort_keys=True,
                    ),
                ),
            )
    return result


def current_assessment(store: Store, claim_id: str) -> Assessment | None:
    # Ordered by insertion, not by timestamp. `datetime('now')` has second
    # resolution and two assessments in one second are ordinary — a withdrawal
    # and its reassessment, for instance — so ordering by time would make
    # "current" a coin toss exactly when it matters.
    row = store.one(
        "SELECT * FROM assessments WHERE claim_id = ? ORDER BY rowid DESC LIMIT 1", claim_id
    )
    if row is None:
        return None
    return _as_assessment(row)


def assessment_history(store: Store, claim_id: str) -> tuple[Assessment, ...]:
    return tuple(
        _as_assessment(row)
        for row in store.query(
            "SELECT * FROM assessments WHERE claim_id = ? ORDER BY rowid", claim_id
        )
    )


def _as_assessment(row) -> Assessment:
    return Assessment(
        claim_id=row["claim_id"],
        state=AssessmentState(row["state"]),
        supporting_bases=row["supporting_bases"],
        contradicting_bases=row["contradicting_bases"],
        policy_version=row["policy_version"],
        code_version=row["code_version"],
        explanation=row["explanation"],
        blocked_lanes=tuple(
            (EvidenceLane(lane), TaskState(state), reason)
            for lane, state, reason in json.loads(row["blocked_lanes_json"])
        ),
        countable_edge_ids=tuple(json.loads(row["countable_edge_ids_json"])),
    )


def stale_claims(store: Store, policy_version: str = POLICY_VERSION) -> tuple[str, ...]:
    """Claims whose current assessment was derived under a superseded policy."""
    return tuple(
        row["claim_id"]
        for row in store.query(
            "SELECT claim_id, policy_version FROM assessments a WHERE a.rowid = ("
            "  SELECT MAX(b.rowid) FROM assessments b WHERE b.claim_id = a.claim_id"
            ") AND a.policy_version != ? ORDER BY claim_id",
            policy_version,
        )
    )
