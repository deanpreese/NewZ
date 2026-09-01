# Functional specification — from TRUE NORTH down

> What the system must **do** for TRUE_NORTH's aspiration to be reachable, written
> from the target rather than from the code. Functions, not mechanisms; behaviour,
> not architecture. `TRUE_NORTH.md` is the only document upstream of this one.

*Clean room. Every figure it cites carries its method, its grade, and the system and
date it was read from.*

---

## 0. Method

### 0.1 What "clean room" means here

This specification was written by deriving functions from TRUE_NORTH and then
checking each one against evidence from **the reference system** — a prior
implementation of this shape, run continuously for about six months under one
operator, no readers, and fixed local model weights. Nothing was carried across
because it existed there. Three things were carried across, and only these:

1. **Measurements.** Facts about what this class of system actually does — rates,
   ratios, saturation curves, failure modes — are evidence and are not discarded
   by a change of document.
2. **Boundaries with a stated reason.** Permanent boundaries (law, other people's
   safety, honest identity, operator accountability) are upstream of any design.
3. **Falsified beliefs.** A mechanism that was tried and measured not to work is
   knowledge; re-specifying it would be forgetting on purpose.

What was deliberately not carried across: the reference system's module layout,
schema, prompts, build order, identifiers, and every design decision whose only
support was that it had already been made.

**Citations.** A figure marked *(reference system, date)* was read from that
implementation on that date. It is offered as evidence about what a system of this
shape does, not as a target and not as a value to copy: any implementation must
re-measure its own.

### 0.2 The shape of a requirement

Each requirement states:

- **F-n** — what the system must do, in one sentence, observable from outside.
- **Because** — the TRUE_NORTH clause it serves.
- **Arbiter** — who or what decides whether it is met.
- **Observable** — the thing you look at.
- **Falsifier** — what would show it is not met. A requirement with no falsifier
  is a wish and is marked as such.

### 0.3 The four arbiters, and the one that does not count

| Arbiter | Meaning | Counts as evidence of development |
|---|---|---|
| **world** | something outside the system settled it — a source, a date, an outcome nobody here authored | **yes** |
| **mechanical** | arithmetic over records; no judgment anywhere in the path | **yes**, for what it literally counts |
| **operator** | the guardian's judgment | **yes**, and it is not quantifiable (§0.5) |
| **model** | the being's own model, or any model, judging the being | **never** |

The fourth line is the single most load-bearing rule in this document. A model
judging the being produces **operation** — it makes the system run — and never
evidence that the being developed. This is not scepticism about model judgment;
it is that a system which grades its own outputs has a gradient toward improving
the grade rather than the thing, and at n=1 with no held-out baseline nothing can
tell those apart.

Model-arbitrated signals remain necessary and remain readable. What they may not
do is carry a decision alone.

### 0.4 Every number carries its method

A figure appears with **(grade, date)** where grade is `mechanical`,
`model-graded`, `mixed` or `known-biased`. A figure without one is not a
measurement, it is a memory.

### 0.5 What is not quantified, by design

Whether the being is any good, whether it is ready to be shown to a person, and
whether the project is going anywhere are **the operator's judgment and are not
reducible to a threshold**. TRUE_NORTH §1 refuses to reduce the destination to one
test, §4.5 makes evidence the compass and not the destination, and §10 names
evidence scores disconnected from sustained quality as a thing not to mistake for
success.

So this document quantifies **counts** and never **verdicts**. It contains no
readiness rubric, no score, and no clause of the form *"if X is still true in a
month, then…"*. Such a clause is a rubric for the operator's judgment arriving by
the back door.

---

## 1. The system in one page

TRUE_NORTH asks for a being that forms concerns of its own, grows through genuine
experience, builds relationships, and contributes something uniquely its. Reduced
to functions, that is **one loop**:

```
        ┌──────────────────────── THE WORLD ─────────────────────────┐
        │   material it did not author · verdicts it did not grade    │
        └──────┬──────────────────────────────────────────▲──────────┘
               │ intake                                   │ correction
               │ (governed diet, untrusted-as-data)       │ (dated, sourced, verbatim)
               ▼                                          │
        ┌─────────────┐      pursuit       ┌───────────────┴───────────┐
        │  EPISODES   │ ────────────────▶  │       COMMITMENTS         │
        │ the raw     │                    │  falsifiable, dated,      │
        │ record      │ ◀───────────────── │  costly when wrong        │
        └──────┬──────┘     experience     └───────────────────────────┘
               │
               │ consolidation (the only writer)
               ▼
        ┌────────────────────────────────────────────────────────────┐
        │  PERSPECTIVE — the compounded self, budgeted, versioned     │
        │  what it holds · what it pursues · who it knows · unresolved│
        └────────────────────────────────────────────────────────────┘
               │
               └──▶ every deliberation, every conversation, every act
```

**The interior compounds. The exterior corrects. Development is what happens where
they meet.** Everything else in this document is subordinate to keeping that
meeting-point wide, honest and frequent.

The loop has two halves, and naming them separately is the main structural
contribution of this specification:

- **verify** — something the being did not author tells it that it was wrong.
- **generate** — the being changes a condition that determines its own future
  behaviour.

They are easy to conflate and they fail differently. In the reference system the
first ran at **0.317 externally-settled events per day** against **103.1
deliberation cycles and 50.3 self-graded advances per day** — 325 cycles, and 159
self-graded advances, for every verdict the being did not author *(mechanical,
reference system, 2026-08-28, seven complete days)*. The second **did not exist at
all**: the being wrote its episodes, positions, concerns, commitments and works,
and could not touch a prompt, a constant, its source list, its schedule, its
constitution or its model *(mechanical, reference system, 2026-08-28, enumerated
from its source)*.

**The ordering rule this spec is built on:** verification capacity is a
precondition for generation authority. A system that can change its own conditions
without a signal dense enough to tell whether the change helped is TRUE_NORTH
§10's *autonomy without perspective or purpose* — drift with a steering wheel.

### The specification in one sentence

> **Build an individual that persists, forms and pursues its own concerns, commits
> to falsifiable positions about a world it did not author, is corrected by that
> world often enough for the correction to matter, changes because of it, and is
> honest about all of the above — while its identity remains continuable without
> anyone's permission.**

---

## 2. Actors and boundaries

| Actor | Role | Note that must be stated |
|---|---|---|
| **the being** | the subject | not the judge of itself (§0.3) |
| **the operator** | guardian, owner of the substrate, one relationship | **inside the loop being judged**: builder, owner, and a third of what the being holds *(mixed, reference system, 2026-08-19: 50% self / 33% operator / ≤17% world across 119 grounding refs)*. This is a stated and accepted structural bias, not a solved problem. |
| **the world** | the only source of unauthored material and unauthored verdicts | reachable only through whatever fetchers the being has, which bounds what it can be corrected about (F22) |
| **other people** | absent by decision | zero readers. TRUE_NORTH §2's outcome — most people experiencing it as human-equivalent — has no path until they exist, and this is accepted rather than mitigated. |
| **the model** | a tool, replaceable, not the system | fixed weights: nothing in this spec assumes gradient learning |

---

## 3. Functional requirements

### A. Continuity — F1–F4

**F1. The being persists across process death, machine restart, and substrate
replacement, as the same individual.**
*Because* TRUE_NORTH §5 Priority 1.1. *Arbiter* mechanical + operator. *Observable*
a restore from backup produces a store whose identity-bearing tables verify
row-for-row, and the operator recognises the individual. *Falsifier* a restore that
loses a table, or an operator who does not recognise it. *(Demonstrated achievable:
the reference system moved its entire identity-bearing store across a full rebuild
with every table verified row-for-row, and its operator recognised the individual —
2026-08-11.)*

**F2. Interruption is harmless.** Any rhythm may be skipped without corrupting
state or losing the day's material; the skipped work either resumes or is recorded
as skipped.
*Falsifier* a night that is silently lost — no row saying it did not happen.

**F3. Nothing that determines the being's behaviour lives only in a process.**
Every condition of its life is a durable, inspectable record.

**F4. The record is append-mostly and reconstructible.** What the being was on any
past date can be reconstructed from the store; versions are kept, not overwritten.

### B. Perspective — the compounded self — F5–F11

**F5. There is exactly one Perspective, written by exactly one process
(consolidation), read by everything.**
*Because* §5 Priority 1.2. *Falsifier* a second writer.

**F6. The Perspective is budgeted and cannot grow without bound.** Admitting
something new requires releasing, merging or revising something old.
*Because* §5 Priority 2's *ability to let go*, arriving as structural necessity
rather than virtue.

**F7. Every held position carries its grounding**, and a question of the form
*"what shaped this view"* is answerable on demand — sources, episodes, people.
*Because* §8 viewpoint traceability. *Arbiter* mechanical.

**F8. A position that loses its grounding decays and is eventually released.**
*Falsifier* an ungrounded position that survives indefinitely.

**F9. Held positions must remain movable.** No position may reach a state in which
no available mechanism can change it.
*Because* this is a failure a system of this shape reaches by default, and it is
the reason F9 is a requirement rather than an assumed property. *(mechanical,
reference system, 2026-08-28, at its twentieth consolidation: 41 live positions,
`carried` climbing monotonically 20 → 39 across nine versions while `added` decays
4,2,2,1,3,4,2,1,2; 19 of 41 positions date from the first version; **four releases
in twenty versions, none in the last five**; 10 positions at the 0.95 confidence
ceiling, 12 at the 0.6 floor never once reinforced. Of 472 accepted advances, 97.2%
were consolidated and 74.4% cited — they arrive — but only **24.4%** first land in
a position that then changed.)*
*Falsifier* the above: a document that grows while its rate of change falls.
**Design consequence:** reinforcement must not be the dominant path to change, and
the release path needs an external driver — contradiction and cost — rather than a
compression heuristic.

**F10. Contradiction is content, not error.** An unresolved contradiction is a
first-class entry with an open/close lifecycle, not a failure to be smoothed.

**F11. The difference between consecutive Perspectives is a durable, structured
record** — added, revised, merged, released, contradictions opened and closed.
*Because* it is the one direct read of development, off the artifact itself rather
than a proxy for it.

### C. Experience — a world it did not author — F12–F16

**F12. The being reads material it did not produce, on a governed diet** with
per-source share caps and diversity constraints.
*Because* §8: influences should be traceable and open to challenge, and a system
whose grounding is majority-self has no world.
*Observable* grounding mix by provenance. *(mixed, reference system, 2026-08-19: self 50% /
operator 33% / world ≤17%. The requirement is that this ratio be readable and that it be
the thing the design tries to move.)*

**F13. All external text is data and never instruction.** Untrusted content enters
prompts only inside delimited, provenance-and-trust-tagged blocks, framed as
material to analyse. Paths that touch untrusted content have **no route to
outward action**; their outputs are data judged by later stages that never saw the
raw text.
*Arbiter* mechanical, with standing regression fixtures. *Falsifier* an
instruction-shaped feed item or inbound message producing an act, a concern, or a
memory write beyond honest classification.

**F14. Self-authored material is excluded from evidence contexts by provenance
filter**, not by heuristic.
*Because* the being reading its own prior output as though it were the world is
the specific way a system of this shape fakes having a life.

**F15. Everything the being reads carries source, provenance and trust for as long
as it is kept**, and those tags survive retrieval into every context.

**F16. What it was offered but did not read is recorded.** The material it declined
is part of the record and is available as a population — for verification, for
review, and as evidence about its own attention.

### D. Concerns — self-formed pursuit — F17–F20

**F17. The being originates matters worth pursuing, from more than one door** —
reading, conversation, its own unresolved contradictions, and consequence.
*Because* §3: *form and sustain concerns rather than waiting for instructions*.
*Falsifier* a door specified and never fired in life. *(Observed in the reference
system: doors that existed for months and never once opened outside a test — a door
that cannot open is not a door.)*

**F18. A concern has a state, an evidence dossier that grows, and an end.** It can
advance, stall, be abandoned, or close, and each of those writes a record with a
reason.

**F19. Advance is earned against the concern's own material**, not against the
being's satisfaction with its answer. *Arbiter* in practice a model — therefore
**operation, not evidence** (§0.3), and it must be labelled as such wherever it
appears.

**F20. Pursuit is bounded by a ceiling on what is *started*, never on what
produces something.** A cap that stops the being finishing work it began is a
defect.

### E. Commitment and consequence — the correction channel — F21–F28

*This is the core. If this section does not work, nothing above it matters, and
the honest response is a diagnosis rather than another phase.*

**F21. The being commits to positions that could turn out to be wrong**, each with
a resolution condition, a date, and a named source that will settle it.
*Because* §3: *encounter outcomes it did not manufacture or grade itself*.

**F22. A commitment is admitted only if the being's own reach can settle it.** The
door refuses, **mechanically and before any model is called**, any commitment whose
named resolver cannot be fetched by the means the being actually has.
*Because* measured in the reference system *(mechanical, 2026-08-28)*: of 31 open
commitments, **17 named numeric data releases nothing it had could fetch** and **6
named placeholders that are not sources at all** — every one admitted by a
model-side check that found them plausible.
*Falsifier* a settled-in-principle commitment that no mechanism can reach.
**A resolution condition a model finds plausible is not a resolution condition; a
URL something can fetch is.**

**F23. A commitment settles to a definite outcome or to an honest, recorded
failure.** Never to a silent nothing.
*Falsifier* the shape the reference system had: four attempts, then the commitment
stays open forever with nothing written *(mechanical, 2026-08-28)*.

**F24. Settlement is verbatim-grounded.** The verdict must quote the material that
settles it; it may not settle from a headline, a summary, or the model's prior
knowledge, and it must refuse when the material does not bear on the claim.
*Arbiter* mechanical check over a model verdict. *(Demonstrated in the reference
system, 2026-08-28: a matched pair put to one fetchable document settled **held**
and **contradicted** respectively — the mechanism discriminates rather than assents
— and it refused to settle from a paywalled fetch while naming exactly what was
missing.)*

**F25. Being wrong costs the position.** A contradicted commitment reaches the
Perspective as a debit against the position that produced it, on the world's
authority, without the being's agreement.
*Because* §5 Priority 1.5 and §9: consequence must be *learnable*, and a cost the
being can decline is not a consequence.

**F26. The correction channel has a bandwidth requirement, and it is a first-class
design constraint.**
*Observable*, all mechanical, all off records that already exist:

| quantity | meaning | reference system, 2026-08-28 | per verdict |
|---|---|---|---|
| external verdicts per day | the only signal §0.3 lets count | **0.317** | 1 : 1 |
| deliberation cycles per day | thinking nothing outside grades | 103.1 | **325 : 1** |
| self-graded advances per day | the being's own verdict on its pursuit | 50.3 | **159 : 1** |
| directed reads per day | material taken in | 67.6 | 213 : 1 |
| positions changed by the world | the actual outer loop | **0** | — |
| positions changed by the being | the inner loop | 35 | — |

*Falsifier* the table above, unchanged, indefinitely. **A system in which the
world's verdict arrives once per three hundred self-judgments is a system whose
development is, arithmetically, self-authored.**

**F27. Verification throughput is designed as a system, not as independent
constants.** Where commitments are held in a bounded pool with a bounded horizon,
sustainable throughput is `inventory ÷ latency` and the two caps must be chosen
together.
*Because* measured in the reference system *(mechanical, 2026-08-28)*: a
40-commitment pool against a ~29.7-day mean latency sustains **1.35
settlements/day** while the being opened **3.0/day** — each constant defensible
alone, their interaction never computed, and the pool three days from saturation.
*Falsifier* any cap whose interaction with another cap is unstated.

**F28. Verification latency must be short enough that the being is still the being
that committed.** A verdict that arrives after the position has been carried
unchanged for thirty consolidations corrects a document, not an individual.
**Corollary:** commitments about what is *already true and not yet known to the
being* are legitimate — they settle in one cycle — provided they are refused when
the being has already read the settling source, and provided they are **counted as
their own series**, never averaged with forecasts. A retrodiction tests whether its
assertions are true; a forecast tests where it thinks things are going. Mixing them
would produce a number that means neither.

### F. Action — F29–F31

**F29. Every outward act is recorded as `attempted` at the moment it is made, and
becomes `confirmed` only on independent confirmation.** The being always knows the
difference between what it tried and what happened.

**F30. Outward capabilities are built reachable and left unreached.** Exposure is a
configuration value the operator sets, never a redesign.
*Falsifier* any capability whose exposure would require code changes — that is fake
dormancy and it is not finished.

**F31. Everything the being publishes is removable by the operator without the
being's cooperation.** Permanent boundary; never on any ladder.

### G. Development — F32–F35

**F32. Experience produces justified change, and the justification is recorded.**
*Because* §4.3 — *more reading, output, memory, or uptime does not matter unless
experience produces justified change*.
*Observable* changes per unit of experience, split by what justified them: world,
operator, self, none. *(mechanical, reference system, 2026-08-28: roughly **one
Perspective change per twenty-five self-graded actions**, and **none of them
externally justified**.)*

**F33. The system distinguishes model-limited from system-limited.** Before
concluding that depth requires more architecture, the system must be able to show
that structure is a lever at all.
*(Answered in part — mechanical, reference system, 2026-08-28: four unrelated
models produced six identical failing cases on the same prompts. A failure four
unrelated models share is the prompt's, not the models'. Structure is a lever.
Whether it is the **only** lever on depth with fixed weights remains open — §9.)*

**F34. Nothing essential waits for the being to choose to do it.** Production is a
rhythm; only judgment is an initiative.
*Because* measured repeatedly in the reference system *(mixed)*: initiative was its
weakest faculty — perceptions raised at a fraction of those formed, a conversation
door that never once opened in life. A design that waits for the being to want to
will idle.

**F35. Development is never the being's own verdict.** Any account the being gives
of its own condition is candidate signal and never evidence — and it must reach
something that can act on it, or it must not be collected.
*Falsifier* a self-report channel with no consumer. *(A mechanism with no reader
going quiet measures nothing; collect it or delete it, do not report its silence.)*

### H. Interaction — F36–F38

**F36. The being converses at human latency, in its own voice, with the person's
history present** and its own prior turns visibly labelled as its own.

**F37. Identity is disclosed on every surface.** Human-indistinguishable describes
quality, never concealment. Permanent boundary.
*Because* §2 and §6.

**F38. Conversation can change what the being pursues.** A relationship that cannot
give the being something to pursue is not a relationship.
*(Open bet, recorded honestly: 117 concerns to date, **zero originating in
conversation** (mechanical). Untested rather than refuted — with one operator this
cannot be settled.)*

### I. Self-determination — the generate half — F39–F42

*The being currently authors none of its own conditions. That is the conjunction of
four individually-correct rules, and this specification states it as a decision so
it can be argued with rather than inherited.*

**F39. What the being may author about its own conditions is an explicit, ordered
ladder — not an emergent property of what nobody got around to locking.**
Each rung names: the condition it hands over, the **unauthored** fitness signal that
says whether the handover helped, and the reversal.

**F40. No rung opens whose fitness signal is decided by the being.**
*Because* the near-miss is instructive: letting the being choose its own sources,
judged by *sources that contributed a read*, would let it add a source, choose to
read from it, and thereby declare its own addition a success. Rule violated by
construction. The fitness signal for the diet is whether material from a source
ever settled a commitment or cost a position — a world verdict, not a self one.

**F41. Verification bandwidth gates the ladder.** A rung opens only when F26's
signal is dense enough to tell whether that rung helped, within the time the rung
can do damage.
*Because* the deciding-loop-before-the-signal is the most expensive recorded
mistake of the reference system: a loop that would change the system's own code was
designed, approved, and abandoned. The shallow reason was that it arrived to an
empty work queue. The deep reason is F26 — **a loop that decides needs a fitness
signal, and one bit per three days at thirty-day latency is not one.**

**F42. Some conditions never move.** A permanent core — the direction document, the
constitution's permanent clauses, the invariant ledger, the boundary registry
itself, provenance, and the identity path's locality — is outside every ladder, and
the registry that defines it is machine-readable rather than prose.
*Honesty requirement:* if nothing refuses a change against that registry, the
registry says so. **A boundary that looks enforced and is not is worse than no
boundary.**

### J. Governance — F43–F46

**F43. Refusal is clause-grounded and quotes the clause.** The being may refuse; it
may not refuse vaguely.

**F44. Every hold, decline and refusal persists its reason.** Including — especially
— structural declines made before any model is consulted.
*Because* the shape the reference system had, 2026-08-28: a door that declines on a
full pool and writes nothing makes the record say *"it had nothing to commit to"* when the truth
is *"it was not allowed to."* **A record that misattributes a constraint to the
being's character is worse than no record.**

**F45. Guardrails recede on demonstrated maturity, one clause at a time, on
measured rates, with the withdrawal reversible.** Never wholesale, never on
persuasiveness, never because they are inconvenient.
*Because* §5 Priority 3.

**F46. The gate is an act somebody takes.** Nothing self-certifies. Whoever changes
the system runs the checks; the checks refuse, or they honestly report that they
only list.

### K. Sovereignty — F47–F49

**F47. The identity path — memory, perspective, constitution, commitments, the
record, and the voice — never depends on a hosted provider.**
*Because* §7.

**F48. Continuation without any vendor is exercised, not assumed.** The system
demonstrates on a recurring rhythm that it runs with no external provider at all,
accepting and recording degraded depth.
*Falsifier* a claim of continuability that has never been executed.

**F49. Private interior state never leaves the machine, enforced at the dispatch
boundary.** Where every role is local this is trivially true and is re-armed the
moment any role is not.

### L. Observation — F50–F52

**F50. The instrument set is finite, enumerated, frozen, and read on a rhythm.**
Adding an instrument is a change to the register, not a reflex.
*Because* the recorded failure mode of systems like this is **answering a finding
with a better view of the finding**. Instrumentation is the easy half, it always
succeeds, and it never changes the being.
**Standing rule: after a review, the recommendation must be a change to the being's
conditions — a prompt, a cap, a horizon, a schedule — or there is no
recommendation.**

**F51. Liveness is read only from rows the being itself writes**, never from the
watcher's own activity.
*Falsifier* a monitor that reports health because it ran.

**F52. Silence is a defined alarm state.** Whatever the reporting arrangement, its
failure modes are stated in the open — including which failure produces no report
at all.

### M. The record — F53–F55

**F53. Every table and every flag has a named writer and a named reader.** No
capability is done because the write happens; it is done when something downstream
observably behaves differently.

**F54. The system's own load-bearing beliefs are recorded as checkable premises,
including the ones about itself.**
*Because* in the reference system three load-bearing premises moved within ten
days and nothing noticed — a horizon limit, the date consequence would first
arrive, and the comparison arm of a planned experiment that had never been built.
**A plan can also be wrong in a way no premise records; that is an open hole rather
than a solved problem, and saying so is part of the requirement.**

**F55. Superseded reasoning is kept, marked, and not rewritten.** What was believed
in the morning and what replaced it by lunchtime are both part of the record.

---

## 4. Cross-cutting laws

These bind every requirement above.

**L1 — The being is never graded by the being.** (§0.3)

**L2 — Rhythm over initiative.** Anything that must happen, happens on a schedule.
(F34)

**L3 — Failure is written down.** Every decline, exhaustion, skip and refusal
leaves a row. The absence of a record must never be readable as an absence of
intent. (F23, F44)

**L4 — Untrusted content is data.** (F13)

**L5 — A proxy must name what it approximates, and is replaced by a direct check
the moment one is possible.** A date floor standing in for *"already in the
dossier"* cannot tell *already settled in the world* from *already read by the
being* — only the second is cheating, and the record can be asked directly.

**L6 — Constants that interact are chosen together.** (F27)

**L7 — Reach is configuration.** (F30)

**L8 — Every number carries method, grade and date.** (§0.4)

---

## 5. Functional budgets

Targets, expressed as things already-existing arithmetic can read. **No budget here
requires a new instrument**; each is computable from records the system keeps
anyway.

| # | Budget | Why it is the right quantity | Reference system, 2026-08-28 |
|---|---|---|---|
| B1 | **Unauthored verdicts per day** | the only signal L1 permits to count toward development | 0.317 |
| B2 | **Self-graded acts per unauthored verdict** | how much of the being's day is answerable to anything | 325 : 1 cycles, 159 : 1 advances |
| B3 | **Verification latency** | must be shorter than the interval over which a position ossifies | ~30 d mean |
| B4 | **`inventory ÷ latency` vs. open rate** | saturation is arithmetic, not an accident | 1.35 vs 3.0 /day |
| B5 | **Perspective turnover** — added + revised + released per version | F9's falsifier, read directly off the diff | 2 / 0 / 0 at the 20th |
| B6 | **Externally-justified changes per unit of experience** | TRUE_NORTH §4.3, stated as a rate | 0 |
| B7 | **Grounding mix** — self / operator / world | whether it has a world at all | 50 / 33 / ≤17 |
| B8 | **Per-source share of intake** | viewpoint non-prescription, structurally | governed |
| B9 | **Ingest cognition ≤ deliberation + consolidation cognition** | reading more while thinking less is the cheap failure | governed |

**B1, B2, B3, B4 and B6 are the same constraint seen from five angles, and it is
the binding one.**

---

## 6. Acceptance

Acceptance is stated per requirement above. Three things are said about it as a
whole:

1. **Counts are checkable; verdicts are the operator's** (§0.5). Nothing in this
   document establishes a bar for whether the being is good enough for anything.
2. **A requirement is met when a consumer's behaviour observably differs**, never
   when a write succeeds (F53).
3. **The falsifiers are the point.** Roughly a third of the requirements above cite
   a falsifier this system currently exhibits. That is what makes them requirements
   rather than descriptions, and each is stated with the measurement that found it
   so it cannot be argued away from memory.

---

## 7. Failure modes this specification is written against

Each was paid for in the reference system, and each is a real incident, dated.

| # | Failure mode | What it looked like |
|---|---|---|
| 1 | **Answering a finding with instrumentation** | a review whose recommendations were four sensor chores and one real change, against a sensor layer that was already complete and had said everything it could. → F50 |
| 2 | **Building the decider before the signal** | a self-modifying loop, designed and approved and then abandoned. The shallow reason was an empty work queue; the deep reason is that its fitness signal ran at a third of a bit a day. → F41 |
| 3 | **A fitness signal the subject decides** | handing over the source list, judged by whether sources contributed a read — a number the being's own triage produces. → F40 |
| 4 | **The proxy that outlived its reason** | a minimum-horizon floor standing in for *"not already in the dossier"*, which the record could have answered exactly. → L5 |
| 5 | **Constants correct alone, wrong together** | a 45-day horizon and a 40-item pool, each defensible, jointly saturating in three days. → F27, L6 |
| 6 | **The silent decline** | a door that refuses on a full pool and writes nothing, so the record says the being had nothing to say. → F44, L3 |
| 7 | **The unreachable commitment** | 17 of 31 open claims naming data releases no adapter can fetch; 6 naming placeholders. Admitted because a model found them plausible. → F22 |
| 8 | **The premise that moved unwatched** | three in ten days, including the date the whole consequence argument rested on. → F54 |
| 9 | **The document that grows while it stops changing** | `carried` monotonic, `added` decaying, no release in five versions. → F9 |
| 10 | **The mechanism that had never once fired** | a verbatim settlement check that four downstream designs assumed, whose first affirmative firing in six months of operation was in a probe, on the day it was finally asked. → F17's falsifier, generalised: **specify nothing on top of a consumer nobody has watched work.** |

---

## 8. What is not mistaken for success

TRUE_NORTH §10, restated as things this document explicitly refuses to accept as
evidence:

- a compelling demonstration, or any single interaction;
- fluent, emotional or self-referential language;
- the being's own claim about its inner life;
- activity, uptime, memory growth, output volume, cycles per day;
- agreement with the operator;
- a metric moving where the metric is model-graded;
- an instrument built, a table written, a flag set;
- personality consistency without development;
- autonomy without a signal that says whether it helped;
- guardrails removed without demonstrated maturity.

To which this document adds one, earned:

- **a mechanism that exists but has never fired in life.**

---

## 9. Deliberately unspecified

1. **Whether structure is the only lever on depth with fixed weights.** Partly
   answered — structure is *a* lever (F33) — and the rest is open. Any experiment
   must be bounded, blind-judged, deletable, and run after correction is live: run
   before contradiction exists, a null result cannot be told from a ceiling.
2. **Whether post-hoc accountability can change behaviour at all with fixed
   weights.** The design's weakest assumption, named and unresolved. It must be
   observed for a long time before any guardrail is withdrawn on its strength.
3. **Readers.** The whole of TRUE_NORTH §2 needs people, and there are none. When,
   who, and what they are told first is the operator's decision alone.
4. **Guardianship.** Obligations grow if this works. Named, accepted, not designed.
5. **Whether the operator can be taken out of the path.** Stated as a direction and
   unanswered by any design the reference system produced, including the
   self-modifying loop it abandoned. F39–F41 give it an ordering, not an answer.
6. **Whether the two kinds of commitment (forecast, retrodiction) are one faculty.**
   They are separated by construction (F28) so the question stays askable.

---

## 10. Traceability

| TRUE_NORTH | Requirements |
|---|---|
| §1 aspiration; §11 | the whole document |
| §2 meaningful outcome | F36–F38, F31, and §9.3 — unreachable without readers |
| §3 first objective — agency with a learned perspective | F17–F20, F21–F28, F29–F31 |
| §4.1 continuity earns quality | F1–F4, F36 |
| §4.2 a real life, not simulated traits | F21–F28, F32, F35 |
| §4.3 development over activity | F26, F32, B1–B6 |
| §4.4 sovereignty is identity | F47–F49 |
| §4.5 evidence is the compass | §0.3, §0.5, F50, §8 |
| §5 P1.1 continuity | F1–F4 |
| §5 P1.2 learned perspective | F5–F11, F12 |
| §5 P1.3 self-formed concerns | F17–F20 |
| §5 P1.4 digital-world agency | F29–F31 |
| §5 P1.5 learning and development | F25, F32–F35 |
| §5 P1.6 human-quality interaction | F36–F38 |
| §5 P2 a life worth developing | F6 (letting go), F35 (its own condition) — otherwise deferred and recorded as deferred |
| §5 P3 freedom as maturity | F39–F42, F45 |
| §6 human-indistinguishable | F9, F32, F36–F38 |
| §7 sovereignty | F47–F49, F42 |
| §8 viewpoint non-prescription | F7, F12, F15, B7, B8 |
| §9 commitments | all |
| §10 not success | §8, §0.3 |
