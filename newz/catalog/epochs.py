"""Diet epochs: immutable sets of enabled source revisions, with a dry run.

An epoch is what the system was allowed to read, and when. Activating one is the
only way to change the diet, and the dry run exists so that the exact effect —
which sources, which budget, what changed — is visible before it happens rather
than reconstructible after.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from newz.canonical import dumps
from newz.control import audit
from newz.control.budget import DailyBudget
from newz.store.db import Store


@dataclass(frozen=True, slots=True)
class EpochPlan:
    """What activating an epoch would do, computed against the current one."""

    epoch: int
    added: tuple[str, ...]
    removed: tuple[str, ...]
    unchanged: tuple[str, ...]
    budget: DailyBudget
    previous_budget: DailyBudget | None
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_activatable(self) -> bool:
        return not self.problems

    def render(self) -> str:
        """The dry run, as a person reads it."""
        lines = [f"epoch {self.epoch}"]
        lines.append(
            f"  budget: {self.budget.discovery} discovery, "
            f"{self.budget.verification} verification, "
            f"{self.budget.correction} correction "
            f"({self.budget.total} reads per local day)"
        )
        if self.previous_budget and self.previous_budget != self.budget:
            lines.append(
                f"  budget changes from {self.previous_budget.total} to {self.budget.total} "
                "reads per local day"
            )
        lines.append(f"  sources: {len(self.unchanged) + len(self.added)} enabled")
        for revision_id in self.added:
            lines.append(f"    + {revision_id}")
        for revision_id in self.removed:
            lines.append(f"    - {revision_id}")
        if not self.added and not self.removed:
            lines.append("    (no membership change)")
        for problem in self.problems:
            lines.append(f"  REFUSED: {problem}")
        return "\n".join(lines)


def current_epoch(store: Store) -> tuple[str, int, DailyBudget, tuple[str, ...]] | None:
    row = store.one("SELECT id, epoch, budget_json FROM diet_epochs ORDER BY epoch DESC LIMIT 1")
    if row is None:
        return None
    members = tuple(
        r["source_revision_id"]
        for r in store.query(
            "SELECT source_revision_id FROM diet_epoch_sources WHERE epoch_id = ? "
            "ORDER BY source_revision_id",
            row["id"],
        )
    )
    return row["id"], row["epoch"], DailyBudget(**json.loads(row["budget_json"])), members


def plan(store: Store, revision_ids: Sequence[str], budget: DailyBudget) -> EpochPlan:
    """Compute the exact effect of activating this diet, without activating it."""
    proposed = sorted(set(revision_ids))
    current = current_epoch(store)
    previous_members: set[str] = set(current[3]) if current else set()
    previous_budget = current[2] if current else None
    next_epoch = (current[1] + 1) if current else 1

    problems: list[str] = []
    for revision_id in proposed:
        if store.one("SELECT id FROM source_revisions WHERE id = ?", revision_id) is None:
            problems.append(f"unknown source revision: {revision_id}")
    if not proposed:
        problems.append("an epoch with no enabled source would stop acquisition silently")
    problems.extend(budget.problems())

    return EpochPlan(
        epoch=next_epoch,
        added=tuple(r for r in proposed if r not in previous_members),
        removed=tuple(sorted(previous_members - set(proposed))),
        unchanged=tuple(r for r in proposed if r in previous_members),
        budget=budget,
        previous_budget=previous_budget,
        problems=tuple(problems),
    )


def activate(store: Store, epoch_plan: EpochPlan, epoch_id: str, note: str, actor: str) -> str:
    """Write the epoch. Refuses a plan that its own dry run refused."""
    if not epoch_plan.is_activatable:
        raise ValueError(f"epoch is not activatable: {'; '.join(epoch_plan.problems)}")

    members = sorted({*epoch_plan.added, *epoch_plan.unchanged})
    with store.write() as connection:
        connection.execute(
            "INSERT INTO diet_epochs (id, epoch, budget_json, note, activated_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (epoch_id, epoch_plan.epoch, dumps(epoch_plan.budget), note),
        )
        connection.executemany(
            "INSERT INTO diet_epoch_sources (epoch_id, source_revision_id) VALUES (?, ?)",
            [(epoch_id, revision_id) for revision_id in members],
        )
        audit.record(
            connection,
            actor=actor,
            action="activate_diet_epoch",
            target=epoch_id,
            reason=note,
            preimage=json.dumps(
                {"added": list(epoch_plan.added), "removed": list(epoch_plan.removed)},
                sort_keys=True,
            ),
            result=f"epoch {epoch_plan.epoch} with {len(members)} sources",
        )
    return epoch_id


def enabled_revisions(store: Store, epoch_id: str) -> tuple[str, ...]:
    return tuple(
        row["source_revision_id"]
        for row in store.query(
            "SELECT source_revision_id FROM diet_epoch_sources WHERE epoch_id = ? "
            "ORDER BY source_revision_id",
            epoch_id,
        )
    )


def as_record(store: Store, epoch_id: str) -> dict[str, Any]:
    row = store.one("SELECT * FROM diet_epochs WHERE id = ?", epoch_id)
    if row is None:
        raise KeyError(epoch_id)
    return {
        "id": row["id"],
        "epoch": row["epoch"],
        "budget": json.loads(row["budget_json"]),
        "note": row["note"],
        "sources": list(enabled_revisions(store, epoch_id)),
    }
