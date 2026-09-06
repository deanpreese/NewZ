"""Task generation and the lifecycle a task moves through.

One task per required evidence lane per claim, deduplicated: a second open task
for the same question is not more effort, it is the same effort counted twice,
and it would make a backlog brake fire on its own bookkeeping.

The counterpart task is the one with a clock on it. `SPEC.md` section 5.2 makes
every claimant-led discovery mandate one, due within 72 hours, and pauses
discovery for the local day when counterparts are overdue or backed up. That
brake is what stops the system opening claims faster than it can close them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from newz.clock import stamp
from newz.control.audit import record as audit_record
from newz.domain.enums import (
    LIVE_TASK_STATES,
    TERMINAL_COMPETENT_STATES,
    TERMINAL_INCOMPLETE_STATES,
    ClaimKind,
    EvidenceLane,
    TaskState,
)
from newz.policy import lanes
from newz.store.db import Store

#: `SPEC.md` section 5.2.
COUNTERPART_DUE_HOURS = 72
COUNTERPART_BACKLOG_LIMIT = 12

TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.OPEN: frozenset({TaskState.SCHEDULED, TaskState.CANCELLED, TaskState.EXPIRED}),
    TaskState.SCHEDULED: frozenset(
        {TaskState.IN_PROGRESS, TaskState.BLOCKED, TaskState.CANCELLED, TaskState.EXPIRED}
    ),
    TaskState.IN_PROGRESS: frozenset(
        {
            TaskState.SATISFIED,
            TaskState.EXHAUSTED,
            TaskState.UNREACHABLE,
            TaskState.BLOCKED,
            TaskState.REFUSED,
            TaskState.CANCELLED,
            TaskState.EXPIRED,
        }
    ),
    # A blocked task returns to scheduled when the precondition clears; it is
    # not terminal, and treating it as one is how a source outage becomes a
    # permanent gap in the record.
    TaskState.BLOCKED: frozenset(
        {TaskState.SCHEDULED, TaskState.CANCELLED, TaskState.EXPIRED, TaskState.REFUSED}
    ),
}


class TaskTransitionRefused(Exception):
    """A move the lifecycle does not permit, named rather than silently allowed."""


@dataclass(frozen=True, slots=True)
class GeneratedTask:
    id: str
    lane: EvidenceLane
    due: str
    created: bool


def _due(now: datetime, lane: EvidenceLane) -> str:
    hours = COUNTERPART_DUE_HOURS if lane is EvidenceLane.INDEPENDENT_COUNTERPART else 24 * 14
    return stamp(now + timedelta(hours=hours))


def generate_tasks(
    store: Store,
    claim_id: str,
    claim_kind: ClaimKind,
    now: datetime,
    *,
    owner: str = "worker:evidence",
    reason: str = "required evidence lane",
    retry_budget: int = 2,
) -> tuple[GeneratedTask, ...]:
    """One task per required lane, skipping lanes that already have a live one."""
    required = sorted(lanes.required(claim_kind), key=lambda lane: lane.value)
    existing = {
        (row["lane"], row["state"])
        for row in store.query("SELECT lane, state FROM tasks WHERE claim_id = ?", claim_id)
    }
    live_lanes = {lane for lane, state in existing if TaskState(state) in LIVE_TASK_STATES}
    satisfied_lanes = {
        lane for lane, state in existing if TaskState(state) in TERMINAL_COMPETENT_STATES
    }

    generated: list[GeneratedTask] = []
    with store.write() as connection:
        for lane in required:
            if lane.value in live_lanes or lane.value in satisfied_lanes:
                generated.append(
                    GeneratedTask(id="", lane=lane, due="", created=False)
                )
                continue
            task_id = f"task:{claim_id.split(':')[-1]}-{lane.value}"
            due = _due(now, lane)
            connection.execute(
                "INSERT OR IGNORE INTO tasks (id, claim_id, lane, state, owner, reason, due, "
                "retry_budget, state_reason, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', datetime('now'))",
                (
                    task_id,
                    claim_id,
                    lane.value,
                    TaskState.OPEN.value,
                    owner,
                    reason,
                    due,
                    retry_budget,
                ),
            )
            generated.append(GeneratedTask(id=task_id, lane=lane, due=due, created=True))
    return tuple(generated)


def transition_task(
    store: Store,
    task_id: str,
    to: TaskState,
    reason: str = "",
    actor: str = "worker:evidence",
) -> TaskState:
    """Move a task, refusing a move the lifecycle does not allow.

    Terminal-incomplete states require a reason. `SPEC.md` section 9.2 surfaces a
    blocked lane with its reason on the claim card, and a refusal with no reason
    on it is exactly the thing that reads like an exhausted search.
    """
    row = store.one("SELECT * FROM tasks WHERE id = ?", task_id)
    if row is None:
        raise KeyError(task_id)
    current = TaskState(row["state"])

    if current in TERMINAL_COMPETENT_STATES | TERMINAL_INCOMPLETE_STATES:
        raise TaskTransitionRefused(f"{task_id} is already terminal ({current.value})")
    if to not in TRANSITIONS.get(current, frozenset()):
        raise TaskTransitionRefused(f"{task_id}: {current.value} -> {to.value} is not a transition")
    if to in TERMINAL_INCOMPLETE_STATES and not reason:
        raise TaskTransitionRefused(
            f"{to.value} records why: a lane that did not search must say so on the card"
        )

    with store.write() as connection:
        connection.execute(
            "UPDATE tasks SET state = ?, state_reason = ? WHERE id = ?",
            (to.value, reason, task_id),
        )
        if to in TERMINAL_INCOMPLETE_STATES:
            audit_record(
                connection,
                actor=actor,
                action="task_terminal_incomplete",
                target=task_id,
                reason=reason,
                preimage=current.value,
                result=to.value,
                channel="command" if to is TaskState.CANCELLED else "system",
            )
    return to


def record_search(
    store: Store,
    task_id: str,
    *,
    expected_record: str,
    repository: str,
    query: str,
    time_window: str,
    searched_scope: str,
) -> None:
    """What was sought and where, without which absence establishes nothing."""
    with store.write() as connection:
        connection.execute(
            "UPDATE tasks SET expected_record = ?, repository = ?, query = ?, time_window = ?, "
            "searched_scope = ? WHERE id = ?",
            (expected_record, repository, query, time_window, searched_scope, task_id),
        )


def open_counterparts(store: Store) -> tuple[str, ...]:
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM tasks WHERE lane = ? AND state IN "
            f"({','.join('?' * len(LIVE_TASK_STATES))}) ORDER BY id",
            EvidenceLane.INDEPENDENT_COUNTERPART.value,
            *sorted(state.value for state in LIVE_TASK_STATES),
        )
    )


def overdue_counterparts(store: Store, now: datetime) -> tuple[str, ...]:
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM tasks WHERE lane = ? AND due <= ? AND state IN "
            f"({','.join('?' * len(LIVE_TASK_STATES))}) ORDER BY id",
            EvidenceLane.INDEPENDENT_COUNTERPART.value,
            stamp(now),
            *sorted(state.value for state in LIVE_TASK_STATES),
        )
    )


def expirable(store: Store, now: datetime) -> tuple[str, ...]:
    """Live tasks whose due time has passed.

    Expiry is offered rather than applied. A sweep that expired tasks the moment
    they came due would clear the counterpart backlog by declaring it over, and
    the brake in `discovery_brake` — which fires on live overdue counterparts —
    would then never engage. Deciding to give up on a question is a decision;
    this only says which questions are waiting on one.
    """
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM tasks WHERE due <= ? AND state IN "
            f"({','.join('?' * len(LIVE_TASK_STATES))}) ORDER BY id",
            stamp(now),
            *sorted(state.value for state in LIVE_TASK_STATES),
        )
    )


@dataclass(frozen=True, slots=True)
class DiscoveryBrake:
    engaged: bool
    reason: str = ""
    open_counterparts: int = 0
    overdue: tuple[str, ...] = ()


def discovery_brake(store: Store, now: datetime) -> DiscoveryBrake:
    """Whether discovery is paused for the local day, and why.

    Two conditions, and they say different things. A backlog means verification
    is not keeping up; an overdue counterpart means one particular claim has been
    left half-investigated, which is worse and fires on a single task.
    """
    overdue = overdue_counterparts(store, now)
    if overdue:
        return DiscoveryBrake(
            True,
            f"{len(overdue)} counterpart task(s) overdue",
            len(open_counterparts(store)),
            overdue,
        )
    backlog = open_counterparts(store)
    if len(backlog) > COUNTERPART_BACKLOG_LIMIT:
        return DiscoveryBrake(
            True,
            f"{len(backlog)} open counterpart tasks exceeds {COUNTERPART_BACKLOG_LIMIT}",
            len(backlog),
        )
    return DiscoveryBrake(False, "", len(backlog))
