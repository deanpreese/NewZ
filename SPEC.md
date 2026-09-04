# SPEC

**Product:** NewZ
**Status:** Authoritative specification
**Document version:** 1.6.0
**Effective:** 2026-09-04
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

The operator works through two surfaces holding different powers.

| Surface | Carries |
|---|---|
| Conversational | Notices the system raises, proposed investigations, offered essays, alerts, daily report acknowledgment, and pause or resume. |
| Command (CLI and service API) | Catalog and diet changes, policy epoch activation, evidence and basis correction, risk reclassification, appraisal and exact-revision clearance, backup, restore, and export. |

The split is structural, not a convenience. A conversational surface cannot
display an exact rendered revision together with its full dependency set, so it
MUST NOT carry R2 or R3 clearance, ledger correction, policy activation, or
export. Both surfaces record actor, time, reason, target preimage, and result
identically; the audit trail does not depend on which one was used.

**Authority comes from the channel, never from the message.** The conversational
surface MUST be bound to a pinned channel identity registered out of band, and
an instruction is authoritative because it arrived there. A message MUST NOT
establish authority by asserting who sent it, by citing a prior approval, or by
any property of its content. Traffic on any other channel — and every inbound
attachment, forward, or quoted body on the authenticated one — is world data
under section 6 and MUST NOT instruct.

**Authorisation requests MUST present the exact effect:** what would be
published or changed, to which audience, and whether it is reversible. Batching
several effects into one request, or describing an effect in terms that obscure
it, is a defect and not a convenience.

**A halt MUST be available out of band.** The operator MUST be able to stop
acquisition and publication through the command surface without depending on the
conversational surface being reachable or the system being responsive, and a
halt MUST NOT be negotiable.

Entry into a halted state MUST also be automatic on detection of a policy or
integrity breach — an admitted edge missing its artifact or span, a publication
path violation, an unauthorized fetch, or a failed dependency invalidation. The
system MUST NOT be able to clear its own halt, and the operator MUST be
notified. A halt is a stop so that correction can happen: release requires a
recorded cause and a regression fixture, not an argument.

**The system MAY choose what to raise; it MUST NOT choose what the operator can
see.** Raising is additive to the record and never a filter on it. Every notice,
interest entry, investigation, assessment, and output remains inspectable in
full through the command surface whether or not it was ever raised.

### 2.2 Reader

A reader may browse claim cards and cleared reports. Each presentation MUST
show current status, material support, material contradiction, source
independence, uncertainty, and last assessment date.

The reader surface is specified here but MUST NOT be delivered before Phase 6
of `PLAN.md`. Its authentication, rate limiting, and abuse controls are
designed together with public reach, not ahead of it.

### 2.3 Model

Models MAY propose extraction, classification, summaries, search queries,
notices, and research tasks. A model MUST NOT grant evidence capability,
establish source independence, lower risk, delete history, or publish
high-risk material.

The model MUST be small and locally served. This is a boundary, not a
deployment preference. `TRUE_NORTH.md` forbids letting an external model,
vendor, or source become the authority for the system's identity or judgment,
and a model strong enough to carry that judgment will eventually be trusted
with it whatever the documents say. A model that cannot carry the system's
rigor forces the rigor to live where it belongs: in deterministic policy and
the persisted evidence graph.

Two consequences bind implementation:

1. No capability, rule, or threshold may be specified in a way that depends on
   model strength. If a rule holds only with a frontier model, the rule is
   wrong and MUST be rewritten to hold with a weak proposer and a strict
   verifier.
2. Model quality MUST NOT be a release gate, a measure of system health, or an
   explanation for an assessment. A better model yields better proposals and
   changes no conclusion by itself.

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
| Notice | An attention record: something in retained material the system found worth marking. Not evidence, never an edge. |
| Interest | A durable, inspectable, revisable disposition toward a subject. It may open investigations and select essay subjects, and reaches nothing else. |
| Essay | A report synthesizing several claims. A projection of the evidence graph, never a source. |
| Entity card | The projection answering what the record holds about one named entity. Computed at build time, never stored as a profile. |
| Basis identity | The resolved upstream origin one edge rests on. See section 7.2. |
| Basis independence | A pairwise property between two resolved bases, used only in threshold counting. See section 7.2. |
| Sighting | One recorded observation of a body at a source, revision, and time. Duplicate bodies may share storage but never share sightings. |
| Independence group | A catalog grouping of sources known to share ownership, syndication, or editorial control. Membership blocks independence; it never establishes it. |
| Lane | A separately budgeted class of scheduled reads: discovery, verification, or correction. |
| Predicate attestation | A versioned record that one named admission predicate held or failed for one edge, with its inputs, so the decision can be replayed. |
| Appraisal | Review of one exact rendered revision for accuracy, fair representation, material omission, privacy, and risk. |
| Clearance | The permission record that lets one exact appraised revision reach a stated audience. |

## 5. Ingestion diet

### 5.1 Source roles

Every enabled source revision MUST declare exactly one role. A role grants
capability for a specific use; it is not a claim that the source is generally
reliable.

A source revision SHOULD also record a **declared scope**: a short description
of the subject matter or authority the source speaks to, such as an agency's
jurisdiction or a repository's collection. Scope is recorded context, not a
policy dimension, and it is not enumerated. It travels with every edge for
audit and appraisal, and it carries decision weight in exactly one place — the
single-record exception in section 7.3, where a final adjudicative record
settles a claim only within that adjudicator's declared scope. The capability
matrix is computed over role, claim kind, assertion kind, and relation
alone.

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
only relevant item, alter evidence weight, or force a conclusion. Unknown
independence MUST never count as corroboration; section 7.2 governs how it is
counted.

Publisher concentration is capped over **retained full reads**, not offered
candidates, because only reads can become evidence. Over a rolling 30 days no
publisher may exceed 20% of retained full reads during Pilot or 10% during
Production, unless the operator records a scoped exception. Offered-menu
concentration MUST be reported and MUST alert above 20%, but does not by itself
block scheduling: with 20 pilot sources and at most two per publisher, ordinary
feed-volume variance would otherwise trip a 10% offered-menu cap immediately
and train the operator to dismiss the alert.

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

- 3 discovery reads;
- 5 verification, counterpart, or corroboration reads; and
- 2 correction or resolution reads.

The budget is weighted toward verification because discovery opens claims
faster than verification can close them: every claimant-led discovery mandates
a counterpart task, and an ordinary R0–R1 promotion needs at least two
independent bases with at least one primary, empirical, or adjudicative record.
A discovery-heavy budget accumulates unresolved claims instead of settling
them.

Discovery MUST additionally pause for the local day when open counterpart tasks
exceed twelve, or when any counterpart task is overdue.

Unused discovery capacity MUST NOT consume the protected verification and
correction reserve. Unused correction capacity MAY be reallocated to
verification within the same local day; the reverse MUST NOT happen. A full
read requires a retained, successfully parsed body; a headline, snippet, feed
summary, or duplicate body does not count.

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

Two claim kinds are constrained at the state machine because the promotion
rules in section 7.3 cannot evaluate them:

- A `normative proposition` claim MUST NOT carry `supports` or `contradicts`
  edges. It admits `claimant_says` and `contextualizes` edges only, and its
  assessment state may only be `reported` or `withdrawn`.
- A `forecast` claim MUST record a resolution horizon and the resolver expected
  to settle it. Before that horizon its state MUST remain `reported` whatever
  edges accumulate. At the horizon it is settled by the resolver or becomes
  `indeterminate`.

### 7.2 Edge relations

An assertion may `claimant_says`, `supports`, `contradicts`, or
`contextualizes` a claim. The relation MUST be stored, versioned, and visible.
It MUST NOT be inferred differently by each downstream consumer.

A countable evidence edge requires:

- a live, quote-verified assertion;
- a retained artifact and exact span;
- a legal role, claim-kind, assertion-kind, and relation tuple;
- a resolved basis identity;
- a risk classification; and
- the policy version that admitted it.

Anything missing or corrupt fails closed and remains contextual material. The
edge also records the source revision's declared scope and topic for audit;
neither gates admission.

Basis identity and basis independence are separate properties and MUST NOT be
conflated.

**Basis identity** is a property of one edge: the edge names the specific
upstream observation, witness, dataset, filing, experiment, or record it rests
on. Identity is resolved when that origin is nameable and stable, even when it
is a single unnamed witness reached through one publication. An edge whose
basis resolves to no distinct upstream origin fails closed and remains
contextual material.

**Basis independence** is a pairwise property between two already-resolved
bases, and is consulted only when counting toward a promotion threshold. Two
bases count separately only under a recorded justification from the closed list
below. Unknown or unjustified independence MUST collapse the two bases into one
for counting; it MUST NOT invalidate either edge and MUST NOT prevent
`provisional_support` or `provisional_contradiction`.

| Independence justification | Distinctness established by |
|---|---|
| Distinct witness | A different named or stably pseudonymized person of record. |
| Distinct instrument or dataset | A different DOI, accession, sensor, or archive identifier. |
| Distinct official record | A different docket, filing, case, or registry number. |
| Distinct experiment | A different laboratory together with a different registration or protocol identifier. |
| Distinct primary observation | A different recorded time, place, and observing party. |

Any independence outside this list requires an operator verification action
recording actor, time, reason, and the evidence for distinctness. Publisher
identity, byline, wording differences, and independence-group membership MUST
NOT by themselves justify independence, and a model MUST NOT originate an
independence justification.

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
- `indeterminate` — every evidence lane required for the claim's kind reached a
  terminal-competent task state without producing a countable edge in either
  direction;
  or
- `withdrawn` — the investigated proposition is no longer maintained, while
  history remains.

`indeterminate` MUST be a function of recorded task state alone. The task
states themselves are enumerated in section 9.2; the evidence lanes required
for each claim kind are declared in the capability matrix and versioned with
it. Together they make an assessment reproduce exactly under section 13. No
assessment state may depend on a judgment of search competence that is not
recorded as a terminal-competent task state.

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
   time window, and searched scope are recorded, and only from a lane that
   reached a terminal-competent state under section 9.2.
9. Countable opposing evidence always produces `contested`; it is never
   subtracted into a net score.
10. Model extraction confidence MUST NOT flow numerically into assessment
    confidence.
11. Every assessment event MUST record the countable independent basis count in
    each direction, so `contested` preserves the shape of a disagreement
    instead of flattening a ten-to-one balance and a one-to-one balance into
    the same label.

For ordinary R0–R1 factual claims, `supported` or `refuted` requires at least
two independent countable bases in that direction, including at least one
primary record, empirical study, or adjudicative record. A basis is countable
when it carries at least one countable edge under section 7.2. There is no
separate verification or qualification state for a basis; countable is the only
bar, and operator verification appears only where section 7.2 requires it to
justify independence.

A narrow attribution claim or a document-existence claim may be settled by the
single record that literally establishes it. So may any claim settled by a
final adjudicative record within that adjudicator's declared scope, including a
record that refutes an allegation.

This single-record exception survives at R2 and R3. It is the only route by
which a false allegation about a living person can reach `refuted` under the
symmetrical thresholds of rule 7; withholding it would make symmetry operate
against the accused. The exception applies only where the record literally
establishes or literally settles the claim, never by inference drawn from the
record.

Every other R2 claim requires two independent countable bases with strong
provenance. Every other R3 claim requires a direct primary or adjudicative
basis plus an independent countable basis, under section 8.

### 7.4 Claim merge and split

Claim identity changes are append-only. Edges address claim identifiers, so a
merge or split MUST NOT rewrite them.

1. A merge MUST emit a supersession event naming both preimages and the
   successor. Neither preimage is deleted or rewritten.
2. Edges move by emitting new edge events against the successor claim. Existing
   edge events remain valid against their original claim.
3. The successor's assessment is derived from its live re-pointed edges. It is
   never copied from either preimage.
4. Both preimage histories remain reachable and MUST resolve to the successor.
5. A split follows the same rules with one preimage and several successors.
   Each edge MUST be re-pointed explicitly, and MUST NOT be duplicated across
   successors without a distinct basis.
6. No merge or split may change an edge's basis, span, role, relation, or risk.

## 8. Risk policy

The effective risk is the maximum of source risk, claim risk, named-entity
risk, domain risk, and intended output risk.

| Tier | Examples | Treatment |
|---|---|---|
| R0 | Historical folklore and obsolete claims | Ordinary attributed research. |
| R1 | UAP, psi, cryptids, alternative physics/history | Ordinary investigation; evidence rules apply. |
| R2 | Active institutions, current secrecy, named organizations | Strong provenance, two independent bases, explicit allegation labels. |
| R3 | Medicine, elections, finance, alleged crimes by living people | Isolated workflow; direct primary/adjudicative basis plus an independent countable basis; operator approval before any publication. |
| R4 | Doxxing, incitement, harassment, operational wrongdoing | Metadata quarantine only; never reproduced or operationalized. |

Missing or unreadable risk state MUST behave as R3 internally and MUST block
publication. A model may raise risk but may not lower it. Private personal data
MUST be minimized, excluded from prompts and output unless strictly necessary
and approved, and encrypted at rest when retained for legitimate review.

Erasure and immutability are reconciled by encryption, not by deletion. Private
personal data MUST be stored encrypted under a per-subject key held outside the
ledger. An erasure obligation is satisfied by destroying that key: the ledger
event survives with an unreadable payload plus a tombstone recording that
erasure occurred, its reason, and its date. No ledger event is ever removed or
rewritten.

R4 material and R3 quarantined personal data MUST carry an expiry. The default
retention is 24 months from last legitimate review, after which the subject key
is destroyed automatically unless the operator records a reasoned extension.
Every access to R3 quarantined material MUST be logged.

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
8. A change to the capability matrix, promotion thresholds, independence
   justifications, required evidence lanes, or the task-state classification in
   section 9.2 is a policy version change. It MUST trigger reassessment of
   every claim whose current assessment was derived under the superseded
   version, and MUST invalidate the dependent presentations. Without this, a
   stored assessment silently reflects a policy that no longer exists, and
   section 13 reproducibility holds only against a version nothing is running.

Every assessment MUST record the policy version it was derived under. Tasks
MUST have an owner, reason, due time, retry policy, and a state drawn from
section 9.2. Verification and correction work MUST have priority over new
discovery when their reserved capacity is available.

### 9.1 Noticing and interest

`TRUE_NORTH.md` requires a system that is curious at intake and that
encounters, rather than one that samples a feed against a quota. Sections 5
through 8 specify how a claim is evaluated once it exists. This section
specifies what makes a claim worth evaluating at all.

**Noticing.** As retained artifacts are extracted, the system MAY record
notices: things in the material it found worth marking, in its own words. A
notice records the artifact, the span it arose from, and its reason. A notice
is not evidence. It MUST NOT become an assertion, an edge, or a basis, and it
MUST NOT appear on a claim card as support for anything. It falls under the
same rule as a lead: it may direct attention and may establish nothing.

**Interest.** The system maintains an interest register: a durable, revisable
set of subjects it is pursuing, each with a rationale and the notices that
produced it. The register MUST be inspectable by the operator in full, and
every change to it MUST be an append-only event carrying its reason. Interest
that cannot be inspected is indistinguishable from bias.

**Origination.** Interest MAY open an investigation. An originated
investigation MUST state its question, its exit conditions, and the observation
that would close it before any task is created. The operator MAY close any
investigation at any time with a recorded reason.

**Essay selection.** Interest MAY select the subject of an essay under section
10.

That is the whole of what interest may do.

Interest MUST NOT influence the scheduler, a diet epoch, an offered-menu
target, a source role, a risk classification, an evidence weight, a promotion
threshold, an independence justification, or any assessment. No path exists
from the interest register to an assessment, and none may be added.
**Interest reaches attention. Evidence reaches conclusion.**

The diet retains sole control of throughput. An originated investigation
receives no additional read budget: its tasks queue in the lanes of section 5.2
under the ordinary priority rules, and the counterpart brake applies unchanged.
So that origination cannot flood the queue, the system MUST hold no more than a
configured ceiling of concurrently open self-originated investigations — five
during Pilot — and MUST NOT open another until one reaches a terminal state or
the operator closes it.

The system MAY raise a notice, a proposed investigation, or a finished essay to
the operator over the conversational surface of section 2.1. Raising something
is not permission to act on it, and under section 2.1 raising is additive: what
the system does not raise remains inspectable in full. A faculty that selects
what to show is one step from selecting what to withhold, and only the record
being complete keeps that step from being available.

### 9.2 Task states

Task states are enumerated here, not left to the implementation, because
`indeterminate` is derived from them. An assessment state may not rest on a set
that no document fixes.

Live states:

- `open` — created, not yet reserved;
- `scheduled` — holds a lane and budget reservation;
- `in_progress` — an attempt is running; and
- `blocked` — waiting on an external precondition such as a source outage, rate
  limit, or quarantine. A blocked task MUST return to `scheduled` when the
  precondition clears; it is not terminal.

Terminal states divide into two classes, and the division is the substance of
this section.

**Terminal-competent** — the search happened and concluded:

- `satisfied` — the task produced what it sought;
- `exhausted` — competent attempts were made against a reachable repository and
  the retry policy is spent; and
- `unreachable` — no competent repository, registry, or resolver exists for the
  question, recorded with what was sought and where it was sought.

**Terminal-incomplete** — the search did not happen:

- `refused` — policy declined the work on risk, retention, or terms grounds;
- `cancelled` — an operator stopped it, with a recorded reason;
- `expired` — the due time passed and the task is no longer useful; and
- `superseded` — a successor task carries the work, typically after a claim
  merge or split.

Only terminal-competent states may contribute to `indeterminate`. Investigating
and finding nothing is a different fact from never investigating, and
collapsing them would let a claim NewZ was refused permission to examine
present exactly like one examined exhaustively — the most misleading result
this system could produce, because it would wear the language of inquiry.

A claim with any required lane in a terminal-incomplete state MUST hold its
current assessment and MUST surface that lane, its state, and its reason on the
claim card. A terminal-incomplete lane MUST NOT satisfy rule 8 of section 7.3;
absence is evidence only from a lane that actually looked.

## 10. Claim card and outputs

Every claim card MUST include:

- exact claim wording and type;
- current assessment and effective risk;
- original claimant and first-known date;
- strongest live supporting and contradicting evidence;
- basis count and independence notes;
- direct quotations with artifact locators;
- important context and limitations;
- missing evidence, active tasks, and any required lane that ended
  terminal-incomplete, with its reason;
- assessment history; and
- a “what would change this” condition.

An **essay** is a report that synthesizes several claims. Its subject MAY be
chosen by interest under section 9.1; its content may not be. An essay MUST:

- cite claim and edge IDs for every factual sentence, as any report must;
- carry the current assessment state of every claim it discusses, including
  `contested` and `indeterminate` ones;
- carry material counterevidence for every claim it discusses; and
- introduce no factual assertion that does not trace to a live edge.

An essay is a projection and never a source. Nothing in it may be cited as
evidence, by this system or by any later revision of it. It passes the same
appraisal, clearance, reach controls, and dependency invalidation as any other
output.

Where the evidence does not support the essay the system wanted to write, the
essay changes or goes unwritten. Interest chose the subject; it does not get
the verdict.

Generated prose MUST cite claim and edge IDs internally. A renderer MUST resolve
those IDs at build time and refuse stale, withdrawn, or uncleared dependencies.
Material changes MUST invalidate all dependent cards, reports, search indexes,
and caches.

R0–R1 material may be published after automated checks and appraisal. R2
requires operator review before publication by default; the operator MAY
pre-clear a named class of R2 output after adversarial review of that class,
and such pre-clearance MUST be scoped, expiring, and revocable. R3 requires
explicit operator approval for the exact rendered revision, with no
pre-clearance. R4 is never published. Public reach MUST default to disabled.

**Authorisation is never inferred.** A clearance MUST NOT be derived from
material the system perceived, from a case the system made for publishing
something, or from a prior approval of a different revision or class.
Pre-clearance under R2 binds only the class it names, only while unexpired, and
never a revision outside it.

**Every published output MUST identify what produced it:** that it was composed
by NewZ from the cited claim record, the policy and code versions in force, and
the date of the assessment it rests on. A system whose purpose is to stop
attribution from silently disappearing MUST NOT publish unattributed prose of
its own. No output may claim human authorship or conceal what produced it.

**Publication is an action with an attempted effect and a confirmed outcome, and
the two MUST NOT be conflated.** Every publication, correction, and retraction
MUST record what was attempted and, separately, whether the effect was confirmed
from evidence outside the renderer's own report: the surface actually serving
the revision, the correction actually attached to the prior output, the
retracted presentation actually absent from navigation. Where no confirmation
source exists for an output class, that class MUST be marked `unconfirmed` and
MUST NOT be counted as published in any report or acceptance criterion. Absence
of an error is not confirmation.

Corrections MUST remain visibly attached to prior outputs. Retraction removes
the current presentation from navigation but MUST leave a tombstone explaining
what changed.

### 10.1 Entity cards

A reader MUST be able to ask what the record holds about a named entity. That
view is an **entity card**: a projection governed exactly as a claim card is —
not a raw query result, and not a stored profile.

The entity record itself holds only what disambiguation requires: a stable
opaque identifier, the surface forms used to refer to it, a type, and the facts
needed to tell two similarly named parties apart. It MUST NOT accumulate claims,
allegations, assessments, or spans. The card is computed from the graph at build
time, so no dossier exists at rest to leak, to compel, or to outlive the sources
it was drawn from.

Every entity card MUST:

- carry the current assessment state of every claim shown, and never list a bare
  allegation;
- carry material counterevidence for every claim shown;
- show basis independence across the whole set, so that ten claims resting on
  one basis display as one basis rather than as a pattern;
- state prominently when no claim shown has reached `supported`, `refuted`, or
  `contested`, since a list of unestablished reports is the form in which this
  view most easily misleads; and
- carry an effective risk equal to the maximum over the claims it shows.

**Aggregation is itself appraised.** Appraisal of an entity card MUST ask
whether the set misleads where no individual item does. That is the failure
specific to this projection — accurate attribution, item by item, adding up to
an implication nothing supports — and it is the reason the view is reviewed
rather than assembled silently.

An entity card naming a living person at R2 or above MUST log every access with
actor, time, and reason. An R3 entity card requires approval of its exact
revision and MUST NOT be published. Public reach for entity cards is controlled
separately from claim cards and defaults to disabled.

Interest under section 9.1 MUST NOT select a person. It attaches to subjects,
questions, and claims. A system that develops an interest in an individual is
building the thing this section exists to prevent.

## 11. Data model

The durable model MUST provide these append-oriented records:

| Aggregate | Required records |
|---|---|
| Catalog | sources, source revisions, roles, scopes, risk floors, publishers, independence groups |
| Diet | immutable epochs, enabled revisions, targets, budgets, grants |
| Acquisition | operations, reservations, attempts, redirects, responses, sightings |
| Preservation | artifacts, bodies, parse executions, segments, spans |
| Semantics | assertions, claims, claim aliases, entities (disambiguation data only, never per-person aggregation) |
| Evidence | bases, derivation links, edge events, policy decisions, predicate attestations |
| Assessment | assessment events, explanations, threshold inputs, supersessions |
| Attention | notices, interest register entries, interest events, origination records |
| Investigation | investigations, claim membership, tasks, task attempts, exit conditions |
| Output | claim-card revisions, entity-card revisions, reports, appraisals, clearances, dependency links, invalidations |
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
- notice and interest-register inspection;
- investigation and task management, including originated investigations;
- claim-card and entity-card rendering;
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
  and malicious documents. Parsed content is untrusted data and MUST NOT be
  read as instructions. Prompt injection is contained at the model boundary
  rather than at fetch: model output is schema-validated proposal data, and
  every quotation a model proposes MUST verify byte-exact against the retained
  span at the recorded offsets. Span verification is the primary defense,
  because a model cannot introduce a quotation that is not already present in
  retained text.
- **Availability:** A failed source, parser, or model call MUST not corrupt the
  ledger or block unrelated investigations.
- **Portability:** Core data MUST export to documented, non-proprietary formats.
- **Recoverability:** Backups MUST include artifacts, metadata, policy, and audit
  history and MUST pass automated restore verification.
- **Observability:** Reports MUST distinguish leads, attempted fetches, retained
  bodies, admitted edges, bases, assessments, and publications.
- **Cost control:** Budget reservations MUST happen before fetch or model work;
  retries MUST not silently exceed the same operation's limit. The system MUST
  enforce a configured monthly ceiling on external requests, and configured
  ceilings on local inference time and on retained artifact-store growth.
  Inference is local under section 2.3, so the binding cost is compute and
  wall-clock rather than vendor spend. Reaching a ceiling pauses acquisition;
  it MUST NOT relax evidence rules or publication checks.

## 14. Acceptance criteria

The first production release is acceptable only when:

1. Every factual card sentence traces to an exact retained span and live edge.
2. Claimant-only input cannot produce an unqualified factual conclusion.
3. Syndication and copied stories cannot satisfy independence thresholds.
4. Support and contradiction produce symmetrical state transitions.
5. Retraction or edge invalidation updates every dependent surface.
6. The R3 pathway cannot bypass exact-revision operator approval, proven
   against fixtures. Live R3 intake is not part of the first release; it is
   gated to Phase 6 of `PLAN.md`.
7. R4 content cannot enter model prompts or reader-facing output.
8. The 20-source pilot meets role/topic coverage and the retained-read
   publisher cap.
9. At least three controlled cases demonstrate `supported`, `contested`, and
   `indeterminate` outcomes, and one demonstrates correction after publication.
9a. Interest can open an investigation and select an essay subject, and can
    reach no scheduler decision, evidence weight, threshold, or assessment.
9b. An essay refuses to render a factual sentence without a live edge, and
    carries every discussed claim's current state and material
    counterevidence.
9c. A message on an unpinned channel cannot instruct, and no clearance follows
    from a case the system made for publishing.
9d. Publication, correction, and retraction each record a confirmed outcome from
    outside the renderer, or are marked `unconfirmed` and not counted.
9e. An entity card shows one basis where ten claims share one, says so when
    nothing about the person is established, and leaves no per-person
    aggregation at rest.
10. A clean restore reproduces claim cards, histories, and artifact hashes.
11. A 30-day pilot completes with at least 100 distinct full reads, at least
    one live claim reaching each of `supported`, `contested`, and
    `indeterminate`, at least one live correction after presentation, and zero
    unresolved critical provenance or publication violations. Fixture cases do
    not satisfy this criterion.

Implementation sequencing and release gates are defined in `PLAN.md`.

## 15. Document history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-09-03 | Initial authoritative specification. |
| 1.6.0 | 2026-09-04 | Added entity cards in section 10.1: per-person browsing kept, but as a governed projection rather than a stored dossier. Entity records hold disambiguation data only; cards are computed at build time, show basis independence across the set, carry state and counterevidence per claim, say so when nothing is established, appraise the aggregation itself, log access for living people at R2 and above, and never publish at R3. Interest may not select a person. |
| 1.5.0 | 2026-09-04 | Adopted six operator-surface and publishing requirements from the pre-rewrite functional spec: authority established by pinned channel rather than message content, authorisation requests presenting the exact effect, an out-of-band halt with automatic non-self-clearable entry on breach, raising as additive to a record the system cannot curate, clearance never inferred from persuasion or unrelated approval, and publication as an action with an attempted effect and a separately confirmed outcome plus mandatory authorship on every output. |
| 1.4.0 | 2026-09-04 | Specified the investigator the rewrite had left out: noticing, an inspectable interest register, interest-originated investigations, and essays as synthesis whose subject interest may choose and whose verdict it may not. Interest reaches attention only; the diet keeps sole control of throughput under a ceiling on open originated investigations. Made a small, locally served model normative rather than incidental, split the operator into a conversational and a command surface, and replaced the model-spend ceiling with local inference ceilings. |
| 1.3.0 | 2026-09-04 | Enumerated task states in section 9.1 and split terminal states into terminal-competent and terminal-incomplete. Only terminal-competent lanes may produce `indeterminate` or satisfy the absence rule; a claim with a refused, cancelled, expired, or superseded required lane holds its state and surfaces the blocked lane on the card. |
| 1.2.0 | 2026-09-04 | Demoted evidence scope from the capability tuple to recorded audit context, so the matrix is computed over role, claim kind, assertion kind, and relation alone. Collapsed "verified" and "qualified" bases into the single bar `countable`. Put the set of terminal task states in the versioned capability matrix, and made a policy version change trigger reassessment of claims derived under the superseded version. |
| 1.1.0 | 2026-09-04 | Separated basis identity from basis independence and added the closed list of independence justifications. Rebalanced the daily lane budget to 3/5/2 with a counterpart backlog brake. Moved publisher concentration to retained reads with tiered caps. Made `indeterminate` a function of terminal task state. Constrained `normative proposition` and `forecast` kinds. Added claim merge and split semantics, crypto-shredding for erasure, R3/R4 retention expiry, cost and storage ceilings. Clarified the single-record exception at R2–R3, R2 clearance, and the prompt-injection boundary. Defined sighting, independence group, lane, predicate attestation, appraisal, and clearance. |
