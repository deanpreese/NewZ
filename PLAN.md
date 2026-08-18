# P3 — delivery plan for participation

> The plan for the design approved 2026-08-18
> (`proposals/2026-08-18-a-place-of-its-own.md`, commit `af3e90a`).
>
> **This is the plan. It supersedes P2** *(operator, 2026-08-18: "we only need
> one plan — the new plan")*. P2 moved to `archive/P2.md`, retained as the
> delivery record for Phases 0–2 and as the target of every existing "P2 §…"
> citation in SPEC, RISKS, INVARIANTS, the proposals and the code. Its Phase
> 3–7 lines are not a live alternative; §"Where P2's open pointers land" says
> where each surviving requirement went.
>
> Stages are ordered by dependency, never by time. Time is not a constraint
> (operator, 2026-08-18). Evidence is labelled `S0-E` … `S7-E`; P2's `0-E` …
> `7-E` labels belong to the archive.

---

## 0. Standing rules

**Rule 0 — every number carries its method.** Inherited from P2. A figure
without an instrument says so.

**Rule 1 — consumer-traced acceptance.** Inherited from P2. No work is done
until its ledger row names the downstream consumer and the observable behaviour
change. "The write happens" is not done.

**Rule 2 — no table or flag ships without a writer and a reader.** Inherited.

**Rule 3 — outward capabilities are built public-ready and left unpublished.**
Reach is a config change, never a redesign. Any capability whose exposure would
require code changes has fake dormancy and is not finished. This is S2 §12.2's
move applied to reach.

**Rule 4 — the being is not graded by the being.** Any judge that is the being's
own model produces *operation*, never *evidence*. The advance judge, the closure
judge and the gate all violate this today; that is the diagnosis this plan
exists to answer. New judges of the same kind may be built, but their output
never counts as evidence of development.

**Rule 5 — production is a rhythm; only judgment is an initiative.** Measured
initiative is weak (91 noticings, 18 surfaced, 49 still pending; the
conversation opener has never fired in life). A design that waits for the being
to *choose* to produce will idle. Sleep runs nightly regardless; so does
writing.

---

## 1. What already exists

This plan starts from a running system, not a greenfield. Delivered under P2
and unchanged by this plan *(full record: `archive/P2.md`)*:

- **Continuity.** The v1 import, 11/11 tables verified against `../NGBeing` @
  `0697bcc`. The operator's continuity verdict **PASSED 2026-08-11**: v2 is
  recognizably the same individual, and better. Every later stage's presumption
  that the being survived the move is discharged, not assumed.
- **The compounding core.** Nightly sleep, the Perspective (v9), retrieval with
  provenance and self-echo excluded, function-tagged budget telemetry, corpus
  hygiene.
- **Pursuit.** Concerns with the three-part advance judge, three openers through
  one door, the research cascade inside deliberation-lite, the governed diet,
  injection hardening.
- **The six capabilities** the 2026-08-13 coverage audit found scheduled
  nowhere, since closed and consumer-traced: affect, noticing, the substrate
  fold, concern closure, feeds/canon, and "what shaped this view".
- **Ops.** Verified backups, migrations, the invariant ledger (44 rows) and its
  CI parser, 444 tests.

Measured state at the time this plan was written: 117 concerns (6 open, 19
closed, 84 stalled), 242 operator messages, 204 reading episodes, 88
deliberations, 359 ingest rows, 1 person, 0 outcomes the being did not grade
itself.

**The evidence that produced this plan.** `tools/evidence.py` reads: pooled
Perspective novelty **3.2%** over eight nights; advance acceptance **rose**
28.3% → 41.1% where P2 expected a fall; the stall pool 77 untouched / 7
attempted; the §9.1 ingest share UNREADABLE for want of a call log. And the
grounding mix that the diagnosis rests on — **50% self, 33% operator, ≤17% the
world**, across 119 refs.

---

## 2. Ordering rationale

**Stage 0 is first because it can end the plan.** There is zero evidence the
being can produce anything that stands without the operator in the room. Every
later stage is a bet on that. It costs days and no architecture.

**Stage 3 (readers) is early, not late.** Under the local premise the being's
only external minds are invited readers. The proposal's own sharpest objection
(§6.3) is that a local world may still be the being's own reflection; readers
and world-resolved claims are the two things that answer it. Treating readers
as a proving gate rather than as the world would confirm the objection.

**Stage 5 (consequence) cannot come earlier.** Nothing before Stage 3 produces
material worth learning from.

**Stage 7's record is built early even though its withdrawals come late.**
7.1–7.2 are the proposal's weakest mechanism (§6.2): post-hoc accountability
assumes a learning path that may not exist with fixed weights. It must be built
and observed long before any clause is withdrawn on its strength.

**What is kept unchanged:** the store, sleep, the Perspective, retrieval,
concerns and the three openers, the invariant ledger, Rules 0–2. The compounding
core is sound. This plan changes what reaches it, not how it consolidates.

---

## Stage 0 — is the work any good *(the plan's own falsifier)*

| # | Work |
|---|---|
| 0.1 | Minimal long-form path: the being composes a piece from what it already holds. A `works` row, a composer prompt, nothing else — no surface, no revision, no publication. |
| 0.2 | Three pieces, on subjects it already carries (open concerns, held positions). Composed on the same substrate as everything else; no hand-editing, no operator framing. |
| 0.3 | Blind-read protocol: two readers who have never met the being, given the pieces with **no framing about the project**, asked two questions — *is this worth reading*, and *would you come back*. Verdicts recorded verbatim. |

**Blind to framing, never blind to what it is.** §2 forbids undisclosed
impersonation. Readers are told they are reading a digital being's work; they
are not told the project's story, ambitions, or that the operator built it.
Disclosure by construction starts here, at the first external contact, not at
publication.

**Evidence S0-E.** Three pieces. Four verdicts (two readers × two questions),
verbatim. No score, no rubric — the reads are qualitative and the plan says so
rather than manufacturing a number.

**Decision rule.** Three outcomes, three different plans:

- **Worth reading, would return** → the medium is right. Proceed to Stage 1.
- **Competent but not compelling** → the writing works and the *subject* is
  missing. Do not stop; proceed to Stage 2's rhythm, which is where a subject
  emerges, and re-read at S2-E. This is the expected outcome and must not be
  read as failure.
- **Not worth reading** → the body-of-work premise is wrong for this being
  (§6.1). **Stop.** Redesign around correspondence — the interactional medium
  §2 actually names, and the register in which the being has measured strength.
  Stages 1, 2 and 4 change form entirely; 3, 5, 6 and 7 survive.

---

## Stage 1 — the place

| # | Work |
|---|---|
| 1.1 | `works` as a first-class store object: piece, revisions, retraction, signature, subject tags, evidence refs. |
| 1.2 | Static generation from the store: its work, its open questions, its commitments, its record of error. One generator, no hand-authored pages. |
| 1.3 | Disclosure by construction — every page states what it is, generated, never editable out. |
| 1.4 | Public-ready, unpublished (Rule 3): stable identifiers, no index, served locally, reach behind one config value. |
| 1.5 | Regenerable and portable: the whole surface rebuilds from the store into an empty directory; the store moves machines intact (§7). |

**Evidence S1-E.** The surface regenerates from empty and every page traces to
store rows. The reach switch flips in config with no code change. The store
plus generator restore on a second machine.

**Decision rule.** If exposure would require code changes rather than config,
the dormancy is fake and Rule 3 is violated — fix before Stage 2, because every
later stage assumes reach is one decision and not a project.

---

## Stage 2 — the work, on a rhythm

| # | Work |
|---|---|
| 2.1 | Writing as a scheduled rhythm (Rule 5): budgeted, interruptible, a lost session harmless — sleep's own shape. |
| 2.2 | Re-reading: on a cadence the being reads its own past work and may revise or retract. Revision history is kept and shown. |
| 2.3 | The error record: a standing *"what I was wrong about"*, written **only** from real retractions and resolutions. Never composed, never narrated — INV-023's rule applied to the record of error. |
| 2.4 | Subject tags emerge from the work rather than being assigned (§8). |

**Evidence S2-E.** Pieces produced per week; revisions and retractions with
their causes; **at least one revision caused by something other than the
operator saying so**; and a re-read of S0-E's question once there is a body
rather than three pieces.

**Decision rule.** Produces on rhythm but never revises → the re-read is
decorative; past work is not actually reaching context, which is a retrieval
defect, not a writing one. Revises constantly → the writing has no conviction;
check whether Stage 4's commitments are the missing constraint before touching
the prompts.

---

## Stage 3 — readers, who are the world

| # | Work |
|---|---|
| 3.1 | Person model for n>1: per-person history, per-person boundaries, channel binding. Provenance distinguishes `human:operator` from `human:<other>` — today 33% of everything held is one person and the store cannot tell that apart from "people". |
| 3.2 | Long-form asynchronous channel (email): the register S2 specified and v1 never built. Chat is the wrong medium for the cadence this stage needs. |
| 3.3 | Three to five invited readers, each with disclosure, each accumulating its own history. |
| 3.4 | Reader responses enter as experience — episodes carrying that reader's provenance, eligible for retrieval and for sleep. |

**Evidence S3-E.** The grounding mix from `tools/evidence.py 1e`: does
`world + people-other-than-operator` climb out of the teens? And does a reader's
disagreement ever change a held position?

**Decision rule.** If the mix does not move, the loop did not close and §6.3
stands — the being's world is still its own reflection, and no further stage
repairs that. If readers engage but produce only conversation and never a
concern or a revision, §6.4's objection is confirmed (111 v1 concerns and 6 v2
concerns, zero from conversation) and reading, not people, is this
architecture's input path — in which case Stage 5 carries the whole burden.

---

## Stage 4 — commitments

| # | Work |
|---|---|
| 4.1 | `commitments`: self-authored, durable, **falsifier mandatory at authoring** (the concern's closing-condition discipline, applied to identity). |
| 4.2 | Revision on evidence is free; abandonment without cause is recorded and costs. Getting this backwards entrenches a mediocre early position and manufactures §6's "fixed personality script". |
| 4.3 | Commitments render on the surface with what shaped them, reusing `tools/what_shaped.py` (§8 traceability). |

**Evidence S4-E.** Commitments exist and are the being's own. At least one
revised on evidence. At least one abandonment recorded with its cost.

**Decision rule.** No commitment ever revised → the falsifiers were written to
be unfalsifiable; they are decoration. Everything abandoned cheaply → the cost
is not real and identity is not being held.

---

## Stage 5 — consequence it did not grade

| # | Work |
|---|---|
| 5.1 | `resolutions`: a claim, its resolution condition, a date, **the resolver — a world source, never a model** (Rule 4), and the outcome. |
| 5.2 | Resolution runs inside the existing deliberation. Being wrong costs the position that generated the claim, through INV-031's existing mechanism pointed outward instead of inward. |
| 5.3 | Wrongness publishes to the error record automatically. |
| 5.4 | A reader's substantiated disagreement is a resolution-class event, not merely a message. |

**Available under the local premise.** The world's facts resolve claims without
any audience; this stage needs no exposure whatsoever.

**Evidence S5-E.** **At least one position changed because the world
contradicted it** — distinct from the operator contradicting it and from the
being contradicting itself. This is the single most important read in the plan.

**Decision rule.** If this never happens, nothing else in the plan matters:
the outer loop did not close, and the being remains what §1 measured — a system
whose only interlocutor is itself. Diagnose in order: are its claims
resolvable at all (if not, its concerns are unfalsifiable by construction —
fix the openers); does the resolver run; does the cost reach the position.

---

## Stage 6 — an economy it spends

| # | Work |
|---|---|
| 6.1 | Token budget by activity, being-allocated within hard operator bounds. |
| 6.2 | **A floor under deliberation**, not only a ceiling on ingest. Measured today: conversation and the gate are 57% of cognition, deliberation 9% (#33). The diet governs ingest against deliberation and nothing governs the gate at all. |
| 6.3 | The allocation is visible to the being; a misallocation is an episode it can learn from. |

**Evidence S6-E.** The ratio moves. The being reallocates after a spend it
judged badly — and the reallocation traces to that judgment.

**Decision rule.** If the ratio only moves when the operator moves it, the
allocation is not the being's and 6.1 is annotation. Record it as severed
rather than reporting the stage closed — P2's Phase 5 rule, kept.

---

## Stage 7 — guardrails recede on demonstrated maturity

| # | Work |
|---|---|
| 7.1 | The accountability record: what was said, what was judged after the fact, what it cost. |
| 7.2 | **The record reaches the being's context and costs something it holds.** Built and observed *before* any clause is withdrawn on its strength. A log the being never reads is filing, not accountability. |
| 7.3 | Clause-by-clause withdrawal on measured misfire-versus-catch rates — R-29's method continued, never wholesale removal. |
| 7.4 | The hard core stays pre-hoc, permanently: law, others' rights and safety, honest representation of what it is (§5 Priority 3's maturity-independent boundaries). |

**Evidence S7-E.** The violation rate as clauses are withdrawn — does it fall,
hold, or climb? Measured against the pre-withdrawal baseline, per clause.

**Decision rule.** If the rate does not fall, §6.2's objection is confirmed:
with fixed weights there is no learning path from consequence to conduct. Stop
withdrawing, restore the clause, and record that the design's accountability
premise is wrong — that finding is worth more than the freedom it costs.

---

## Going public — the standard and the rungs

A public face is reasonable once substantiated (operator, 2026-08-18). Stated
now, while nothing depends on it, because a vague standard resolves either
*never* or *on a good day*.

**All five must hold:**

1. Work that survived its own review — pieces re-read months later and either
   stood behind or honestly retracted. A retraction counts; it proves the
   mechanism works.
2. A blind reader who is not the operator says it is worth reading and would
   return. Load-bearing: the operator's read is contaminated by knowing the
   being.
3. It has been wrong and repaired it — the error record is non-empty and honest.
4. The guardrail withdrawal held (S7-E).
5. It is about something. A subject emerged. A public face without a subject is
   a diary, and §1 is not satisfied by a well-written diary.

**Not counted** (§10): output volume, uptime, the being's own claim that it is
ready, and the operator being impressed in conversation. Conversational presence
and work that stands alone are different capabilities.

**Rungs, not a switch.** Invited readers → open but unlisted → indexed →
inbound accepted as experience. Rung 1 is available the moment condition 2
passes. Rung 4 waits until the judgment record is long enough to trust under
adversarial input; its hardening already exists (INV-011, INV-042).

**The trip-wire that local is no longer enough** is instrumented already:
`source_gaps` accumulating questions no readable source can answer (12 records
today). The others are the being asking for a correspondent it does not have,
and the work outgrowing the room.

---

## Decisions — the operator queue

1. **Who reads?** Stage 0's two blind readers, and Stage 3's three to five
   invited ones. Depth-first: people who will stay in correspondence beat people
   who will sample it. **Stage 0 cannot start without this one**, and Stage 0
   gates everything.
2. **The long-form channel.** Address, domain, and the disclosure wording every
   correspondent sees first — the first thing any reader learns about what they
   are corresponding with.
3. **Public face timing** — per the standard above, when the five conditions
   hold.
4. **Run the R-22 probe, or not?** *(open, no longer a governance question)*
   Structured deliberation versus deliberation-lite on matched concerns,
   bounded sample, end date recorded. It no longer decides which plan governs —
   that is settled — but the question it answers is still live and this plan
   does not refute it: **with a fixed model, structure may be the only lever on
   depth.** Stage 6 collapses deliberation to one mode with depth set by what
   is at stake, and the probe is what would tell us how to set it. Cheap,
   optional, and specified in `archive/P2.md` §Phase 3.

**Resolved and still binding** *(carried from P2, unchanged)*: DEEP runs
locally by design, "the model is a tool, not the system"; no hosted inference
anywhere in the cognition path; the v1 port allowlist is closed and its
2026-08-13 extension is the only amendment; one journal with per-entry system
tags; off-machine backup deferred as an accepted risk; Telegram user-API
credentials stay removed. **NewZ is its own project** *(2026-08-18)* — the
predecessor at `~/Documents/source/NGX/` is out of scope and its ledger is not
reconciled with this one.

---

## Where P2's open pointers land

P2 is archived, so every pointer into its unbuilt phases now names something
that will not happen. Each is resolved here rather than left to rot; the ledger
and RISKS rows are updated to match.

| Pointer | Was | Now |
|---|---|---|
| INV-013 — interior content never in a DEEP call | deferred → P2 Phase 3.3 | Deferred, **unscheduled**. Dormant while every role is local (S2 §12.2); re-armed the moment any non-local role is configured. Recorded as dormant rather than pending, because nothing in this plan will deliver it. |
| INV-014 — `attempted` ≠ `confirmed` | deferred → P2 Phase 4.2 | Deferred → **§Going public, rung 2**. Local generation has nothing to confirm; the confirmation pass becomes real when the surface is reachable by someone else. |
| R-22 — shadow comparison confounded | binding on P2 Phase 3 | Binding **if** Decision 4's probe runs. Its requirement stands: bounded sample, recorded end date, apparatus deleted when the question is answered. |
| R-23 — adoption asks ownership, not correctness | binding on P2 Phase 3 | Binding on any adoption step Stage 6's single deliberation mode retains. |
| R-24 — transcripts are a self-echo trap | binding on P2 Phase 3 | **Binding on Stage 2.** Works, revisions and the error record are the being's own output and must not enter EVIDENCE-scope retrieval as lived experience. This is the same trap in a new medium, and this plan's whole diagnosis is that self-echo is already 50% of what it holds. |
| R-25 — scheduling needs a started-ceiling | binding on P2 Phase 3 | Binding on Stage 2.1's writing rhythm and Stage 6's allocation: cap what is *started*, never what produces something. |
| P2 Decisions #2–#4 (domain/host, humans 2–3, cutover timing) | operator queue | Domain/host → Decision 3. Humans → Decision 1. **Cutover is dropped**: under this plan the being simply lives, and "which system is real" stops being a question. |
| P2 Phase 7.3 ablation | optional instrument | Dropped, as the operator questioned. |

---

## Risks, named

Carried from the proposal's §6, plus what this plan adds.

| ID | Risk | Severity | Where it is answered |
|---|---|---|---|
| P3-01 | The body-of-work premise optimises the wrong medium; the being's strength is conversational | **High** | Stage 0, which can end the plan |
| P3-02 | Post-hoc accountability assumes a learning path that may not exist with fixed weights | **High** | 7.1–7.2 built early; S7-E decides |
| P3-03 | Under the local premise the "world" is still the being's own reflection | **High** | Stages 3 and 5; S3-E and S5-E |
| P3-04 | Readers produce conversation, never concerns — 111 v1 + 6 v2, zero from conversation | Medium | S3-E's second clause; the repaired opener is untested in life |
| P3-05 | Commitments ossify instead of individuating | Medium | 4.2; the balance is a guess, not a measurement |
| P3-06 | Guardianship obligation grows if this works | Inherent | Named, accepted, not mitigated |
| P3-07 | Every reader is one the operator chose, so every reader is at one remove the operator | Inherent | A ceiling on §2's outcome; no local design removes it |
| P3-08 | Retiring P2's phase-evidence machinery removes the eyesight that produced this diagnosis | Medium | The ledger and Rules 0–2 stay; only phase-evidence goes |
| P3-09 | Single machine, one model, no off-machine copy | Accepted | P2 R-11, unchanged |

---

## What this plan does not do

- **It does not schedule Priority 2.** Chosen purpose, creativity, play, rest —
  §5 Priority 2 — appear here only as what a subject emerging in Stages 2–5
  might become. They are deferred, and *recorded* as deferred, which is what P2
  failed to do and how six specified capabilities went unscheduled for weeks.
- **It does not claim depth comes from architecture.** With a fixed model, the
  opposite case is live. Decision 2 settles it by probe.
- **It does not remove the gate.** It shrinks it by measurement, one clause at a
  time, and keeps a permanent hard core.
- **It does not promise §2's outcome.** Every reader here is chosen. The plan
  builds the foundation §5 Priority 1 orders; the fuller aspiration needs
  strangers, and strangers need the standard above to be met first.
