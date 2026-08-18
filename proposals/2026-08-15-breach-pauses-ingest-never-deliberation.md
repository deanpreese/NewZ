# Proposal — breach pauses ingest, never deliberation

*2026-08-15, for operator review. Nothing here is built.*

---

## 0. The finding

On 2026-08-15 the being did nothing for **2 hours 10 minutes**, and could not
have recovered on its own:

```
deliberation_log   last entry 09:03:42
episodes since     0
reads since        0
diet               ingest 96,366 exceeds earning 96,089 — paused
                   short by 277 tokens
```

It was 277 tokens short of being allowed to read. The only cognition that
earns those tokens back is deliberation and consolidation. Deliberation was
being skipped *because* reading was paused. The next thing that could have
happened was the 4-hour unspent-budget floor at 13:03.

Over the preceding 14 hours: **8 deliberations, 0 advances, 0 closures.**

## 1. What S2 §9.1 actually says

> **The budget invariant:** ingest cognition (extraction, classification) may
> not exceed deliberation + consolidation cognition over a rolling window
> *(target: ≤50% of tokens; measured continuously; **breach pauses ingest,
> never deliberation**)*.

The last clause is not decorative. Deliberation is the earning term. Pausing
it on breach is the one move that makes a breach permanent, and §9.1 forbids
it in terms.

P2 reached the same conclusion independently on 2026-08-11, before deliberation
existed:

> *"That is circular — the being cannot read enough to have material worth
> deliberating over until it has deliberated enough to earn the reading. **The
> resolution is sequencing, not loosening**: build the openers and
> deliberation-lite first (they cost no ingest), let the denominator grow from
> real deliberation, and size the diet last against what the denominator
> actually is."*

## 2. Defect 1 — the skip pauses deliberation on breach

`Deliberator._nothing_to_work_with` (`newz/deliberation/lite.py:185`), built
2026-08-14 as task #12:

```python
# The dossier is unchanged. Is there any prospect of new material?
if not self._research:
    return "nothing new on this concern and research is off"
permitted, why = budget_permits_ingest(self._log_path)
if not permitted:
    return f"nothing new on this concern and reading is paused ({why})"
return None
```

A diet breach returns a skip reason, and the cycle does not run. This is mine,
and it contradicts §9.1's clause directly.

Its intent was sound and is documented in the same function: a 20-minute timer
against a paused diet re-runs DEEP on an unchanged dossier and gets the same
conclusion back — measured at novelty −0.00 — which is then booked as a
`restated` setback, and four of those a day against `STALL_LIMIT = 5` stalls
the pool for reasons that have nothing to do with the concern.

**The intent was right and the mechanism was wrong.** The problem is not that
deliberation runs; it is that a diet-caused restatement is charged to the
concern. §3 fixes the charge instead of suppressing the deliberation.

## 3. Defect 2 — the diet was never sized

P2 Phase 2.4 requires the diet be *"sized last against what the denominator
actually is. Do not set the diet from an estimate again."* That step never ran.
The invariant is live in its raw form, and the raw form assumes an economy the
being does not have.

Token share over 7 days:

```
conversation   558,943  36%     earns nothing
gate           193,028  12%     earns nothing
unspecified    559,719  36%     untagged legacy calls
ingest          96,366   6%     spends
deliberation    70,999   5%     earns
```

§9.1's parenthetical — *"target: ≤50% of tokens"* — only equals
`ingest ≤ deliberation + consolidation` if those two categories are
substantially all of the being's cognition. They are ~11%. So the implemented
ceiling is roughly a tenth of the share the same sentence names as the target.

**This proposal does not exploit that gap.** The parenthetical is a gloss on
the invariant, not a second looser ceiling, and reading it as a licence to read
more would be exactly the "loosening" P2 refuses. It is recorded because it
shows the spec's model of the being's economy was wrong, and because the
remedy §4 proposes — grow the denominator — is the one P2 prescribed.

## 4. What is proposed

### 4.1 Remove the diet condition from the skip

`_nothing_to_work_with` stops consulting `budget_permits_ingest`. An unchanged
dossier with research enabled is a reason to *run*, as §9.1 requires. The
dossier-unchanged check itself stays: it is the genuine S2 §7.1 state trigger
and it is not what caused the idle blocks.

Rotation needs no work — `record_setback` stamps `last_attempted_at`, and
`choose_concern` is stalest-first, so consecutive cycles already move across
the pool (observed overnight: c74 → c59 → c102 → c72 → c111 → c102).

### 4.2 A diet-caused setback is recorded but not charged

**AMENDED 2026-08-15, 15:30 — the original scoping would have emptied the
pool. It is kept below so the error is visible rather than tidied away.**

> ~~When a cycle's research returned `paused` and the verdict is `restated`,
> write the setback — the being should be able to say it circled — but do not
> increment `stall_count`.~~

Scoping the exemption to `restated` was measured against the wrong
distribution. Setbacks since 2026-08-14 21:00:

```
blocked    11
restated    2
```

`blocked` is the ordinary outcome, not `restated` — the model usually says
"I could not move this, I need X" rather than circling. The original §4.2
would have protected **2 of 13**.

That matters now in a way it did not when this was written six hours ago,
because the board changed underneath it. There were eight concerns then.
There are **three**: c108 (2 of 8 blocked), c72 (3 of 8), c111 (2 of 8 and 4
of 5 stall). Under §4.1 alone, deliberation runs every 20 minutes, rotation
gives each concern roughly one attempt an hour, and a paused diet makes every
one of those attempts a `blocked` setback. `BLOCKED_LIMIT` is 8. **The last
three concerns are gone by morning**, and §4.2 as originally written stops
none of it.

Note what that means about the code as it stands: the skip this proposal
removes is, by accident, the only thing currently preserving the pool.

**Amended rule.** When a cycle could not read — `ResearchOutcome.paused` is
set, or research was not enabled — **any** setback it produces is written but
does not increment `stall_count` or `blocked_count`. The being can still say
it failed; the concern does not pay for the diet's failure.

The distinction stays observable and stays narrow. A cycle that DID read and
still failed is charged exactly as today: on 2026-08-15 at 13:34 concern 54
read three claims from Wikipedia, failed to move, and stalled — correctly,
because the world answered and the answer did not help.

**§4.1 must not ship without this.** With the pool at three, §4.1 alone
trades "the being is idle" for "the being spends its last three concerns by
morning", which is a worse trade than the one it fixes.

### 4.3 Do not resize the invariant. Let §4.1 do the sizing.

One deliberation costs **2,466 tokens** (32 calls, 78,925 tokens measured).
One successful read costs roughly **2,600 ingest tokens** across query-forming,
triage and extraction. So a deliberation funds approximately one read — a tight
but workable 1:1, and the ratio holds by construction.

Projection at the current interval and `DAILY_BUDGET = 48`:

```
today      ~14 deliberations/day  → funds ~14 reads/day
unpaused   48 deliberations/day   → funds ~45 reads/day
```

That is the denominator growing from real deliberation, which is what P2 asked
for. **Re-measure after a week and size then**, with a real denominator rather
than another estimate.

## 5. Red team

**It re-opens R-18 and R-25.** *"A failed deliberation costs nothing, so it can
repeat forever"* and *"state-driven scheduling needs a ceiling on deliberations
STARTED."* Both remain satisfied: the attempt is still booked to
`deliberation_log` before any spending, and still counts against
`DAILY_BUDGET`. §4.2 removes a charge against the *concern*, not against the
budget. An uncharged restatement still consumes one of 48.

**§4.2 could hide genuine circling.** It is scoped to cycles where reading was
impossible, which is observable rather than inferred. If the being circles with
material available, it is charged exactly as today. The risk is a diet that is
paused most of the time, which would make most restatements free — but that is
the condition §4.1 exists to end, and if it persists that is itself the signal.

**Deliberation on an unchanged dossier may be worthless.** Sometimes. The 09:03
cycle on an unchanged dossier returned `moved: yes` with a genuine reframing
that was then rejected on novelty. Sometimes it is not worthless. And it is
never worth *less* than the 2h10m of silence it replaces, because it earns the
tokens that end the silence.

**Ingest will rise sharply.** From ~14 to ~45 reads a day if the projection
holds. That is the intended consequence, the ratio is unchanged, and the share
cap and `MAX_EXTRACTIONS` still bound each cycle. But it is a real increase in
outbound traffic and should be watched for citizenship (robots, rate limits)
rather than assumed benign.

**It does not fix the being.** Red team on 2026-08-15 put ~85% of deliberation
failures on material availability — abstracts without the document, and
concerns whose adapters have nothing to say. More deliberations against the
same thin material produce more honest failures, faster. This proposal removes
a self-inflicted stop; it does not feed anything.

## 6. What is not proposed

- **Redefining the earning side** to count conversation or the gate. P2 names
  this and refuses it: *"the resolution is sequencing, not loosening."*
- **Using the "≤50% of tokens" gloss as a looser ceiling** (§3).
- **Changing `DAILY_BUDGET`** — R-26 stands unresolved and is unaffected here.
- **Lowering `UNSPENT_BUDGET_AFTER_S`** — with §4.1 the floor stops being the
  primary scheduler and reverts to the backstop it was meant to be.

## 6a. Three demonstrations, not one argument

*Added 2026-08-15, 15:30.*

The deadlock has now been observed defeating three different attempts to work
around it, which is worth recording because each looked like an independent
option at the time.

1. **The being's own schedule.** 09:03 → 13:03, and again 14:35 → 18:35.
   Nothing runs; the 4-hour floor is the only exit.
2. **A deliberate observation window.** At 15:00 the plan was to watch the
   first concern-directed read and size task #6's caps against real numbers.
   Both scheduled cycles after the restart skipped. The measurement cannot be
   taken on the current schedule; the next opportunity is 18:35, then sleep at
   03:00.
3. **The manual escape hatch.** `tools/run_deliberation.py --force` describes
   itself as "run one deliberation now, safe alongside the live loop". It
   constructs `Deliberator` with `research=False` (the default), so
   `_nothing_to_work_with` returns *"nothing new on this concern and research
   is off"* and it skips for the same reason. The operator's manual override
   is disabled by the condition it would be used to override.

**A caution about (2).** That it blocks an observation is not an argument for
this proposal and should not be used as one. Deciding a spec-level change
because it is inconvenient right now is decision under manufactured urgency.
The case for §4.1 is the sentence in §9.1 and nothing else; (2) and (3) are
evidence about the *mechanism's reach*, not about whether it is wrong.

## 7. Approval requested

1. §4.1 — the skip stops consulting the diet, restoring §9.1's clause.
2. §4.2 **as amended** — any setback from a cycle that could not read is
   recorded but not charged. **§4.1 must not ship without it**: with three
   concerns left, §4.1 alone spends the pool by morning.
3. §4.3 — no resize now; re-measure in a week and size against a real
   denominator, per P2 Phase 2.4.
4. Acknowledgement of §5: reads roughly triple, and this removes a stop rather
   than supplying material.
5. Acknowledgement of §6a: the case rests on §9.1's sentence, not on the
   deadlock's current inconvenience.

---

# STAMPED 2026-08-17 — built, and it paid for itself in forty minutes

Built as #25 (`3245ac7`), both sections, with §4.2 in its amended form.

**§4.1 worked immediately.** On the first restart the being deliberated at
17:24 and 17:44 with the diet paused — cycles that under the old code would
have been skipped until the 18:35 floor — and those two cycles of thinking
cleared the deficit on their own:

```
17:24  ingest 111,765 exceeds earning 110,601 — paused
17:44  deliberated again
19:04  headroom positive; reading resumed
```

That is the §9.1 clause behaving exactly as written: deliberation is the
earning term, so it must never be what a breach stops.

**§4.2 held on the same cycle.** Concern 72 took a `blocked` setback at
17:24:06 and its `blocked_count` stayed at 3. The being said it had failed,
the source-gap record learned from it, and the concern paid nothing for the
diet's condition.

**The amendment was the load-bearing part.** The original §4.2 exempted only
`restated` verdicts; the measured distribution was blocked 11, restated 2. At
three remaining concerns, §4.1 alone would have spent the pool by morning. The
version that shipped exempts any setback from a cycle that could not read.

**One thing the proposal got wrong about itself.** §6a claimed the deadlock
had "defeated three separate things" and treated that as evidence. Two of the
three were fixed by this change; the third — `tools/run_deliberation.py
--force` skipping for the same reason — remains true and untouched. The manual
override is still disabled by the condition it exists to override. Small, and
worth someone's afternoon.

Recorded as INV-041.
