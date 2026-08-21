# The questions it could not answer

*2026-08-21. A proposal for `source_gaps` — the record of what the being tried
to consume and couldn't. Written against the operator's direction that the
operator must not be the bottleneck: the system has to consume information and
grow without a person in the path. Red team at §5. It split the proposal in two
and held the interesting half; the operator then removed that half outright,
for a better reason than the one the red team had.*

---

## 0. The finding, in one line

**The being is not short of sources. It is failing to use what its sources
return, repeatedly, on the same questions — and the record of that failure does
not say so.**

32 gaps. **28** say *"sources answered but nothing was relevant enough to
read"*. **4** say *"nothing usable was extracted"*. **Zero** say *"no source
answered"* and **zero** say *"I have already read everything my sources return
for this"* — the two cases that would mean the diet needs widening.

Anyone reading only the count would add sources. The count is the one thing
that is currently read.

---

## 1. Why this is the right place to look

The journal was the wrong place, and for exactly the reason the operator gave:
every entry needs a person present, reading, and typing. `source_gaps` is its
opposite — **self-authored, generated at machine rate, and about the world
rather than about the operator**. 27 of the 32 rows were written in the last
seven days, against 1,140 sources read and 5,369 claims kept in the same
window.

It is also the signal the design already points at. `newz/world/research.py`
says the gap record *"is what source_review reads to decide which sources to
ADD (S2 §9.1)"*; `newz/resolutions/resolver.py` says *"it is how §9.1 learns
which sources to…"*. The learning does not exist. `source_gaps_open` counts
rows for the surface, `tools/source_review.py` groups them when a person types
it, and nothing turns a failed question into a changed one.

That is the same defect as the retrieval index nothing maintained, the
agreement writer nothing called, and closure welded to progress — but on the
one input the being produces by itself, at its own rate, without anyone.

---

## 2. What the record cannot say

`record_gap` writes `(ts, concern_id, query, gap)`, where `gap` is one of four
sentences the code composes. The sentence is the whole of the diagnosis, and it
collapses everything a consumer would need:

| The record says | It does not say |
|---|---|
| "nothing was relevant enough to read" | how many candidates there were |
| | whether the **embedding floor** cut them or the **triage call** refused them |
| | the best score, and how far under 0.35 it was |
| | how many were **capped** rather than rejected *(the suffix says how many, in prose)* |
| "nothing usable was extracted" | whether extraction failed, or the material genuinely held nothing |

Two stages reject, and the record names neither. A floor that rejected
everything at 0.34 and a model that read six summaries and refused all six are
different failures with different remedies, and today they produce the same
row.

**This is the R-37 shape again**: a record that reads like a finding and carries
less than it claims.

---

## 3. What the distribution already says

**The same questions fail over and over.** 32 gaps across **12 distinct
queries** — 9 on one concern, 8 on another, 3 on a third. The same question is
asked, fails at the same stage, and nothing changes before it is asked again.
A loop with no learning in it, measured rather than asserted.

**And this bug has been found twice before, one layer up.** E1.0 is the record
of a relevance filter that ranked feed candidates against open concerns and
starved the diet — 27 of 61 feeds polled continuously and read **zero** times.
R-28 is the record of a share cap acting as a veto. Both were found **by hand**,
by a person reading a number that had no consumer. `source_gaps` is where the
same failure at the research layer would announce itself, if the record said
which filter had done the rejecting.

---

## 4. What this proposes

### W12a — the gap record carries its cause *(Class A)*

`record_gap` takes the counts the research pass already holds and cannot
currently write: candidates found, rejected by floor, rejected by triage,
capped, already-read, best score, and which stage produced the gap as an
enumerated `cause` rather than a sentence. Migration 0040; the prose sentence
stays, because it is what a person reads.

Then one consumer that acts without a person: the read (E3.6) and the weekly
report gain **repeat failures by query and cause** — *"this question has failed
9 times, always at the relevance floor, best score 0.31"* — which is a fact
nobody can currently obtain without writing SQL.

*Done when:* every gap row names its cause and its counts, no gap is written
without them, and a query that has failed repeatedly at one stage is visible
without anyone querying the store.

*Why Class A:* it changes what is recorded and read, never what the being reads.

### W12b — removed, not held *(operator, 2026-08-21)*

An earlier draft proposed that after N failures at the same stage the next
attempt read the best-scoring candidate anyway, and §5 held it behind a
fortnight of W12a's counts. **The operator removed it instead**, and the reason
is better than the one the red team gave:

> *in 7-10 days the system will look different and could require a different
> action*

A held item is still a commitment to a shape — it says the answer will be *some
version of relaxing the filter*, decided later. That is a bet on the diagnosis
made before the diagnosis exists. W12a is being built precisely because nobody
can currently tell a floor that cut everything from a triage call that refused
everything from a question no source could settle, and those have nothing in
common as remedies: one is a threshold, one is a prompt, one is R-33 and lives
at the opener.

So the queue carries no successor. In a week the counts will say what the
failure actually is, against a store that has meanwhile read a thousand more
sources, and the action is chosen then from what is true then.

*Recorded because the shape of this decision recurs:* the plan holds several
"held pending evidence" items, and each one is a pre-commitment worth
re-reading. Rule 6 puts the judgment with the operator; this is the operator
using it to decline to pre-commit.

## 5. Red team

**RT1 — the concentration may be R-33, not a source gap.** Nine failures on
*"Does the disparity between open interest and trading volume indicate…"* and
eight on *"How does the absence of independent corroboration for AI usage data
distort…"* may mean those questions cannot be answered by any source that
exists — which is R-33's finding about concerns being unfalsifiable by
construction, and R-36's that a terminus can be unreachable. **Fixing the
source layer for an unanswerable question is fixing the wrong end**, and it
would look like progress: more reading, no more answers. *Decision:* W12a's
read must show the query text beside the failure count, so the first thing seen
is the question, not the number. If the repeated questions are malformed, the
work belongs at the opener and this proposal is answered by not doing it.

**RT2 — relaxing a filter after N failures is E1.0's fix applied blindly.**
`_relevant`'s own docstring says it: *"reading too much is a budget problem, but
inventing a relevance score would make it a memory problem."* W12b overrides
the being's own judgment on a schedule, and the material it lets through is
precisely the topical-but-useless band measured at 0.571–0.638. *Decision:* one
source per relaxation, marked provisional, and the yield measured — if
provisional reads keep claims at a materially lower rate than ordinary ones,
the mechanism is removed rather than tuned.

**RT3 — W12b is Class B and this proposal is otherwise Class A.** It changes
what the being reads, so it costs an evidence window and confounds anything
else changing in it. W1–W10 were all Class A for exactly that reason. *Decision:*
W12a alone. The operator then removed W12b rather than sequencing it — see
§4, and note that this red-team entry argued for *ordering* what should have
been argued out of existence.

**RT4 — n=1, 32 rows, 12 queries, a fortnight.** Any threshold chosen now is
fitted to two weeks of one being's behaviour. *Decision:* W12a chooses no
threshold. It counts. N in W12b is chosen from the distribution W12a produces,
and the choice is recorded with the distribution it was chosen from.

**RT5 — the embedder was only proven days ago.** `ee84745` (2026-08-20) found
the retrieval index had never been maintained; the relevance floor uses a
different embedding path, and 7 gaps have been written since. So the floor is
not obviously broken — but the same class of silent failure was live in this
system this week, and W12a's counts are what would distinguish "the floor is
working and the material is bad" from "the floor is scoring nothing above
0.35". *Decision:* recorded as the first thing the counts should be read for.

**RT6 — a consumer that only reports still ends at a person.** W12a makes the
failure legible and does not act on it; under the operator's own direction that
is not enough on its own. *Counter:* it is the diagnosis that decides which
action is right, and there are two candidate actions — relax the filter, or fix
the opener — pointing at different subsystems. Acting before knowing which is
how E1.0's filter got built in the first place. *Recorded honestly:* if W12a
runs a fortnight and nothing is built on it, this proposal has added a
measurement and not a loop.

**RT7 — the same hand wrote the finding, the fix and the red team.** No
independence, and the SEL's own structural separation for red teams was not
used here either. Mitigation is that every number above is reproducible from
the store in one query.

---

## 6. What this does not do

- It does not add a source, a feed, or an adapter. The distribution says the
  adapter set is not exhausted — that gap has fired **zero** times.
- It does not touch the opener, the concern schema, or R-33/R-36. If RT1 is
  right, that is where the work goes, and this proposal's job is to say so.
- It does not classify a gap with a model. The cause is mechanical: which stage
  rejected, and how many.
- It does not make the operator a reader of anything new.

---

## 7. Decided

**W12a approved and built 2026-08-21** — migration 0040, the cause and the
counts on every gap, and the questions page carrying what it asked and could
not answer, question first.

**W12b removed** rather than held *(operator)*: in 7–10 days the system will
look different and could require a different action. Nothing succeeds this in
the queue. The counts are read then, against whatever is true then.

**RT1 stands as the thing to look for**: if the repeat failures are questions
no source can settle, the work is at the opener and not here at all.
