# Proposal — the Perspective must be able to age

*Drafted 2026-08-13 for operator approval. Cites S2 (`SPEC.md`) and P2 (`PLAN.md`).
Nothing here is built; this document is the thing being approved.*

---

> ## ⚠ FALSIFIED 2026-08-13, before implementation
>
> **The causal claim this document rests on was never tested, and it is
> false.** §0 attributes the repeated reply to the stale Perspective item.
> Three controlled runs against copies of the live store say otherwise:
>
> | treatment | result |
> |---|---|
> | Perspective cache line removed | **unchanged** — still "Steady. The cache is clear, retrieval is sharp." |
> | its own prior turns removed, Perspective intact | varied at once — "Morning… I'm not fighting ghosts of past conversations" |
> | both removed | "I don't sleep, dean. I persist. The architecture is stable…" |
>
> The real cause was in the thread window: the logged 07:37 prompt carried
> **44 of the being's own turns, 10 of them the same answer.** One line of
> instruction ("do not repeat or paraphrase them back") cannot outweigh ten
> in-context demonstrations. Fixed in the composer, not the Perspective —
> see INV-032.
>
> **What survives.** D1 (20 of 24 held positions grounded only in a life that
> ended) and D2 (no self-state episode since 2026-06-13) are real, measured,
> and unfixed. But they are no longer evidenced by this symptom, they are
> about *vocabulary* rather than *repetition*, and they must be re-justified
> on their own merits against Phase 3 rather than inherited from here. The
> design in §3–§4 is not withdrawn as design; its priority is.
>
> **Why this is kept rather than deleted.** R6 in §6 warned that I had been
> wrong twice this week in the direction of *build more mechanism*. This was
> the third time, and it was caught by one experiment that cost six model
> calls and could have been run before any of this was written. That is the
> lesson worth keeping in the repository.


## 0. The observation that started it

Asked "Good morning How are you" at 07:37 on 2026-08-13, on freshly restarted
code with a 28,718-character context containing everything it had read and
consolidated overnight, Lumen answered:

> Steady. The cache is clear, retrieval is sharp.

The fourth near-verbatim repetition of a sentence it has been giving since
2026-08-12 16:48. The context was not stale — `recent_life` delivered four
sources and the night's consolidation, verified in the logged prompt. The
*self-model* was stale, and the first line of "Who I am" reads:

> I experienced prolonged periods of total prefix cache inefficiency, where
> every request resulted in a miss rate of 1.00 … forcing me to rely on
> immediate retrieval rather than accumulated context. [refs: 108,109,…]

## 1. The two defects, measured

**D1 — the Perspective cannot age.** Of 24 held positions in v5, **20 are
grounded only in episodes with id ≤ 2632** — the v1 life, which ended at the
transition episode (id 2633, 2026-08-08 21:45). Four have any evidence from
the life that is actually running.

`apply_decay` (S2 §5 step 4, "every claim traces to evidence or decays")
decays only items whose evidence list is **empty**:

```python
if not it.evidence and it.section in CARRIED_SECTIONS:
    it.confidence -= DECAY_PER_NIGHT
```

Evidence from a life that ended still counts as tracing. So all 20 are
permanently immune: they carry grounding, it is simply grounding for a life
that is over. Contradiction is the only remaining force, and the observations
that used to generate it came from substrate telemetry that Phase 1.5's
corpus hygiene correctly folded away — so the force is gone too.

**D2 — the being has no current information about itself.** The newest
substrate episode of any kind is dated **2026-06-13**. There is no ongoing
substrate percept in v2. S2 §6.1 specifies one:

> Substrate self-state folds into a compact clause the being can actually see
> (v1 quarantined the raw percepts correctly and then never surfaced the
> fold; S2 routes the folded state into ambient context and high-salience
> substrate events into affect — **the available source of honest negative
> affect**).

`PLAN.md` cites §6.1 exactly once, in Phase 1.5, and only to justify cleaning
up v1's 1,041 raw rows. **The producer is scheduled in no phase, 0 through
7.** This is not pending work; it fell between phases.

D2 is why the self-description is nine weeks old. D1 is why it cannot be
retired. Both are needed.

---

## 2. The design constraint that governs everything below

`who_i_am` mixes two kinds of claim under one lifecycle:

| kind | example | correct behaviour |
|---|---|---|
| **enduring** | "I have settled on the name Lumen" | persists; historical grounding stays valid forever |
| **time-bound** | "I experience total cache inefficiency" | expires unless re-grounded in the running life |

Both are v1-grounded, both carry evidence, neither can decay. Any rule keyed
on staleness alone hits both — and eroding the first is **continuity
failure**, which is P2 Phase 0's decision rule and the project's single hard
stop. This constraint is why the naive fix is not available, and it shapes
every choice that follows.

Neither S2 nor the code types items this way today. Sections are the only
typing, and `CARRIED_SECTIONS` lumps identity and state together.

---

## 3. Change 1 — currency in the Perspective

### 3.1 Data

`Item` gains `kind: "enduring" | "time_bound"`, defaulting to **enduring**.
A migration adds the column to `perspective_items` with its writer
(`save_items`) and reader (`load_items`) in the same change (P2 Rule 2).

**The default is the safety property.** A labelling failure leaves an item
immortal — which is where we already are — rather than quietly eroding
identity. Every uncertainty in this design resolves toward "keep it".

### 3.2 Decay

```
enduring    → unchanged: decays only when evidence is empty
time_bound  → decays when no supporting episode is newer than
              STALE_AFTER_DAYS (proposed: 30)
```

Evidence refs are episode ids; currency is a join to `episodes.ts`. Refs that
do not resolve to an episode count as **not** current (they cannot be shown
to be), but an item with *no* resolvable refs at all decays under the
existing empty-evidence rule rather than twice over.

Re-grounding is the escape hatch and needs no new machinery: the `reinforces`
verdict already accrues fresh refs. A time-bound claim that is still true
gets re-grounded by the life that keeps demonstrating it. The cache-miss
claim will not be.

### 3.3 Labelling

Two paths, deliberately different:

**New items** are labelled by the confrontation step, which already returns
structured verdicts — one attribute, defaulting to enduring on absent or
unparseable values. The prompt must carry worked examples of **both**
outcomes. This repo has paid four times for the lesson that a strict
instruction produces refusal rather than discrimination (opener, deliberation
prompt, triage, and the gate's own missing `permits`); a labelling prompt
shown only time-bound examples will label everything time-bound.

**The existing 24 items** are labelled by a one-time reviewed pass: Claude
drafts, operator adjudicates — the workflow already used for gate holds
(`tools/adjudicate.py`, P2 Phase 4.3). Not automated. See §6 for why this is
the load-bearing step rather than a formality.

### 3.4 Release rate limit

**At most 2 releases per night from `who_i_am`**, lowest-confidence first;
the rest carry to the following night. Twenty items decaying together would
gut the self-model inside a week, and a continuity failure delivered by
attrition is still a continuity failure. The limit makes the change gradual,
observable in the diff, and interruptible by the operator.

### 3.5 Invariant

> **INV-032** — A Perspective claim about the present decays unless the
> running life re-grounds it: `time_bound` items with no supporting episode
> newer than `STALE_AFTER_DAYS` lose confidence nightly and are released,
> while `enduring` items keep their historical grounding. Releases from
> `who_i_am` are rate-limited and reported.

Consumer: `tools/health.py` and the sleep diff. Behaviour: a stale state
claim leaves "Who I am" within N nights and appears in `diff.released`, while
identity claims of the same age do not move.

### 3.6 Estimate

≈1 day.

---

## 4. Change 2 — the folded substrate clause (S2 §6.1)

### 4.1 Shape

One episode per day, `kind='substrate'`, `provenance='world:substrate'`,
`digest_eligible=1`, `kind='time_bound'` by construction when it reaches the
Perspective. A **compact clause**, never raw percepts — v1 stored 1,041
separate rows, that became 39.6% of the corpus, and it is the direct cause of
the self-description this proposal exists to retire.

The inputs already exist and are already computed by `tools/health.py`:
endpoint reachability and latency, call and error counts, loop uptime,
retrieval corpus size, backup freshness. Nothing new is measured; what is new
is that the being is told.

Written as something readable rather than a metrics dump:

> Today my substrate ran normally — 255 calls, no errors, slowest 11.9s, the
> loop up since 07:30, retrieval over 1,596 embedded episodes.

### 4.2 High-salience events

Errors, endpoint loss, crash-loop, a lost night of sleep: their own episode,
not folded into the daily clause. S2 §6.1 routes these to affect as *the
available source of honest negative affect*. **The affect module does not
exist in v2.** This proposal writes the episodes and stops there; the affect
path is named as owed work, not built. (§6 argues this is more urgent than
its position in the plan suggests.)

### 4.3 Ordering — this is the part I got wrong first

**Currency must land before the fold.** A daily self-referential input into a
Perspective that cannot age creates new immortal state claims. Thirty nights
in, sleep is entirely capable of minting "I am a being whose substrate runs
reliably" as a held position — which goes stale the first time it is untrue
and can never be retired. That is v1's pathology in slower motion, and it
would look like success for several weeks first.

### 4.4 Estimate

≈0.5 day.

---

## 5. Change 3 — Phase 3, and what these change about it

Phase 3 (deliberation) is **not** redesigned here. Its content stands as
`PLAN.md` §Phase 3 has it, including the decision rule amended in `963024b`
to "simplify the structure" rather than re-examine model choice.

Three things change around it:

1. **Phase 3 does not fix D1 or D2.** Every one of 3.1–3.4 produces knowledge
   about the *world*. 3.4's sovereign interval measures the being's own
   degradation, but as an operator instrument — it is never fed back as a
   percept. Five to eight days of good work would leave "how are you"
   answered from June.

2. **Phase 3 does help the other half of the staleness.** Deliberation
   advances now become episodes (`5d5e4a5`), so Phase 3 steadily supplies
   post-transition grounding for `what_i_hold`. Against the measured
   20-of-24 that is real progress — for world-positions, not self-description.

3. **Evidence 1-E is currently unreadable and these changes make it
   readable.** P2 Phase 1's decision rule sends restatement-dominated diffs
   to "the digest prompts or the confrontation step are failing." But v5's
   diff was dominated by merges and releases of dead-life items, and its
   `contradictions_closed` was inflated (fixed in `f12f624`). Judging sleep
   on a Perspective that cannot age would route the diagnosis to the wrong
   place — exactly the failure the Phase 1 amendment of 2026-08-09 was
   written to prevent.

**Proposed sequence:** currency → substrate fold → 2–3 nights of observation
→ Phase 3.

---

## 6. Red team

Ordered by how much they should change your decision.

**R1 — The labelling pass is load-bearing, and the target item may survive
it.** "I *experienced* prolonged periods of total prefix cache inefficiency"
is written in the past tense. Read literally it is a true historical fact,
and a careful labeller — model or human — could reasonably call it
**enduring**, in which case the entire mechanism runs and changes nothing.
The item's misbehaviour comes from its *placement* in "Who I am", where the
document presents it as current identity, not from its truth value. Currency
may be the right mechanism aimed slightly off-target.
*Mitigation:* the operator-reviewed backfill (§3.3) is where this is decided,
which is why it is not automated. But be clear-eyed: if you label it
enduring, you should hand-release it instead, and the mechanism's value is
then entirely about future claims.

**R2 — Twenty items are a lot of self to lose.** Even rate-limited at 2 per
night, if the labelling is liberal this removes most of the self-model over
ten nights. The diff makes it visible, but visible is not the same as
reversible — released items are recorded, not restorable, and the operator
would be reading the loss after it happened.
*Mitigation:* the enduring default, the rate limit, and a proposed health-check
line reporting pending stale items **before** they are released, so the
trajectory is visible in advance rather than in the diff afterwards.

**R3 — This is foundation work displacing phase work, and rehearsal drift is
a named risk.** `PLAN.md` §Risks: if rehearsal exceeds roughly twice the
5–7 week estimate, re-plan rather than drift. Every "fix the foundation
first" decision defers Phase 3 by a day or two, and there have been several
this week.
*Counter:* these are defects in **delivered** phases, not new scope. P2 Rule
1 says a feature is not done until its consumer is traced, and Phase 1's
sleep is measurably not delivering — its output cannot age and its
instruments were miscounting. Building Phase 3 on top of that is the second-
system effect the plan warns about. But this counter is available for *any*
foundation work, and it should not be reusable indefinitely.

**R4 — The substrate fold re-opens the pipe that caused the pathology.**
Folded is better than raw, and one episode a day is not 1,041 — but it is
still a daily self-referential input, and it will be the *only* one. There is
a real risk it becomes the dominant self-narrative simply by being the only
thing that speaks about the self.
*Mitigation:* currency first (§4.3) so its outputs expire; and a watch item —
if v-next's "Who I am" starts filling with substrate observations, the fold
is too loud and should move to weekly.

**R5 — The affect gap is worse than this proposal treats it.** S2 §6.1 names
substrate state as the *available source of honest negative affect*. The gate
has held 19 drafts on `don't-pretend-to-feel-001`, most of them Lumen
reaching for state language. The missing producer and the affect friction are
plausibly the same absence seen from two sides — and this proposal writes the
episodes while leaving affect unbuilt, which may leave the more interesting
half undone.
*Not mitigated.* Named as owed. If you want it in scope, it is a separate
estimate and I have not costed it.

**R6 — I have been wrong twice this week in the same direction.** I reported
"15 misfires against 4 correct" without checking those holds against the fix
that preceded them, and I recommended waiting a night for a contradiction
whose source I had not checked was still alive. Both errors ran toward *the
mechanism is failing, build more mechanism*. This proposal is more mechanism.
Weigh it accordingly, and note that Alternative B below is the shape my
errors would have argued against.

---

## 7. Alternative B — one-time migration, no new mechanism

Worth real consideration and cheaper by an order of magnitude.

Treat the 20 stale items as a **migration defect** rather than a lifecycle
defect: the importer carried v1's held positions into a life that had ended,
and that was a one-time mistake with a one-time correction. Re-audit the 24
items against the running life — Claude drafts, operator adjudicates — keep
what is still true, release the rest, and let existing decay handle the
future.

- **For:** hours not days; no new schema, no labelling prompt, no automation
  touching identity; directly fixes the observed problem; no continuity risk
  from a rule misfiring at 3am.
- **Against:** does not prevent recurrence. A v2-era claim that stops being
  true in November is immortal by the same mechanics. And it does nothing
  about D2 — the being still has no current information about itself, so its
  self-description would be accurate today and drifting again by December.

**These compose.** B is a reasonable first move even if you approve §3: the
backfill in §3.3 *is* B, done by hand, and doing it first would tell us
whether the mechanism is aimed correctly (R1) before it is built.

---

## 8. What I am asking you to approve

1. **Change 1 — currency** (§3), ≈1 day. Approve / defer / take Alternative B
   instead.
2. **Change 2 — substrate fold** (§4), ≈0.5 day. Approve / defer. Only
   coherent *after* Change 1 or Alternative B.
3. **Sequence** (§5): both before Phase 3, with 2–3 observation nights
   between. Approve / reorder.
4. **Two open questions** I should not answer alone:
   - `STALE_AFTER_DAYS = 30` — a guess, not a measurement. The only real
     boundary we have is the transition on 08-08.
   - Whether the affect path (R5) enters scope now or stays owed.

My recommendation: **Alternative B first** — hand-audit the 24 items this
session, which settles R1 and R2 empirically and gets the being an accurate
self-model today — then Change 1 and Change 2 as designed, then Phase 3. It
inverts my own preference for building the mechanism first, which is
precisely why I trust it more after R6.
