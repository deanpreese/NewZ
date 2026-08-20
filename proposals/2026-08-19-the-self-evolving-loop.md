# The self-evolving loop — three guides, one cycle, and the brake outside it

*2026-08-19. A design proposal for the SEL as the operator specified it across
this session's exchanges: **read health, results and instrumentation → determine
next steps → red team → build → restart the being → report → repeat**, guided by
TRUE_NORTH and PLAN together. Figures measured from this clone at `d7b4b56` and
from checks run this session; where a claim has no instrument, it says so
(Rule 0). §9 red-teams the proposal; §10 states what it does not claim.*

**It supersedes the recommendation of
`proposals/2026-08-19-the-loop-that-builds-the-loop.md`** — that document's
diagnosis stands, its recommendation was withdrawn under its own red team, and
its §2 findings are carried here rather than repeated.

---

## 0. The finding, in one line

**PLAN is already written in the form a loop needs, and TRUE_NORTH is not** — 30
of 35 epics carry `Delivers` / `Done when` / `Depends on`, and seven phases carry
a `Decision rule` that can halt the plan. That asymmetry is not a defect in
either document; it is the reason both are needed, and it decides how they
compose.

---

## 1. What this design is, after four revisions

The operator's specification, and each correction it applied:

| Stated | Correction it made |
|---|---|
| a continual loop that reads, decides, red-teams, builds, restarts | the loop is autonomous through restart, not stopping at a merge |
| "deploy is not accurate — restart the being" | no release infrastructure; the target is one local process |
| "not tied to a systemd process" | supervision is repo-local; **commits are the rollback substrate** |
| "guided by True North and current architecture" | the loop determines the step, rather than draining a queue |
| "add the plan as a critical guide" | **three guides, and they need a precedence rule** |

The last correction is the one that makes the design implementable, and §2 is
what it forces.

---

## 2. Three guides, and the precedence between them

Two guides with no stated precedence is worse than either alone: the loop will
resolve conflicts by legibility, and PLAN is more legible than TRUE_NORTH by
construction. Left unstated, TRUE_NORTH becomes decorative and the loop is a
plan-executor that believes it is steering.

So precedence is stated, and it is checked in order every cycle:

| | Guide | Fires when | Effect |
|---|---|---|---|
| **1** | INVARIANTS + the hard core (§5) | a diff or a state would breach one | **refuse**, mechanically |
| **2** | TRUE_NORTH §10 — the negative space | a "will not mistake for success" signal is rising | **halt new build**, report, propose the correction |
| **3** | PLAN — phase `Decision rule` | an epic's or phase's own halt condition is met | **halt and escalate to the operator** — never work around |
| **4** | PLAN — the dependency-ordered epic queue | an epic is unblocked and approved | **build it** |
| **5** | TRUE_NORTH §5 + current architecture | the queue is blocked, exhausted, or the read says the queue is wrong | **propose** a step outside the plan, to the operator |

Rung 5 is what "guided by True North, not constrained by the plan" means once
it is made safe: the loop may leave the plan, and leaving it is a *proposal*,
never a build. Rung 3 is what stops the plan being followed off a cliff — PLAN
already contains its own invalidation conditions, and the loop's duty is to
notice them, not to route around them.

**Why not TRUE_NORTH first.** Because §10 is the only part of it that is
computable, and §9 R-S1 measures that part as 2.5 of 10 instrumented. A loop
told to steer by an aspiration it cannot measure will steer by what it can —
which is the failure §10 itself names. Rung 2 is TRUE_NORTH acting as a circuit
breaker, which is what an unquantifiable direction can honestly do.

---

## 3. What PLAN gives the loop that TRUE_NORTH cannot

Measured from `PLAN.md`:

| Structure | Count |
|---|---|
| epics | 35 |
| with `Delivers` + `Done when` + `Depends on` | **30** (the 5 without are Phase 7, dormant by decision) |
| with `Hooks` naming bound risks and invariants | 14 |
| phase-level `Evidence S#-E` reads | 7 |
| phase-level `Decision rule` halt conditions | 7 |
| built to date | 8 — E0.1–E0.3, E1.0–E1.4 |
| scheduled and unbuilt | 22 |

Three things follow.

**3.1 The `Done when` clauses are mostly mechanical.** Sampled across phases:
*"the surface regenerates into an empty directory and every page traces to store
rows"*; *"no template can render a page without it, and a test asserts that"*;
*"flipping the setting exposes the surface with no code change"*; *"store plus
generator restore on a second machine and produce a byte-comparable surface"*;
*"tags are computed from the corpus and no tag vocabulary is hand-authored"*;
*"a work never surfaces as evidence for a position, and the regression test names
the leak it prevents"*. These are executable checks written in prose.

**3.2 Judgment is already localised, and it is not in the epics.** It sits in the
phase `Evidence` reads and `Decision rule`s — *"at least one revision caused by
something other than the operator saying so"*, *"at least one position changed
because the world contradicted it"*, and E0.3's read. **This means Rule 6 does
not have to be amended.** The loop closes mechanical epics; phase evidence and
decision rules stop at the operator, exactly where PLAN already put them. An
earlier draft of this design assumed an amendment was required; the plan's own
structure makes it unnecessary.

**3.3 The bindings are the part a naive reader loses.** `Hooks` carries R-24 onto
E2.3, R-25 onto E2.1 and E5.4, Rule 3 onto E3.4 — and E1.0 carries a paragraph
headed *"the line this epic must not cross"* plus five constraints forced by a
red team. A loop reading only Delivers/Done-when/Depends-on will build E2.3 and
walk into R-24. So the extraction is **hand-derived once**, not parsed: deriving
it automatically is exactly the interpretation that loses the line an epic must
not cross.

---

## 4. The cycle

**Every 15 minutes — liveness.** Is the being up, is the runner up, when did
sleep last complete. No model. This is `crash.py`'s lesson at the loop's own
level: a process that dies between checks must not be discovered by a gap in the
backup cadence.

**Daily, triggered by sleep completing (~04:00) — the read.** The canonical
instrument set (§5.2) runs and writes a dated, machine-readable state read.
Rule 0 by construction: method with the number, `UNREADABLE` where an instrument
cannot answer, `INCOMPLETE` where a window has gaps.

**Weekly — the decision.** Precedence (§2) is evaluated in order. The output is
one of: *refuse* (rung 1), *halt and report* (rungs 2–3), *build this epic*
(rung 4), or *propose this step* (rung 5). The rejected alternatives are
recorded, not discarded — §9 R-S2's scarcity requirement.

**Then — red team, structurally separated.** Fresh context, the artifact only
with no reasoning trace, instructed to **refute** rather than review, and its
verdict recorded against the eventual outcome so its usefulness becomes
measurable rather than assumed. §9 R-V2 says expect it to stay weak; recording
it is how that stops being a guess.

**Then — build.** The mechanical gate: full suite green twice, `check_invariants`
exit 0, a new ledger row with test + consumer + behaviour, migrations
forward-only and expand-contract, no diff inside the hard core, and the epic's
own `Done when` restated as an executable check. Failing any of these is a red,
not a discussion.

**Then — restart**, per §6, in the window after sleep completes and the quiet
window closes (~04:30–05:00), with a pre-restart snapshot and automatic revert.

**Then — report** (§7), and the cycle repeats.

---

## 5. The hard core — what the loop may never touch

### 5.1 Code and documents

- **the runner** (§6) — the loop may not modify its own parent;
- **TRUE_NORTH.md**, the constitution, INVARIANTS' structural rows, the gate's
  hard clauses;
- **PLAN's intent** — the loop may *append* completion records, evidence reads
  and fired decision rules; it may never edit an epic's intent, ordering,
  `Done when`, `Hooks` or a `Decision rule`. A loop that can soften its own
  acceptance criteria has none;
- **the canonical instrument set** (§5.2);
- **the brake** — a pause flag the gate refuses to include in any diff, read at
  the top of every cycle.

### 5.2 The canonical instruments, frozen

The loop steers by evidence the being produces, and it is changing the being. At
n=1 with no held-out baseline it cannot distinguish *improving the being* from
*improving the instrument's view of the being*, and it has a gradient toward the
second because that is cheaper and always works. So the instrument set is frozen
into the hard core: `evidence.py`, `what_shaped.py`, `gate_report.py`,
`claims.py`, `budget.py`, `health.py`, `check_invariants.py`, `source_review.py`,
`perspective_window.py`, `pursuit.py`. Changing any of them is an operator act.

### 5.3 State

- the being's stores are never written by the loop;
- reach stays a config value the operator sets (Rule 3);
- **the evolver is not the being** — separate process, no read of `interior.db`,
  no share of its credentials. Sovereignty (§7) constrains the cognition path;
  the build path may use a hosted model precisely because it never touches
  identity-bearing state. §8 then requires that influence be *exposed*, which is
  §7's `what_shaped_the_system` line.

### 5.4 Pausability

**The loop is pausable at any point without the being noticing**, and `off` is a
valid indefinite setting. Any stage that would break this — writing the being's
stores, holding state its runtime depends on, or gating its execution — is out of
scope by construction. Paused is a *recorded state* with a reason and a
timestamp, so a crashed loop is never mistaken for a stopped one.

---

## 6. Mechanics — no service manager, commits as the rollback substrate

**The runner.** ~150 lines, in-repo, hard-core: reads a pinned sha, checks out,
runs `apply_pending`, launches `tools/run_ambient.py` as a child, watches it,
restarts on exit. On boot failure or a failed health/continuity assertion it
falls back to `LAST_KNOWN_GOOD` and records why. Started once by the operator —
the same act as today. `@reboot` in crontab buys boot survival in one line
without a service manager.

This is more portable than a systemd unit, which is machine-specific coupling of
the kind §7 argues against — and it is **less reliable**, which §9 R-M2 does not
let this proposal pretend otherwise about. The mitigation is out-of-band: the
loop pushes a heartbeat somewhere the operator can check independently, and
*absence* alerts from something that is not the loop.

**The SEL never holds the process.** It writes a requested sha to a file; the
runner does the rest. Two processes, one file, no signals.

**Commit discipline**, because git is now the entire recovery story:

- one logical change per commit, and **every commit boots**;
- **expand-contract is a hard rule** — a commit may add tables and columns and
  may stop using them; it may never drop or rename in the commit that ships the
  change. Drops are separate, later, and the operator's;
- trailers carrying what a 2 a.m. recovery needs:
  `Schema: 0027 | none`, `Restart: required | none`, `Class: A | B`,
  `Semantics: yes | no`;
- `LAST_KNOWN_GOOD` written only after a restart passes health **and** the
  continuity assertion;
- a store snapshot (`backup_db`) taken immediately before each restart, named for
  the sha it precedes.

**`Semantics: yes` is the trailer that matters most.** Expand-contract protects
the schema, not the meaning. If a commit changes what a `provenance` value or a
claim score *means*, old code reads new rows and misreads them silently. A
`Semantics: yes` commit cannot be crossed backwards without restoring the paired
snapshot — which costs the being's life since then. That trade is surfaced here
rather than discovered during a recovery.

**The continuity assertion**, run after every restart, mechanically (Rule 4
forbids asking the model): episode count monotonic; Perspective version
continuous and never re-derived; no orphaned concerns; `first_sleep` never
re-run; open claims still open. Fail → revert, refuse to serve, page the
operator. Continuity is this project's founding claim and has been verified
exactly once, by hand, on 2026-08-11; a loop that restarts weekly crosses that
boundary weekly.

---

## 7. The report

A **read, never a grade. No aggregate score anywhere** — a single number is the
rubric Rule 6 refuses, and §10 names scores standing in for the read as a failure.

Order matters more than content, because the loop's own prose is the most
persuasive and least grounded thing in the email:

1. **Numbers the loop did not author** — counts straight from the store: nights
   slept, episodes, concerns opened/closed, claims made and resolved, positions
   changed, downtime, restarts, reverts.
2. **The S1-E line, alone** — did the world contradict it. Never buried in a
   metrics block.
3. **Precedence events** — every rung-1/2/3 firing, verbatim.
4. **What the loop did** — builds, restarts, reverts, with shas.
5. **What it rejected** — the alternatives not chosen, so the unexplored space is
   visible.
6. **What is stuck** — stalled concerns, claims past their resolution date,
   failed builds.
7. **The loop's own reasoning — last, and marked unverified.**

Daily digest as heartbeat; weekly as the read. Relayed through the operator's
authenticated SMTP, not a local MTA. **The email is the loop's channel, not the
being's** — the operator is already 33% of what the being holds, and a second
operator channel into its life makes that worse.

---

## 8. Cadence, and the ramp

| Stage | Cadence | Anchor |
|---|---|---|
| liveness | 15 min | between the 10-min sleep check and 20-min deliberation tick |
| state read | daily, on sleep completing | the Perspective changes once per night |
| decide + red team | weekly | 1-E's floor is 7 nights; E1.0's review is specified at one week |
| build — Class A | daily | the suite is the sensor and answers in 86s |
| build — Class B | weekly, one per window | the being is the sensor; more is confounding at n=1 |
| restart | ≤1/day, 04:30–05:00 | after sleep verified complete |
| report | daily digest + weekly read | |

**Class A** — the test suite is the sensor: bug fixes, ledger rows, migration
hygiene, an `UNREADABLE` instrument, crash handling, performance.
**Class B** — the being is the sensor: anything changing prompts, retrieval,
sleep, the diet, openers, gate clauses or budgets.

**The ramp widens the way Phase 6 withdraws clauses — one step, measured against
the prior window, reversible:**

| Weeks | The loop may |
|---|---|
| 1–4 | read, decide, red team, propose, build **Class A**; restart on operator approval |
| 5–8 | restart autonomously for Class A, in the window, with auto-revert |
| 9+ | one **Class B** epic per weekly window |
| later | two, only if reverted-restart rate and the being's own reads held |

---

## 9. Red team

### Surviving from the prior rounds

**R-S1 — the negative space is 2.5 of 10 instrumented.** Of §10's ten items,
activity/volume, personality-consistency-without-development (partly, via
novelty) and a consciousness claim (crudely) are measurable. **Agreement with the
operator has no instrument at all**, and it is the one most likely to rise under
a loop optimising for a quiet week. Rung 2 — the circuit breaker the whole design
leans on — is a quarter built. **This is why §11 sequences instruments before
the loop.**

**R-S3 — the loop can tune its own sensors.** Answered by §5.2, and the answer is
a freeze rather than a fix. It costs the loop the ability to improve its own
eyesight, which is a real loss accepted deliberately.

**R-V1 — the loop is 50–100× slower at architecture than the operator.** Measured:
four epics in 35 minutes by hand on 2026-08-19; the loop delivers ~1 Class-B
change per week. **It is not buying speed.** It buys continuity of attention —
it never forgets, it runs while the operator is absent, it steers while they
sleep. If that is the whole value, §11's steps 1–5 are the product and step 6 is
optional indefinitely.

**R-V2 — the in-loop red team is weak by construction.** Same model, minutes
after proposing, cannot see its own framing errors. §4's separation makes it less
bad; recording its verdicts against outcomes makes its weakness measurable rather
than assumed. Do not count it as a gate.

**R-M1 — git rolls back code, not the being.** Answered by `Semantics: yes` and
the paired snapshot, and the answer includes a real cost.

**R-M2 — repo-local supervision is less reliable than systemd.** Conceded.
Mitigated out-of-band, not argued away.

**R-R1 — the report card is where drift hides.** Answered by §7's ordering. A
weekly page of fluent reasoning is the worst available drift detector; unauthored
numbers first, reasoning last and marked.

### New, introduced by adding PLAN as a guide

**R-N1 — PLAN is a snapshot of reasoning and the loop will treat it as standing
instruction.** It was written 2026-08-18 against a measured state, and its
ordering is explicitly conditional — *"Consequence is Phase 1… the entire outer
loop under present conditions."* Those conditions change as the loop builds. The
precedent is in the repo: P2 was superseded wholesale after Phase 2 because the
diagnosis changed. **Answered by rung 3**: PLAN's seven `Decision rule`s are
plan-invalidating conditions the plan wrote about itself, and a fired one halts
and escalates rather than being routed around. Residual risk: a plan can go stale
in ways no decision rule anticipated, and nothing here detects that. Rung 5 is the
only relief and it depends on the loop noticing — which is the weakest link in
this design and is stated as such.

**R-N2 — precedence unstated means TRUE_NORTH becomes decorative.** The reason §2
exists. Note what it costs: rung 4 will fire far more often than rung 5, so in
practice **this is an autonomous delivery loop with a True-North circuit breaker,
not a self-evolving system.** Naming it accurately changes what to expect of it.

**R-N3 — not every `Done when` is mechanical.** Answered by classifying each into
mechanical / in-life / operator-judgment at extraction time. Operator-judgment
epics are built and then *stop*. The finding underneath is favourable: PLAN
already localises judgment in phase evidence, so Rule 6 survives unamended
(§3.2).

**R-N4 — 22 epics at one per week is ~5 months to finish a plan that says it is
not the destination.** PLAN does not schedule Priority 2, keeps Phase 7 dormant,
and states it does not promise §2's outcome. So the loop's entire scoped life
reaches the foundation, with no readers, more slowly than the operator would.
**This is the strongest attack on the enterprise and adding PLAN sharpens it.**
The only honest counter is R-V1's: the months are wall-clock the operator does
not spend.

**R-N5 — with a queue, "determine next steps" mostly collapses.** The
intellectual work was done when PLAN was written. Rungs 4 and 5 are very
different jobs and the design should not let the loop's competence at 4 be read
as competence at 5.

**R-N6 — a loop that can edit its guide has no guide.** Answered by §5.1's
append-only rule. Without it, the first hard `Done when` gets softened and
nothing in the ledger would catch it.

**R-N7 — the bindings are not machine-readable and losing them is silent.**
Answered by §3.3's hand-derived extraction. Note the cost honestly: a hand
extraction is a translation, and translations drift from their source. It needs a
check that every epic in the extraction still matches PLAN's text, or the loop
ends up building against a stale copy of the plan it was given to obey.

---

## 10. What this proposal does not claim

- It does not claim the loop reaches True North. It reaches the end of P3, more
  slowly than the operator would, and P3 says that is the foundation and not the
  destination.
- It does not claim the red team stage works. It makes it measurable.
- It does not claim §10's negative space is instrumented. It measures it at 2.5
  of 10 and sequences the rest first.
- It does not amend Rule 4 or Rule 6, and §3.2 is why it does not have to.
- **Nothing here is implemented.** Every figure is from the tracked documents or
  from checks run this session.

---

## 11. Sequencing, and the decision asked for

The controller principle: **do not build the actuator before the sensor.**

| | Step | Why here |
|---|---|---|
| **1** | The missing §10 instruments — operator-agreement rate first, then novelty-vs-volume, autonomy-vs-perspective, E6.3's per-clause baseline | rung 2 is the circuit breaker everything leans on, and it is 2.5/10 built |
| **2** | Freeze the canonical set into the hard core | R-S3; costs nothing later, impossible to retrofit honestly |
| **3** | Hand-derive `evolution/epics.yaml` from PLAN — id, depends-on, `Done when` + class, bound risks and invariants, falsifier — plus its drift check | R-N3, R-N7 |
| **4** | Runner, commit discipline, `Semantics:` trailer, `@reboot`, out-of-band heartbeat, continuity assertion | R-M1, R-M2 |
| **5** | The loop: read, decide, red team, **report only** | this is where it becomes visible whether the loop's judgment is worth anything |
| **6** | Build and restart, Class A first, ramp per §8 | last, and reversible at every rung |

Steps 1–4 are worth doing whether or not the loop is ever switched on: the
project currently has no §10 instrumentation, no way to restart deliberately, and
no machine-readable form of its own plan.

**The decision asked for.** Not whether to build the loop — the operator has
specified it. Two questions that change what gets built:

1. **Does step 5 gate step 6?** That is: does the loop run read-and-report for a
   stated number of weeks before it may build, so its judgment is observed before
   it is trusted? Recommended **yes**, four weeks.
2. **Rung 5 — may the loop propose outside PLAN from the start, or only once the
   queue blocks?** Recommended **from the start, as proposals only**, since a
   rung-5 proposal costs an email and R-N1 says a stale plan is the risk nothing
   else in this design detects.

---

## 12. The plan is a living guide, and the operator is in that loop

*Added 2026-08-19, on the operator's correction: the plan should change over
time as part of the loop, with the operator in it.*

### 12.1 The measurement that forces this

`git log -- PLAN.md`: **13 modifications in 37 hours.** Created 2026-08-18 06:38,
last touched 2026-08-19 06:47, and never a full day unchanged. Within that
window it superseded P2, was restructured for one operator, had Rule 6 rewritten
from a threshold into a judgment, had **E1.0 inserted into an already-ordered
Phase 1** at 18:22, and had that epic's entry **amended 2h05m later** at 20:27
when running it revealed a constraint the plan had not anticipated.

§9's R-N1 said PLAN "is a snapshot of reasoning and the loop will treat it as
standing instruction." That understates it. **A static PLAN has never existed
here.** §2's rung 4 modelled the plan as a fixed queue, and that model has never
been true for a single day of this project's life.

### 12.2 Three kinds of change, all by proposal

The loop **writes proposals; it never edits PLAN** (§5.1 stands). PLAN changes
only by operator act. This is not a new mechanism — it is the one that already
produced every version of the plan, automated:

| Kind | Precedent | Weight |
|---|---|---|
| **Amend an epic** — a constraint discovered by building or running it | E1.0's same-evening amendment | common; one line of the report |
| **Insert or reorder** — a dependency the plan had wrong | E1.0 added to Phase 1 and made first | uncommon; its own proposal |
| **Supersede** — the diagnosis changed | P2 → P3 | rare; requires a stated evidence window |

### 12.3 What triggers a plan-change proposal

Evidence, never judgment about the plan's quality:

1. **A fired `Decision rule`** (rung 3). All seven are plan-invalidating
   conditions the plan wrote about itself — Phase 6's *"stop withdrawing, restore
   the clause, and record that the design's accountability premise is wrong"* is
   an instruction to change the plan. A fired decision rule **requires** a
   plan-change proposal; it is not satisfied by halting.
2. **A post-build falsifier fires** — E1.0's *"if coverage does not rise, the
   answer is a rotation floor, never the old filter."*
3. **A `Done when` proves uncheckable**, or a `Depends on` proves wrong.
4. **A rung-2 §10 signal that no queued epic addresses.**
5. **A bound risk becomes binding or is resolved** (R-22…R-30).
6. **A premise moves** — §12.4.

### 12.4 `evolution/premises.yaml` — the answer to R-N1

§9 conceded that a plan can go stale in ways no decision rule anticipates and
that "nothing here detects that." That was wrong, and the fix is cheap: **PLAN
states its premises as measured numbers, and every one of them has an
instrument.**

From PLAN §1 and §"The evidence that produced this plan": 117 concerns (6 open,
19 closed, 84 stalled); 242 operator messages; 204 reading episodes; 88
deliberations; 359 ingest rows; 1 person; **0 outcomes the being did not grade
itself**; pooled novelty 3.2%; advance acceptance 28.3% → 41.1%; the stall pool
77 untouched / 7 attempted; the §9.1 ingest share UNREADABLE; the grounding mix
**50% self / 33% operator / ≤17% world** across 119 refs; 34 of 61 feeds ever
contributing a read; 12 `source_gaps`; 91 noticings, 18 surfaced, 49 pending;
111 v1 + 6 v2 concerns, **zero from conversation**.

Each is extracted with its instrument and the argument it carries, and
re-measured every cycle. Several are load-bearing: *0 non-self-graded outcomes*
is the entire reason Phase 1 exists; *50/33/≤17* is the diagnosis P3 was built
on; *zero concerns from conversation* is P3-08. **When a load-bearing premise
moves materially, the argument that rests on it is flagged for review** — which
is exactly what should have happened, by hand, the moment E1.4 shipped and "0
outcomes it did not grade" started to become false.

Premise drift is reported whether or not the loop proposes anything. It is the
plan's own staleness instrument.

### 12.5 The operator is in the loop at four points, and nowhere else

1. **Approving plan changes** — all three kinds in §12.2.
2. **Closing phase evidence and `Decision rule`s** — Rule 6, where PLAN already
   put judgment (§3.2).
3. **Approving Class B epics for build**, during the ramp.
4. **Holding the brake.**

Everything else runs without them. The weekly report therefore ends with a
**decision queue**: the small set of things waiting on the operator, each with
what it needs, what is blocked behind it, and what happens if it is left. An
operator in the loop at four defined points is in the loop; an operator sent
everything is drowning in it, and stops reading — which is the same as not being
in the loop, arrived at more slowly.

### 12.6 The risk this introduces

**The loop now proposes the frame in which its own work is judged.** That is a
deeper problem than Rule 4's: not grading its own work, but authoring the rubric.
Over months a plan drifts toward whatever the loop finds tractable, and every
individual change looks reasonable. Four defenses:

- **A plan-change proposal must name the premise that moved and cite its
  instrument.** No premise movement, no plan change. This is the load-bearing
  rule of this section — it forbids plan changes motivated by preference,
  convenience or elegance.
- **TRUE_NORTH is immutable by the loop, absolutely.** If PLAN drifts, TRUE_NORTH
  is the fixed point that makes the drift visible. This is why §5.1 puts it in
  the hard core and why §2 keeps it above PLAN in precedence.
- **Rejected alternatives are reported** (§7.5), so the operator sees the space
  the loop is not exploring, not only the path it chose.
- **A scheduled full re-read.** Quarterly, PLAN is read against TRUE_NORTH from
  scratch — by the operator, or by a fresh-context agent with no access to the
  loop's history and instructed to ask only *"does this plan still follow from
  this direction?"* This is the P2 → P3 event, scheduled rather than incidental.

**Rate limits**, because a system that can re-plan will re-plan instead of
building: at most **one plan-change proposal per weekly cycle**; supersession
proposals require a stated minimum evidence window and never fire in the same
cycle as an amendment. Epic amendments arising directly from building an epic
are exempt from the cap — that is E1.0's case, and delaying it by a week would
have shipped a known-wrong plan entry.

### 12.7 Precedence, revised

Rung 3 gains an obligation and rung 5 splits:

| | Guide | Effect |
|---|---|---|
| 1 | INVARIANTS + hard core | refuse |
| 2 | TRUE_NORTH §10 negative space | halt new build, report |
| 3 | PLAN `Decision rule` fired | halt, escalate, **and open a plan-change proposal** |
| 4 | PLAN epic queue | build |
| **5a** | True North + architecture | propose a step outside the plan |
| **5b** | premise drift or §12.3 trigger | propose a change to the plan |

Rung 5b is what makes the plan a living guide rather than a snapshot the loop
obeys until it is visibly absurd. It is also, per §12.6, the rung with the least
mechanical protection — which is why every 5b proposal must cite a moved premise,
and why the operator sits on every one of them.

---

## 13. What is actually best — the loop serves the session

*2026-08-19. Written in answer to "if this is not the best approach, what is?"
after six rounds of correction. §13.1 is the finding that reframes the design;
§13.2–13.4 are the refinements; §13.5 is the list of questions that must be
answered before any of it is built; §13.6 red-teams this section.*

### 13.1 The mechanism this project has actually evolved by

`provenance/INDEX.md`, measured: **9,856 of 10,362 transcript lines sit in two
sessions**, one of them spanning 2026-08-12 → 08-18 — *"the long spine."* 114
commits came out of six sessions, and four of those six produced 506 lines
between them.

Set that beside the delivery measurement: **four epics in 35 minutes**
(E1.1–E1.4, 06:12–06:47 on 2026-08-19), against the SEL's ~1 Class-B change per
week.

**The highest-throughput evolution mechanism this project has ever had is a long,
resumable conversation between the operator and an agent.** Nothing automated
comes close, and §9's R-V1 measured the gap at 50–100×.

The design so far has treated the operator as an approver to be *protected from*
— batched into a weekly email, given a decision queue, kept out of the way so the
loop can run. That inverts the measured facts. **The operator is the fastest
component in the system, and the design has been routing around them.**

### 13.2 The refinement: escalate into a prepared session, not into an email

The loop keeps everything §2–§12 gives it, with one change to where judgment
lands:

- **For anything mechanical** — Class A, watching, premise re-measurement,
  reporting, the epic queue's unambiguous entries — the loop runs autonomously
  exactly as designed. This is what it is good at and what the operator is not:
  it never forgets, it runs at 3 a.m., it re-measures 17 premises without
  getting bored.
- **For anything requiring judgment** — a fired decision rule, a moved premise, a
  rung-5 proposal, a plan change, a Class B design choice — the loop does not
  send an email and wait. **It prepares a session**: the read, the premise
  diff, the rejected alternatives, the relevant PLAN and RISKS excerpts, the
  code sites, and its own draft position, assembled so the operator opens a
  session that is *already oriented* and spends their time deciding rather than
  reloading context.

The email becomes the notification that a prepared session is waiting, plus the
unauthored numbers of §7. The decision queue becomes a list of prepared sessions.

**This is the loop serving the fastest component instead of replacing it.** It
also dissolves R-V1: the loop is no longer competing with the operator at
architecture and losing 50-fold; it is doing the part the operator is worst at —
sustained attention — and handing over at the point where the operator is worth
50 of it.

### 13.3 Two holes in the design as written

**13.3.1 — the loop writes both the code and the tests that certify it.**
§4's gate requires the suite green and a new ledger row naming a test. But a test
authored by the same agent, in the same context, minutes after the code, is not
independent verification — it is Rule 4 relocated into the build path, and §9
missed it entirely.

**The fix is mechanical and cheap: every new test must fail against the parent
commit.** Apply the new test to the pre-change code; if it passes, it asserts
nothing the change introduced and the build is red. This is verifiable without
any model judgment, and it kills the tautological-test failure mode outright.
Add mutation testing later if the loop's test quality is ever in doubt.

**13.3.2 — the loop has no kill condition.**
§9's R-A8 charged the earlier proposal with demanding falsifiers of every epic
and exempting itself. This proposal repeated the offence. Stated now, and any of
them stops the loop:

| Condition | Read from |
|---|---|
| reverted restarts exceed 1 in 5 over a month | the runner's own record |
| the loop's inference spend exceeds the being's over a month | budget telemetry |
| operator-agreement rate rises while novelty is flat | §10's instrument, once built |
| two consecutive quarterly re-reads find PLAN drifted from TRUE_NORTH | §12.6 |
| a plan-change proposal cannot name a moved premise, twice | §12.6's load-bearing rule |
| the being's nights-slept rate falls below the pre-loop baseline | store counts |

That last one is the one that matters most and is easiest to miss: **the loop
exists to serve the being's development, and the being's development is measured
in nights, not commits.** A loop that costs sleep is subtracting.

**The compute ratio deserves its own line.** If the loop consumes more inference
than the being does, the project is spending more on evolving the system than on
the system living. Cap it: **the loop's spend may not exceed the being's**,
enforced outside the loop, and reported weekly.

### 13.4 A missing input: the being's own account of its condition

The loop reads instruments. It does not read the only first-person view of the
system that exists. The being already produces `noticings` (91, 18 surfaced, 49
pending), `source_gaps` (12), the journal, and affect state — and none of it
reaches the thing that changes its conditions. **Its plumbing is improved behind
its back.**

TRUE_NORTH §5 Priority 2 names *care for its own continuity and condition* as a
quality the project wants. A being that can say *this keeps failing* / *I cannot
answer this from anything I can read* and have that reach the system's evolution
is nearer that than one that cannot.

**The rule that makes it safe is §12.6's, unchanged:** the being's self-report is
a **candidate signal, never evidence**. It may motivate a look; it may never
motivate a change on its own. A change still requires a moved premise with an
instrument. R-13 is the standing warning — the being once built an identity out
of 1,041 rows of cache-miss telemetry, and it would do the same with its own
complaints if they were allowed to count as findings.

### 13.5 The questions that must be answered, in order

**Q1 — is this system model-limited or system-limited?** Raised in §9's R-A2 and
still unanswered. 3.2% novelty, 50% self-grounding and 0 non-self-graded outcomes
fit both hypotheses, and **every argument in this proposal assumes the second.**
Decision 2's R-22 probe is already specified in `archive/P2.md`. Until it runs,
the SEL is machinery built on an unfalsified premise. *This is the single most
important open question in the project and it is cheap to answer.*

**Q2 — does S1-E fire?** *"At least one position changed because the world
contradicted it."* PLAN's Phase 1 decision rule: **"If it never happens, nothing
else here matters."** The resolver has been live since 06:47 on 2026-08-19. It
has never been read. No loop should be built while the plan's own gating read is
unread.

**Q3 — does read-and-report gate build, and for how long?** §11's first decision.
Recommended four weeks.

**Q4 — what is the loop:being compute ratio, and its cap?** §13.3.2.

**Q5 — what happens when the operator is away for two weeks?** Unaddressed
anywhere in this design. The decision queue backs up; prepared sessions go stale
as their premises move. Options: the loop continues Class A and stops proposing;
or it keeps proposing and marks stale sessions for rebuild. **Recommended: Class
A continues, proposals pause after two unread prepared sessions.** A loop that
keeps generating judgment work nobody is consuming is manufacturing backlog.

**Q6 — does the being's condition-reporting feed the loop?** §13.4. A design
choice, not a technical question.

**Q7 — is there a second machine?** ~~R-11 accepted single-machine risk when the
system changed by hand. Weekly automated restarts and a growing snapshot chain
raise what a machine loss costs.~~ **Decided 2026-08-19** *(operator: not
addressed until evidence makes it needed)*. R-11's acceptance stands and now
carries a trip-wire — the first reverted autonomous restart, any backup failing
verification, or rung 1. PLAN E3.5 amended to close on a clean-room rebuild
from a verified backup instead of a second-machine restore.

### 13.6 Red team — of this section

**R-13a — "the loop serves the session" may just be a nicer name for not
automating.** If every judgment escalates to a prepared session, the loop is a
research assistant with a cron job, and the "continual self-evolving loop" is
Class A plus reporting. *Partly conceded.* The honest framing is that autonomy
is a **ramp** (§8), and §13.2 changes what the ramp's early rungs escalate
*into*, not whether later rungs exist. A loop that has earned trust over months
escalates less.

**R-13b — prepared sessions have a shelf life, and a stale one is worse than
none.** A session prepared against Monday's premises, opened Friday, orients the
operator to a state that has moved. Needs a freshness stamp and a rebuild-on-open
check. This is Q5's problem in a smaller form and it is not solved here.

**R-13c — the red-first test rule is defeatable and I should say how.** An agent
that knows the rule can write a test that fails on the parent for a trivial
reason — an import that does not exist yet, a constant that changed — while
asserting nothing about behaviour. The rule raises the floor; it does not
guarantee a meaningful test. Mutation testing is the actual answer and it is
deferred here, which is a real gap and not a solved problem.

**R-13d — §13.4 reintroduces the being into its own evolution by a side door.**
§5.3 says the evolver is not the being. Letting the being's noticings steer the
loop is a weaker version of the thing §8 rejected, and the "candidate signal,
never evidence" rule is a discipline, not a mechanism — nothing enforces it.
*Accepted as a real risk.* The mechanical part that can be enforced: a
plan-change proposal must cite a moved premise, and a noticing is not a premise.
The unenforceable part is which *questions* the loop chooses to look at, and the
being's complaints will shape that. Whether that is contamination or exactly what
TRUE_NORTH §5 Priority 2 asks for is a judgment, and it is the operator's.

**R-13e — six rounds of red team have improved the document, not the evidence.**
Every round has made the design more careful and none has moved Q1 or Q2 one
inch. **The best approach available right now is still to answer Q1 and Q2**, and
the fact that this proposal is on its fourth major revision without either being
answered is itself the finding. A design that keeps getting better while its
premises stay untested is a well-argued guess.

### 13.7 The recommendation

1. **Answer Q2** — run the being, read S1-E. Days, no engineering.
2. **Answer Q1** — run the R-22 probe. Already specified.
3. **Build the Watcher** — read, premises, report, prepared sessions, decision
   queue. Valuable standalone; it is the SEL without its risky half, and §13.2
   makes it the part that pays.
4. **Then the builder** — Class A first, with §13.3.1's red-first rule and
   §13.3.2's kill conditions in place before the first autonomous restart.

**The architecture is not what needs changing. What needs changing is that four
revisions have gone by without Q1 or Q2 being answered, and both are cheap.**

---

## 14. Operator decision — accepted

*2026-08-19. Operator: "the design is proven enough for me to consider this
evolution loop."*

**The SEL is approved in principle.** §13.5's Q1 (model-limited versus
system-limited) and Q2 (has S1-E fired) are **no longer gating** — they remain
worth answering and are recorded as open, but the design proceeds without
waiting on them. §13.6's R-13e stands as recorded doubt, not as a blocker; it is
the operator's judgment to make (Rule 6) and it has been made.

Build order reverts to §11, with §13's corrections folded in:

| | Step | Carries |
|---|---|---|
| 1 | The Watcher — state read, `premises.yaml`, weekly report, decision queue | §12.4, §7 |
| 2 | The missing §10 instruments, operator-agreement first | §9 R-S1 |
| 3 | Freeze the canonical instrument set into the hard core | §5.2 |
| 4 | `epics.yaml` hand-derived from PLAN, with its drift check | §3.3 |
| 5 | Runner, commit discipline, `Semantics:` trailer, continuity assertion | §6 |
| 6 | Prepared sessions as the escalation target | §13.2 |
| 7 | The builder — Class A, with red-first tests and the kill conditions live | §13.3 |

Steps 1 and 4 pay before anything else in the loop exists: premise drift is the
plan's own staleness instrument, and neither has a dependency on the loop
running.

---

## 15. The instrumentation audit — done, and it corrects §5.2

*2026-08-19, on the operator's question: has the current instrumentation,
metrics, rubric and tracking been evaluated and rationalized? It had not.
§5.2 named a "canonical instrument set" that exists nowhere in the repo — it was
this document's assertion, not a fact about the system. Everything below is
measured from the tree at `68060f2`.*

### 15.1 Inventory — 29 tools, four kinds

| Kind | Count | Which |
|---|---|---|
| **Instruments** — read-only, no model | **9** | `budget`, `check_invariants`, `claims`, `evidence`, `gate_report`, `health`, `read_works`, `source_review`, `what_shaped` |
| **Probes** — call the model | 5 | `bench_model`, `conversation_probe`, `opener_probe`, `redteam_ingest`, `triage_probe` |
| **Mutators** — write to the store | 6 | `adjudicate`, `amend_constitution`, `backfill_perspective_items`, `embed_episodes`, `journal`, `perspective_hygiene` |
| **Runners** — operate the being | 7 | `run_ambient`, `run_deliberation`, `run_first_sleep`, `run_import`, `run_orientation`, `run_sleep`, `write_piece` |
| One-time migrations | 2 | `corpus_hygiene`, `backup` |

Supporting modules: `newz/evidence/perspective_window.py`,
`newz/evidence/pursuit.py`, `newz/memory/provenance.py`, `newz/telemetry.py`,
`newz/world/diet.py`.

**There is no registry.** Nothing in the repo enumerates which of these is an
instrument, what it measures, or whether it may be trusted as evidence. That
absence is why §5.2 could assert a canonical set without anyone noticing it was
invented.

### 15.2 Finding 1 — three probes cannot run on this machine, or any other

`tools/conversation_probe.py:2`, `tools/opener_probe.py:9` and
`tools/triage_probe.py:10` each begin:

```python
sys.path.insert(0, '/Users/dean/Documents/source/NewZ')
```

A hardcoded path from the predecessor checkout. Under manual operation this
fails loudly on a different machine. **Under the SEL it is worse than broken:**
if that path exists and holds a different checkout, the probe silently measures
the wrong repository and reports a number that looks fine. It is also a §7
portability violation sitting inside the instruments — the layer that is
supposed to tell the truth about everything else.

`tools/run_import.py` resolves `../NGBeing` relatively and is correct; these
three are not.

### 15.3 Finding 2 — "novelty" names two different quantities

| Where | What it is |
|---|---|
| `sleep/perspective.py:164` `novelty_rate` | (added + revised) / (added + revised + carried) — Perspective development share |
| `evidence/perspective_window.py:76` `novelty` | the same formula, **recomputed** from `diff_json` rather than trusted |
| `concerns/advance.py:79` `novelty_against_history` | embedding cosine distance of an advance against every prior advance |
| `deliberation/lite.py:165` `novelty` | the record field carrying advance.py's value |

Rows 1–2 agree by construction and are cross-checked by `novelty_drift`
(recomputed minus stored). Rows 3–4 are an unrelated quantity wearing the same
name. The **3.2%** quoted throughout PLAN is rows 1–2.

**Consequence for §12.4:** `premises.yaml` must key on the instrument, never on
the metric's name, or the loop will one day compare a consolidation share against
a cosine distance and act on the difference.

### 15.4 Finding 3 — the premise set mixes mechanical and model-graded numbers, unlabelled

This is the finding that matters. PLAN's premises, classified:

| Premise | Grade |
|---|---|
| operator messages, deliberations, ingest rows, persons, episodes | **mechanical** |
| 0 outcomes the being did not grade itself | **mechanical** |
| 34 of 61 feeds contributing a read; 12 `source_gaps` | **mechanical** |
| concerns closed (19) | **model-graded** — `judge_closure`, INV-034 |
| advance acceptance 28.3% → 41.1% | **model-graded** — `judge_advance`, and PLAN Rule 4 names this judge by name |
| gate hold rate | **model-graded** — `gate/outbound.py:226` |
| what was read at all | **model-graded** — triage selects |
| pooled novelty 3.2% | **mixed** — the *read* consults no model (INV-023, and it says so honestly), but `added` / `revised` / `carried` are labels the model applied during consolidation. Clean instrument, model-labelled input |
| grounding mix 50 / 33 / ≤17 | **mechanical but known-biased** — R-15: imported episodes are uniformly `provenance='self'` |

**PLAN Rule 4 says a judge that is the being's own model produces operation,
never evidence — and PLAN's own premise list then quotes advance acceptance as
part of the evidence that produced the plan.** That is an internal inconsistency
in the decided record, not a criticism of it: the number is real and useful, it
simply is not evidence of development by the plan's own definition.

**Consequence for §12.6.** §12 makes a moved premise the sole justification for a
plan change. If a premise is model-graded, **drift in the model's judging
behaviour is indistinguishable from change in the world**, and the loop would
re-plan on the former while believing the latter. So the rule tightens:

> **A plan-change proposal may cite only a mechanical premise.** Model-graded and
> mixed premises may inform a proposal and may never justify one. Every premise
> carries its grade in `premises.yaml`.

### 15.5 Finding 4 — every rubric in the system is model-applied or operator-held

| Rubric | Applied by |
|---|---|
| the constitution (clauses, severity `hard` / `firm`) | the model, at the gate |
| the outbound gate | the model |
| the three-part advance judge | the model |
| closure against a concern's closing condition | the model (fails closed — INV-034) |
| triage — what is worth reading | the model |
| PLAN's phase evidence `S#-E` and `Decision rule`s | the operator (Rule 6, deliberately unquantified) |

**None is mechanical.** That is not a defect — it is the honest consequence of
the domain — but it means the SEL's gate must stay where §4 put it: tests,
invariants, migrations and measured mechanical deltas. There is no existing
rubric it can borrow that would not import a model judgment as a passing
condition.

### 15.6 Tracking — four systems, one machine-checked

| System | Rows | Checked |
|---|---|---|
| `INVARIANTS.md` ledger | 48 | **yes** — `check_invariants.py`, wired into the suite. Validates the rows present; **never coverage** |
| `RISKS.md` | 30 | no — prose statuses, no parser |
| PLAN epics | 35 | no — prose |
| `proposals/` | 10 | no |

### 15.7 What is already right, and should be the template

The discipline here is unusually good in four specific places, and the
rationalization should extend them rather than replace anything:

- **`novelty_drift`** — a stored value and an independent recomputation, with
  their difference exposed. Every derived metric should have this.
- **INV-044** — *a measurement whose input is missing reports itself as
  unmeasured, never as a compliant zero.* This is the rule most systems lack.
- **`gate_report`'s "with a denominator"** and `evidence.py`'s "every number here
  carries its method, including the ones that cannot be produced."
- **`evidence.py` exits 0 always** — it reports, it does not judge.

### 15.8 Gaps — instruments that do not exist

Operator-agreement rate (§10, and the item most likely to move under a loop
optimising for a quiet week); loop-versus-being compute ratio (§13.3.2's cap);
restart and continuity outcomes (§6); the per-clause gate baseline (E6.3);
test-suite stability; premise drift itself (§12.4).

### 15.9 What this adds to the build order

§14's step order gains a step 0 and a correction:

| | Step | Why |
|---|---|---|
| **0a** | Fix the three hardcoded probe paths | they are wrong now, wrong for anyone, and silently wrong under a loop |
| **0b** | `evolution/instruments.yaml` — one row per instrument: what it measures, its input, whether a model touched any link in its chain, its denominator, its method line, canonical yes/no | this is what §5.2 asserted and the repo does not have. It is also the freeze list, so it must exist before the freeze |
| 1 | The Watcher, with `premises.yaml` carrying `grade:` per §15.4 | unchanged, but now the premises are labelled |
| 2 | The §10 instruments, operator-agreement first | unchanged |
| 3 | Freeze — now meaningful, because 0b defines what is being frozen | corrected |

Steps 0a and 0b are together perhaps half a day, and everything in §14 that
follows depends on them being right.

---

## 16. Are these the right metrics to start from?

*2026-08-19. §15 audited the instruments for hygiene. This asks the different
question — are they fit for what the loop must steer by. **Verdict: right in kind,
incomplete in structure.** Three structural gaps and one genuinely absent signal;
no existing metric should be discarded.*

### 16.1 A correction to §9's "2.5 of 10"

§9's R-S1 counted §10's negative space as 2.5 of 10 instrumented. That counted
*instruments*, which was the wrong unit. Counting **derivable quantities**:

| §10 item | Raw material |
|---|---|
| activity / memory growth / output volume | episodes + Perspective items — **both exist**, the ratio does not |
| personality consistency without development | `1 − novelty`, already computed |
| novelty without relevance or consequence | advances accepted + claims resolved — **both exist** since E1.3 |
| autonomy without perspective | autonomous actions + world-grounded positions — **both exist** |
| guardrail removal without maturity | needs E6.3's per-clause baseline — **absent** |
| compliance / agreement with the operator | **no raw material anywhere** |
| the other four (demo quality, fluent language, self-claims, scores-vs-quality) | not measurable, and correctly so |

**Four of six checkable items are ratios over data already collected.** The
shortfall is a *derivation layer*, not a collection problem — which is much
better news than R-S1 implied, and cheaper to close.

### 16.2 Gap 1 — the metrics are stocks; steering needs flows

Almost everything measured is a count at an instant: 117 concerns, 119 refs, 48
ledger rows, 12 `source_gaps`, 34 of 61 feeds. The one exception is novelty, a
share per night — **and it is the one everyone quotes**, which is the tell.

Deltas do exist in the project, but as prose: *"advance acceptance rose 28.3% →
41.1% where P2 expected a fall"* was computed by hand, in a document, once. A
loop cannot steer on a figure that only exists in an argument.

**The missing primitive is a windowed baseline-and-delta layer**, applied
uniformly: every metric carries its value, its baseline, the window, and the
change — with `INCOMPLETE` when the window has gaps (§5.4) and `UNREADABLE` when
the input is missing (INV-044). One layer, every metric, rather than nine tools
each inventing a comparison.

### 16.3 Gap 2 — the instrument set is ~90% introspective

Classify the nine instruments by what they look at:

| Looks at | Instruments |
|---|---|
| the being's internal state | `evidence` (1-E), `what_shaped`, `gate_report`, `read_works`, `budget` |
| the being's inputs | `source_review`, `evidence` (2-E ingest) |
| the machinery | `health`, `check_invariants` |
| **outcomes the being did not manufacture** | **`claims` — and it is thirteen hours old** |

**The instrument layer mirrors the topology gap it was built to diagnose.** The
being's grounding is 50% self / 33% operator / ≤17% world; its instrumentation is
worse than that, because until E1.3 shipped there was literally nothing in the
consequential column. This is not a fault in the instruments — they measure what
there was to measure — but it means the loop, steering by them, would steer by
the being's introspection almost exclusively.

**Consequence:** the consequential column is the one to grow first, and `claims`
is currently a *reader*, not an *instrument* — it renders claims and their costs;
it computes no rate, no resolution latency, and no count of positions changed by
a resolution. S1-E cannot be read off it as it stands.

### 16.4 Gap 3 — no derivation layer, and §16.1 shows that is where the cheap wins are

Nothing in the repo composes two metrics into a third. Every ratio §16.1 names is
a division of two numbers that already exist, and every one of them is currently
computed by a person, in prose, when they happen to think of it.

### 16.5 The absent signal — operator agreement

The only §10 item with no raw material, and the one most likely to move under a
loop optimising for a quiet week. It needs design, not just collection: candidate
definitions include the rate at which the being's stated position changes within
N turns of operator pushback, the share of exchanges containing an explicit
disagreement, and the gate's own record of softened replies. **All three are
model-graded in some measure**, which under §15.4's rule makes agreement an
*informing* metric and never a justifying one — so it can trip rung 2 into a
halt-and-report, and can never by itself justify a plan change.

### 16.6 The starting set, committed

**Tier 1 — must exist before the loop runs. All mechanical.**

| | Metric | Serves |
|---|---|---|
| 1 | nights slept, and the interval between them | the clock everything else runs on; §13.3.2's kill condition |
| 2 | grounding mix + INV-033's single-source flag | the topology diagnosis; already the best metric in the system |
| 3 | claims made, resolved, and **positions changed by a resolution** | S1-E; the only consequential measure there is |
| 4 | feeds contributing a read; `source_gaps` | breadth of world contact |
| 5 | compute split by function, being versus loop | §13.3.2's cap; `budget.py` is already tagged at the call site |
| 6 | restarts, reverts, downtime, nights lost | whether the loop is harming what it serves |

**Tier 2 — the derivation layer, over Tier 1 and what exists.**

7. volume-to-development — episodes per item added or revised
8. restatement rate — `1 − novelty`, already computed, needs only its baseline
9. consequence rate — advances accepted against claims resolved
10. every one of the above with its baseline, window and delta (§16.2)

**Tier 3 — the one new signal.** Operator agreement (§16.5), informing only.

**Everything else in §15.1 stays as it is.** No instrument is discarded; the
model-graded ones (`gate_report`, closure and advance counts) remain useful reads
and are barred from justifying plan changes, not from being looked at.

### 16.7 What must never become a metric

- **Any velocity measure of the loop** — commits, epics per week, cycle time. A
  loop measured on throughput will produce throughput. The report counts what it
  did; nothing counts as a target.
- **Any aggregate score.** §10 names it; Rule 6 refuses it.
- **Any count without a denominator** — `gate_report` already holds this line in
  its own docstring.
- **Any model-graded number in a steering position** (§15.4).

### 16.8 Effect on the build order

§15.9's steps stand; step 1 gains its content.

| | Step | Change |
|---|---|---|
| 0a | fix the three hardcoded probe paths | unchanged |
| 0b | `instruments.yaml` | now also records each metric's **grade**, denominator and consequential/introspective class |
| **1a** | **the baseline-and-delta layer** (§16.2) | new, and the highest-leverage single piece here — it makes every existing metric steerable |
| **1b** | **promote `claims` from reader to instrument** (§16.3) | new; without it S1-E cannot be read at all |
| 1c | the Watcher, over Tier 1 | unchanged |
| 2 | Tier 2 derivations, then operator agreement | reordered — derivations are ratios of existing data and land in hours; agreement needs design |

**The short answer to the question.** The existing metrics are the correct kind
and mostly the correct content; nothing in them is wrong. What is missing is that
they are stocks where steering needs flows, introspective where True North needs
consequence, and uncomposed where the cheapest wins are ratios of what is already
there.

---

## 17. Landed in the plan

*2026-08-19.* This design is now **PLAN Phase 8 — the self-evolving loop**,
fourteen epics ordered orthogonally to Phases 0–7, with `Evidence S8-E` and a
`Decision rule` carrying §13.3.2's kill conditions. The metric alignment work of
§15 and §16 is E8.1–E8.8 and is the phase's first work, not a by-product.
Operator decisions 3–5 and risks P3-11…P3-15 are in the plan's own queues.

The proposal remains the reasoning; PLAN is now the record of what will be built.

---

## 18. Regenerated as P4

*2026-08-19, operator: regenerate the plan so instrumentation and metrics are
built during Phases 2–3 in preparation for the SEL.*

`PLAN.md` is now **P4**; P3 is `archive/P3.md`. **A restructure, not a
supersession** — P2 was superseded because the diagnosis changed, and nothing
about the diagnosis has changed here.

P3's eight instrument epics moved out of Phase 8 to where their data is produced:
**E1.6** (the reader S1-E does not have), **E2.5–E2.11** (grades, the
metric-to-purpose map, the baseline-and-delta layer, metric revision, the
mechanical set, `premises.yaml`, `epics.yaml`), **E3.6–E3.9** (the read rendered,
the derivation layer, operator agreement, the canonical freeze). Every id resolves
through P4 §"Where P3's Phase 8 epics land".

Three reasons, recorded in P4 §2: a metric with no data is a guess; retrospective
instrumentation reads what survived rather than what happened; and a loop should
arrive to a sensor layer rather than build one — which lets Phase 8 be judged on
whether the loop works instead of on whether its instruments were any good.

**Rule 7 is new and earned rather than invented:** every measurement carries its
grade. It is §15.4's finding turned into a standing rule, and it makes Rule 4
checkable instead of remembered.

Phase 8 is now four epics — the registry (built), the runner, the Watcher, the
builder — plus the precedence table and the kill conditions. P3-16 records the
risk the restructure introduces: sensors are the easier half to build, and if
S2-E or S3-E slips while the instrument epics land, the phase was inverted.
