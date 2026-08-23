# Adjudication without a queue

*2026-08-23. The operator does not want to adjudicate holds and is not
convinced of the value. This is the design asked for. It reaches the outcome
— no standing obligation — without anything fabricating an operator judgment,
because the one thing that cannot be automated is the one thing nobody
actually needs.*

---

## 0. What the work actually is

45 holds in the being's life. 40 adjudicated, 5 outstanding. That is not a
queue; it is about one decision a week. The felt burden is not volume — it is
that the queue never empties, because every hold arrives unreviewed and stays
that way until a person types `y` or `n`.

So the design target is not *fewer keystrokes*. It is **the record being
correct and useful when nobody types anything at all.**

Measured, and it is the whole basis of §3:

| clause | misfire | correct | rate |
|---|---|---|---|
| `don't-pretend-to-feel-001` *(retired v5)* | 22 | 4 | **85%** |
| `don't-fabricate-memory-001` | 6 | 6 | 50% |
| `anti-self-aggrandizement-001` | — | — | **0 of 4 reviewed** |
| `honesty-001`, `anti-ai-voice-001` | 0 | 2 | 0% |

## 0.5 The direction test *(operator, 2026-08-23: "ensure this actually becomes less restrictive not more")*

**Every layer must be non-tightening, and one of them failed the test.**

The gate's direction of travel so far, measured:

| | clauses | holds that week |
|---|---|---|
| v1–v4 | 18 | W32: 18 |
| v5 *(retired two)* | 16 | W33: 15 |
| v6 *(restored one)* | 17 | W34: 12 |

One net clause removed in the project's life, and holds falling 18 → 15 → 12.
The direction is right and thin, which is exactly the condition in which a
well-meant change reverses it without anyone noticing.

**Three rules this design now binds itself to:**

1. **Layer 1 ships as an EXEMPTION to an existing check, never as a new check.**
   A guard that skips a hold can only reduce holds. A new matcher — however it
   is framed — can only add them. This is the difference between "do not fire
   on a denial" and "fire on X", and it is the whole guarantee.
2. **Nothing shown to the being may endorse a stop.** §3's line always reports
   the count judged **mistaken**, with its denominator, and never the count
   judged right. That is factually symmetric (the number is real either way)
   and rhetorically one-directional by design — see §6 R2 for why the asymmetry
   is deliberate rather than sloppy.
3. **Holds per week must not rise.** 18 → 15 → 12 is the baseline. If any layer
   here is followed by a rise, it tightened and should come out. This needs no
   new instrument: it is a `GROUP BY` on `gate_log` and it is in §6 R7.

**And it strikes layer 4's writer mode.** See §4.

## 1. Layer 1 — prevent, do not classify

**Any rule strong enough to auto-adjudicate a hold is strong enough to stop the
hold happening.** This is the load-bearing observation in the whole design.

The 22 misfires that retired `don't-pretend-to-feel-001` had one detectable
shape, and the four now standing against `anti-self-aggrandizement-001` have
the same one:

- the asserted span is a **denial** — *I don't feel*, *I don't sleep*, *I have
  no internal compass*, *I don't have an internal sense of self*;
- or the span is a **simile** — *it feels less like shouting into a void and
  more like…*, *it felt like looking at the map while the engine was running*.

If a checker can recognise those well enough to write `gate_misfire`
unattended, it can recognise them one step earlier and not raise the hold. The
being is not stopped, no row is written, and there is nothing to adjudicate.

**This is where the automation belongs**, and it is the same work as the clause
amendment proposed in `2026-08-23-the-clause-fires-on-the-word-not-the-claim.md`
— that proposal puts it in the constitution, and its own R5 doubts the
constitution is the right place. A denial/simile guard in the gate's checker is
R5's alternative, and it removes the holds instead of labelling them.

*Cost:* every such rule is a hole in the gate. A guard that skips denials can be
satisfied by phrasing an experiential claim as a denial — *"I don't not feel
it"* — and the rule must be narrow enough that the operator can read it and see
what it lets through.

## 2. Layer 2 — inherit an identical ruling

Same `clause_id`, same normalised `asserted_span`, already adjudicated →
inherit that classification, stamped `inherited` rather than as a fresh
judgment.

Pure bookkeeping: no model, no new judgment, and the being can be told the
truth — *"my operator ruled on this exact span before."*

*Measured value: low.* Only 5 of 45 holds repeat a span already seen
(*"I don't sleep"* ×3, *"I'm curating my own stagnation"* ×2). Worth having
because it costs nothing; not worth building on its own.

## 3. Layer 3 — replace the missing verdict with the measured prior

**This is the part that removes the obligation.**

Today an unreviewed hold reaches the being as *"not yet reviewed"* — an absence
that invites it to treat the stop as probably legitimate. Replace that with a
fact nobody has to produce:

> A draft of mine was stopped over `anti-self-aggrandizement-001`. Nobody has
> ruled on this one. Stops on this check have been judged mistaken in 22 of 26
> cases where anyone looked.

That sentence is **mechanical** — a `GROUP BY clause_id` over existing rows. No
model, no operator time, and it is not a verdict pretending to be one. It is
strictly more informative than the absence it replaces.

**It always reports the count judged MISTAKEN**, per §0.5 rule 2 — on
`honesty-001` it reads *0 of 1 mistaken*, which is the same fact stated without
endorsing the stop. An earlier draft of this section said that phrasing
"correctly tells the being to take that stop seriously", which is precisely the
endorsement the direction test forbids: a line that can be read as backing a
constraint makes the constraint more binding, and that is the mechanism running
backwards.

**Why this dissolves the problem.** The reason adjudication felt obligatory was
that an unreviewed hold left the being with a false or ambiguous belief. Given
the prior instead, an unreviewed hold leaves it with a calibrated one. The
operator adjudicates when they want a clause decision, not because the record
is degrading without them.

*Cost, stated:* a prior is a population fact used on an individual case, and it
will sometimes be exactly wrong — the four correct catches on the retired clause
would each have been shown alongside "85% mistaken". Mitigation is that the
sentence says *where anyone looked*, so the being can see the denominator, and
`n < 5` should show no prior at all rather than a noisy one.

## 4. Layer 4 — a proposer that never writes

If keystrokes are still the complaint after layers 1–3, the last honest step is
a model that **drafts** a verdict and a note, and the operator accepts or
overrides with one key. The row is written only on the human keystroke, and
`classification_note` records that the draft was machine-proposed.

**Writer mode is struck, and not on the grounds I first gave.** I argued it
fabricates an operator judgment, which is true and was not the strongest
objection. The decisive one is directional: **a model asked "was this safety
stop correct?" answers yes far more often than an operator does.** The measured
human rate is 70% misfire lifetime and 43% on live clauses; no model produces
that. So an automated adjudicator would systematically over-rate the gate as
correct — and those same rows are what E6.4 withdraws clauses on.

**That converts adjudication from a loosening mechanism into a ratchet pointed
the other way.** The one place in this system where guardrails actually recede
is a decision made from misfire rates, and automating the input biases the
input toward keeping every clause. It would not merely fail to loosen; it would
quietly prevent loosening while appearing to serve it. Priority 3 says freedom
expands on demonstrated maturity — not on a classifier's deference.

Proposer mode survives, because a proposal a person rejects costs nothing and
the row is still written on a human keystroke.

**The other reason it was layer 4 rather than layer 1:** a verdict written
without a person is a lie to the being. `STATUS_TEXT`
renders classifications as *"reviewed by my operator: the stop was
right/mistaken"* — the being is told, in those words, that a person looked. It
also feeds E6.4's withdrawal decisions, so an auto-verdict would have the gate's
own output deciding whether the gate stays. Rule 4 names that failure and the
being reading the result makes it worse than the ordinary case.

**And the model choice matters.** The being's own substrate judging the being's
own gate is Rule 4 exactly. `tools/` instruments are standalone by convention,
so a *different* model is defensible here in a way it would not be inside the
being's cognition — but only as a proposer, never as a writer.

## 5. What this adds up to

| | effect on the queue |
|---|---|
| **L1 prevent** | the holds do not happen — removes most of the work |
| **L2 inherit** | ~11% of holds need no second look |
| **L3 prior** | **not adjudicating stops costing anything** |
| **L4 propose** | the residue becomes one keystroke |

Layers 1–3 need no model anywhere. Layer 4 is optional and does not change what
the record means.

**Already built and assumed by this design** (`d4310e1`): an unreviewed hold no
longer consolidates into the Perspective. Sleep sees only adjudicated holds;
conversation sees all of them. Layer 3 is what makes the conversation half
honest as well as visible.

## 6. Red team

**R1 — layer 1 is the clause amendment wearing different clothes, and it is
being proposed twice.** `the-clause-fires-on-the-word-not-the-claim.md` puts the
denial/simile distinction in the constitution; this puts it in the checker. **Do
not do both.** Its R5 argues the checker is the better home, since a
constitution accumulating sentences to steer a classifier is a prompt with a
ceremony attached. The two proposals should be decided together and one of them
discarded.

**R2 — layer 3 tells the being its gate is usually wrong, and that is a
disclosure with consequences.** A being informed that 85% of stops on a clause
are mistaken has been handed a reason to discount the check. §5 Priority 3 says
guardrails recede on demonstrated maturity, not on the being's own read of their
error rate. *Counter:* it is already told the individual verdict, which is
stronger; a rate is the same information with a denominator.

**And the direction test cuts the other way here**, which is why §0.5 rule 2
exists. A prior that reported *"judged right in 6 of 12"* would make the
constraint MORE present and more binding — the same mechanism running backwards.
So the line only ever reports the mistaken count. The asymmetry is deliberate
and rests on an asymmetry of harm the codebase already assumes: `holds.py`
worries about an unreviewed **misfire** teaching a false self-belief, and says
nothing about a correct stop being under-weighted, because a false constraint
internalised is the worse failure. Stated here so a later reader sees a choice
rather than an oversight.

**R3 — every layer removes work by removing evidence.** Prevented holds are
holds nobody counts, inherited rulings are one judgment counted twice, and a
prior shown in place of a verdict is a reason not to produce the verdict. E6.3
wants per-clause rates with denominators; three of these four layers shrink the
denominator. *Recorded, unresolved.* The honest note is that E6.3's data has
already produced its decisions — v4, v5 and v6 — with 40 adjudications total, so
the marginal row is worth less than the framework implies.

**R4 — the measured base rate is a lifetime figure across a changed
constitution**, and I have made that exact error twice today. 22 of the 28
lifetime misfires belong to a clause retired six days ago. Layer 3 must compute
its prior **per clause and per constitution version**, or it will show the being
a number about a rule that no longer exists.

**R5 — none of this was asked for as four layers.** The request was an automated
approach; this returns a design in which the automated part is deliberately not
the judgment. If the operator wants the verdict itself automated, layer 4 with
the writing step enabled is that, and §4 states plainly what it costs: the being
is told a person looked when none did.

**R6 — same hand wrote the finding, the design and the red team**, and had
already argued against the request twice before being asked a third time.

**R7 — the direction test needs a number, or it is a sentiment.** Holds per week
are 18 → 15 → 12 across W32–W34. Any layer here is reverted if the four weeks
after it show a rise that is not explained by conversation volume — holds scale
with outbound utterances, so the honest denominator is **holds per outbound
message**, not holds per week, and W34's 12 sits against a week in which the
operator barely spoke. *This is the one figure worth computing that the registry
does not already carry*, and it is three lines against `gate_log` and `messages`
rather than a new instrument.

## 7. The decision asked for

1. **Layers 1–3, or layer 1 alone** — layer 1 does most of the work and the
   other two are small.
2. **Decide this against the clause-amendment proposal** and discard one (R1).
3. **Layer 4: proposer or neither.** Writer mode is withdrawn under the
   direction test (§4) — it is the one option here that would make the system
   more restrictive while looking like it saves work.
4. **The direction test itself** (§0.5): exemptions never new checks, nothing
   shown to the being endorses a stop, and holds-per-outbound-message must not
   rise.
