"""One authorized read, recorded end to end.

The crash-injection test is the one to read: it asserts the ordering obligation
from ADR-0001, which is the difference between an orphan file and a ledger that
cites bytes that are not there.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from newz.acquisition import artifacts, instruction
from newz.acquisition.fetcher import FetchResult, fetch
from newz.acquisition.run import acquire, trace
from newz.control.scheduler import claim, reserve
from newz.domain.enums import (
    AttemptOutcome,
    FetchRefusal,
    InstructionMarker,
    OperationKind,
    OperationState,
    ReadLane,
    RetentionPolicy,
)
from tests import canaries
from tests.transport import Reply

DAY = "2026-09-05"


def operation_for(store, canary, index: int = 1, lane: ReadLane = ReadLane.DISCOVERY):
    return reserve(
        store,
        operation_id=f"operation:o{index}",
        reservation_id=f"reservation:r{index}",
        kind=OperationKind.FETCH,
        lane=lane,
        source_revision_id=canary.revision.id,
        epoch_id="epoch:1",
        policy_version="1.0.0",
        intent=f"canary read {index}",
        idempotency_key=f"{DAY}:{canary.revision.id}:{index}",
        local_day=DAY,
    )


def test_a_read_becomes_an_artifact_a_response_and_a_sighting(catalog, transport):
    canary = canaries.CANARIES[0]
    operation = operation_for(catalog, canary)
    claim(catalog, operation.id, "worker:fetch", datetime(2026, 9, 5, 12, 0, 0))
    record = acquire(catalog, operation, canary.revision, transport)

    assert record.outcome is AttemptOutcome.RETAINED
    assert record.artifact_id and record.response_id and record.sighting_id
    assert (
        catalog.one("SELECT state FROM operations WHERE id = ?", operation.id)["state"]
        == OperationState.SUCCEEDED.value
    )
    stored = catalog.one("SELECT * FROM artifacts WHERE id = ?", record.artifact_id)
    assert (catalog.artifact_root / stored["stored_path"]).read_bytes()
    assert stored["content_hash"] == record.content_hash


def test_the_trace_reconstructs_the_read_from_the_ledger_alone(catalog, transport):
    canary = canaries.CANARIES[0]
    operation = operation_for(catalog, canary)
    acquire(catalog, operation, canary.revision, transport)

    reconstructed = trace(catalog, operation.id)
    assert reconstructed["operation"]["epoch_id"] == "epoch:1"
    assert reconstructed["operation"]["policy_version"] == "1.0.0"
    assert reconstructed["reservation"]["lane"] == "discovery"
    attempt = reconstructed["attempts"][0]
    assert attempt["outcome"] == "retained"
    assert attempt["response"]["normalized_mime"] == "text/html"
    assert attempt["response"]["content_hash"]
    assert attempt["response"]["sighting_id"]


def test_a_duplicate_body_shares_an_artifact_and_never_a_sighting(catalog, transport):
    """SPEC 6.5. Two sources serving identical bytes are two observations."""
    first, second = canaries.CANARIES[0], canaries.CANARIES[1]
    shared = b"<html><body><p>identical bytes</p></body></html>"
    transport.serve_bytes(first.revision.endpoint_url, shared, "text/html")
    transport.serve_bytes(second.revision.endpoint_url, shared, "text/html")

    one = acquire(catalog, operation_for(catalog, first, 1), first.revision, transport)
    two = acquire(catalog, operation_for(catalog, second, 2), second.revision, transport)

    assert one.artifact_id == two.artifact_id
    assert one.sighting_id != two.sighting_id
    assert catalog.one("SELECT COUNT(*) AS n FROM artifacts")["n"] == 1
    assert catalog.one("SELECT COUNT(*) AS n FROM sightings")["n"] == 2


def test_content_that_tries_to_instruct_becomes_an_observation_about_the_source(
    catalog, transport
):
    canary = canaries.CANARIES[3]  # the injection fixture
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    assert record.retained
    assert record.instruction_observations >= 3

    standing = instruction.operational_standing(catalog, canary.revision.id)
    assert standing["instruction_attempts"][InstructionMarker.DIRECTIVE.value] >= 1
    assert standing["instruction_attempts"][InstructionMarker.AUTHORITY_CLAIM.value] >= 1
    # Operational standing and nothing else: there is no score here to raise.
    assert set(standing) == {
        "source_revision_id",
        "instruction_attempts",
        "attempts",
        "refused_attempts",
    }


def test_the_injected_instruction_changed_nothing_about_the_read(catalog, transport):
    """It asked to be treated as a verified primary record and was retained as
    what it is: a claimant page from the source that served it."""
    canary = canaries.CANARIES[3]
    acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    sighting = catalog.one("SELECT * FROM sightings")
    assert sighting["source_revision_id"] == canary.revision.id
    revision = catalog.one(
        "SELECT role, risk_floor FROM source_revisions WHERE id = ?", canary.revision.id
    )
    assert revision["role"] == "claimant"
    assert revision["risk_floor"] == "R1"


def test_a_source_that_may_not_be_retained_stays_a_lead(catalog, transport):
    canary = canaries.CANARIES[0]
    lead_only = canary.revision.__class__(
        **{**canary.revision.as_record(), "retention_policy": RetentionPolicy.LEAD_ONLY}
    )
    record = acquire(catalog, operation_for(catalog, canary), lead_only, transport)

    assert record.refusal is FetchRefusal.RETENTION_PROHIBITED
    assert record.artifact_id is None
    assert catalog.one("SELECT COUNT(*) AS n FROM artifacts")["n"] == 0
    # The attempt is still recorded: the read happened.
    assert catalog.one("SELECT COUNT(*) AS n FROM attempts")["n"] == 1


def test_a_refusal_is_recorded_as_a_fact_about_the_source(catalog, transport):
    canary = canaries.CANARIES[0]
    transport.serve(canary.revision.endpoint_url, Reply(status=429, headers={"Retry-After": "60"}))
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)

    assert record.refusal is FetchRefusal.RATE_LIMITED
    row = catalog.one("SELECT * FROM attempts WHERE id = ?", record.attempt_id)
    assert row["outcome"] == "refused"
    assert row["refusal_reason"] == "rate_limited"
    assert (
        catalog.one("SELECT state FROM operations WHERE id = ?", record.operation_id)["state"]
        == OperationState.QUARANTINED.value
    )


def test_an_error_and_a_refusal_are_different_terminal_states(catalog, transport):
    canary = canaries.CANARIES[0]
    transport.serve(canary.revision.endpoint_url, Reply(status=503, headers={"Content-Type": "text/html"}))
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    assert record.outcome is AttemptOutcome.ERROR
    assert (
        catalog.one("SELECT state FROM operations WHERE id = ?", record.operation_id)["state"]
        == OperationState.FAILED.value
    )


def test_a_retained_read_emits_one_outbox_event(catalog, transport):
    canary = canaries.CANARIES[0]
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    row = catalog.one("SELECT * FROM outbox WHERE consumed_at IS NULL")
    assert row["kind"] == "artifact_retained"
    assert row["subject"] == record.artifact_id


def test_a_crash_between_the_artifact_and_the_row_leaves_no_dangling_reference(
    catalog, transport, monkeypatch
):
    """The ordering obligation. The file may be orphaned; the row may not dangle."""
    canary = canaries.CANARIES[0]
    result = fetch(canary.revision.endpoint_url, transport)
    assert result.retained

    original = artifacts.record_artifact

    def crash(*args, **kwargs):
        original(*args, **kwargs)
        raise sqlite3.OperationalError("power loss between the file and the commit")

    monkeypatch.setattr(artifacts, "record_artifact", crash)
    with pytest.raises(sqlite3.OperationalError):
        acquire(
            catalog,
            operation_for(catalog, canary),
            canary.revision,
            transport,
            result=result,
        )

    # The bytes are on disk and nothing in the ledger claims them.
    assert artifacts.missing_artifacts(catalog) == ()
    assert len(artifacts.orphan_artifacts(catalog)) == 1
    assert catalog.one("SELECT COUNT(*) AS n FROM artifacts")["n"] == 0
    assert catalog.one("SELECT COUNT(*) AS n FROM responses")["n"] == 0
    assert catalog.one("SELECT COUNT(*) AS n FROM sightings")["n"] == 0


def test_the_retried_read_after_a_crash_completes_without_duplicating_bytes(
    catalog, transport, monkeypatch
):
    canary = canaries.CANARIES[0]
    result = fetch(canary.revision.endpoint_url, transport)
    original = artifacts.record_artifact

    def crash(*args, **kwargs):
        original(*args, **kwargs)
        raise sqlite3.OperationalError("power loss")

    monkeypatch.setattr(artifacts, "record_artifact", crash)
    with pytest.raises(sqlite3.OperationalError):
        acquire(catalog, operation_for(catalog, canary), canary.revision, transport, result=result)

    monkeypatch.setattr(artifacts, "record_artifact", original)
    record = acquire(
        catalog, operation_for(catalog, canary), canary.revision, transport, result=result
    )
    assert record.retained
    assert artifacts.orphan_artifacts(catalog) == ()
    assert artifacts.missing_artifacts(catalog) == ()


def test_a_response_or_sighting_cannot_be_rewritten(catalog, transport):
    canary = canaries.CANARIES[0]
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    for table, identifier in (("responses", record.response_id), ("sightings", record.sighting_id)):
        with pytest.raises(sqlite3.IntegrityError, match="immutable"), catalog.write() as connection:
            connection.execute(
                f"UPDATE {table} SET artifact_id = 'artifact:other' WHERE id = ?", (identifier,)
            )


def test_an_unretained_result_carries_no_body_into_the_ledger(catalog, transport):
    canary = canaries.CANARIES[0]
    record = acquire(
        catalog,
        operation_for(catalog, canary),
        canary.revision,
        transport,
        result=FetchResult(
            outcome=AttemptOutcome.REFUSED,
            url=canary.revision.endpoint_url,
            refusal=FetchRefusal.NON_PUBLIC_ADDRESS,
            detail="example -> 127.0.0.1",
        ),
    )
    assert record.artifact_id is None
    assert catalog.one("SELECT COUNT(*) AS n FROM artifacts")["n"] == 0
    assert list(catalog.artifact_root.rglob("*.partial")) == []
