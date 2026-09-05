"""Surprise and consequence.

**No self-grading.** A confirmed outcome comes from outside the system's own
account of it: for a publication, the confirmation rule of `SPEC.md` section 10,
which reads the surface back; for an investigation, the evidence graph itself —
whether the claim reached the state the investigation set out to reach. Where no
external confirmation exists the status is `unverifiable`, and an unverifiable
outcome feeds no consequence. A system permitted to score its own report would
learn from its own opinion of itself.

**Surprise is retained whether or not it fits anything live.** Confirmations are
cheap to keep and worthless alone; a system that retains only what it expected
learns the shape of its own expectations.

**A consequence must change something and cite itself as the reason.** Activity
that grows while behaviour does not is the failure this exists to make visible.
And what it may change is bounded: an interest's priority, a task's retry policy,
a source's operational standing, or a future decision rule. Never a threshold,
an evidence weight, a risk classification, or any assessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.domain.enums import OutcomeStatus
from newz.store.db import Store

#: What a consequence is allowed to change. The list is closed, and it is the
#: boundary of section 9.1 restated for learning: interest reaches attention,
#: consequence reaches behaviour, and neither reaches a conclusion.
CHANGEABLE = frozenset(
    {"interest_priority", "task_retry_policy", "source_operational_standing", "decision_rule"}
)


class SelfGrading(Exception):
    """An outcome the system would have been scoring from its own report."""


@dataclass(frozen=True, slots=True)
class Surprise:
    id: str
    expectation_id: str
    outcome_id: str
    divergence: str
    fits_live_interest: bool
    raised_to_operator: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "expectation_id": self.expectation_id,
            "outcome_id": self.outcome_id,
            "divergence": self.divergence,
            "fits_live_interest": self.fits_live_interest,
            "raised_to_operator": self.raised_to_operator,
        }


def confirm_outcome(
    store: Store,
    *,
    outcome_id: str,
    expectation_id: str,
    observed: str,
    confirmation_source: str,
    status: OutcomeStatus = OutcomeStatus.CONFIRMED,
) -> str:
    """Record what actually happened, and where that was learned.

    A confirmed status with no source outside the system is refused rather than
    downgraded, because a caller that meant `unverifiable` should say so.
    """
    if status is OutcomeStatus.CONFIRMED and not confirmation_source.strip():
        raise SelfGrading(
            "a confirmed outcome names where it was confirmed; the system's own report "
            "is not a source"
        )
    with store.write() as connection:
        connection.execute(
            "INSERT INTO confirmed_outcomes (id, expectation_id, status, observed, "
            "confirmation_source, at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (outcome_id, expectation_id, status.value, observed, confirmation_source),
        )
    return outcome_id


def confirm_from_publication(
    store: Store, *, outcome_id: str, expectation_id: str, publication_id: str
) -> str:
    """The publication confirmation rule of section 10, used as an outcome."""
    row = store.one("SELECT * FROM publications WHERE id = ?", publication_id)
    if row is None:
        raise KeyError(publication_id)
    if row["status"] != "confirmed":
        return confirm_outcome(
            store,
            outcome_id=outcome_id,
            expectation_id=expectation_id,
            observed=f"publication {publication_id} is {row['status']}",
            confirmation_source="",
            status=OutcomeStatus.UNVERIFIABLE,
        )
    return confirm_outcome(
        store,
        outcome_id=outcome_id,
        expectation_id=expectation_id,
        observed=f"publication {publication_id} confirmed",
        confirmation_source=row["confirmation_source"],
    )


def confirm_from_evidence(
    store: Store, *, outcome_id: str, expectation_id: str, claim_id: str
) -> str:
    """The evidence graph as the outside: did the claim reach a state at all."""
    row = store.one(
        "SELECT state, explanation FROM assessments WHERE claim_id = ? ORDER BY rowid DESC LIMIT 1",
        claim_id,
    )
    if row is None:
        return confirm_outcome(
            store,
            outcome_id=outcome_id,
            expectation_id=expectation_id,
            observed=f"{claim_id} has no assessment",
            confirmation_source="",
            status=OutcomeStatus.UNVERIFIABLE,
        )
    return confirm_outcome(
        store,
        outcome_id=outcome_id,
        expectation_id=expectation_id,
        observed=f"{claim_id} is {row['state']}: {row['explanation']}",
        confirmation_source=f"evidence graph, assessment of {claim_id}",
    )


def record_surprise(
    store: Store,
    *,
    surprise_id: str,
    expectation_id: str,
    outcome_id: str,
    divergence: str,
    fits_live_interest: bool,
    raise_to_operator: bool = False,
) -> Surprise:
    """Retain a divergence. Fitting nothing live is not a reason to drop it."""
    with store.write() as connection:
        connection.execute(
            "INSERT INTO surprises (id, expectation_id, outcome_id, divergence, "
            "fits_live_interest, raised_to_operator, at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                surprise_id,
                expectation_id,
                outcome_id,
                divergence,
                int(fits_live_interest),
                int(raise_to_operator),
            ),
        )
    return Surprise(
        id=surprise_id,
        expectation_id=expectation_id,
        outcome_id=outcome_id,
        divergence=divergence,
        fits_live_interest=fits_live_interest,
        raised_to_operator=raise_to_operator,
    )


def compare(store: Store, expectation_id: str, outcome_id: str) -> tuple[bool, str]:
    """Whether the outcome diverged from the expectation, and how."""
    expectation = store.one("SELECT * FROM expectations WHERE id = ?", expectation_id)
    outcome = store.one("SELECT * FROM confirmed_outcomes WHERE id = ?", outcome_id)
    if expectation is None or outcome is None:
        raise KeyError(expectation_id if expectation is None else outcome_id)
    expected = expectation["expected"].strip().lower()
    observed = outcome["observed"].strip().lower()
    diverged = expected not in observed
    return diverged, f"expected {expectation['expected']!r}; observed {outcome['observed']!r}"


def record_consequence(
    store: Store,
    *,
    consequence_id: str,
    expectation_id: str,
    outcome_id: str,
    score: str,
    changed: str,
    change_cites: str,
) -> str:
    """Score the delta and record the change it justified.

    Refuses an unverifiable outcome, refuses a change outside the closed list,
    and refuses a consequence that changed nothing. The last is the important
    one: a consequence with no change is an explanation, and an explanation with
    no change is the defect `SPEC.md` section 13 names.
    """
    outcome = store.one("SELECT * FROM confirmed_outcomes WHERE id = ?", outcome_id)
    if outcome is None:
        raise KeyError(outcome_id)
    if outcome["status"] == OutcomeStatus.UNVERIFIABLE.value:
        raise SelfGrading("an unverifiable outcome feeds no consequence")
    if changed not in CHANGEABLE:
        raise ValueError(
            f"a consequence may change {sorted(CHANGEABLE)}; {changed!r} would be learning "
            "reaching a conclusion"
        )
    if not change_cites.strip():
        raise ValueError(
            "a consequence cites itself as the reason for the change; a change that does "
            "not say why is not traceable to what caused it"
        )
    with store.write() as connection:
        connection.execute(
            "INSERT INTO consequences (id, expectation_id, outcome_id, score, changed, "
            "change_cites, at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (consequence_id, expectation_id, outcome_id, score, changed, change_cites),
        )
    return consequence_id


def surprises(store: Store, only_unfitting: bool = False) -> tuple[dict[str, Any], ...]:
    sql = "SELECT * FROM surprises"
    if only_unfitting:
        sql += " WHERE fits_live_interest = 0"
    return tuple(dict(row) for row in store.query(sql + " ORDER BY id"))


def calibration(store: Store) -> dict[str, Any]:
    """How often the system was right, and what it did about being wrong."""
    expectations = store.one("SELECT COUNT(*) AS n FROM expectations")["n"]
    confirmed = store.one(
        "SELECT COUNT(*) AS n FROM confirmed_outcomes WHERE status = 'confirmed'"
    )["n"]
    surprise_rows = store.query("SELECT fits_live_interest FROM surprises")
    consequences = store.one("SELECT COUNT(*) AS n FROM consequences")["n"]
    return {
        "expectations": expectations,
        "confirmed_outcomes": confirmed,
        "surprises": len(surprise_rows),
        "surprises_fitting_no_live_interest": sum(
            1 for row in surprise_rows if not row["fits_live_interest"]
        ),
        "consequences": consequences,
        "surprises_without_consequence": max(len(surprise_rows) - consequences, 0),
        "changes_by_kind": {
            row["changed"]: row["n"]
            for row in store.query(
                "SELECT changed, COUNT(*) AS n FROM consequences GROUP BY changed"
            )
        },
    }
