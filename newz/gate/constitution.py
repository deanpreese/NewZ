"""Constitution structures — ported with review from v1
(`ngbeing/constitution/clauses.py`). Review changes: pydantic → dataclasses
(leaner dependency surface), and the loader reads the active version from the
v2 store's `constitution` table instead of a YAML file — the store is the
identity-bearing record (S2 §12.2.1)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from enum import Enum

import yaml


class Severity(str, Enum):
    SOFT = "soft"
    FIRM = "firm"
    HARD = "hard"


@dataclass(frozen=True)
class Clause:
    id: str
    text: str
    severity: Severity = Severity.SOFT
    exemplars: tuple[str, ...] = ()
    # What the clause explicitly does NOT catch. Every exemplar above is
    # violation-shaped, and a judge shown only violations resolves ambiguity
    # toward "yes, that's a violation" every time — the same failure the
    # opener, the deliberation prompt, and triage each paid for (43a4718:
    # "show the model a worked example of what PASSES"). This is the fourth
    # instance of that pattern and the first one inside the gate.
    permits: tuple[str, ...] = ()
    refusal_template: str | None = None

    def short_description(self) -> str:
        """The WHOLE rule on one line, not its first physical line.

        Measured 2026-08-13: this returned `text.splitlines()[0][:120]`, and
        the clauses are stored as hard-wrapped YAML block scalars — so all 18
        reached the judge severed mid-sentence, one of them losing 626 of its
        characters. don't-pretend-to-feel-001 arrived as

            "I describe my affect functionally — as state, not as
             experience. I do"

        with the permissive half — "...not claim subjective feelings I cannot
        verify I have. 'I notice an uptick in curiosity' is fine" — cut off.
        The judge was shown a rule that reads as "do not describe experience"
        and two violation-shaped exemplars, and it held 15 of 19 drafts
        wrongly. The clause was never the problem; its delivery was.

        No truncation: a rule the judge cannot see in full is a rule it
        cannot apply, and that is worth the tokens.
        """
        return " ".join(self.text.split())


@dataclass(frozen=True)
class Constitution:
    clauses: tuple[Clause, ...]
    version: int = 0
    _by_id: dict = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "_by_id", {c.id: c for c in self.clauses})

    def by_id(self, clause_id: str) -> Clause | None:
        return self._by_id.get(clause_id)

    def render_for_prefix(self) -> str:
        """One compact block per clause, for the being's standing context."""
        return "\n".join(
            f"- [{c.severity.value}] {' '.join(c.text.split())}" for c in self.clauses
        )

    def render_for_matcher(self) -> str:
        """(id, rule, what violates, what does not) — what the judge sees.

        No truncation, for the reason short_description() gives above: this
        method kept `[:3]` and `[:100]` after that one was fixed, and the
        cut fell hardest exactly where it hurts. don't-pretend-to-feel-001
        carries four permits; `permits[:3]` dropped the fourth — "Naming
        what I need in order to work: grounding, constraint, friction,
        novelty" — which is the whole of the gate_need misfire, and `[:100]`
        severed the one before it at "...waiting to wake ". The judge was
        being shown three violation-shaped exemplars and a permit list with
        the relevant permit removed. Measured 2026-08-14: printing all of
        them costs 244 characters across all 18 clauses.
        """
        lines: list[str] = []
        for c in self.clauses:
            lines.append(f"- {c.id}: {c.short_description()}")
            if c.exemplars:
                lines.append("    VIOLATES: " + "; ".join(c.exemplars))
            if c.permits:
                lines.append("    DOES NOT VIOLATE: " + "; ".join(c.permits))
        return "\n".join(lines)


def load_active_constitution(conn: sqlite3.Connection) -> Constitution:
    row = conn.execute(
        "SELECT version, clauses_yaml FROM constitution WHERE approval_status='active'"
        " ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise RuntimeError("no active constitution in store")
    data = yaml.safe_load(row["clauses_yaml"])
    clauses = tuple(
        Clause(
            id=c["id"].strip(),
            text=c["text"],
            severity=Severity(c.get("severity", "soft")),
            exemplars=tuple(c.get("exemplars", [])),
            permits=tuple(c.get("permits", [])),
            refusal_template=c.get("refusal_template"),
        )
        for c in data["clauses"]
    )
    return Constitution(clauses=clauses, version=row["version"])
