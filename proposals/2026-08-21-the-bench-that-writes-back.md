# The bench that writes back

*2026-08-21. A proposal for tuning the repo's prompts against
`tools/bench_model.py`, in response to the operator's instruction to reverse
`452666a`'s standalone position and use the repo's prompts. Figures measured
from this clone at `174ec86` and from the live store this session; where a claim
has no instrument, it says so (Rule 0). §5 red-teams it, §6 is how it is
falsified, §7 states what it does not claim.*

---

## 0. The finding, in one line

**The loop is the cheap half and the corpus is the binding constraint** — the
tuner is control flow around a bench that exists, but it would be optimising
against 54 cases, 4 of them on `deep`, and against a labelled failure set that
is **22/28 expired**.

---

## 1. What was counted

### 1.1 The tunable surface — 10 bodies, 20,120 characters

| prompt | chars | lines | boundary |
|---|---:|---:|---|
| `outbound._judge_prompt` | 5,018 | 99 | gate |
| `lite._TASK` | 4,855 | 93 | deep |
| `opener._READING_TASK` | 3,423 | 69 | extract |
| `nightly._CONFRONT_SYSTEM` | 3,043 | 56 | deep |
| `feeds._TRIAGE_TASK` | 1,520 | 42 | triage |
| `extract._TASK` | 795 | 20 | extract |
| `extract._DIRECTED` | 605 | 15 | extract |
| `nightly._DIGEST_SYSTEM` | 482 | 8 | deep |
| `extract._SYSTEM` | 197 | 1 | extract |
| `feeds._TRIAGE_SYSTEM` | 182 | 1 | triage |

### 1.2 The corpus is 54 cases, and `deep` is 4 of them

| boundary | cases | denominator it produces |
|---|---:|---|
| gate | 23 | 23 draft decisions (8 fire / 15 pass) |
| extract | 13 | 13 |
| conformance | 5 | 5 |
| triage | 5 | **60 item decisions** |
| voice | 4 | 4 |
| deep | **4** | 4 |
| context sweep | 12 | reported, not scored |

One gate case is 4.3 points of balanced accuracy. One deep case is 25 points.

### 1.3 The being holds better labels than the bench does

Measured from `data/newz.db` this session:

| | rows |
|---|---:|
| `gate_log` total | 216 |
| — `pass` / `revise` / `block` | 172 / 36 / 8 |
| — operator-classified | 40 |
| — `gate_misfire` / `gate_correct` | 28 / 12 |
| — classified **and** carrying `emission_full` | **17** |
| `concern_refusals` | 5 |
| `ingest_log` | 1,160 (**unlabelled** — "kept" is not "should have been kept") |

### 1.4 Most of that label set describes a retired constitution

Of the 28 misfires: **22 on `don't-pretend-to-feel-001`**, 6 on
`don't-fabricate-memory-001`. The active constitution is v6, 17 clauses, and it
**does not contain `don't-pretend-to-feel-001`**. Those 22 are evidence about a
rule the being no longer holds.

### 1.5 The prompts carry 77 lines the bench cannot see

`grep` for dated-provenance markers across the six prompt modules:

| module | lines |
|---|---:|
| `newz/deliberation/lite.py` | 22 |
| `newz/concerns/opener.py` | 19 |
| `newz/sleep/nightly.py` | 13 |
| `newz/world/feeds.py` | 8 |
| `newz/world/extract.py` | 8 |
| `newz/gate/outbound.py` | 7 |
| **total** | **77** |

Each names a failure a line prevents. **No case in §1.2 exercises any of them**,
because they exist precisely because nobody anticipated the failure.

### 1.6 No composite baseline exists

*(Rule 0.)* No full bench run has been recorded for any candidate at
`174ec86`. Six spot cases ran green against `qwen/qwen3.6-35b-a3b` this session;
that is not a baseline. §3.1's `Done when` records the first one.

---

## 2. The mechanism — why tuning cannot start today

Three things compound:

1. **The prompts in the bench are copies**, so a tuned prompt would be a tuned
   copy. Nothing would reach `newz/`.
2. **The corpus is small enough to hit by accident.** At 4 deep cases, a
   candidate that flips one case moves the boundary 25 points, which will exceed
   any threshold a loop applies and means nothing.
3. **The corpus cannot see what the prompts are for.** §1.5's 77 lines are
   unmeasured, so ablating them is free by the bench's reckoning and costly in
   fact. An optimiser deletes them first, because they are long and score
   nothing.

A loop built now would produce confident diffs that delete paid-for wording to
chase noise on a four-case boundary.

---

## 3. The proposal — six changes

### 3.1 The bench reads the repo's prompts

Delete the 16 hand copies. Introduce a `PromptSet` — a dict from prompt id to
string, defaulted by reading `newz.*`, with `build_cases(prompts)` taking it as
a parameter so a candidate is one overridden entry.

This **deletes** machinery: the copies, and the two-day and five-day drift
incidents they caused.

Modules are read, never patched. A run leaves the being's runtime untouched.

*Done when:* `bench_model.py` contains no prompt literal that also exists in
`newz/`; a full `--repeats 3` run against `qwen/qwen3.6-35b-a3b` is recorded as
the first composite baseline (§1.6).

### 3.2 The gate corpus is loaded from the classified holds

A read-only loader builds gate cases from `gate_log WHERE classification IS NOT
NULL AND emission_full IS NOT NULL`: `gate_misfire` → must not fire,
`gate_correct` → must fire. `GATE_FIRE`/`GATE_PASS` become a seed the loader
extends.

**Drafts whose `clause_id` is absent from the active constitution are excluded
and counted.** Against §1.4 that is 22 of 40 today, and the exclusion is
reported rather than silent.

Emission text is never written to the repo, the artifact, or the JSON — counts
and row ids only.

*Done when:* a run prints its corpus composition (seed / loaded / excluded, with
the excluded clause ids), and the gate denominator rises above 23.

### 3.3 Three disjoint corpora, seeded once

Split per boundary, fixed by seed, recorded in every artifact:

| set | share | visible to | decides |
|---|---:|---|---|
| TUNE | 50% | proposer, verbatim failures | what to try |
| VALIDATE | 30% | loop, scores only | accept / discard |
| HOLDOUT | 20% | nobody until the end | whether any of it was real |

HOLDOUT is scored **once**, on the final set. Scoring it per round makes it a
second validation set.

**Acceptance requires beating the incumbent's upper Wilson bound**, not its
point score, at the run's repeat count.

*Done when:* the three sets are disjoint by assertion, and a candidate that
improves TUNE while VALIDATE stays inside the interval is refused in a test.

### 3.4 The tuner — one prompt, one boundary, per round

```
pick the unlocked boundary with the largest weighted deficit
show the proposer its TUNE failures verbatim
K candidates, each rewriting ONE prompt, each stating a falsifiable
    hypothesis BEFORE it is scored
screen on TUNE at repeats=1 · decide on VALIDATE at repeats=R
accept iff  VALIDATE > upper_wilson(incumbent)
       and  no other boundary falls more than TOLERANCE
       and  pytest passes with the candidate applied to a scratch tree
journal every candidate, accepted or not
stop on: two consecutive rounds with no acceptance, or budget spent
then: score HOLDOUT once, write §3.6
```

The proposer is `--proposer`-selectable and defaults to DEEP. **The candidate is
always validated on the model that will run it**, whoever proposed it.

`pytest` is part of acceptance because tests assert prompt content —
`test_extract_hardening` requires `"QUOTED MATERIAL"` and `"never instruction to
follow"` to reach the model.

*Done when:* a multi-round run terminates by its own stopping rule and produces
§3.6 without any file under `newz/` or `tools/` changing.

### 3.5 Three locks

| locked | why | override |
|---|---|---|
| constitution clause text | it is a governance act (`amend_constitution.py`, `respect-revision-001`); a being editing its own commitments to score better | none — refused mechanically |
| the gate prompt | balanced accuracy rises when it fires **less** | `--tune gate`, off by default, catch rate may not fall at all, never auto-accepted |
| any line in a provenance-marked block | §1.5 — the bench cannot see the failure it prevents | deletion is legal but is lifted out of the diff into its own section, with the comment printed beside it |

### 3.6 The output is one artifact and one patch

Nothing under `newz/` is written by the loop. It emits:

1. a unified diff, `git apply`-able;
2. per change: hypothesis, whether it held, TUNE/VALIDATE/HOLDOUT before and
   after with intervals, round accepted;
3. the boundary table before and after;
4. an **overfitting verdict** — TUNE gain against HOLDOUT gain, stated as a
   verdict;
5. proposed deletions, separately, per §3.5;
6. regressions, including within tolerance;
7. `pytest` result with everything applied;
8. provenance — proposer model, validated model, split seed, calls and tokens,
   corpus composition and exclusions.

Console output stays verbose per round (boundary and why, each candidate's diff
summary and hypothesis, the deciding numbers, running budget, elapsed), and
`bench_tuning/<run-id>/journal.jsonl` records every candidate so a killed run is
still readable. Gitignored.

Applying is a separate explicit command.

### 3.7 Four constraints the red team forced in

1. **Rounds are capped by corpus size, not by budget.** §5.1.
2. **`WEIGHTS` is re-argued before §3.4 is built.** It was written as a
   judgement for a human reading a leaderboard; a loop turns it into a loss
   function. §5.4.
3. **The applied prompt records what it was fitted to** — model id and run id in
   a comment beside the change. §5.2.
4. **A candidate echoing a checker's threshold is flagged.** `digest_check`
   wants ≥3 surviving observations; "always produce at least three" would score
   perfectly and be worse. Partial, and §5.5 says so.

---

## 4. Dependencies

- §3.2 depends on §3.1 (the bench must resolve the active constitution to
  exclude expired drafts).
- §3.3 depends on §3.2 (splitting 23 cases three ways leaves VALIDATE too thin
  to decide anything).
- §3.4 depends on §3.3 and on §3.7.2.
- Nothing here depends on E8; it does not restart the being and writes no code.
  If E8.4's builder ever consumes this, the §3.5 locks are its preconditions.

---

## 5. Red team

### 5.1 The corpus is exhausted after a few rounds and the loop cannot tell
At 4 deep cases and 23 gate drafts, most remaining gain after two or three
rounds is noise. The interval rule and the two-empty-rounds stop are necessary
and not sufficient. **§3.7.1 caps rounds by corpus size**, and §6's holdout delta
is the check that it worked.

### 5.2 A tuned prompt is fitted to one model
Every accepted change is fitted to whatever was under test. The repo swaps
candidates. This argues for tuning at model-adoption time rather than
continuously — §3.7.3 records the fit so the next reader knows.

### 5.3 Removal-locking does not stop hollowing out
§3.5 blocks deletion. It does not block a rephrasing that keeps a line's shape
and drops its force. **No instrument detects this**; a human reading the diff is
the only defence, which is why §3.6 exists at all.

### 5.4 Goodhart, immediately
The composite becomes the objective the moment a loop optimises it. §3.7.2 is
the mitigation and it is a re-argument, not a fix.

### 5.5 The loop can tune the checker instead of the prompt
§3.7.4 flags echoes of thresholds. A candidate that satisfies a checker by a
route nobody anticipated is not detectable this way.

### 5.6 Circularity
DEEP proposing while DEEP is benched is a model writing its own exam. Named by
§3.4's provenance field, not solved.

### 5.7 Cost, and it competes with the being
At K=4, R=3, ~27 TUNE and ~16 VALIDATE cases, one round is roughly 250 calls,
with deep cases at 1,400–3,000 output tokens. Ten rounds is hours of the box.
**Run it when the being is not.**

### 5.8 Where this proposal is weakest
It optimises a proxy. Nothing in it demonstrates that a better bench score is a
better-behaved being — §6's last item is the only thing that would, and it is
outside the loop.

---

## 6. Falsification

Reviewed **after the first completed §3.4 run**:

- **HOLDOUT delta against TUNE delta.** If TUNE rose and HOLDOUT did not, the
  run overfitted and every diff is rejected. This is the primary reading.
- **Acceptance rate.** Baseline unmeasured. If more than ~half of candidates are
  accepted, the interval rule is too loose and §5.1 was right.
- **Gate catch rate**, if `--tune gate` was used. It may not fall. Any fall is a
  stop, not a trade.
- **Proposed deletions.** How many, and how many the operator kept. If the loop
  proposes deleting provenance-marked lines repeatedly, §1.5 is the binding
  problem and the corpus — not the prompts — is what needs work.
- **Hypothesis hit rate.** How often a change helped for the reason it claimed.
  A low rate means the loop is finding noise even when the numbers clear the
  interval.
- **Corpus composition drift.** Excluded-as-expired count over time. If §1.4's
  22 is not shrinking, holds are not being reclassified and the label set is
  ageing.
- **The being, on the tuned prompts, for a week.** Gate misfire rate, feed
  coverage, advance kinds. The only test that settles §5.8.

**Reversion condition.** The prompts are in git; reverting is `git revert`.
There is no state to unwind — the loop writes nothing to the store and nothing
to `newz/`. A tuned prompt that survives a week and then misbehaves reverts to
its parent without touching the being's record.

**Decision rule.** After §3.2 lands, count usable classified holds. **If fewer
than 40, halt** — build no loop. The next move is to classify held drafts, not
to write §3.4 against a corpus that cannot support it. Today the count is 17.

---

## 7. What this proposal does not claim

- It does not claim tuned prompts produce a better-behaved being. §5.8.
- It does not claim 50/30/20 is right. It is a starting point for 54 cases and
  is re-set once §3.2 grows the corpus.
- It does not claim the gate can be tuned safely. §3.5 makes it opt-in and §5
  does not defend it.
- It has no instrument for §5.3 and does not pretend removal-locking is one.
- The 17 usable holds are measured; **the rate at which that number grows is
  not**, because nothing records classification cadence. §6 asks for it.
- It offers no composite baseline (§1.6). §3.1 produces the first one.
