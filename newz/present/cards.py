"""The claim card: every field `SPEC.md` section 10 requires, and no others.

The rule that shapes this module is that a card carries no sentence that is not
already a row. There is no summarizer here and no model call — the "important
context", the "what would change this" line and the counterevidence are all
projections of edges, tasks and thresholds. A card that needed prose written for
it would be a card whose claims could not be audited back to a span.

Every card records exactly what it rests on, so that when one of those things
changes the card is known to be stale rather than assumed to be current.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from newz.canonical import digest
from newz.domain.enums import EdgeRelation, RiskTier
from newz.evidence.assess import assessment_history, current_assessment, evidence_input
from newz.evidence.edges import load_edges
from newz.research.packets import evidence_packet
from newz.store.db import Store
from newz.version import CODE_VERSION, POLICY_VERSION


@dataclass(frozen=True, slots=True)
class CardEvidence:
    edge_id: str
    relation: str
    role: str
    assertion_kind: str
    quote: str
    locator: str
    artifact_id: str
    source_revision_id: str
    basis_id: str
    first_seen_at: str
    retrieved_from: str
    counted: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "relation": self.relation,
            "role": self.role,
            "assertion_kind": self.assertion_kind,
            "quote": self.quote,
            "locator": self.locator,
            "artifact_id": self.artifact_id,
            "source_revision_id": self.source_revision_id,
            "basis_id": self.basis_id,
            "first_seen_at": self.first_seen_at,
            "retrieved_from": self.retrieved_from,
            "counted": self.counted,
        }


@dataclass(frozen=True, slots=True)
class ClaimCard:
    claim_id: str
    wording: str
    claim_kind: str
    state: str
    risk: str
    original_claimant: str
    first_known_date: str
    supporting: tuple[CardEvidence, ...]
    contradicting: tuple[CardEvidence, ...]
    context: tuple[CardEvidence, ...]
    supporting_bases: int
    contradicting_bases: int
    independence_note: str
    missing_evidence: tuple[str, ...]
    active_tasks: tuple[tuple[str, str], ...]
    blocked_lanes: tuple[tuple[str, str, str], ...]
    history: tuple[tuple[str, str], ...]
    what_would_change_this: str
    limitations: tuple[str, ...]
    policy_version: str
    code_version: str
    assessed_at: str
    #: Everything the card rests on, by kind. The validator walks it.
    dependencies: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "wording": self.wording,
            "claim_kind": self.claim_kind,
            "state": self.state,
            "risk": self.risk,
            "original_claimant": self.original_claimant,
            "first_known_date": self.first_known_date,
            "supporting": [item.as_record() for item in self.supporting],
            "contradicting": [item.as_record() for item in self.contradicting],
            "context": [item.as_record() for item in self.context],
            "supporting_bases": self.supporting_bases,
            "contradicting_bases": self.contradicting_bases,
            "independence_note": self.independence_note,
            "missing_evidence": list(self.missing_evidence),
            "active_tasks": [list(task) for task in self.active_tasks],
            "blocked_lanes": [list(lane) for lane in self.blocked_lanes],
            "history": [list(entry) for entry in self.history],
            "what_would_change_this": self.what_would_change_this,
            "limitations": list(self.limitations),
            "policy_version": self.policy_version,
            "code_version": self.code_version,
            "assessed_at": self.assessed_at,
            "dependencies": {kind: list(ids) for kind, ids in sorted(self.dependencies.items())},
        }

    @property
    def content_hash(self) -> str:
        record = self.as_record()
        # The build time is not part of the identity: rebuilding an unchanged
        # card must produce the same revision, or every rebuild looks like a
        # correction.
        record.pop("assessed_at", None)
        return digest(record)


def _evidence_rows(store: Store, inputs, counted: set[str]) -> dict[str, list[CardEvidence]]:
    grouped: dict[str, list[CardEvidence]] = {"supports": [], "contradicts": [], "contextualizes": []}
    for edge in load_edges(store, inputs.claim.id):
        assertion = inputs.assertions.get(edge.assertion_id)
        if assertion is None or not assertion.spans:
            continue
        span = assertion.spans[0]
        sighting = store.one(
            "SELECT s.observed_at, r.final_url FROM sightings s "
            "JOIN responses r ON r.id = s.response_id WHERE s.artifact_id = ? "
            "ORDER BY s.observed_at LIMIT 1",
            span.artifact_id,
        )
        row = CardEvidence(
            edge_id=edge.id,
            relation=edge.relation.value,
            role=edge.role.value,
            assertion_kind=edge.assertion_kind.value,
            quote=span.quote,
            locator=span.locator,
            artifact_id=span.artifact_id,
            source_revision_id=assertion.source_revision_id,
            basis_id=edge.basis_id,
            first_seen_at=sighting["observed_at"] if sighting else "",
            retrieved_from=sighting["final_url"] if sighting else "",
            counted=edge.id in counted,
        )
        if edge.relation is EdgeRelation.SUPPORTS:
            grouped["supports"].append(row)
        elif edge.relation is EdgeRelation.CONTRADICTS:
            grouped["contradicts"].append(row)
        else:
            grouped["contextualizes"].append(row)
    return grouped


def _independence_note(edges: list[CardEvidence], counted_bases: int) -> str:
    """Say plainly when several citations rest on one origin."""
    counted = [item for item in edges if item.counted]
    if not counted:
        return "no countable basis"
    distinct_citations = len({item.basis_id for item in counted})
    if counted_bases < distinct_citations:
        return (
            f"{distinct_citations} citations resolve to {counted_bases} independent "
            "basis" + ("" if counted_bases == 1 else "es")
        )
    if counted_bases == 1:
        return "one independent basis"
    return f"{counted_bases} independent bases"


def _limitations(inputs, supporting: list[CardEvidence], contradicting: list[CardEvidence]) -> tuple[str, ...]:
    """Stated limits, computed from what the record does and does not hold."""
    notes: list[str] = []
    if inputs.claim.kind.value == "forecast" and not inputs.horizon_reached:
        notes.append(
            "This is a forecast. It holds at reported until its resolution horizon, "
            "whatever evidence accumulates."
        )
    if inputs.claim.kind.value == "normative_proposition":
        notes.append(
            "This is a normative proposition. The promotion rules cannot evaluate it, "
            "so it is recorded and attributed rather than assessed."
        )
    testimony_only = supporting and all(
        item.assertion_kind == "testimony" for item in supporting if item.counted
    )
    if testimony_only:
        notes.append(
            "Every counted supporting item is testimony. That establishes that the "
            "reports were made, not that the events occurred."
        )
    if contradicting and not supporting:
        notes.append("Nothing in the record supports this claim.")
    if inputs.claim.risk is RiskTier.R3:
        notes.append(
            "This claim concerns a living party at R3. Publication requires operator "
            "approval of the exact revision."
        )
    return tuple(notes)


def claim_card(store: Store, claim_id: str) -> ClaimCard:
    """Project the card. Reads the graph; writes nothing."""
    inputs = evidence_input(store, claim_id)
    assessment = current_assessment(store, claim_id)
    if assessment is None:
        raise ValueError(f"{claim_id} has no assessment; a card is a view of one")

    counted = set(assessment.countable_edge_ids)
    grouped = _evidence_rows(store, inputs, counted)
    packet = evidence_packet(store, claim_id)

    claimant = ""
    first_seen = ""
    origin = store.one(
        "SELECT c.quote, a.recorded_at, s.name FROM claim_origins c "
        "LEFT JOIN artifacts art ON art.id = c.artifact_id "
        "LEFT JOIN sightings sg ON sg.artifact_id = c.artifact_id "
        "LEFT JOIN source_revisions sr ON sr.id = sg.source_revision_id "
        "LEFT JOIN sources s ON s.id = sr.source_id "
        "LEFT JOIN assertions a ON a.artifact_id = c.artifact_id "
        "WHERE c.claim_id = ? ORDER BY c.extraction_run_id LIMIT 1",
        claim_id,
    )
    if origin is not None:
        claimant = origin["name"] or ""
        first_seen = origin["recorded_at"] or ""
    earliest = min(
        (item.first_seen_at for item in grouped["supports"] + grouped["contradicts"] if item.first_seen_at),
        default=first_seen,
    )

    active = tuple(
        (task.lane.value, task.state.value)
        for task in sorted(inputs.tasks, key=lambda t: t.id)
        if task.state.value in ("open", "scheduled", "in_progress", "blocked")
    )

    dependencies = {
        "claim": (claim_id,),
        "edge": tuple(sorted(item.edge_id for group in grouped.values() for item in group)),
        "assessment": (f"{claim_id}@{assessment.policy_version}",),
        "artifact": tuple(
            sorted({item.artifact_id for group in grouped.values() for item in group})
        ),
    }

    return ClaimCard(
        claim_id=claim_id,
        wording=inputs.claim.wording,
        claim_kind=inputs.claim.kind.value,
        state=assessment.state.value,
        risk=(inputs.claim.risk or RiskTier.R3).value,
        original_claimant=claimant,
        first_known_date=earliest,
        supporting=tuple(grouped["supports"]),
        contradicting=tuple(grouped["contradicts"]),
        context=tuple(grouped["contextualizes"]),
        supporting_bases=assessment.supporting_bases,
        contradicting_bases=assessment.contradicting_bases,
        independence_note=_independence_note(
            grouped["supports"] + grouped["contradicts"],
            assessment.supporting_bases + assessment.contradicting_bases,
        ),
        missing_evidence=packet.missing_lanes,
        active_tasks=active,
        blocked_lanes=tuple(
            (lane.value, state.value, reason) for lane, state, reason in assessment.blocked_lanes
        ),
        history=tuple((entry.state.value, entry.explanation) for entry in assessment_history(store, claim_id)),
        what_would_change_this=packet.what_would_change_it,
        limitations=_limitations(inputs, grouped["supports"], grouped["contradicts"]),
        policy_version=assessment.policy_version,
        code_version=assessment.code_version,
        assessed_at="",
        dependencies=dependencies,
    )


def build_card(store: Store, claim_id: str, revision_id: str) -> tuple[str, bool]:
    """Persist a card revision if it differs from the live one.

    Returns the revision id in force and whether a new one was built. Rebuilding
    an unchanged card is a no-op: every rebuild looking like a correction would
    make the correction notice worthless.
    """
    card = claim_card(store, claim_id)
    live = store.one(
        "SELECT * FROM card_revisions WHERE claim_id = ? AND live = 1 ORDER BY revision DESC LIMIT 1",
        claim_id,
    )
    if live is not None and live["content_hash"] == card.content_hash:
        return live["id"], False

    next_revision = (
        store.one("SELECT COALESCE(MAX(revision), 0) AS r FROM card_revisions WHERE claim_id = ?", claim_id)["r"]
        + 1
    )
    with store.write() as connection:
        # The successor is written first: the predecessor's `superseded_by`
        # points at it, and a foreign key cannot be satisfied by a row that is
        # about to exist.
        connection.execute(
            "INSERT INTO card_revisions (id, claim_id, revision, content_json, content_hash, "
            "policy_version, code_version, risk, state, live, built_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))",
            (
                revision_id,
                claim_id,
                next_revision,
                json.dumps(card.as_record(), sort_keys=True),
                card.content_hash,
                card.policy_version or POLICY_VERSION,
                card.code_version or CODE_VERSION,
                card.risk,
                card.state,
            ),
        )
        if live is not None:
            connection.execute(
                "UPDATE card_revisions SET live = 0, superseded_by = ? WHERE id = ?",
                (revision_id, live["id"]),
            )
        connection.executemany(
            "INSERT OR IGNORE INTO card_dependencies (card_revision_id, kind, dependency_id) "
            "VALUES (?, ?, ?)",
            [
                (revision_id, kind, dependency)
                for kind, ids in sorted(card.dependencies.items())
                for dependency in ids
            ],
        )
    return revision_id, True


def load_card(store: Store, revision_id: str) -> dict[str, Any]:
    row = store.one("SELECT * FROM card_revisions WHERE id = ?", revision_id)
    if row is None:
        raise KeyError(revision_id)
    return json.loads(row["content_json"])


def render_card(card: ClaimCard) -> str:
    """The card as a person reads it. Composed from the projection, not written."""
    lines = [
        card.wording,
        f"[{card.claim_kind}] {card.state} — risk {card.risk}",
        f"Assessed under policy {card.policy_version}, code {card.code_version}.",
        "",
    ]
    if card.original_claimant:
        lines.append(f"First recorded from {card.original_claimant} at {card.first_known_date}.")
        lines.append("")

    for title, items in (("Supporting", card.supporting), ("Contradicting", card.contradicting)):
        if not items:
            continue
        lines.append(f"{title}:")
        for item in items:
            mark = "counted" if item.counted else "not counted"
            lines.append(f"  [{mark}] {item.assertion_kind} by {item.role}, {item.locator}")
            lines.append(f'    "{item.quote}"')
            lines.append(f"    {item.retrieved_from or item.artifact_id}")
        lines.append("")

    lines.append(
        f"Bases: {card.supporting_bases} supporting, {card.contradicting_bases} contradicting "
        f"({card.independence_note})."
    )
    if card.missing_evidence:
        lines.append(f"Missing evidence: {', '.join(card.missing_evidence)}.")
    for lane, state, reason in card.blocked_lanes:
        lines.append(f"Lane {lane} ended {state}: {reason}")
    if card.limitations:
        lines.append("")
        for note in card.limitations:
            lines.append(f"Note: {note}")
    lines.append("")
    lines.append(f"What would change this: {card.what_would_change_this}.")
    if len(card.history) > 1:
        lines.append("")
        lines.append("History:")
        for state, explanation in card.history:
            lines.append(f"  {state} — {explanation}")
    return "\n".join(lines)
