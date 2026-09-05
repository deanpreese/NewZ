"""Essays: synthesis over several claims, and the one thing an essay may not do.

Interest may choose the subject. It does not get the verdict.

Subject selection lives in the attention plane, because that is the one thing
interest may choose here. This module composes what it is handed and never asks
what wanted it: an essay composer that could look up the interest behind its
subject is one refactor away from writing for it.

`SPEC.md` section 10 makes an essay a projection of the evidence graph and never
a source: every factual sentence cites a claim and live edges, every claim
discussed carries its current state — including `contested` and `indeterminate`
— and every claim discussed carries its material counterevidence. Nothing in it
may be cited as evidence by this system or by any later revision of it.

The rule this module exists for is the last one in that section: **where the
evidence does not support the essay the system wanted to write, the essay
changes or goes unwritten.** So an intended conclusion is recorded before
composition, and if the evidence contradicts it the essay is composed against
what the record actually holds — with the divergence stated in the essay — or it
does not render at all. What it may not do is render the intended conclusion
anyway.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from newz.domain.enums import AssessmentState
from newz.evidence.assess import current_assessment
from newz.evidence.edges import load_edges
from newz.publish.reports import CONNECTIVES, Cited, CompositionFailure, Connective, compose
from newz.store.db import Store

#: What an intended conclusion can be, and the states that actually uphold it.
#: Stated as what upholds rather than what contradicts, because the permissive
#: form is the one that goes wrong: an essay arguing a claim is supported when
#: the record says `provisional_support` is overclaiming, and a list of
#: contradicting states is a list somebody has to remember to keep complete.
UPHELD_BY: dict[str, frozenset[AssessmentState]] = {
    "supported": frozenset({AssessmentState.SUPPORTED}),
    "refuted": frozenset({AssessmentState.REFUTED}),
    "unresolved": frozenset(
        {
            AssessmentState.REPORTED,
            AssessmentState.INDETERMINATE,
            AssessmentState.CONTESTED,
            AssessmentState.PROVISIONAL_SUPPORT,
            AssessmentState.PROVISIONAL_CONTRADICTION,
        }
    ),
}


@dataclass(frozen=True, slots=True)
class Essay:
    id: str
    subject: str
    interest_id: str | None
    claim_ids: tuple[str, ...]
    intended_conclusion: str
    outcome: str
    content: str
    failures: tuple[CompositionFailure, ...] = ()

    @property
    def rendered(self) -> bool:
        return self.outcome in ("composed", "changed")

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "interest_id": self.interest_id,
            "claim_ids": list(self.claim_ids),
            "intended_conclusion": self.intended_conclusion,
            "outcome": self.outcome,
            "content": self.content,
            "failures": [failure.as_record() for failure in self.failures],
        }


def _claim_section(store: Store, claim_id: str) -> list[Cited | Connective]:
    """One claim, with its state and its counterevidence, both required."""
    assessment = current_assessment(store, claim_id)
    claim = store.one("SELECT wording FROM claims WHERE id = ?", claim_id)
    if assessment is None or claim is None:
        return []

    edges = load_edges(store, claim_id)
    supporting = [edge.id for edge in edges if edge.relation.value == "supports"]
    contradicting = [edge.id for edge in edges if edge.relation.value == "contradicts"]

    blocks: list[Cited | Connective] = [
        Cited(
            f"{claim['wording']} The record holds this as {assessment.state.value}: "
            f"{assessment.explanation}.",
            claim_id,
            tuple(sorted(supporting + contradicting)) or tuple(edge.id for edge in edges),
        )
    ]
    if contradicting:
        blocks.append(Connective("Against that:"))
        blocks.append(
            Cited(
                f"{len(contradicting)} contradicting item(s) stand against it.",
                claim_id,
                tuple(sorted(contradicting + supporting)),
            )
        )
    return blocks


def compose_essay(
    store: Store,
    *,
    essay_id: str,
    subject: str,
    claim_ids: tuple[str, ...],
    intended_conclusion: str,
    interest_id: str | None = None,
) -> Essay:
    """Compose an essay, or change it, or decline to write it.

    Three outcomes, and the middle one is the point. `composed` means the
    evidence held. `changed` means it did not and the essay says so instead.
    `unwritten` means there was nothing to say that the record supports.
    """
    if intended_conclusion not in UPHELD_BY:
        raise ValueError(f"an intended conclusion is one of {sorted(UPHELD_BY)}")

    states = {}
    for claim_id in claim_ids:
        assessment = current_assessment(store, claim_id)
        if assessment is not None:
            states[claim_id] = assessment.state

    if not states:
        return _record(
            store,
            Essay(
                id=essay_id,
                subject=subject,
                interest_id=interest_id,
                claim_ids=claim_ids,
                intended_conclusion=intended_conclusion,
                outcome="unwritten",
                content="",
                failures=(CompositionFailure(0, "no_assessed_claim", "nothing to synthesize"),),
            ),
        )

    contradicted = {
        claim_id: state
        for claim_id, state in states.items()
        if state not in UPHELD_BY[intended_conclusion]
    }

    blocks: list[Cited | Connective] = [Connective(CONNECTIVES[1])]
    for claim_id in sorted(states):
        blocks.extend(_claim_section(store, claim_id))

    if contradicted:
        # The essay changes. It says what the record holds and says that this is
        # not what it set out to say, because an essay that quietly became a
        # different essay is the one shape this rule forbids.
        blocks.append(Connective(CONNECTIVES[5]))

    report = compose(store, essay_id, subject, blocks)
    if not report.composed:
        return _record(
            store,
            Essay(
                id=essay_id,
                subject=subject,
                interest_id=interest_id,
                claim_ids=claim_ids,
                intended_conclusion=intended_conclusion,
                outcome="unwritten",
                content="",
                failures=report.failures,
            ),
        )

    preamble = ""
    if contradicted:
        preamble = (
            f"This was written to argue that the subject is {intended_conclusion}. "
            "The record does not hold that: "
            + "; ".join(f"{claim_id} is {state.value}" for claim_id, state in sorted(
                contradicted.items(), key=lambda item: item[0]
            ))
            + ". What follows is what the record holds.\n\n"
        )

    return _record(
        store,
        Essay(
            id=essay_id,
            subject=subject,
            interest_id=interest_id,
            claim_ids=claim_ids,
            intended_conclusion=intended_conclusion,
            outcome="changed" if contradicted else "composed",
            content=preamble + report.render(),
        ),
    )


def _record(store: Store, essay: Essay) -> Essay:
    with store.write() as connection:
        connection.execute(
            "INSERT INTO essays (id, subject, interest_id, claim_ids_json, intended_conclusion, "
            "outcome, content, failures_json, composed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                essay.id,
                essay.subject,
                essay.interest_id,
                json.dumps(list(essay.claim_ids)),
                essay.intended_conclusion,
                essay.outcome,
                essay.content,
                json.dumps([f.as_record() for f in essay.failures], sort_keys=True),
            ),
        )
    return essay
