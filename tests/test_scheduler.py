"""Reservations, lanes, leases, and the ceilings.

The concurrency tests use real threads against real connections to the same
file. A busy-timeout that is only asserted in a comment is not a busy-timeout.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from newz.control.budget import DailyBudget, availability
from newz.control.scheduler import (
    ReservationRefused,
    claim,
    finish,
    reclaimable,
    reserve,
)
from newz.domain.enums import (
    AttemptOutcome,
    FetchRefusal,
    OperationKind,
    OperationState,
    ReadLane,
)
from newz.store.db import open_store
from tests import canaries

DAY = "2026-09-05"
REVISION = "srcrev:harbour-uap-1"


def make(store, index: int, lane: ReadLane = ReadLane.DISCOVERY, day: str = DAY, **kwargs):
    return reserve(
        store,
        operation_id=f"operation:o{index}",
        reservation_id=f"reservation:r{index}",
        kind=OperationKind.FETCH,
        lane=lane,
        source_revision_id=kwargs.pop("revision", REVISION),
        epoch_id="epoch:1",
        policy_version="1.0.0",
        intent=f"read {index}",
        idempotency_key=kwargs.pop("key", f"{day}:{lane.value}:{index}"),
        local_day=day,
        **kwargs,
    )


def test_a_reservation_is_taken_before_anything_is_fetched(catalog):
    operation = make(catalog, 1)
    assert operation.state is OperationState.RESERVED
    row = catalog.one("SELECT * FROM reservations WHERE operation_id = ?", operation.id)
    assert row["lane"] == "discovery"
    assert row["borrowed_from"] is None


def test_the_same_idempotency_key_returns_the_same_operation_and_costs_nothing(catalog):
    first = make(catalog, 1)
    second = make(catalog, 2, key=f"{DAY}:discovery:1")
    assert second.id == first.id
    assert catalog.one("SELECT COUNT(*) AS n FROM reservations")["n"] == 1


def test_a_lane_cannot_exceed_its_daily_capacity(catalog):
    for index in range(3):
        make(catalog, index, ReadLane.DISCOVERY)
    with pytest.raises(ReservationRefused) as raised:
        make(catalog, 99, ReadLane.DISCOVERY)
    assert raised.value.refusal is FetchRefusal.BUDGET_EXHAUSTED


def test_discovery_never_borrows_from_the_protected_reserve(catalog):
    for index in range(3):
        make(catalog, index, ReadLane.DISCOVERY)
    # Verification and correction are both untouched and both unavailable to it.
    used = {ReadLane.DISCOVERY: 3}
    assert not availability(ReadLane.DISCOVERY, used, DailyBudget()).available
    with pytest.raises(ReservationRefused):
        make(catalog, 100, ReadLane.DISCOVERY)


def test_correction_capacity_may_serve_verification_within_the_same_day(catalog):
    for index in range(5):
        make(catalog, index, ReadLane.VERIFICATION)
    borrowed = make(catalog, 5, ReadLane.VERIFICATION)
    row = catalog.one("SELECT * FROM reservations WHERE operation_id = ?", borrowed.id)
    assert row["borrowed_from"] == "correction"
    assert borrowed.borrowed_from is ReadLane.CORRECTION


def test_verification_never_returns_capacity_to_discovery(catalog):
    """The borrow runs one way, and the day's total still holds."""
    for index in range(3):
        make(catalog, index, ReadLane.DISCOVERY)
    used = {ReadLane.DISCOVERY: 3, ReadLane.VERIFICATION: 0}
    assert availability(ReadLane.DISCOVERY, used, DailyBudget()).borrowable == 0


def test_the_whole_day_is_ten_reads_and_not_one_more(catalog):
    taken = 0
    for lane, capacity in (
        (ReadLane.DISCOVERY, 3),
        (ReadLane.VERIFICATION, 5),
        (ReadLane.CORRECTION, 2),
    ):
        for index in range(capacity):
            make(catalog, f"{lane.value}-{index}", lane)
            taken += 1
    assert taken == 10
    for lane in ReadLane:
        with pytest.raises(ReservationRefused):
            make(catalog, f"{lane.value}-over", lane)


def test_a_new_local_day_restores_capacity(catalog):
    for index in range(3):
        make(catalog, index, ReadLane.DISCOVERY)
    tomorrow = make(catalog, 4, ReadLane.DISCOVERY, day="2026-09-06")
    assert tomorrow.state is OperationState.RESERVED


def test_a_source_outside_the_epoch_cannot_be_reserved(catalog):
    canaries.install(catalog)
    with catalog.write() as connection:
        connection.execute(
            "INSERT INTO source_revisions (id, source_id, revision, endpoint_url, delivery_kind, "
            "role, declared_scope, risk_floor, retention_policy, expected_mime, recorded_at) "
            "VALUES ('srcrev:outside-1', 'source:harbour-uap', 2, 'https://x.example/', 'page', "
            "'claimant', 'scope', 'R1', 'full_text', 'text/html', datetime('now'))"
        )
    with pytest.raises(ReservationRefused) as raised:
        make(catalog, 1, revision="srcrev:outside-1")
    assert raised.value.refusal is FetchRefusal.HOST_NOT_IN_CATALOG


def test_a_lease_is_exclusive_until_it_expires(catalog):
    operation = make(catalog, 1)
    now = datetime(2026, 9, 5, 12, 0, 0)
    assert claim(catalog, operation.id, "worker:a", now, lease_seconds=300)
    assert not claim(catalog, operation.id, "worker:b", now + timedelta(seconds=60))
    assert claim(catalog, operation.id, "worker:b", now + timedelta(seconds=400))


def test_an_expired_lease_reclaims_a_killed_workers_operation(catalog):
    operation = make(catalog, 1)
    now = datetime(2026, 9, 5, 12, 0, 0)
    claim(catalog, operation.id, "worker:a", now, lease_seconds=60)
    assert reclaimable(catalog, now + timedelta(seconds=30)) == ()
    assert reclaimable(catalog, now + timedelta(seconds=90)) == (operation.id,)


def test_a_terminal_operation_never_moves_again(catalog):
    operation = make(catalog, 1)
    finish(catalog, operation.id, OperationState.SUCCEEDED, "hash")
    with pytest.raises(ValueError, match="already terminal"):
        finish(catalog, operation.id, OperationState.FAILED, "no")
    assert not claim(catalog, operation.id, "worker:a", datetime(2026, 9, 5, 12, 0, 0))


def test_a_non_terminal_state_cannot_be_recorded_as_terminal(catalog):
    operation = make(catalog, 1)
    with pytest.raises(ValueError, match="not a terminal state"):
        finish(catalog, operation.id, OperationState.LEASED, "no")


def test_concurrent_writers_do_not_oversell_the_day(tmp_path, catalog):
    """Ten threads, three discovery slots, one file. Three win."""
    taken: list[str] = []
    refused: list[FetchRefusal] = []
    barrier = threading.Barrier(10)
    lock = threading.Lock()

    def worker(index: int) -> None:
        connection = open_store(catalog.path, catalog.artifact_root)
        barrier.wait()
        try:
            operation = make(connection, index)
        except ReservationRefused as error:
            with lock:
                refused.append(error.refusal)
        else:
            with lock:
                taken.append(operation.id)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(taken) == 3
    assert len(refused) == 7
    assert set(refused) == {FetchRefusal.BUDGET_EXHAUSTED}
    assert catalog.one("SELECT COUNT(*) AS n FROM reservations")["n"] == 3


def test_concurrent_writers_with_one_key_produce_one_operation(catalog):
    """The idempotent path under contention: one operation, one reservation."""
    results: list[str] = []
    barrier = threading.Barrier(6)
    lock = threading.Lock()

    def worker(index: int) -> None:
        connection = open_store(catalog.path, catalog.artifact_root)
        barrier.wait()
        operation = make(connection, index, key="one-key")
        with lock:
            results.append(operation.id)
        connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(set(results)) == 1
    assert catalog.one("SELECT COUNT(*) AS n FROM operations")["n"] == 1


# ---------------------------------------------------------------------------
# Retry, backoff, and pacing
# ---------------------------------------------------------------------------


def test_a_policy_refusal_is_not_retried(catalog):
    """Most refusals will not become permissions by being asked again."""
    from newz.control.retry import RetryPolicy

    policy = RetryPolicy()
    for refusal in FetchRefusal:
        expected = refusal in {FetchRefusal.RATE_LIMITED, FetchRefusal.TIMEOUT}
        assert policy.is_retryable(AttemptOutcome.REFUSED, refusal) is expected, refusal


def test_an_error_is_retried_and_a_retained_read_is_not(catalog):
    from newz.control.retry import RetryPolicy

    policy = RetryPolicy()
    assert policy.is_retryable(AttemptOutcome.ERROR, None)
    assert not policy.is_retryable(AttemptOutcome.RETAINED, None)


def test_backoff_grows_deterministically_and_is_capped():
    from newz.control.retry import RetryPolicy

    policy = RetryPolicy(base_delay_seconds=60, multiplier=4, max_delay_seconds=3_600)
    assert [policy.delay_after(n) for n in (1, 2, 3, 4, 5)] == [60, 240, 960, 3600, 3600]
    assert policy.delay_after(2) == policy.delay_after(2)
    assert policy.due_at(datetime(2026, 9, 5, 12, 0, 0), 1) == datetime(2026, 9, 5, 12, 1, 0)
    with pytest.raises(ValueError, match="counted from 1"):
        policy.delay_after(0)


def test_the_retry_budget_is_spent_rather_than_endless():
    from newz.control.retry import RetryPolicy

    policy = RetryPolicy(max_attempts=3)
    assert not policy.exhausted(2)
    assert policy.exhausted(3)


def test_a_host_is_not_read_twice_inside_the_politeness_floor(catalog, transport):
    from newz.acquisition.run import acquire
    from newz.control.retry import RetryPolicy, pacing_refusal
    from tests import canaries

    canary = canaries.CANARIES[0]
    operation = make(catalog, 1)
    acquire(catalog, operation, canary.revision, transport)

    # Asked the way the acquisition path asks it: with the local wall clock.
    # An earlier version of this test read the recorded UTC timestamp back and
    # passed that in, which compared UTC against UTC and so agreed with the
    # floor in every timezone -- including the ones where the floor was not
    # working at all.
    now = datetime.now()
    host = "harbour.example"
    assert pacing_refusal(catalog, host, now, RetryPolicy()) is FetchRefusal.RATE_LIMITED
    assert pacing_refusal(catalog, host, now + timedelta(seconds=31), RetryPolicy()) is None
    assert pacing_refusal(catalog, "other.example", now, RetryPolicy()) is None


def test_the_politeness_floor_does_not_depend_on_the_host_timezone(catalog, transport):
    """The ledger stamps UTC; a caller says `datetime.now()`, which is local.

    Subtracting one from the other yields the UTC offset, and the failure is
    invisible from inside a single timezone: east of Greenwich elapsed time came
    out hours large and the floor paced nothing, west of it elapsed time came
    out negative and the floor refused every read forever. Both read as a
    working floor from the outside.
    """
    from newz.acquisition.run import acquire
    from newz.clock import as_utc
    from newz.control.retry import RetryPolicy, last_attempt_at, pacing_refusal
    from tests import canaries

    acquire(catalog, make(catalog, 1), canaries.CANARIES[0].revision, transport)
    recorded = last_attempt_at(catalog, "harbour.example")
    assert recorded.tzinfo is UTC, "the ledger's timestamps are UTC and say so"

    naive_local = datetime.now()
    aware_utc = datetime.now(UTC)
    assert as_utc(naive_local) == pytest.approx(aware_utc, abs=timedelta(seconds=2))
    assert pacing_refusal(catalog, "harbour.example", naive_local, RetryPolicy()) is (
        pacing_refusal(catalog, "harbour.example", aware_utc, RetryPolicy())
    )


def test_a_clock_that_went_backwards_is_not_a_licence_to_read_again(catalog, transport):
    from newz.acquisition.run import acquire
    from newz.control.retry import RetryPolicy, pacing_refusal
    from tests import canaries

    canary = canaries.CANARIES[0]
    acquire(catalog, make(catalog, 1), canary.revision, transport)
    assert (
        pacing_refusal(
            catalog, "harbour.example", datetime.now() - timedelta(hours=1), RetryPolicy()
        )
        is FetchRefusal.RATE_LIMITED
    )
