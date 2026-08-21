# The bench that writes back

*2026-08-21. A proposal for using `tools/bench_model.py` to understand and tune
the prompts the repo actually sends, in response to the operator's instruction
to reverse `452666a`'s standalone position. Figures measured from this clone at
`d13ec55` and from the live store this session; where a claim has no instrument,
it says so (Rule 0).*

**Supersedes this document's first two drafts.** The first was prose. The second
specified an artifact, a patch file, a journal and a scratch worktree, which is
a release pipeline and not a diagnostic *(operator, 2026-08-21: "this is too
complicated … this is a diagnostic tool to help understand and tune existing
prompts")*. §2 is what remains after that correction, and §3 is what it removed.

---

## 0. The finding, in one line

**The tool writes nothing, so the only question is whether its numbers mean
anything** — and against 54 cases, 4 of them on `deep`, most of them do not
without the two guards in §2.3.

---

## 1. What was counted

**The tunable surface.** 10 prompt bodies, 20,120 characters:
`outbound._judge_prompt` 5,018 · `lite._TASK` 4,855 · `opener._READING_TASK`
3,423 · `nightly._CONFRONT_SYSTEM` 3,043 · `feeds._TRIAGE_TASK` 1,520 ·
`extract._TASK` 795 · `extract._DIRECTED` 605 · `nightly._DIGEST_SYSTEM` 482 ·
`extract._SYSTEM` 197 · `feeds._TRIAGE_SYSTEM` 182.

**The corpus.** 54 cases — gate 23, extract 13, conformance 5, triage 5 (60 item
decisions), voice 4, **deep 4**. One gate case is 4.3 points of balanced
accuracy. One deep case is 25.

**No baseline exists.** *(Rule 0.)* No full run has been recorded for any
candidate. Six spot cases ran green against `qwen/qwen3.6-35b-a3b` this session;
that is not a baseline.

**The prompts carry 77 lines the corpus cannot see** — dated provenance markers
across the six modules (`lite.py` 22, `opener.py` 19, `nightly.py` 13,
`feeds.py` 8, `extract.py` 8, `outbound.py` 7). Each names a failure a line
prevents. No case exercises any of them, so deleting one is free by the bench's
reckoning and costly in fact.

---

## 2. The proposal — three changes

### 2.1 The bench reads the repo's prompts

Delete the 16 hand copies. `build_cases(prompts)` takes a `PromptSet` — a dict
from prompt id to string, defaulted by reading `newz.*`.

This **deletes** machinery: the copies, and the drift they caused twice.

Modules are read, never patched.

*Done when:* no prompt literal in `bench_model.py` also exists in `newz/`, and a
`--repeats 3` run is recorded as the first baseline.

### 2.2 Score a variant against what the repo has

```
bench_model.py --prompt triage.task --variant my_edit.txt
```

Runs both, prints both, side by side, with intervals and the per-case failures
for each. This is the whole diagnostic: you edit a prompt in a scratch file, you
find out whether it is better, and you decide.

*Done when:* a variant that fixes one triage case shows as +1 case with its
interval, and the unchanged boundaries show as unchanged.

### 2.3 A loop that proposes variants and prints the winner

```
bench_model.py --tune triage --rounds 6
```

Each round: show a model the current prompt and the cases that failed, ask for
one rewrite, score it, keep it if it is better. At the end, print a diff of the
best prompt found against the repo's current one, and the scores either side.

**Two guards, because §1's numbers are small:**

1. **Half the cases are held back.** The proposer sees failures from the tuning
   half; the score that decides is from the other half. Both are printed every
   round. If the tuning half improves and the held-back half does not, the
   output says so and the diff is not worth applying.
2. **A change must beat the incumbent's upper interval**, not its point score.
   At 4.3 points a gate case and 25 a deep one, a point-score comparison would
   accept noise every round.

Output goes to stdout, verbose, per round:

```
── round 3 · triage · incumbent tune 0.61 [0.48-0.73] · held-back 0.58 ────────
   failing: triage_summaries, triage_unfamiliar
   variant: +6 lines, "name the shape of a keep, not just examples"
     tune 0.71  held-back 0.69 [0.55-0.80]  vs upper 0.71 ····· below, discard
   variant: -1 +2 lines, "the ordinary answer is nothing" moved up
     tune 0.66  held-back 0.74 [0.61-0.84]  vs upper 0.71 ····· keep
     gate 0.87→0.87  extract 0.79→0.78  deep 0.75→0.75
```

Redirect it if you want to keep it. The tool does not.

*Done when:* a run ends and prints a diff, having created no file.

---

## 3. What it does not do

**It writes nothing.** Not `newz/`, not the store, not git, not a file of its
own. The last draft specified an artifact, a patch, a journal and a scratch
worktree for a `pytest` run; all four are gone. The diff goes to the terminal
and you apply it by hand or you do not.

That removes the reason for everything else that was in the last draft. There is
no lock list, because nothing is applied. There is no protected-line mechanism,
because you read the diff. There is no approval gate, because there is nothing
to approve against — **the tool has no code path that writes to `newz/`**, which
is a stronger guarantee than a flag that defaults to off.

Two consequences worth stating rather than discovering:

- **The gate is tunable like anything else**, because a gate diff is a diff you
  read. Note when reading one that gate score is balanced accuracy and a prompt
  can raise it by firing *less* — the run prints catch and false-fire
  separately for exactly this.
- **Constitution clause text is not in scope** and is not offered as a prompt
  id. It lives in the store under a governance flow; it is not a prompt.

---

## 4. Red team

**The corpus is too small and the loop cannot tell.** At 4 deep cases, most gain
after two or three rounds is noise. §2.3's two guards are necessary and not
sufficient. The honest mitigation is that you read the diff and the held-back
number, both of which are printed.

**A tuned prompt is fitted to one model.** Every gain is fitted to whatever was
under test, and the repo swaps candidates. Tune at model-adoption time, not
continuously.

**The loop will propose deleting §1's 77 lines**, because they are long and
score nothing. Nothing in the tool stops it; the diff is printed and you are the
one who knows what those lines cost to learn. This is the single strongest
argument for the tool never applying anything.

**It optimises a proxy.** Nothing here shows a better bench score is a
better-behaved being. §5's last item is the only thing that would.

**Circularity.** If the proposer and the model under test are the same, it is a
model writing its own exam. Print which model did which.

---

## 5. Falsification

Reviewed after the first `--tune` run:

- **Held-back score against tuning score.** If the first rose and the second did
  not, the run fitted the cases it was shown. Primary reading.
- **Keep rate.** If most variants are kept, the interval guard is too loose and
  the corpus is too small — stop and grow it.
- **Proposed deletions of provenance-marked lines.** If they recur, the corpus
  is the problem and no amount of tuning fixes it.
- **The being, on a tuned prompt, for a week.** Gate misfire rate, feed
  coverage, advance kinds. The only test that settles the proxy question.

**Reversion.** The prompts are in git and the tool changed none of them.
Reverting an applied diff is `git revert`. There is no state to unwind.

**Decision rule.** Build §2.1 and §2.2 first and use them by hand for a week. If
hand-written variants do not produce a single improvement that survives the
held-back half, **do not build §2.3** — the corpus, not the prompts, is what
needs work, and a loop would only generate that same non-result faster.

---

## 6. What this does not claim

- It does not claim tuned prompts produce a better-behaved being. §4.
- It does not claim the corpus is adequate. §1 says it is 4 cases on `deep`, and
  §5's decision rule exists because of it.
- It offers no baseline. §2.1 produces the first one.
- It has no instrument for a rewrite that keeps a provenance-marked line's shape
  and drops its force. A human reading the diff is the only defence.
