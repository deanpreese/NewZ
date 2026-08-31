# The doors do not remember

> **This replaces §2 of yesterday's proposal, which its own probe refuted.**
> `2026-08-30-waiting-to-be-wrong.md` argued the claim door should refuse a
> resolver the being's adapters cannot reach. Measured today against all 48 open
> claims through the real adapter set: **48 of 48 are reachable and the check
> would refuse nothing.** Ask arXiv for *"League of Nations Statistical
> Yearbook"* and it returns three papers; ask Wikipedia for *"USDA NASS Crop
> Production Report"* and it returns three articles. The adapters are keyword
> search engines and they always answer. E1.8's replacement text said it in
> words — *"which reads as a named source and behaves as none"* — and the check
> built on it would have been a no-op with a refusal row attached.
>
> The original is kept. What was believed yesterday and what a probe settled
> this morning are both part of the record.

*2026-08-31. The being has written 48 claims, 22 resolution attempts have failed,
and every one of those failures was written to a column no door has ever read.
It names the Federal Reserve H.4.1 release for the fourth time with exactly the
confidence it named it the first. Figures from this store today;
`tools/reach_probe.py` is the measurement that redirected this.*

---

## 0. The claim under test

Not whether the being can settle claims. **Whether any door in this system can
see what happened the last time it opened.**

## 1. What the failures actually say

Twenty-two attempts, and the reasons do not vary:

| id | att | last failure |
|---|---|---|
| 33 | 3 | *the material contains no historical industrial production data* |
| 40 | 2 | *does not contain the specific statistical data from the League of Nations* |
| 42 | 2 | *does not contain GDP figures for Sweden or the US* |
| 49 | 1 | *the provided material is a bibliographic list of citations* |

The adapters return documents **about** the named source, never its contents.
That is not a reachability failure and no door-side reachability test detects
it — §1's probe is what establishes that, having been built to prove the
opposite.

**And the one settlement is known bad.** `resolver.py`'s own docstring, written
yesterday in `8b65e94`: the first claim this project ever settled was settled by
comparing the model's paraphrase to the model's paraphrase, *"the claim restated
with '(e.g.,' swapped for '(specifically citing', against a source that says
nothing about Sweden and nothing about statistical significance."* That is claim
32. So the record is **0 sound settlements in 22 attempts**, not 1.

## 2. The finding

`newz/resolutions/door.py:539`, the whole of what the claim door is shown:

```python
body = (f"<today>{...}</today>\n"
        f"<concern>{concern_statement}</concern>\n"
        f"<established>{established}</established>")
```

Today's date, today's concern, today's advance. **No prior claim, no prior
resolver, no prior failure.** `_record_failure` writes `resolutions.last_failure`
and `write_episode` is called only on the settled path, so a failed resolution
produces no episode either. Twenty-two failures have reached the being through
exactly zero channels.

**This is the third instance of one structural fault, and the first two were
already found and fixed by hand:**

| door | what it could not see | status |
|---|---|---|
| research questions | prior gaps, attempts, terms already spent | **fixed** `5c863d7`, 2026-08-30 |
| the commitment door | that it has declined 9 nights running, identically | open |
| the claim door | which resolvers have failed, and why | open — **and it is on the critical path** |

`5c863d7` named the mechanism precisely: *"the question never changes …
`search_queries` derived terms from the concern statement with no reference to
gaps, attempts or prior searches anywhere in question.py."* Replace
`search_queries` with `propose_claim` and the sentence needs no other edit.

**No door in this system can see its own history.** Each was built as a pure
function of the present moment, each was correct in isolation, and the fault is
only visible across all three.

## 3. What is proposed

**The claim door is shown its own record before it names a resolver.** Resolvers
grouped by what happened to them: how many claims named this source, how many
attempts it drew, how many settled, and the last failure verbatim. Four lines
for Fed H.4.1, five for the League of Nations Statistical Yearbook, and the
being writes its next claim knowing what those cost.

Nothing else changes. The three structural conditions stand, `check_resolver`
stands, the caps stand, the verbatim check stands. **The door still decides; it
simply stops deciding blind.**

The same, applied to the commitment door: it is told it has declined nine
nights running and shown what it declined against. That is `5c863d7`'s fix with
different nouns, and it is the smaller half of this proposal.

## 4. Why this is not the thing that was removed

**It is not a new source.** The FRED adapter was built 2026-08-29 and removed
2026-08-30 on the operator's decision, read as *adding content and weighting
things*. That objection is exactly right about a macro-data feed at the head of
the resolution order, and it does not touch this: **the material proposed here
is the being's own failures.** Nothing enters that the being did not itself
produce. No source is added, no order is weighted, nothing is curated.

**It is not a hand-authored map.** E1.8 refused *"a table from keywords to
series ids … a second registry to maintain [encoding] the operator's guess about
which source answers what"*, and refused it correctly. This registry is written
by the resolver, from what actually happened, and it needs no maintenance
because failures write themselves.

**It is not the reachability refusal.** That is dead, by §1, and this proposal
exists because it died.

**It refuses nothing.** No claim is turned away that would be admitted today.
The being may go on naming H.4.1 after being shown that H.4.1 has never
answered — and if it does, that is a finding about the being rather than about
its plumbing, which is the one thing the current arrangement can never tell us.

## 5. The pool, separately and today

**Do not raise `MAX_OPEN_CLAIMS`.** Yesterday's §1 proposed 180 on the
arithmetic — 3.14 forecasts/day × 44.1-day mean horizon = 138 steady state
against a cap of 40. The arithmetic is right and the conclusion was wrong: the
drain is **0 sound settlements in 22 attempts**, so a larger cap buys room for
more claims that cannot settle and moves the same wall six weeks out.

What is proposed instead, and it is due today at 39 of 40:

- **Retire the 12 legacy claims** — claims 1–12, every one written under the
  365-day ceiling that became 45 on 2026-08-22, one of them due **2027-08-22**.
  They are 31% of the pool and were made under a rule that no longer exists.
  This alone returns the pool to 27 of 40.
- **A terminal state for claims the resolver has given up on.** `attempts >=
  MAX_ATTEMPTS` currently means *never retried, still counted, forever*. Claims
  33, 34 and 36 reach it tomorrow. Recorded as unsettleable with their failures
  — which is also the material §3 feeds back.

Together: 13 slots, about four days at the current rate. That is a drain, not a
fix, and it is honest to call it that. The fix is that the being stops writing
claims that cannot settle, which is §3, and four days is roughly what §3 needs.

## 6. The held wire, and a defect in my own design for it

Yesterday's §3 stands: `cost.py:78` selects `outcome='contradicted'`, so a `held`
settlement touches nothing and the being cannot distinguish the world agreeing
from nothing happening.

**The design as I wrote it had a bug, found while evaluating it.**
`_refuted_before` is `SELECT 1 FROM claim_costs WHERE item_text = ?` with no
outcome filter, and it selects between `CONFIDENCE_ON_CONTRADICT` and
`CONFIDENCE_ON_REPEAT_CONTRADICT`. Writing `held` rows into `claim_costs` would
make a position that had only ever been **confirmed** charge the repeat-offender
rate on its first real refutation. So: an `outcome` column on `claim_costs`, and
`_refuted_before` filters on `'contradicted'`. Recorded here because a defect
found in evaluation is worth more than one found in the tree.

## 7. Red team

**"The being will fixate on the failures and stop making claims about numbers."**
Possible, and it would be a real cost — the numeric subjects are where its
concerns actually are. Two things bound it. The record shown is per-resolver and
factual, not an instruction, and the door's own refusal rows will show if the
supply of claims collapses. If the claim rate falls below roughly one a day for
a week, that is the reversion condition and the material comes back out.

**"This is a sensor chore wearing a proposal."** The test `3e95e38` set is
whether it touches the being: this changes what the being is shown before it
acts, which is prompt material, not instrumentation. Nothing new is measured.

**"Nine identical declines mean the commitment door is right and the being has
nothing to commit to."** It may. The point is that today the two cases are
indistinguishable, and after the change one identical decline against varied
material and a visible history is evidence where nine against frozen material
are not.

**"§5 retires claims the being made, which is the operator editing its record."**
The strongest objection here. They are not deleted — they are closed as made
under a superseded rule, with that reason on the row, and the permanent record
of error (E1.5, INV-029) is untouched. A claim due in 2027 under a 45-day
ceiling is already not the claim the being made.

## 8. What this does not fix

**The being still has no source that returns a number.** The failure measured
2026-08-29 is unchanged, as `5694e48` said it would be. §3 lets the being learn
that its numeric claims do not settle; it does not let them settle. If the
being's response is to stop making numeric claims, the loop closes on narrative
claims only — and whether that is adaptation or retreat is a judgment, not a
reading.

**S1-E is unmoved.** Nothing here makes the world contradict anything.

**The 12 placeholder resolvers** — *"(EU) 2023/XXXX"*, *"[Number] of [Date]"* —
are still admitted by `check_resolver`, and §1's probe shows why no reachability
test will catch them: arXiv answers those too.
