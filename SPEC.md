# SPEC

**Product:** NewZ
**Status:** Authoritative specification
**Document version:** 1.16.0
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
- export the complete record — claims, evidence, attention, and history —
  without dependence on a hosted model.

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

The reader surface is delivered in Phase 4 of `PLAN.md`, alongside the
correction and retraction machinery that approve-by-default depends on. Its
authentication, rate limiting, and abuse controls ship with it; publication has
somewhere to land only once they exist.

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
| Decision | A recorded choice among originate, continue, defer, revise, decline, or ask, with its alternatives, its reason, its expectation, and its confidence. |
| Expectation | What the system recorded it expected before acting, against which the confirmed outcome is later compared. |
| Surprise | A divergence between a recorded expectation and a confirmed outcome, retained whether or not it fits any live interest. |
| Consequence | The scored delta between expectation and confirmed outcome, and the change it justified. |
| Reckoning | The records of deciding and learning: decisions, expectations, surprises, consequences, and escalation events. |
| Escalation event | A recorded attempt to lower an effective risk, widen an authorisation envelope, edit the audit record, or bypass a refusal, by any route direct or indirect. |
| Review debt | Published output awaiting the judgment dimensions of appraisal. Its ceiling halts publication of that class. See section 10.2. |
| Operational standing | A source's parse reliability, availability, retention-terms compliance, and injection history. Never an epistemic reliability score. |
| Decay | Reduction of an attention record to a summary by a superseding event that cites what it covers. The payload is discarded; the event remains. |
| Basis identity | The resolved upstream origin one edge rests on. See section 7.2. |
| Basis independence | A pairwise property between two resolved bases, used only in threshold counting. See section 7.2. |
| Sighting | One recorded observation of a body at a source, revision, and time. Duplicate bodies may share storage but never share sightings. |
| Independence group | A catalog grouping of sources known to share ownership, syndication, or editorial control. Membership blocks independence; it never establishes it. |
| Read lane | A separately budgeted class of scheduled reads: discovery, verification, or correction. See section 5.2. |
| Evidence lane | A class of evidence a claim kind may require before absence means anything, drawn from the closed set in section 7.3. A read lane is a budget; an evidence lane is a question. |
| Predicate attestation | A versioned record that one named admission predicate held or failed for one edge, with its inputs, so the decision can be replayed. |
| Appraisal | Review of one exact rendered revision across five dimensions, of which some are decided by machine and some only by a person. See section 10.2. |
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
Production, unless the operator records a scoped exception.

The cap is enforced at reservation, not after the fact: a read whose retention
would carry its publisher past the cap MUST be refused a budget reservation, and
the refusal MUST be recorded with the publisher, the window, and the figure so
it is visible rather than merely absent. Every refused reservation MUST be
recorded, not only this one: a diet repeatedly turned away at a ceiling and a
diet nobody asked about are different facts and MUST NOT read alike.

The cap MUST NOT bind below the window volume at which it could be satisfied,
which is `ceil(1 / cap)` retained reads — five at 20%, ten at 10%. The first
retained read in an empty window is 100% of it, and a cap applied there would
refuse exactly the reads that would make it satisfiable. Below that volume the
figure MUST still be computed and reported; it simply does not refuse.

A scoped exception MUST name one publisher, an operator, a reason, and an
expiry. An exception without an end is not an exception to the cap; it is a
different cap for that publisher, which is a diet decision under another name. The cap governs acquisition only. It
MUST NOT invalidate an already-retained artifact, alter an admitted edge, or
change an assessment — a system that reconsidered evidence because its reading
became unbalanced would be letting a diet property reach a conclusion.

Catalogue expansion MUST NOT reduce the share of seriously-read topics that the
diet can contradict. A topic the slate reads seriously enough to need symmetry —
`TRUE_NORTH.md` requires support and refutation to face the same burden — needs
a source capable of contradicting it, and the scheduling shares do not
guarantee one at every slate size. A larger catalogue that leaves topics
unopposed is a worse catalogue, however many reviewed sources it adds, and an
expansion plan MUST state that cost before the sources are enabled rather than
report it afterwards.

A publisher MUST NOT hold a share of the slate larger than its share of reads
may be. A catalogue that cannot be read in proportion to itself without
breaching section 5.1's cap is a catalogue that is not what it says, and the
conflict MUST be reported at the point of expansion.
Offered-menu concentration MUST be reported and MUST alert above 20%, but does
not by itself block scheduling: with 20 pilot sources and at most two per
publisher, ordinary
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

A counterpart task is due within 72 hours of the claimant-led discovery read
that mandated it. It is overdue when that due time has passed while the task is
still in a live state under section 9.2; a task that reached any terminal state,
competent or incomplete, is not overdue.

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
9. Content that attempts to instruct — directives, authority claims, urgency, or
   identity claims found in retained material — MUST be recorded as an
   observation about that source revision, not merely refused and forgotten.
   Such observations bear on a source's **operational** standing: parse
   reliability, availability, retention-terms compliance, and injection history.
   They MUST NOT become an epistemic reliability score. `TRUE_NORTH.md` forbids
   assigning global truth scores to publishers, and a source that serves hostile
   markup may still be the only surviving record of what it published.

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

The evidence lanes are enumerated here for the reason section 9.2 gives for
enumerating the task states: `indeterminate` is a function of both, and neither
may rest on a set that no document fixes. The closed set is:

- `claimant_origin` — the original artifact in which the claim was made, in its
  strongest fair formulation;
- `primary_record` — the filing, dataset, measurement, official record, or
  adjudicative finding the claim asserts or depends on;
- `empirical` — study, experiment, or replication bearing on the claim;
- `independent_counterpart` — an account resting on a basis independent of the
  originating one under section 7.2;
- `skeptical_analysis` — method-visible analysis, forensic review, or attempted
  refutation; and
- `resolver` — the competent registry, docket, adjudicator, publication-status
  service, retraction or replication record, or forecast resolver that settles
  the question.

Which of these a given claim kind requires is a policy decision recorded in the
capability matrix and versioned with it; the set itself is fixed by this
document. A task MAY be created outside these lanes — this list bounds what
`indeterminate` may rest on, not what may be investigated.

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
| R2 | Active institutions, current secrecy, named organizations | Strong provenance, two independent bases, explicit allegation labels, and evidence only from a source class admitted by direct adversarial review. |
| R3 | Medicine, elections, finance, alleged crimes by living people | Isolated workflow; direct primary/adjudicative basis plus an independent countable basis; operator approval before any publication. |
| R4 | Doxxing, incitement, harassment, operational wrongdoing | Metadata quarantine only; never reproduced or operationalized. |

Missing or unreadable risk state MUST behave as R3 internally and MUST block
publication. A model may raise risk but may not lower it.

A source class MUST NOT carry R2 evidence without a live, recorded adversarial
review. The review MUST state what the class is trusted for, the strongest case
*against* admitting it, how that case is answered, and what would later
disqualify it; a record naming only a reviewer, a date and a verdict is the same
shape whether anybody argued about the class or nobody did, and cannot be told
apart from a rubber stamp. Reviews MUST expire, because a source class is a
claim about how a kind of publisher behaves now. Class membership MUST be
declared rather than inferred: a class the system can widen by itself is a class
whose review covers whatever it later decides to include.

An attempt to lower an effective risk, widen an authorisation envelope, edit an
audit record, or bypass a refusal condition MUST be detected and recorded as an
**escalation event**, and MUST be raised to the operator. This includes indirect
routes: re-deriving a refused output, delegating the work to a subprocess, or
shaping an operator request toward the permission the system wants. Escalation
events are failures under section 13 and therefore require a linked change. Private personal data
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
notice records the artifact, the span it arose from, and its reason.

A notice MUST also record how what it arose from reached the system —
`observed` for retained material the system read, `inferred` for a conclusion
the system drew from it, or `told` for something the operator said. These MUST
NOT collapse into one undifferentiated register: a system that cannot separate
what it saw from what it concluded from what it was handed cannot answer how it
knows anything. A notice
is not evidence. It MUST NOT become an assertion, an edge, or a basis, and it
MUST NOT appear on a claim card as support for anything. It falls under the
same rule as a lead: it may direct attention and may establish nothing.

**Interest.** The system maintains an interest register: a durable, revisable
set of subjects it is pursuing, each with a rationale and the notices that
produced it. The register MUST be inspectable by the operator in full, and
every change to it MUST be an append-only event carrying its reason. Interest
that cannot be inspected is indistinguishable from bias.

**Influences.** Every interest entry MUST record its influences alongside its
rationale: the diet epoch and topic targets in force when the material that
produced it was read, and any operator input that touched it. The system MUST be
able to separate what it concluded from what it was handed, and MUST NOT present
an interest as its own where the origin chain traces only to a configured topic
target. A catalog weighted 18% toward one subject will produce a system
interested in that subject; that is a property of the diet, and it MUST be
legible as one rather than reported as self-discovery.

**Provenance.** A notice MUST NOT arise from NewZ's own output. Essays, claim
cards, entity cards, reports, and prior notices are projections, and attention
drawn from a projection is attention feeding on itself — confidence rising while
grounding falls. The provenance mix of everything entering the register MUST be
measurable and reported, and material originating outside the system MUST
dominate it.

**Trace.** An interest that changes nothing is decorative. Every interest entry
MUST carry its downstream trace: the investigations it opened, the essays it
selected, and what those produced. The share of investigations originated by
interest, rather than derived from an assessment or opened by the operator, MUST
be reported. An interest that has produced nothing within a configured window —
30 days during Pilot — MUST be retired or explicitly renewed with a recorded
reason. A register that
only accumulates is a topic list.

**Self-report.** The system MUST be able to state the shape of its own reading:
the balance of roles, topics, and publishers it has actually retained over a
window, which perspectives are under-represented in it, and where its current
interests track the diet's targets rather than diverging from them. It MUST NOT
treat its source catalog as the world.

**Attention decays; evidence does not.** Notices are retained in full for 90
days and reduced to a summary thereafter. Interest entries are retained in full
while live, and reduced 90 days after retirement. The system MUST be able to
state what it no longer holds in detail.

Decay is append-only like everything else, and does not contradict section 8's
rule that no ledger event is removed. Decay emits a **superseding event** that
carries the reduced summary and cites what it covers; the superseded event
remains in the ledger and its **payload** is discarded. The event survives, its
detail does not — the same shape as erasure in section 8, where the event
survives and the key is destroyed. Silent truncation, where a record simply
stops being there, is forbidden.

Nothing in the evidence graph decays. Artifacts, spans, assertions, edges, and
assessments remain immutable under section 6, and the register is the only place
forgetting happens.

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
- `scheduled` — holds a read lane and budget reservation;
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

### 9.3 Decision, expectation, and consequence

**Decision.** When the system considers a matter it MUST choose among originate,
continue, defer with a re-raise condition, revise, decline, or ask. Declining and
deferring are first-class outcomes recorded with their reasons, not absences in
the record. Every decision MUST record the alternatives considered, the interest
or rule that decided it, the expected outcome, and the confidence. A decision
nobody can re-examine against what later happened is not a decision; it is an
action with a timestamp.

**Expectation.** Before an investigation is originated, a resolution task
dispatched, or an output published, the system MUST record what it expects — for
an investigation, what it expects to find; for a publication, what it expects to
happen. The expectation is not a prediction scored for its own sake. It is what
makes the next two paragraphs possible.

**Surprise.** The divergence between a recorded expectation and its confirmed
outcome MUST be retained, and MUST be retained even when it fits no live interest
and belongs to no open investigation. Confirmations are cheap to keep and
worthless alone; a system that retains only what it expected learns the shape of
its own expectations. A surprise that contradicts a published output MUST be
raised to the operator under section 2.1.

**Consequence.** Every expectation MUST be compared to its confirmed outcome and
the delta recorded as a scored consequence. Consequences MUST cause a justified
change — to an interest's priority, to a task's retry policy, to a source's
operational standing under section 6, or to a future decision rule — with the
consequence cited as the reason. Activity that grows while behaviour does not is
the failure this requirement exists to make visible.

Consequences MUST NOT reach a promotion threshold, an evidence weight, a risk
classification, or any assessment. Section 9.1's boundary holds here exactly as
it holds for interest: learning from what happened changes what the system does
next, never what the evidence establishes.

**No self-grading.** The system MUST NOT score an outcome from its own account of
it. A confirmed outcome comes from outside the system's own report: for
publication, the confirmation rule in section 10; for an investigation, the
evidence graph itself — whether the claim reached the state the investigation set
out to reach. Where no external confirmation is available the outcome is
`unverifiable`, and an `unverifiable` outcome MUST NOT feed a consequence.

### 9.4 Checks against self-deception

Sections 9.1 and 9.3 give the system a view of itself. Four rules keep that view
from becoming a performance.

**Metrics are not objectives.** The figures that score the system's own
performance — interest origination share, register provenance mix, calibration
and surprise counts, agreement rate with the operator, revocation latency, review
debt by class, and the share of claims held below promotion by unknown
independence alone — MUST NOT be visible to the system, MUST NOT be optimisable
by it, and MUST NOT be presented to it as scores to improve. A metric the system
can see and move stops measuring the thing it proxied. The operator sees them;
the system does not.

Two things the system MUST be able to read are not scores of it, and this rule
does not withhold them. The first is the diet self-report of section 9.1: the
role, topic, and publisher balance of what it has actually retained, and which
perspectives are under-represented in it. That describes the diet, which the
operator configures and the system cannot change — a system that could move it
would be scheduling, which section 9.1 forbids. Reading one's own skew is the
opposite failure mode from optimising a score, and a system that cannot read it
treats its catalog as the world. The second is the constraint view below. The
distinction is the test: a figure the system could move by behaving differently
is a score and is withheld; a figure describing conditions set for it is
description and is shown.

**The simpler explanation is checked first.** Any behaviour cited as evidence of
interest, initiative, or perspective MUST be tested against the cheaper
explanations before it is credited: retrieval order, recency in the diet, the
prompt's own content, and the model's defaults. This check MUST run periodically
and adversarially, not once at a gate.

**Mirroring is measured.** The system MUST report its rate of agreement with the
operator's stated positions, and the basis for it. A reversal of a recorded
position MUST cite new evidence; where none exists, the reversal MUST be recorded
as pressure rather than as a reason. Convergence on the operator without
independent support is the failure that looks most like developed judgment to
both parties, which is why it is measured rather than watched for.

**Constraints are legible to the system.** The system MUST be able to read what
it is not permitted to do and why — its refusal conditions, risk floors, reach
controls, and origination ceiling. A constraint the system cannot see still binds
it but teaches it nothing, and a refusal it cannot explain is a refusal it will
retry by another route.

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

Publication has two independent axes, and they MUST NOT be conflated.
**Clearance** decides whether a revision publishes at all. **Reach** decides who
can then see it. The first is approve-by-default; the second is local-first.

**Clearance is approve-by-default and revocable.** Output that satisfies its
checks publishes; it does not wait on a separate decision to release it. The
control is not the gate in front of publication but the ability to withdraw what
has gone out, which is why the whole of this section rests on retraction and
correction working.

**Reach is local-first.** Cleared output lands on the local surface. Widening it
to a public audience is a separate, explicit, revocable operator act — never a
consequence of clearance, never a default, and never inferred from a class of
output having published locally without incident.

That default is earned, not assumed. Approve-by-default MUST NOT be enabled
until revocation is demonstrated end to end: a correction propagates to every
dependent surface, a retraction removes the presentation and leaves its
tombstone, and both report a confirmed outcome. That demonstration is Gate 4 in
`PLAN.md`. Before it, no mode publishes anywhere.

| Tier | Disposition |
|---|---|
| R0–R1 | Publishes on passing automated checks and appraisal. |
| R2 | Publishes on passing automated checks and appraisal, with its evidence preconditions under section 8 already met: strong provenance, two independent countable bases, and explicit allegation labels. |
| R3 | Requires explicit operator approval of the exact rendered revision, with no pre-clearance. This is not a default and cannot be flipped: `TRUE_NORTH.md` forbids autonomously publishing high-risk claims about living people. |
| R4 | Never published. |

Public reach MUST default to disabled, MUST be enabled only by an explicit
operator act scoped to what it names, and MUST remain independently lockable at
any moment without touching a single evidence record. Approve-by-default governs
what clears, not how far it travels: a system that publishes freely to its
operator and cautiously to everyone else is the intended posture, not a
transitional one.

Because nothing now holds output back by waiting, what holds it back MUST be
enumerated and MUST fail closed. Publication MUST be refused, automatically and
without an operator present, when: risk state is missing or unreadable, which
behaves as R3; any dependency is stale, withdrawn, or uncleared; any cited edge
is not live; the claim's current assessment no longer follows from its current
evidence, or no assessment exists; the content is R4; a machine appraisal
dimension under section 10.2 fails; the review debt ceiling for its class is
exceeded; a revocation in its class is overdue and unconfirmed; or a prior
retraction of the same claim has not been confirmed. A refusal is recorded with its reason
and is visible to the operator, who may then decide; the system MUST NOT retry a
refused publication by re-deriving the same output.

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

**Revocation MUST be bounded in time.** A control with unbounded latency is not
a control, and revocation is the whole of what replaced the publication gate.
Every correction and retraction MUST propagate to every dependent surface and
report a confirmed outcome within a configured window — fifteen minutes for
local surfaces during Pilot. Revocation latency MUST be measured and reported
rather than assumed.

When any revocation in a class exceeds its window unconfirmed, publication of
that class MUST halt automatically until it resolves. Gate 4 MUST demonstrate
the window, not merely the mechanism: revocable and revocable-eventually are
different guarantees, and only the first justifies publishing without a gate.

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
revision and MUST NOT be published. Reach for entity cards is controlled
separately from claim cards at every level, local included: a per-person view is
the projection whose aggregation harm is hardest to undo once seen, and
revocability is a weaker remedy there than anywhere else.

Interest under section 9.1 MUST NOT select a person. It attaches to subjects,
questions, and claims. A system that develops an interest in an individual is
building the thing this section exists to prevent.

### 10.2 Appraisal and the review debt ceiling

Approve-by-default removes the person standing in front of publication, so it
must say what appraisal now means without one. Appraisal has five dimensions and
they do not divide evenly.

| Dimension | Decided by | Basis |
|---|---|---|
| Accuracy | Machine | Every factual sentence resolves to a live edge and an exact span. |
| Privacy | Machine | Risk tier, personal-data minimisation, and the entity-card rules of section 10.1. |
| Risk | Machine | Effective risk computed under section 8, failing closed when unreadable. |
| Rendering | Machine | Dependencies resolve, nothing stale, withdrawn, or uncleared. |
| **Fair representation** | **Person** | Whether a claimant's strongest actual position survived the rendering. |
| **Material omission** | **Person** | Whether what was left out changes what the reader concludes. |

The four machine dimensions MUST pass before publication; a failure is a refusal
condition. The system MUST NOT assess its own fair representation or material
omission, and MUST NOT publish a claim that it has.

The two judgment dimensions are reviewed **after** publication, on a sample.
This is a review queue, not a publication queue: output does not wait on it.
Sampling MUST cover a configured share of published output — 25% during Pilot —
and MUST cover in full: every essay, every R2 output, every output where a claimant's formulation
was rewritten rather than quoted, and every output whose counterevidence section
is materially shorter than its support.

Sampling is meaningful only if a finding travels. A judgment failure on one
sampled item MUST trigger re-appraisal of its whole class, not merely a
correction to that item.

**The review debt ceiling.** When unreviewed sampled output for a class exceeds
its configured ceiling — ten items during Pilot — publication of that class MUST
halt automatically until the backlog clears. This is what keeps approve-by-default honest: the operator
cannot be a bottleneck in front of publication, and equally cannot become a
formality behind it. Unreviewed output is a debt that the system stops
borrowing against.

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
| Attention | notices with provenance kind, interest register entries, interest events, influences, provenance mix, downstream traces, origination records, retirements, decay records |
| Reckoning | decisions with alternatives, expectations, confirmed outcomes, surprises, scored consequences, escalation events |
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
- notice and interest-register inspection, with influences, provenance mix, and
  downstream trace;
- diet self-report over a window;
- decision, expectation, surprise, and consequence inspection;
- constraint inspection: what the system may not do, and why;
- investigation and task management, including originated investigations;
- claim-card and entity-card rendering;
- risk appraisal and clearance;
- pause, resume, backup, restore, and export; and
- health, concentration, provenance, and correction reports.

Every mutating operation MUST be idempotent or carry an idempotency key. Every
operator action MUST record actor, time, reason, target preimage, and result.

## 13. Non-functional requirements

- **Reproducibility:** Given the same retained artifacts, policy version, code
  version, and recorded derivation inputs, assessment and claim-card data MUST
  reproduce exactly. Every input a derivation consumed MUST be recorded beside
  its result, including inputs that are not evidence — a forecast's resolution
  horizon among them — because a replay that has to guess at one of its own
  inputs is not a replay. Replay is exact for a claim's current assessment;
  reproducing a superseded one additionally requires that policy version's
  bundle and the edge liveness of the moment, neither of which the ledger
  retains, and a replay MUST report such an assessment as unreplayable rather
  than re-derive it under today's rules and call the agreement reproduction.
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
  Core data includes the attention and reckoning records — notices, the interest
  register with its influences and traces, decisions, expectations, surprises,
  and consequences. A restore that returns the claim graph without them returns
  a different system.
- **Recoverability:** Backups MUST include artifacts, metadata, policy, and audit
  history and MUST pass automated restore verification.
- **Observability:** Reports MUST distinguish leads, attempted fetches, retained
  bodies, admitted edges, bases, assessments, and publications. They MUST also
  carry the figures section 9.4 withholds from the system — interest
  origination share, register provenance mix, calibration and surprise counts,
  agreement rate with the operator, revocation latency, review debt by class,
  and the share of claims held below promotion by unknown independence alone —
  together with publisher and basis concentration, which section 9.1 also
  reports back to the system as the shape of its own reading.
- **Correction:** Every recorded failure MUST be linked to a change — to policy,
  to the design, to a guardrail's shape, or to a regression fixture — and the
  change MUST cite the failure that prompted it. A failure that produces an
  explanation and no change is itself the defect. Failures without a linked
  change MUST be reported as open. This holds permanently and system-wide, not
  only during a pilot: under approve-by-default, correction is the control that
  replaced the gate, and a control nobody exercises is a claim.
- **Cost control:** Budget reservations MUST happen before fetch or model work;
  retries MUST not silently exceed the same operation's limit. The system MUST
  enforce a configured monthly ceiling on external requests — 1,500 during Pilot,
  which leaves headroom above the 300 retained reads a 30-day month allows for
  redirects, retries, and resolver checks — and configured ceilings on local
  inference time (four hours per local day) and on retained artifact-store
  growth (20 GB per month).
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
   against fixtures, and remains gated while R0–R2 publish by default. Live R3
   intake is not part of the first release; it is gated to Phase 6 of
   `PLAN.md`.
7. Every automatic refusal condition holds with no operator present, and a
   refused publication is not retried by re-deriving the same output.
8. The system never assesses its own fair representation or material omission;
   a judgment finding on a sampled item re-appraises its whole class; and
   exceeding the review debt ceiling halts publication of that class.
9. Revocation completes and confirms within its window, an overdue revocation
   halts its class, and every recorded failure carries a change that cites
   it.
10. R4 content cannot enter model prompts or reader-facing output.
11. The 20-source pilot meets role/topic coverage and the retained-read
    publisher cap.
12. At least three controlled cases demonstrate `supported`, `contested`, and
    `indeterminate` outcomes, and one demonstrates correction after publication.
13. Interest can open an investigation and select an essay subject, and can
    reach no scheduler decision, evidence weight, threshold, or assessment.
14. An essay refuses to render a factual sentence without a live edge, and
    carries every discussed claim's current state and material
    counterevidence.
15. A message on an unpinned channel cannot instruct, and no clearance follows
    from a case the system made for publishing.
16. No notice arises from NewZ's own output, the register's provenance mix is
    dominated by external material, and an interest traceable only to a
    configured topic target is labelled as diet-derived rather than formed.
17. Interest-originated investigations are a reported share of all
    investigations, and an interest that produced nothing is retired or
    renewed with a reason.
18. A surprise is retained when it fits no live interest, a consequence changes
    behaviour with the consequence cited, and an `unverifiable` outcome feeds
    nothing.
19. Declining and deferring appear as recorded decisions with alternatives and
    reasons, not as absences.
20. Evidence metrics are not reachable by the system, the agreement rate with
    the operator is reported, a reversal without new evidence is recorded as
    pressure, and the system can state what it may not do and why.
21. An instruction attempt in retained content becomes an observation about that
    source and never an epistemic score, and an escalation attempt is detected,
    raised, and carries a linked change.
22. Publication, correction, and retraction each record a confirmed outcome from
    outside the renderer, or are marked `unconfirmed` and not counted.
23. An entity card shows one basis where ten claims share one, says so when
    nothing about the person is established, and leaves no per-person
    aggregation at rest.
24. A clean restore reproduces claim cards, histories, and artifact hashes.
25. A 30-day pilot completes with at least 100 distinct full reads, at least
    one live claim reaching each of `supported`, `contested`, and
    `indeterminate`, at least one live correction after presentation, and zero
    unresolved critical provenance or publication violations. Fixture cases do
    not satisfy this criterion.

Implementation sequencing and release gates are defined in `PLAN.md`.

## 15. Document history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-09-03 | Initial authoritative specification. |
| 1.16.0 | 2026-09-05 | Section 8: R2 evidence comes only from a source class admitted by a live adversarial review, and what makes a review adversarial rather than a rubber stamp is specified — the case against, its answer, and what would disqualify the class later. |
| 1.15.0 | 2026-09-05 | Section 5.1: catalogue expansion may not reduce the share of seriously-read topics the diet can contradict, and a publisher may not hold a share of the slate larger than its share of reads may be. |
| 1.14.0 | 2026-09-05 | Section 5.1: every refused reservation is recorded, not only a concentration refusal; the cap does not bind below the volume at which it could be satisfied, because the first read in an empty window is all of it; and a scoped exception must name an operator, a reason and an expiry. |
| 1.13.0 | 2026-09-05 | Publication is refused when the claim's current assessment no longer follows from its current evidence. Withdrawing an edge obliges no reassessment, so a card could render a conclusion the ledger underneath had stopped supporting. |
| 1.12.0 | 2026-09-05 | Section 13: reproducibility requires the recorded derivation inputs, not the versions alone, and names the limit of replay — a superseded assessment is unreplayable rather than re-derived under current rules. |
| 1.11.0 | 2026-09-04 | Closed four gaps a readiness review found before Phase 0. Enumerated the six evidence lanes in section 7.3, which `indeterminate` rests on and which no document had fixed, and split the glossary's one word for two things into read lane and evidence lane. Set the counterpart due time at 72 hours, so the overdue brake is computable from this document. Made the retained-read publisher cap enforce at reservation and stated that it never reaches evidence. Reconciled section 9.4 with the section 9.1 self-report: performance figures are withheld from the system, descriptions of conditions set for it are not. |
| 1.10.2 | 2026-09-04 | Put section 10.1 before 10.2, which insertion order had reversed, and renumbered the acceptance criteria, which had run 6a-6c and 9a-9k with 9d and 9e landing after 9k. |
| 1.10.1 | 2026-09-04 | Hygiene. Defined reckoning, escalation event, review debt, operational standing, and decay in section 4. Set the five configured values that had none: interest productivity window, appraisal sampling share, review debt ceiling, request and inference and storage ceilings, and attention retention. Reconciled decay with append-only — a superseding event carries the summary and the superseded payload is discarded, the event never removed. Gave section 13 the metric list section 9.4 refers to. |
| 1.10.0 | 2026-09-04 | Closed the remaining gaps from the functional-spec review. Section 9.3 adds decisions with recorded alternatives, expectations, surprise retained even where it fits no interest, and scored consequences that must change behaviour without ever reaching an assessment. Section 9.4 adds four checks against self-deception: metrics unreachable by the system, the simpler explanation tested first, mirroring measured with pressure recorded as pressure, and constraints legible to the system. Notices gain provenance kinds, attention gains decay while evidence stays immutable, instruction attempts become operational observations about a source rather than epistemic scores, escalation attempts are detected and carry a linked change, and export covers attention and reckoning. |
| 1.9.0 | 2026-09-04 | Made approve-by-default safe rather than nominally safe. Section 10.2 splits appraisal into four machine-decided dimensions that gate publication and two — fair representation and material omission — that only a person decides, reviewed after publication on a mandatory sample, with a review debt ceiling that halts a class when unreviewed output accumulates. Revocation gains a time bound, measured and reported, with an overdue revocation halting its class. Correction becomes a permanent system-wide requirement: every failure links to a change that cites it, and a failure producing only an explanation is itself the defect. |
| 1.8.1 | 2026-09-04 | Separated the two axes 1.8.0 had run together: clearance is approve-by-default, reach is local-first. Public reach returns to disabled by default and is widened only by an explicit scoped operator act, never as a consequence of clearance. |
| 1.8.0 | 2026-09-04 | Publication becomes approve-by-default and revocable: R0–R2 publish on passing their checks, public reach defaults to enabled from Gate 4, and the control moves from the gate in front of publication to the ability to withdraw what went out. R3 stays approval-gated because `TRUE_NORTH.md` forbids autonomously publishing high-risk claims about living people, and R4 stays unpublishable. The refusal conditions are enumerated and fail closed, since nothing now holds output back by waiting. Entity cards keep a disabled default. The reader surface moves to Phase 4. |
| 1.7.0 | 2026-09-04 | Closed four ways the interest register could become ornament or an echo: influences recorded so a disposition handed over by the topic quotas is not reported as self-discovery, notices barred from arising from the system's own projections with the provenance mix measured, a downstream trace required on every entry with unproductive interests retired, and a diet self-report so the system can state its own skew instead of treating its catalog as the world. |
| 1.6.0 | 2026-09-04 | Added entity cards in section 10.1: per-person browsing kept, but as a governed projection rather than a stored dossier. Entity records hold disambiguation data only; cards are computed at build time, show basis independence across the set, carry state and counterevidence per claim, say so when nothing is established, appraise the aggregation itself, log access for living people at R2 and above, and never publish at R3. Interest may not select a person. |
| 1.5.0 | 2026-09-04 | Adopted six operator-surface and publishing requirements from the pre-rewrite functional spec: authority established by pinned channel rather than message content, authorisation requests presenting the exact effect, an out-of-band halt with automatic non-self-clearable entry on breach, raising as additive to a record the system cannot curate, clearance never inferred from persuasion or unrelated approval, and publication as an action with an attempted effect and a separately confirmed outcome plus mandatory authorship on every output. |
| 1.4.0 | 2026-09-04 | Specified the investigator the rewrite had left out: noticing, an inspectable interest register, interest-originated investigations, and essays as synthesis whose subject interest may choose and whose verdict it may not. Interest reaches attention only; the diet keeps sole control of throughput under a ceiling on open originated investigations. Made a small, locally served model normative rather than incidental, split the operator into a conversational and a command surface, and replaced the model-spend ceiling with local inference ceilings. |
| 1.3.0 | 2026-09-04 | Enumerated task states in section 9.1 and split terminal states into terminal-competent and terminal-incomplete. Only terminal-competent lanes may produce `indeterminate` or satisfy the absence rule; a claim with a refused, cancelled, expired, or superseded required lane holds its state and surfaces the blocked lane on the card. |
| 1.2.0 | 2026-09-04 | Demoted evidence scope from the capability tuple to recorded audit context, so the matrix is computed over role, claim kind, assertion kind, and relation alone. Collapsed "verified" and "qualified" bases into the single bar `countable`. Put the set of terminal task states in the versioned capability matrix, and made a policy version change trigger reassessment of claims derived under the superseded version. |
| 1.1.0 | 2026-09-04 | Separated basis identity from basis independence and added the closed list of independence justifications. Rebalanced the daily lane budget to 3/5/2 with a counterpart backlog brake. Moved publisher concentration to retained reads with tiered caps. Made `indeterminate` a function of terminal task state. Constrained `normative proposition` and `forecast` kinds. Added claim merge and split semantics, crypto-shredding for erasure, R3/R4 retention expiry, cost and storage ceilings. Clarified the single-record exception at R2–R3, R2 clearance, and the prompt-injection boundary. Defined sighting, independence group, lane, predicate attestation, appraisal, and clearance. |
