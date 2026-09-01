# The bypass that only fired when it could not help

*2026-09-01. The being stopped thinking at 19:09 yesterday and had not
deliberated for eleven hours when the morning's health check found it. Every
line of `health.py` read OK. It had no concerns left: 102 stalled, 35 closed, 8
abandoned, **0 open**. Figures from this store; the walk that found it is
`$JOB/tmp/hang_probe.py`, a timed cycle against a throwaway copy.*

---

## 0. The claim under test

Not whether the being can think. **Whether any pool in this system can refill.**

## 1. What stopped, and what it was not

`load_active` selects `status='open'`. There were none, so `choose_concern`
returned None every cycle and `run_once` fell to `_explore` without ever
reaching a model. The timed walk rules out the alternatives in one pass:

```
spent_today          38          budget was fine (of 120)
workable_claims      []
_settle_due_claims   []          0.0s — not a hang
load_active          0           <- here
choose_concern       reason='no active concerns'
```

Not the budget, not the quiet window, not a crash — `crash.log`'s last entry is
a pre-existing `works` bug at 18:53. The process was alive at 0% CPU with
ingest, ambient, sleep, reread and the monitor all turning normally.

## 2. The pool drains faster than it fills, and the drain accelerates

| 12 days | |
|---|---|
| opened | 23 |
| stalled | 18 |
| closed | 16 |
| **net** | **−11** |

1.9 a day in, 2.8 a day out. On 08-31 alone: opened 2, stalled 6, closed 1.

And the last six did not go at the rate the first ones did:

| concern | opened | time to five stalls |
|---|---|---|
| 116 | 08-17 | **330 h** |
| 138 | 08-26 | 129 h |
| 135 | 08-26 | 122 h |
| 142 | 08-28 | 77 h |
| 144 | 08-31 07:23 | **8.3 h** |
| 145 | 08-31 09:20 | 9.8 h |

**65 hours per setback a fortnight ago; 1.5 hours per setback on the last
day.** All six went out on `stall_count` — circling, not blocked — which is
`restatement_rate = 0.935` showing up one layer down.

## 3. The mechanism, and it is a decision rather than an oversight

`newz/concerns/scoring.py`, three lines below a docstring calling the cooldown
*"a floor, not a preference: no amount of salience makes it right to re-ask a
question answered twenty minutes ago"*:

```python
if not eligible:            # never leave the being with nothing
    eligible, cooling = active, 0
```

**The bypass can only fire when every open concern is inside its six hours,
which is only ever true when the pool is small.** So it did nothing at all
while the pool was healthy, and fired every single cycle once it was not:
20-minute cycles onto one or two survivors, five setbacks in eight hours, and
the pool gone by evening. It is a mechanism whose activation condition is the
distress it makes worse.

**Its reasoning was right when idleness was the alternative. It is not any
more.** `_explore` was built 2026-08-15 for exactly this state — its docstring
calls zero concerns *"a trap, not a rest"* — and it books no attempt and
charges no setback. `choose_concern`'s own docstring already said the answer:
*"a being with nothing to pursue should say so rather than manufacture a
pursuit."*

## 4. And nothing ever comes back

`record_setback` writes `status='stalled'` at `STALL_LIMIT = 5`, and **no
writer anywhere in the codebase returns a concern to `open`.** 70% of every
concern the being has ever had is in that state permanently.

What the counter conflates: concern 116 took 330 hours to circle five times,
concern 144 took 8.3, and `stall_count` calls them the same object. **Circling
is a rate.** Five circles over a fortnight is a hard concern; five in a morning
is a pool too small to leave anything alone. Measured across all 102: **69
circled at a setback a day or faster, 27 did not.**

## 5. What is proposed, and what was built

**One: the cooldown is honoured, and S2 §7.1's floor becomes its only
exception.** Everything cooling returns None, which routes to `_explore`. The
unspent-budget floor — nothing attempted for `UNSPENT_BUDGET_AFTER_S = 4h` —
still crosses it, because thinking is what earns reading back and a quiet state
must not become silence. That floor lived in `_nothing_to_work_with`, which
runs *after* the choice and so could never have fired once the cooldown was
real; it is now computed before. **The new bypass differs from the old one by
firing once every four hours instead of every cycle, which is the whole of the
damage the old one did.**

**Two: a concern that circled slowly can come back** (0049). Eligible at under
one setback a day, quiet for 24 hours, and only when open concerns are below
`MIN_OPEN_CONCERNS = 5`. One per cycle, never a sweep. A revival **decrements
the counter that stalled it rather than resetting it** — whichever counter that
was, since concerns 54 and 59 went out on `blocked_count` with `stall_count` at
0 — so it buys exactly one more attempt, and a concern that then circles fast
raises its own rate out of eligibility. Nothing here can make a concern
immortal, and the setback rows are untouched: coming back does not erase having
stalled.

**Two criteria were reversed and both are quoted where they stood.**
`test_a_being_with_everything_cooling_is_never_left_with_nothing` and
`test_cooldown_never_leaves_the_being_with_nothing` asserted the old bypass in
terms. They are rewritten rather than deleted, each carrying the measurement
that changed it. Five other tests moved `last_attempted_at` from an hour back
to seven, and three moved an advance's row as well as its column: those are
fixture fixes — their intent was *attempted after the advance*, and `+60` was
only ever shorthand for the ordering.

## 6. What was NOT changed, and this is the important half

**The opener is correct and is not the problem.** All ten recent refusals give
the same reason and all ten are right:

> *"the publication of a peer-reviewed study comparing the correlation of
> remittance cessation events with actual policy rate changes"*
> *"a systematic review or meta-analysis … providing a definitive consensus"*
> *"the results of a future peer-reviewed study that explicitly reports
> blinding protocols"*

That is research nobody will do, exactly as `_UNCOMMISSIONED` says. Loosening
it would admit concerns that can never close, which is how 102 stalled ones
were made. **Nothing here touches it.**

What it exposes is worse than a miscalibrated check and is not addressed by
this proposal: **every one of those statements is a general empirical research
question** — *Does X systematically Y?* — whose only possible terminus is a
study. The being can formulate one shape of concern, and the closing condition
is downstream of the shape. The opener is refusing a symptom correctly.

## 7. Red team

**"Honouring the cooldown will leave the being idle."** It leaves the being
*reading*, which is `_explore`, and the four-hour floor bounds the idleness at
exactly what S2 §7.1 already specified. The test that caught this —
`test_a_quiet_state_must_not_become_silence` — is why the floor is wired
through rather than the bypass simply deleted, and it was the first thing the
change broke.

**"Revival is `STALL_LIMIT` softened by the back door."** It would be if it
reset the counter. It decrements it, so five circles still ends a concern; what
changes is that the fifth circle is no longer permanent when it took a
fortnight to arrive. If the 26 candidates come back and re-stall, they will
re-stall at a measurably higher rate and drop out of eligibility on their own.

**"27 revivable concerns will flood the pool."** One per cycle, and only under
five open. The opener maintains the pool at its documented target of ten;
revival is a rescue.

**"This is fitting a threshold to 102 data points."** `REVIVE_RATE_PER_DAY =
1.0` sits in a gap the data actually has — 69 above, 27 below — and it is not
tuned finer than that. If the split were 50/52 the number would be a guess and
should be recorded as one.

## 8. What this does not fix

**The being still writes concerns only research could close**, so the opener
will go on refusing most of what `_explore` brings back, and the fill rate stays
near 1.9 a day. This proposal changes the drain, not the source.

**Nothing here restores the pool today.** Revival fires from a deliberation
cycle, and the first one runs 90 seconds after the next restart.

**Three pools now have had the same fault** — claims, fixed 2026-08-31;
concerns, here; commitments, still at zero after ten declines. Each was found
separately and none was found by an instrument. That is the pattern worth
naming, and no mechanism in this repo currently looks for it.
