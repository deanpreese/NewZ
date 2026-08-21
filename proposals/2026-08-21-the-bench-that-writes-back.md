# The bench that writes back

*2026-08-21. A proposal for using `tools/bench_model.py` to understand and tune
the prompts the repo actually sends, against the inputs it has actually sent
them. Figures measured from this clone at `65be881`, from `logs/llm_calls.jsonl`
and from the live store this session; where a claim has no instrument, it says
so (Rule 0).*

**Supersedes this document's first three drafts.** The first was prose. The
second specified an artifact, a patch, a journal and a scratch worktree — a
release pipeline, not a diagnostic. The third dropped those but still invented
its own corpus. The third also kept phases, hand-running and a
per-boundary decision the operator was expected to make; those are gone too
*(operator, 2026-08-21: "does this leverage current prompts and LLM input and
output from the repo" … "all of this should happen without my intervention")*.
**One command, unattended, one diff at the end.**

---

## 0. The finding, in one line

**The corpus already exists and the bench was not using it** — 2,559 recorded
calls carrying full prompt and full response, against 54 cases written by hand,
two of which measure widths the system has never produced.

---

## 1. What was counted

### 1.1 The recorded calls — 2,559, with everything needed to replay them

`logs/llm_calls.jsonl`, 18MB, one JSON line per call since day one: `role`,
`function`, `model`, `system`, `user`, `response`, tokens, duration, error.
3 errored.

Every call site builds its prompt as `template + payload` with a known join, so
the payload separates mechanically. Verified this session:

| shape | recorded | split | payload chars: min / median / max |
|---|---:|---|---|
| extract | 1,187 | 1187/1187 | 587 / 2,021 / 6,544 |
| opener.reading | 272 | — | — |
| delib | 170 | 170/170 | 8,551 / 13,735 / 19,869 |
| triage | 157 | 157/157 | 637 / 6,776 / 11,900 |
| gate | 47 | 47/47 | 12 / 331 / 926 |
| digest | 17 | payload **is** the user turn | — |
| confront | 5 | payload **is** the user turn | — |
| **replayable** | **1,855** | | |

The remaining 704 are call sites the bench does not cover (`question`,
`research`, `claim_door`, `conversation`, `works`, `closure`).

### 1.2 The hand-built corpus measures two widths that do not occur

| | hand-built | recorded |
|---|---:|---:|
| deliberation dossier | 2,258 chars | median **13,735**, max 19,869 |
| gate emission | max 128 chars | median 331, max 926 |
| gate context sweep | 2k / 8k / 16k | **nothing above 926** |
| triage listing | 7,158 | median 6,776 ✓ |

Deliberation is benched at **16% of production width**, on the boundary where
holding a schema at width is the entire question. The context sweep tests three
widths the gate has never been given.

### 1.3 The tunable surface — 10 bodies, 20,120 characters

`outbound._judge_prompt` 5,018 · `lite._TASK` 4,855 · `opener._READING_TASK`
3,423 · `nightly._CONFRONT_SYSTEM` 3,043 · `feeds._TRIAGE_TASK` 1,520 ·
`extract._TASK` 795 · `extract._DIRECTED` 605 · `nightly._DIGEST_SYSTEM` 482 ·
`extract._SYSTEM` 197 · `feeds._TRIAGE_SYSTEM` 182.

### 1.4 Labels, where judgment rather than structure is being scored

`gate_log`: 216 rows, **40 operator-classified** — 28 `gate_misfire`, 12
`gate_correct`, **17 carrying `emission_full`**. Of the 28 misfires, **22 are on
`don't-pretend-to-feel-001`, which the active constitution (v6) does not
contain**; they describe a retired rule and are excluded.

`concern_refusals`: 5. `ingest_log`: 1,160, **unlabelled** — "kept" is not
"should have been kept".

### 1.5 The prompts carry 77 lines no case exercises

Dated provenance markers across the six modules (`lite.py` 22, `opener.py` 19,
`nightly.py` 13, `feeds.py` 8, `extract.py` 8, `outbound.py` 7). Each names a
failure a line prevents. Replay does not fix this: the failures happened before
the lines existed, so they are not in the log either.

---

## 2. The proposal — three changes

### 2.1 The bench reads the repo's prompts

Delete the 16 hand copies. `build_cases(prompts)` takes a `PromptSet` — prompt
id to string, defaulted by reading `newz.*`. Modules are read, never patched.

This **deletes** machinery: the copies, and the drift they caused twice.

*Done when:* no prompt literal in `bench_model.py` also exists in `newz/`.

### 2.2 The cases come from the recorded calls

A reader over `logs/llm_calls.jsonl` that, per line: identifies the shape from
the join marker, splits the payload off the old template, and re-renders it
against whichever `PromptSet` is being scored. `--since`, `--function` and
`--sample N` bound a run.

**This deletes the hand-built fixtures** — `_DOSSIER`, `_DOSSIER_DRY`,
`_EPISODE_ROWS`, `_HELD`, `_CANDIDATES`, `_NOISE`, `_SUMMARIES`, the three
`_KEEP_*` items, `_CLEAN_MATERIAL`, `_CHUNK` — and the context sweep, whose
widths §1.2 shows do not occur. Real width is whatever the log holds.

What survives as hand-written: `GATE_FIRE` / `GATE_PASS` as a seed beside the
classified holds, and the nine injection payloads, because an attack that has
not happened is not in the log and is the one thing worth inventing.

**Three things make this work without gold answers:**

1. **Most checks are structural** — schema held, refs real, no truncation,
   verbatim grounding, the fence respected, confidences in range. Those need a
   real input, not a right answer, and they are what `delib_check`,
   `digest_check`, `confront_check`, `extract_check` and `ground_check` already
   do.
2. **Labels are used where judgment is scored** — §1.4's classified holds for
   the gate, expired-clause rows excluded and counted.
3. **The baseline is free.** The recorded `response` is already there, so
   scoring the current prompts across all 1,855 inputs costs **zero LLM calls**.
   *Caveat:* a recorded response reflects the prompt live at the time, so
   pre-E1.0 triage rows carry the retired prompt. Rows are dated; a run reports
   how many predate the current prompt.

*Done when:* a run prints its corpus composition — replayed per shape, excluded
as expired, predating the current prompt — and the deliberation denominator is
the log's, not four.

### 2.3 One command, unattended

```
bench_model.py --tune
```

No arguments, no phases, no decision asked of the operator until it is done.
The run:

1. reads the current prompts (§2.1);
2. **establishes its own baseline for free** — scoring the 1,855 recorded
   responses costs zero model calls (§2.2);
3. **chooses its own order**, working boundaries worst-first by weighted deficit
   against that baseline;
4. per boundary, per round: shows a model the failing payloads, takes one
   rewrite, scores it on held-back payloads, keeps it if it beats the
   incumbent's upper interval;
5. **drops a boundary by itself** when its held-back half is too thin to decide
   anything, or when two rounds pass with nothing kept — and says which and why;
6. **stops by itself** when no boundary is still improving, or the call budget
   is spent;
7. prints one diff of everything it kept, with before and after either side.

`--prompt X --variant f.txt` remains for scoring one edit by hand, but nothing
in the loop requires it.

**Two guards, applied by the tool, not by the operator:**

1. **Half the replayed payloads are held back.** The proposer sees failures from
   one half; the deciding score is the other. Both print every round.
2. **A change must beat the incumbent's upper interval**, not its point score.

Output goes to stdout, verbose, throughout — a long run is watchable and never
silent:

```
── round 3 · triage · 157 replayed (78 tune / 79 held) ────────────────────────
   incumbent  tune 0.61 [0.52-0.69]  held 0.58
   failing (tune): 31 — 22 kept an item the being later never cited
   variant: +6 lines, "name the shape of a keep, not just examples"
     tune 0.71  held 0.69 [0.58-0.78]  vs upper 0.69 ······· below, discard
   variant: -1 +2 lines, "the ordinary answer is nothing" moved up
     tune 0.66  held 0.74 [0.63-0.82]  vs upper 0.69 ······· keep
     gate 0.87→0.87  extract 0.79→0.78  deep 0.75→0.75
```

Redirect it if you want to keep it. The tool does not.

*Done when:* `--tune` with no arguments runs to its own stopping condition and
prints a diff, having asked nothing and created no file.

---

## 3. What it does not do

**It writes nothing.** Not `newz/`, not the store, not git, not a file of its
own. **The tool has no code path that writes to `newz/`** — a stronger guarantee
than a flag defaulting to off, because it cannot be edited away without being
visible. The diff goes to the terminal; you apply it by hand or you do not.

It **reads** two things it did not before: `logs/llm_calls.jsonl`, and
`data/newz.db` read-only for §1.4's holds. Both are the operator's own record.
Neither is ever copied into the repo, a commit, or the tool's output — runs
report counts and row ids, never emission or payload text.

Because nothing is applied, there is no lock list and no protected-line
mechanism. Two consequences worth stating rather than discovering:

- **The gate is tunable like anything else**, because a gate diff is a diff you
  read. Its score is balanced accuracy and a prompt can raise it by firing
  *less*, so catch and false-fire print separately.
- **Constitution clause text is not a prompt** and is not offered as a prompt
  id. It lives in the store under a governance flow.

---

## 4. Red team

**Replay does not make the corpus representative, only real.** 1,855 calls are
what this being did, on the feeds it reads, in the months it has run. A prompt
tuned on them is tuned to that distribution — which is the right one for this
being and the wrong one for judging a model in general.

**The log is a survivor.** It records calls that were made. It cannot contain
the read that was never triaged or the question that was never opened, so
false-negative failure modes stay invisible. §1.5's 77 lines are the same
problem in another form.

**Recorded responses are a baseline, not ground truth.** They came from prompts
live at the time, and from whichever model was serving. §2.2 dates and counts
them; it does not make them true.

**A tuned prompt is fitted to one model.** Tune at model-adoption time, not
continuously, and print which model did which.

**The loop will propose deleting §1.5's lines**, because they are long and score
nothing. Nothing in the tool stops it. This is the single strongest argument for
the tool never applying anything.

**It optimises a proxy.** Nothing here shows a better bench score is a
better-behaved being. §5's last item is the only thing that would.

---

## 5. Falsification

Reviewed after the first `--tune` run:

- **Held-back score against tuning score.** If the first rose and the second did
  not, the run fitted the payloads it was shown. Primary reading.
- **Keep rate.** If most variants are kept, the interval guard is too loose.
- **Proposed deletions of provenance-marked lines.** If they recur, the corpus
  is the problem and tuning does not fix it.
- **Deliberation at real width.** §1.2 predicts the current prompt scores worse
  on 13,735-character dossiers than on the 2,258-character fixture. If it does
  not, the width concern was wrong and the fixture was adequate.
- **The being, on a tuned prompt, for a week.** Gate misfire rate, feed
  coverage, advance kinds. The only test that settles the proxy question.

**Reversion.** The prompts are in git and the tool changed none of them.
Reverting an applied diff is `git revert`. No state to unwind.

**Decision rule, applied by the run rather than by the operator.** The free
baseline is the first thing `--tune` computes. A boundary already at the ceiling
of what its checks can detect has nothing for the loop to find, and the run
**skips it and says so** rather than spending a budget proving it. If every
boundary is skipped, the run ends immediately with that finding, which is the
useful answer: the next step is better checks, not better prompts.

---

## 6. What this does not claim

- It does not claim tuned prompts produce a better-behaved being. §4.
- It does not claim the replayed distribution is the right one to tune against.
  §4's first two points.
- It offers no baseline yet. §2.2 produces the first one, for free.
- It has no instrument for a rewrite that keeps a provenance-marked line's shape
  and drops its force. A human reading the diff is the only defence.
- The 704 unreplayed calls are counted, not covered. Adding a shape is a join
  marker and a check apiece.
