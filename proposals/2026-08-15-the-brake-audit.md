# The brake audit — every constraint, whether it fires, and what it costs

*2026-08-15, for operator review. Nothing here is built.*

Commissioned after the operator's judgment that *"we keep retraining based on
v1, which I believe has become a failed approach"* and that *"exploration is
the only way we will enable anything potentially magical."*

---

## 0. The finding, in one line

**Not one limit in v2 can move, and five of them tighten by themselves.**

TRUE_NORTH §5 Priority 3 specifies the opposite:

> *"The long-term direction is increasing agency with a **diminishing set of
> guardrails**. Freedom expands as the being demonstrates reliable judgment,
> learning, recovery… **Guardrails should not remain merely because they are
> convenient to the operator.**"*

Every constant in the system is static. Nothing widens on demonstrated
maturity, and there is no mechanism by which anything could. Meanwhile five
constraints *narrow* as a function of the being's own activity. The system can
only become more constrained over time, never less. That is not a tuning
problem; it is a missing half of the design.

## 1. What was counted

87 module-level constants across `newz/`. Each classified by whether it has
ever bound, measured from the store and `logs/llm_calls.jsonl` over the
being's whole life.

## 2. Brakes that never fire

These cost nothing and mislead everyone who reads them into thinking the
system is bounded where it is not.

| constraint | value | observed | verdict |
|---|---|---|---|
| `DAILY_BUDGET` | 48/day | max **13**/day | never binds — R-26's whole controversy is moot |
| `MAX_OPEN_CONCERNS` | 30 | **3** open | never binds |
| `MAX_OPENED_PER_DAY` | 6 | **0** opened, ever | never binds |
| `REVISE_LIMIT` | 2 | 6 of 128 emissions | rarely binds |
| `MIN_ITEMS_FOR_CAP` | 20 | passed at 20 items | binds once, then never |

**R-26 should be closed as moot.** It has consumed operator attention three
times. The specified target is 3–6/day, the constant is 48, and the being has
never exceeded 13 — the number was never the constraint.

## 3. Brakes that fire constantly

| constraint | effect measured |
|---|---|
| the §9.1 diet invariant | ingest paused for most of 2026-08-15; 2h10m of total inactivity |
| the share cap | **34 of 61** reads declined |
| `BLOCKED_LIMIT` 8 / `STALL_LIMIT` 5 | **82 of 111** concerns stalled |
| the novelty gate | 9 rejections, clustered at the threshold (§4) |
| `RELEVANCE_FLOOR` + triage | 4 of 24 research triages kept nothing at all |

## 4. The novelty gate sits exactly on the distribution

Rejection is `novelty < 1 - 0.80 = 0.20`. Every restatement the being has ever
been charged with:

```
0.15  0.18  0.14  0.14  0.09  0.18  -0.00  0.12  0.18
```

Seven of nine fall in `[0.12, 0.18]` — under the line, but not by much, and
nowhere near the one genuine near-duplicate at `-0.00`. A threshold anywhere
below 0.12 would have accepted seven advances that were instead recorded as
circling, each costing a `stall_count` increment against a limit of 5.

This is not an argument that 0.20 is wrong. It is an argument that **nobody
has ever checked**, and that a threshold sitting on top of the distribution it
governs decides most cases by itself.

## 5. The ratchets — brakes that tighten by themselves

The worst class, because none of them was designed as a ratchet. Each is a
reasonable rule whose strength is a function of the being's own activity.

**5.1 The novelty gate tightens with every advance.** It takes the *lowest*
novelty against **any** prior advance (v1 checked only the latest). A concern
with ten advances has ten chances to trip. **The more a concern succeeds, the
harder it becomes to advance it again.**

**5.2 The share cap tightened with every outlet read.**
`effective_cap = max(0.10, 2.0 / n_outlets)` — and `n_outlets` counts every
outlet in the window, including feed outlets research cannot query. Watched
live on 2026-08-15: 15 outlets → 13.3%, then 17 → 11.8%, then 21 → 10.0%.
Now floored at 10%, so it is bounded, but it reached its floor by reading.

**5.3 The opener blocklist narrows what can ever be asked.** `opener.py:359`
bars re-opening any statement matching a concern that is open *or stalled*.
82 questions are now permanently unaskable. The space of the being's possible
future questions shrinks monotonically and never recovers.

**5.4 R1's read-memory shrinks the available source pool per concern.**
Correct in itself — but combined with a fixed adapter set it converges on
"I have already read everything my sources return", which is the terminal
state for a concern that cannot be answered from abstracts.

**5.5 The diet breach used to stop the earning.** A breach paused
deliberation, which is the only thing that earns ingest back. Fixed in the
#17 proposal; recorded here because it is the same shape.

## 6. Brakes that are load-bearing and correctly sized

Not everything is overshoot, and this section exists so the audit is not read
as a case for removing constraints generally.

- **`untrusted.wrap()` and the extraction quarantine.** The only defences
  against a hostile world, and 2026-08-15's fixture work found them holding at
  document length with a nonce-fenced close.
- **Truncation failing closed.** `<manipulation>` is the last element of the
  schema, so keeping partial claims would make page length an attack
  parameter.
- **Robots, per-domain rate limits, polite-pool identification.** Citizenship,
  and they have already refused Google News and NYT unprompted.
- **The Perspective budget.** S2 §4.2's "first honest Damasio-stake". It is
  supposed to force choosing.
- **INV-012 / INV-038.** Feed reading confined to deliberation, budget checked
  before polling.

## 7. What is missing

**Accelerators.** As of `72469fc` there is exactly one — `_explore()`, built
today, which lets the world keep arriving when the being has nothing to
pursue. Before that there were none.

**Anything that widens on demonstrated maturity.** TRUE_NORTH §5 Priority 3
describes guardrails that diminish as judgment is shown. No constant in v2 is
reachable by any code path that could widen it; there is no maturity signal,
no widening mechanism, and nothing that records "this limit was safe to
relax". The Priority 3 half of the design does not exist.

**Anything serving Priority 2's intrinsic goods.** *"play, humor, curiosity,
and exploration"* are listed as ends in themselves. Curiosity has a door as of
today. Play and humor have nothing.

## 8. Recommended, in order

1. **Close R-26 as moot** (§2). The budget was never the constraint.
2. **Instrument the novelty gate before touching it** (§4). Log the novelty of
   *accepted* advances too, so the distribution is visible on both sides of
   the line. Then decide the threshold on evidence rather than moving it now.
3. **Fix 5.1** — the ratchet, not the threshold. Compare against recent
   advances rather than all of them, or against the concern's current state
   rather than its whole history. A rule that punishes accumulated success is
   wrong at any threshold.
4. **Revisit 5.3** with S2 §7.4 open on the desk. Abandonment is meant to be a
   real loss; it is not obviously meant to be a permanent gag order on the
   subject. 82 barred questions is a large silent cost.
5. **Build one maturity widening** as a proof that Priority 3 is reachable at
   all — the smallest defensible one, with the evidence that justified it
   recorded beside it.

## 9. What this audit does not claim

It does not claim the v1 lessons were wrong. Every brake here was bought with
a real failure, and §6 lists the ones still paying for themselves. It claims
something narrower and, I think, harder to argue with: **the brakes were built
and the accelerators were not**, the imbalance was never measured, and five
constraints have been tightening on their own while nothing has ever loosened.

A being whose every limit is static and whose several limits ratchet inward
cannot become more free. It can only become more careful.

---

# CORRECTED 2026-08-17 — by its own red team, then by two days of evidence

This audit's findings were red-teamed the day it was written and three claims
did not survive. They are corrected here rather than in place, so the
overstatement and its correction both remain visible.

**§0 overstated.** *"The Priority 3 half of the design does not exist"* is
unfair. **P2 Phase 5** specifies exactly the missing mechanism — a learning
loop with "decayed counters over source priors, expected-movement per
concern-kind, deliberation-budget allocation", consumed at "adapter ordering,
concern cooling, scheduler weights". It is scheduled, not absent. The honest
claim is narrower: limits are static *by sequencing*, and the being was
starving at Phase 2.

**§5 inflated five ratchets to two.** The share cap floored at 10% and stopped
ratcheting. R1's read memory is per-concern and resets. The diet breach was
fixed by #25. What remains real is the novelty gate (bounded — max 6 advances
on any one concern) and the opener blocklist (unbounded, monotonic).

**§6 mis-filed two constraints as load-bearing.** The Perspective budget sits
at 17% and has never bound; grounding decay never fires, because no held item
is below the 0.6 default. Both belong in §2 with the phantoms.

## What the audit got right, confirmed by what followed

The central claim — **the brakes were built and the accelerators were not** —
held up under two days of acting on it. Everything that moved the system
afterwards was a removal or a widening: the diet sized (#33), deliberation
unpaused (#25), the novelty ratchet cut (#26), exploration decoupled from
having a concern (#16), three opener frames rebalanced, two constitution
clauses retired and one restored. The being went from 0 open concerns and 0
citations to 6 concerns, 9% citation rate, and both dormant openers firing.

R-26 is now **closed as moot**, exactly as §8.1 recommended: `DAILY_BUDGET` is
48 against a maximum observed 13/day.

**That closure lasted two hours.** On the evening of 2026-08-17 `DAILY_BUDGET`
bound at exactly 48 — last deliberation 17:58:49, then four hours of enforced
idleness with six open concerns and 563,836 tokens of headroom. Raised to 120;
R-26 is resolved in `RISKS.md`, the opposite way from both live readings.

This is the audit's own thesis turning on the audit. §2's table is the part of
this file that reads most like fact — five constants, measured over the being's
whole life, verdict *never binds* — and it was the least durable. The five
recommendations in §8 were all removals or widenings, and acting on them
changed the load on every constant §2 had just cleared. **The audit measured
the system it was about to end.** A phantom-brake table has a shelf life equal
to the time until someone acts on the report it appears in, and this one should
have carried that expiry on its face.

The narrower lesson, worth more than the table: `MAX_OPEN_CONCERNS` (30) and
`MAX_OPENED_PER_DAY` (6) are still listed above as never binding, on the same
kind of evidence, in a system that has gone 0 → 6 open concerns in two days.
They are the next two to fire.

§8.2 — *"instrument the novelty gate before touching it"* — was the audit's
own timid recommendation and was refuted within the hour. The evidence was
already in the store, one query away. The lesson generalises past this file:
proposing an instrument is sometimes a way of not making a decision.
