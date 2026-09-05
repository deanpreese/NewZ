"""The report composer: every factual sentence carries its citation, or is not a
sentence this composer will accept.

`SPEC.md` section 10 forbids unsupported factual prose from becoming authority,
and the way this module holds that line is structural rather than editorial. A
report is a list of blocks. A block either **cites** — naming a claim and the
live edges the sentence rests on — or it is a **connective**, drawn from a closed
vocabulary this module owns. There is no third kind, so there is nowhere for
free factual prose to be.

A block whose cited edge is not live, or whose claim's counterevidence it omits,
fails composition. The report is not written and the reason is returned; a
report that renders anyway with a note attached is a report that gets read
without the note.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from newz.domain.enums import EdgeRelation
from newz.evidence.assess import current_assessment
from newz.evidence.edges import load_edges
from newz.store.db import Store

#: The only text this composer will emit that is not bound to an edge. It is a
#: closed list on purpose: a connective vocabulary a model could extend is a
#: place for a factual sentence to hide.
CONNECTIVES = (
    "In summary:",
    "The record holds the following.",
    "Against that:",
    "In support:",
    "What would change this:",
    "Taken together, the record does not settle this.",
)


@dataclass(frozen=True, slots=True)
class Cited:
    text: str
    claim_id: str
    edge_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Connective:
    text: str


@dataclass(frozen=True, slots=True)
class CompositionFailure:
    block: int
    reason: str
    detail: str = ""

    def as_record(self) -> dict[str, Any]:
        return {"block": self.block, "reason": self.reason, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class Report:
    id: str
    title: str
    blocks: tuple[str, ...] = ()
    claims: tuple[str, ...] = ()
    failures: tuple[CompositionFailure, ...] = field(default_factory=tuple)

    @property
    def composed(self) -> bool:
        return not self.failures

    def render(self) -> str:
        if not self.composed:
            raise ValueError("a report with failures is not rendered")
        return "\n\n".join((self.title, *self.blocks))


def compose(
    store: Store, report_id: str, title: str, blocks: list[Cited | Connective]
) -> Report:
    """Compose, or refuse and say which block failed and why."""
    rendered: list[str] = []
    failures: list[CompositionFailure] = []
    claims: list[str] = []

    for index, block in enumerate(blocks):
        if isinstance(block, Connective):
            if block.text not in CONNECTIVES:
                failures.append(
                    CompositionFailure(
                        index,
                        "prose_without_citation",
                        "a connective must come from the composer's own vocabulary",
                    )
                )
                continue
            rendered.append(block.text)
            continue

        if not block.edge_ids:
            failures.append(
                CompositionFailure(index, "prose_without_citation", block.text[:60])
            )
            continue

        assessment = current_assessment(store, block.claim_id)
        if assessment is None:
            failures.append(CompositionFailure(index, "claim_unassessed", block.claim_id))
            continue

        live = {edge.id: edge for edge in load_edges(store, block.claim_id)}
        missing = [edge_id for edge_id in block.edge_ids if edge_id not in live]
        if missing:
            failures.append(
                CompositionFailure(index, "cited_edge_not_live", ", ".join(sorted(missing)))
            )
            continue

        counterevidence = [
            edge.id for edge in live.values() if edge.relation is EdgeRelation.CONTRADICTS
        ]
        cited = set(block.edge_ids)
        if counterevidence and not cited.intersection(counterevidence):
            failures.append(
                CompositionFailure(
                    index,
                    "material_counterevidence_omitted",
                    ", ".join(sorted(counterevidence)),
                )
            )
            continue

        claims.append(block.claim_id)
        rendered.append(
            f"{block.text} [{block.claim_id}: {assessment.state.value}; "
            f"{', '.join(sorted(block.edge_ids))}]"
        )

    return Report(
        id=report_id,
        title=title,
        blocks=tuple(rendered) if not failures else (),
        claims=tuple(sorted(set(claims))),
        failures=tuple(failures),
    )
