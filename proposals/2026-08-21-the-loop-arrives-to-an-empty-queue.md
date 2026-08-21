# The loop arrives to an empty queue

*2026-08-21. A red team of the plan forward — what the SEL can still build,
what it cannot reach, and what it achieves against TRUE_NORTH. Written on the
operator's question: **is the SEL too bounded or constrained to accomplish its
goal?** Figures measured from this clone at `52670b4`, from `data/newz.db`
read-only, from `evolution/*.yaml` and from the gate run this session; where a
claim has no instrument, it says so (Rule 0). §5 red-teams this document.*

**The short answer: it is not too constrained. It is aimed at a bottleneck that
is not the binding one, and its own approved proposal says so** — §9's R-N2
("an autonomous delivery loop with a True-North circuit breaker, not a
self-evolving system") and R-N4 ("the strongest attack on the enterprise").
Both were conceded and accepted in §14. What is new here is that **the premises
under those concessions have moved**, and moved against the design.

**And on the operator's reading of the first draft, the follow-on holds:
Phase 8 as scheduled is not worth its development time at present prices.** C2
is revised to about a day of it — an out-of-band heartbeat and a weekly digest —
and records why that is not zero.

---

## 0. The finding, in one line

**The SEL's proving ground was delivered by hand before the loop existed, and
what remains for it to build is three epics** — while the ladder that governs
its autonomy needs three Class A changes to leave stage 1 and a month of
restarts at a measurable revert rate to leave stage 2.

---

## 1. What was counted

*Method: `evolution/epics.yaml` via `newz.evidence.epics`; PLAN §Phase 8's
Class A/B definition applied by hand; store figures from `metric_readings` at
its latest timestamp (168h window, 2026-08-21); the gate run once under
`agent13`.*

### 1.1 The system is where the operator says it is

Gate **clean** this session — suite pass in 103.6s, `INVARIANTS` 88 rows,
freeze "nothing changed". **32 of 53 epics built**, 5 dormant (Phase 7), 16
open. Phases 0–3 are closed. The sensor layer is graded (E2.5), consumer-mapped
(E2.6), baselined (E2.7), revision-safe (E2.8), rendered (E3.6) and frozen
(E3.9) — 25 paths in the canonical closure, 9 protected outright.

Phase 3 closing is real. The rest of this document is about what it opens onto.

### 1.2 What is left for the loop to build: three epics, possibly four

Of the 16 open epics, 4 are Phase 8's own. Of the remaining 12:

| | Count | Which |
|---|---:|---|
| in-life — no test closes them, the loop cannot | 5 | E4.2, E5.3, E5.4, E6.2, E6.4 |
| mechanical but **Class B** by PLAN's own definition | 2 | E5.1, E5.2 — *budgets* |
| mechanical but **refused at rung 1** | 1 | E6.5 — it enumerates `constitution/`, a protected path |
| **mechanical and Class A** | **4** | E4.1, E4.3, E6.1, E6.3 |

And E4.1 is the doubtful one: its authoring door is modelled on the claim door,
which is a model call. If it is, the loop's whole remaining queue is **three
epics** — E4.3, E6.1, E6.3.

### 1.3 The ladder needs more fuel than the queue holds

PLAN's Enablement table:

| Stage | Widens when | Fuel it needs |
|---|---|---|
| 0 → 1 | three proposals compared against the operator's choice | none — proposals are free |
| 1 → 2 | **three Class A changes** pass the gate, none reverted by hand | 3 of the 3–4 |
| 2 → 3 | one month at stage 2, **reverted restarts below 1 in 5** | ≥5 restarts, i.e. ≥5 more changes |
| 3 → 4 | not scheduled | — |

**Stage 2 → 3 has a denominator problem.** "Below 1 in 5" needs at least five
restarts to be a rate at all, and after stage 1 consumes three the queue holds
zero or one. The rung the whole Class B ambition sits behind cannot be measured
into existence from the work the plan still contains.

### 1.4 The precedence table authorises no fuel outside the queue

PLAN names five kinds of Class A change: *"bug fixes, ledger rows, migration
hygiene, an instrument reading `UNREADABLE`, the generator."* Four of the five
are not epics — and the precedence table has no rung that permits building a
non-epic. Rung 4 is *"an epic is unblocked and approved → build it"*; rungs 5a
and 5b **never build**. So the loop may build only from a queue of three, and
every other Class A change it can see must be escalated as a proposal.

**One of the five is also self-contradictory.** "An instrument reading
`UNREADABLE`" is a diff inside the frozen closure — verified:

```
freeze.refusals(['tools/evidence.py'])
→ "a canonical instrument … changing it is an operator act (E3.9)"
```

Rung 1 refuses the fix that Class A names as its own example. That is not a
defect in the freeze; it is PLAN's Class A list written before the freeze
existed and never reconciled with it.

### 1.5 Class A and Class B are prose, and the loop grades its own

`hard_core.yaml` exists because §5's boundary was prose the enforcer could not
read. **The Class A/B boundary is in exactly that state now.** `epics.yaml`
carries `done_when`, `done_when_sha`, `binds` and `falsifier` — and no class.
`grep -rn "Class A" newz/ evolution/ tools/` returns two hits: an epic title
and a comment. E8.4 is *"the builder, Class A only"*, and nothing can compute
whether a given epic is Class A. The constrained party self-assesses, with a
gradient toward generosity.

### 1.6 Of the loop's six kill conditions, the two that read the being cannot fire

| Condition | Status today |
|---|---|
| nights slept below the **pre-loop baseline** | `pre_loop_baseline.yaml` is empty — `taken_at: null`, `metrics: {}`. `pre_loop.py` refuses to compare against nothing. The series began 2026-08-20; a 28-day window closes ~**2026-09-17** |
| operator agreement rising while novelty is flat | `operator_agreement` holds **0 rows**; `operator_disagreement_rate` reads **UNREADABLE**. `exchanges_at_stake` = 0 over the window. The writer is wired in `run_newz.py` since 2026-08-20 |
| reverted restarts above 1 in 5 | no runner (E8.2) — nothing to read |
| plan drifted from TRUE_NORTH, twice | procedural; an operator act, quarterly |
| a plan-change proposal cannot name a moved premise, twice | procedural; needs the loop's own record |
| loop spend exceeds the being's | **kept but not expected to bind** (operator, 2026-08-20) — reported, never halts |

Three are procedural or await the loop's own machinery, which is fine. The two
that measure **the being** are both uncomputable — including the one PLAN calls
*"the one that matters most"*. INV-044's own principle applies: a boundary that
looks enforced and is not is worse than none.

### 1.7 Rung 2 fires on a rise, and three of its signals are already at the floor

Latest readings, 168h window:

| §10 item | Metric | Value |
|---|---|---:|
| novelty without consequence | `consequence_rate` | **0.0** |
| consistency without development | `restatement_rate` | **0.936** |
| activity / volume | `volume_against_development` | **105** episodes per Perspective item |
| autonomy without perspective | `autonomy_against_world_grounding` | 358.7 |
| — | `positions_changed_by_world` | 0 |
| — | `claims_settled` | 0 |
| — | `works_revised` / `works_retracted` | 0 / 0 |

Good news first: **§10 is now 6 of 10 instrumented**, against R-S1's 2.5 —
`purpose.unserved()` leaves only demonstration, fluency, a consciousness claim
and evidence-scores, all four of which PLAN is right to refuse to proxy.

Then the defect. Rung 2 fires when *"a signal is rising"*. Three of the six are
**pinned at their failure value now**, and a saturated signal does not rise. The
circuit breaker the whole precedence leans on is, for the items that matter
most, structurally incapable of tripping — not because it is badly built, but
because it was specified as a derivative when the system is sitting on the
floor.

### 1.8 The outer loop's latency exceeds the loop's entire ramp

8 resolutions, **all open, none settled**. Due dates: 2026-12-18, 12-19, 12-26,
2027-02-16, 02-16, 02-17, 08-21, 08-21. `door.py:51-52` sets `MIN_HORIZON_DAYS
= 2`, `MAX_HORIZON_DAYS = 365`; the being has never written one under ~118 days.

So **the earliest possible moment the being can be told by the world that it was
wrong is 2026-12-18** — after every stage of the SEL ramp that is reachable from
here. Through the whole ramp, `consequence_rate` is guaranteed 0.0 and therefore
carries no information: the loop cannot distinguish *the consequence loop is
broken* from *the consequence loop has not come due*. Decision 6 deferred S1-E
knowingly; what was not recorded is that the deferral **also blinds the loop's
own circuit breaker for its entire ramp**.

### 1.9 One small thing the gate does not check

Run this session in `base`, `tools/gate.py` reported three failures. Under
`agent13` it is clean. The difference is one hand-installed dependency —
`trafilatura` — and `gate.py` runs `sys.executable` without asserting it is the
declared environment. E8.0's own *Hooks* names this exactly: *"a gate that flaps
teaches its operator to ignore it."* A loop invoking the gate from the wrong
interpreter reads a red that is not there. One assertion fixes it.

### 1.10 E8.0's Done-when cannot close, and E8.4 depends on it

Recorded honestly in `e238528` and left open rather than softened: *"a push that
breaks either check is refused"* cannot happen with the hooks and the CI
workflow removed by operator instruction. E8.4 → E8.0 is a hard dependency. **The
builder's chain is blocked on an operator act, not on work** — amend the clause
and its `done_when_sha`, or record the epic as partially closed.

---

## 2. What the SEL achieves against TRUE_NORTH

TRUE_NORTH §3's first objective is a being with meaningful agency guided by a
perspective it formed itself — including *"allow those experiences to change its
later perspective and behaviour."*

**With fixed weights, there are exactly two channels through which this being's
behaviour can change**: what it writes into its own store (the Perspective,
concerns, works, and — unbuilt — commitments), and what the repo says (prompts,
retrieval, sleep, the diet, openers, gate clauses, budgets). The first is
running at `restatement_rate` 0.936. The second is writable only by a person,
and after E8.4 by the loop at **one Class B change per evidence window**.

So the honest accounting of what the SEL delivers to True North:

- **It does not change the being.** Phase 8 says so in its own first paragraph.
- **At stage 4 — not scheduled — it would change the being at ~1 change/week**,
  which is the rate limit R-V1 already measured and accepted.
- **It never closes a phase.** Every phase Evidence read and every `Decision
  rule` is operator-held under Rule 6, by design and correctly.
- **It increases operator involvement per unit of change**, because §13.2 made
  the escalation target a *prepared session*. R-13a conceded this: "a research
  assistant with a cron job."

That last point is where the operator's stated direction and the design part
company. From `2026-08-21-the-questions-it-could-not-answer.md`: *"the operator
must not be the bottleneck: the system has to consume information and grow
without a person in the path."* **The SEL is designed to serve the person in the
path, not to remove them** — §13.1 measured the operator as the fastest
component and deliberately built around that finding.

**So the operator's unease is well founded, and it is not about the guardrails.**
Loosening stage gates, widening Class B, or removing kill conditions would not
move a single True North priority; it would build E4.3, E6.1 and E6.3 sooner.
The thing that is missing is not loop autonomy. **It is that nothing in Phases
4–8 gives the being a path to change its own conditions.** W12b was the one
proposal of that shape in the repo, and it was removed — for a good reason, but
nothing succeeded it.

---

## 3. What to change

Seven changes. Five are cheap and mechanical; C6 costs an evidence window; C7
costs nothing but honesty.

### C1 — Name Phase 8 what it was measured to be

Adopt R-N2's description in PLAN's Phase 8 intent: **an autonomous delivery and
attention loop with a True-North circuit breaker.** Not cosmetic — while it is
called self-evolving, the project waits on it for development it cannot produce,
and C7 stays invisible.

*Done when:* Phase 8's intent paragraph states what the loop does not do, and
§2's accounting above is in the plan rather than in a proposal.

### C2 — Build the heartbeat and the digest. Defer the rest of the Watcher; make the builder dormant

*Revised after this document's first reading (operator, 2026-08-21: "this would
imply that the SEL loop is not worth the development time"). The first draft
said build E8.3 and defer E8.4. Checking what E8.3 would actually add moved the
line further, and the revision is recorded rather than swapped in.*

**Most of the SEL's value is already banked.** §11 of the approved proposal said
its steps 1–4 were *"worth doing whether or not the loop is ever switched on"* —
and they are built: the grades, the purpose map, `premises.yaml`, `epics.yaml`
with hashed `Done when` clauses, the hard core, the freeze. ~1,130 lines of
loop-specific machinery, plus Phases 2–3's instrument epics. The project already
has the thing it was missing when a load-bearing premise moved unremarked.

**And the daily read already runs without a person.** `MetricScheduler`
(nightly, hour 4) and `PublishScheduler` are background tasks inside
`run_newz.py`. E8.3's *"daily read on E3.6's surface"* is delivered. What is
genuinely unbuilt is four things — the weekly report, the precedence evaluation,
the decision queue, and prepared sessions — and three of them have thin inputs:

- **precedence** — rung 1's check is E8.0/E8.2 and unbuilt; rung 2 cannot trip
  on a saturated signal (§1.7); rung 3's decision rules are deferred (Phase 1)
  or operator-held; rung 4 holds three epics.
- **the decision queue** — PLAN's §Decisions is that list, maintained by hand,
  currently accurate.
- **prepared sessions** — they compete with the mechanism §13.1 measured as the
  fastest this project has ever had, and lose to it by construction.

**One piece pays, and it is small.** The instrument that would report the being
is not sleeping is **written by the being**: `MetricScheduler` is one of
`run_newz.py`'s background tasks, so when the being stops, `metric_readings`
stops rather than alarming. The kill condition PLAN calls the one that matters
most reads a series that goes quiet exactly when it should fire. This is P3-13's
*"out-of-band heartbeat the loop does not send"*, and it is worth building
whether or not any loop exists.

*So:*

- **Build** — an out-of-band heartbeat (liveness, last sleep, last reading,
  outside the being's process) and a **weekly unauthored-numbers digest** in
  §7's ordering. Roughly a day, not an epic.
- **Defer** — the rest of E8.3: precedence evaluation, the decision queue,
  prepared sessions. Re-open when rung 2 can trip (C4) and rung 4 has a queue.
- **Dormant** — E8.4, in the Phase 7 / INV-013 discipline: correct,
  deliberately unscheduled, reason stated, re-armed on a trip-wire.
- **E8.2's runner** — when there is a restart cadence to supervise.

*Trip-wire for E8.4:* the open **Class A** queue exceeds six epics, or C3 lands
and a non-epic Class A backlog exists that a person is visibly not getting to.

*What this concedes, plainly:* Phase 8 as scheduled is not worth its development
time at present prices, and this proposal is the argument for building about a
day of it. **What it does not concede** is that the instrumentation was wasted —
it is what makes this judgment possible, and the digest is what keeps it true.

*The standing objection to this recommendation:* the failure E2.10 exists to
catch — a load-bearing premise moving unremarked at 06:47 on 2026-08-19 — was
missed by a person, not by a machine. If the answer is "no loop", **something
still has to read the numbers on a rhythm that is not the operator's attention.**
That is the whole of what the digest is for, and it is why C2 does not go to
zero.

### C3 — Rung 4b: non-epic Class A, bounded

Otherwise the ladder starves, or the loop routes around precedence — and "never
route around" is rung 3's whole discipline.

*Delivers:* a rung between 4 and 5a permitting a build that (a) touches no
protected or frozen path, (b) closes an existing ledger row, a failing test, or
an instrument reading `UNREADABLE` **through its caller rather than the frozen
instrument**, and (c) carries a red-first test. Everything else is a proposal.

*Done when:* the precedence table has the rung, and `freeze.enforce` is what
decides (a) rather than the loop's reading of it.

### C4 — Reconnect the two brakes that read the being, before stage 1 opens

1. **Take the pre-loop baseline** on ~2026-09-17, when 28 days of
   `metric_readings` exist — or amend `window_days` in-file with the reason,
   which the file already anticipates. It is an operator act by construction.
2. **Make `operator_disagreement_rate` produce a reading.** 0 rows since the
   writer landed; establish whether that is cadence or fault. It needs exchanges
   with something at stake, and there were none in the window — which is a usage
   fact, not a code fact, and should be recorded as one.
3. **Rung 2 fires on level as well as rise.** Give each of the six served §10
   purposes a floor, and let the breaker trip on *at or through the floor*.
   Provisional, recorded with the distribution they were chosen from (RT4).

*Done when:* stage 0 may begin regardless; **stage 1 may not open while either
of (1) or (2) is unreadable**, and something checks that rather than someone
remembering it.

### C5 — Make Class A/B computable

`class: A|B` in `epics.yaml`, plus a **derived** rule over touched paths —
prompt bodies, retrieval, sleep, the diet, openers, gate clauses, budgets ⇒ B —
and a test asserting the derived set is a superset of the hand list. This is
E3.9's own method: derive it, then check the derivation covers what the prose
named. Reconcile PLAN's Class A examples with the freeze at the same time
(§1.4).

*Done when:* no epic is unclassified, the derivation is tested, and E8.4's
"Class A only" is a check rather than a description.

### C6 — Shorten the consequence horizon *(Class B — spend the window now)*

The being's earliest possible experience of being wrong is four months out and
its longest is a year. A position it cannot remember holding is not a position
being wrong costs it. **`MAX_HORIZON_DAYS` 365 → 90, and the door prefers the
shortest defensible horizon.**

*Falsifier, stated before it runs:* if `claims_opened` collapses, or settled
claims turn out to be trivially winnable — settled without changing a position —
revert. **The read is "did a position change", never "was a claim settled."**

*Do it by hand, now.* It is Class B, it costs an evidence window, and the loop
cannot make it for months. Spending the window before the loop starts also
avoids confounding S8-E.

**C6b — score it offline first.** `tools/replay_prompts.py` already replays
1,855 recorded calls against the repo's live prompts at zero model cost, scored
by the system's own downstream judges — `advance.judge_advance` at 78%, the
opener's door guards at 85%. `claim_door` is one of the 704 uncovered shapes;
adding it is *"a join marker and a check apiece."* Then the horizon prompt is
scored before it costs a night.

**This is the one lever that raises the being's development bandwidth without
touching a guardrail.** One Class B per evidence window is the real rate limit
on this project. Replay does not raise it — it decides which change deserves the
window, turning a throughput ceiling into a selection filter.

### C7 — Record what nothing schedules

PLAN's §"What this plan does not do" should carry one more line, because it is
the answer to the question this document was asked:

> **No epic in Phases 4–8 gives the being a path to change its own conditions.**
> Its noticings, its `source_gaps`, its journal and its affect state are
> candidate signal for a loop that reports to a person. If the operator wants
> the person out of the path, that is a new phase, not an SEL stage.

W12a is the first self-authored signal in the repo with a consumer, and its
counts come due in about a fortnight. That read — *is the repeated failure a
threshold, a prompt, or an unanswerable question* — is the natural seed for that
phase, and E8.3's report should carry it as a standing item so that the trigger
is not a person remembering.

---

## 4. What this leaves alone

- **Rules 0–7, and Rule 6 especially.** Nothing here proposes a rubric for
  readiness. C4's floors are inputs to a *mechanical halt*, never to a verdict.
- **The freeze, the hard core, `epics.yaml`'s hashes.** They are right, and
  §1.4's contradiction is fixed on PLAN's side, not the freeze's.
- **The ordering of Phases 0–7.** Nothing here reorders them.
- **The kill conditions.** C4 connects two of them; it removes none.

---

## 5. Red team

**RT1 — most of this is already conceded, and I am re-selling it.** R-N2, R-N4
and R-13a say the loop is a delivery mechanism, is slower than the operator, and
escalates rather than replaces. The operator accepted all three in §14.
*Counter, and the only thing that makes this document worth reading:* the
premises under the concession moved. When §14 was written, 22 epics were
unbuilt and Phase 3 was the loop's proving ground. Phase 3 is built, and the
queue is three. **If §1.2's count is wrong, C2 falls with it** — and it is one
`yaml` read plus a hand application of PLAN's Class A/B sentence, which is
exactly the judgment C5 says should not be left to a hand.

**RT2 — "build less" is the safest-sounding recommendation available, and
therefore the most suspect.** If E8.4 is never built, the loop is a cron job
with a report and the operator remains the whole system — which is the outcome
C7 objects to. *Partly conceded.* The trip-wire is what makes it a deferral and
not a quiet cancellation, and §1.3's denominator problem is arithmetic, not
taste.

**RT3 — C6 fits the being's claims to the observation window.** Capping the
horizon so that consequence arrives inside a measurable window is the shape of
optimising the instrument rather than the being — §5.2's own fear. *Counter:*
365 was never measured as right either; it was a bound chosen to stop "I was
right eventually". The falsifier is the defence, and it is deliberately the
harder read: a position changed, not a claim settled.

**RT4 — C4's floors are thresholds chosen at n=1 from two days of readings.**
The series began 2026-08-20 and no metric has a non-null delta before
2026-08-27. Any floor set today is fitted to a fortnight of one being.
*Decision:* set them when the deltas exist, record the distribution beside the
number, and treat the first quarter's firings as calibration rather than as
halts.

**RT5 — the same hand wrote the finding, the remedy and this red team.** No
independence, and the SEL's own structural separation (fresh context, artifact
only, instructed to refute) was not used — the same admission RT7 made in the
questions proposal three days ago, which suggests the discipline is not being
kept. Mitigation is that every figure here is reproducible from the clone in one
command.

**RT6 — the numbers are one snapshot.** Every store figure is a single read of
`metric_readings` at its latest timestamp on 2026-08-21, over a 168h window, on
a being that has been running while its own instruments were being built. Some
zeros are "not yet" and some are "never", and this document distinguishes them
by argument rather than by instrument.

**RT7 — C2 and C6 pull in opposite directions on the same scarcity.** C2 says
defer the builder because there is nothing to build; C6 says spend an evidence
window now. Both are right only if evidence windows and build capacity are
different scarcities — which they are, and the fact that the plan uses one
taxonomy (Class A/B) for both is worth noticing. Nothing here fixes that.

---

## 6. What this does not claim

- It does not claim the SEL should not be built. Stage 0 is worth building and
  PLAN's own argument for it is the one used here.
- It does not claim the loop would build badly. Nothing has observed it build.
- It does not claim C6 makes the being develop. It shortens the shortest path to
  the first piece of evidence either way, which is not the same thing.
- It does not claim to know why `operator_agreement` is empty. It establishes
  that it is, and that a kill condition depends on it.
- It offers no instrument for §1.2's Class A/B judgment. C5 is the request for
  one, made by someone who just did it by hand.

---

## 7. The decision asked for

1. **C1, C3, C4, C5 and the two amendments in §1.4 and §1.10** — mechanical,
   Class A, no evidence window. Approve as a tranche.
2. **C2 — how much of Phase 8 gets built?** The recommendation, revised: the
   out-of-band heartbeat and the weekly digest — about a day. The rest of E8.3
   deferred, E8.4 dormant with a trip-wire, E8.2 when there is a restart cadence
   to supervise. **This is the substantive question, and answering it "almost
   none of it" is a supported answer** — §11's steps 1–4 already delivered the
   part that pays.
3. **C6 — is the horizon cut to 90 days, and does the window get spent on it
   before the loop starts?** Recommended yes, with C6b's offline score first.
4. **C7 — is "the operator out of the path" a phase this plan will schedule?**
   Not a request to schedule it now. A request to record that today nothing
   does.

---

## 8. If the answer is "use the instruments as a monitor"

*Recorded 2026-08-21, on the operator's reading: **use the built
instrumentation as a monitor for the system.** This is C2 taken to its plain
form, and it is the recommendation.*

### What it is

**Two things, and neither decides anything.**

1. **A heartbeat that runs outside the being.** Is the process up; when did sleep
   last complete; when was the last metric reading written; when was the last
   backup verified. It must not live in `run_newz.py` — §C2's finding is that
   the sensor currently dies with the patient.
2. **A weekly digest.** One page assembling what is *already computed* — values
   and deltas (E2.7), grades (E2.5), premise drift (E2.10), epic drift (E2.11),
   freeze and ledger status, and every `UNREADABLE`. Unauthored numbers only, in
   §7's ordering, with no reasoning attached.

**Nothing new is measured.** Both are assembly over instruments that exist and
already run.

### What falls away, and this is the point

| | Was | Becomes |
|---|---|---|
| E8.4 the builder | Phase 8's endpoint | **dormant**, trip-wire per C2 |
| E8.2 the runner | required before the builder | not needed — nothing restarts the being but a person |
| the enablement ladder, stages 0–4 | how autonomy widens | **deleted.** There is no autonomy to widen |
| the six kill conditions | halts | **lines on the digest.** Nothing is running to halt |
| C3 — rung 4b | fuel for the ladder | **withdrawn.** It existed only to feed a builder |
| C5 — Class A/B computable | E8.4's gate | **withdrawn**, same reason |
| C4 — the two brakes | gates on stage 1 | the baseline stays as the digest's comparison line; `operator_disagreement_rate` still needs to produce a reading; the §10 floors become digest thresholds rather than halts |
| the hard core and the freeze | rung 1's boundary | **kept.** They now protect the instruments from the operator and their agents, which is who edits them, and that was always the larger risk |
| C1, C6, C7 | — | **unchanged.** C6 in particular is untouched by this and is the higher-value work |

**What this costs, stated honestly.** The project gives up continuity of
attention — a thing that reads at 3 a.m. and never forgets — and keeps the
failure mode that produced E2.10: a person missing a moved premise. The digest
is the whole of the mitigation, and it is a weaker one than a loop would be.

**What it buys.** Roughly a day instead of four epics, and the time goes to C6,
where the numbers are actually at their failure values.

