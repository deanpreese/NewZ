# The instruments have no heartbeat

*2026-08-20. A proposal for the work between Phase 3 closing and the SEL
starting, from the readiness review run against `ee84745`. Ten items, three
tranches, all Class A. Red team at §5, and it killed one of the items.*

---

## 0. The finding, in one line

**Phase 3 delivered the instruments and did not deliver their heartbeats.** The
suite is green (727), the ledger is clean (78), the surface rebuilds
byte-comparably, and the hard core is enumerated — and underneath that: the
agreement writer has no caller, the metric series has one reading, four of the
six kill conditions have no metric behind them, nothing runs the gate, and
nothing regenerates the page the Watcher is specified to read.

The SEL is a rhythm. What Phase 3 built is a set of tools that run when a person
types them.

---

## 1. What this proposes

| | Item | Tranche | Class |
|---|---|---|---|
| W1 | R-37c — a derivation's declared inputs become its **only** inputs | T1 | A |
| W2 | R-37d — the reply batch is **recorded**, and an exchange is one reply and everything it answered | T1 | A |
| W3 | E3.8 gets a rhythm, and `kill:operator-agreement` gets its metric | T1 | A |
| W4 | `authority.may_justify` becomes the rule `premises.py` already re-implements | T1 | A |
| W5 | E8.0 — a declared environment, one gate command, hooks, CI | T2 | A |
| W6 | The commit trailers start, enforced at `commit-msg` | T2 | A |
| W7 | R-37e — the surface regenerates nightly, and an empty backup stops verifying | T2 | A |
| W8 | Measurement code outside `newz/evidence` cannot enter unclassified; `.gitignore` joins the core | T3 | A |
| W9 | PLAN's `Done when` clauses are hashed into `epics.yaml`, so softening one fails the gate | T3 | A |
| W10 | `pre_loop_baseline.yaml` — the kill condition that matters most gets a definition | T3 | A |
| W11 | **the enforcement layer joins the core it enforces**, and so do `epics.yaml` and `premises.yaml` | T3 | A |

**Nothing here is new capability for the being.** Every item is judged by the
test suite, so under Phase 8's taxonomy the whole tranche is Class A and none of
it competes for an evidence window. Phases 0–7 are not reordered; Phase 8 is not
started.

**Approving this proposal is the operator act these files require.**
`instruments.yaml`, `hard_core.yaml` and `epics.yaml` are inside the hard core,
and W1, W3, W8, W9 and W10 all write to them.

---

## 2. The clock, which is what decides the order

`_baseline()` takes the last measured reading from **before the window opened**,
and the window is 168 hours. The series began at 2026-08-20 08:42 with 18
readings at one timestamp. So:

- **no metric has a non-null delta before 2026-08-27**;
- the six baselined metrics never yet recorded — `consequence_rate`,
  `restatement_rate`, `volume_against_development`,
  `autonomy_against_world_grounding`, `operator_disagreement_rate`,
  `episodes_recorded` — reach theirs around 2026-08-28;
- and under E2.8, **changing a metric's definition resets its baseline and
  starts the series again.**

Which makes the ordering mechanical rather than a preference. Every definition
change in this proposal — W1's derivations, W2's redefinition of an exchange,
W3's new series — is **free today and costs seven days after 2026-08-27**. T1
lands first because the clock says so, not because it is the most important.

---

## 3. The items

### T1 — the definition changes, before the series is worth keeping

**W1 — a derivation's declared inputs become its only inputs.**

R-37c, confirmed: `consequence_rate` declares `advance_acceptance` and
`claims_opened` and actually reads `concern_advances` and `resolutions`;
`autonomy_against_world_grounding` declares two inputs and reads three
quantities. The grades come out defensible by luck.

The fix is not to correct the declarations — a second hand-maintained list
drifting from the thing it describes is the E2.11 problem, and correcting it
once leaves nothing checking it. Each derivation becomes a **pure function over
a mapping of already-computed input values**, and the mapping exposes only the
names in `DERIVED_FROM`. Reading an undeclared input raises. The declaration
stops being a claim about the implementation and becomes the implementation's
argument list.

That forces the inputs to exist as registered, recorded metrics in the same
nightly pass, which three of them are not: `advance_acceptance`,
`perspective_novelty` and the settled-claims count `consequence_rate` divides by
(which is not a registered metric at all today — its numerator is an
unregistered quantity). They are added to the registry and to `record_all`.

*Done when:* every derivation is a function of a declared-inputs mapping,
undeclared access raises, and a test asserts that each function's inputs are
exactly its `DERIVED_FROM` row. Definition versions bumped in the same commit.

**W2 — the reply batch is recorded rather than inferred.**

R-37d, confirmed: `_pairs` takes the next outbound message after each inbound
one, and the drainer coalesces pending messages into one reply — three messages
answered by one reply become three exchanges judged against the same text.

The drainer knows the batch. Migration `0039` records it (an `answered_by`
column on the inbound row, written when the batch is replied), and `_pairs`
becomes a group-by rather than a guess. **An exchange becomes one reply and
everything it answered**, with the person's messages concatenated in order.

*Forward-only, no backfill.* Judging the 148 historical inbound messages under
the old pairing would fill the first window with exactly the figure this item
exists to remove. The series starts when the writer is correct.

*Not a cognition-path change.* It writes an id the reply path already has. It
does not change what the being says, what it reads, or how it decides, so it
does not reset the evidence window the way R-31/R-33/R-35/R-36's fixes did.

*Done when:* a coalesced batch produces one exchange, the concatenation order is
tested, and no exchange is judged twice.

**W3 — E3.8 gets a rhythm, and the sixth kill condition gets its metric.**

`agreement.classify()` has no production caller — only
`tests/test_agreement.py`. `operator_agreement` holds 0 rows.
`disagreement_rate` therefore returns UNREADABLE every night, and
`kill:operator-agreement` has **no metric serving it** in the registry.

An `AgreementScheduler` in `run_newz.py`, on the nightly cadence and before
`MetricScheduler`, so each night's reading sees the exchanges judged. Bounded at
`MAX_PER_RUN`, failing closed as `classify` already does.
`operator_disagreement_rate` gains `kill:operator-agreement` in its `serves`
list, and `perspective_novelty` gains it too — the condition is *agreement
rising while novelty is flat*, and it reads two metrics.

*What this does not do,* recorded because it is the likely outcome: it does not
guarantee a readable rate. The denominator is exchanges where a position was at
stake, and it may stay empty for weeks. See §5 RT1 and RT2 — an earlier draft of
this item proposed a minimum denominator before the halt may fire, and the red
team killed it.

*Done when:* the scheduler records verdicts in life, the read shows the rate with
its denominator, and UNREADABLE carries the count it was computed from.

**W4 — `authority.py` gets its production caller.**

`newz/evidence/authority.py` — the module that makes Rule 7 mechanical (*may
halt on any grade, may justify only if mechanical*) — is called from tests only.
`premises.py` line 124 re-implements the same rule inline
(`grade_of(d.metric) == "mechanical"`). One line, one import, one copy of the
rule deleted.

*Done when:* `premises` calls `may_justify`, and a test asserts a model-graded
premise cannot justify a plan change through that path.

### T2 — the gate, which is E8.0

**W5 — a declared environment and one gate command.**

No `.github/`, no hooks, no `environment.yml`, no lock; five runtime
dependencies installed by hand against `requires-python = ">=3.12"` while
`agent13` runs 3.13.11. `freeze_check`, `check_invariants`, the E2.11 drift
check and `rebuild_check` all run only when typed.

- `environment.yml` declaring the interpreter, and `pip install -e '.[dev]'` as
  the only hand step, with a fresh-clone smoke path in the README section E8.0
  asks for;
- `tools/gate.py` — pytest, `check_invariants` (which carries the epic drift
  check), `freeze_check`. `--soak N` runs the suite N times for E8.0's ten
  consecutive green runs. `rebuild_check` stays out of the per-commit path on
  time and joins the weekly job;
- `.githooks/pre-commit` running the gate, enabled by
  `git config core.hooksPath .githooks` — tracked in the repo, one command to
  install;
- `.github/workflows/gate.yml` as the backstop for when the operator pushes.

*Done when:* a fresh clone installs and runs the suite from the declared
environment with no hand steps beyond the documented one, `--soak 10` is green,
and a commit that breaks either check is refused locally.

**W6 — the trailers start.**

`Schema:` / `Restart:` / `Class:` / `Semantics:` appear on **0 of 80 commits**.
E8.2 makes git the entire recovery story and `Semantics: yes` the trailer a 2
a.m. recovery reads. History written before the discipline starts is history the
runner cannot read, and the discipline costs four one-line answers.

Enforced at `commit-msg` from the first commit after approval. Not retroactive —
the runner's `LAST_KNOWN_GOOD` will not point behind the adoption date, and that
is stated in `hard_core.yaml`'s `open_gaps` rather than discovered.

**W7 — the surface regenerates, and an empty backup stops verifying.**

R-37e, both halves, and both land on the SEL. `published/` is from 13:12 while
the store has been written continuously since — E8.3's daily read is specified
against a page nothing refreshes. And `cleanroom.verify()` returns a row count
without asserting one, so a backup that restores to nothing passes the check
that E8.2's rollback depends on.

A regeneration rhythm in `run_newz.py` after the nightly reading, so the page
matches the series. `verify()` gains a minimum and `rebuild()` and `health.py`
treat zero as a failure rather than a number.

### T3 — the boundaries E8.2 and E8.4 will lean on

**W8 — no unclassified measurement code, and `.gitignore` joins the core.**

`hard_core.yaml` records the hole itself: the derived rule reaches
`newz/evidence` and stops, `newz/telemetry.py` and `newz/memory/provenance.py`
are named by hand, and **nothing detects a failure to name the next one**.

The check: take the transitive `newz.*` import closure of the canonical tools;
every module in it must be classified in `hard_core.yaml` as frozen or as a
mechanism with a reason. An unclassified module fails the gate. The
classification lives inside the core, so only the operator can add an exclusion —
which is the property that makes it a boundary.

`.gitignore` is added to the core's paths. It is tracked, so it produces a diff;
leaving it writable leaves a two-step path to invisibility — ignore a file, then
edit it unseen.

*Recorded for E8.2:* the brake must be a **tracked** file. `runner.yaml` is
already gitignored, and a brake living there would be a pause flag no diff check
can see, which is the R-37b shape again.

**W9 — a `Done when` cannot be softened without failing the gate.**

`hard_core.yaml` records that PLAN.md is protected by *section* and no check
reads sections. E2.11's drift check already re-derives ids, titles and
dependencies from PLAN's text; extending it to hash each epic's **`Done when`
clause** into `epics.yaml` costs a field and reuses the parser. A loop editing
its own acceptance criterion then fails the same check that already runs.

Narrowed deliberately to `Done when` — see §5 RT7.

**W10 — "pre-loop baseline" gets a definition.**

The phrase appears three times in PLAN, once in `instruments.yaml`, once in the
SEL proposal, and is defined nowhere. It is the read behind the kill condition
Phase 8 calls the one that matters most.

`evolution/pre_loop_baseline.yaml`, inside the core, written **once by the
operator** at the moment stage 0 starts: the metric values, the window they were
computed over, and the reading ids they came from. Measured from the being's own
recorded series, not imputed — and written by the operator, because a loop that
computes the baseline it is judged against has none.

**W11 — the enforcement layer is outside the boundary it enforces.**

Found while enumerating the files each item touches, after the review was
written. `hard_core.contains()` answers **False** for every one of these:

| File | What it does | Today |
|---|---|---|
| `newz/evidence/freeze.py` | computes the refusal | writable |
| `newz/evidence/hard_core.py` | reads the registry, derives the frozen set | writable |
| `newz/evidence/reach.py` | attests reach against the pin (INV-076) | writable |
| `newz/evidence/authority.py` | may-halt / may-justify (INV-073) | writable |
| `tools/freeze_check.py` | the entry point | writable |
| `evolution/epics.yaml` | the queue and, under W9, the `Done when` hashes | writable |
| `evolution/premises.yaml` | the premises rung 5b justifies a plan change with | writable |

`hard_core.yaml` states the principle — *a boundary the constrained party can
widen is not a boundary* — and puts itself inside the core for that reason. The
**code that reads it** was not. Neither was the file W9 is about to put the
acceptance criteria in, nor the file a plan-change proposal must cite a moved
premise from: a loop that can write `premises.yaml` can manufacture the premise
that justifies its own plan change, which is rung 5b defeated at the source.

All of it is `paths:` entries in `hard_core.yaml` plus a test, **except
`epics.yaml`**, which has a real conflict: PLAN expects the loop to record
completions, and `status: built` is a completion record. *Recommended:*
`epics.yaml` frozen except the `status` field, enforced structurally rather than
by path — the loop may flip a status and may not touch a dependency, a class or
a `Done when` hash. *Alternative, if the structured check is judged too clever:*
freeze it whole and syncing status becomes the operator's, at the cost of one
edit per built epic.

*Done when:* a diff touching any row above is refused for the loop, a test
asserts each refusal by name, and the `epics.yaml` status exception is tested in
both directions.

*Why this is T3 and not T1:* nothing enforces any of it until E8.0's gate runs
and E8.4's builder is the party being refused. It must land **before the loop
builds**, not before the series accrues.

---

## 4. What this does not do

- **It does not start Phase 8.** No runner, no Watcher, no builder. E8.0 is the
  only Phase 8 epic in it, and E8.0 is the gate.
- **It does not backfill the agreement series.** 148 historical exchanges stay
  unjudged.
- **It does not fix the classifier judging the being with the being's own model
  family** (R-37d's second paragraph). `model-graded` records that a model
  judged, not which one; the row already stores the model, and the registry
  reason will say so.
- **It does not touch R-11's second machine, mutation testing, or the R-22
  probe.**
- **It does not close R-36.** The door still checks that a date is future and
  never that an event is.
- **It does not make the gate a boundary against the loop.** See RT5.

---

## 5. Red team

Written against this proposal, not for it.

**RT1 — W3 may deliver a metric that is unreadable forever, and it will look
fixed.** 148 inbound messages in eleven days, and the denominator excludes
`neither` by design. If the operator rarely says something a position could be
staked against, `disagreement_rate` returns UNREADABLE indefinitely — and a
wired-and-empty kill condition reads, on a dashboard, exactly like a working
one. *Decision:* keep the item, and make the emptiness legible: the read shows
the at-stake count beside the rate, and the registry records that a persistently
absent denominator is itself the finding. Including `neither` to manufacture a
denominator is refused — it would measure how often the operator says something
contestable, not what the being does when they do.

**RT2 — the minimum-denominator threshold I proposed is an invented number, and
it kills the condition it protects.** The first draft of W3 said the halt may
only fire with at least N at-stake exchanges in the window. At n=1 there is no
basis for any N, and any N large enough to be meaningful is large enough that
the halt never fires — inventing a denominator so a kill condition can behave is
the failure §10 names and the reasoning the operator already applied to the
spend condition on 2026-08-20. *Decision: the sub-item is withdrawn.* UNREADABLE
means unreadable, and INV-044 is the discipline.

**RT3 — W1 moves the fault rather than removing it.** Binding a derivation to
its declared inputs says nothing about whether a *primitive* metric's
implementation matches its registry text. `nights_slept` is "Perspective
versions written in the window" in the registry and whatever
`mechanical.py` does in fact. *Decision:* recorded as remaining, not claimed
fixed. The derivation layer was where a grade could be laundered silently; the
primitives are where it can be wrong loudly.

**RT4 — W2 is a `Semantics: yes` change and I nearly ordered it after W3.** If
the agreement series starts before the batch is recorded, the first week's rate
is computed over a denominator that counts messages and the second week's counts
exchanges, with no definition boundary between them unless E2.8 is invoked — the
exact defect E2.8 exists for. *Decision:* W2 strictly before W3, and the
definition version is bumped in W2's commit regardless of whether any reading
exists yet.

**RT5 — the pre-commit hook constrains the honest party.** The loop will run as
the same user, `--no-verify` is one flag, and CI only fires on a push the
operator makes rarely. W5 therefore buys hygiene for the operator — which is
worth having, since a red commit went in on 2026-08-19 — and close to nothing
against the loop. *Decision:* keep it, and refuse to let it read as a boundary.
`hard_core.yaml`'s `open_gaps` entry for enforcement stays open, and it closes
with E8.4's builder gate, not with this.

**RT6 — W8 will be gamed by the honest party too.** Every new module in the
closure demands a `hard_core.yaml` line during ordinary work, and the cheapest
way past a gate failure is to write `mechanism` without thinking. *Decision:*
the failure message names the metrics the module could affect by name
(`metrics_affected` already computes this), so the classification is made with
its consequence in front of the person making it. Residual risk accepted and
recorded.

**RT7 — W9 hashes prose the operator edits constantly.** Hashing intent, hooks
and decision rules would fail the gate on every ordinary PLAN edit and train the
operator to bypass it — a check that cries wolf is worse than no check.
*Decision:* narrow to the `Done when` clause alone. It is the acceptance
criterion, it is the thing a loop softening its own standards would touch, and
it changes rarely. Intent and Hooks stay convention, and `hard_core.yaml` says
so.

**RT8 — W10 could be the invented denominator RT2 refuses.** *Counter:* it is
computed from the being's own recorded readings over a stated window, not from
an imputed value, and what is being fixed is that "pre-loop" has no date rather
than that it has no number. *Decision:* keep, with the file recording the
window, the reading ids and the date, and with the operator as its only writer.

**RT9 — T1 must fit before 2026-08-27 and it contains a migration.** Four items
and one schema change, all Class A, none touching the cognition path. If T1 slips
past the 27th the cost is not failure — it is seven days of series thrown away
for whichever metric's definition moves late. *Decision:* proceed, and if only
part of T1 lands, land W1 and W2 (the definition changes) and let W3 and W4
follow, since those two add series rather than redefining one.

**RT10 — ten items of instrument work is how the loop never gets built.** The
review's own finding was that Phase 3 built tools instead of rhythms; a proposal
answering it with ten more items of instrument work is the same failure wearing
a fix. *Counter:* T2 **is** E8.0, which PLAN already orders before everything in
Phase 8; T1 is four small items on a seven-day clock; T3 is three boundary items
that E8.2 and E8.4 are specified against and cannot be built without.
*Decision:* proceed, and hold the line that nothing in T3 is a prerequisite for
starting **stage 0** — the loop can read, decide, propose and report while T3 is
open. If T3 slips, the loop still reads.

**RT12 — the review missed W11, and only the act of listing files found it.**
The readiness review read `hard_core.yaml`, quoted its `open_gaps`, and accepted
its account of what was unprotected. The registry's gaps are honest about the
brake, the runner, the stage file and PLAN's sections — and silent about the
enforcer, because a document describing a boundary does not notice that the code
reading it sits outside. It took running `contains()` over the actual file list
to see it. *Decision:* recorded as the method lesson — **ask the check, not the
document** — and it is an argument for W8, whose whole content is a check that
answers a question a document was previously trusted for.

**RT11 — the review that produced this proposal was run by the party proposing
the work.** Every finding in it is mechanical and reproducible from the commands
in §6 of the review, which is the mitigation available; it is not independence.
*Recorded, not solved.* The structural separation the SEL specifies for its own
red team (fresh context, artifact only, instructed to refute) applies here too
and was not used.

---

## 6. Order, and the dated gate

| When | What | Gate |
|---|---|---|
| Now → 2026-08-26 | **T1** — W1, W2, W3, W4 | suite green, ledger clean, definition versions bumped |
| 2026-08-27 | the series has its first real deltas | nothing to do but read them |
| Next | **T2** — W5, W6, W7 | `tools/gate.py --soak 10` green from a fresh clone |
| Then | **T3** — W8, W9, W10, W11 | a diff touching unclassified measurement code, the enforcer, or a `Done when` is refused |
| Then | **E8.2**, **E8.3** — the runner and the Watcher | PLAN's own `Done when` clauses, unchanged |
| Then | stage 0 runs, three proposals compared *(Decision 3)* | the operator's judgment, Rule 6 |

**Stage 0 does not wait for T3.** It reads, decides, proposes and reports, and
its reads improve as the series deepens.

---

## 7. The decision asked for

1. **Approve the tranche**, in the order at §6, as Class A work under Phase 8's
   own taxonomy.
2. **Approve the hard-core writes** it entails: `instruments.yaml` (W1, W3),
   `hard_core.yaml` (W8, W11, W6's note, RT5's gap), `epics.yaml` (W9), the new
   `pre_loop_baseline.yaml` (W10), and edits to the frozen measurement modules
   `derived.py`, `baseline.py`, `mechanical.py`, `agreement.py`, `premises.py`
   (W1–W4), each carrying E2.8's `definition_version` obligation.
3. **Confirm the withdrawal at RT2** — no minimum denominator before the
   agreement halt may fire.
4. **Choose W11's `epics.yaml` form** — frozen except `status` (recommended), or
   frozen whole with status becoming the operator's.
5. **Note what stays open:** R-36, R-11's machine, mutation testing, the R-22
   probe, and the fact that the gate is not a boundary against the loop until
   E8.4.

Nothing in this proposal is built. It is written for approval, and the tree is
otherwise clean at `ee84745`.
