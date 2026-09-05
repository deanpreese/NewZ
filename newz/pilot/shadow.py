"""Shadow: live acquisition, assessments computed and compared, nothing believed.

The stage exists so a divergence is found before it is believed. Live material
goes through the whole pipeline, the assessments it produces are compared
against what the offline fixtures said they should be, and **every divergence
gets a recorded cause** — not a dismissal and not a shrug. Presentation is
withheld entirely.

Shadow exits when all three hold: every enabled route has been fetched live at
least once, every divergence has a cause, and no pause condition has fired.
Shadow days do not consume Gate 5's pilot dates, because a stage that counted
toward the thing it is checking would be checking nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.evidence.assess import evidence_input
from newz.pilot.modes import DeploymentMode, current_mode
from newz.pilot.violations import open_violations, routes_outstanding
from newz.policy.promotion import assess
from newz.store.db import Store
from newz.version import CODE_VERSION


class NotInShadow(Exception):
    """A shadow operation attempted outside shadow mode."""


@dataclass(frozen=True, slots=True)
class ShadowResult:
    claim_id: str
    expected: str
    observed: str
    matched: bool
    cause: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "expected": self.expected,
            "observed": self.observed,
            "matched": self.matched,
            "cause": self.cause,
        }


def shadow_assess(store: Store, claim_id: str, expected_state: str, run_id: str) -> ShadowResult:
    """Compute the assessment and compare it. Nothing is written to `assessments`.

    That is the whole discipline of the stage: `assess` is called, the answer is
    recorded here, and the authoritative table is left alone. A shadow run that
    wrote an assessment would be a pilot run with a different name.
    """
    if current_mode(store) is not DeploymentMode.SHADOW:
        raise NotInShadow("shadow assessment runs in shadow mode and nowhere else")

    result = assess(evidence_input(store, claim_id))
    observed = result.state.value
    matched = observed == expected_state

    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO shadow_runs (id, claim_id, expected, observed, matched, "
            "cause, code_version, ran_at) VALUES (?, ?, ?, ?, ?, '', ?, datetime('now'))",
            (run_id, claim_id, expected_state, observed, int(matched), CODE_VERSION),
        )
    return ShadowResult(claim_id, expected_state, observed, matched)


def record_cause(store: Store, run_id: str, cause: str) -> None:
    """Explain a divergence. Required, and not satisfiable by 'expected'."""
    if not cause.strip():
        raise ValueError("a divergence records its cause")
    with store.write() as connection:
        cursor = connection.execute(
            "UPDATE shadow_runs SET cause = ? WHERE id = ? AND matched = 0", (cause, run_id)
        )
        if cursor.rowcount != 1:
            raise KeyError(f"{run_id} is not an unexplained divergence")


def unexplained_divergences(store: Store) -> tuple[str, ...]:
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM shadow_runs WHERE matched = 0 AND cause = '' ORDER BY id"
        )
    )


def presentation_withheld(store: Store) -> bool:
    """Nothing published while in shadow. Asserted from the record, not assumed."""
    if current_mode(store) is not DeploymentMode.SHADOW:
        return True
    entered = store.one(
        "SELECT at FROM mode_transitions WHERE to_mode = 'shadow' ORDER BY rowid DESC LIMIT 1"
    )
    since = entered["at"] if entered else "0000"
    published = store.one(
        "SELECT COUNT(*) AS n FROM publications WHERE attempted_at >= ?", since
    )["n"]
    return published == 0


def exit_criteria(store: Store, epoch_id: str = "") -> dict[str, Any]:
    """What Shadow must show before Pilot. All three, or it is not done."""
    outstanding = routes_outstanding(store, "shadow", epoch_id)
    unexplained = unexplained_divergences(store)
    violations = [violation.id for violation in open_violations(store)]
    runs = store.query("SELECT matched FROM shadow_runs")
    return {
        "routes_outstanding": list(outstanding),
        "unexplained_divergences": list(unexplained),
        "open_violations": violations,
        "runs": len(runs),
        "matched": sum(1 for row in runs if row["matched"]),
        "presentation_withheld": presentation_withheld(store),
        "satisfied": not outstanding
        and not unexplained
        and not violations
        and bool(runs)
        and presentation_withheld(store),
    }
