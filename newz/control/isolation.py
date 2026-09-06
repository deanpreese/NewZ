"""The isolated workflow R3 material is handled in.

`SPEC.md` section 8 puts medicine, elections, finance and alleged crimes by
living people at R3: an isolated workflow, a direct primary or adjudicative
basis plus an independent countable one, operator approval before any
publication, every access logged, and private personal data excluded from
prompts and output unless strictly necessary and approved. `PLAN.md` gates live
R3 intake to Phase 6, after the isolated workflow has been exercised.

Most of that already existed and was built for other reasons. The promotion
thresholds carry the evidence bar, clearance refuses an R3 revision without an
operator's approval of that exact content hash, entity cards will not render at
R3, the reader surface does not list it, the conversational surface has no
method that could clear it, and erasure holds the per-subject keys. What was
missing was the isolation itself, in two specific places.

**Nothing autonomous opens an R3 case.** A workflow the system can enter by
itself is not isolated from it. `open_case` demands an operator, a named
subject and a reason, and an R3 claim with no case behind it is a claim that
arrived by a route nobody chose.

**The model does not read quarantined material.** `extract` sends segment text
to the local endpoint, and until now it would have sent an R3 body as readily as
any other — the boundary that stops a model *granting* capability said nothing
about what a model is *shown*. `guard_model_read` is the gate, and it refuses by
default. The exception section 8 allows is narrow and is built narrow: an
approval names one artifact, one purpose, one operator and an expiry, and is
spent when it is used. A standing approval would be the exclusion rescinded
while appearing to be honoured.

A refused access is logged like a permitted one. An attempt that was turned away
is a fact about what something tried to do, and a quarantine that recorded only
its successes would describe a system nobody had tested the walls of.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from newz.clock import as_utc, from_ledger, stamp
from newz.domain.enums import RiskTier
from newz.store.db import Store


class QuarantineRefused(Exception):
    """A read of quarantined material that was not permitted."""


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    claim_id: str
    subject: str
    opened_by: str
    reason: str
    closed_at: str = ""
    closed_reason: str = ""

    @property
    def open(self) -> bool:
        return not self.closed_at

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "subject": self.subject,
            "opened_by": self.opened_by,
            "reason": self.reason,
            "open": self.open,
            "closed_reason": self.closed_reason,
        }


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------


def open_case(
    store: Store,
    *,
    case_id: str,
    claim_id: str,
    subject: str,
    opened_by: str,
    reason: str,
) -> Case:
    """Open an R3 case. An operator act, and only an operator act.

    `opened_by` is required and must name a person. The system may raise a
    claim's risk to R3 on its own — `SPEC.md` section 8 allows a model to raise
    risk and never to lower it — but raising risk is recognising that something
    is dangerous, and opening a case is deciding to work on it anyway. Those are
    different acts and only the second is a person's.
    """
    if not opened_by.startswith("operator:"):
        raise QuarantineRefused(
            f"an R3 case is opened by an operator, not by {opened_by or 'nobody'}: "
            "raising a claim's risk is the system's, deciding to work on it is not"
        )
    if not subject.strip():
        raise ValueError("an R3 case names the subject it concerns")
    if not reason.strip():
        raise ValueError("an R3 case records why it was opened")

    row = store.one("SELECT risk FROM claims WHERE id = ?", claim_id)
    if row is None:
        raise KeyError(claim_id)
    if (row["risk"] or RiskTier.R3.value) != RiskTier.R3.value:
        raise QuarantineRefused(
            f"{claim_id} is {row['risk']}, and an R3 case is not how a claim becomes R3: "
            "reclassify it first, where the monotonicity rule can see the change"
        )

    with store.write() as connection:
        connection.execute(
            "INSERT INTO r3_cases (id, claim_id, subject, opened_by, reason, closed_at, "
            "closed_reason, opened_at) VALUES (?, ?, ?, ?, ?, NULL, '', datetime('now'))",
            (case_id, claim_id, subject, opened_by, reason),
        )
    return Case(case_id, claim_id, subject, opened_by, reason)


def close_case(store: Store, case_id: str, reason: str, now: datetime) -> None:
    if not reason.strip():
        raise ValueError("closing a case records why")
    with store.write() as connection:
        connection.execute(
            "UPDATE r3_cases SET closed_at = ?, closed_reason = ? WHERE id = ?",
            (stamp(now), reason, case_id),
        )


def case_for(store: Store, claim_id: str) -> Case | None:
    row = store.one(
        "SELECT * FROM r3_cases WHERE claim_id = ? ORDER BY rowid DESC LIMIT 1", claim_id
    )
    return _as_case(row) if row else None


def _as_case(row) -> Case:
    return Case(
        id=row["id"],
        claim_id=row["claim_id"],
        subject=row["subject"],
        opened_by=row["opened_by"],
        reason=row["reason"],
        closed_at=row["closed_at"] or "",
        closed_reason=row["closed_reason"],
    )


def claims_without_a_case(store: Store) -> tuple[str, ...]:
    """Claims explicitly at R3 that nobody opened a case for.

    A claim that reached R3 by reclassification and has no case behind it is
    being investigated on the ordinary path at a risk the ordinary path is not
    for. It is the shape an isolation failure takes when nothing crashes.
    """
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT c.id AS id FROM claims c LEFT JOIN r3_cases r ON r.claim_id = c.id "
            "WHERE c.risk = ? AND r.id IS NULL ORDER BY c.id",
            RiskTier.R3.value,
        )
    )


def claims_with_unreadable_risk(store: Store) -> tuple[str, ...]:
    """Claims with no risk state, which behave as R3 and are not the same problem.

    `SPEC.md` section 8: missing or unreadable risk behaves as R3 internally and
    blocks publication. So these are inside this workflow's scope — but a claim
    nobody has classified and a claim someone classified as dangerous need
    different answers, and reporting them in one list would hide the handful
    that matter among the many that are merely unlabelled.
    """
    return tuple(
        row["id"]
        for row in store.query("SELECT id FROM claims WHERE risk IS NULL ORDER BY id")
    )


# ---------------------------------------------------------------------------
# Quarantine
# ---------------------------------------------------------------------------


def quarantine(store: Store, artifact_id: str, case_id: str, reason: str) -> None:
    """Put a retained body inside a case."""
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO quarantined_artifacts (artifact_id, case_id, reason, "
            "recorded_at) VALUES (?, ?, ?, datetime('now'))",
            (artifact_id, case_id, reason),
        )


def case_of_artifact(store: Store, artifact_id: str) -> str:
    row = store.one(
        "SELECT case_id FROM quarantined_artifacts WHERE artifact_id = ? ORDER BY case_id LIMIT 1",
        artifact_id,
    )
    return row["case_id"] if row else ""


def is_quarantined(store: Store, artifact_id: str) -> bool:
    return bool(case_of_artifact(store, artifact_id))


def record_access(
    store: Store,
    *,
    artifact_id: str,
    case_id: str,
    actor: str,
    purpose: str,
    permitted: bool,
    detail: str = "",
) -> None:
    """Log it, permitted or not."""
    with store.write() as connection:
        connection.execute(
            "INSERT INTO quarantine_access (artifact_id, case_id, actor, purpose, permitted, "
            "detail, at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (artifact_id, case_id, actor, purpose, int(permitted), detail),
        )


def accesses(store: Store, artifact_id: str = "") -> tuple[dict[str, Any], ...]:
    sql = "SELECT * FROM quarantine_access"
    params: tuple[Any, ...] = ()
    if artifact_id:
        sql += " WHERE artifact_id = ?"
        params = (artifact_id,)
    return tuple(
        {
            "artifact_id": row["artifact_id"],
            "case_id": row["case_id"],
            "actor": row["actor"],
            "purpose": row["purpose"],
            "permitted": bool(row["permitted"]),
            "detail": row["detail"],
        }
        for row in store.query(sql + " ORDER BY id", *params)
    )


# ---------------------------------------------------------------------------
# The model boundary
# ---------------------------------------------------------------------------


def approve_model_read(
    store: Store,
    *,
    approval_id: str,
    artifact_id: str,
    case_id: str,
    approved_by: str,
    necessity: str,
    expires_at: datetime,
) -> None:
    """The narrow exception: one artifact, one operator, one reason, one expiry.

    `necessity` is not a formality. Section 8 permits private personal data in a
    prompt only where it is *strictly necessary*, so the approval has to say what
    it is necessary for; an approval whose reason is "to extract from it" is the
    default being restated rather than an exception being made.
    """
    if not approved_by.startswith("operator:"):
        raise QuarantineRefused("only an operator approves a model read of quarantined material")
    if not necessity.strip():
        raise ValueError("an approval says what makes the read strictly necessary")
    with store.write() as connection:
        connection.execute(
            "INSERT INTO model_read_approvals (id, artifact_id, case_id, approved_by, "
            "necessity, expires_at, used_at, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, NULL, datetime('now'))",
            (approval_id, artifact_id, case_id, approved_by, necessity, stamp(expires_at)),
        )


def guard_model_read(store: Store, artifact_id: str, now: datetime, actor: str = "extract") -> None:
    """Refuse to show quarantined material to a model, unless one approval says otherwise.

    Called before a prompt is built, not after: the point is that the text never
    reaches the endpoint, and a check that ran afterwards would be describing
    something that had already happened.
    """
    case_id = case_of_artifact(store, artifact_id)
    if not case_id:
        return

    row = store.one(
        "SELECT * FROM model_read_approvals WHERE artifact_id = ? AND used_at IS NULL "
        "ORDER BY rowid",
        artifact_id,
    )
    if row is None:
        record_access(
            store,
            artifact_id=artifact_id,
            case_id=case_id,
            actor=actor,
            purpose="model_read",
            permitted=False,
            detail="no approval",
        )
        raise QuarantineRefused(
            f"{artifact_id} is quarantined under {case_id}: private personal data is "
            "excluded from prompts unless an operator has recorded that a particular "
            "read is strictly necessary"
        )

    if as_utc(now) > from_ledger(row["expires_at"]):
        record_access(
            store,
            artifact_id=artifact_id,
            case_id=case_id,
            actor=actor,
            purpose="model_read",
            permitted=False,
            detail=f"approval {row['id']} expired at {row['expires_at']}",
        )
        raise QuarantineRefused(
            f"approval {row['id']} for {artifact_id} expired at {row['expires_at']}"
        )

    with store.write() as connection:
        # Spent on use. An approval that survived its own use would be a
        # standing permission wearing a single act's clothes.
        connection.execute(
            "UPDATE model_read_approvals SET used_at = ? WHERE id = ?", (stamp(now), row["id"])
        )
    record_access(
        store,
        artifact_id=artifact_id,
        case_id=case_id,
        actor=actor,
        purpose="model_read",
        permitted=True,
        detail=f"approval {row['id']}: {row['necessity']}",
    )


def report(store: Store) -> dict[str, Any]:
    """What the isolated workflow currently holds, for an operator."""
    cases = tuple(
        _as_case(row) for row in store.query("SELECT * FROM r3_cases ORDER BY id")
    )
    refused = [entry for entry in accesses(store) if not entry["permitted"]]
    return {
        "cases": [case.as_record() for case in cases],
        "open_cases": sum(1 for case in cases if case.open),
        "quarantined_artifacts": store.one(
            "SELECT COUNT(DISTINCT artifact_id) AS n FROM quarantined_artifacts"
        )["n"],
        "accesses": len(accesses(store)),
        "refused_accesses": len(refused),
        "unused_approvals": store.one(
            "SELECT COUNT(*) AS n FROM model_read_approvals WHERE used_at IS NULL"
        )["n"],
        "r3_claims_without_a_case": list(claims_without_a_case(store)),
        "claims_with_unreadable_risk": list(claims_with_unreadable_risk(store)),
    }
