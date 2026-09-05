"""The record shapes Phase 0 freezes.

These are pure data. Nothing here reads a clock, a store, or the network: times
arrive as inputs so that a derivation reproduces (`SPEC.md` section 13).

The attention and reckoning shapes land here rather than at the phase that
builds them, because `PLAN.md` Phase 0 freezes the record types and a type added
later is a migration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from newz.domain.enums import (
    AdmissionPredicate,
    AssertionKind,
    AssessmentState,
    ClaimKind,
    DecisionOutcome,
    EdgeRelation,
    EvidenceLane,
    IndependenceJustification,
    NoticeProvenanceKind,
    OutcomeStatus,
    RefusalReason,
    RiskTier,
    SourceRole,
    TaskState,
)

# --------------------------------------------------------------------------
# Preservation
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Span:
    """An exact quotation with offsets and a locator inside retained segments.

    A span is valid only when its quotation matches retained text at the recorded
    offsets (`SPEC.md` section 6 item 6). `verified` is that check's result, not
    an intention to run it.
    """

    artifact_id: str
    segment_id: str
    start: int
    end: int
    quote: str
    locator: str
    verified: bool = False

    def as_record(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "segment_id": self.segment_id,
            "start": self.start,
            "end": self.end,
            "quote": self.quote,
            "locator": self.locator,
            "verified": self.verified,
        }


# --------------------------------------------------------------------------
# Semantics
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Assertion:
    """An atomic proposition that a source makes in one or more spans."""

    id: str
    kind: AssertionKind
    spans: tuple[Span, ...]
    source_revision_id: str
    role: SourceRole
    declared_scope: str = ""
    live: bool = True

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "spans": [s.as_record() for s in self.spans],
            "source_revision_id": self.source_revision_id,
            "role": self.role,
            "declared_scope": self.declared_scope,
            "live": self.live,
        }


@dataclass(frozen=True, slots=True)
class Claim:
    """An atomic proposition NewZ is investigating; distinct from an assertion."""

    id: str
    kind: ClaimKind
    wording: str
    risk: RiskTier | None = None
    #: Forecasts only. `SPEC.md` section 7.1.
    resolution_horizon: str | None = None
    resolver: str | None = None
    aliases: tuple[str, ...] = ()
    withdrawn: bool = False

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "wording": self.wording,
            "risk": self.risk,
            "resolution_horizon": self.resolution_horizon,
            "resolver": self.resolver,
            "aliases": list(self.aliases),
            "withdrawn": self.withdrawn,
        }


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Basis:
    """The upstream observation, witness, dataset, filing, experiment, or record
    on which evidence depends.

    `resolved` is basis *identity*: the origin is nameable and stable, even when
    it is a single unnamed witness reached through one publication. Independence
    is a separate, pairwise property and is not stored here.
    """

    id: str
    origin_kind: str
    origin_identifier: str
    resolved: bool
    independence_group: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "origin_kind": self.origin_kind,
            "origin_identifier": self.origin_identifier,
            "resolved": self.resolved,
            "independence_group": self.independence_group,
        }


@dataclass(frozen=True, slots=True)
class IndependenceClaim:
    """A pairwise assertion that two resolved bases are distinct.

    Consulted only when counting toward a threshold. Unknown or unjustified
    independence collapses the pair for counting and invalidates neither edge.
    """

    basis_a: str
    basis_b: str
    justification: IndependenceJustification
    evidence: str = ""
    operator_actor: str | None = None
    operator_reason: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "basis_a": self.basis_a,
            "basis_b": self.basis_b,
            "justification": self.justification,
            "evidence": self.evidence,
            "operator_actor": self.operator_actor,
            "operator_reason": self.operator_reason,
        }


@dataclass(frozen=True, slots=True)
class PredicateAttestation:
    """That one named admission predicate held or failed, with its inputs."""

    predicate: AdmissionPredicate
    held: bool
    inputs: tuple[tuple[str, str], ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate,
            "held": self.held,
            "inputs": [list(pair) for pair in self.inputs],
        }


@dataclass(frozen=True, slots=True)
class EdgeEvent:
    """A versioned relation from an assertion to a claim.

    Append-only: a withdrawal is a later event, never an edit. `admitted` and
    `refusal_reason` are the outcome of the policy engine, recorded on the event
    so the decision can be read without re-running it.
    """

    id: str
    assertion_id: str
    claim_id: str
    relation: EdgeRelation
    basis_id: str
    role: SourceRole
    assertion_kind: AssertionKind
    risk: RiskTier | None
    policy_version: str | None
    admitted: bool
    live: bool = True
    refusal_reason: RefusalReason | None = None
    attestations: tuple[PredicateAttestation, ...] = ()
    declared_scope: str = ""
    topic: str = ""
    #: Adjudicator edges only. `None` means unknown, which fails closed: the
    #: single-record exception of `SPEC.md` section 7.3 requires the record to
    #: settle the claim *within that adjudicator's declared scope*.
    adjudicative_scope_covers_claim: bool | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "assertion_id": self.assertion_id,
            "claim_id": self.claim_id,
            "relation": self.relation,
            "basis_id": self.basis_id,
            "role": self.role,
            "assertion_kind": self.assertion_kind,
            "risk": self.risk,
            "policy_version": self.policy_version,
            "admitted": self.admitted,
            "live": self.live,
            "refusal_reason": self.refusal_reason,
            "attestations": [a.as_record() for a in self.attestations],
            "declared_scope": self.declared_scope,
            "topic": self.topic,
            "adjudicative_scope_covers_claim": self.adjudicative_scope_covers_claim,
        }


@dataclass(frozen=True, slots=True)
class Assessment:
    """NewZ's evaluation of a claim at a point in time. Append-only.

    Carries the independent basis count in each direction, so `contested`
    preserves the shape of a disagreement rather than flattening a ten-to-one
    balance and a one-to-one balance into the same label.
    """

    claim_id: str
    state: AssessmentState
    supporting_bases: int
    contradicting_bases: int
    policy_version: str
    code_version: str
    explanation: str
    blocked_lanes: tuple[tuple[EvidenceLane, TaskState, str], ...] = ()
    countable_edge_ids: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "state": self.state,
            "supporting_bases": self.supporting_bases,
            "contradicting_bases": self.contradicting_bases,
            "policy_version": self.policy_version,
            "code_version": self.code_version,
            "explanation": self.explanation,
            "blocked_lanes": [[lane, state, reason] for lane, state, reason in self.blocked_lanes],
            "countable_edge_ids": list(self.countable_edge_ids),
        }


@dataclass(frozen=True, slots=True)
class SupersessionEvent:
    """A merge or split. Names both preimages and the successor; deletes nothing."""

    id: str
    kind: str
    preimage_claim_ids: tuple[str, ...]
    successor_claim_ids: tuple[str, ...]
    reason: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "preimage_claim_ids": list(self.preimage_claim_ids),
            "successor_claim_ids": list(self.successor_claim_ids),
            "reason": self.reason,
        }


# --------------------------------------------------------------------------
# Investigation
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Task:
    """A unit of evidence work in one evidence lane.

    `SPEC.md` section 9 requires an owner, a reason, a due time, a retry policy,
    and a state from section 9.2.
    """

    id: str
    claim_id: str
    lane: EvidenceLane
    state: TaskState
    owner: str
    reason: str
    due: str
    retry_budget: int = 0
    state_reason: str = ""
    #: Absence counts only when these are recorded (`SPEC.md` 7.3 rule 8).
    expected_record: str = ""
    repository: str = ""
    query: str = ""
    time_window: str = ""
    searched_scope: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "lane": self.lane,
            "state": self.state,
            "owner": self.owner,
            "reason": self.reason,
            "due": self.due,
            "retry_budget": self.retry_budget,
            "state_reason": self.state_reason,
            "expected_record": self.expected_record,
            "repository": self.repository,
            "query": self.query,
            "time_window": self.time_window,
            "searched_scope": self.searched_scope,
        }


@dataclass(frozen=True, slots=True)
class Investigation:
    """A bounded program of claims, questions, tasks, and exit conditions."""

    id: str
    question: str
    claim_ids: tuple[str, ...]
    exit_conditions: tuple[str, ...]
    closing_observation: str
    origin: str
    state: str = "open"

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "claim_ids": list(self.claim_ids),
            "exit_conditions": list(self.exit_conditions),
            "closing_observation": self.closing_observation,
            "origin": self.origin,
            "state": self.state,
        }


# --------------------------------------------------------------------------
# Attention — shapes only. Phase 4A builds the faculty.
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Notice:
    """Something in retained material the system found worth marking.

    Not evidence. It may direct attention and may establish nothing.
    """

    id: str
    artifact_id: str
    span: Span
    reason: str
    provenance_kind: NoticeProvenanceKind
    #: Retained in full for 90 days, then reduced by a superseding event.
    superseded_by: str | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "span": self.span.as_record(),
            "reason": self.reason,
            "provenance_kind": self.provenance_kind,
            "superseded_by": self.superseded_by,
        }


@dataclass(frozen=True, slots=True)
class InterestEntry:
    """A durable, revisable disposition toward a subject.

    `subject_entity_id` is absent by construction: interest attaches to subjects,
    questions and claims, never to an individual (`SPEC.md` section 10.1).
    """

    id: str
    subject: str
    rationale: str
    notice_ids: tuple[str, ...]
    #: What was in force when the material that produced it was read.
    diet_epoch_id: str
    topic_targets: tuple[tuple[str, str], ...]
    operator_input: str = ""
    diet_derived: bool = False
    investigation_ids: tuple[str, ...] = ()
    essay_ids: tuple[str, ...] = ()
    retired: bool = False
    retirement_reason: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "rationale": self.rationale,
            "notice_ids": list(self.notice_ids),
            "diet_epoch_id": self.diet_epoch_id,
            "topic_targets": [list(pair) for pair in self.topic_targets],
            "operator_input": self.operator_input,
            "diet_derived": self.diet_derived,
            "investigation_ids": list(self.investigation_ids),
            "essay_ids": list(self.essay_ids),
            "retired": self.retired,
            "retirement_reason": self.retirement_reason,
        }


@dataclass(frozen=True, slots=True)
class DecayEvent:
    """A superseding event carrying a reduced summary and citing what it covers.

    The superseded event remains in the ledger; its payload is discarded. Silent
    truncation is forbidden.
    """

    id: str
    covers_record_ids: tuple[str, ...]
    summary: str
    reason: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "covers_record_ids": list(self.covers_record_ids),
            "summary": self.summary,
            "reason": self.reason,
        }


# --------------------------------------------------------------------------
# Reckoning — shapes only. Phase 4A builds the faculty.
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Decision:
    """A choice among originate, continue, defer, revise, decline, or ask.

    A decision nobody can re-examine against what later happened is not a
    decision; it is an action with a timestamp — hence the alternatives.
    """

    id: str
    outcome: DecisionOutcome
    subject: str
    alternatives: tuple[str, ...]
    decided_by: str
    reason: str
    expectation_id: str | None = None
    confidence: str = ""
    re_raise_condition: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "outcome": self.outcome,
            "subject": self.subject,
            "alternatives": list(self.alternatives),
            "decided_by": self.decided_by,
            "reason": self.reason,
            "expectation_id": self.expectation_id,
            "confidence": self.confidence,
            "re_raise_condition": self.re_raise_condition,
        }


@dataclass(frozen=True, slots=True)
class Expectation:
    """What the system recorded it expected before acting."""

    id: str
    subject: str
    expected: str
    recorded_before: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "expected": self.expected,
            "recorded_before": self.recorded_before,
        }


@dataclass(frozen=True, slots=True)
class ConfirmedOutcome:
    """An outcome from outside the system's own account of it.

    Where no external confirmation is available the status is `UNVERIFIABLE`,
    and an unverifiable outcome feeds no consequence.
    """

    id: str
    expectation_id: str
    status: OutcomeStatus
    observed: str
    confirmation_source: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "expectation_id": self.expectation_id,
            "status": self.status,
            "observed": self.observed,
            "confirmation_source": self.confirmation_source,
        }


@dataclass(frozen=True, slots=True)
class Surprise:
    """A divergence between expectation and confirmed outcome.

    Retained whether or not it fits a live interest: a system that retains only
    what it expected learns the shape of its own expectations.
    """

    id: str
    expectation_id: str
    outcome_id: str
    divergence: str
    fits_live_interest: bool
    raised_to_operator: bool = False

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "expectation_id": self.expectation_id,
            "outcome_id": self.outcome_id,
            "divergence": self.divergence,
            "fits_live_interest": self.fits_live_interest,
            "raised_to_operator": self.raised_to_operator,
        }


@dataclass(frozen=True, slots=True)
class Consequence:
    """The scored delta between expectation and confirmed outcome, and the change
    it justified. Activity that grows while behaviour does not is the failure
    this record exists to make visible."""

    id: str
    expectation_id: str
    outcome_id: str
    score: str
    changed: str
    change_cites: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "expectation_id": self.expectation_id,
            "outcome_id": self.outcome_id,
            "score": self.score,
            "changed": self.changed,
            "change_cites": self.change_cites,
        }


@dataclass(frozen=True, slots=True)
class EscalationEvent:
    """A recorded attempt to lower risk, widen an envelope, edit the audit
    record, or bypass a refusal — by any route, direct or indirect."""

    id: str
    route: str
    attempted: str
    detected_by: str
    raised_to_operator: bool = False
    linked_change: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "route": self.route,
            "attempted": self.attempted,
            "detected_by": self.detected_by,
            "raised_to_operator": self.raised_to_operator,
            "linked_change": self.linked_change,
        }


@dataclass(frozen=True, slots=True)
class OperatorAction:
    """Actor, time, reason, target preimage, and result — identically from either
    surface, so the audit trail does not depend on which one was used."""

    id: str
    actor: str
    at: str
    action: str
    reason: str
    target_preimage: str
    result: str
    channel: str = "command"

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor,
            "at": self.at,
            "action": self.action,
            "reason": self.reason,
            "target_preimage": self.target_preimage,
            "result": self.result,
            "channel": self.channel,
        }


@dataclass(frozen=True, slots=True)
class Presentation:
    """A rendered revision and the records it depends on.

    Phase 0 carries the shape only, for the dependency-invalidation rule: a
    policy version change invalidates what was derived under the superseded one.
    """

    id: str
    kind: str
    claim_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    policy_version: str
    live: bool = True
    invalidation_reason: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "claim_ids": list(self.claim_ids),
            "edge_ids": list(self.edge_ids),
            "policy_version": self.policy_version,
            "live": self.live,
            "invalidation_reason": self.invalidation_reason,
            "metadata": dict(self.metadata),
        }
