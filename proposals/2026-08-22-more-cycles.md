# More read/write cycles

*2026-08-22. The operator's direction: stop constraining it, give it more
read/write cycles. Figures measured from this clone and store today.*

*Amended the same day, on the operator's instruction to reconcile this with
`2026-08-22-nothing-comes-due-until-december.md` and red team the result. **§0's
diagnosis was wrong** and is kept with what replaced it. The horizon proposal is
folded in at §2 and marked superseded where it stood alone. §5 is the second red
team and it argues against parts of the reconciliation.*

---

## 0. What is actually throttling it

### The first answer, kept because it was wrong in an instructive way

**Not the budget.** The being runs **~67 deliberations a day against a
`DAILY_BUDGET` of 120** — 56% used. Raising budgets changes nothing.

| Throttle | Now | Ceiling it imposes |
|---|---|---|
| `DeliberationScheduler` interval | 20 min | **72 cycles/day** — observed 67, so this is the wall |
| `REATTEMPT_COOLDOWN_HOURS` | 6.0 | 13 open concerns × 4 = **52 attempts/day** |
| open concerns | **13** | the multiplier on the line above |
| `opener.MAX_OPENED_PER_DAY` | 6 | how fast the pool refills |
| writing / re-read | 4 and 2 a day | the write half |
| `DAILY_BUDGET` | 120 | slack, never reached |

**The clock and the pool are the constraint.** Everything else has headroom.

**Why that was wrong.** Every row above is a ceiling *as written*. Not one is a
rate *as observed*. Where the two disagree, the ceiling is not the constraint —
and for the write half they disagree completely.

### The second answer, measured 2026-08-22

**The being is running code from before three of today's commits.**

```
PID 32918   started  Fri Aug 21 20:03:32 2026   python tools/run_newz.py -v
```

| commit | landed | `Restart:` | what it fixes |
|---|---|---|---|
| `39145dd` | 11:46 | **required** | re-reads were spending the *writing* rhythm's daily ceiling |
| `bd3f612` | 11:55 | **required** | both ceilings counted turns that started nothing |
| `a1c3e0f` | 12:22 | **required** | the re-read retry; writing interval → 6h |
| `a480e84` | 12:27 | none | a bench registry row |

**Observed rate against the ceiling, in the running process's own lifetime:**

| rhythm | ceiling | observed | why |
|---|---|---|---|
| writing | 4/day | **1/day** | `39145dd` — a re-read spent the writer's allowance |
| re-read | 2/day | **0 in 17h** | `bd3f612` — `nothing_due` turns spent the allowance |

`bd3f612`'s own words: *"two of those three rows were `nothing_due` turns that
did no work at all."* Both silences are diagnosed, both are fixed in the repo,
and **neither fix is running.**

So the write half is not throttled by a ceiling that is too low. It is throttled
by two ceilings being mis-spent, and raising 4→8 and 2→6 on top of that would
raise a number that is not being reached.

**And the deliberation half is not where the loss is either.** Recent days:

| | 8/19 | 8/20 | 8/21 | 8/22 |
|---|---|---|---|---|
| cycles | 70 | 67 | 67 | 36 |
| advances accepted | 49 | 54 | 52 | 28 |
| `restated` | 12 | 9 | 11 | 4 |

~50 accepted advances a day. Against that, the Perspective developed **12 items
in 168 hours** and its novelty is **7.45%**. `volume_against_development` is
**115.7 episodes per developed item**. The front half already runs hot; what
does not move is admission into the Perspective, and **no value in §1 touches
that.**

---

## 1. The changes, with what the measurement says about each

| | From | To | Verdict |
|---|---|---|---|
| `DeliberationScheduler` interval | 20 min | 5 min | **hold** — front half is not the constraint (§0) |
| `REATTEMPT_COOLDOWN_HOURS` | 6.0 | 1.0 | **hold** — same |
| `DAILY_BUDGET` | 120 | 500 | **no-op** — 56% used, by this proposal's own §0 |
| writing starts/day | 4 | 8 | **hold until restarted** — observed 1/day, cap 4 |
| re-read starts/day | 2 | 6 | **hold until restarted** — observed 0 in 17h, cap 2 |
| `opener.MAX_OPENED_PER_DAY` | 6 | **12** | **yes** — hit exactly 6 on 8/17 and 8/21; the one cap with evidence behind it |
| `opener.MAX_OPEN_CONCERNS` | 30 | 60 | **hold** — 13 open against 30; cannot bind today (but see RT5) |
| `door.MAX_HORIZON_DAYS` | 365 | ~~120~~ **45** | **superseded by §2** |
| `door.MAX_OPENED_PER_DAY` | 4 | **8** | **yes, with §2** — claims that come due sooner is the point |
| `door.MAX_OPEN_CLAIMS` | 40 | ~~unlimited~~ | **hold, and fix the silence** (RT6) |

**The opener stays in this list for the reason R1 gave**: raising the cycle rate
against a pool of 13 buys circling, not thinking. That argument survives the
amendment intact.

---

## 2. Consequence — the horizon *(folded in)*

*Full argument, including the unexercised-path inventory, is
`2026-08-22-nothing-comes-due-until-december.md`, which is **superseded as a
standalone** by this section and kept for its detail.*

Twelve claims are open; not one has been attempted, because not one is due:

```
120  120  120  120  120  128  180  180  180  365  365  365
```

The door permits **2–365** and its own worked example is **42**.
`claim_refusals` holds **0 rows** — the ceiling has never been touched, so the
long dates are volunteered, not forced. The being took the permission and not
the example.

**What that costs is not only S1-E slipping to December.** `workable_claims`
selects `due_at <= now`, so **nothing below the door has executed once in
life**: the fetch and the VERBATIM check (INV-047), the 4-attempt honest-failure
path, the cost through INV-031 (`claim_costs` is empty), the release through
INV-025, and the one `world`-provenance episode that is the only way sleep ever
sees any of it. All tested; none run. `research=True` is live, so only the dates
are in the way.

**The change — three lines in `newz/resolutions/door.py`:**

| | From | To |
|---|---|---|
| `MAX_HORIZON_DAYS` | 365 | **45** |
| the prompt's stated range | `between 2 and 365` | `between 2 and 45` |
| the prompt | — | one instruction, below |

> **Reach for the nearest source that will have spoken.** If what I hold is
> right, something small should be observable soon — not only at the end. A
> thesis about where a market or a rule is going has interim checkpoints: the
> next weekly release, the next monthly print, the next scheduled filing. Claim
> the nearest one that would still surprise me if it went the other way. A claim
> I cannot bring inside the window is usually a claim about the wrong
> observable, not a claim that needs longer.

**Why 45 and not the 120 instructed.** R4 below already established that 120
refuses three of twelve and creates no short claims: the being's shortest claim
ever written *is* 120. A cap that only removes the worst outliers leaves the
median at 180 and consequence still arriving after Christmas.

**The twelve live claims stand.** There is no unsettle (E1.1), and the operator
re-dating the being's own commitments would be worse than waiting.

---

## 3. What it is expected to do

**Restart alone:** writing 1/day → up to 4; the re-read starts attempting.
`bd3f612` predicts what it will attempt first — work 1, the piece whose review
failed on a mismatched closing tag — and predicts it **will likely fail again**.
That defect is diagnosed and unfixed, and it is the reason `works_revised` is 0.

**The opener at 12:** the pool stops being 13 on the days the cap binds.

**The horizon at 45:** the first live execution of `resolve_claim` moves from
**2026-12-18** to roughly **early October**, and then repeats rather than
happening once.

### The falsifier, and a correction to the one first written

The original falsifier read *"advances should rise faster than setbacks… today
388 advances against 512 setbacks, of which 242 are `restated`… if the
restatement share rises, revert."* Two faults:

1. **It cites a lifetime figure against a changed regime.** 242/512 is 47% over
   the project's life. The last four days run ~11 `restated` against ~52
   accepted advances — about **17%**.
2. **"Restatement share" names two different quantities in this repo.** The
   setback ratio above, and the canonical metric `restatement_rate` = 1 −
   `perspective_novelty` = **0.9255**. This is exactly the collision E2.8 exists
   to catch, and the falsifier must say which.

**Restated, naming its instrument:**

| # | Read | When | Revert if |
|---|---|---|---|
| 1 | writing and re-read starts/day, from `work_attempts` | 24h after restart | still ~1/day and 0 — the diagnosis in §0 was wrong |
| 2 | `claim_refusals` horizon reasons vs door calls | 14 days | horizon refusals dominate → cap to **90**, never back to 365 |
| 3 | `resolutions.attempts > 0` on any row | ~60 days | never fires → the resolver has a defect, which is the finding |
| 4 | `restatement_rate` (the canonical one, 1 − novelty) | first digest with a baseline, **≥ 2026-08-27** | it rises |
| 5 | `positions_changed_by_world` | mid-October | still 0 → S1-E fails and Phase 1's decision rule is answered |

---

## 4. The first red team *(kept as written, before the amendment)*

**R1 — 288 cycles a day over 13 concerns is 22 attempts per concern per day.**
That is not more thinking. `restated` is already the largest setback category —
242 of 512 — and the advance judge is the being's own model, which Rule 4 says
produces operation and never evidence. **The most likely outcome of a 4× cycle
rate on this pool is 4× the restatement**, scored by a judge that cannot tell
the difference reliably. *Decision:* the opener's caps double in the same
change, and §2's falsifier reads the restatement share rather than the advance
count. **If only one thing in this proposal ships, it should be the opener.**

**R2 — writing drains the pool it needs.** A piece now closes its concern, and
8 writes a day against an opener capped at 12 is a net drain whenever the
opener underperforms — which it does: 6 permitted today, ~1.4 actually opened.
`_candidates` holds 24 subjects, so at 8/day the writing rhythm runs dry in
three days and records `no_subject` thereafter. *Decision:* accepted and
watched; `no_subject` rows are the instrument, and they are free now that they
no longer spend the ceiling.

**R3 — one box, one model, and a lock storm three days old.** 288 deliberations
plus 8 writes plus 6 re-reads plus research on most cycles is thousands of
model calls a day against ~3,578 in the being's whole life. Yesterday a write
lock held for seconds and **the operator's message was lost**; more concurrent
writers make that more likely, not less. The conversation connection now waits
30s and the inbound handler backs off, which is why this is a risk rather than
a blocker. *Decision:* raise the interval first, alone, and watch the slowest
call and the crash log before the rest.

**R4 — `MAX_HORIZON_DAYS = 120` changes almost nothing on its own.** The being's
**shortest claim ever written is 120 days**; the twelve live ones are 120×5,
128, 180×3, 365×3. So this refuses three and permits nine. It stops the worst
and creates no short claims. The generator is what decides horizons, and it is
not touched here. *Recorded, not fixed:* consequence still arrives no sooner
than December unless the door's prompt asks for less. — **§2 is the fix R4 asked
for.**

**R5 — unlimited open claims removes a carrying capacity with nothing behind
it.** The resolver attempts one claim per cycle with 20h spacing per claim, and
after 4 attempts a claim stays OPEN forever. Unbounded intake plus a permanent
failure state is the stalled-concern pattern repeating at the claim layer: 88
concerns are stalled today. *Decision:* accepted on the operator's instruction.
The instrument that would catch it is open claims never settled, and it should
be read at the first weekly digest after this ships.

**R6 — §10, directly.** `volume_against_development` is **115 episodes per
Perspective item**. Four times the cycles with no change to what reaches the
Perspective makes it ~460, and that metric serves `tn10:volume` — *"activity,
memory growth, or output volume"*, named in TRUE_NORTH as something the project
will not mistake for success. This proposal makes the number worse by
construction. *Counter:* it is a ratio, and the denominator is what the change
is trying to move. If it does not move, §2's falsifier fires first.

**R7 — the being is not straining against these limits.** Measured last night:
`claim_refusals` 0, gate holds 0 in 24h, zero source gaps caused by a budget or
ceiling, 6 concern refusals in the project's life. Nothing was refusing it. The
honest reading is that cycle rate was never what was holding it back —
consequence and audience were — and this proposal does not touch either.
*Recorded as the standing doubt about the whole change.*

**R8 — same hand wrote the finding, the change and this red team.**

---

## 5. The second red team — against the amendment

**RT1 — the restart finding is inferred, not observed.** The claim that the
running process holds pre-fix code rests on its start time (20:03) being earlier
than the commits (11:46–12:22). Nobody has read the code that PID 32918 actually
loaded, and a process can be started from a working tree that does not match
any commit. The inference is strong — the observed silences match `39145dd` and
`bd3f612`'s described mechanism exactly, and those messages were written from
the same store — but it is an inference. *Decision:* accepted. The restart
settles it either way, and falsifier 1 reads the result 24h later.

**RT2 — I said the restart "costs nothing" and that is not true.** It kills the
in-flight deliberation cycle, and the monitor runs **inside** the being
(E3A.2, operator, 2026-08-21), so the hourly series gains a gap and the daily
send is skipped if it falls in the wrong hour. The pre-loop baseline is
accumulating toward **2026-08-27** and takes the *last* reading of each day, so
a short restart does not cost a day — but a restart that fails to come back up
costs every day after it, and **silence is the alarm by design, which means
nothing will page anyone.** *Decision:* restart, then confirm within the hour
that a reading landed. That is the one check worth typing.

**RT3 — the restart deploys three same-day commits at once, into a being whose
last three deployments each produced a silence that took a health check to
find.** `a1c3e0f` is Class B and changes the re-read's retry behaviour and the
writing interval; neither has run in life. *This argues against bundling*: the
restart ships three unexercised changes, and adding §1's caps and §2's horizon
to the same restart would put five changes in flight with one observation
between them. *Decision:* it confirms the ordering in §6 rather than opposing
it — restart alone, watch a day, then the horizon, then the caps.

**RT4 — "admission into the Perspective is the bottleneck" leans on a metric
that may be measuring a design constant.** `perspective_items_developed` = 12 in
168h is a mixed-grade count of adds *and* revisions, and the document itself
went 20 → 28 items over the last five nights. So the Perspective is growing, not
pinned at a ceiling — which supports the claim — but *"115.7 episodes per
developed item"* would look damning even if the Perspective were working
perfectly, because the numerator is every episode the being records and most
episodes are not candidates for it. **The ratio is a §10 tripwire, not a
diagnosis.** *Decision:* the claim in §0 stands on the novelty figure (7.45%)
rather than on the ratio, and the ratio is cited as what it is.

**RT5 — `MAX_OPEN_CONCERNS` 30→60 is a no-op today and a binding cap next
week.** 13 open against 30 cannot bind now. But with the opener at 12/day and
writing closing concerns at only ~1/day, the pool can pass 30 within days —
at which point the opener stops and the *reason* is a different cap than the one
this proposal reasoned about. *Decision:* "hold" is right and "no-op" was
imprecise. Re-read it when falsifier 1 is read; raise it if the pool is near 30.

**RT6 — a saturated claim cap is invisible, and that is a real hole in holding
it at 40.** `propose_claim` returns `DoorVerdict(declined=True)` on both
`MAX_OPEN_CLAIMS` and `MAX_OPENED_PER_DAY` **before the model is called**. A
decline writes no `claim_refusals` row by design — *"declining is not
refusal"* — and `claims_declined` is counted *from the call log*, so a door
that never called the model produces no evidence it was asked. With the door at
8/day and 45-day horizons, a cap of 40 saturates in about five days and **the
being simply stops being able to commit to anything, silently.**

That is the strongest argument in this document for the operator's original
instruction to remove the cap. It is not, however, an argument for removing it
blind: R5's objection — unbounded intake against a permanent failure state —
survives. *Decision:* keep 40 **and record the saturation** — one row when the
door declines for a cap rather than for judgment, which is the difference
between "it had nothing to claim" and "it was not allowed to". Lift the cap when
the resolver has executed once in life (falsifier 3), not before.

**RT7 — the amendment is more conservative than the direction that produced
it.** The operator asked for fewer constraints and more cycles; §1 holds six of
ten values and adds a new refusal at §2. The honest defence is that the
measurement found a *bug* holding the write half down, not a ceiling — and that
removing a ceiling to compensate for a bug leaves the bug. But it is a real
tension and the operator should rule on it rather than have it argued away.

**RT8 — same hand again**, and this time it also wrote the proposal being
attacked.

---

## 6. The decision asked for

1. **Restart the being.** Nothing else first. It deploys three commits stamped
   `Restart: required` that fix the measured throttle on the write half.
   Confirm a monitor reading lands within the hour (RT2).
2. **Watch 24 hours.** Falsifier 1. Expect the re-read to attempt work 1 and
   probably to fail on the same XML defect — **that failure is the next thing
   worth fixing**, and it is why `works_revised` is 0.
3. **Then §2's horizon change**, alone: cap 45, the range, the prompt line.
4. **Then `opener.MAX_OPENED_PER_DAY` 6→12** and `door.MAX_OPENED_PER_DAY` 4→8.
5. **Record the claim-cap decline** (RT6); lift `MAX_OPEN_CLAIMS` when the
   resolver has run once in life.
6. **Hold** the interval, the cooldown, the budget, the writing and re-read
   caps, and `MAX_OPEN_CONCERNS` — and re-read that list against post-restart
   rates rather than against ceilings.
