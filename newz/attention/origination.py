"""Investigation origination: interest opening a question nobody asked for.

`SPEC.md` section 9.1 puts three requirements ahead of any task being created —
the question, the exit conditions, and the observation that would close it — and
the ordering is the discipline. An investigation that decides afterwards what
would have settled it can always find that something did.

Two bounds keep origination from becoming throughput. An originated
investigation gets **no additional read budget**: its tasks queue in the ordinary
lanes under the ordinary priority, and the counterpart brake applies unchanged.
And no more than a configured number may be open at once, so a system that finds
everything interesting cannot flood the queue the diet controls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from newz.attention.interest import (
    ORIGINATION_CEILING,
    load_interest,
    open_originated_investigations,
    record_outcome,
)
from newz.store.db import Store


class OriginationRefused(Exception):
    """Interest wanted to open something and could not. Recorded, not silent."""


@dataclass(frozen=True, slots=True)
class Origination:
    investigation_id: str
    interest_id: str
    question: str
    tasks: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "interest_id": self.interest_id,
            "question": self.question,
            "tasks": list(self.tasks),
        }


def originate(
    store: Store,
    *,
    interest_id: str,
    investigation_id: str,
    question: str,
    exit_conditions: tuple[str, ...],
    closing_observation: str,
    claim_id: str,
    claim_kind,
    now: datetime,
    rationale: str = "",
    ceiling: int = ORIGINATION_CEILING,
) -> Origination:
    """Open an investigation from an interest, then generate its tasks.

    The order in this function is the requirement: the investigation exists,
    with its exit conditions, before `generate_tasks` is reached. Nothing here
    touches a budget or a lane — the tasks land in the queue the diet controls,
    exactly as an operator-opened investigation's would.
    """
    from newz.research.investigations import open_investigation
    from newz.research.tasks import generate_tasks

    entry = load_interest(store, interest_id)
    if entry.retired:
        raise OriginationRefused(f"{interest_id} is retired")

    open_now = open_originated_investigations(store)
    if open_now >= ceiling:
        raise OriginationRefused(
            f"{open_now} self-originated investigations are already open, and the ceiling "
            f"is {ceiling}: origination may not flood the queue the diet controls"
        )

    open_investigation(
        store,
        investigation_id=investigation_id,
        question=question,
        rationale=rationale or entry.rationale,
        exit_conditions=exit_conditions,
        closing_observation=closing_observation,
        origin="interest",
        claim_ids=(claim_id,),
        actor=f"interest:{interest_id}",
    )
    record_outcome(store, interest_id, "investigation", investigation_id)
    generated = generate_tasks(store, claim_id, claim_kind, now)

    return Origination(
        investigation_id=investigation_id,
        interest_id=interest_id,
        question=question,
        tasks=tuple(task.id for task in generated if task.created),
    )
