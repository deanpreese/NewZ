# PLAN

**Status:** Authoritative delivery plan
**Document version:** 1.10.0
**Effective:** 2026-09-04
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
- Turn publication on when correction and invalidation work end to end, and not
  before. Approve-by-default is earned by demonstrated revocation: the ability
  to withdraw is the control that replaces the gate.
- Keep reach local first. What clears and where it lands are separate
  decisions; widening to a public audience is its own act, taken later and on
  its own evidence.
- Gates govern contact with the outside world, never the building of a faculty.
  No capability waits on an assessment being written or a maturity score being
  awarded; what waits is live acquisition and publication. Gate 4A is the shape
  of this — it does not withhold permission to build the investigator, it
  demonstrates that interest cannot reach an assessment.

## Milestones

| Milestone | Outcome | Exit gate |
|---|---|---|
| M0 — Contract | Domain language, policies, fixtures, and decisions are executable | Gate 0 |
| M1 — Provenance spine | Authorized fetch becomes an immutable, inspectable artifact | Gate 1 |
| M2 — Evidence graph | Artifacts become typed assertions, claims, bases, and qualified edges | Gate 2 |
| M3 — Investigation loop | Missing evidence schedules work and new evidence changes assessment | Gate 3 |
| M4 — Safe presentation | Claim cards, correction, appraisal, and clearance work end to end | Gate 4 |
| M4A — The investigator | Noticing, interest, originated investigations, and essays work without reaching a conclusion | Gate 4A |
| M5 — Contested pilot | Reviewed 20-source, local-only live pilot proves the system | Gate 5 |
| M6 — Production | Controlled catalog expansion and cleared publishing | Gate 6 |

## Phase 0 — Contract and test corpus

**Purpose:** Turn the specification into versioned executable policy before
building persistence around ambiguous concepts.

Deliver:

1. Repository skeleton, automated checks, local development environment, and
   architectural decision record template.
2. ADR-0001, storage: state the concurrency requirement, record SQLite in WAL
   mode plus a local content-addressed artifact store as the decision, and
   record the rejected PostgreSQL alternative and the conditions that would
   reverse the choice.
3. ADR-0002, model tier: record the model, its size, and its local serving
   path, with the reason stated as the `TRUE_NORTH.md` boundary against an
   external model becoming the authority for judgment — not as a cost or
   privacy decision. Record what would reverse it, and note that no rule may be
   written to depend on model strength.
4. ADR-0003, runtime and toolchain: record Python 3.13 in the conda environment
   `agent13` as the implementation platform, with the standard library's
   `sqlite3` against SQLite 3.51 as the store driver — a version that already
   carries WAL, `STRICT` tables, and `RETURNING`. Record the deterministic
   consequences the choice must respect: policy, promotion, and the capability
   matrix are pure functions with pinned versions, so a runtime upgrade is a
   code version change under `SPEC.md` section 13 and reproduces or is a
   defect. Record what would reverse it, and pin the property-testing,
   type-checking, and migration tools, none of which are present in the
   environment yet.
5. Enumerations and schemas for source roles, claim kinds, assertion kinds,
   edge relations, assessment states, risk tiers, task states, decision
   outcomes, notice provenance kinds, and the expectation, surprise, and
   consequence records. Declared scope is recorded free text, not an
   enumeration. These are frozen here: a record type added after this point is
   a migration, which is why the attention and reckoning shapes land now rather
   than at the phase that builds them.
6. A machine-readable capability matrix implementing the rules in `SPEC.md`,
   computed over role, claim kind, assertion kind, and relation. It declares
   the required evidence lanes per claim kind that make `indeterminate`
   deterministic, and the closed list of basis-independence justifications. The
   task states come from `SPEC.md` section 9.2 and the closed set of evidence
   lanes from section 7.3; the matrix decides which lanes each claim kind
   requires, never which lanes exist. Deriving roughly two thousand cells from
   about ten stated principles is a design task: every judgment call the
   principles do not settle is recorded as a decision in the matrix, not
   resolved silently in code.
7. Deterministic promotion logic over independent bases, with basis identity
   and basis independence as separate inputs.
8. A risk classifier with fail-closed handling and operator-review hooks.
9. A fixture corpus covering HTML, PDF, structured data, malformed documents,
   prompt injection, copied articles, retractions, and conflicting evidence.
10. Controlled case files for:
    - a narrow attributed claim;
    - two independent supporting bases;
    - support plus contradiction;
    - absence from a competent expected repository;
    - a copied story falsely appearing independent;
    - a patent misused as proof of performance;
    - a complaint misused as proof of guilt;
    - an allegation refuted by a final adjudicative record;
    - a claim whose bases are resolved but of unknown independence;
    - a normative proposition and an unresolved forecast;
    - an R3 allegation; and
    - an R4 operational payload.

Tests:

- exhaustive allow/deny tests for the capability matrix;
- symmetry tests for support and refutation, including the single-record
  exception at R2 and R3;
- property tests showing duplicate bases never increase strength, and that
  unknown independence collapses bases for counting without invalidating any
  edge;
- `indeterminate` derived from terminal-competent task state alone, with no
  competence judgment outside recorded state;
- a required lane ending `refused`, `cancelled`, `expired`, or `superseded`
  never producing `indeterminate` and never satisfying the absence rule; the
  claim holds its state and the blocked lane surfaces with its reason;
- a policy version change reassessing every claim derived under the superseded
  version, and invalidating its dependent presentations;
- normative claims refusing `supports` and `contradicts` edges, and forecasts
  refusing promotion before their horizon;
- claim merge and split preserving both preimage histories and re-pointing
  edges without rewriting them;
- risk monotonicity and missing-state refusal;
- snapshot tests for canonical claim and policy serialization.

**Gate 0:** Policy decisions are deterministic, versioned, and pass the hostile
fixture suite. No network access exists yet.

## Phase 1 — Catalog, control plane, and provenance spine

**Purpose:** Make every byte attributable to an authorized operation.

Deliver:

1. SQLite (WAL) migrations for catalog, diet epochs, operations, reservations,
   acquisition attempts, audit events, and transactional outbox, with foreign
   keys enforced and `synchronous = FULL`.
2. Source catalog validation: stable identity, publisher, independence group,
   delivery endpoint, topic, role, declared scope, risk floor, and retention
   policy.
3. Immutable diet epochs and a dry-run command that shows exact source and
   budget effects before activation.
4. Scheduler with local-day accounting and protected discovery,
   verification, and correction lanes.
5. Safe HTTP fetcher with SSRF controls, redirect enforcement, byte/time
   ceilings, decompression limits, content-type normalization, rate limiting,
   retry, backoff, and quarantine.
6. Instruction-attempt observations recorded against the source revision,
   feeding operational standing only and never an epistemic score.
7. Content-addressed local artifact storage and immutable response/sighting
   records, with artifact bytes fsynced and renamed into place before the
   referencing row commits.

Tests:

- concurrent reservation and idempotency tests, including writer contention and
  busy-timeout behavior under WAL;
- lease expiry reclaiming an operation from a killed worker;
- URL and redirect attack fixtures;
- oversized, slow, compressed, and mislabeled response fixtures;
- source revision and epoch immutability tests;
- backup and clean-restore tests for database plus artifacts, including
  integrity and foreign-key checks in the verification path;
- crash-injection between artifact write and row commit leaving no dangling
  reference.

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
4. Lane-aware scheduling: 3 discovery, 5 verification, and 2 correction reads
   in the initial daily budget, with discovery pausing for the local day when
   open counterpart tasks exceed twelve or any counterpart task is overdue.
5. Configured directed-search adapters that create leads only.
6. Resolution adapters for competent registries, dockets, publication status,
   retractions, replications, and time-bound forecasts.
7. Retry, expiration, cancellation, and terminal indeterminate outcomes.
8. Dependency invalidation when evidence, risk, or assessment changes.

Tests:

- protected-capacity tests: discovery never borrows from the verification or
  correction reserve, unused correction capacity may serve verification within
  the same local day, and verification never returns capacity to discovery;
- discovery brake tests at the counterpart-backlog and overdue thresholds;
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

1. Claim-card projection containing every field required by `SPEC.md`, and the
   reader surface of `SPEC.md` section 2.2 with its authentication, rate
   limiting, and abuse controls — publication has somewhere to land only once
   these exist.
2. Entity-card projection under `SPEC.md` section 10.1: computed from the graph
   at build time, never stored as an accumulated profile, showing basis
   independence across the whole set and every claim's current state and
   counterevidence.
3. Search and browse over claims, topics, entities, status, and assessment
   history.
4. Report composer that accepts claim and edge references, never unsupported
   factual prose as authority.
5. Dependency validator and invalidation/rebuild pipeline.
6. Appraisal workflow split as `SPEC.md` section 10.2 requires: the four
   machine dimensions gating publication, the two judgment dimensions sampled
   behind it with full coverage of essays, R2 output, rewritten claimant
   formulations, and thin counterevidence, plus review debt accounting that
   halts a class when the ceiling is passed.
7. Exact-revision clearance records, local and public reach controls, and the
   enumerated automatic refusal conditions that hold with no operator present.
8. Correction notices, superseded revisions, and retraction tombstones.
9. Export of one claim or the full corpus with artifacts, policy versions, and
   checksums.

Tests:

- every displayed factual sentence has a live edge and span;
- an entity card showing ten claims that rest on one basis displays one basis,
  not a pattern;
- an entity card with no `supported`, `refuted`, or `contested` claim says so
  prominently rather than listing bare reports;
- no per-person aggregation exists at rest: deleting every card leaves entity
  records holding only disambiguation data;
- an R3 entity card cannot publish, and access to an R2-or-above card naming a
  living person is logged;
- stale dependency and withdrawn-edge refusal;
- material counterevidence cannot be omitted;
- R2 solicitation/operator-review behavior;
- R3 exact-render approval and concurrent invalidation;
- R4 exclusion from prompts and outputs;
- every published output carries what produced it, with policy and code
  versions and assessment date;
- publication, correction, and retraction each confirmed from outside the
  renderer, or marked `unconfirmed` and excluded from published counts;
- a forced render failure reports attempted-not-confirmed rather than success;
- the system refuses to assess its own fair representation or material omission;
- a judgment finding on one sampled item re-appraises its whole class;
- passing the review debt ceiling halts that class, and clearing it resumes;
- a correction and a retraction each complete and confirm inside the window, and
  an overdue one halts its class;
- a recorded failure with no linked change is reported as open;
- clearance refused when the only support is a case the system made, a
  perceived instruction, or an approval of a different revision or class;
- lockdown disables public reach without mutating evidence, and an injected
  policy breach enters lockdown automatically and cannot be self-cleared.

**Gate 4:** A local reader can audit every sentence in a claim card, and a
post-publication correction automatically updates the card and adds a visible
history entry. A retraction removes the presentation, leaves its tombstone, and
confirms both from outside the renderer, inside the configured window rather
than merely eventually. This gate is what earns
approve-by-default: passing it turns local publication on for R0–R2, and failing
it leaves it off. Public reach is a separate decision and stays disabled here.
R3 stays approval-gated and R4 unpublishable either way.

## Phase 4A — The investigator

**Purpose:** Give the system the faculty that decides what is worth
investigating. Until this exists the pipeline samples a feed against a quota;
`TRUE_NORTH.md` asks for something that encounters.

Deliver:

1. Noticing over retained spans, recording artifact, span, and reason, with a
   hard structural bar on a notice becoming an assertion, edge, or basis.
2. An append-only interest register with rationales, recorded influences,
   provenance mix, downstream trace, and retirement; its full operator
   inspection view; and its conversational-surface summary.
3. The diet self-report: retained role, topic, and publisher balance over a
   window, the perspectives under-represented in it, and where current interests
   track the diet's targets rather than diverging from them.
4. Investigation origination from interest, requiring question, exit
   conditions, and closing observation before any task is created, under the
   configured ceiling of concurrently open originated investigations.
5. Essay selection and composition: synthesis over several claims, every
   factual sentence bound to a live edge, every discussed claim carrying its
   current state and material counterevidence.
6. The conversational operator surface: notices raised, investigations
   proposed, essays offered, alerts, daily acknowledgment, pause and resume —
   and a structural refusal of clearance, ledger correction, policy
   activation, and export.
7. A separation test harness that enumerates every write path out of the
   interest register and out of the consequence recorder.
8. Decisions with recorded alternatives, expectations before acting, surprise
   retained independently of live interest, and scored consequences that cite
   what they changed.
9. The self-deception checks: evidence metrics unreachable by the system, the
   simpler-explanation review, the mirroring report with reversal-as-pressure,
   and a constraint-inspection view the system itself can read.
10. Escalation detection across direct and indirect routes, raised to the
   operator and carrying a linked change.
11. Attention retention and decay, with a record of what was let go.

Tests:

- interest cannot reach the scheduler, a diet epoch, an offered-menu target, a
  source role, an evidence weight, a threshold, or an assessment, proven by
  enumerating the register's write paths rather than by sampling behavior;
- interest cannot select a person as a subject, and an entity card built in
  Phase 4 is never an origin for one;
- a notice cannot become an assertion, edge, or basis, and never appears on a
  claim card as support;
- a notice cannot arise from an essay, claim card, entity card, report, or prior
  notice, and the register's provenance mix stays dominated by external
  material;
- an interest whose origin chain reaches only a configured topic target is
  labelled diet-derived, not formed;
- an interest producing no investigation and no essay within its window is
  retired or renewed with a reason, and the interest-origination share of all
  investigations is reportable;
- the diet self-report names an under-represented perspective when the retained
  balance is deliberately skewed;
- a surprise contradicting a live interest is retained and raised, and one
  fitting no interest at all is still retained;
- a consequence changes an interest priority, a retry policy, or a decision rule
  and cites itself as the reason; an `unverifiable` outcome changes nothing;
- no consequence path reaches a threshold, evidence weight, risk class, or
  assessment;
- declining and deferring appear as decisions with alternatives and reasons;
- the system cannot read its own evidence metrics, and can read its own
  constraints;
- a reversal of a recorded position without new evidence is logged as pressure,
  and the agreement rate is reported;
- an escalation attempt by an indirect route is detected, raised, and blocks
  until a change cites it;
- decayed attention leaves a record of what was let go, while evidence is
  unchanged;
- originated investigations consume no budget beyond the ordinary lanes, and
  the origination ceiling holds under concurrent triggers;
- an essay refuses to render a factual sentence with no live edge, and refuses
  to omit material counterevidence;
- an essay whose evidence turns against it changes or fails to render, and
  never renders the intended conclusion anyway;
- the conversational surface refuses R2 and R3 clearance, ledger correction,
  policy activation, and export;
- an instruction arriving on an unpinned channel, or asserting its sender in the
  message body, does not instruct;
- an authorisation request presents one exact effect with its audience and
  reversibility, and a batched or vague request is refused;
- the halt path works with the conversational surface unreachable;
- nothing raised or unraised changes what the command surface can inspect;
- both surfaces produce identical audit records for the same action.

**Gate 4A:** The system opens an investigation nobody asked for, pursues it
through the existing lanes, and writes an essay about what it found — and a
static audit of the interest register shows no write path to any scheduling or
evidence decision. One originated investigation must reach a conclusion its
originating interest did not want. The register must additionally report its
provenance mix, its interest-origination share, and at least one interest
retired for producing nothing — a register that only grows has not been
demonstrated to do anything. A recorded expectation must have been contradicted
by a confirmed outcome, retained as a surprise, and cited by a change; and the
simpler-explanation review must have been run adversarially against the
behaviour this gate credits.

## Phase 5 — Reviewed contested-source pilot

**Purpose:** Validate the system against live, low-risk material without opening
public distribution.

Deliver:

1. Resolve the 20 pilot slots specified in `SPEC.md` to stable sources. For
   each, record retention rights, observed MIME, full-text capability,
   publisher, independence group, role, declared scope, risk, and counterpart
   behavior.
2. Create offline fixtures from every source and pass them through the complete
   pipeline before live enablement.
3. Run a Shadow stage before Pilot: live acquisition from the reviewed catalog
   with assessments computed and compared against fixture expectations but not
   authoritative, and all presentation withheld. Shadow exits when every one of
   the 20 source and parser routes has been fetched live at least once, shadow
   assessments match fixture expectations or every divergence has a recorded
   cause, and no pause condition below has fired. Shadow does not consume Gate 5
   pilot dates.
4. Activate the contested diet at two new live sources per day, local-only.
5. Produce daily funnel reports:
   lead → reserved → fetched → retained → parsed → asserted → edge admitted or
   refused → assessment changed → presentation invalidated.
6. Report offered and retained role/topic shares separately, along with
   publisher concentration over retained reads, basis concentration, overdue
   counterpart tasks, parser failures, and risk/publication violations.
7. Report the interest-origination share, the register's provenance mix, the
   calibration and surprise counts, the agreement rate with the operator, and
   the diet self-report, alongside the operator-facing concentration figures. The
   first two are how RT-1 becomes visible: an interest register nothing depends
   on is indistinguishable from a good one until someone counts what it caused.
8. Report the share of claims held below `supported` or `refuted` solely by
   unknown basis independence. This is the leading indicator that the evidence
   rules are unsatisfiable in practice rather than merely strict; a sustained
   reading above 90% is a design finding and MUST be escalated to the operator
   rather than absorbed.
9. Require operator acknowledgment of daily reports during the first seven
   clean days.

Pause conditions:

- any claimant-only non-attribution factual promotion;
- any false independence count;
- any missing artifact/span on an admitted edge;
- any R3 or R4 publication-path violation;
- any unbounded or unauthorized fetch;
- any failure to invalidate a dependent claim card; or
- critical backup/restore failure.

Pause and resumption semantics, so the gate is countable:

- A pause suspends acquisition. Dates during a pause are not eligible dates.
- Resumption requires a recorded cause, a fix, and a permanent regression
  fixture for the violation. This is the pilot instance of the permanent
  correction requirement in `SPEC.md` section 13, not a rule that expires with
  the pilot.
- A fix that changes evidence, promotion, risk, or publication behavior resets
  the route-exercise requirement: all 20 routes must be exercised again under
  the new code version. Eligible dates and retained reads accumulated before
  the fix are retained.
- A fix that touches none of those paths preserves route exercise; the code
  version is recorded against each route so the distinction is auditable.

**Gate 5:** At least 30 eligible local dates, 100 distinct retained full reads,
all 20 source/parser routes exercised under the current code version, and zero
open critical violations. At least one **live** pilot claim must reach each of
`supported`, `contested`, and `indeterminate`, and at least one live claim must
be corrected after presentation; fixture cases do not satisfy this. The
operator explicitly approves progression.

## Phase 6 — Production and expansion

**Purpose:** Increase useful coverage without weakening evidence or safety.

Deliver in order:

1. Expand the low-risk R0–R1 catalog while maintaining topic/role coverage and
   concentration alerts.
2. Widen reach: enable public audiences for output that has been publishing
   locally by default since Gate 4, as an explicit scoped operator act, with
   reach still independently lockable at any moment. The reader surface itself
   was delivered in Phase 4 and has been serving locally since.
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

Automate schema migration, artifact integrity checks, scheduled online backups
of the database file with integrity and foreign-key verification, artifact-store
integrity sweeps against recorded hashes, export verification, and full clean
restore. No migration may be irreversible without a tested paired restore.
Because state is one database file plus a content-addressed tree, a restore
drill MUST verify byte-exact reproduction of claim cards, histories, and
artifact hashes, not merely that the service starts.

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
  → P14a noticing and the interest register
  → P14b investigation origination and the conversational surface
  → P14c essay selection and composition
  → P15 pilot catalog and offline adapter fixtures
  → P16 shadow run
  → P17 local contested pilot
  → P18 production readiness
```

P16 is the Shadow stage defined in Phase 5 and carries Phase 5's shadow exit
criteria; it is not a separate gate.

Each pull request MUST include migrations if needed, first writer and reader,
policy/version effects, inspection output, fixtures, rollback behavior, and the
acceptance tests that prove completion.

## Definition of done

The rewrite is complete when all `SPEC.md` acceptance criteria and Gate 6 pass,
the four governing documents match implemented behavior, and a new operator can
restore the system, inspect a claim from conclusion to original artifact, run a
correction, and lock down publication using documented interfaces alone.

Document drift is tracked, not assumed: each governing document carries a
version and a history table, and any pull request that changes behavior a
document describes MUST bump that document in the same change.

## Document history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-09-03 | Initial authoritative delivery plan. |
| 1.10.0 | 2026-09-04 | Added ADR-0003 for the runtime and toolchain, so the first backlog item is not the first undecided one. Fixed the capability matrix's stale reference to the task states and named `SPEC.md` 7.3 as the source of the evidence-lane set, which the matrix maps and does not define. Moved the interest-cannot-select-a-person test from Phase 4 to Phase 4A, where the interest register exists, and renumbered the Phase 4 deliverables, which 1.9.1 had missed. |
| 1.9.1 | 2026-09-04 | Renumbered the Phase 0, 1, and 4A deliverable lists, which had accumulated lettered suffixes. |
| 1.9.0 | 2026-09-04 | Froze the attention and reckoning record shapes in Phase 0 rather than deferring them to the phase that builds them, added decisions, expectations, surprise, consequence, self-deception checks, escalation detection and attention decay to Phase 4A, extended Gate 4A to require a contradicted expectation and an adversarial simpler-explanation review, and added calibration, surprise, and agreement-rate reporting to the pilot. |
| 1.8.0 | 2026-09-04 | Phase 4 delivers the split appraisal workflow with review debt accounting, Gate 4 demonstrates the revocation window rather than the mechanism alone, and Gate 5's resumption rule is marked as an instance of the permanent correction requirement. |
| 1.7.1 | 2026-09-04 | Gate 4 turns on local publication only; public reach stays disabled and is widened as its own act in Phase 6. Added the local-first delivery principle. |
| 1.7.0 | 2026-09-04 | Made Gate 4 the point that earns approve-by-default, moved the reader surface into Phase 4 so publication has somewhere to land, and added the enumerated fail-closed refusal conditions to Phase 4 delivery. |
| 1.6.0 | 2026-09-04 | Added interest-register influences, provenance, trace, and retirement to Phase 4A with the diet self-report, extended Gate 4A to require a register that demonstrably caused something, and added the origination share and provenance mix to pilot reporting. |
| 1.5.0 | 2026-09-04 | Recorded that gates govern contact with the outside world rather than the building of a faculty, and added entity-card delivery and tests for Phase 4. |
| 1.4.0 | 2026-09-04 | Added Phase 4 and Phase 4A tests for the adopted operator-surface and publishing requirements: channel-established authority, exact-effect requests, out-of-band halt, raising as additive, clearance never inferred, output authorship, and confirmed publication outcomes. |
| 1.3.0 | 2026-09-04 | Added Phase 4A and Gate 4A for the investigator — noticing, interest, originated investigations, essays, and the conversational surface — placed before the pilot because a pilot without it is a feed reader on a timer. Added ADR-0002 for the model tier and backlog items P14a through P14c. |
| 1.2.1 | 2026-09-04 | Took task states out of the capability matrix, now fixed by `SPEC.md` 9.1, and added the terminal-incomplete regression test. |
| 1.2.0 | 2026-09-04 | Scoped the capability matrix to role, claim kind, assertion kind, and relation, and named it a design task rather than a transcription. Added the policy-change reassessment test. |
| 1.1.0 | 2026-09-04 | Moved storage to SQLite with ADR-0001 as a Phase 0 deliverable. Rebalanced the daily lane budget to 3/5/2 and specified borrow direction. Gave the Shadow stage a place and exit criteria in Phase 5. Defined pause and route-exercise reset semantics for Gate 5 and required live cases rather than fixtures. Added the unknown-independence indicator to pilot reporting, scheduled the reader surface into Phase 6, and added Phase 0 cases and tests for the new SPEC rules. |
