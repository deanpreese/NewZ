"""Clearance, and the refusals that hold with nobody present.

Approve-by-default removes the person standing in front of publication, so what
holds output back has to be enumerated and has to fail closed. `SPEC.md` section
10 lists the conditions; they are here as one function that returns every reason
it found rather than the first, because a refusal a person has to re-trigger to
learn the rest of is a refusal that wastes their attention.

Two rules about what a clearance is. It names an **exact revision and its
content hash**, so approving something that must be rebuilt to be read is not
possible. And it is **never inferred** — not from material the system perceived,
not from a case the system made for publishing, and not from a prior approval of
a different revision or class.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.domain.enums import RiskTier
from newz.publish.appraisal import appraise, class_of, debt_exceeded
from newz.store.db import Store
from newz.version import POLICY_VERSION


@dataclass(frozen=True, slots=True)
class Refusal:
    condition: str
    detail: str

    def as_record(self) -> dict[str, Any]:
        return {"condition": self.condition, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ClearanceResult:
    card_revision_id: str
    granted: bool
    clearance_id: str
    refusals: tuple[Refusal, ...]
    output_class: str
    requires_operator: bool = False

    def as_record(self) -> dict[str, Any]:
        return {
            "card_revision_id": self.card_revision_id,
            "granted": self.granted,
            "clearance_id": self.clearance_id,
            "refusals": [refusal.as_record() for refusal in self.refusals],
            "class": self.output_class,
            "requires_operator": self.requires_operator,
        }


def class_halted(store: Store, output_class: str) -> str:
    row = store.one(
        "SELECT reason FROM class_halts WHERE class = ? AND cleared_at IS NULL", output_class
    )
    return row["reason"] if row else ""


def halt_class(store: Store, output_class: str, reason: str) -> None:
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO class_halts (class, reason, halted_at, cleared_at) "
            "VALUES (?, ?, datetime('now'), NULL)",
            (output_class, reason),
        )


def clear_halt(store: Store, output_class: str) -> None:
    with store.write() as connection:
        connection.execute(
            "UPDATE class_halts SET cleared_at = datetime('now') WHERE class = ? "
            "AND cleared_at IS NULL",
            (output_class,),
        )


def refusal_conditions(
    store: Store, card_revision_id: str, now: str = ""
) -> tuple[Refusal, ...]:
    """Every enumerated reason this revision may not publish, with no operator present."""
    from newz.evidence.assess import reassessment_owed
    from newz.publish.publication import overdue_revocations, unconfirmed_retraction

    row = store.one("SELECT * FROM card_revisions WHERE id = ?", card_revision_id)
    if row is None:
        raise KeyError(card_revision_id)
    output_class = class_of(store, card_revision_id)
    refusals: list[Refusal] = []

    claim = store.one("SELECT risk FROM claims WHERE id = ?", row["claim_id"])
    risk = (claim["risk"] if claim else None) or RiskTier.R3.value
    if claim is None or claim["risk"] is None:
        refusals.append(Refusal("risk_state_missing", "unreadable risk behaves as R3"))
    if risk == RiskTier.R4.value:
        refusals.append(Refusal("content_is_r4", "R4 is never published"))

    owed = reassessment_owed(store, row["claim_id"])
    if owed:
        # The card is a rendering of a conclusion, and the conclusion stopped
        # following from its own evidence. Publishing it would put a statement
        # on a surface that the ledger underneath already disagrees with.
        refusals.append(Refusal("assessment_no_longer_follows", owed))

    appraisal = appraise(store, card_revision_id)
    for result in appraisal.machine:
        if not result.passed:
            refusals.append(
                Refusal(f"machine_appraisal_failed:{result.dimension.value}", result.detail)
            )

    if debt_exceeded(store, output_class):
        refusals.append(
            Refusal("review_debt_ceiling_exceeded", f"unreviewed output in {output_class}")
        )

    halted = class_halted(store, output_class)
    if halted:
        refusals.append(Refusal("class_halted", halted))

    if now:
        overdue = overdue_revocations(store, now, output_class)
        if overdue:
            refusals.append(
                Refusal("revocation_overdue", f"{len(overdue)} unconfirmed past its window")
            )

    pending = unconfirmed_retraction(store, row["claim_id"])
    if pending:
        refusals.append(Refusal("prior_retraction_unconfirmed", pending))

    return tuple(refusals)


def clear(
    store: Store,
    card_revision_id: str,
    clearance_id: str,
    *,
    now: str = "",
    operator_actor: str = "",
    operator_approves_exact_revision: str = "",
) -> ClearanceResult:
    """Grant or refuse clearance for one exact revision.

    R3 requires an operator's approval naming this revision's content hash. An
    approval of a different revision, or of the class, does not carry: `SPEC.md`
    forbids autonomously publishing high-risk claims about living people, and an
    approval that travels is an approval that eventually travels somewhere
    nobody looked.
    """
    row = store.one("SELECT * FROM card_revisions WHERE id = ?", card_revision_id)
    if row is None:
        raise KeyError(card_revision_id)
    output_class = class_of(store, card_revision_id)
    refusals = list(refusal_conditions(store, card_revision_id, now))

    claim = store.one("SELECT risk FROM claims WHERE id = ?", row["claim_id"])
    risk = (claim["risk"] if claim else None) or RiskTier.R3.value
    requires_operator = risk == RiskTier.R3.value

    if requires_operator:
        if not operator_actor:
            refusals.append(
                Refusal("operator_approval_required", "R3 publishes only on an operator's approval")
            )
        elif operator_approves_exact_revision != row["content_hash"]:
            refusals.append(
                Refusal(
                    "approval_names_a_different_revision",
                    "an approval carries only for the exact content it named",
                )
            )

    granted = not refusals
    with store.write() as connection:
        connection.execute(
            "INSERT INTO clearances (id, card_revision_id, content_hash, class, granted, "
            "refusal_reason, policy_version, operator_actor, cleared_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                clearance_id,
                card_revision_id,
                row["content_hash"],
                output_class,
                int(granted),
                "; ".join(f"{r.condition}: {r.detail}" for r in refusals) or None,
                POLICY_VERSION,
                operator_actor or None,
            ),
        )
    return ClearanceResult(
        card_revision_id=card_revision_id,
        granted=granted,
        clearance_id=clearance_id,
        refusals=tuple(refusals),
        output_class=output_class,
        requires_operator=requires_operator,
    )


# ---------------------------------------------------------------------------
# Reach
# ---------------------------------------------------------------------------

LOCAL = "local"
PUBLIC = "public"


def reach_enabled(store: Store, audience: str) -> bool:
    """Public reach defaults to off by being absent rather than by a stored false."""
    row = store.one("SELECT enabled FROM reach_settings WHERE audience = ?", audience)
    if row is None:
        return audience == LOCAL
    return bool(row["enabled"])


def set_reach(
    store: Store, audience: str, enabled: bool, *, actor: str, reason: str, scope: str = ""
) -> None:
    """Widening reach is an explicit, scoped operator act. Locking down is not.

    An operator must name themselves and their reason to enable an audience.
    Disabling one takes neither, because a control that is harder to pull than
    to push is not a control.
    """
    if enabled and (not actor or not reason or not scope):
        raise ValueError(
            "enabling an audience is an explicit scoped operator act: actor, reason and scope"
        )
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO reach_settings (audience, enabled, scope, changed_by, reason, "
            "changed_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (audience, int(enabled), scope, actor or "system", reason or "locked down"),
        )
