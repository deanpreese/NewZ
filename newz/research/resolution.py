"""Resolvers, and what happens when one answers.

A resolver is a competent outside authority for a particular kind of question: a
registry, a docket, a publication-status service, a retraction notice, a
replication record, or the thing that settles a forecast at its horizon.

Two outcomes matter and they are not the same fact. `satisfied` means the
resolver answered. `unreachable` means no competent resolver exists for this
question, recorded with what was sought and where — which is what lets absence
count under `SPEC.md` 7.3 rule 8. `refused` means policy declined the work, and
that one never counts, because the search did not happen.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from newz.control.audit import record as audit_record
from newz.domain.enums import EvidenceLane, TaskState
from newz.research.tasks import record_search, transition_task
from newz.store.db import Store

#: The resolver classes `PLAN.md` Phase 3 names. A resolver declares which lane
#: it answers for; nothing else about it is policy.
RESOLVERS: dict[str, EvidenceLane] = {
    "competent_registry": EvidenceLane.PRIMARY_RECORD,
    "docket": EvidenceLane.RESOLVER,
    "publication_status": EvidenceLane.RESOLVER,
    "retraction_notice": EvidenceLane.RESOLVER,
    "replication_record": EvidenceLane.EMPIRICAL,
    "forecast_resolver": EvidenceLane.RESOLVER,
}


@dataclass(frozen=True, slots=True)
class Resolution:
    attempt_id: str
    task_id: str
    claim_id: str
    resolver: str
    outcome: TaskState
    detail: str

    def as_record(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "task_id": self.task_id,
            "claim_id": self.claim_id,
            "resolver": self.resolver,
            "outcome": self.outcome.value,
            "detail": self.detail,
        }


def record_resolution(
    store: Store,
    *,
    attempt_id: str,
    task_id: str,
    claim_id: str,
    resolver: str,
    outcome: TaskState,
    detail: str,
    sought: str,
    searched: str,
    time_window: str = "",
) -> Resolution:
    """Record what the resolver did, and move the task to match.

    `sought` and `searched` are required for a competent terminal outcome. A
    resolver that reports `exhausted` without saying what it looked for has
    produced a sentence, not a search, and `SPEC.md` 7.3 rule 8 will not let it
    satisfy the absence rule anyway — so it is refused here rather than
    discovered later.
    """
    if resolver not in RESOLVERS:
        raise KeyError(f"no resolver named {resolver!r}")
    if outcome in (TaskState.EXHAUSTED, TaskState.UNREACHABLE) and not (
        sought and searched and time_window
    ):
        # All three, because SPEC 7.3 rule 8 asks for all of them. A search with
        # no window is a search with no scope in time, and "we looked and found
        # nothing" without saying when is the sentence this rule exists to stop.
        raise ValueError(
            f"{outcome.value} records what was sought, where, and over what window; "
            "absence is evidence only from a lane that can say what it looked for"
        )

    with store.write() as connection:
        connection.execute(
            "INSERT INTO resolution_attempts (id, task_id, claim_id, resolver, outcome, detail, "
            "sought, searched, attempted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (attempt_id, task_id, claim_id, resolver, outcome.value, detail, sought, searched),
        )

    if sought or searched:
        record_search(
            store,
            task_id,
            expected_record=sought,
            repository=searched,
            query=detail or sought,
            time_window=time_window,
            searched_scope=searched,
        )
    transition_task(store, task_id, outcome, reason=detail, actor=f"resolver:{resolver}")
    return Resolution(
        attempt_id=attempt_id,
        task_id=task_id,
        claim_id=claim_id,
        resolver=resolver,
        outcome=outcome,
        detail=detail,
    )


def apply_retraction(
    store: Store,
    *,
    basis_id: str,
    reason: str,
    evidence_assertion_id: str | None = None,
    actor: str = "resolver:retraction_notice",
) -> tuple[str, ...]:
    """Withdraw every live edge resting on a retracted basis.

    A retraction does not delete anything. The edge events stay, marked not
    live, so the record still says that this was admitted and later withdrawn —
    which is the difference between a correction and a quiet edit.
    """
    from newz.evidence.edges import withdraw_edge

    affected = [
        row["id"]
        for row in store.query(
            "SELECT id FROM edge_events WHERE basis_id = ? AND live = 1 AND admitted = 1 "
            "ORDER BY id",
            basis_id,
        )
    ]
    for edge_id in affected:
        withdraw_edge(store, edge_id, reason)

    with store.write() as connection:
        audit_record(
            connection,
            actor=actor,
            action="apply_retraction",
            target=basis_id,
            reason=reason,
            preimage=json.dumps({"withdrawn_edges": affected}, sort_keys=True),
            result=f"{len(affected)} edge(s) withdrawn",
            channel="system",
        )
    return tuple(affected)
