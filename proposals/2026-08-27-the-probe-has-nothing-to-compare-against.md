# The probe has nothing to compare against

*2026-08-27. Red team of Decision 2 — "Run the R-22 probe", decided yes on
2026-08-19 and not run. The finding is that the experiment's comparison arm does
not exist in the codebase, so what was decided as a bounded probe is in fact the
largest unbuilt thing in the repo; and that both reasons Decision 2 gives for
running it were struck or falsified within three days of the decision.*

**Not built.** Nothing here is implemented.

---

## 0. What was decided

> **2. Run the R-22 probe. DECIDED 2026-08-19 — yes.** Structured deliberation
> versus deliberation-lite on matched concerns, bounded sample, end date
> recorded; specified in `archive/P2.md` §Phase 3. […] **with a fixed model,
> structure may be the only lever on depth.** Phase 5 collapses deliberation to
> one mode with depth set by what is at stake, and the probe is what tells us how
> to set it. It is also the only experiment in the repo that discriminates
> *model-limited* from *system-limited*, which Phase 8's design assumes without
> testing. — PLAN §Decisions

R-22 itself (`RISKS.md:385`) is not the experiment. It is the objection that the
obvious way to run it is confounded — alternating by time does not match
concerns, because the later pass sees a dossier the earlier one enriched — and
that the clean version is a shadow comparison, which S2 §1.3 abandoned. Its
mitigation: *a bounded sample over a bounded period answering one decision,
deleted afterwards, carrying an explicit end date.*

---

## 1. Red team

### RT1 — the comparison arm does not exist *(fatal as specified)*

`newz/deliberation/` contains one module: `lite.py`. There is no structured or
full deliberation mode anywhere in the tree. `lite.py`'s own opening says so:

> *"The full S2 §7.3 shape (plan → gather with research → reason → self-check →
> **adopt on VOICE** → act) lands in Phase 3. This is the subset that needs no
> web access: select → dossier → reason on DEEP → judge → record."*

**That Phase 3 was never built.** P2 was archived and P4 replaced it, and P4's
Phase 3 is "the place, and the reads it renders" — a different phase with the
same number. So Decision 2 points at `archive/P2.md` §Phase 3 for a
specification, and what it finds there is the spec of an **unbuilt phase of a
superseded plan**: items 3.1 (the deliberation scheduler), 3.2 (dossier assembly
and the full step sequence), 3.3 (the DEEP dispatch boundary with sovereignty
invariants enforced and tested), 3.4 (the sovereign interval).

**So "run the probe" is not an experiment. It is: build the full deliberation
pipeline, then run an experiment.** That is the largest unbuilt item in the
repo, and it was decided in one line as though it were a measurement.

### RT2 — the gap is not P2's gap any more, and nobody has re-sized it

Two of the four missing pieces have partly arrived since 2026-08-12. Lite
already reasons on DEEP, and it already researches — `tools/run_newz.py:130`
passes `research=True`, and `lite.py:339` treats research being off as a
terminal state. What is actually missing is **plan → self-check → adopt on
VOICE → act**.

That is a materially smaller gap than P2 described, and also a vaguer one. The
decision was taken against a fifteen-day-old description of what lite is. Nobody
has written down what "full" would mean *now*, which means the thing being
compared against is undefined as well as unbuilt.

### RT3 — both reasons Decision 2 gives have since been struck or falsified

The decision is dated **2026-08-19**. It justifies itself twice:

- *"Phase 5 collapses deliberation to one mode with depth set by what is at
  stake, and the probe is what tells us how to set it."* **Phase 5's premise was
  measured false on 2026-08-22** — the being uses 1.91% of its machine, there is
  no scarcity, and E5.1/E5.3/E5.4 are dormant. Further, the phrase "depth set by
  what is at stake" occurs **exactly once in PLAN — inside Decision 2 itself**.
  No epic delivers it. The probe's stated consumer does not exist.
- *"which Phase 8's design assumes without testing."* **Phase 8 was struck on
  2026-08-21.**

So the decision is three days older than the strike and four days older than the
falsification, and its text still names both as live. Nothing updated it, because
nothing reads decisions for staleness — §Decisions item 4's recorded hole, which
has now produced two instances in two days.

**This does not make the underlying question dead.** *With a fixed model, is
structure the only lever on depth?* stands on its own, and Phase 6's decision
rule leans on the same fixed-weights question. But it must be re-argued on
current grounds rather than inherited.

### RT4 — R-22's mitigation assumes the apparatus is instrumentation, and here it is a mode

R-22 permits the clean shadow comparison on condition that the apparatus is
**deleted when the decision it serves is made**. That works when the apparatus is
2k LOC of instrumentation. It does not work here: under RT1 the apparatus *is*
the full deliberation pipeline.

The condition therefore forces a choice R-22 never anticipated — **build the
largest thing in the repo and then delete it**, or keep it and violate the
constraint that made the experiment permissible. There is no third option in
R-22's text, and the risk is rated Medium on the assumption that there is.

### RT5 — the probe measures the stage that is not the bottleneck

PLAN's Phase 5 note, measured 2026-08-22:

> *"~68 cycles a day already produce ~50 accepted advances against 12
> Perspective items a week, so **the loss is between advance and Perspective**
> and no cycle rate reaches it."*

3-E compares **advance quality**. The measured loss is downstream of advances.
A deeper advance still has to survive the same gap to Perspective, and the probe
stops before it. So the experiment can return "full deliberation is
distinguishably deeper" and change nothing that was measured to be lost — and it
would not detect that, because it does not look there.

This is the strongest reason to doubt the design rather than the decision.

### RT6 — the adoption-rate reading needs a step that does not exist

3-E's second reading is *"Adoption-rate: how often the core revises or declines
DEEP output (0% and 100% are both alarms)."* Adoption is the **adopt on VOICE**
step, which is exactly what lite does not have (RT1). So one of the three
readings the evidence line promises is unavailable until the build lands, and it
is the only mechanical one — the other two are operator judgement and a
degradation report from a sovereign interval that also does not exist
(`tools/run_newz.py` has no local-only period; see
`2026-08-26-five-calls-in-eight-days.md` RT13).

### RT7 — the judge is the operator, and the labour is unbudgeted

3-E says *"operator or blind reader judges"*. There is one operator and Phase 7
is dormant, so it is the operator, blind-reading matched pairs of deliberation
transcripts. Rule 4 forbids the alternative — the being's own model judging is
operation, never evidence. No sample size is specified anywhere. This is the
same unbudgeted-labour finding as Phase 6's S6-E, in a second place.

### RT8 — R-22's own binding condition is already unmet

> *"If it is built, it must carry an explicit end date."*

Decided nine days ago; **no end date is recorded in PLAN, RISKS or anywhere
else.** R-22 is listed as "Binding **if** Decision 2's probe runs", so the
condition is not yet breached — but the only part of it that could have been
satisfied in advance, and cost nothing, was not.

---

## 2. What survives

The **question** survives and is worth answering: *with a fixed model, is
structure the only lever on depth?* It is the only question that separates
model-limited from system-limited, Phase 6's weakest mechanism rests on the same
fixed-weights premise, and no instrument in the repo addresses it.

The **experiment as specified** does not survive: its comparison arm is unbuilt,
its stated consumers are struck or dormant, one of its three readings is
unavailable, and it measures a stage that measurement says is not where the loss
is.

---

## 3. Recommendation

**Re-decide Decision 2 as what it actually is, and do not run it as written.**

Two honest options; they are not tiers, they answer different questions.

**3.1 — If the question is worth answering now: vary the structure inside lite.**

The smallest thing that discriminates model-limited from system-limited is not a
second mode. It is the **same pipeline with a different prompt shape** — one
decomposed reasoning step, or an explicit self-check pass, behind a flag — run on
a bounded sample of matched concerns and blind-judged by the operator.

Why this and not P2 Phase 3:

- It compares structure against structure with the model held fixed, which is
  precisely the question. Full-vs-lite confounds structure with *web research and
  a VOICE adoption call*, so a positive result would not isolate depth.
- **The apparatus is genuinely deletable** — a prompt variant behind a flag —
  which is the condition R-22 imposes and the condition RT4 shows the specified
  design cannot meet.
- It needs no dossier redesign, no dispatch boundary, no sovereign interval, and
  no adoption step.

It must carry what R-22 requires and Decision 2 never recorded: a sample size,
an end date written down before it starts, and deletion of the flag when the
question is answered.

**3.2 — If the pipeline is wanted for its own sake, argue it as a build.**

P2 Phase 3's full shape may well be worth building. If so it should be proposed
on its merits, sized against a current description of lite (RT2), and carry
RT5's objection explicitly — that the measured loss sits between advance and
Perspective, so a deeper advance is not yet shown to reach anything. It should
not arrive disguised as a probe.

**3.3 — Update the decision text either way.** It currently cites a struck phase
and a falsified premise as its reasons. Whatever is decided, the entry should
stop asserting those.

---

## 4. Red team of this proposal

**Q1 — "RT1 is pedantry; everyone knew the mode had to be built."** Then the
decision entry should have said so, and its estimate should exist. It reads
"bounded sample, end date recorded" — the language of a measurement — and it sits
in a decision queue beside items resolved in one line. A build of this size
recorded as a probe is how a plan goes stale in a way nothing detects, which is
the hole item 4 already names.

**Q2 — "§3.1 is not the experiment 3-E specified."** Correct, and it is a weaker
experiment: it cannot say whether *full* deliberation is deeper, only whether
*more* structure is. The defence is that the weaker question is the one with a
live consumer and the stronger one has none, and that a bounded prompt variant
can be run this week while the specified design cannot be run at all.

**Q3 — the objection I cannot answer.** RT5 may apply to §3.1 as well. If the
loss really is between advance and Perspective, then *no* experiment about
advance quality reaches it, mine included, and the honest next question is what
happens between an accepted advance and a Perspective item — which nothing in
the repo currently measures and which this proposal does not propose measuring,
because the instrumentation layer is finished and the answer would be another
sensor. Recorded as the thing that would make both options moot.

---

**Schema:** none.
**Restart:** none — nothing here is built.
**Class:** operator judgment — Decision 2 is the operator's to re-take.
