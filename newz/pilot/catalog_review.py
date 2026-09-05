"""Reviewing a proposed pilot catalog against what `SPEC.md` section 5.2 requires.

This validates a slate. It does not choose one — which publications this system
reads is a decision about what enters the record, and it belongs to the operator
rather than to the code that will read them.

What the section requires is countable, so it is counted here: twenty reviewed
slots in a stated role distribution, all eight initial topics covered, full text
retained where evidence is possible, no more than two sources from one
publisher, and a counterpart task scheduled for every claimant-led discovery.

Each slot must also record what `PLAN.md` Phase 5 item 1 asks for — retention
rights, observed MIME, full-text capability, publisher, independence group,
role, declared scope, risk and counterpart behaviour — because a slot that
cannot say its retention terms is a slot nobody has actually reviewed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from newz.domain.enums import RetentionPolicy, RiskTier, SourceRole

#: `SPEC.md` section 5.2, the required shape of the twenty.
REQUIRED_SLOTS: dict[str, int] = {
    "claimant_or_firsthand": 5,
    "primary_or_adjudicative": 6,
    "empirical_or_replication": 4,
    "skeptical_or_forensic": 3,
    "historical_or_general_context": 2,
}

SLOT_ROLES: dict[str, frozenset[SourceRole]] = {
    "claimant_or_firsthand": frozenset({SourceRole.CLAIMANT, SourceRole.FIRSTHAND_WITNESS}),
    "primary_or_adjudicative": frozenset({SourceRole.PRIMARY_RECORD, SourceRole.ADJUDICATOR}),
    "empirical_or_replication": frozenset({SourceRole.EMPIRICAL_STUDY}),
    "skeptical_or_forensic": frozenset({SourceRole.SKEPTICAL_INVESTIGATION}),
    "historical_or_general_context": frozenset(
        {SourceRole.HISTORICAL_CONTEXT, SourceRole.GENERAL_CONTEXT}
    ),
}

#: `SPEC.md` section 3. All eight must be covered.
REQUIRED_TOPICS = (
    "uap_and_aerospace_anomalies",
    "psi_and_consciousness_claims",
    "alternative_physics_and_energy",
    "forteana_cryptids_and_anomalous_natural_events",
    "anomalous_history_and_archaeology",
    "declassified_material_and_historical_secrecy",
    "metascience_methods_and_replication",
    "general_scientific_and_institutional_context",
)

MAX_PER_PUBLISHER = 2


@dataclass(frozen=True, slots=True)
class ProposedSlot:
    """One reviewed source, with everything a review must have established."""

    source_id: str
    publisher: str
    topic: str
    role: SourceRole
    declared_scope: str
    risk_floor: RiskTier
    retention_policy: RetentionPolicy
    observed_mime: str
    full_text_capable: bool
    retention_rights: str
    independence_group: str | None = None
    counterpart_behaviour: str = ""

    def slot_kind(self) -> str:
        for kind, roles in SLOT_ROLES.items():
            if self.role in roles:
                return kind
        return "unclassified"

    def problems(self) -> list[str]:
        out: list[str] = []
        if not self.retention_rights.strip():
            out.append("retention rights not established")
        if not self.observed_mime.strip():
            out.append("MIME not observed")
        if not self.declared_scope.strip():
            out.append("declared scope missing")
        if self.full_text_capable and self.retention_policy is not RetentionPolicy.FULL_TEXT:
            out.append("full text is possible but retention is not set to full text")
        if not self.full_text_capable and self.retention_policy is RetentionPolicy.FULL_TEXT:
            out.append("full-text retention claimed where full text is not available")
        if self.role in SLOT_ROLES["claimant_or_firsthand"] and not self.counterpart_behaviour:
            out.append(
                "a claimant-led source records its counterpart behaviour: every claimant-led "
                "discovery mandates a counterpart task"
            )
        return out


@dataclass(frozen=True, slots=True)
class CatalogReview:
    slots: tuple[ProposedSlot, ...]
    problems: tuple[str, ...] = field(default_factory=tuple)

    @property
    def acceptable(self) -> bool:
        return not self.problems

    def as_record(self) -> dict[str, Any]:
        return {
            "slots": len(self.slots),
            "by_kind": self.by_kind(),
            "topics_covered": sorted({slot.topic for slot in self.slots}),
            "problems": list(self.problems),
            "acceptable": self.acceptable,
        }

    def by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = dict.fromkeys(REQUIRED_SLOTS, 0)
        for slot in self.slots:
            counts[slot.slot_kind()] = counts.get(slot.slot_kind(), 0) + 1
        return counts


def review(slots: list[ProposedSlot]) -> CatalogReview:
    """Check a proposed slate. Reports every problem rather than the first."""
    problems: list[str] = []

    if len(slots) != 20:
        problems.append(f"the pilot contains 20 reviewed slots; this has {len(slots)}")

    counts: dict[str, int] = dict.fromkeys(REQUIRED_SLOTS, 0)
    for slot in slots:
        counts[slot.slot_kind()] = counts.get(slot.slot_kind(), 0) + 1
    for kind, required in REQUIRED_SLOTS.items():
        if counts.get(kind, 0) != required:
            problems.append(f"{kind}: {counts.get(kind, 0)} slots, {required} required")
    if counts.get("unclassified"):
        problems.append(f"{counts['unclassified']} slot(s) hold a role no bucket covers")

    missing_topics = sorted(set(REQUIRED_TOPICS) - {slot.topic for slot in slots})
    if missing_topics:
        problems.append(f"topics not covered: {', '.join(missing_topics)}")

    per_publisher: dict[str, int] = {}
    for slot in slots:
        per_publisher[slot.publisher] = per_publisher.get(slot.publisher, 0) + 1
    for publisher, count in sorted(per_publisher.items()):
        if count > MAX_PER_PUBLISHER:
            problems.append(f"{publisher}: {count} sources, at most {MAX_PER_PUBLISHER} permitted")

    for slot in slots:
        for problem in slot.problems():
            problems.append(f"{slot.source_id}: {problem}")

    return CatalogReview(slots=tuple(slots), problems=tuple(problems))


def outstanding_for_operator() -> list[str]:
    """What only the operator can supply before the pilot can start.

    Written as a list rather than a paragraph because it is a checklist, and
    because the code that will read these sources should not be the thing that
    chose them.
    """
    return [
        f"{count} {kind.replace('_', ' ')} source(s)" for kind, count in REQUIRED_SLOTS.items()
    ] + [
        "covering all eight initial topics",
        "no more than two from any one publisher",
        "each with retention rights established in writing",
        "each with its independence group recorded where one applies",
        "each with an observed MIME and a fixture captured from it",
    ]
