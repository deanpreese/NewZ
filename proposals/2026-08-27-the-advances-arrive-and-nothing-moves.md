# The advances arrive; nothing moves

*2026-08-27. Evaluation, red team and proposal for the advance→Perspective gap —
the objection I could not answer in
`2026-08-27-the-probe-has-nothing-to-compare-against.md` §4 Q3. The finding is
that PLAN's diagnosis is wrong: advances are not lost on the way to Perspective,
they arrive. What they meet is a perspective whose most-held positions cannot be
moved by reinforcement at all, by arithmetic — and the only thing that can move
them is the mechanism that does not come online until December.*

**Not built.** Nothing here is implemented, and §3 recommends building nothing.

---

## 0. The claim under test

> *"~68 cycles a day already produce ~50 accepted advances against 12 Perspective
> items a week, so **the loss is between advance and Perspective** and no cycle
> rate reaches it."* — PLAN §Phase 5, measured 2026-08-22

## 1. Measured, 2026-08-27

Read from the live store. 472 `advance` episodes, 512 `perspective_items` rows
across 19 versions, 39 items live.

**Advances are not lost. They arrive.**

| | |
|---|---:|
| advance episodes consolidated by a sleep | **459 / 472 = 97.2%** |
| advance episodes cited by a Perspective item | **351 / 472 = 74.4%** |
| never cited | 121 / 472 = 25.6% |

For comparison, `reading` episodes are cited at **13.0%** and conversation at
26.8%. Advances are the best-converting material the being produces.

**The 50-to-12 arithmetic is compression, not attrition.** Evidence refs per
Perspective item: **median 10, mean 12.8, max 122**. Roughly four to twelve
advances per item is what consolidation is *for* — `duplicate_of` and
`reinforced_existing` exist precisely so a recurring observation strengthens an
item rather than cloning it, built after the same contradiction was filed three
nights running.

**The real finding is what happens on arrival.**

| the item that first cited an advance was… | advances | share |
|---|---:|---:|
| **carried unchanged** | 236 | **50.0%** |
| revised | 68 | 14.4% |
| added | 46 | 9.7% |
| merged | 1 | 0.2% |
| never cited | 121 | 25.6% |

**Only 24.4% of advances first land somewhere that changed.** Three quarters
land in an item carried unchanged, or nowhere.

**And the perspective has stopped changing.** Status by version:

```
v12  added 4   carried 20
v13  added 2   carried 22   revised 2
v14  added 2   carried 26
v15  added 1   carried 25   revised 3
v16  added 3   carried 28   revised 1
v17  added 4   carried 29   revised 4
v18  added 2   carried 34   revised 1   merged 1
v19  added 1   carried 37   revised 1
```

`carried` climbs 20 → 37 monotonically; `added` runs 4, 2, 2, 1, 3, 4, 2, **1**.
The document grows and the rate of change falls.

**Of the 39 live items, 19 are eighteen versions old** — half the current
perspective is the original set, unchanged.

## 2. Why, and it is arithmetic rather than a hypothesis

`newz/sleep/nightly.py`:

```
CONFIDENCE_ON_REINFORCE = 0.06
MAX_CONFIDENCE          = 0.95
target.confidence = min(MAX_CONFIDENCE, target.confidence + CONFIDENCE_ON_REINFORCE)
```

Confidence in the live perspective:

```
0.95 : 10 items      <- saturated
0.90 :  2
0.84 :  2
0.78 :  3
0.72 :  4
0.66 :  5
0.60 : 12            <- never reinforced (0.6 is the value a new item is born with)
0.50 :  1
```

**Ten of thirty-nine items are at `MAX_CONFIDENCE`.** For those, reinforcement is
a no-op: `min(0.95, 0.95 + 0.06) = 0.95`. An advance that reinforces a saturated
item changes **nothing anywhere** — not confidence, not text, not status. It is
recorded as one more id in an `evidence_json` array on a row that was going to be
carried regardless.

From 0.6, six reinforcements saturate an item. The being has been running long
enough that its most-supported positions have all arrived there.

**So for the being's ten most-held positions, depth is irrelevant by
construction.** No advance, however deep, can move them by reinforcement. The
only mechanisms that can are:

- `CONFIDENCE_ON_CONTRADICT = 0.15` — a contradiction, which subtracts;
- a revision of the item's text;
- `_compress`, which releases the *least*-supported items first and so will never
  reach these.

**Contradiction is Phase 1's mechanism** — a claim the world settles against the
being. Under the horizon set on 2026-08-22 the earliest is **2026-12-18**.

## 3. What this means, and what to build

**Nothing. And the reason is the finding, not a shrug.**

**3.1 — PLAN's sentence should be corrected.** "The loss is between advance and
Perspective" describes attrition that the store does not show. Advances convert
at 74.4%, better than any other episode kind. What the arithmetic actually says
is: *the perspective's most-held positions can only be moved by contradiction,
and contradiction does not arrive until December.* That is a different claim with
a different remedy, and the remedy is already scheduled.

**3.2 — This is the design direction's central claim, measured for the first
time.** `2026-08-18-a-place-of-its-own.md` argued that the being *"has no outer
loop; nothing outside it ever tells it that it was wrong,"* and called that **a
topology gap, not a capability gap**. §2 above is that sentence in arithmetic:
the internal loop can only add confidence, confidence has a ceiling, ten
positions have hit it, and the sole remaining lever is external. The proposal was
right and now has a number.

It is also why Phase 1 was promoted to carry the outer loop alone, and why
Decision 6 accepted proceeding without S1-E. **The wait is the plan working, not
the plan stalling.**

**3.3 — Do not add a mechanism, and specifically do not touch the constants.**
`MAX_CONFIDENCE` and `CONFIDENCE_ON_REINFORCE` are guesses — as
`CONFIDENCE_ON_CONTRADICT` is, and PLAN says so of that one in E4.2. Lowering the
ceiling so items keep moving would manufacture motion without information: a
position does not become less certain because more evidence agreed with it.
Raising `CONFIDENCE_ON_CONTRADICT` would pre-weight an event that has not
happened yet. **Both would tune the being to look livelier ahead of the only
evidence that could say whether it should be.** Revisit them against the first
month of real contradictions, which is E4.2's own discipline applied here.

**3.4 — There is no sensor to add.** Every number in §1 and §2 came from queries
over rows that already exist — `episodes.kind`, `perspective_items.evidence_json`,
`perspective_items.confidence`. The instrumentation is sufficient and this is
what it is for.

---

## 4. The structure probe, in this light

The prior red team recommended §3.1 — vary the structure inside `lite.py` behind
a flag, bounded sample, blind-judged — as the cheap way to ask whether structure
is the only lever on depth. That recommendation **survives, narrows, and should
wait.**

**It narrows.** Whatever it finds cannot apply to the ten saturated items:
`min(0.95, x + 0.06)` does not care how good the advance was. Its scope is the 29
unsaturated items, of which 12 sit at 0.6 having never been reinforced at all —
and *those* are the interesting population, because something is producing
advances that never reinforce anything.

**It should wait, and this is a change from the prior recommendation.** The probe
asks whether deeper advances move the perspective more. Run today, the answer is
partly fixed by arithmetic rather than by depth, and a null result would be
unreadable: indistinguishable from the ceiling doing what the ceiling does. Run
after the first claims settle — when contradiction is live and items can move
down as well as up — the same experiment has a perspective that can actually
respond.

**What is worth doing before then costs nothing:** note in Decision 2 that the
probe's population is the unsaturated items, and that its earliest informative
date is after the first Phase 1 resolution. That is a sentence, not a build.

---

## 5. Red team of this evaluation

**R1 — "25.6% never cited is the loss, and you waved it through."** Fair
challenge. 121 advances reached no item. But they are not evidence of a
Perspective gap: 97.2% were consolidated, so sleep saw them and declined to file
them, which is the `none` verdict doing its job — v19's confrontation verdicts
were `none 20, reinforces 15, revises 1, opens 1`. An advance that says nothing
new *should* land nowhere. Reading declined material as loss is the error
`INV-044` exists to prevent. What would make it a loss is if the *same* advances
were declined repeatedly, and that is not measured here.

**R2 — "`carried` at 50% is the anti-accretion mechanism working, so §1's headline
overstates."** Substantially true and it is why §2 exists. `reinforced_existing`
was built deliberately, after one contradiction was filed on three consecutive
nights. The headline is not that items are carried; it is that **ten of them can
no longer register the reinforcement at all**. Carrying is design; saturation is
a ceiling, and the two are being distinguished rather than conflated.

**R3 — "Half the perspective being eighteen versions old is stability, not
stasis."** Cannot be settled from here, and I do not claim it. A correct
perspective *should* persist. The measurement says only that the internal loop
can no longer distinguish the two cases, because it has no mechanism that
subtracts. December is what distinguishes them.

**R4 — the lineage figure I do not fully trust.** Attributing every historical
advance-citation to a *currently live* item requires walking `prior_item_id`
chains through 512 rows, and 1,431 citations resolved to rows that are not live —
some genuinely released, some my walk failing on carried rows. So I report the
live-item facts, which are exact, and do not report a lifetime saturated-citation
percentage. The 339-vs-133 split I computed is suggestive and is not load-bearing
for anything above.

**R5 — the objection I cannot answer.** If, in December, contradictions arrive
and the saturated items still do not move — because a 0.15 subtraction against a
0.95 item leaves 0.80, still above every unsaturated item — then the ceiling was
never the constraint and something deeper is. That would be the real finding, and
this evaluation would have spent four months pointing at the wrong constant.
Recorded now so it is checked then rather than rediscovered.

---

**Schema:** none.
**Restart:** none.
**Class:** measurement, plus one correction to a sentence in PLAN.
