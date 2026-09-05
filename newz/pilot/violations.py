"""Pause conditions, and what it takes to start again.

`PLAN.md` Phase 5 lists seven conditions that pause the pilot, and then does the
thing that makes the gate countable: it says what a pause costs. Dates during a
pause are not eligible dates. Resumption requires a recorded cause, a fix, and a
**permanent** regression fixture — which is the pilot instance of the correction
requirement in `SPEC.md` section 13, not a rule that expires with the pilot.

And a fix that changes evidence, promotion, risk or publication behaviour resets
the route-exercise requirement: all twenty routes must be exercised again under
the new code version. Eligible dates and retained reads accumulated before the
fix are kept. The distinction between a fix that resets and one that does not is
recorded rather than argued, because a project counting down to thirty days has
every incentive to argue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from newz.store.db import Store
from newz.version import CODE_VERSION

#: `PLAN.md` Phase 5. Each one pauses acquisition when it fires.
PAUSE_CONDITIONS = (
    "claimant_only_factual_promotion",
    "false_independence_count",
    "missing_artifact_or_span_on_admitted_edge",
    "r3_or_r4_publication_path_violation",
    "unbounded_or_unauthorized_fetch",
    "failure_to_invalidate_a_dependent_card",
    "critical_backup_or_restore_failure",
)

#: The conditions whose fix necessarily changes how evidence is decided, so
#: every route must be exercised again under the new code.
RESET_CONDITIONS = frozenset(
    {
        "claimant_only_factual_promotion",
        "false_independence_count",
        "missing_artifact_or_span_on_admitted_edge",
        "r3_or_r4_publication_path_violation",
        "failure_to_invalidate_a_dependent_card",
    }
)


@dataclass(frozen=True, slots=True)
class Violation:
    id: str
    condition: str
    detail: str
    detected_at: str
    resolved: bool
    resets_routes: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "condition": self.condition,
            "detail": self.detail,
            "detected_at": self.detected_at,
            "resolved": self.resolved,
            "resets_routes": self.resets_routes,
        }


def record_violation(
    store: Store, *, violation_id: str, condition: str, detail: str, detected_at: str
) -> Violation:
    """Record a pause condition firing, and pause by recording it.

    Entry into lockdown is separate and automatic; this is the pilot's own
    accounting, which survives the pause and outlives it.
    """
    if condition not in PAUSE_CONDITIONS:
        raise ValueError(f"a pause condition is one of {list(PAUSE_CONDITIONS)}")
    resets = condition in RESET_CONDITIONS
    with store.write() as connection:
        connection.execute(
            "INSERT INTO violations (id, condition, detail, detected_at, resets_routes) "
            "VALUES (?, ?, ?, ?, ?)",
            (violation_id, condition, detail, detected_at, int(resets)),
        )
    return Violation(violation_id, condition, detail, detected_at, False, resets)


def resolve_violation(
    store: Store, violation_id: str, *, cause: str, fix: str, fixture: str, resolved_at: str
) -> None:
    """Resume, which takes three things and not one.

    A cause without a fix is an explanation. A fix without a fixture is a
    promise. `SPEC.md` section 13 makes the fixture permanent, so the next
    occurrence of this failure is a test failure rather than a discovery.
    """
    missing = [
        name for name, value in (("cause", cause), ("fix", fix), ("fixture", fixture)) if not value.strip()
    ]
    if missing:
        raise ValueError(
            "resumption requires a recorded cause, a fix, and a permanent regression "
            f"fixture; missing: {', '.join(missing)}"
        )
    with store.write() as connection:
        cursor = connection.execute(
            "UPDATE violations SET cause = ?, fix = ?, fixture = ?, resolved_at = ? "
            "WHERE id = ? AND resolved_at IS NULL",
            (cause, fix, fixture, resolved_at, violation_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"{violation_id} is not an open violation")


def open_violations(store: Store) -> tuple[Violation, ...]:
    return tuple(
        Violation(
            id=row["id"],
            condition=row["condition"],
            detail=row["detail"],
            detected_at=row["detected_at"],
            resolved=False,
            resets_routes=bool(row["resets_routes"]),
        )
        for row in store.query(
            "SELECT * FROM violations WHERE resolved_at IS NULL ORDER BY detected_at, id"
        )
    )


def paused_on(store: Store, local_day: str) -> str:
    """Whether the day was inside a pause, and which violation caused it."""
    for row in store.query("SELECT * FROM violations ORDER BY detected_at, id"):
        started = row["detected_at"][:10]
        ended = row["resolved_at"][:10] if row["resolved_at"] else None
        if started <= local_day and (ended is None or local_day <= ended):
            return f"{row['condition']} ({row['id']})"
    return ""


def record_day(store: Store, local_day: str, retained_reads: int, report: str = "") -> bool:
    """Record a local day and whether it counts. Returns eligibility."""
    paused = paused_on(store, local_day)
    eligible = not paused
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO pilot_days (local_day, eligible, paused_reason, "
            "retained_reads, report_json, acknowledged_at, acknowledged_by) "
            "VALUES (?, ?, ?, ?, ?, "
            "(SELECT acknowledged_at FROM pilot_days WHERE local_day = ?), "
            "(SELECT acknowledged_by FROM pilot_days WHERE local_day = ?))",
            (local_day, int(eligible), paused, retained_reads, report, local_day, local_day),
        )
    return eligible


def eligible_dates(store: Store) -> tuple[str, ...]:
    return tuple(
        row["local_day"]
        for row in store.query(
            "SELECT local_day FROM pilot_days WHERE eligible = 1 ORDER BY local_day"
        )
    )


def acknowledge_day(store: Store, local_day: str, actor: str) -> None:
    """`PLAN.md` Phase 5 item 9: the first seven clean days need an operator's eyes."""
    with store.write() as connection:
        connection.execute(
            "UPDATE pilot_days SET acknowledged_at = datetime('now'), acknowledged_by = ? "
            "WHERE local_day = ?",
            (actor, local_day),
        )


def unacknowledged_days(store: Store, limit: int = 7) -> tuple[str, ...]:
    return tuple(
        row["local_day"]
        for row in store.query(
            "SELECT local_day FROM pilot_days WHERE eligible = 1 AND acknowledged_at IS NULL "
            "ORDER BY local_day LIMIT ?",
            limit,
        )
    )


# ---------------------------------------------------------------------------
# Route exercise
# ---------------------------------------------------------------------------


def record_route(
    store: Store, source_revision_id: str, normalized_mime: str, stage: str, at: str
) -> None:
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO route_exercises (source_revision_id, normalized_mime, "
            "code_version, exercised_at, stage) VALUES (?, ?, ?, ?, ?)",
            (source_revision_id, normalized_mime, CODE_VERSION, at, stage),
        )


def routes_exercised(store: Store, stage: str = "", code_version: str = CODE_VERSION) -> set[str]:
    sql = "SELECT source_revision_id FROM route_exercises WHERE code_version = ?"
    params: list[Any] = [code_version]
    if stage:
        sql += " AND stage = ?"
        params.append(stage)
    return {row["source_revision_id"] for row in store.query(sql, *params)}


def routes_outstanding(store: Store, stage: str = "", epoch_id: str = "") -> tuple[str, ...]:
    """Enabled routes not yet exercised under the current code version."""
    enabled = {
        row["source_revision_id"]
        for row in store.query(
            "SELECT source_revision_id FROM diet_epoch_sources WHERE epoch_id = ?"
            if epoch_id
            else "SELECT source_revision_id FROM diet_epoch_sources WHERE epoch_id = "
            "(SELECT id FROM diet_epochs ORDER BY epoch DESC LIMIT 1)",
            *([epoch_id] if epoch_id else []),
        )
    }
    return tuple(sorted(enabled - routes_exercised(store, stage)))


def route_reset_pending(store: Store) -> tuple[str, ...]:
    """Violations whose fix reset the route requirement, so it must be met again."""
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM violations WHERE resets_routes = 1 ORDER BY detected_at, id"
        )
    )


def gate_5_status(store: Store, epoch_id: str = "") -> dict[str, Any]:
    """What Gate 5 asks for, and how much of it the record can show.

    Deliberately blunt about the parts nothing here can supply. Thirty eligible
    dates take thirty days, a hundred retained reads take live acquisition, and
    the approval at the end is the operator's. This counts; it does not judge.
    """
    dates = eligible_dates(store)
    reads = store.one(
        "SELECT COUNT(DISTINCT artifact_id) AS n FROM sightings"
    )["n"]
    outstanding = routes_outstanding(store, "pilot", epoch_id)
    states = {
        row["state"]
        for row in store.query(
            "SELECT state FROM assessments a WHERE a.rowid = "
            "(SELECT MAX(b.rowid) FROM assessments b WHERE b.claim_id = a.claim_id)"
        )
    }
    corrections = store.one(
        "SELECT COUNT(*) AS n FROM revocations WHERE kind = 'correction' AND status = 'confirmed'"
    )["n"]
    return {
        "eligible_dates": len(dates),
        "eligible_dates_required": 30,
        "distinct_retained_reads": reads,
        "distinct_retained_reads_required": 100,
        "routes_outstanding": list(outstanding),
        "states_reached": sorted(states),
        "states_required": ["contested", "indeterminate", "supported"],
        "confirmed_corrections_after_presentation": corrections,
        "open_violations": [v.id for v in open_violations(store)],
        "unacknowledged_of_first_seven": list(unacknowledged_days(store)),
        "code_version": CODE_VERSION,
        "operator_approval": "not recorded",
        "note": (
            "Counting only. Thirty eligible dates take thirty days, a hundred retained "
            "reads take live acquisition, and the approval at the end is the operator's."
        ),
    }


def next_local_day(local_day: str) -> str:
    return (date.fromisoformat(local_day) + timedelta(days=1)).isoformat()
