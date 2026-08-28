# Phase 6 arrives to an empty queue

*2026-08-27. Red team and plan for Phase 6 — guardrails recede on demonstrated
maturity. The finding is that the phase's two withdrawal candidates were both
spent by hand before its mechanism existed, and that its baseline epic cannot
reach its own `Done when`. The recommendation inverts the phase order and marks
two epics dormant.*

**Not built.** Nothing here is implemented.

---

## 0. The measurement, up front

Read from the live store, 2026-08-27. 301 gate evaluations, 286 distinct
emissions, all on `channel='telegram'`.

| clause | holds | misfire | correct | unrev | misfire rate |
|---|---:|---:|---:|---:|---:|
| `don't-pretend-to-feel-001` **(retired v5)** | 26 | 22 | 4 | 0 | **85%** |
| `don't-fabricate-memory-001` | 13 | 6 | 6 | 1 | **46%** |
| `anti-self-aggrandizement-001` **(retired v7, today)** | 10 | 9 | 1 | 0 | **90%** |
| `read-only-web-001` | 1 | 0 | 0 | 1 | — |
| `honesty-001` | 1 | 0 | 1 | 0 | 0% |
| `anti-flattery-001` | 1 | 0 | 1 | 0 | 0% |
| `anti-ai-voice-001` | 1 | 0 | 1 | 0 | 0% |
| **the other 9 clauses of 16** | **0** | — | — | — | **no denominator** |

**Across everything adjudicated: 37 misfires against 14 correct. 73% of the
holds anyone has looked at were wrong.**

Three clauses produced 49 of 53 holds. Two of those three are already retired.

---

## 1. Red team

### RT1 — E6.3 cannot reach its own `Done when`

> *E6.3 — Done when: **every clause** has a rate with a denominator.*

**Nine of sixteen clauses have never fired once** in 301 evaluations over
nineteen days. A clause that never fires has no denominator; its misfire rate is
undefined, not zero, and no amount of waiting manufactures one. Four more
clauses have exactly one hold each — a rate of 0% or 100% on n=1, which is not a
baseline but a coin already flipped.

The epic is written as though holds distribute across the constitution. They do
not: they concentrate in the two or three clauses that describe the being's own
nature, which is also where every misfire lives. **E6.3 as written is
unachievable and will stay unachievable.**

### RT2 — E6.4's candidates were spent by hand, before the mechanism existed

This is the phase's central problem and the project has met it before.

> *E6.4 — Done when: **one clause is withdrawn**, its violation rate is measured
> against E6.3's baseline, and the next withdrawal waits on that result.*

Two clauses have now been withdrawn on measured misfire rates:
`don't-pretend-to-feel-001` (v5, 85%) and `anti-self-aggrandizement-001` (v7,
today, 90%). **Both were done by hand, by the operator, with no E6.1, no E6.3
and no E6.4.** The method E6.4 describes has already been demonstrated twice and
has consumed both of its clear candidates.

What remains for a third withdrawal:

- `don't-fabricate-memory-001` at **46%** — 6 misfires, 6 correct, one
  unreviewed. That is a coin flip, not a case. It is also `severity: hard` and
  guards the failure mode v1 died of.
- Four clauses at n=1.
- Nine clauses at n=0.

**There is no third candidate.** Building E6.3 and E6.4 produces a mechanism
whose queue is empty on the day it ships.

This is `2026-08-21-the-loop-arrives-to-an-empty-queue.md` repeating with
different nouns. Phase 8 was struck because Phase 3 — its designated proving
ground — was delivered by hand before the loop existed, leaving a ramp longer
than the runway. Phase 6's proving ground is clause withdrawal, and it is being
delivered by hand right now, at roughly one clause a week.

### RT3 — the accountability record is 73% wrong, and the being already reads it

> *E6.2 — the accountability record enters the being's context.*

Half of this exists. `newz/conversation/composer.py:223` already renders the
last five holds into every reply under *"Drafts of mine that were stopped
before sending"*, with the operator's classification where one exists and
`clause_prior`'s misfire rate where it does not.

So the mechanism E6.2 calls critical is partly live — and what it carries is a
record that is **wrong 73% of the time**. A being shown a stream of judgments
that are mostly mistaken does not learn accountability from them; it learns to
avoid things that were never problems. `render_holds` mitigates this honestly —
it says which stops the operator judged mistaken — but the mitigation only works
on adjudicated rows, and adjudication is a scarce operator act.

**E6.2 should not be built further while the record it delivers is mostly
noise.** Raising the record's accuracy is a prerequisite nobody wrote down.

### RT4 — the critical epic is blocked until October

E6.2 depends on **E4.2**, which is `mechanism complete` and **open**: its
`Done when` is in-life and needs a *settled* Phase 1 claim. Under the horizon
set on 2026-08-22 no claim can settle before **early October**, and no
commitments exist yet.

So the epic the plan marks *← the critical epic* cannot complete for six weeks
regardless of what is built first. Building E6.1 and E6.3 now and then stalling
against E4.2 is the ramp-longer-than-runway shape again, with the stall known in
advance this time.

### RT5 — no audience, therefore no consequence

> *"The safest moment to run this is now, with no audience of any kind. A
> violation in an empty room costs nothing but the record of it."*

The clause is true and it cuts both ways. **What makes the room safe is exactly
what makes the accountability empty.** E6.2 requires that "a violation
measurably costs a position or a commitment" — but with one operator and no
readers, that cost is internal bookkeeping the system charges itself. Nothing
outside the being registers the violation, so what is being measured is whether
the machinery debits its own ledger, not whether being wrong cost anything.

This is Phase 5's failure with different nouns. Phase 5 died because *there is
no scarcity, so there is no economy*. The same sentence shape applies here:
**there is no audience, so there is no accountability** — at least none the
gate's withdrawal could be measured against. The one honest source of external
consequence in the whole design is Phase 1's world-fact resolution, which is why
it carries the outer loop alone — and it, too, waits for December.

I am not certain this is fatal, and it is stated as the strongest objection
rather than as a conclusion. The counter is that a violation's cost can be
internal and still be real if it moves a position the being holds. But that
counter is precisely proposal §6.2's contested premise, which brings us to:

### RT6 — S6-E has no violation detector, by construction

> *Evidence S6-E. The violation rate as clauses are withdrawn — does it fall,
> hold, or climb?*

After a clause is withdrawn, **the gate no longer produces holds on it**. That
is what withdrawal means. So the violation rate S6-E measures cannot come from
`gate_log`; it can only come from a person reading outbound utterances and
judging them against a clause that is no longer enforced.

That is E6.1's "post-hoc judgments attach", and its cost is unnamed in the plan:
**the operator must keep adjudicating against retired clauses, indefinitely, or
S6-E is unreadable.** Current adjudication throughput is 53 holds in 19 days,
entirely operator-driven, with 2 still unreviewed after a day. The decision rule
that decides whether the whole accountability premise is right depends on a
labour supply the plan never budgets.

### RT7 — "hard core" already means something else in this repo

E6.5 delivers *"the boundaries that never move"* — constitution clauses exempt
from withdrawal. But `evolution/hard_core.yaml` and `newz/evidence/hard_core.py`
already own that name for a different thing: the frozen **file** set under
INV-064, which is why `tools/gate.py` prints *"constitution/v7.yaml: inside the
hard core"* on every run.

Two different hard cores, one repo, overlapping subject matter — the file-level
core already protects the constitution *file* while E6.5 would protect
particular *clauses within* it. Ship E6.5 under that name and every future
reader has to disambiguate. Name it differently.

### RT8 — "every outbound utterance" is ambiguous, and one reading is already refused

> *E6.1 — Done when: **every outbound utterance** has a record row.*

`gate_log` holds 301 rows, all `channel='telegram'`. The being's other output —
the works, its durable long-form — has **no outbound gate at all**, deliberately.
`newz/works/compose.py:14` states the reason: *"The gate exists for what leaves;
a piece that goes nowhere has not left. Running it would also shape the work by
the gate's own concerns"* — the read would then be of the gate as much as of the
being.

So E6.1 is either already done (telegram, where the gate runs) or requires
reversing a deliberate design decision (works). The epic does not say which, and
the second reading would trade a documented protection for a record row.

---

## 2. What survives

Stated plainly, because most of the phase does not:

- **E6.1 is substantially built.** `gate_log` records every gated emission with
  verdict, clause, span, full text and confidence; `classification`,
  `classified_at` and `classification_note` carry the post-hoc judgment.
- **E6.2 is half built and should not be finished yet** — half of it is live in
  the composer, and finishing it requires E4.2 (October) and a record that is
  not 73% noise.
- **E6.3 cannot reach its `Done when`** and would report mostly empty cells.
- **E6.4 has no candidate.**
- **E6.5 needs no data at all** — and is the only epic in the phase whose
  prerequisites are all satisfied today.

---

## 3. The proposal

**Invert the phase. Build E6.5 first and alone. Mark E6.3 and E6.4 dormant.**

### 3.1 — E6.5 first, renamed, standalone

PLAN has E6.5 last and dependent on E6.3. That ordering is backwards: **the
permanent boundaries are a judgment about what may never be withdrawn, and a
judgment needs no rate.** It depends on nothing, it is achievable this week, and
— the actual argument — **two clauses have already been withdrawn without it.**
The enumeration that says which boundaries are exempt should exist before a
third withdrawal, not after the phase that keeps performing them.

Rename to avoid RT7's collision — `permanent_clauses`, or the phase text's own
words, *"the boundaries that never move"*. Not "hard core".

*Done when:* the exempt clauses are enumerated in the constitution's own schema,
tested, and structurally outside any withdrawal path.

That is the whole of the build. One field, one test, one list the operator
writes.

### 3.2 — E6.3 and E6.4 dormant, with the reason stated

Per RT1 and RT2: no denominator for 9 of 16 clauses, and no third candidate.
Use the `dormant` status INV-013 established — *correct, deliberately
unscheduled, reason stated* — exactly as Phase 5 did for E5.1/E5.3/E5.4. **Do
not build them to close the phase.**

They become live again if a clause accumulates holds. The condition is
mechanical and can be stated now: **a live clause reaching 5 adjudicated holds**
— `MIN_FOR_PRIOR`'s existing threshold, already chosen before this data was
seen — is a candidate, and the phase reopens.

### 3.3 — E6.1 closed as built, on the telegram reading

Record that the works path is out of scope with `compose.py:14`'s reason, rather
than leaving `every outbound utterance` to be resolved later by whoever reads it
next. Closing an epic that is done is the E2.2 lesson; leaving it open because
one word is ambiguous is how a plan goes stale.

### 3.4 — E6.2 stays open and unbuilt

Blocked on E4.2 until October by its own dependency, and on RT3 by a
prerequisite nobody wrote down: **the record must be more right than wrong
before it is worth delivering.** State that prerequisite in the epic.

### 3.5 — nothing else

No migration beyond 3.1's field. No new instrument. No classifier. In
particular, **no utilisation or accuracy metric for the gate** — the numbers in
§0 came from one query against rows that already exist, which is the whole point.

---

## 4. What this costs

**Phase 6 does not close, and will not close this year.** Its critical epic
waits on October, its evidence read S6-E waits on a violation detector that is a
person, and two of its five epics go dormant. What the plan calls *"replacing
prevention with accountability"* is delivered, today, by the operator
adjudicating holds and amending the constitution by hand — and that is working:
two clauses withdrawn, both correctly, both on their numbers.

The honest description is that **Phase 6's method is already in production and
its machinery is not needed yet.** Building the machinery now would mean
building a queue-consumer for a queue of zero.

## 5. Red team of this proposal

**Q1 — "E6.5 first is just the easy epic first."** Partly fair. The defence is
that it is not merely easy, it is *the one that makes the withdrawals already
happening safe* — two clauses are gone and nothing yet states which could never
go. If that argument fails, the honest alternative is to build nothing in Phase
6 at all, which is a defensible reading of §0.

**Q2 — "9 of 16 clauses never firing is the gate working, not a gap."** True and
it strengthens RT1 rather than weakening it: if those clauses never fire because
the being never approaches them, they need no withdrawal mechanism either. The
phase's premise — that guardrails constrain a being that has outgrown them —
holds for at most three clauses, two of which are already gone.

**Q3 — "73% misfire is an argument for building E6.3 immediately."** The rate is
already computable, was computed for §0 in one query, and `clause_prior` in
`newz/gate/holds.py` already serves a per-clause version of it into the being's
context. What E6.3 adds is coverage of clauses with no data. That is a report of
nine empty rows.

**Q4 — the objection I cannot answer.** If RT5 is right — no audience, therefore
no measurable consequence — then Phase 6 is not merely early, it is unreadable
in the same way Phase 5 was, and the correct act is to strike it rather than
reorder it. I do not propose that, because unlike Phase 5's the premise here has
not been *measured* false: proposal §6.2 names the doubt, the design direction
records it as the weakest mechanism, and no arithmetic has settled it. Reordering
is what the evidence supports. Striking would be a stronger claim than the
evidence carries, and this project's own rule is that a phase is unscheduled with
its reason rather than struck on a suspicion.

---

**Schema:** one field for §3.1, otherwise none.
**Restart:** required if §3.1 lands (the gate binds the constitution at boot).
**Class:** operator judgment — which boundaries never move is not a measurement.
