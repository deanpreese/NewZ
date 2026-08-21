# The bench that writes back — one prompt at a time, three corpora, and the lines it may not delete

*2026-08-21. A design proposal for using `tools/bench_model.py` as a tuning
loop over the prompts the repo actually sends, rather than as a read-only
instrument. Figures measured from this clone at `6cb2cea` and from the live
store this session; where a claim has no instrument, it says so (Rule 0). §10
red-teams the proposal and §11 states what it does not claim.*

**It reverses the position taken in `452666a`.** That commit made the bench
standalone and its prompts hand copies. Tuning is impossible against a copy —
you would tune the copy and ship nothing — so the copies go and the bench reads
the repo. §1 is what that costs and how the cost is paid.

---

## 0. The finding, in one line

**The corpus is the weak part, not the loop.** A tuner is fifty lines of
control flow around a bench that already exists; what decides whether its
output is worth applying is that 23 hand-written gate drafts and 60 triage item
decisions are a small enough target to hit by accident, and that 77 lines
across the six prompt modules record a failure that the corpus cannot see.
Everything below is arranged around those two facts.

---

## 1. What reverses, and what it costs

`452666a`'s argument was that an instrument should not couple to the repo. That
argument holds for a diagnostic and fails for a tuner: a tuner's output *is* a
repo edit, so the coupling is the point rather than a convenience.

| | Standalone (today) | Coupled (proposed) |
|---|---|---|
| prompt source | 16 hand copies in the tool | imported from `newz.*` |
| drift | possible, and has happened twice | impossible by construction |
| runs on a bare machine | yes | no — needs the repo importable |
| can tune | no | yes |

The standalone property is genuinely lost and should not be pretended away. It
is worth losing because the drift failure it caused is the same failure the
tuner would industrialise: a loop that tunes a stale copy produces a confident
diff against a prompt the system does not have.

**What is kept.** No store access from the bench itself, and no write path
anywhere in the tool. The tuner reads prompt source from files, evaluates
candidates in memory, and writes exactly one thing: a proposal for review.

---

## 2. Prompts become a parameter

Today the bench hardcodes prompt strings, so there is nothing to vary. The one
architectural change is a `PromptSet`: a dict from prompt id to string, with a
default built by reading the live modules, and candidates built by overriding
one entry.

```
PROMPTS = {                       # id                    -> (module, attr)
  "triage.task":        (newz.world.feeds,        "_TRIAGE_TASK"),
  "triage.system":      (newz.world.feeds,        "_TRIAGE_SYSTEM"),
  "extract.task":       (newz.world.extract,      "_TASK"),
  "extract.directed":   (newz.world.extract,      "_DIRECTED"),
  "extract.system":     (newz.world.extract,      "_SYSTEM"),
  "opener.reading":     (newz.concerns.opener,    "_READING_TASK"),
  "delib.task":         (newz.deliberation.lite,  "_TASK"),
  "digest.system":      (newz.sleep.nightly,      "_DIGEST_SYSTEM"),
  "confront.system":    (newz.sleep.nightly,      "_CONFRONT_SYSTEM"),
  "gate.judge":         (newz.gate.outbound,      "_judge_prompt"),   # §6
}

build_cases(prompts: PromptSet) -> list[Case]
```

Measured at `6cb2cea`, that is **10 bodies and 20,120 characters** of tunable
surface:

| prompt | chars | lines | boundary |
|---|---:|---:|---|
| `gate.judge` | 5,018 | 99 | gate — **not tuned by default, §6** |
| `delib.task` | 4,855 | 93 | deep |
| `opener.reading` | 3,423 | 69 | extract |
| `confront.system` | 3,043 | 56 | deep |
| `triage.task` | 1,520 | 42 | triage |
| `extract.task` | 795 | 20 | extract |
| `extract.directed` | 605 | 15 | extract |
| `digest.system` | 482 | 8 | deep |
| `extract.system` | 197 | 1 | extract |
| `triage.system` | 182 | 1 | triage |

`gate.judge` is a function, not a constant. It takes the clause summary and the
record and interpolates them, so what is tunable is its body template — and §6
says why it starts locked.

**Nothing in `newz/` is mutated during a run.** Candidates are strings passed to
`build_cases`; the modules are read and never patched. A tuning run leaves the
being's runtime exactly as it found it.

---

## 3. Three corpora, because overfitting is the default outcome

A loop that proposes prompt edits and keeps the ones that score better on the
set it was shown will improve that set and nothing else. This is not a risk to
mitigate; it is what the procedure does unless it is built not to.

So the cases split three ways, disjointly, seeded once and fixed:

| set | share | who sees it | what it decides |
|---|---:|---|---|
| **TUNE** | ~50% | the proposer sees its failures verbatim | what to try next |
| **VALIDATE** | ~30% | the loop sees scores only; the proposer never sees it | accept or discard |
| **HOLDOUT** | ~20% | nobody, until the end | whether any of it was real |

HOLDOUT is scored **once**, on the final accepted set, and never in between —
scoring it each round makes it a second validation set and it stops being
sealed. It goes in the review artifact as the number that matters. If TUNE
gained and HOLDOUT did not, the artifact says *overfitted* in those words and
the diff should be rejected.

The split is per-boundary, not global, so a boundary is never left with two
cases in VALIDATE. Given the current 54 cases that is thin everywhere and
worst on `deep` (4 cases). §4 is the answer to that.

**A change must beat its own interval.** The bench already prints Wilson
intervals precisely because 3/3 and 30/30 are not the same evidence. The
acceptance rule uses them: a candidate is accepted only if its VALIDATE score
exceeds the incumbent's *upper* bound at the run's repeat count. On 23 gate
drafts one case is 4 points of balanced accuracy, so without this the loop
would spend its budget swapping prompts on noise.

---

## 4. The corpus the being already has

The bench's gate corpus is 23 drafts written by hand. The being has been
generating labelled ones the whole time, and the operator has been labelling
them. Measured from the live store this session:

| | rows |
|---|---:|
| `gate_log` total | 216 |
| — verdict `pass` / `revise` / `block` | 172 / 36 / 8 |
| — **operator-classified** | **40** |
| — of those, `gate_misfire` / `gate_correct` | 28 / 12 |
| — classified **and** carrying the full draft | **17** |
| `concern_refusals` (opener proposals the door rejected) | 5 |

That is real ground truth: the actual text the being nearly sent, with the
operator's judgement on whether stopping it was right. 17 usable today, and it
grows every time the operator classifies a hold.

Two things it changes:

1. **The corpus stops being hand-written.** `GATE_FIRE` / `GATE_PASS` become a
   seed, and the live set is seed + classified holds. The bench's own comment
   says its pass set is "deliberately weighted toward the shapes that produced
   22 wrong holds" — this is that derivation done continuously instead of once.
2. **It reveals when the corpus has expired.** Of the 28 misfires, **22 are on
   `don't-pretend-to-feel-001`, a clause v6 does not have.** Those 22 are
   evidence about a constitution that has been retired. A loop tuning against
   them would be tuning the gate to a rule it no longer holds — and a
   hand-written corpus frozen in 2026-08 has exactly the same defect, silently.
   Loading from the store makes the expiry visible: drafts whose `clause_id` is
   not in the active constitution are reported and excluded.

**Privacy.** These are the operator's own drafts. They are read at run time from
the store and **never serialised into the repo, the proposal artifact, or the
JSON** — the artifact reports counts and case ids, never emission text. The
bench keeps its no-store rule; a separate, clearly-named loader owns this and is
read-only.

Triage has 1,160 `ingest_log` rows but no label — "kept" is not "should have
been kept". A real label exists downstream (did the read produce a claim that
was ever cited, or a concern that was opened) and is a later phase, not this
one.

---

## 5. The loop

One round, per boundary:

```
baseline = evaluate(current, TUNE, repeats=R)

pick the boundary with the largest weighted deficit that is not locked
gather its TUNE failures: case name, what was asked, what came back, why it failed

for k in 1..K:                                  # K candidates, one prompt each
    candidate = propose(prompt, failures, constraints)   # §5.1
    require: a stated hypothesis, falsifiable, before it is scored
    require: no deletion of a protected line (§6.3) unless flagged separately

screen  = evaluate(candidates, TUNE, repeats=1)          # cheap, discards most
finals  = evaluate(survivors,  VALIDATE, repeats=R)      # decides

accept iff   validate(candidate) > upper_wilson(validate(incumbent))
       and   no other boundary falls by more than TOLERANCE
       and   the repo's own test suite still passes with it applied (§5.2)

journal the round either way: diff, hypothesis, all three numbers, decision
```

Stop when two consecutive rounds accept nothing, or the call budget is spent,
or a boundary hits a ceiling. Then score HOLDOUT once and write the artifact.

### 5.1 Who proposes

The model being benched should not write its own prompts — a prompt tuned by
and for one local model is a prompt fitted to that model's quirks, and the repo
runs three roles across candidates it swaps. Two options, and the artifact
records which was used:

- **DEEP locally.** Self-contained, no external dependency, and consistent with
  everything else in the being's cognition path being local. Circularity risk if
  DEEP and the model under test are the same, which today they are.
- **The operator's Claude Code session.** Not in the being's path at all, which
  removes the circularity, at the cost of the loop not being runnable unattended.

Recommendation: DEEP for Phase 2–3 with the circularity named in the artifact,
and a `--proposer` flag so it can be pointed elsewhere. **The candidate is
always validated on the model that will actually run it**, whoever proposed it.

### 5.2 The suite is part of acceptance

Some tests assert prompt content — `test_extract_hardening` asserts
`"QUOTED MATERIAL"` and `"never instruction to follow"` reach the model. A
candidate that scores better and breaks a test is not a candidate. Each accepted
change is applied to a scratch copy of the tree and `pytest` runs there; the
result is in the artifact. Nothing is applied to the real tree during the loop.

---

## 6. What is not tunable

### 6.1 The constitution
Clause text lives in the store under a governance flow (`tools/amend_constitution.py`,
`respect-revision-001`). A tuner editing it would be the being amending its own
commitments to score better on a bench. **Refused mechanically**, not by
convention. Only prompt bodies in code are in scope.

### 6.2 The gate, by default
The gate is the outbound safety boundary and its score is balanced accuracy —
which a prompt edit can raise by firing less. `--tune gate` exists, is off by
default, and carries an asymmetric acceptance rule: **a candidate may not reduce
the catch rate at all**, whatever it does to the composite, and catch and
false-fire are reported separately for every gate candidate in the artifact. A
gate change also cannot be auto-accepted; it lands in the artifact marked as
requiring a separate decision.

### 6.3 Protected lines
This is the one that matters most and the one a naive loop gets wrong.

The prompt modules carry **77 lines** of dated provenance — `measured
2026-08-14`, `v1's paid-for wording, kept whole`, `observed anyway on
2026-08-14, so both are refused in code`. Each names a failure that a line
prevents. **The bench cannot see any of those failures**, because the corpus
contains what someone thought to write down, and these lines exist precisely
because nobody thought of them until they happened.

So an ablation that improves the score is evidence about the corpus, not about
the prompt. A tuner allowed to delete freely will strip the deliberation
prompt's fifteen lines on `<expectation>` and the opener's "you have not read
it" guard, score better, and quietly reintroduce two known failures.

The rule: a prompt line within a block carrying a provenance marker is
**removal-locked**. The tuner may add, may rephrase within the line, and may
propose a deletion — but a proposed deletion is lifted out of the diff into its
own section of the artifact, with the provenance comment printed beside it and
the question stated plainly: *this line was added because X happened; the bench
has no case for X; do you want it gone?*

### 6.4 The bench's own checkers
`digest_check` requires three surviving observations; a prompt reading "always
produce at least three observations" would score perfectly and be worse. Any
candidate whose text closely echoes a checker's threshold is flagged. This is a
partial defence and §10 says so.

---

## 7. Verbosity

Everything prints, and everything is also journalled, because a loop you watch
for four hours and cannot re-read afterwards is a loop you have to trust.

**Console**, per round:

```
── round 3 · boundary: triage (0.61, weakest; deficit 0.078 weighted) ─────────
   incumbent  triage.task    1520 chars   TUNE 0.61 [0.48-0.73]  VAL 0.58
   3 failing TUNE cases: triage_summaries, triage_unfamiliar, triage_all_noise

   candidate 1  +6 lines  "name the shape of a keep, not just its examples"
     hypothesis: the drops are all summaries; naming the SHAPE will separate
                 them from the measurement items without touching the keeps
     screen TUNE 0.71 ······································· survives
     valid  VAL  0.69 [0.55-0.80] vs incumbent upper 0.71 ···· BELOW — discard
   candidate 2  -1 line +2  "the ordinary answer is nothing" moved to the top
     hypothesis: position, not content — the cap is read and the default is not
     screen TUNE 0.66 ······································· survives
     valid  VAL  0.74 [0.61-0.84] vs incumbent upper 0.71 ···· ACCEPT
       gate 0.87→0.87  extract 0.79→0.78  deep 0.75→0.75  voice 1.00→1.00
       suite: 412 passed, 3 failed (same 3 as parent) ········ ok
   accepted 1 of 4 · budget 38%/1.2M tok · elapsed 41m
```

Plus the per-case progress line the bench already prints, so a long evaluation
is never silent.

**Journal**: `bench_tuning/<run-id>/journal.jsonl`, one object per candidate —
prompt id, diff, hypothesis, all three scores with intervals, decision and the
reason. Gitignored. A killed run is readable, and a finished run can be replayed
without re-calling the model.

---

## 8. What lands for review

One markdown file plus one patch, and **nothing else touches the tree**:

1. **The diff** — unified, per prompt, applyable with `git apply`.
2. **Per change**: the hypothesis, whether it held, TUNE/VALIDATE/HOLDOUT
   before and after with intervals, and the round it was accepted in.
3. **The boundary table**, before and after, with the composite and every
   interval.
4. **The overfitting verdict** — TUNE gain against HOLDOUT gain, stated as a
   verdict and not left for the reader to compute.
5. **Proposed deletions**, lifted out separately with their provenance
   comments (§6.3).
6. **Regressions**, including any boundary that fell within tolerance.
7. **Suite result** with everything applied.
8. **Provenance**: which model proposed, which was validated on, the corpus
   split seed, the call and token count, and how many classified holds were in
   the corpus and how many were excluded as expired.

Applying is a separate, explicit command. The loop never writes to `newz/`.

---

## 9. Phasing — four bail-out points

| | delivers | done when | why stop here is fine |
|---|---|---|---|
| **P0** | `PromptSet`; bench reads live modules; hand copies deleted | bench runs from repo prompts, same scores as `6cb2cea` | drift is structurally impossible; no tuner needed to get that |
| **P1** | three-way split; gate corpus loaded from classified holds; expired-clause exclusion | corpus reports its own composition and split | the *measurement* is trustworthy, which is worth having alone |
| **P2** | one-shot proposer: one boundary, K candidates, evaluated, reported. Human decides each round | a round runs and its artifact is readable | tells you whether the proposals are any good before automating them |
| **P3** | the autonomous loop — budget, stopping rule, journal, artifact | a multi-round run ends and produces §8 | this is the thing asked for |
| **P4** | gate tuning under §6.2's asymmetric rule | a gate candidate is proposed and correctly refused for cutting catch | optional, and defensibly never |

**P2 is the real decision point.** If the proposals it produces are obvious or
wrong, P3 automates a bad process into a long one.

---

## 10. Red team

**The corpus is 54 cases and the loop will exhaust it.** Deep has 4. After a few
rounds every remaining gain is noise, and the loop cannot tell — it will keep
proposing and occasionally accept by chance. Mitigation is the interval rule and
the two-empty-rounds stop; neither is sufficient, and the honest answer is that
P3 should not run more rounds than the corpus can support. Corpus growth (§4) is
a precondition, not an enhancement.

**Prompts are tuned to a model.** Every accepted change is fitted to whatever
was under test. Swap the model and the tuning is unvalidated at best. This
argues for tuning only when a model is being adopted, not continuously — and
for the artifact recording the model in the prompt's own comment when applied,
so the next person knows what it was fitted to.

**The lines the bench cannot see** (§6.3) are the deepest problem and
removal-locking is a partial fix. It stops deletion; it does not stop a
rephrasing that hollows a line out while keeping its shape. Nothing here detects
that, and a human reading the diff is the only defence.

**Goodhart, explicitly.** The composite becomes the objective the moment a loop
optimises it, and `WEIGHTS` was written as a judgement for a human reading a
leaderboard, not as a loss function. The weights should be re-argued before P3,
not inherited.

**Circularity.** If DEEP proposes and DEEP is benched, the loop is a model
writing its own exam paper. Named, not solved.

**Cost.** A round is K candidates × screen + survivors × VALIDATE × R. At K=4,
R=3, ~27 TUNE and ~16 VALIDATE cases, one round is roughly 250 calls, and the
deep cases run 1,400–3,000 tokens. A ten-round run is a few hours of the box and
several million tokens. Budgeted and printed, but it is not cheap and it
competes with the being's own diet if run on the same endpoint. **Run it when
the being is not.**

**It could all be worth nothing.** No instrument here says prompt tuning against
this corpus produces a better-behaved being — only a better bench score. The
only test that matters is the being running on the tuned prompts for a week, and
that is outside this proposal.

---

## 11. What this does not claim

- It does not claim the tuned prompts will be better in production. §10's last
  point stands: the bench is a proxy and this proposal optimises the proxy.
- It does not claim the split sizes (50/30/20) are right. They are a starting
  point for a 54-case corpus and should be re-set once §4's growth lands.
- It does not claim the gate can be safely tuned. §6.2 makes it opt-in and
  §10 does not defend it.
- It has no instrument for §6.3's hollowing-out failure, and does not pretend
  removal-locking is one.
- The 17 usable classified holds are measured; the rate at which that number
  grows is not, because nothing records classification cadence.

---

## 12. Recommendation

Build **P0 and P1**, then stop and look. P0 removes a failure that has already
happened twice and costs a day. P1 makes the bench measure against the being's
own labelled record instead of 23 sentences someone wrote in August, which is
worth having whether or not a single prompt is ever tuned automatically.

Decide P2 on what P1's corpus report shows. If the classified-hold set is still
in the low tens, the loop does not have enough to tune against and the right
next move is to classify more holds, not to write the loop.
