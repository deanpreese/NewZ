"""Gate 1: every byte is attributable to an authorized operation.

Four offline canary sources — two HTML, one PDF, and one attribution-only
claimant source — through one scheduler. What the gate asks for is that the
traces reconstruct and the hashes hold, and that failure can neither exceed the
budget nor leave a state nobody can name.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

import pytest

from newz.acquisition import artifacts
from newz.acquisition.run import acquire, trace
from newz.control.scheduler import ReservationRefused, claim, reclaimable
from newz.domain.enums import (
    TERMINAL_OPERATION_STATES,
    AttemptOutcome,
    OperationState,
    ReadLane,
    SourceRole,
)
from newz.store.backup import verify
from tests import canaries
from tests.canaries import CORPUS
from tests.test_acquisition import operation_for
from tests.transport import Reply

LANES = (ReadLane.DISCOVERY, ReadLane.DISCOVERY, ReadLane.DISCOVERY, ReadLane.VERIFICATION)
NOW = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def gate_run(catalog, transport):
    """The four canaries, each reserved, leased, fetched and recorded."""
    records = []
    for index, canary in enumerate(canaries.CANARIES):
        operation = operation_for(catalog, canary, index, LANES[index])
        assert claim(catalog, operation.id, f"worker:{index}", NOW)
        records.append(acquire(catalog, operation, canary.revision, transport))
    return catalog, records


def test_the_canary_set_is_what_the_gate_names():
    """Two HTML, one PDF, and one attribution-only source."""
    by_mime: dict[str, int] = {}
    for canary in canaries.CANARIES:
        by_mime[canary.revision.expected_mime] = by_mime.get(canary.revision.expected_mime, 0) + 1
    assert by_mime == {"text/html": 3, "application/pdf": 1}
    claimants = [c for c in canaries.CANARIES if c.revision.role is SourceRole.CLAIMANT]
    assert len(claimants) == 2
    # Two of the HTML sources are ordinary pages; the attribution-only one is a
    # claimant, which under the Phase 0 matrix can establish attribution alone.
    assert any(c.revision.role is SourceRole.FIRSTHAND_WITNESS for c in canaries.CANARIES)
    assert any(c.revision.role is SourceRole.PRIMARY_RECORD for c in canaries.CANARIES)


def test_all_four_are_retained_through_one_scheduler(gate_run):
    store, records = gate_run
    assert all(record.retained for record in records)
    assert store.one("SELECT COUNT(*) AS n FROM operations")["n"] == 4
    assert store.one("SELECT COUNT(*) AS n FROM reservations")["n"] == 4
    assert store.one("SELECT COUNT(*) AS n FROM sightings")["n"] == 4


def test_every_artifact_hash_is_the_hash_of_the_source_bytes(gate_run):
    store, records = gate_run
    for canary, record in zip(canaries.CANARIES, records, strict=True):
        expected = hashlib.sha256((CORPUS / canary.fixture).read_bytes()).hexdigest()
        assert record.content_hash == expected
        row = store.one("SELECT stored_path FROM artifacts WHERE content_hash = ?", expected)
        stored = (store.artifact_root / row["stored_path"]).read_bytes()
        assert hashlib.sha256(stored).hexdigest() == expected


def test_every_trace_reconstructs_from_the_ledger(gate_run):
    store, _ = gate_run
    for index, canary in enumerate(canaries.CANARIES):
        reconstructed = trace(store, f"operation:o{index}")
        operation = reconstructed["operation"]
        assert operation["state"] == OperationState.SUCCEEDED.value
        assert operation["source_revision_id"] == canary.revision.id
        assert operation["epoch_id"] == "epoch:1"
        assert operation["policy_version"] == "1.0.0"
        assert operation["intent"]
        assert reconstructed["reservation"]["lane"] == LANES[index].value

        attempt = reconstructed["attempts"][0]
        assert attempt["url"] == canary.revision.endpoint_url
        assert attempt["outcome"] == AttemptOutcome.RETAINED.value
        response = attempt["response"]
        assert response["content_hash"]
        assert response["artifact_id"] and response["sighting_id"]


def test_no_operation_is_left_in_an_unnameable_state(gate_run):
    store, _ = gate_run
    states = {row["state"] for row in store.query("SELECT DISTINCT state FROM operations")}
    assert states <= {state.value for state in TERMINAL_OPERATION_STATES}
    assert reclaimable(store, NOW) == ()
    assert store.one(
        "SELECT COUNT(*) AS n FROM operations WHERE lease_owner IS NOT NULL"
    )["n"] == 0


def test_the_store_verifies_after_the_run(gate_run):
    store, _ = gate_run
    report = verify(store)
    assert report.ok, report.as_record()
    assert artifacts.orphan_artifacts(store) == ()
    assert artifacts.missing_artifacts(store) == ()


def test_failure_cannot_exceed_the_budget(catalog, transport):
    """Every canary fails, every failure is recorded, and the day still stops at ten."""
    for canary in canaries.CANARIES:
        transport.serve(canary.revision.endpoint_url, Reply(status=503, headers={"Content-Type": "text/html"}))

    taken = 0
    refused = 0
    for index in range(20):
        canary = canaries.CANARIES[index % len(canaries.CANARIES)]
        lane = (ReadLane.DISCOVERY, ReadLane.VERIFICATION, ReadLane.CORRECTION)[index % 3]
        try:
            operation = operation_for(catalog, canary, index, lane)
        except ReservationRefused:
            refused += 1
            continue
        acquire(catalog, operation, canary.revision, transport)
        taken += 1

    assert taken == 10
    assert refused == 10
    assert catalog.one("SELECT COUNT(*) AS n FROM attempts")["n"] == 10
    assert catalog.one("SELECT COUNT(*) AS n FROM artifacts")["n"] == 0

    # Every operation is terminal and named. Two protections stack here: the
    # budget stops the eleventh read, and the per-host pacing floor turns most
    # of the ten into refusals before the socket, so a failing source is not
    # hammered inside one local day.
    by_state = {
        row["state"]: row["n"]
        for row in catalog.query("SELECT state, COUNT(*) AS n FROM operations GROUP BY state")
    }
    assert set(by_state) <= {OperationState.FAILED.value, OperationState.QUARANTINED.value}
    assert sum(by_state.values()) == 10
    assert by_state[OperationState.FAILED.value] >= 1
    assert by_state.get(OperationState.QUARANTINED.value, 0) >= 1


def test_a_worker_killed_mid_operation_leaves_the_operation_reclaimable(catalog, transport):
    """Ambiguity is bounded by the lease rather than by the worker's cooperation."""
    canary = canaries.CANARIES[0]
    operation = operation_for(catalog, canary, 1)
    assert claim(catalog, operation.id, "worker:doomed", NOW, lease_seconds=60)
    # The worker dies here: no terminal state, no attempt row.
    assert catalog.one("SELECT COUNT(*) AS n FROM attempts")["n"] == 0

    from datetime import timedelta

    assert reclaimable(catalog, NOW + timedelta(seconds=90)) == (operation.id,)
    assert claim(catalog, operation.id, "worker:next", NOW + timedelta(seconds=90))
    record = acquire(catalog, operation, canary.revision, transport)
    assert record.retained
    # The reclaim cost no extra slot: the reservation was taken once.
    assert catalog.one("SELECT COUNT(*) AS n FROM reservations")["n"] == 1
