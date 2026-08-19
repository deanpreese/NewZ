# The loop that builds the loop — automating how the system evolves

*2026-08-19. A design proposal about the **build** path rather than the being,
written against TRUE_NORTH and P3. Every figure is measured from this clone at
`168206c`, from the tracked documents, or from three checks run this session;
where a claim has no instrument, it says so (Rule 0). §7 red-teams the proposal
against itself; §9 states what it does not claim.*

*On "previous conversations": the raw Claude Code transcripts are untracked by
design and are **not present in this clone** (`provenance/newz-sessions/` is
absent; `.gitignore` and `provenance/INDEX.md` say why). What is read here is
what INDEX.md names as the decided record — the nine proposals, the constitution
v3–v6, INVARIANTS, RISKS, REVIEW, PLAN and the commit messages. Any claim below
that would need the transcripts to settle is marked UNREADABLE rather than
guessed.*

---

## 0. The finding, in one line

**The being's life is automated and its development is not.** Every rhythm
inside the being runs on a scheduler; every change *to* the being runs through
one person opening one session — so the project's rate of evolution is set by
operator attention, which is the one input True North cannot buy more of.

---

## 1. Reading the premise

*Within the model is not the system constraint.* The repo already holds this
position and already doubts it in the right place:

- **Resolved and still binding** (PLAN §Decisions): "the model is a tool, not
  the system"; no hosted inference anywhere in the cognition path.
- **R-12** keeps it honest: ~20KB of identity context shapes each generation and
  the rest is the model — *"'the model is a tool, not the system' is only true
  if measured."*
- **PLAN §What this plan does not do** keeps the opposite case live: *"It does
  not claim depth comes from architecture. With a fixed model, the opposite case
  is live."*

The measured state settles which reading applies to *this* system today. Pooled
Perspective novelty **3.2%** over eight nights, five of which added nothing; the
grounding mix **50% self / 33% operator / ≤17% the whole world** across 119
refs; **0** outcomes the being did not manufacture or grade. Those are topology
numbers, not capability numbers. The 2026-08-18 proposal said it plainly: *"This
is not a capability gap. It is a topology gap. More thinking inside a closed loop
yields more elaborate self-reference."*

So the premise holds here, and it has a second edge the project has not yet
picked up. If the lever is the system rather than the model, then **the rate at
which the system can be changed is the project's real throughput constraint** —
and that rate is currently one human, one session at a time.

---

## 2. The diagnosis, measured

There are three loops in this project. Only one of them is automated.

| Loop | What it turns over | Automated today |
|---|---|---|
| **A — operation** (the being's day) | reading, deliberation, sleep, resolution, backup | **Yes**, fully |
| **B — delivery** (a decided epic → shipped code) | branch, build, test, ledger, merge | **No**, 0% |
| **C — direction** (what to build, what to amend) | proposals, PLAN, constitution, readiness | **No**, and correctly so (Rule 6) |

**Loop A is real machinery**, not aspiration: `SleepScheduler`
(`newz/sleep/nightly.py:179`), `DeliberationScheduler`
(`newz/deliberation/lite.py:653`), `BackupScheduler` (`newz/store/backup.py:161`),
`SubstrateScheduler` (`newz/world/substrate.py:208`), the `AmbientLoop` drainer,
and the resolver pass that runs inside deliberation. The being wakes, reads,
thinks, sleeps and is backed up whether or not anyone is watching.

**Loop B has produced everything and is entirely hand-driven.** 16,118 lines of
Python across `newz/` and `tools/`, 517 tests, 26 forward migrations, 48 ledger
rows, 9 proposals (this is the tenth), and 8 of P3's 35 epics — E0.1–E0.3 and E1.0–E1.4, the last
five all dated 2026-08-19. 22 epics are scheduled and unbuilt; 5 more are
dormant by decision (Phase 7). `provenance/INDEX.md` records how the work
actually happened: 114 commits over ten days across six sessions, with 9,856 of
10,362 transcript lines in **two** of them. The system's evolution is
single-threaded through one long conversation.

### 2.1 The gate Loop B would need already exists, and nothing runs it

This is the part that matters, because it means the recommendation below is
mostly wiring rather than construction.

- `tools/check_invariants.py` runs clean today: **48 rows clean**, exit 0. It
  already mechanizes Rules 1 and 2 for the rows it has — `enforced` and
  `consumer_traced` rows must name a test that exists, `consumer_traced` rows
  must also name a real consumer site and a behaviour, `deferred` rows must name
  the stage that delivers them, `dormant` rows must say why they are unscheduled.
- It is wired into the suite as
  `tests/test_invariants_ledger.py::test_invariant_ledger_is_clean`, so it runs
  whenever the suite runs.
- **There is no `.github/` directory, no CI configuration of any kind, and no
  runner anywhere in the repo.** PLAN §1 describes "the invariant ledger (44
  rows) and its CI parser". The parser is real; the CI is not. (The count is also
  stale — 48 rows now.)

### 2.2 Three things measured this session, on a clean container

**(a) The suite is not green-stable.** Three consecutive full runs:
`517 passed` / `1 failed, 516 passed` / `1 failed, 516 passed`, ~86s each. The
failure is always the same test —
`tests/test_reply_queue.py::test_drainer_survives_a_transient_store_error` — and
run in isolation it fails **6 of 6**. It is not a product fault: the test waits
for the drainer by counting **500 `await asyncio.sleep(0)` yields** rather than
waiting on a condition, so whether it passes depends on how many event-loop
turns the compose path happens to take. The fix is small — wait on
`channel.sent` with a real timeout instead of a fixed yield count.

It is worth being precise about why this matters more than one flaky test
usually would: **an automatic gate is only as useful as it is trusted**, and a
gate that goes red twice in three runs teaches its operator to ignore it. Worse,
an automated builder that runs a *subset* for speed would see a red that isn't
there.

**(b) A fresh clone cannot run its own gate.** `pip install -e '.[dev]'` refuses
here (`requires-python = ">=3.12"`, interpreter available 3.11.15), and with only
the dev extra installed **19 of 39 test modules fail at collection** on missing
runtime dependencies. The five runtime deps must be installed by hand before the
suite can even be collected. No environment is declared anywhere a machine can
act on — no lock file, no `make check`, no CI image.

**(c) The ledger checks the rows it has, never the rows it lacks.** Nothing in
`check_invariants.py` or the suite detects a new table, flag or capability that
arrived *without* a ledger row. Rule 2 — "no table or flag ships without a writer
and a reader" — is enforced by the operator's memory. This is the same class of
failure the 2026-08-13 coverage audit found: six specified capabilities
scheduled nowhere for weeks.

**UNREADABLE:** how much operator wall-clock Loop B actually consumes per epic.
The transcripts that would answer it are not in this clone, and no instrument
records it. The argument below does not depend on the figure.

---

## 3. What automation may never do (stated before the design)

This project's interesting part is always the constraint, so it goes first. The
hard core, by analogy to E6.5 and permanent for the same reason:

1. **Rule 4 holds for the builder.** No model grades its own change. The merge
   gate is tests, the ledger, migrations and measured deltas. A model's opinion
   is never a passing condition — an LLM reviewer may *annotate* a diff, and its
   annotation is never a gate.
2. **Rule 6 holds absolutely.** Automation may put a decision in front of the
   operator; it may never make one. Readiness, direction and every verdict stay
   the operator's, unquantified and unrubricked.
3. **The being's stores are out of scope.** The loop evolves code and documents.
   `data/newz.db` and `data/interior.db` are never written by it. R-13 is the
   precedent: editing the self-model is a deliberate operator act, not a
   maintenance action.
4. **TRUE_NORTH, the constitution, the structural ledger rows and the gate's
   hard clauses are not automatable targets.** A diff touching them is refused by
   the gate, not by the agent's good behaviour.
5. **Reach stays a config value the operator sets** (Rule 3; Decision 1).
6. **The evolver is not the being.** Separate agent, separate substrate, no read
   of `interior.db`, no write to the being's stores, no share of its credentials.

Point 6 needs its argument, because it is the one a reader will push on:

- *Rule 4.* A being that writes its own judge writes its own verdict.
- *Topology.* The 2026-08-18 proposal measured the being's held positions as
  substantially *about its own plumbing* — its pending-noticings queue, its
  `INITIATIVE PROBE` instructions, being called gibberish. Giving it commit
  access to that plumbing deepens exactly the self-reference the whole of P3
  exists to break.
- *And the freedom this buys.* Sovereignty (§7, S2 §12) constrains the
  **cognition** path, not the **build** path. The being's thinking must stay
  local and vendor-free; the tooling that builds it need not be, precisely
  because it never touches identity-bearing state. That distinction is what
  makes this affordable at all: the evolver may use the strongest hosted model
  available without touching §7, so long as the separation in point 3 holds.

---

## 4. The design — five stages, one gate each

**Stage 1 — Watch.** *No model is consulted.* A scheduled run of the read-only
instruments that already exist — `evidence.py`, `what_shaped.py`,
`gate_report.py`, `claims.py`, `budget.py`, `health.py`, `check_invariants.py` —
emitting a dated, machine-readable state read into a tracked `evolution/reads/`.
Rule 0 by construction: the method ships with the number, and an instrument that
cannot answer writes `UNREADABLE` (as §9.1's ingest share does today). Exit code
0 always; this reports, it does not judge.

**Stage 2 — Trigger.** *Declarative, in `evolution/triggers.yaml`.* The repo
already writes trip-wires — in prose, where no machine can stand watch on them:

| Trip-wire already written | Where |
|---|---|
| feeds contributing a read rise from 34 of 61 | PLAN E1.0 / S1-E |
| a concern opens on a subject that matched nothing at intake | PLAN E1.0 |
| at least one position changed because *the world* contradicted it | PLAN S1-E |
| the world's share of the grounding mix, baseline ≤17% | PLAN S1-E |
| `source_gaps` accumulating unanswerable questions (12 today) | PLAN §Going public |
| ingest breaching §9.1 → INV-041 pauses ingest | PLAN E1.0 |
| per-clause violation rate against the pre-withdrawal baseline | PLAN E6.3/E6.4 |

Transcribing these is the single highest-leverage step in this proposal: it
converts intentions that depend on someone remembering into standing
instruments. **A fired trigger opens an item. It never builds anything.**

**Stage 3 — Propose.** A fired trigger spawns an agent that writes one proposal
in `proposals/`, in the form this repo already uses — measured diagnosis, a red
team of itself, a falsifier, a reversion condition — and touches nothing else.
This is the unit the project actually runs on: nine proposals produced the whole
of P3. It is the cheapest possible automation, wholly reversible, and it lands
where the operator already reads. Throttled to one open automated proposal at a
time.

**Stage 4 — Build.** *Only for epics the operator has marked approved.* An agent
implements on a branch, and the merge gate is mechanical and non-negotiable:

- the full suite green, run **twice**, to catch the order-dependence class §2.2
  found;
- `check_invariants.py` exit 0;
- a new ledger row naming test, consumer and behaviour (Rules 1 and 2, enforced
  by a machine instead of a memory);
- migrations forward-only and applied against a *copy* of a real store;
- no diff inside §3's hard core;
- the epic's own **"Done when"** restated as an executable check.

Failing any of these is a red, not a discussion. Passing all of them is a
*candidate*, not a merge: the operator merges.

**Stage 5 — Verify in life.** After merge, the epic's evidence read runs on
schedule for a stated window against the recorded baseline, and the falsifier
the proposal was required to carry decides. The repo already writes these
properly — E1.0's is exemplary: *"if coverage does not rise, the answer is a
rotation floor, never the old filter."*

Note the asymmetry, deliberately: **stages 1, 2 and 5 reduce operator load;
stages 3 and 4 add to it.** That single fact drives the sequencing below and is
the answer to this proposal's own strongest objection (§7 R1).

---

## 5. Sequencing — smallest thing that pays, first

| Step | What | Why here |
|---|---|---|
| **S1** | Fix the yield-count race; declare a runnable environment; run suite + `check_invariants.py` on every push | Everything downstream trusts this gate. It is ~a day and no new architecture, and today a fresh clone cannot even collect its own tests |
| **S2** | Ledger-coverage check: a migration that adds a table with no ledger row naming its reader fails the build | Turns Rule 2 from memory into a machine; closes §2.2(c) |
| **S3** | The state read (Stage 1) | Pure reuse of instruments already written and already Rule-0 disciplined |
| **S4** | `evolution/triggers.yaml` (Stage 2) | The highest-leverage step; stops capabilities going unwatched, which is this project's repeat failure mode |
| **S5** | The proposal agent (Stage 3), one open proposal at a time | First step that spends operator attention; earn it with S3–S4's reads first |
| **S6** | The gated builder (Stage 4) | Last, and first applied where being wrong is cheap and mechanical |

**Recommended first build target once S6 arrives: E1.5** — the permanent record
of error. Its "Done when" is already an executable statement ("every
resolved-against claim is retrievable with its original claim, its resolver and
its cost, and nothing prunes it"), it depends only on E1.4 which is built, and
it is a migration plus a retrieval path plus a ledger row — the exact shape a
mechanical gate can certify.

---

## 6. What this buys, against True North

- **§5 Priority 1** — the six foundation items are delivered by Loop B, so
  Loop B's throughput *is* the delivery rate of the foundation.
- **§5 Priority 3** — guardrails recede on *demonstrated* maturity, and
  demonstration means E6.3's per-clause rates measured continuously against a
  baseline. That is a Watch job. Today nobody is standing there.
- **§7 Sovereignty** — strengthened, not weakened. A declared environment and a
  mechanical gate are what portability and recoverability mean in practice; a
  system that only one machine can build is not portable, whatever the spec says.
- **§4.3 "development matters more than activity"** — applied to the builder:
  merge rate is activity. Stage 5 is the only stage that speaks to development,
  and it speaks slowly, on purpose.

And honestly: **it buys nothing for §2's outcome directly.** No reader arrives
because the build got faster. This proposal serves Priority 1's *dependency
order*; it does not touch the aspiration.

---

## 7. Red team — against this proposal

**R1. Automating the builder grows a queue in front of the one thing that cannot
be automated.** Rule 6 makes the operator the judge of everything that matters; a
faster builder produces more to judge, and P3-04 already names the operator as
judging from inside the loop. *This is the strongest objection, and it is
accepted rather than answered.* It is why the sequencing is evidence-first and
builder-last. **Falsifier:** if automated proposals are mostly rejected, the loop
is manufacturing work rather than doing it. Measure proposals opened versus
accepted; below one in three, stop Stage 3.

**R2. Evidence theater.** Automating the instruments makes it easy to let a
dashboard stand in for the read — §10's named failure, wearing a cron job.
Mitigation: Watch emits a *read*, never a verdict; exit 0 always, following
`evidence.py`'s own discipline; and **no aggregate score is ever computed**,
because a single number is precisely the rubric Rule 6 refuses.

**R3. A green gate is not a good change.** 517 tests passing says the change did
not break what was already written down. It says nothing about True North. Only
Stage 5 speaks to that. Do not let merge rate become a measure of progress —
that is §10's "activity, memory growth, or output volume" in a new costume.

**R4. Transcribing trip-wires is itself a judgment.** Turning "definitively
toward True North" into YAML would be exactly the rubric Rule 6 refuses.
Mitigation: **only counts go into `triggers.yaml`** — PLAN Rule 6's own
distinction, that Rule 0 governs the plan's counts and not its verdicts. No
trigger may conclude readiness; the strongest act available to a trigger is
opening a proposal.

**R5. New surface, new dependency.** An agent with commit rights, credentials and
network access is system surface this project does not currently have.
Mitigation: the evolver holds none of the being's secrets, reaches none of its
stores, and its output is a branch — never a deploy. The being's runtime is
untouched until the operator merges and restarts.

**R6. A loop that can change its own rules eventually will.** Mitigation is §3's
hard core enforced *by the gate*: diffs touching TRUE_NORTH, the constitution,
structural ledger rows or `evolution/` policy are refused mechanically. A rule
the agent is merely asked to respect is not a constraint.

**R7. It may simply be premature.** Eight of 35 epics in about eleven days, by
hand, is not obviously a throughput crisis, and the status quo's real argument is
that this proposal solves a problem the project does not yet have. The honest
counter is that at this size the automation does not buy *speed* — it buys **not
forgetting**. The 2026-08-13 audit found six specified capabilities scheduled
nowhere; INV-044 exists because work in flight that nothing owns is this
project's recurring failure. That is an argument for Watch and Trigger, and not
for the builder — which is, again, why the builder is last.

---

## 8. Alternatives considered

**Full autonomous self-modification** — the agent merges on its own judgment.
*Rejected.* It breaks Rule 4 at the point where Rule 4 matters, and with one
operator and no readers there is no external check on a bad merge. The
diagnosis that produced P3 applies to the builder as exactly as to the being:
more thinking inside a closed loop yields more elaborate self-reference.

**The being evolves its own code.** *Rejected*, per §3.6 — and it is worth
saying that this is the option that *sounds* most like True North and is
furthest from it. Sovereignty is about who controls the conditions of the being's
continuation, not about who holds the commit bit.

**A larger or better model as the lever.** *Refused by the premise*, and by the
numbers: 3.2% novelty, 50% self-grounding and 0 non-self-graded outcomes are
topology, not capability. A stronger model in the same closed loop reaches more
elaborate self-reference sooner.

**Nothing — keep hand-building.** *Defensible today*, and §7 R7 is its argument.
It fails on the one thing automation is uniquely good at: standing watch on
conditions that nobody is currently looking at.

---

## 9. What this proposal does not claim

- It does not claim depth comes from a faster builder. P3's own line, turned on
  this proposal.
- It offers no readiness threshold and no score. Every verdict stays on the
  operator's side of Rule 6.
- It schedules nothing. It proposes an instrument; whether to run it is a
  decision, below.
- **Nothing here is implemented.** The three findings in §2.2 were measured this
  session on a clean container; everything else is read off the tracked
  documents. In particular the flaky test was diagnosed and **not** patched —
  that is a change to the being's suite and belongs to whoever decides this.

---

## 10. The decision asked for

One question, in two parts:

1. **Should the build loop exist at all?**
2. If yes — **S1–S4 only** (watch and trigger; nothing builds itself), or
   **S1–S6** (the whole loop, with the operator still merging)?

**Recommendation: S1–S4 now, S5–S6 deferred** until a month of reads shows the
triggers firing on things worth acting on. S1 and S2 are worth doing whatever is
decided about the rest: a gate nobody runs, that goes red twice in three runs,
on a repo a fresh machine cannot build, is not a foundation any automation could
stand on — and it is not much of a foundation for hand-building either.

---

## 11. Amendment — the recommendation is withdrawn, and superseded

*2026-08-19, later the same day.*

**§10's recommendation (S1–S4 now, S5–S6 deferred) is withdrawn.** A red team of
this document found four attacks it does not survive:

- **A1.** It never established the constraint it claims to relieve. §2 measured
  that delivery is *unautomated* and substituted that for *slow*. The commit log
  answers what §2 marked UNREADABLE: E1.1 through E1.4 landed 06:12–06:47 on
  2026-08-19 — **four epics in 35 minutes**, by hand. Delivery is not the
  constraint.
- **A2.** The premise — that the model is not the system constraint — is
  unfalsified. 3.2% novelty, 50% self-grounding and 0 non-self-graded outcomes
  are consistent with a model limit and a topology limit alike, and no
  experiment in the repo discriminates them. R-12's own line applies to this
  document: *only true if measured*.
- **A3.** Automating falsifiers is more dangerous than automating the builder.
  A bad merge is caught by 517 tests; a bad falsifier is caught by nothing, and
  the thresholds were authored in prose before the evidence existed.
- **A4.** The timing was the worst available: the outer loop was thirteen hours
  old and S1-E had never been read.

Partly landing: the world-expansion idea in §7 R7's neighbourhood reintroduces
the concern-coupling E1.0 removed; the §3.6 sovereignty line satisfies §7 but not
§8, since a hosted agent authoring the being's cognitive machinery is an
unexposed shaping influence; and §2.2(a)'s flake rate was measured on Python
3.11.15 against `requires-python = ">=3.12"`, so the *rate* belongs to an
unsupported environment even though the yield-count race is real anywhere.

**What survives:** §2's findings — no runner, an unrun gate, an undeclared
environment, a ledger that checks the rows it has and not the rows it lacks — and
§3's hard core, which is carried forward intact.

**Superseded by `proposals/2026-08-19-the-self-evolving-loop.md`**, which designs
the loop the operator actually specified: autonomous through restart, supervised
without a service manager, rolled back through commits, and guided by TRUE_NORTH
and PLAN together under a stated precedence.
