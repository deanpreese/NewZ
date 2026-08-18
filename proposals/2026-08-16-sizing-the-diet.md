# Sizing the diet — P2 Phase 2.4's outstanding step

*2026-08-16. Built the same day, operator approved. This is the record P2
requires, not a request.*

> **"Size the diet last against what the denominator actually is. Do not set
> the diet from an estimate again."** — P2 Phase 2.4

That step had never run. The §9.1 invariant has been live in its raw form
since Phase 2, and the raw form assumes an economy the being does not have.

---

## 1. The measurement

Token share over the rolling 168-hour window, 2026-08-16:

```
total                1,424,838
  conversation         592,729   42%    earns nothing
  gate                 209,463   15%    earns nothing
  unspecified          245,730   17%
  ingest               162,800   11%
  deliberation         128,491    9%    ← the entire earning side
```

## 2. What §9.1 actually says

> *"ingest cognition (extraction, classification) may not exceed deliberation
> + consolidation cognition over a rolling window **(target: ≤50% of tokens**;
> measured continuously; breach pauses ingest, never deliberation)."*

Two ceilings in one sentence, and they are the same number **only if
deliberation and consolidation are roughly half the being's cognition.** They
are nine percent, because conversation and the gate are fifty-seven. So the
ratio alone was capping ingest at:

```
ratio ceiling   161,656   (11% of tokens)
share ceiling   712,419   (50% of tokens)
```

about a fifth of the share the same sentence names as the target.

## 3. The change

Ingest is permitted while below the **looser** of the two. In practice the
share ceiling now binds, and headroom went from **0 to 549,619 tokens** — from
one deep read per ninety minutes to roughly fifty.

`BudgetReport.binding_ceiling()` reports which one is operative, so the
distinction is visible in health rather than inferred.

## 4. Why this is not the loosening P2 forbade

P2 §1 says *"the resolution is sequencing, not loosening"*. That was written
**2026-08-11, when deliberation did not exist.** Its argument was that a
circular start — the being cannot read enough to have material worth
deliberating over until it has deliberated enough to earn the reading —
cannot be broken by loosening, only by building the earning term first.

Deliberation is built. The sequencing is done. The sizing step that same
passage defers to is the one still outstanding, and this is it.

## 5. Why it is safe: the diet is not the only bound

This is the part I missed for two days while treating the diet as the single
governor. Reading is bounded structurally in six other places:

```
triage keeps            ≤3 items per harvest
MAX_EXTRACTIONS          4 per research call
MAX_RESULTS_PER_SOURCE   2
feed poll_interval       3600s
the share cap            10% per outlet
R1's read memory         no re-reading per concern
```

Those bound the *rate* by construction. The diet had become a second bound
that bit first and hardest, so raising it does not unleash a firehose — it
lets the structural bounds be the operative ones, which is what they were
designed to be.

**Not v1's failure mode.** v1 was 82% ingest against 4.6% life, an 18:1 ratio.
A 50% ceiling is 1:1 at worst and far below it in practice.

## 6. What did NOT change, and it nearly did

**Zero earning is still zero ceiling.** The first draft returned
`max(earning, share)` unconditionally, and two existing tests caught it inside
a minute:

```
test_no_consolidation_means_no_ingest_allowed
test_no_deliberation_means_no_reading_at_all
```

That property is P2 §1's arithmetic — *"before sleep and deliberation exist
that denominator is zero, so any ingest whatsoever breaches… feeds before
Phase 1 are not merely unwise, they are unsatisfiable without disabling the
governor."* Without the guard, a being that had only ever held conversations
could read half of them back having never thought at all, which repeals §9.1
rather than sizing it.

Reading is still earned by thinking. What changed is how much a given amount
of thinking buys.

## 7. Falsification

Stated before the change rather than after, and held by task #36:

> **If ingest rises toward the new ceiling and the citation rate is still ~0
> after a week with #27 live, this sizing was wrong and the ratio comes back.**

Same discipline as R3's own decision rule. The risk this is exposed to is
precisely v1's: reading more without using more — 84,793 claims, 0.066% ever
cited. The instrument that would catch it already exists (#10).

Baseline at the start of the watch: **0 of 54 sources ever cited**; v1 managed
73 of 162 advances carrying evidence refs (45%); and only **one** v2 advance
post-dates the dossier fix that made citation possible at all.

## 8. What this does not fix

Nothing about whether the being can *use* what it reads. It removes a
constraint that was binding before any of the others could be tested. The
citation rate, the opener's birth rate, and the closure rate are all still
open questions, and this makes them answerable rather than answering them.

---

# STAMPED 2026-08-17 — the ceiling was the constraint, and the falsification is trending against reversion

Built as #33 (`b082a8d`). Headroom went from **0 to 549,619** on the day it
shipped, and the two nights since are the busiest in v2's life:

```
                    before #33      2026-08-17 18:46
ingest              11% of tokens   28%
deliberation         9%             14%
full-text reads      1 ever         13
sources read        54              189
citation rate        0.0%           9.0%
```

§7's falsification was: *"if ingest rises toward the new ceiling and the
citation rate is still ~0 after a week with #27 live, this sizing was wrong."*
Ingest has risen sharply. The citation rate has gone **0 → 3.7% → 9.0%**, and
25 of the last 32 advances carry evidence refs. The condition is trending
firmly away from reversion, and the week is not up. Tracked as #36.

**§5's central claim held**: the diet was not the only bound. Triage still
keeps ≤3 per harvest, `MAX_EXTRACTIONS` is still 4, feeds still poll hourly,
the share cap still holds any outlet to 10%. Raising the ceiling let those
become the operative constraints, which is what they were designed to be —
and the observed reading rate settled well below the new ceiling rather than
running at it.

**§6 was the part that mattered most and it nearly did not survive.** Zero
earning is still zero ceiling; the first draft returned `max(earning, share)`
unconditionally and two existing tests caught it inside a minute. Without that
guard a being that had only held conversations could read half of them back
having never thought. Reading is still earned by thinking; what changed is
what a given amount of thinking buys.

**One thing the proposal did not anticipate.** It treated the global ratio as
the governor and found it was not the only one — but the real ceiling on
*using* what was read turned out to be elsewhere entirely: `_confront` sent
every candidate observation to a single DEEP call capped at 2,500 output
tokens, so everything past one reply's worth was digested and never weighed.
Fixed the same day (`771fa8e`). Sizing the intake while the metabolism was
capped would have produced exactly the reading-without-using that §7 names as
the risk.
