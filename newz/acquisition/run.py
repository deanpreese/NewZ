"""One authorized read, end to end.

This is the seam Gate 1 exercises: a reservation becomes an attempt, an attempt
becomes bytes, and bytes become an artifact, a response, and a sighting — or the
whole thing becomes a recorded refusal, which is equally a fact about the source.

The transaction boundary is the point of the module. The artifact is made
durable first and outside the transaction; everything that references it commits
together, including the operation's terminal state. A crash anywhere in between
leaves either nothing or a complete trace, never a row citing bytes that are not
there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from newz.acquisition import artifacts, instruction
from newz.acquisition.fetcher import FetchPolicy, FetchResult, fetch, host_of
from newz.acquisition.transport import Transport
from newz.catalog.sources import SourceRevision
from newz.control.retry import RetryPolicy, pacing_refusal
from newz.control.scheduler import Operation
from newz.domain.enums import (
    TERMINAL_OPERATION_STATES,
    AttemptOutcome,
    FetchRefusal,
    OperationState,
)
from newz.store.db import Store

TEXTUAL_MIMES = frozenset({"text/html", "text/plain", "text/csv", "application/json", "application/xml"})


@dataclass(frozen=True, slots=True)
class AcquisitionRecord:
    operation_id: str
    attempt_id: str
    outcome: AttemptOutcome
    refusal: FetchRefusal | None
    artifact_id: str | None
    response_id: str | None
    sighting_id: str | None
    content_hash: str
    instruction_observations: int
    detail: str

    @property
    def retained(self) -> bool:
        return self.artifact_id is not None


class OperationAlreadyTerminal(Exception):
    """A finished operation is not a slot to run something else in.

    Without this the second run writes an attempt against an operation that
    already reported its outcome, and the ledger holds two answers to one
    authorization. A retry is a new operation with its own reservation, which
    is also what makes a retry cost budget.
    """


def _refuse_if_terminal(store: Store, operation_id: str) -> None:
    row = store.one("SELECT state FROM operations WHERE id = ?", operation_id)
    if row is not None and row["state"] in {s.value for s in TERMINAL_OPERATION_STATES}:
        raise OperationAlreadyTerminal(f"{operation_id} is already {row['state']}")


def _suffix(operation_id: str) -> str:
    return operation_id.split(":", 1)[-1]


def acquire(
    store: Store,
    operation: Operation,
    revision: SourceRevision,
    transport: Transport,
    policy: FetchPolicy | None = None,
    result: FetchResult | None = None,
    retry: RetryPolicy | None = None,
    now: datetime | None = None,
) -> AcquisitionRecord:
    """Run the operation's fetch and record everything it produced.

    `result` exists for the crash-injection tests, which need to reach the state
    just before the commit without a live transport. It changes no behaviour.
    """
    _refuse_if_terminal(store, operation.id)
    suffix = _suffix(operation.id)
    attempt_id = f"attempt:{suffix}"

    if result is None:
        paced = pacing_refusal(
            store,
            host_of(revision.endpoint_url),
            now or datetime.now(),
            retry or RetryPolicy(),
        )
        if paced is not None:
            # The politeness floor is enforced before the socket, and the
            # refusal is recorded like any other: a read we declined to make is
            # a fact about the day's budget, not an absence.
            return _record_unretained(
                store,
                operation,
                attempt_id,
                FetchResult(
                    outcome=AttemptOutcome.REFUSED,
                    url=revision.endpoint_url,
                    refusal=paced,
                    detail="minimum interval between reads of this host",
                ),
            )

    outcome = result or fetch(revision.endpoint_url, transport, policy)

    if not outcome.retained:
        return _record_unretained(store, operation, attempt_id, outcome)

    if not revision.may_retain_evidence:
        # The read happened and the terms forbid keeping the body. The attempt is
        # recorded, the bytes are not, and the material stays a lead.
        return _record_unretained(
            store,
            operation,
            attempt_id,
            FetchResult(
                outcome=AttemptOutcome.REFUSED,
                url=outcome.url,
                final_url=outcome.final_url,
                status=outcome.status,
                bytes_read=outcome.bytes_read,
                redirects=outcome.redirects,
                refusal=FetchRefusal.RETENTION_PROHIBITED,
                detail=revision.retention_policy.value,
            ),
        )

    # Durable first, and outside the transaction that will reference it.
    stored = artifacts.store_bytes(store.artifact_root, outcome.body)

    observations: tuple[instruction.InstructionObservation, ...] = ()
    if outcome.normalized_mime in TEXTUAL_MIMES:
        observations = instruction.scan(outcome.body.decode("utf-8", errors="replace"))

    artifact_id = f"artifact:{stored.content_hash[:16]}"
    response_id = f"response:{suffix}"
    sighting_id = f"sighting:{suffix}"

    with store.write() as connection:
        artifact_id = artifacts.record_artifact(
            store, connection, artifact_id, stored, outcome.normalized_mime
        )
        connection.execute(
            "INSERT INTO attempts (id, operation_id, url, started_at, outcome, refusal_reason, "
            "http_status, bytes_read, redirects_json, detail) "
            "VALUES (?, ?, ?, datetime('now'), ?, NULL, ?, ?, ?, '')",
            (
                attempt_id,
                operation.id,
                outcome.url,
                AttemptOutcome.RETAINED.value,
                outcome.status,
                outcome.bytes_read,
                json.dumps(list(outcome.redirects)),
            ),
        )
        connection.execute(
            "INSERT INTO responses (id, attempt_id, final_url, http_status, declared_mime, "
            "normalized_mime, content_hash, byte_size, headers_json, artifact_id, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                response_id,
                attempt_id,
                outcome.final_url or outcome.url,
                outcome.status,
                outcome.declared_mime,
                outcome.normalized_mime,
                stored.content_hash,
                stored.byte_size,
                json.dumps(dict(outcome.headers), sort_keys=True),
                artifact_id,
            ),
        )
        # A duplicate body shares the artifact and never shares the sighting.
        connection.execute(
            "INSERT INTO sightings (id, response_id, source_revision_id, artifact_id, observed_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (sighting_id, response_id, revision.id, artifact_id),
        )
        if observations:
            instruction.record(
                connection,
                source_revision_id=revision.id,
                artifact_id=artifact_id,
                observations=observations,
                id_prefix=f"instruction:{suffix}",
            )
        connection.execute(
            "INSERT INTO outbox (at, kind, subject, payload) VALUES (datetime('now'), ?, ?, ?)",
            (
                "artifact_retained",
                artifact_id,
                json.dumps(
                    {
                        "operation": operation.id,
                        "sighting": sighting_id,
                        "content_hash": stored.content_hash,
                        "normalized_mime": outcome.normalized_mime,
                    },
                    sort_keys=True,
                ),
            ),
        )
        _finish(connection, operation.id, OperationState.SUCCEEDED, stored.content_hash)

    return AcquisitionRecord(
        operation_id=operation.id,
        attempt_id=attempt_id,
        outcome=AttemptOutcome.RETAINED,
        refusal=None,
        artifact_id=artifact_id,
        response_id=response_id,
        sighting_id=sighting_id,
        content_hash=stored.content_hash,
        instruction_observations=len(observations),
        detail="",
    )


def _record_unretained(
    store: Store, operation: Operation, attempt_id: str, outcome: FetchResult
) -> AcquisitionRecord:
    """A refusal or an error is a fact about the source and is recorded as one."""
    state = (
        OperationState.QUARANTINED
        if outcome.outcome is AttemptOutcome.REFUSED
        else OperationState.FAILED
    )
    with store.write() as connection:
        connection.execute(
            "INSERT INTO attempts (id, operation_id, url, started_at, outcome, refusal_reason, "
            "http_status, bytes_read, redirects_json, detail) "
            "VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?)",
            (
                attempt_id,
                operation.id,
                outcome.url,
                outcome.outcome.value,
                outcome.refusal.value if outcome.refusal else None,
                outcome.status,
                outcome.bytes_read,
                json.dumps(list(outcome.redirects)),
                outcome.detail,
            ),
        )
        _finish(
            connection,
            operation.id,
            state,
            outcome.refusal.value if outcome.refusal else outcome.detail,
        )

    return AcquisitionRecord(
        operation_id=operation.id,
        attempt_id=attempt_id,
        outcome=outcome.outcome,
        refusal=outcome.refusal,
        artifact_id=None,
        response_id=None,
        sighting_id=None,
        content_hash="",
        instruction_observations=0,
        detail=outcome.detail,
    )


def _finish(connection, operation_id: str, state: OperationState, outcome: str) -> None:
    connection.execute(
        "UPDATE operations SET state = ?, outcome = ?, terminal_at = datetime('now'), "
        "lease_owner = NULL, lease_expires_at = NULL WHERE id = ?",
        (state.value, outcome, operation_id),
    )


def trace(store: Store, operation_id: str) -> dict:
    """The reconstructible acquisition trace Gate 1 asks for.

    Everything that happened under one authorization, read back from the ledger
    rather than from anything the fetcher returned.
    """
    operation = store.one("SELECT * FROM operations WHERE id = ?", operation_id)
    if operation is None:
        raise KeyError(operation_id)
    reservation = store.one("SELECT * FROM reservations WHERE operation_id = ?", operation_id)
    attempts = store.query(
        "SELECT * FROM attempts WHERE operation_id = ? ORDER BY id", operation_id
    )
    out: dict = {
        "operation": {
            "id": operation["id"],
            "kind": operation["kind"],
            "lane": operation["lane"],
            "intent": operation["intent"],
            "state": operation["state"],
            "outcome": operation["outcome"],
            "local_day": operation["local_day"],
            "source_revision_id": operation["source_revision_id"],
            "epoch_id": operation["epoch_id"],
            "policy_version": operation["policy_version"],
        },
        "reservation": (
            {"lane": reservation["lane"], "borrowed_from": reservation["borrowed_from"]}
            if reservation
            else None
        ),
        "attempts": [],
    }
    for attempt in attempts:
        entry = {
            "id": attempt["id"],
            "url": attempt["url"],
            "outcome": attempt["outcome"],
            "refusal_reason": attempt["refusal_reason"],
            "http_status": attempt["http_status"],
            "redirects": json.loads(attempt["redirects_json"]),
            "detail": attempt["detail"],
        }
        response = store.one("SELECT * FROM responses WHERE attempt_id = ?", attempt["id"])
        if response is not None:
            sighting = store.one(
                "SELECT * FROM sightings WHERE response_id = ?", response["id"]
            )
            entry["response"] = {
                "final_url": response["final_url"],
                "normalized_mime": response["normalized_mime"],
                "declared_mime": response["declared_mime"],
                "content_hash": response["content_hash"],
                "byte_size": response["byte_size"],
                "artifact_id": response["artifact_id"],
                "sighting_id": sighting["id"] if sighting else None,
            }
        out["attempts"].append(entry)
    return out
