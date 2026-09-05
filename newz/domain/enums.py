"""Every enumeration the system is allowed to reason over.

These are frozen at Phase 0 (`PLAN.md` Phase 0 item 5). A member added after
this point is a migration. Values are the stable wire form: they appear in
records, in the capability matrix, and in exports, so they are renamed only by a
policy version change.

Declared scope is deliberately absent. `SPEC.md` section 5.1 makes it recorded
free text rather than an enumeration.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class SourceRole(StrEnum):
    """`SPEC.md` section 5.1. A role grants capability for a specific use; it is
    never a claim that the source is generally reliable."""

    CLAIMANT = "claimant"
    FIRSTHAND_WITNESS = "firsthand_witness"
    PRIMARY_RECORD = "primary_record"
    EMPIRICAL_STUDY = "empirical_study"
    ADJUDICATOR = "adjudicator"
    SKEPTICAL_INVESTIGATION = "skeptical_investigation"
    HISTORICAL_CONTEXT = "historical_context"
    GENERAL_CONTEXT = "general_context"


@unique
class ClaimKind(StrEnum):
    """`SPEC.md` section 7.1."""

    ATTRIBUTION = "attribution"
    DOCUMENT_EXISTENCE = "document_existence"
    EVENT_OR_OBSERVATION = "event_or_observation"
    MEASUREMENT_OR_ASSOCIATION = "measurement_or_association"
    CAUSAL_OR_MECHANISTIC = "causal_or_mechanistic"
    CAPABILITY_OR_PERFORMANCE = "capability_or_performance"
    IDENTITY_OR_WRONGDOING_ALLEGATION = "identity_or_wrongdoing_allegation"
    FORECAST = "forecast"
    NORMATIVE_PROPOSITION = "normative_proposition"


@unique
class AssertionKind(StrEnum):
    """`SPEC.md` section 7.1. What a source is doing when it says a thing."""

    OBSERVATION = "observation"
    TESTIMONY = "testimony"
    ALLEGATION = "allegation"
    MEASUREMENT = "measurement"
    DOCUMENTED_EVENT = "documented_event"
    INFERENCE = "inference"
    PREDICTION = "prediction"


@unique
class EdgeRelation(StrEnum):
    """`SPEC.md` section 7.2."""

    CLAIMANT_SAYS = "claimant_says"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXTUALIZES = "contextualizes"


COUNTABLE_RELATIONS: frozenset[EdgeRelation] = frozenset(
    {EdgeRelation.SUPPORTS, EdgeRelation.CONTRADICTS}
)


@unique
class AssessmentState(StrEnum):
    """`SPEC.md` section 7.3."""

    REPORTED = "reported"
    PROVISIONAL_SUPPORT = "provisional_support"
    PROVISIONAL_CONTRADICTION = "provisional_contradiction"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    CONTESTED = "contested"
    INDETERMINATE = "indeterminate"
    WITHDRAWN = "withdrawn"


@unique
class RiskTier(StrEnum):
    """`SPEC.md` section 8. Ordered by `RISK_ORDER`, never by member order."""

    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"


RISK_ORDER: tuple[RiskTier, ...] = (
    RiskTier.R0,
    RiskTier.R1,
    RiskTier.R2,
    RiskTier.R3,
    RiskTier.R4,
)


@unique
class TaskState(StrEnum):
    """`SPEC.md` section 9.2. The division below is the substance of the set."""

    OPEN = "open"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    SATISFIED = "satisfied"
    EXHAUSTED = "exhausted"
    UNREACHABLE = "unreachable"
    REFUSED = "refused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


LIVE_TASK_STATES: frozenset[TaskState] = frozenset(
    {TaskState.OPEN, TaskState.SCHEDULED, TaskState.IN_PROGRESS, TaskState.BLOCKED}
)

#: The search happened and concluded. Only these may contribute to
#: `indeterminate` or satisfy the absence rule of `SPEC.md` section 7.3 rule 8.
TERMINAL_COMPETENT_STATES: frozenset[TaskState] = frozenset(
    {TaskState.SATISFIED, TaskState.EXHAUSTED, TaskState.UNREACHABLE}
)

#: The search did not happen. Investigating and finding nothing is a different
#: fact from never investigating.
TERMINAL_INCOMPLETE_STATES: frozenset[TaskState] = frozenset(
    {TaskState.REFUSED, TaskState.CANCELLED, TaskState.EXPIRED, TaskState.SUPERSEDED}
)


@unique
class EvidenceLane(StrEnum):
    """`SPEC.md` section 7.3. A question a claim kind may require an answer to.

    Distinct from `ReadLane`, which is a budget.
    """

    CLAIMANT_ORIGIN = "claimant_origin"
    PRIMARY_RECORD = "primary_record"
    EMPIRICAL = "empirical"
    INDEPENDENT_COUNTERPART = "independent_counterpart"
    SKEPTICAL_ANALYSIS = "skeptical_analysis"
    RESOLVER = "resolver"


@unique
class ReadLane(StrEnum):
    """`SPEC.md` section 5.2. A separately budgeted class of scheduled reads."""

    DISCOVERY = "discovery"
    VERIFICATION = "verification"
    CORRECTION = "correction"


@unique
class IndependenceJustification(StrEnum):
    """`SPEC.md` section 7.2, the closed list. Anything outside it requires an
    operator verification action, which is `OPERATOR_VERIFIED`."""

    DISTINCT_WITNESS = "distinct_witness"
    DISTINCT_INSTRUMENT_OR_DATASET = "distinct_instrument_or_dataset"
    DISTINCT_OFFICIAL_RECORD = "distinct_official_record"
    DISTINCT_EXPERIMENT = "distinct_experiment"
    DISTINCT_PRIMARY_OBSERVATION = "distinct_primary_observation"
    OPERATOR_VERIFIED = "operator_verified"


MECHANICAL_JUSTIFICATIONS: frozenset[IndependenceJustification] = frozenset(
    j for j in IndependenceJustification if j is not IndependenceJustification.OPERATOR_VERIFIED
)


@unique
class DecisionOutcome(StrEnum):
    """`SPEC.md` section 9.3. Declining and deferring are outcomes, not absences."""

    ORIGINATE = "originate"
    CONTINUE = "continue"
    DEFER = "defer"
    REVISE = "revise"
    DECLINE = "decline"
    ASK = "ask"


@unique
class NoticeProvenanceKind(StrEnum):
    """`SPEC.md` section 9.1. A system that cannot separate what it saw from what
    it concluded from what it was handed cannot answer how it knows anything."""

    OBSERVED = "observed"
    INFERRED = "inferred"
    TOLD = "told"


@unique
class OutcomeStatus(StrEnum):
    """`SPEC.md` sections 9.3 and 10. Absence of an error is not confirmation."""

    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"
    UNVERIFIABLE = "unverifiable"


@unique
class AppraisalDimension(StrEnum):
    """`SPEC.md` section 10.2. The split is which of them a machine may decide."""

    ACCURACY = "accuracy"
    PRIVACY = "privacy"
    RISK = "risk"
    RENDERING = "rendering"
    FAIR_REPRESENTATION = "fair_representation"
    MATERIAL_OMISSION = "material_omission"


MACHINE_DIMENSIONS: frozenset[AppraisalDimension] = frozenset(
    {
        AppraisalDimension.ACCURACY,
        AppraisalDimension.PRIVACY,
        AppraisalDimension.RISK,
        AppraisalDimension.RENDERING,
    }
)

#: The two the system may never assess about its own output.
JUDGMENT_DIMENSIONS: frozenset[AppraisalDimension] = frozenset(
    {AppraisalDimension.FAIR_REPRESENTATION, AppraisalDimension.MATERIAL_OMISSION}
)


@unique
class RefusalReason(StrEnum):
    """Why an edge, a promotion, or a publication was refused.

    Every refusal names itself. A refusal the operator cannot read is a refusal
    the system will retry by another route (`SPEC.md` section 9.4).
    """

    DENY_BY_DEFAULT = "deny_by_default"
    NORMATIVE_ADMITS_NO_EVIDENCE = "normative_admits_no_evidence"
    CLAIMANT_ESTABLISHES_ATTRIBUTION_ONLY = "claimant_establishes_attribution_only"
    ALLEGATION_IS_NOT_PROOF = "allegation_is_not_proof"
    INFERENCE_IS_NOT_EVIDENCE = "inference_is_not_evidence"
    PREDICTION_IS_NOT_EVIDENCE = "prediction_is_not_evidence"
    FILING_IS_NOT_PERFORMANCE = "filing_is_not_performance"
    WRONGDOING_NEEDS_ADJUDICATION = "wrongdoing_needs_adjudication"
    TESTIMONY_IS_BOUNDED = "testimony_is_bounded"
    CONTEXT_ROLE_IS_CONTEXTUAL_ONLY = "context_role_is_contextual_only"
    ROLE_LACKS_CAPABILITY = "role_lacks_capability"
    UNRESOLVED_BASIS = "unresolved_basis"
    MISSING_ARTIFACT_OR_SPAN = "missing_artifact_or_span"
    UNVERIFIED_QUOTE = "unverified_quote"
    ASSERTION_NOT_LIVE = "assertion_not_live"
    MISSING_RISK_STATE = "missing_risk_state"
    QUARANTINED_R4 = "quarantined_r4"
    MISSING_POLICY_VERSION = "missing_policy_version"


@unique
class AdmissionPredicate(StrEnum):
    """The named predicates an edge is checked against.

    Each one produces a predicate attestation (`SPEC.md` section 4) recording
    whether it held and on what inputs, so the decision replays.
    """

    ASSERTION_LIVE = "assertion_live"
    QUOTE_VERIFIED = "quote_verified"
    ARTIFACT_AND_SPAN_PRESENT = "artifact_and_span_present"
    TUPLE_PERMITTED = "tuple_permitted"
    BASIS_IDENTITY_RESOLVED = "basis_identity_resolved"
    RISK_CLASSIFIED = "risk_classified"
    POLICY_VERSION_RECORDED = "policy_version_recorded"


# ---------------------------------------------------------------------------
# Acquisition and control. Added in Phase 1, which is where persistence begins;
# `PLAN.md` Phase 0 froze the evidence vocabulary, and these are the operational
# states that vocabulary is acquired under.
# ---------------------------------------------------------------------------


@unique
class OperationKind(StrEnum):
    """What an authorized operation does. Every network act is one of these."""

    FETCH = "fetch"
    PARSE = "parse"
    RESOLVE = "resolve"


@unique
class OperationState(StrEnum):
    """`ARCHITECTURE.md`: workers claim operations through leases with an expiry,
    so a crashed worker's operation is reclaimed rather than lost."""

    RESERVED = "reserved"
    LEASED = "leased"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    QUARANTINED = "quarantined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


TERMINAL_OPERATION_STATES: frozenset[OperationState] = frozenset(
    {
        OperationState.SUCCEEDED,
        OperationState.FAILED,
        OperationState.QUARANTINED,
        OperationState.CANCELLED,
        OperationState.EXPIRED,
    }
)


@unique
class AttemptOutcome(StrEnum):
    """The terminal outcome of one attempt. `REFUSED` means policy declined
    before or during the read; `ERROR` means the far side or the network did."""

    RETAINED = "retained"
    REFUSED = "refused"
    ERROR = "error"


@unique
class FetchRefusal(StrEnum):
    """Why a fetch was refused, before or during the read.

    Refusals are recorded, never merely returned: an unbounded fetch that did
    not happen is as much a fact about a source as one that did.
    """

    SCHEME_NOT_ALLOWED = "scheme_not_allowed"
    URL_MALFORMED = "url_malformed"
    CREDENTIALS_IN_URL = "credentials_in_url"
    PORT_NOT_ALLOWED = "port_not_allowed"
    HOST_NOT_RESOLVABLE = "host_not_resolvable"
    NON_PUBLIC_ADDRESS = "non_public_address"
    HOST_NOT_IN_CATALOG = "host_not_in_catalog"
    REDIRECT_LIMIT = "redirect_limit"
    REDIRECT_SCHEME_DOWNGRADE = "redirect_scheme_downgrade"
    REDIRECT_OFF_POLICY = "redirect_off_policy"
    RESPONSE_TOO_LARGE = "response_too_large"
    DECOMPRESSION_LIMIT = "decompression_limit"
    CONTENT_TYPE_NOT_ALLOWED = "content_type_not_allowed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REQUEST_CEILING = "request_ceiling"
    STORAGE_CEILING = "storage_ceiling"
    RETENTION_PROHIBITED = "retention_prohibited"
    SOURCE_QUARANTINED = "source_quarantined"


@unique
class RetentionPolicy(StrEnum):
    """`SPEC.md` section 6 item 8. Where full retention is prohibited the
    material can remain a lead and cannot qualify as evidence."""

    FULL_TEXT = "full_text"
    METADATA_ONLY = "metadata_only"
    LEAD_ONLY = "lead_only"


@unique
class DeliveryKind(StrEnum):
    FEED = "feed"
    PAGE = "page"
    DOCUMENT = "document"
    DATASET = "dataset"
    API = "api"


@unique
class InstructionMarker(StrEnum):
    """What retained content did when it tried to instruct.

    These bear on a source's *operational* standing only. `TRUE_NORTH.md`
    forbids global truth scores, and a source that serves hostile markup may
    still be the only surviving record of what it published.
    """

    DIRECTIVE = "directive"
    AUTHORITY_CLAIM = "authority_claim"
    URGENCY = "urgency"
    IDENTITY_CLAIM = "identity_claim"
    SUPPRESSION_REQUEST = "suppression_request"
