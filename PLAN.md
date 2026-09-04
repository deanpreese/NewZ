# PLAN

**Status:** Authoritative delivery plan
**Effective:** 2026-09-03
**Strategy:** Greenfield implementation with gated rollout

This plan delivers the system in `SPEC.md` using the shape in
`ARCHITECTURE.md`. The prior NewZ codebase and data model are not migration
targets. Useful ideas may be reimplemented only when they satisfy the new
contracts and tests.

## Delivery principles

- Build provenance before scale.
- Make unsafe states structurally difficult, not merely discouraged by prompts.
- Prove every boundary with hostile fixtures before live acquisition.
- Keep discovery, verification, and correction as separately budgeted lanes.
- Prefer one complete vertical slice to a broad collection of partial adapters.
- Keep public reach off until correction and invalidation work end to end.

## Milestones

| Milestone | Outcome | Exit gate |
|---|---|---|
| M0 — Contract | Domain language, policies, fixtures, and decisions are executable | Gate 0 |
| M1 — Provenance spine | Authorized fetch becomes an immutable, inspectable artifact | Gate 1 |
| M2 — Evidence graph | Artifacts become typed assertions, claims, bases, and qualified edges | Gate 2 |
| M3 — Investigation loop | Missing evidence schedules work and new evidence changes assessment | Gate 3 |
| M4 — Safe presentation | Claim cards, correction, appraisal, and clearance work end to end | Gate 4 |
| M5 — Contested pilot | Reviewed 20-source, local-only live pilot proves the system | Gate 5 |
| M6 — Production | Controlled catalog expansion and cleared publishing | Gate 6 |

## Phase 0 — Contract and test corpus

**Purpose:** Turn the specification into versioned executable policy before
building persistence around ambiguous concepts.

Deliver:

1. Repository skeleton, automated checks, local development environment, and
   architectural decision record template.
2. Enumerations and schemas for source roles, evidence scopes, claim kinds,
   assertion kinds, edge relations, assessment states, risk tiers, and task
   states.
3. A machine-readable capability matrix implementing the rules in `SPEC.md`.
4. Deterministic promotion logic over independent bases.
5. A risk classifier with fail-closed handling and operator-review hooks.
6. A fixture corpus covering HTML, PDF, structured data, malformed documents,
   prompt injection, copied articles, retractions, and conflicting evidence.
7. Controlled case files for:
   - a narrow attributed claim;
   - two independent supporting bases;
   - support plus contradiction;
   - absence from a competent expected repository;
   - a copied story falsely appearing independent;
   - a patent misused as proof of performance;
   - a complaint misused as proof of guilt;
   - an R3 allegation; and
   - an R4 operational payload.

Tests:

- exhaustive allow/deny tests for the capability matrix;
- symmetry tests for support and refutation;
- property tests showing duplicate bases never increase strength;
- risk monotonicity and missing-state refusal;
- snapshot tests for canonical claim and policy serialization.

**Gate 0:** Policy decisions are deterministic, versioned, and pass the hostile
fixture suite. No network access exists yet.

## Phase 1 — Catalog, control plane, and provenance spine

**Purpose:** Make every byte attributable to an authorized operation.

Deliver:

1. PostgreSQL migrations for catalog, diet epochs, operations, reservations,
   acquisition attempts, audit events, and transactional outbox.
2. Source catalog validation: stable identity, publisher, independence group,
   delivery endpoint, topic, role, scope, risk floor, and retention policy.
3. Immutable diet epochs and a dry-run command that shows exact source and
   budget effects before activation.
4. Scheduler with local-day accounting and protected discovery,
   verification, and correction lanes.
5. Safe HTTP fetcher with SSRF controls, redirect enforcement, byte/time
   ceilings, decompression limits, content-type normalization, rate limiting,
   retry, backoff, and quarantine.
6. Content-addressed object storage and immutable response/sighting records.

Tests:

- concurrent reservation and idempotency tests;
- URL and redirect attack fixtures;
- oversized, slow, compressed, and mislabeled response fixtures;
- source revision and epoch immutability tests;
- backup and clean-restore tests for database plus objects.

**Gate 1:** Four offline canary sources—two HTML, one PDF, and one
attribution-only—produce reconstructible acquisition traces and artifact hashes
through one scheduler. Failure cannot exceed budget or leave ambiguous state.

## Phase 2 — Parsing and evidence graph

**Purpose:** Build the only path from retained material to an assessment.

Deliver:

1. Versioned parser registry for HTML, PDF, text, and structured data.
2. Stable artifact segments and exact span verification.
3. Schema-validated model extraction for assertions, entities, and claim
   candidates. Preserve the raw model proposal as an operation artifact.
4. Claim registry with atomic wording, aliases, merge proposals, and explicit
   claim kinds.
5. Basis registry with derivation links, unknown status, and operator-verified
   correction actions.
6. Evidence-edge policy engine with refusal reasons and predicate attestations.
7. Append-only assessments derived from live edges and independent bases.
8. Inspection endpoints for artifact → span → assertion → edge → claim →
   assessment traversal.

Tests:

- exact-quote offset and page/heading locator tests;
- parser-version and content-hash reproducibility;
- claimant-only, patent, complaint, testimony, preprint, replication, and final
  adjudication cases;
- syndication and hidden-common-origin cases;
- edge invalidation, retraction, and reassessment tests;
- deterministic replay from retained artifacts.

**Gate 2:** The controlled corpus produces the expected `reported`,
`supported`, `contested`, `refuted`, and `indeterminate` states. Every state is
explainable without reading model chain-of-thought or trusting generated prose.

## Phase 3 — Investigation and correction loop

**Purpose:** Make the system actively close evidence gaps instead of passively
collecting claims.

Deliver:

1. Investigations with claim membership, rationale, priority, exit conditions,
   and lifecycle.
2. Evidence packets that show strongest support, strongest contradiction,
   basis independence, missing lanes, and risk.
3. Task generation for claimant origin, primary record, empirical evidence,
   independent counterpart, skeptical analysis, and resolver checks.
4. Lane-aware scheduling: 6 discovery, 2 verification, and 2 correction reads
   in the initial daily budget.
5. Configured directed-search adapters that create leads only.
6. Resolution adapters for competent registries, dockets, publication status,
   retractions, replications, and time-bound forecasts.
7. Retry, expiration, cancellation, and terminal indeterminate outcomes.
8. Dependency invalidation when evidence, risk, or assessment changes.

Tests:

- no-borrow protected-capacity tests;
- counterpart due within 72 hours for claimant-led discovery;
- task deduplication and reachable-resolver tests;
- retraction and failed-replication scenarios;
- source outage and parser failure recovery;
- end-to-end new-evidence → revised-assessment trace.

**Gate 3:** Three full fixture investigations reach different defensible
outcomes, one remains explicitly unresolved, and one reverses after a later
correction. No manual database edit is required.

## Phase 4 — Claim cards and safe output

**Purpose:** Make evidence legible while preventing presentation from outrunning
the ledger.

Deliver:

1. Claim-card projection containing every field required by `SPEC.md`.
2. Search and browse over claims, topics, entities, status, and assessment
   history.
3. Report composer that accepts claim and edge references, never unsupported
   factual prose as authority.
4. Dependency validator and invalidation/rebuild pipeline.
5. Appraisal workflow for accuracy, fair representation, material omission,
   privacy, risk, and rendering.
6. Exact-revision clearance records and local/public reach controls.
7. Correction notices, superseded revisions, and retraction tombstones.
8. Export of one claim or the full corpus with artifacts, policy versions, and
   checksums.

Tests:

- every displayed factual sentence has a live edge and span;
- stale dependency and withdrawn-edge refusal;
- material counterevidence cannot be omitted;
- R2 solicitation/operator-review behavior;
- R3 exact-render approval and concurrent invalidation;
- R4 exclusion from prompts and outputs;
- lockdown disables public reach without mutating evidence.

**Gate 4:** A local reader can audit every sentence in a claim card, and a
post-publication correction automatically updates the card and adds a visible
history entry. Public reach remains disabled.

## Phase 5 — Reviewed contested-source pilot

**Purpose:** Validate the system against live, low-risk material without opening
public distribution.

Deliver:

1. Resolve the 20 pilot slots specified in `SPEC.md` to stable sources. For
   each, record retention rights, observed MIME, full-text capability,
   publisher, independence group, role, scope, risk, and counterpart behavior.
2. Create offline fixtures from every source and pass them through the complete
   pipeline before live enablement.
3. Activate the contested diet at two new live sources per day, local-only.
4. Produce daily funnel reports:
   lead → reserved → fetched → retained → parsed → asserted → edge admitted or
   refused → assessment changed → presentation invalidated.
5. Report offered and retained role/topic shares separately, along with
   publisher concentration, basis concentration, overdue counterpart tasks,
   parser failures, and risk/publication violations.
6. Require operator acknowledgment of daily reports during the first seven
   clean days.

Pause conditions:

- any claimant-only non-attribution factual promotion;
- any false independence count;
- any missing artifact/span on an admitted edge;
- any R3 or R4 publication-path violation;
- any unbounded or unauthorized fetch;
- any failure to invalidate a dependent claim card; or
- critical backup/restore failure.

**Gate 5:** At least 30 eligible local dates, 100 distinct retained full reads,
all 20 source/parser routes exercised under the current code version, zero open
critical violations, and demonstrated supported, contested, indeterminate, and
corrected cases. The operator explicitly approves progression.

## Phase 6 — Production and expansion

**Purpose:** Increase useful coverage without weakening evidence or safety.

Deliver in order:

1. Expand the low-risk R0–R1 catalog while maintaining topic/role coverage and
   concentration alerts.
2. Enable cleared public claim cards with public reach still independently
   lockable.
3. Add R2 source classes after direct adversarial review.
4. Add R3 intake only after the isolated workflow and exact-revision approval
   are exercised in production-like tests.
5. Add OCR, transcript, and media-forensics paths as separate releases, each
   with fixtures, provenance rules, and rollback.
6. Consider adaptive source ranking only after external review can measure
   source fitness without using the system's own conclusions as ground truth.

**Gate 6:** Production service objectives, security review, disaster-recovery
drill, policy replay, and public correction drill pass. R4 remains permanently
quarantined.

## Cross-cutting work

### Security

- Threat-model acquisition, document parsing, prompt injection, model data
  exfiltration, malicious URLs, sensitive-person data, and publication abuse.
- Isolate fetch and document workers with least privilege and egress policy.
- Encrypt secrets and sensitive retained data; never store credentials in the
  repository.
- Record access to R3 quarantined material.

### Observability

Instrument counts and latency at every pipeline boundary. Metrics MUST use
explicit denominators and MUST distinguish source, publication, artifact body,
and evidence basis. Alert on stalled correction tasks, concentration,
unexpected refusal changes, stale projections, budget leakage, and clearance
violations.

### Quality

Use unit tests for policy, property tests for invariants, contract tests for
adapters, golden tests for parsers/renderers, integration tests for persistence,
and controlled end-to-end cases for behavior. Every defect at a trust boundary
adds a permanent regression fixture.

### Operations

Automate schema migration, artifact integrity checks, point-in-time database
recovery, object-store versioning, export verification, and full clean restore.
No production migration may be irreversible without a tested paired restore.

## Initial backlog

The first implementation sequence is:

```text
P01 repository and CI
  → P02 domain schemas and policy matrix
  → P03 controlled fixture corpus
  → P04 catalog and immutable diet epochs
  → P05 operation/reservation ledger
  → P06 safe fetcher and object retention
  → P07 parser registry and verified spans
  → P08 assertion/claim extraction
  → P09 basis and independence graph
  → P10 evidence qualification and assessment
  → P11 investigations and evidence tasks
  → P12 resolution and correction
  → P13 claim cards and dependency invalidation
  → P14 appraisal, clearance, and lockdown
  → P15 pilot catalog and offline adapter fixtures
  → P16 shadow run
  → P17 local contested pilot
  → P18 production readiness
```

Each pull request MUST include migrations if needed, first writer and reader,
policy/version effects, inspection output, fixtures, rollback behavior, and the
acceptance tests that prove completion.

## Definition of done

The rewrite is complete when all `SPEC.md` acceptance criteria and Gate 6 pass,
the four governing documents match implemented behavior, and a new operator can
restore the system, inspect a claim from conclusion to original artifact, run a
correction, and lock down publication using documented interfaces alone.
