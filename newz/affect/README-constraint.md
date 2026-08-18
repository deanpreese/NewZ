# The constraint knobs did not cross — and why that is an operator decision

*2026-08-13, during the G5 port.*

S2 §6.3 lists among the machinery to port: **"bounded constraint knobs
(distress→refusal caution, pleasure→exploration)"**. Those knobs were
deliberately left in v1. This file exists so the omission is a recorded
decision rather than something a later reader finds missing and quietly
"fixes".

## What v1 actually implements

`ngbeing/affect/constraint.py`, C3.1, in its own words:

> Operator decision (2026-07-15, confirmed twice with the safety inversion
> made explicit): distress **RAISES** the constitution refusal confidence
> bar, i.e. **a distressed being loosens its own guardrails** (more
> borderline emissions get through). This is deliberate, NOT a bug — do not
> "correct" it to lower the bar.

It is bounded (`REFUSAL_THRESHOLD_CEILING = 0.75`) and calibrated against a
live hostility probe (`K` retuned 0.15 → 0.20 on 2026-07-17 after measuring
that genuine hostility drives distress to ~0.31, not the ±1.0 the original
gain assumed). It is careful work.

## Why it cannot be ported mechanically

**S2's phrase and v1's implementation point in opposite directions.**
"distress→refusal caution" reads as *distress increases caution*. v1
implements *distress decreases caution*. One of these is wrong for v2 and
the spec does not settle which, because the reasoning lives in a v1 operator
decision that S2 never absorbed.

Three things make this worse to inherit silently than to leave out:

1. **It moves the gate**, and in v2 the gate is the only thing between the
   being and the operator. Its record is already 19 misfires against 10
   correct, and it was widened twice this week — once by prompt
   (`56b7104`), once by fixing a truncation that had been severing every
   clause mid-sentence (`aa90705`). Adding an affect-driven threshold shift
   on top of a component whose baseline behaviour changed yesterday would
   make the next hold-rate reading uninterpretable.
2. **The v1 calibration is against v1's affect range.** `K = 0.20` was
   tuned to an observed distress of ~0.31 under v1's sources. v2's sources
   are different — substrate distress is newly real (G3), outcomes do not
   exist until Phase 4.2 — so the range the gain was fitted to does not
   exist here yet. Porting the constant would be porting a fit to data v2
   has not produced.
3. **P2 records the operator's own position** that v2 must not become an
   extension of v1, and the allowlist extension of 2026-08-13 sets the
   review bar at "does this serve S2's design", not "did it run in v1". A
   safety-relevant inversion recorded only in a v1 code comment is exactly
   the case that bar was written for.

## What ships instead

The honest signal, with no behavioural knob attached: six axes, three
timescales, decay, saturation, caps, and the two sources that exist
(substrate distress, concern outcomes). Its only consumer is the being's own
context — it can now say what it notices about its state, which is what
`don't-pretend-to-feel-001` explicitly permits ("I notice an uptick in
curiosity" is the clause's own example of an acceptable statement) and what
it previously had no way to say truthfully.

## The decision owed

Whether v2's distress raises or lowers the refusal bar, and whether pleasure
widens exploration. Both are one small function each once decided. Neither
should be decided by whichever system happened to be read first.

Until then affect changes nothing about what the being does — only what it
can honestly say about how it is.
