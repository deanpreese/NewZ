"""One scheduler, one operation ledger.

`SPEC.md` section 6 item 1: all network acquisition passes through here, and
every attempt receives an intent, a budget reservation, a source revision, a
policy epoch, and a terminal outcome. Nothing below this module may reach the
network on its own account, and the reservation is taken *before* the fetch, so
a crash between the two costs a slot rather than losing the record of an act.

Leases are how a crashed worker's operation comes back. A lease is a claim with
an expiry: when it passes, the operation is reclaimable by anyone, and the
reclaim is recorded. That is deliberately not a heartbeat — a worker that has
stopped cannot be relied on to say so.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from newz.clock import stamp
from newz.control.budget import (
    MONTHLY_REQUEST_CEILING,
    MONTHLY_STORAGE_CEILING_BYTES,
    DailyBudget,
    availability,
)
from newz.control.concentration import record_refusal, would_exceed
from newz.domain.enums import (
    TERMINAL_OPERATION_STATES,
    FetchRefusal,
    OperationKind,
    OperationState,
    ReadLane,
)


class ReservationRefused(Exception):
    """The budget said no. Carries the reason so the refusal is recordable."""

    def __init__(self, refusal: FetchRefusal, detail: str = "") -> None:
        super().__init__(f"{refusal.value}: {detail}" if detail else refusal.value)
        self.refusal = refusal
        self.detail = detail


@dataclass(frozen=True, slots=True)
class Operation:
    id: str
    kind: OperationKind
    lane: ReadLane
    source_revision_id: str
    epoch_id: str
    policy_version: str
    intent: str
    idempotency_key: str
    state: OperationState
    local_day: str
    borrowed_from: ReadLane | None = None


def _used_by_lane(store, local_day: str) -> dict[ReadLane, int]:
    """Reservations are what consume capacity, not completions.

    A read that was reserved and then failed still cost the day a slot: the far
    side was contacted. Counting completions instead would let a failing source
    be retried without limit.
    """
    used: dict[ReadLane, int] = {}
    for row in store.query(
        "SELECT lane, borrowed_from, COUNT(*) AS n FROM reservations "
        "WHERE local_day = ? GROUP BY lane, borrowed_from",
        local_day,
    ):
        lane = ReadLane(row["borrowed_from"] or row["lane"])
        used[lane] = used.get(lane, 0) + row["n"]
    return used


def month_of(local_day: str) -> str:
    return local_day[:7]


def requests_this_month(store, local_day: str) -> int:
    row = store.one(
        "SELECT COUNT(*) AS n FROM attempts WHERE substr(started_at, 1, 7) = ?",
        month_of(local_day),
    )
    return row["n"] if row else 0


def stored_bytes_this_month(store, local_day: str) -> int:
    row = store.one(
        "SELECT COALESCE(SUM(byte_size), 0) AS n FROM artifacts "
        "WHERE substr(stored_at, 1, 7) = ?",
        month_of(local_day),
    )
    return row["n"] if row else 0


def reserve(
    store,
    *,
    operation_id: str,
    reservation_id: str,
    kind: OperationKind,
    lane: ReadLane,
    source_revision_id: str,
    epoch_id: str,
    policy_version: str,
    intent: str,
    idempotency_key: str,
    local_day: str,
    budget: DailyBudget | None = None,
    discovery_paused: str = "",
) -> Operation:
    """Take a slot, or refuse with a reason.

    Idempotent by key: asking twice for the same operation returns the operation
    that already exists and consumes nothing. That is what makes a retry after an
    ambiguous crash safe.

    `discovery_paused` carries the counterpart brake of `SPEC.md` section 5.2,
    computed by the caller rather than read from here. The scheduler owns lanes
    and reservations; task state belongs to the research manager, and a
    scheduler that reached into it would own both.
    """
    budget = budget or DailyBudget()

    existing = store.one("SELECT * FROM operations WHERE idempotency_key = ?", idempotency_key)
    if existing is not None:
        reservation = store.one(
            "SELECT borrowed_from FROM reservations WHERE operation_id = ?", existing["id"]
        )
        return Operation(
            id=existing["id"],
            kind=OperationKind(existing["kind"]),
            lane=ReadLane(existing["lane"]),
            source_revision_id=existing["source_revision_id"],
            epoch_id=existing["epoch_id"],
            policy_version=existing["policy_version"],
            intent=existing["intent"],
            idempotency_key=existing["idempotency_key"],
            state=OperationState(existing["state"]),
            local_day=existing["local_day"],
            borrowed_from=(
                ReadLane(reservation["borrowed_from"])
                if reservation and reservation["borrowed_from"]
                else None
            ),
        )

    def refuse(reason: FetchRefusal, detail: str) -> ReservationRefused:
        """Write the refusal down, then raise it.

        `FetchRefusal` says refusals are recorded and never merely returned, and
        for fetches that was true; reservations only ever raised. A diet
        repeatedly turned away at a ceiling then read exactly like a diet nobody
        had asked about, which is the shape of absence this system exists to
        avoid producing.
        """
        record_refusal(
            store,
            idempotency_key=idempotency_key,
            source_revision_id=source_revision_id,
            lane=lane.value,
            refusal=reason.value,
            detail=detail,
            local_day=local_day,
        )
        return ReservationRefused(reason, detail)

    if store.one(
        "SELECT 1 FROM diet_epoch_sources WHERE epoch_id = ? AND source_revision_id = ?",
        epoch_id,
        source_revision_id,
    ) is None:
        raise refuse(
            FetchRefusal.HOST_NOT_IN_CATALOG,
            f"{source_revision_id} is not enabled in {epoch_id}",
        )

    if lane is ReadLane.DISCOVERY and discovery_paused:
        raise refuse(FetchRefusal.DISCOVERY_PAUSED, discovery_paused)

    if requests_this_month(store, local_day) >= MONTHLY_REQUEST_CEILING:
        raise refuse(FetchRefusal.REQUEST_CEILING, month_of(local_day))
    if stored_bytes_this_month(store, local_day) >= MONTHLY_STORAGE_CEILING_BYTES:
        raise refuse(FetchRefusal.STORAGE_CEILING, month_of(local_day))

    # SPEC 5.1: enforced here rather than after the fact, because a read whose
    # retention would breach the cap has already been taken by the time a report
    # could notice it, and the cap may not answer that by discarding evidence.
    concentrated = would_exceed(store, source_revision_id, local_day)
    if concentrated:
        raise refuse(FetchRefusal.PUBLISHER_CONCENTRATION, concentrated)

    try:
        with store.write() as connection:
            # Re-read inside the write lock: availability computed outside it is
            # a decision made against a state that may already have moved.
            used = _used_by_lane(store, local_day)
            lane_state = availability(lane, used, budget)
            if not lane_state.available:
                raise ReservationRefused(
                    FetchRefusal.BUDGET_EXHAUSTED,
                    f"{lane.value} on {local_day}",
                )
            borrowed_from = None if lane_state.own_remaining > 0 else lane_state.borrowed_from

            connection.execute(
                "INSERT INTO operations (id, kind, lane, source_revision_id, epoch_id, "
                "policy_version, intent, idempotency_key, state, local_day, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    operation_id,
                    kind.value,
                    lane.value,
                    source_revision_id,
                    epoch_id,
                    policy_version,
                    intent,
                    idempotency_key,
                    OperationState.RESERVED.value,
                    local_day,
                ),
            )
            connection.execute(
                "INSERT INTO reservations (id, operation_id, local_day, lane, borrowed_from, "
                "created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (
                    reservation_id,
                    operation_id,
                    local_day,
                    lane.value,
                    borrowed_from.value if borrowed_from else None,
                ),
            )
    except ReservationRefused as refusal:
        # The budget decision is made under the write lock, on purpose, but a
        # refusal recorded inside that lock would roll back with the transaction
        # it refused — the record would vanish along with the thing it recorded.
        record_refusal(
            store,
            idempotency_key=idempotency_key,
            source_revision_id=source_revision_id,
            lane=lane.value,
            refusal=refusal.refusal.value,
            detail=refusal.detail,
            local_day=local_day,
        )
        raise
    except sqlite3.IntegrityError as error:
        # Another writer took the same key between our read and our lock.
        if "idempotency_key" in str(error):
            return reserve(
                store,
                operation_id=operation_id,
                reservation_id=reservation_id,
                kind=kind,
                lane=lane,
                source_revision_id=source_revision_id,
                epoch_id=epoch_id,
                policy_version=policy_version,
                intent=intent,
                idempotency_key=idempotency_key,
                local_day=local_day,
                budget=budget,
            )
        raise

    return Operation(
        id=operation_id,
        kind=kind,
        lane=lane,
        source_revision_id=source_revision_id,
        epoch_id=epoch_id,
        policy_version=policy_version,
        intent=intent,
        idempotency_key=idempotency_key,
        state=OperationState.RESERVED,
        local_day=local_day,
        borrowed_from=borrowed_from,
    )


def claim(store, operation_id: str, owner: str, now: datetime, lease_seconds: int = 300) -> bool:
    """Take the lease, if it is free or expired. Returns whether it was taken."""
    expires = stamp(now + timedelta(seconds=lease_seconds))
    with store.write() as connection:
        cursor = connection.execute(
            "UPDATE operations SET state = ?, lease_owner = ?, lease_expires_at = ? "
            "WHERE id = ? AND state IN (?, ?) "
            "AND (lease_expires_at IS NULL OR lease_expires_at <= ?)",
            (
                OperationState.LEASED.value,
                owner,
                expires,
                operation_id,
                OperationState.RESERVED.value,
                OperationState.LEASED.value,
                stamp(now),
            ),
        )
        return cursor.rowcount == 1


def reclaimable(store, now: datetime) -> tuple[str, ...]:
    """Operations whose worker stopped without saying so."""
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM operations WHERE state = ? AND lease_expires_at <= ? ORDER BY id",
            OperationState.LEASED.value,
            stamp(now),
        )
    )


def finish(store, operation_id: str, state: OperationState, outcome: str) -> None:
    """Record a terminal state. A terminal operation never moves again."""
    if state not in TERMINAL_OPERATION_STATES:
        raise ValueError(f"{state.value} is not a terminal state")
    with store.write() as connection:
        cursor = connection.execute(
            "UPDATE operations SET state = ?, outcome = ?, terminal_at = datetime('now'), "
            "lease_owner = NULL, lease_expires_at = NULL "
            f"WHERE id = ? AND state NOT IN ({','.join('?' * len(TERMINAL_OPERATION_STATES))})",
            (
                state.value,
                outcome,
                operation_id,
                *sorted(s.value for s in TERMINAL_OPERATION_STATES),
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError(f"{operation_id} is already terminal or does not exist")
