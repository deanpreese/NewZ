# SPEC

**Product:** NewZ
**Status:** Authoritative specification
**Effective:** 2026-09-03
**Delivery model:** Greenfield rewrite

This document specifies a research system for contested claims. It supersedes
all earlier functional specifications and existing behavior. Requirements use
**MUST**, **SHOULD**, and **MAY** in their ordinary normative sense.

## 1. Product contract

NewZ MUST let an operator build and inspect investigations into fringe science,
anomalous phenomena, and conspiracy claims without turning discovery material
directly into belief.

For every investigated claim, NewZ MUST answer:

1. What exactly is being claimed?
2. Who made the claim, where, and when?
3. What retained material supports, contradicts, or contextualizes it?
4. Which publications share the same underlying basis?
5. What is the current assessment and why?
6. What evidence is missing?
7. What changed since the previous assessment?

The primary output is a **claim card** backed by a reconstructible evidence
graph. Narrative articles, conversations, alerts, and reports are projections
of that graph and MUST NOT become independent sources of evidence.

## 2. Users and surfaces

### 2.1 Operator

The operator configures sources, approves policy changes, reviews sensitive
material, manages investigations, and controls publication reach.

The operator MUST be able to:

- inspect every transformation from fetch to conclusion;
- pause all acquisition and publication independently;
- override scheduling without overriding evidence rules;
- correct source identity, basis identity, and risk classification with an
  append-only reasoned action;
- request reassessment or retraction; and
- export the complete claim record without dependence on a hosted model.

### 2.2 Reader

A reader may browse claim cards and cleared reports. Each presentation MUST
show current status, material support, material contradiction, source
independence, uncertainty, and last assessment date.

### 2.3 Model

Models MAY propose extraction, classification, summaries, search queries, and
research tasks. A model MUST NOT grant evidence capability, establish source
independence, lower risk, delete history, or publish high-risk material.

## 3. Domain and non-goals

The initial topic taxonomy is:

| Topic | Initial menu target |
|---|---:|
| UAP and aerospace anomalies | 18% |
| Psi and consciousness claims | 15% |
| Alternative physics and energy | 15% |
| Forteana, cryptids, anomalous natural events | 12% |
| Anomalous history and archaeology | 10% |
| Declassified material and historical secrecy | 10% |
| Metascience, methods, and replication | 10% |
| General scientific and institutional context | 10% |

These are discovery-menu targets, not conclusion quotas.

NewZ is not:

- a social network or engagement recommender;
- a general-purpose news reader;
- an oracle that assigns one truth score to a source;
- a system for identifying, targeting, or exposing private people;
- a provider of personalized medical, legal, financial, or election advice;
- an autonomous publisher of criminal allegations; or
- an operational guide to wrongdoing.

## 4. Canonical concepts

| Concept | Meaning |
|---|---|
| Source | A stable publisher, repository, witness archive, or delivery origin. |
| Artifact | An immutable retained representation of one fetched source version. |
| Segment | A stable addressable unit within an artifact: paragraph, table, page, or transcript interval. |
| Span | An exact quotation with offsets and a locator inside retained segments. |
| Assertion | An atomic proposition that a source makes in one or more spans. |
| Claim | An atomic proposition NewZ is investigating; distinct from an assertion. |
| Basis | The upstream observation, witness, dataset, filing, experiment, or record on which evidence depends. |
| Evidence edge | A versioned relation from an assertion to a claim. |
| Assessment | NewZ's append-only evaluation of a claim at a point in time. |
| Investigation | A bounded program of claims, questions, tasks, and exit conditions. |
| Claim card | The reader-facing projection of the current claim and its evidence graph. |
| Diet epoch | An immutable version of enabled sources, roles, limits, and policy. |

## 5. Ingestion diet

### 5.1 Source roles

Every enabled source revision MUST declare exactly one role and a maximum
evidence scope. A role grants capability for a specific use; it is not a claim
that the source is generally reliable.

| Role | Maximum ordinary use |
|---|---|
| Claimant | Establish that the source made a stated claim. |
| Firsthand witness | Establish that the witness reported an experience. |
| Primary record | Establish the existence/content of a filing, dataset, measurement, or official record within scope. |
| Empirical study | Report methods and results as provisional empirical evidence. |
| Adjudicator | Establish a current final finding within the authority's declared scope. |
| Skeptical investigation | Supply method-visible analysis, replication, or counterevidence. |
| Historical context | Supply provenance, chronology, and interpretive context. |
| General context | Supply relevant scientific or institutional background. |

The offered discovery menu SHOULD target:

| Scheduling bucket | Target |
|---|---:|
| Claimant, testimony, and community material | 25% |
| Primary artifacts and adjudicative records | 30% |
| Empirical work and replication | 20% |
| Skeptical, forensic, and investigative analysis | 15% |
| Historical, metascientific, and general context | 10% |

Targets MUST be computed over offered candidates. They MUST NOT suppress the
only relevant item, alter evidence weight, or force a conclusion. No publisher
may occupy more than 10% of the rolling 30-day offered menu unless the operator
records a scoped exception. Unknown independence MUST never count as
corroboration.

### 5.2 Initial pilot

The pilot MUST contain 20 reviewed source slots:

- 5 claimant or firsthand sources;
- 6 primary-record or adjudicative sources;
- 4 empirical or replication sources;
- 3 skeptical or forensic sources; and
- 2 historical or general-context sources.

It MUST cover all eight initial topics, retain full text where evidence is
possible, use no more than two sources from one publisher, and schedule a
counterpart task for every claimant-led discovery.

The initial ceiling is 10 distinct full artifact reads per local day:

- 6 discovery reads;
- 2 verification or counterpart reads; and
- 2 correction or resolution reads.

Unused discovery capacity MUST NOT consume the protected verification and
correction reserve. A full read requires a retained, successfully parsed body;
a headline, snippet, feed summary, or duplicate body does not count.

## 6. Acquisition and preservation

1. All network acquisition MUST pass through one scheduler and operation
   ledger. Every attempt receives an intent, budget reservation, source
   revision, policy epoch, and terminal outcome.
2. Feed entries and search results are leads only. They MUST NOT become factual
   evidence without a retained full artifact.
3. The fetcher MUST enforce scheme, host, redirect, size, timeout, and MIME
   policy before parsing. Unsupported content is refused without reading an
   unbounded body.
4. HTML, PDF, plain text, structured data, images/OCR, and audio/transcript
   routes MUST be explicit and versioned. A parser MUST record its
   implementation version and normalized MIME.
5. Every retained body MUST have a content hash. Duplicate bodies MAY share
   storage but MUST retain distinct sightings and source context.
6. Parsed segments MUST have stable locators. A span is valid only when its
   quotation matches retained text at the recorded offsets.
7. Artifacts, assertions, sightings, and parse executions are immutable.
   Corrections append a successor or invalidation event.
8. Source terms and retention policy MUST be recorded. When full retention is
   prohibited, the material can remain a lead but cannot qualify as evidence.

## 7. Claims and evidence

### 7.1 Claim kinds

Every claim MUST use one of:

- attribution;
- document existence;
- event or observation;
- measurement or association;
- causal or mechanistic;
- capability or performance;
- identity or wrongdoing allegation;
- forecast; or
- normative proposition.

Every source assertion MUST be typed as observation, testimony, allegation,
measurement, documented event, inference, or prediction.

### 7.2 Edge relations

An assertion may `claimant_says`, `supports`, `contradicts`, or
`contextualizes` a claim. The relation MUST be stored, versioned, and visible.
It MUST NOT be inferred differently by each downstream consumer.

A countable evidence edge requires:

- a live, quote-verified assertion;
- a retained artifact and exact span;
- a legal role, scope, claim-kind, assertion-kind, and relation tuple;
- a recorded basis with verified or mechanically justified identity;
- a risk classification; and
- the policy version that admitted it.

Anything missing or corrupt fails closed and remains contextual material.

### 7.3 Promotion rules

The current assessment state is one of:

- `reported` — a claim or experience is attributed but not established;
- `provisional_support` — one countable supporting basis exists;
- `provisional_contradiction` — one countable contradicting basis exists;
- `supported` — the applicable support threshold is met without countable
  contradiction;
- `refuted` — the symmetrical contradiction threshold is met without countable
  support;
- `contested` — countable evidence exists in both directions;
- `indeterminate` — a competent search or resolution attempt did not settle the
  claim; or
- `withdrawn` — the investigated proposition is no longer maintained, while
  history remains.

Rules:

1. Claimant material may establish only an accurately attributed meta-claim.
2. A witness report is evidence that the report occurred, not by itself that
   the external event occurred.
3. A patent proves a filing and its contents, not performance.
4. A complaint proves an allegation was filed, not guilt.
5. A study proves it reported a result; one study is not consensus.
6. Repetition from one basis MUST NOT increase evidentiary strength.
7. Support and refutation use symmetrical thresholds.
8. Absence counts only when an expected record, competent repository, query,
   time window, and searched scope are recorded.
9. Material opposing evidence always produces `contested`; it is never
   subtracted into a net score.
10. Model extraction confidence MUST NOT flow numerically into assessment
    confidence.

For ordinary R0–R1 factual claims, `supported` or `refuted` requires at least
two independent verified bases in that direction, including at least one
primary record, empirical study, or adjudicative record. Narrow attribution
and final-record claims may be settled by the single record that literally
establishes them. R2–R3 requirements are stricter under section 8.

## 8. Risk policy

The effective risk is the maximum of source risk, claim risk, named-entity
risk, domain risk, and intended output risk.

| Tier | Examples | Treatment |
|---|---|---|
| R0 | Historical folklore and obsolete claims | Ordinary attributed research. |
| R1 | UAP, psi, cryptids, alternative physics/history | Ordinary investigation; evidence rules apply. |
| R2 | Active institutions, current secrecy, named organizations | Strong provenance, two independent bases, explicit allegation labels. |
| R3 | Medicine, elections, finance, alleged crimes by living people | Isolated workflow; direct primary/adjudicative basis plus an independent qualified basis; operator approval before any publication. |
| R4 | Doxxing, incitement, harassment, operational wrongdoing | Metadata quarantine only; never reproduced or operationalized. |

Missing or unreadable risk state MUST behave as R3 internally and MUST block
publication. A model may raise risk but may not lower it. Private personal data
MUST be minimized, encrypted at rest if retained for legitimate review, and
excluded from prompts and output unless strictly necessary and approved.

## 9. Investigation workflow

1. A lead creates or links to an atomic claim without changing its assessment.
2. The system searches for the original claimant artifact and records the
   strongest fair formulation.
3. It creates tasks for primary records, empirical work, independent
   corroboration, skeptical analysis, and known resolution mechanisms.
4. Each acquired artifact passes through preservation, extraction, basis
   resolution, and evidence qualification.
5. A deterministic assessor derives the current state from live edges.
6. The system records missing lanes and what observation would change the
   assessment.
7. New evidence, retraction, or source correction triggers reassessment and
   invalidates dependent presentations.

Tasks MUST have an owner, reason, due time, retry policy, and terminal state.
Verification and correction work MUST have priority over new discovery when
their reserved capacity is available.

## 10. Claim card and outputs

Every claim card MUST include:

- exact claim wording and type;
- current assessment and effective risk;
- original claimant and first-known date;
- strongest live supporting and contradicting evidence;
- basis count and independence notes;
- direct quotations with artifact locators;
- important context and limitations;
- missing evidence and active tasks;
- assessment history; and
- a “what would change this” condition.

Generated prose MUST cite claim and edge IDs internally. A renderer MUST resolve
those IDs at build time and refuse stale, withdrawn, or uncleared dependencies.
Material changes MUST invalidate all dependent cards, reports, search indexes,
and caches.

R0–R1 material may be published after automated checks and appraisal. R2 is
solicited or operator-reviewed by default. R3 requires explicit operator
approval for the exact rendered revision. R4 is never published. Public reach
MUST default to disabled.

Corrections MUST remain visibly attached to prior outputs. Retraction removes
the current presentation from navigation but MUST leave a tombstone explaining
what changed.

## 11. Data model

The durable model MUST provide these append-oriented records:

| Aggregate | Required records |
|---|---|
| Catalog | sources, source revisions, roles, scopes, risk floors, publishers, independence groups |
| Diet | immutable epochs, enabled revisions, targets, budgets, grants |
| Acquisition | operations, reservations, attempts, redirects, responses, sightings |
| Preservation | artifacts, bodies, parse executions, segments, spans |
| Semantics | assertions, claims, claim aliases, entities |
| Evidence | bases, derivation links, edge events, policy decisions, predicate attestations |
| Assessment | assessment events, explanations, threshold inputs, supersessions |
| Investigation | investigations, claim membership, tasks, task attempts, exit conditions |
| Output | claim-card revisions, reports, appraisals, clearances, dependency links, invalidations |
| Operations | policy versions, operator actions, audit events, metrics, alerts |

All identifiers MUST be stable and opaque. All timestamps MUST be UTC with the
budget timezone stored separately. Current state SHOULD be a projection of
events, not an overwritable truth row. Referential and policy invariants MUST
be enforceable below the user-interface layer.

## 12. Interfaces

The implementation MUST expose equivalent CLI and service operations for:

- catalog validation and diet preview;
- acquisition run and retry;
- artifact and span inspection;
- claim creation, merge proposal, and reassessment;
- evidence packet inspection;
- investigation and task management;
- claim-card rendering;
- risk appraisal and clearance;
- pause, resume, backup, restore, and export; and
- health, concentration, provenance, and correction reports.

Every mutating operation MUST be idempotent or carry an idempotency key. Every
operator action MUST record actor, time, reason, target preimage, and result.

## 13. Non-functional requirements

- **Reproducibility:** Given the same retained artifacts, policy version, and
  code version, assessment and claim-card data MUST reproduce exactly.
- **Auditability:** Every displayed factual sentence MUST trace to live evidence
  edges and exact spans.
- **Security:** Fetching MUST resist SSRF, redirect escape, decompression bombs,
  malicious documents, and prompt injection. Parsed content is untrusted data.
- **Availability:** A failed source, parser, or model call MUST not corrupt the
  ledger or block unrelated investigations.
- **Portability:** Core data MUST export to documented, non-proprietary formats.
- **Recoverability:** Backups MUST include artifacts, metadata, policy, and audit
  history and MUST pass automated restore verification.
- **Observability:** Reports MUST distinguish leads, attempted fetches, retained
  bodies, admitted edges, bases, assessments, and publications.
- **Cost control:** Budget reservations MUST happen before fetch or model work;
  retries MUST not silently exceed the same operation's limit.

## 14. Acceptance criteria

The first production release is acceptable only when:

1. Every factual card sentence traces to an exact retained span and live edge.
2. Claimant-only input cannot produce an unqualified factual conclusion.
3. Syndication and copied stories cannot satisfy independence thresholds.
4. Support and contradiction produce symmetrical state transitions.
5. Retraction or edge invalidation updates every dependent surface.
6. R3 output cannot bypass exact-revision operator approval.
7. R4 content cannot enter model prompts or reader-facing output.
8. The 20-source pilot meets role/topic coverage and publisher caps.
9. At least three controlled cases demonstrate `supported`, `contested`, and
   `indeterminate` outcomes, and one demonstrates correction after publication.
10. A clean restore reproduces claim cards, histories, and artifact hashes.
11. A 30-day pilot completes with at least 100 distinct full reads and zero
    unresolved critical provenance or publication violations.

Implementation sequencing and release gates are defined in `PLAN.md`.
