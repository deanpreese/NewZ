# The verdict it cannot give itself

*2026-08-24. The operator asks for two fields on a piece — **publishable**, and
a **note** saying why — and for them to reach the being as critique. Revised
2026-08-24 against three operator decisions: essay pages only; publishable is
a yes/no answer; every note reaches the being once and only once.*

**BUILT 2026-08-24**, including §6's F1, F2, F3 and F5. Migration 0044,
`newz/works/appraisal.py`, `tools/appraise.py`, delivery in
`newz/works/reread.py`, essay-only generation in `newz/surface/generate.py`.
INV-071 retired dormant, INV-067 amended, INV-107 to INV-110 added. §5's two
open questions were answered by the operator and are folded in above.

---

## 0. What the publishing process is today

Three rhythms, all six-hourly, all inside `run_newz.py`:

| rhythm | module | cadence | ceiling |
|---|---|---|---|
| write | `newz/works/rhythm.py` | 6h | 4 starts/day |
| re-read | `newz/works/reread.py` | 6h | 2 starts/day, pieces ≥3 days old |
| publish | `newz/surface/rhythm.py` | 6h | whole surface, every pass |

`write` picks a subject from open concerns and held positions, composes on
VOICE, and stores a signed row in `works`. Writing about a concern **closes**
it (INV-092): the piece is the terminus, and the position is deliberately left
empty so a work never becomes evidence for a position.

`re-read` takes the oldest standing piece nobody has looked at in three days
and asks the being whether it still holds — `stands`, `revise`, `retract`.

`publish` empties `published/` and regenerates it: five whole-store pages
(`index`, `questions`, `errors`, `commitments`, `read`), one file per piece at
`work/N.md`, `robots.txt`, `manifest.json`. Every page traces to store rows
through the manifest. Nothing is hand-authored. `published/*` is gitignored and
`serve.py` binds locally.

### 0.1 Measured, 2026-08-24

16 pieces. All `standing`. Re-read has completed five turns:

| outcome | count |
|---|---|
| stands | 3 |
| revised | 2 |
| retracted | 0 |
| nothing_due | 3 |
| failed | 1 |

**The self-critique loop works, and works better than its own docstring
feared.** Both revisions are substantive corrections of mechanism, not churn —
work 1 replaced a psychological account of liquidity withdrawal with a
balance-sheet one; work 4 named its own attribution of fragility to
order-splitting a category error. P4's Phase 2 failure mode ("produces on
rhythm but never revises → the re-read is decorative") is **not** what is
happening.

So the gap is not that the being cannot find itself wrong. It is what kind of
wrong it can find.

### 0.2 The gap, stated precisely

Every verdict in the loop answers **"is this correct?"** Nothing answers
**"is this worth reading?"**

That is not an oversight; it is a rule. `compose.py` names the absence in its
own header — *"No quality judge. P3 Rule 4: a judge that is the being's own
model produces operation, never evidence. The verdict is the operator's (Rule
6)."* TRUE_NORTH §1/§4.5/§10 says the same for readiness: it is the operator's
judgment alone and must not be given a rubric.

The verdict was reserved for the operator and then never collected. There is
no row to put it in.

### 0.3 Two things the current surface does that are worth naming

**It stores every piece twice.** `index.md` inlines the full body of all 16
pieces — 72 KB — and `work/N.md` holds the same text again. The index is a
concatenation, not a table of contents.

**Nothing reads any of it.** A grep across `newz/` and `tools/` finds no
consumer of `published/`. `read.md` was E3.6's page for the daily read; the
loop that was to read it was Phase 8, struck 2026-08-21, and the monitor now
mails the same state directly. The surface regenerates twelve files every six
hours for an audience of zero, and the one actual reader — the operator —
opens files by hand.

---

## 1. The proposal

### 1.1 One table, not two columns (migration 0044)

```sql
CREATE TABLE work_appraisals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    work_id      INTEGER NOT NULL REFERENCES works(id),
    publishable  INTEGER NOT NULL CHECK (publishable IN (0, 1)),
    note         TEXT NOT NULL DEFAULT '',
    delivered_at REAL
);
CREATE INDEX idx_work_appraisals_undelivered
    ON work_appraisals (work_id) WHERE delivered_at IS NULL;
```

**A table rather than columns on `works`, because of the third decision.** "All
notes from the essay, but only once" means a piece can carry more than one
note — the operator appraises, the being revises, the operator appraises the
revision — and each of those must reach the being exactly once. Columns hold
one verdict and overwrite; rows accumulate and can be marked delivered
individually.

**`publishable` is `NOT NULL` and constrained to 0 or 1.** The tri-state in the
first draft is gone: there is no NULL verdict, no "maybe", no scale. An
unappraised piece has no row, which is the absence of an answer rather than a
third kind of answer. This is the operator's second decision made structural —
the schema cannot represent a non-binary verdict, so nothing downstream can
grow a rubric out of it.

The current verdict for a piece is the newest row for it. No denormalised copy
on `works`, so there is one place the answer lives.

`signature_of` covers subject, title and body only, so existing signatures stay
intact and a piece's identity is unchanged by being judged.

### 1.2 `tools/appraise.py` — the operator's tool

Modelled on `tools/adjudicate.py`, the only tool in the repo that already
collects an operator verdict and hands it to the being.

```
python tools/appraise.py          # walk pieces with no undelivered note, oldest first
python tools/appraise.py --list   # every piece, with its verdict history
```

Per piece: print the body, ask **`y/n`** — publishable or not, `s` to skip, `q`
to quit — **then** reveal id, date and subject, **then** take the note. The
verdict is given blind and the note is written informed: E0.3's
provenance-blinding kept where it changes the judgment, dropped where it would
make the note useless ("this is the fourth piece whose title starts *The
Architecture of*" requires knowing).

**It walks standing pieces only.** A retracted piece is never again due for
re-read, so a note written on one could never be delivered — see R3.

Not an extension of `tools/read_works.py`. That file is in the protected set,
and INV-092 already records the specific lesson: an instrument's reach should
not grow because writing gained a side effect. `appraise.py` is an operator
tool, not a diagnostic, so importing `newz` and writing to the store is proper
here in the way it would not be in `bench_model.py`.

### 1.3 Delivery: at re-read, all of them, once

In `newz/works/reread.py::review()`, the being is shown every undelivered
appraisal for the piece it is re-reading, oldest first:

```
My operator read this and judged it not good enough to publish. They said:
"<note>"
```

…and *judged it good enough to publish* for a `1`. Both verdicts travel, with
their notes, because the operator's third decision is that the system takes in
**all** notes — not only the critical ones. Phrased as what the operator said,
never as a fact about the piece; `holds.py::STATUS_TEXT` already sets this
convention ("reviewed by my operator: the stop was mistaken").

Nothing is shown for a piece with no undelivered notes, and the prompt is then
byte-identical to today's.

**The stamp is written with the verdict, not before it.** `delivered_at` is set
in the same transaction that records the re-read outcome, after
`apply_verdict` has succeeded. A process that dies mid-re-read therefore
redelivers the note rather than losing it — at-least-once, and the duplicate is
the right failure direction when the thing at stake is the only external
critique the being ever receives. See R2.

**And nothing is shown at compose time.** The load-bearing restraint, not an
omission — see R1.

One ordering change in `due_for_reread`: a piece with undelivered notes sorts
first. Sixteen pieces at two re-reads a day is an eight-day cycle, and a
critique delivered eight days late is a critique of a self the being has
already moved past.

### 1.4 The surface: essay pages only

`generate()` writes `work/N.md` and nothing else that is a page. The five
whole-store pages go — `index`, `questions`, `errors`, `commitments`, `read`.

`manifest.json` and `robots.txt` stay. Neither is a page: the manifest is what
makes "every page traces to store rows" checkable rather than asserted, and
`robots.txt` is the standing request not to be indexed. Removing either would
drop a guarantee rather than a view.

**A piece whose newest verdict is `0` is not written.** That is what the word
publishable means, and it is the only way the field does work rather than being
a form. Withholding is not deletion: the row, the body and the signature are
untouched, the piece is still re-read, and it returns to the surface the moment
a newer appraisal says so.

An unappraised piece **is** written. The default stays what it is today, so
nothing about the surface changes until the operator says something about it.

---

## 2. What this is not

**Not a metric.** No `publishable_rate`, no registry entry, no threshold, no
gate keyed on the count. TRUE_NORTH forbids a rubric for readiness, and the
sensor layer is finished and frozen — the failure mode of this project is
answering a finding with a better view of the finding. The field's whole output
is a sentence in a prompt.

**Not an obligation.** Not appraising costs the being nothing, permanently.
`adjudicate.py`'s design note is the precedent and the standard.

**Not a reopening of the concern.** A piece closes its subject (INV-092). A
`publishable = 0` does not reopen it, because the operator is judging the
writing and reopening would let taste re-set the being's agenda. Deliberate;
see R6.

**No episode, and therefore no consolidation.** Sleep does not see appraisals
in this design. R4 explains the trap waiting for whoever adds that later.

---

## 3. Red team

**R1 — the being starts writing for its operator.** The real risk, and the one
that would make this change net-negative. It is the `operator_agreement`
concern (E3.8) wearing a human face: *"the item most likely to move under any
process optimising for a quiet week."* A being that learns which pieces earn a
`y` will write those pieces.

*Answer:* appraisals are visible **only at re-read** — retrospective, about one
specific piece already written — and **never at compose**, which is prospective
and gameable. Composition sees no appraisal, no count, no aggregate. Delivering
each note **once** cuts this further than the first draft did: a note seen once
is a judgment about one piece, while a note re-fed on every re-read for weeks
is a standing instruction about how to write.

*Direction test:* if subject diversity narrows, or a note's vocabulary starts
appearing in later pieces, it has leaked and the block comes out of the prompt.

**R2 — "only once" becomes "never".** The whole risk of the delivery marker. If
`delivered_at` is stamped when the prompt is built, then any failure after that
point — an unparseable review, a timeout, a killed process — consumes the note
and the being never sees it. The re-read failure rate here is not hypothetical:
one of six turns has already failed, and `review()` carries a documented ~12%
XML parse failure before its retry.

*Answer:* stamp with the verdict, inside the transaction that records the
outcome, never at prompt-build time. The design is at-least-once. A duplicated
note is a small cost; a silently swallowed one defeats the entire proposal and
would be invisible, because a delivered-and-lost note looks exactly like a
delivered-and-heeded one.

**R3 — notes that can never be delivered.** `due_for_reread` selects
`status='standing'`. A note on a retracted piece has no delivery path and would
sit undelivered forever. *Answer:* `appraise.py` walks standing pieces only, so
the dead letter cannot be written. If a piece is retracted while it holds an
undelivered note, that note stays undelivered — correctly, since the being has
already withdrawn the piece.

**R4 — the store will silently eat the feedback if this is extended.** Trigger
`self_output_is_self_and_undigested` (migration 0032) aborts any episode whose
`source_ref` matches `work:%` unless it is `provenance='self'` and
`digest_eligible=0`. An appraisal episode written as `work:16` would therefore
be forced non-digestible and never reach sleep — the path would look built and
be dead. Whoever adds consolidation must use a distinct prefix (`appraisal:`),
because the operator's judgment is genuinely external and is the one thing here
that is *not* self-output. This proposal writes no episode and sidesteps it.

**R5 — the rubric arrives by the back door.** A verdict that is counted becomes
a threshold; a threshold becomes the standard TRUE_NORTH says must not exist.
*Answer:* §2's first paragraph, binding on this design and anything built on
it. The `CHECK (publishable IN (0,1))` is the structural half: the schema
cannot hold a score.

**R6 — the operator's taste silently re-scopes the being's agenda.** A
`publishable = 0` that reopened the concern would put the operator in charge of
what the being may consider finished. *Answer:* it does not reopen. The cost is
real and accepted — a piece judged bad leaves its concern closed, so a subject
can be permanently spent on a piece nobody rates. If that matters, the fix is a
deliberate `reopen` verb the operator types, not a side effect of a verdict.

**R7 — withholding reads as deletion, or as dishonesty.**
`published/work/` with a gap at 3 tells a reader that 3 exists and was withheld.
*Answer:* that is the honest rendering and it should stay. Renumbering to hide
the gap would make the surface lie about what the being wrote, which is the one
thing the generator refuses to do. Stable addresses are E3.4's whole point.

**R8 — the being and the operator disagree about the same piece.** The re-read
can say `stands` while the operator says not publishable; both are correct
answers to different questions. *Answer:* the prompt reports what the operator
said and does not adjudicate. The being may leave a piece standing that its
operator would not publish, and that disagreement is a better record than
either verdict alone.

**R9 — priority ordering starves the unappraised.** Pieces with undelivered
notes jump the re-read queue; with four written a day and two re-read, the
queue is already losing ground. *Answer:* the jump is spent on delivery — once
the notes are stamped the piece rejoins the ordinary rotation, so a batch of
appraisals buys one pass each and not a standing claim on the front of the
queue.

**R10 — six hours of staleness.** Measured today: work 16 was written at 19:12,
the surface was generated at 19:08, and `work/16.md` does not exist. A withheld
piece likewise stays visible for up to six hours. *Answer:* accept it.
`appraise.py` regenerating the surface would give an operator tool a second job
and drag the generator into its import closure for six hours of tidiness.

---

## 4. Done when

- A piece can carry the operator's yes or no and their reason, and does not
  have to.
- A piece whose newest verdict is no is not on the surface, and is still in the
  store, still signed, still re-read.
- Every note reaches the being exactly once, and a failed re-read redelivers
  rather than swallows.
- At least one re-read verdict changes because of a note — the being revising
  or retracting something on grounds it could not have reached on its own.

That last one is the whole point and it is falsifiable. If every appraised
piece still comes back `stands`, the critique is decorative and the block
should come out of the prompt rather than be made louder.

---

## 6. Red team, second pass — what the first one missed

*§3 red-teamed the idea. This pass red-teams it against the code, and two of
the findings are severe enough that the proposal should not be built as
written.*

### F1 — the success condition trips a latent signature bug *(severe)*

`apply_verdict` on a revision writes `title`, `body`, `word_count`, `status`
and `last_reviewed_at`. It does **not** recompute `signature`. Verified: the
string "signature" appears in `reread.py` only inside a comment.

`read_works.py --verify` recomputes each signature from the stored subject,
title and body, and reports a mismatch as **ALTERED** — which its own docstring
defines as *"has been edited since it was written, which for a body of work is
the thing a signature exists to catch."*

Why this has never fired: **11 intact · 0 altered · 5 unsigned**, and the five
unsigned are works 1–5, written before E3.1. Both pieces ever revised — work 1
and work 4 — are in that unsigned set. **No signed piece has ever been
revised.** Works 6–16 are all signed.

This proposal's Done-when is *"at least one re-read verdict changes because of
a note"* — that is, a revision. The first time it succeeds on any piece written
since 2026-08-21, the canonical integrity instrument will report the being's
work as tampered with. The proposal's success mode is the bug's trigger.

*This must be fixed before delivery, and the fix is a decision, not a
one-liner.* Recomputing `signature` on revision makes it attest to the current
text and silently discards the attestation for the original. The chain-
preserving fix is to store the prior signature on the `work_revisions` row —
which already keeps `prior_title` and `prior_body` and is the natural place for
it — and recompute on `works`. Either way it is a change to a signed record and
belongs in the ledger.

### F2 — the outer loop does not close: a revision cannot clear a verdict *(severe)*

The design's own logic defeats it. A piece marked `0` is withheld. The note
reaches the being. The being revises the piece on those grounds — the outcome
§4 calls the whole point. And the newest appraisal still says `0`, so the piece
stays withheld and **nothing the being did changed anything.**

That is the exact pathology `newz-design-direction` names: *"Nothing outside it
ever tells it that it was wrong."* Here something does tell it — and then the
consequence does not move when the behaviour moves, which is a worse teacher
than silence, because it teaches that acting on the critique is inert.

Two ways out, and they are not equivalent:

- **A revision invalidates the appraisal**, returning the piece to unappraised
  and therefore to the surface. The loop closes. The cost is that the being can
  un-withhold its own work by rewriting it, which hands the publish decision
  back to the being — precisely what the operator asked to take out of its
  hands.
- **The operator re-appraises revised pieces**, and `appraise.py` surfaces
  "revised since your last verdict" as its own queue. The loop closes through a
  person, which is honest about where the judgment lives, and costs the
  operator a second pass per revised piece.

The second is the right one, and it is not what the proposal says. §1.2's walk
order must change from "pieces with no undelivered note" to include "pieces
revised since their newest appraisal."

### F3 — production outruns appraisal by roughly seven to one *(structural)*

Four pieces a day is 28 a week. 16 pieces exist after six days. Nobody
appraises 28 essays a week, so the appraisal queue diverges from the moment it
is built and most pieces are never judged at all. The field would then exist
while the loop it is supposed to close stays open — a form after all, defeated
by arithmetic rather than by design.

`works/rhythm.py` already contains the answer, written before this question was
asked: *"the constraint worth respecting is not how much it can produce but
whether anything reads what it produced. **Raise it when there is a reader, not
before.**"* The ceiling was raised from 2 to 4 on 2026-08-22, when there was
still no reader.

**This proposal creates the first reader.** On the module's own stated terms
the rate question therefore reopens, and the honest recommendation is that
`MAX_STARTS_PER_DAY` should come **down** to something an operator can actually
read — one a day, perhaps two. That is a change to the being's conditions
rather than to what watches it, and it is probably worth more than the two
fields are.

### F4 — "essay pages only" is a ledger act, not a deletion

Three costs the first draft understated:

**It breaks a ledgered invariant.** INV-071 — *"The state read is a page like
any other and computes no aggregate score"* — is `consumer_traced` to
`tests/test_surface.py::test_the_read_computes_no_aggregate_score` with
mechanism `newz/surface/generate.py`. Delete `read.md` and the invariant has no
subject. INV-067's mechanism text also says in terms that the generator "writes
five `.md` pages plus one per piece and the manifest." The ledger is at **106
rows clean** today; this change makes it not clean until INV-071 is retired
with a stated reason and INV-067 is amended. That is an operator act with a
paper trail, not a deletion.

**It deletes about half of `test_surface.py`.** 28 tests; the read (6),
commitments (4), errors (1) and questions (2) tests lose their subject outright,
before counting the `index.md` assertions inside the regeneration and
retraction tests. And these are not bookkeeping — they encode decisions that
exist because their absence was a failure: *a capability that does not exist
says so* (an absent capability rendering as a blank page is indistinguishable
from a broken one), *the read computes no aggregate score*, *an ungraded metric
is not shown at all*. Deleting the pages deletes the only place those rules are
enforced.

**The nav must change, at the most sensitive point in the generator.** `_page`
hardcodes a five-page nav line and `_one_work` passes `here="index"`, so essay
pages would carry five dead links. `_page` is also INV-068's chokepoint — *"the
only way the surface produces a page"*, validating the disclosure before
assembling anything. A small edit, in the one function whose whole value is
that nothing routes around it.

None of this argues against the decision. It argues that the change is
migration-sized rather than a subtraction, and should be planned as one.

### F5 — priority ordering and at-least-once can livelock each other

§1.3 sorts pieces with undelivered notes first; §3 R2 stamps `delivered_at`
only on success. Together: a piece whose re-read keeps failing keeps its
undelivered note, therefore keeps sorting first, therefore is retried every
turn — while consuming the 2-per-day ceiling, which `starts_today` charges
before anything is spent. One re-read in six has already failed in life.

The first draft's R9 claimed "the jump is spent on delivery." It is spent on
*successful* delivery, and the failure case is exactly the one that repeats.
Needs a bound: after N failed delivery attempts the piece loses priority and
rejoins the ordinary rotation, note still undelivered.

### F6 — the blind verdict is blind only once

`--list` shows verdict history, and re-appraising a revised piece (F2) means
the operator has already read it and already ruled on it. Blindness survives
the first pass on a piece and nothing after that. Worth keeping for what it
still buys on first contact, not worth defending as a property of the tool.

### What this pass changes

- **F1 and F2 are blocking.** The signature fix and the revised-since-appraisal
  queue are part of the work, not follow-ups.
- **F3 is the recommendation worth more than the feature.** Lower
  `MAX_STARTS_PER_DAY`; it is a change to the being's conditions and it is what
  makes the rest arithmetically possible.
- **F4 means the surface reduction needs its own ledger act** before it is
  built.
