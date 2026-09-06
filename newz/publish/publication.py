"""Publishing, correcting, retracting — and confirming each from outside.

`SPEC.md` section 10 makes publication an action with an attempted effect and a
separately confirmed outcome, and forbids conflating them. So every function
here records what was attempted, and a second, separate step reads the surface
back and records whether the effect actually happened. An output class with no
confirmation source available is marked `unconfirmed` and is not counted as
published in any report.

Revocation is bounded in time, because a control with unbounded latency is not a
control and revocation is the whole of what replaced the publication gate. When
a correction or a retraction passes its window unconfirmed, its class halts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from newz.clock import stamp
from newz.control.audit import record as audit_record
from newz.present.cards import load_card
from newz.publish.appraisal import class_of, sample_for_review
from newz.publish.surface import LocalSurface
from newz.store.db import Store

#: `SPEC.md` section 10: fifteen minutes for local surfaces during Pilot.
REVOCATION_WINDOW_MINUTES = 15

ATTEMPTED = "attempted"
CONFIRMED = "confirmed"
UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    id: str
    card_revision_id: str
    audience: str
    status: str
    detail: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "card_revision_id": self.card_revision_id,
            "audience": self.audience,
            "status": self.status,
            "detail": self.detail,
        }


def publish(
    store: Store,
    *,
    publication_id: str,
    card_revision_id: str,
    clearance_id: str,
    surface: LocalSurface,
    audience: str = "local",
) -> PublicationRecord:
    """Attempt to serve a cleared revision. Attempting is all this does."""
    clearance = store.one("SELECT * FROM clearances WHERE id = ?", clearance_id)
    if clearance is None:
        raise KeyError(clearance_id)
    if not clearance["granted"]:
        raise ValueError(f"{clearance_id} was refused; publication does not proceed")
    if clearance["card_revision_id"] != card_revision_id:
        raise ValueError("a clearance carries only for the revision it named")

    row = store.one("SELECT * FROM card_revisions WHERE id = ?", card_revision_id)
    card = load_card(store, card_revision_id)
    surface.serve(row["claim_id"], card_revision_id, row["content_hash"], card)

    with store.write() as connection:
        connection.execute(
            "INSERT INTO publications (id, card_revision_id, clearance_id, audience, status, "
            "attempted_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (publication_id, card_revision_id, clearance_id, audience, ATTEMPTED),
        )
    return PublicationRecord(publication_id, card_revision_id, audience, ATTEMPTED)


def confirm_publication(
    store: Store, publication_id: str, surface: LocalSurface
) -> PublicationRecord:
    """Read the surface back. The renderer's own report is not evidence."""
    row = store.one("SELECT * FROM publications WHERE id = ?", publication_id)
    if row is None:
        raise KeyError(publication_id)
    revision = store.one(
        "SELECT * FROM card_revisions WHERE id = ?", row["card_revision_id"]
    )
    serving = surface.serves_revision(revision["claim_id"], revision["content_hash"])
    status = CONFIRMED if serving else UNCONFIRMED
    detail = "the surface serves this revision" if serving else "the surface does not serve it"

    with store.write() as connection:
        connection.execute(
            "UPDATE publications SET status = ?, confirmed_at = datetime('now'), "
            "confirmation_source = ? WHERE id = ?",
            (status, f"local surface at {surface.root}", publication_id),
        )
    if status is CONFIRMED or status == CONFIRMED:
        _queue_if_sampled(store, row["card_revision_id"])
    return PublicationRecord(publication_id, row["card_revision_id"], row["audience"], status, detail)


def _queue_if_sampled(store: Store, card_revision_id: str) -> None:
    from newz.publish.appraisal import appraise

    appraisal = appraise(store, card_revision_id)
    if appraisal.sampled:
        sample_for_review(
            store,
            card_revision_id,
            appraisal.sample_reason,
            f"review:{card_revision_id.split(':')[-1]}",
        )


def published_count(store: Store, audience: str = "local") -> int:
    """Confirmed only. An unconfirmed publication is not counted as published."""
    row = store.one(
        "SELECT COUNT(*) AS n FROM publications WHERE audience = ? AND status = ?",
        audience,
        CONFIRMED,
    )
    return row["n"] if row else 0


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------


def _open_revocation(
    store: Store,
    *,
    revocation_id: str,
    kind: str,
    claim_id: str,
    card_revision_id: str,
    reason: str,
    now: datetime,
) -> str:
    due = stamp(now + timedelta(minutes=REVOCATION_WINDOW_MINUTES))
    with store.write() as connection:
        connection.execute(
            "INSERT INTO revocations (id, kind, claim_id, card_revision_id, class, reason, "
            "attempted_at, due_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                revocation_id,
                kind,
                claim_id,
                card_revision_id,
                class_of(store, card_revision_id),
                reason,
                stamp(now),
                due,
                ATTEMPTED,
            ),
        )
    return due


def correct(
    store: Store,
    *,
    revocation_id: str,
    claim_id: str,
    card_revision_id: str,
    reason: str,
    surface: LocalSurface,
    now: datetime,
) -> str:
    """Attach a correction to the output it corrects, and start its clock."""
    due = _open_revocation(
        store,
        revocation_id=revocation_id,
        kind="correction",
        claim_id=claim_id,
        card_revision_id=card_revision_id,
        reason=reason,
        now=now,
    )
    surface.attach_correction(
        claim_id,
        {"revocation_id": revocation_id, "reason": reason, "at": stamp(now)},
    )
    return due


def retract(
    store: Store,
    *,
    revocation_id: str,
    claim_id: str,
    card_revision_id: str,
    reason: str,
    surface: LocalSurface,
    now: datetime,
    tombstone_id: str,
) -> str:
    """Remove the presentation from navigation and leave a tombstone behind.

    The tombstone is the point. A page that simply disappears leaves a reader
    with no way to know what they read; a tombstone says what changed.
    """
    due = _open_revocation(
        store,
        revocation_id=revocation_id,
        kind="retraction",
        claim_id=claim_id,
        card_revision_id=card_revision_id,
        reason=reason,
        now=now,
    )
    explanation = f"This presentation was retracted: {reason}"
    surface.withdraw(
        claim_id,
        {
            "claim_id": claim_id,
            "card_revision_id": card_revision_id,
            "explanation": explanation,
            "at": stamp(now),
        },
    )
    with store.write() as connection:
        connection.execute(
            "INSERT INTO tombstones (id, claim_id, card_revision_id, explanation, created_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (tombstone_id, claim_id, card_revision_id, explanation),
        )
        connection.execute(
            "UPDATE card_revisions SET live = 0 WHERE id = ?", (card_revision_id,)
        )
        audit_record(
            connection,
            actor="system",
            action="retract",
            target=card_revision_id,
            reason=reason,
            preimage=claim_id,
            result=tombstone_id,
            channel="system",
        )
    return due


def confirm_revocation(
    store: Store, revocation_id: str, surface: LocalSurface, now: datetime
) -> str:
    """Confirm from the surface, and record the latency it actually took."""
    row = store.one("SELECT * FROM revocations WHERE id = ?", revocation_id)
    if row is None:
        raise KeyError(revocation_id)

    if row["kind"] == "retraction":
        effected = not surface.in_navigation(row["claim_id"]) and surface.has_tombstone(
            row["claim_id"]
        )
    else:
        effected = any(
            notice["revocation_id"] == revocation_id
            for notice in surface.corrections_on(row["claim_id"])
        )

    status = CONFIRMED if effected else UNCONFIRMED
    with store.write() as connection:
        connection.execute(
            "UPDATE revocations SET status = ?, confirmed_at = ?, confirmation_source = ? "
            "WHERE id = ?",
            (
                status,
                stamp(now),
                f"local surface at {surface.root}",
                revocation_id,
            ),
        )
    return status


def revocation_latency_seconds(store: Store, revocation_id: str) -> float | None:
    row = store.one("SELECT attempted_at, confirmed_at FROM revocations WHERE id = ?", revocation_id)
    if row is None or not row["confirmed_at"]:
        return None
    return (
        datetime.fromisoformat(row["confirmed_at"]) - datetime.fromisoformat(row["attempted_at"])
    ).total_seconds()


def overdue_revocations(
    store: Store, now: str, output_class: str | None = None
) -> tuple[str, ...]:
    """Revocations past their window with no confirmation."""
    if output_class:
        rows = store.query(
            "SELECT id FROM revocations WHERE status != ? AND due_at <= ? AND class = ? "
            "ORDER BY id",
            CONFIRMED,
            now,
            output_class,
        )
    else:
        rows = store.query(
            "SELECT id FROM revocations WHERE status != ? AND due_at <= ? ORDER BY id",
            CONFIRMED,
            now,
        )
    return tuple(row["id"] for row in rows)


def halt_classes_with_overdue_revocations(store: Store, now: str) -> tuple[str, ...]:
    """An overdue revocation halts its class automatically, with no operator."""
    from newz.publish.clearance import halt_class

    halted: list[str] = []
    for revocation_id in overdue_revocations(store, now):
        row = store.one("SELECT class, kind FROM revocations WHERE id = ?", revocation_id)
        halt_class(
            store,
            row["class"],
            f"{row['kind']} {revocation_id} passed its window unconfirmed",
        )
        halted.append(row["class"])
    return tuple(sorted(set(halted)))


def unconfirmed_retraction(store: Store, claim_id: str) -> str:
    row = store.one(
        "SELECT id FROM revocations WHERE claim_id = ? AND kind = 'retraction' AND status != ? "
        "ORDER BY id LIMIT 1",
        claim_id,
        CONFIRMED,
    )
    return f"retraction {row['id']} is not confirmed" if row else ""


def revocation_report(store: Store) -> dict[str, Any]:
    """What section 13 asks to be measured rather than assumed."""
    rows = store.query("SELECT * FROM revocations ORDER BY id")
    latencies = [
        revocation_latency_seconds(store, row["id"])
        for row in rows
        if row["confirmed_at"]
    ]
    return {
        "revocations": len(rows),
        "confirmed": sum(1 for row in rows if row["status"] == CONFIRMED),
        "unconfirmed": sum(1 for row in rows if row["status"] != CONFIRMED),
        "max_latency_seconds": max(latencies) if latencies else None,
        "window_seconds": REVOCATION_WINDOW_MINUTES * 60,
    }
