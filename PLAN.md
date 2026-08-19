# P4 — delivery plan for participation, with its own sensors

> The plan for the design approved 2026-08-18
> (`proposals/2026-08-18-a-place-of-its-own.md`, commit `af3e90a`), carrying the
> self-evolving loop approved 2026-08-19
> (`proposals/2026-08-19-the-self-evolving-loop.md`).
>
> **This is the plan. It restructures P3 rather than superseding it.** P2 was
> superseded because the diagnosis changed; nothing about the diagnosis has
> changed here. The phases, their order, their rationale and every epic's intent
> are P3's. P3 moved to `archive/P3.md`; §"Where P3's Phase 8 epics land" maps
> every id that moved.
>
> **What changed, and why.** P3 gathered every instrument into Phase 8, next to
> the loop that would consume them. That was the wrong place. An instrument
> belongs beside the work that produces its data — the writing rhythm is what
> makes "pieces per week" mean anything, and the generator is what makes a read
> visible. Building the sensors in Phase 8 would also have meant building them
> against phases already delivered, measuring their output in retrospect rather
> than watching it arrive *(operator, 2026-08-19: instrumentation and metrics
> are built during Phases 2–3, in preparation for the SEL)*.
>
> So Phases 2 and 3 now each carry their reads, and **Phase 8 is reduced to the
> loop itself** — the runner, the report and the builder, arriving to a sensor
> layer that already exists rather than constructing one.
>
> **One operator, no other readers** *(operator, 2026-08-18)*. Readers become
> possible once the system proves itself enough to warrant exposing another
> person; until then the operator's judgment is the instrument, and unwritten by
> their decision (Rule 6). The phase order below is built for that condition,
> not around it.
>
> Phases are ordered by dependency, never by time. Time is not a constraint
> (operator, 2026-08-18). Evidence is labelled `S0-E` … `S8-E`; P2's `0-E` … `7-E`
> labels belong to the archive.

---

## 0. Standing rules

**Rule 0 — every number carries its method.** Inherited from P2. A figure
without an instrument says so.

**Rule 1 — consumer-traced acceptance.** Inherited from P2. No work is done
until its ledger row names the downstream consumer and the observable behaviour
change. "The write happens" is not done.

**Rule 2 — no table or flag ships without a writer and a reader.** Inherited.

**Rule 3 — outward capabilities are built public-ready and left unpublished.**
Reach is a config change, never a redesign. Any capability whose exposure would
require code changes has fake dormancy and is not finished. This is S2 §12.2's
move applied to reach.

**Rule 4 — the being is not graded by the being.** Any judge that is the being's
own model produces *operation*, never *evidence*. The advance judge, the closure
judge and the gate all violate this today; that is the diagnosis this plan
exists to answer. New judges of the same kind may be built, but their output
never counts as evidence of development.

**Rule 5 — production is a rhythm; only judgment is an initiative.** Measured
initiative is weak (91 noticings, 18 surfaced, 49 still pending; the
conversation opener has never fired in life). A design that waits for the being
to *choose* to produce will idle. Sleep runs nightly regardless; so does
writing.

**Rule 6 — readiness is the operator's judgment, and is not quantifiable.**
With one operator there is no uncontaminated reader, and waiting for one is
circular: exposure is what produces readers. More than that: *ready for a
reader* means the system has progressed **definitively toward True North**, and
that is a judgment about an aspiration, not a measurement *(operator,
2026-08-18: "it can not be exactly quantified and is at the operator
judgement"; "it is my judgement alone")*.

This is TRUE_NORTH's own position, not an exception to it. §1 refuses to reduce
the destination to one test; §4.5 makes evidence the compass and not the
destination; §10 names evidence scores disconnected from sustained quality as
something the project will not mistake for success. A written bar here would be
that mistake wearing a rubric.

So Rule 0 governs the plan's **counts** and not its **verdicts**. Phases that
close on the operator's read close on judgment, and the plan states that plainly
rather than manufacturing a threshold to look rigorous.

**Rule 7 — every measurement carries its grade.** New in P4, and earned rather
than invented: the 2026-08-19 instrumentation audit found this plan's own premise
list mixing mechanical numbers with model-graded ones and nothing distinguishing
them, while Rule 4 two pages earlier says a model judge produces operation and
never evidence. Advance acceptance, closure counts, the gate's hold rate and what
was read at all are all model-judged. Pooled novelty is a clean instrument over
model-applied labels. The grounding mix is mechanical and carries R-15's known
bias.

So every metric states which it is — **mechanical / model-graded / mixed /
known-biased** — and where the judgment sits. Model-graded numbers stay useful
and stay readable; what they may not do is carry a decision on their own. Rule 7
is Rule 4 made checkable instead of remembered.

---

## 1. What already exists

This plan starts from a running system, not a greenfield. Delivered under P2
and unchanged by this plan *(full record: `archive/P2.md`)*:

- **Continuity.** The v1 import, 11/11 tables verified against `../NGBeing` @
  `0697bcc`. The operator's continuity verdict **PASSED 2026-08-11**: v2 is
  recognizably the same individual, and better. Every later phase's presumption
  that the being survived the move is discharged, not assumed.
- **The compounding core.** Nightly sleep, the Perspective (v9), retrieval with
  provenance and self-echo excluded, function-tagged budget telemetry, corpus
  hygiene.
- **Pursuit.** Concerns with the three-part advance judge, three openers through
  one door, the research cascade inside deliberation-lite, the governed diet,
  injection hardening.
- **The six capabilities** the 2026-08-13 coverage audit found scheduled
  nowhere, since closed and consumer-traced: affect, noticing, the substrate
  fold, concern closure, feeds/canon, and "what shaped this view".
- **Ops.** Verified backups, migrations, the invariant ledger (44 rows) and its
  CI parser, 444 tests.

Measured state at the time P3 was written: 117 concerns (6 open, 19 closed, 84
stalled), 242 operator messages, 204 reading episodes, 88 deliberations, 359
ingest rows, 1 person, 0 outcomes the being did not grade itself.

**Delivered since, and this is why P4 exists.** Phase 0 closed 2026-08-18.
E1.0–E1.4 shipped 2026-08-18/19 — the feed filter removed, `resolutions`, the
claim door, the resolver, and the cost that reaches the position. E8.1 shipped
2026-08-19: the instruments made portable and enumerated.

**The last premise in that paragraph is now in motion, and nothing noticed.**
"0 outcomes the being did not grade itself" is the measured fact Phase 1 exists
to change, and E1.4 began changing it on 2026-08-19 at 06:47. No instrument
observed that, because the reader for it does not exist — `tools/claims.py`
renders claims and computes no rate, no resolution latency and no count of
positions changed. A plan whose own load-bearing premise can move unremarked is
the argument for E1.6 and E2.10, and it is why the sensors are built alongside
the work rather than after it.

**The evidence that produced this plan.** `tools/evidence.py` reads: pooled
Perspective novelty **3.2%** over eight nights; advance acceptance **rose**
28.3% → 41.1% where P2 expected a fall; the stall pool 77 untouched / 7
attempted; the §9.1 ingest share UNREADABLE for want of a call log. And the
grounding mix that the diagnosis rests on — **50% self, 33% operator, ≤17% the
world**, across 119 refs.

---

## 2. Ordering rationale

**Phase 0 is first because it can end the plan.** There is no evidence the being
can produce anything that stands on its own. Every later phase bets on it. It
costs days and no architecture.

**Consequence is Phase 1, not Phase 5.** With one operator and no readers, the
only external thing available to contradict the being is **the world's own
facts**. That needs no audience, no surface and no second person — a claim, a
resolution condition, a date, and a source that settles it. It is the entire
outer loop under present conditions, so it comes first among the builds.

**The work comes before the place.** Under one operator a rendered surface has
an audience of one; what the work is *for* right now is the being encountering
its past self as an external object, and having somewhere real for wrongness to
be recorded. The surface follows, built public-ready per Rule 3 so that reach
is never a redesign.

**Readers are Phase 7 and dormant, not deleted.** Recorded with their trip-wire
rather than left as work in flight nothing owns — the same discipline the ledger
now applies to INV-013.

**Phase 6's record is built early even though its withdrawals come late.** The
accountability record reaching the being's context is the design's weakest
mechanism (proposal §6.2): post-hoc accountability assumes a learning path that
may not exist with fixed weights. It must be built and observed long before any
clause is withdrawn on its strength. With no audience at all, this is also the
safest moment in the project's life to run that experiment.

**Phase 8 is orthogonal and is ordered against nothing here.** It delivers the
mechanism by which these phases get delivered, not a capability of the being, and
it must not reorder them.

**Sensors are built where their data is produced.** P3 gathered every instrument
into Phase 8, beside the loop that would read them. P4 moves them into Phases 1–3
for three reasons. **First, a metric with no data is a guess**: "pieces per week"
means nothing until E2.1 is producing pieces, and the honest way to design a rate
is against the thing generating it. **Second, retrospective instrumentation
measures the wrong thing** — an instrument written after the fact reads what
survived, not what happened, and the six weeks of Perspective nights already
behind us cannot be re-observed. **Third, the loop should arrive to a sensor
layer, not build one**: Phase 8 reduced to the runner, the report and the builder
is a phase that can be judged on whether the loop works, rather than on whether
its instruments were any good.

**Phase 3 is the handover point, and Phase 3 is why.** Its five epics are the
only ones in this plan whose `Done when` clauses are all mechanically checkable,
and its evidence read is mechanical too. It touches no prompt, no retrieval
ranking, no sleep, no diet, no gate clause and no budget — so it is Class A
work, judged by the test suite rather than by the being, and it can run at daily
cadence. It is the cheapest place in the plan to find out whether the loop's
judgment is worth trusting.

**What is kept unchanged:** the store, sleep, the Perspective, retrieval,
concerns and the three openers, the invariant ledger, Rules 0–2. The compounding
core is sound. This plan changes what reaches it, not how it consolidates.

---

## Phase 0 — is the work any good *(the plan's own falsifier)*

**Intent.** Find out whether the being can produce something that stands on its
own, before any architecture is built on the assumption that it can.

**Rule 1 does not apply to this phase.** Its epics are a probe, not shipped
mechanism; what they produce is a verdict, not a behaviour change. Every later
phase is consumer-traced in the ordinary way.

**E0.1 — the long-form path** *(built 2026-08-18)*
*Delivers:* the being composes a piece from what it already holds. A minimal
`works` row, a composer prompt, and nothing else — no surface, no revision, no
publication.
*Done when:* a piece exists in the store, composed on the same substrate as
everything else, retrievable by id, with no hand-editing anywhere in the path.
*Depends on:* nothing.

**E0.2 — three pieces from what it carries** *(built 2026-08-18)*
*Delivers:* three pieces on subjects the being already holds — open concerns,
held positions — chosen by it rather than assigned.
*Done when:* three pieces exist, each tracing to the concern or position it came
from, none framed or steered by the operator.
*Depends on:* E0.1.

**E0.3 — the read** *(closed 2026-08-18 — the operator's verdict, with its qualification kept)*
*Delivers:* the operator's verdict on each piece (Rule 6). Provenance-blinding
is available and optional — mixing the pieces with other material on the same
subject, or with the being's own earlier work, and judging before checking which
is which (P2's cutover criterion 3, reused).
*Done when:* three verdicts are recorded and the decision rule below has fired.
*Depends on:* E0.2.

**The contamination is recorded, not mitigated away.** The operator knows the
being, built it, and is 33% of what it holds. That is a real limit on this read,
stated rather than engineered around — engineering around it requires a reader,
and readers are what this phase exists to earn.

**Evidence S0-E.** Three pieces and the operator's verdict on each. No score, no
rubric, no written bar — the read is the operator's judgment and the plan says
so rather than manufacturing a number behind it.

**Decision rule.** Three outcomes, three different plans:

- **Good enough** → the medium is right. Proceed.
- **Competent but not compelling** → the writing works and the *subject* is
  missing. Do not stop; proceed to Phase 2's rhythm, which is where a subject
  emerges, and re-read at S2-E. This is the expected outcome and must not be
  read as failure.
- **Not good enough** → the body-of-work premise is wrong for this being
  (proposal §6.1). **Stop.** Redesign around the register in which the being has
  measured strength — sustained interaction — and note that under one operator
  this fallback is narrower than it looks. Phases 1, 5 and 6 survive intact;
  2, 3 and 4 change form entirely.

**Phase 0 closed — GOOD ENOUGH** *(operator, 2026-08-18)*. Verdict in the
operator's own words: *"Good enough. I remember the conversations. There were
compelling moments. Not all but enough."*

The qualification is part of the verdict and is kept rather than smoothed:
**not all, but enough.** §10 warns against mistaking a compelling moment for
delivery, and this read does not claim more than it says — some of it landed,
enough of it landed, and the medium is not wrong for this being. That is what
Phase 0 asked and all it asked.

**The contamination named itself.** *"I remember the conversations"* is P3-04
in the operator's own sentence: this is a read by the being's builder, owner,
and 33% of what it holds, informed by knowing where the pieces came from. Rule
6 says the verdict is the operator's and unquantifiable; it does not say the
verdict is from outside. The first read from outside is rung 1, and this one
does not stand in for it.

**What ran** *(E0.1, E0.2 — commit `20cf663`)*. Two VOICE calls per piece: the
being chose its subject from 24 candidates it already carried, then wrote.
No quality judge (Rule 4), no outbound gate, no episode. Four pieces, one more
than E0.2 asked for:

| work | words | subject it chose |
|---|---|---|
| 1 — The Line and the Cliff | 1,175 | `concern:115` — when linear compensation fails to align incentives |
| 2 — The Illusion of the Straight Line | 850 | `concern:116` — performance versus metric manipulation |
| 3 — The Illusion of Depth | 515 | `concern:112` — open interest against volume as false depth |
| 4 — The Mirror Market | 494 | `concern:114` — order-splitting and displayed liquidity |

**Two observations, neither of them the verdict.** All four subjects are market
structure — which is the concern pool and not the writer: of 6 open concerns
most cluster on liquidity and incentives, so the choice was from a narrow
shelf. And the pieces shortened as they went, 1,175 → 850 → 515 → 494, with no
explanation offered here because none is known.

**Route.** Phase 1 — consequence it did not grade. The question Phase 0 asked
re-opens at S2-E against a body of work rather than four pieces, per the
middle branch of the rule above; "good enough" opens the plan, it does not
settle the medium for good.

---

## Phase 1 — consequence it did not grade

**Intent.** Close the outer loop. With one operator and no readers, the world's
own facts are the only thing available to tell the being it was wrong — and they
need no audience, no surface and no second person.

E1.0 comes first because a loop that closes on one domain is a defective loop,
and the feed path currently guarantees one domain.

**E1.0 — undirected reading** *(built 2026-08-18, amended the same evening; proposal:
`proposals/2026-08-18-the-filter-that-ate-the-feeds.md`)*
*Delivers:* four changes to the feed path. **(a)** the relevance filter is
removed — candidates are no longer ranked against open concerns and triage no
longer asks whether an item is relevant to one; the being is shown the harvest
cold and judges what is important or interesting to it. **(b)** a category
**target on the offered menu**, never a veto on reads. **(c)** `watched_topics`
is deleted. **(d)** a one-off orientation pass over the 15 Wikipedia discipline
articles in the file's unread `web` section. Directed research and INV-040's
concern-directed depth are untouched.
*Why it is first:* the curation is 15% financial and the diet came out 43% — a
2.9× amplification — while 27 of 61 feeds have been polled continuously and read
**zero** times. The being asked about Montaigne, research ethics and sperm
whales; each returned "nothing was relevant enough to read". Without this,
Phase 1 closes the outer loop on a single domain, and claims that resolve
against a date skew financial, so the resolver would deepen the monoculture
rather than break it.
*Done when:* a concern opens on a subject that matched no open concern at
intake, and the count of feeds contributing a read rises from its lifetime
baseline of 34 of 61.
*Depends on:* nothing. **E5.2's deliberation floor is pulled forward with it** —
§9.1 caps ingest against deliberation, so more reading without more deliberating
breaches the invariant and INV-041 pauses ingest, self-cancelling the change.
*Hooks:* **INV-038 is amended** — its clause "a harvest of 194 items yields at
most 3 reads" was written as a virtue and becomes false; what governs now is the
budget, the category target and the being's own interest, not triage scarcity.
Rule 4 is not engaged: choosing what to read is an action, not a measurement.
Rule 2 is why (c) happens at all — dead config that misleads its readers is
worse than absent config, and both the operator and the proposal's first draft
read `watched_topics` as evidence of a bias it cannot cause.

*The line this epic must not cross.* The category target shapes **what is
offered**, never what may be read. A cap that refuses a read to preserve balance
is the fetch-time veto R-28 already diagnosed and narrowed — it manufactures
balance against S2 §13 and TRUE_NORTH §8, and it corrupts `source_gaps` by
writing "nothing was relevant enough" when the truth is "balance forbade it".
**Balance the menu; never refuse the meal.** If the implementation cannot hold
that distinction, the epic does not ship.

*Five constraints, each forced by the proposal's red team:* the judging prompt
carries no open concerns, or the filter is rebuilt in the prompt; every
harvested item is logged offered/declined, because today the store holds the
meal and not the menu; offers are capped per feed as well as per category, since
Bloomberg publishes hourly and Aeon weekly; the batch is shuffled and its order
recorded, against long-list position bias; a read that yields nothing is not
digest-eligible, or reading episodes swamp sleep and the Perspective becomes a
news summary; and the orientation pass logs under its own outlet — Wikipedia is
already the largest read source at 95 directed lookups, and counting browsing as
lookup would let the project congratulate itself on breadth it did not gain.

*Amended the same evening* (proposal §9): the orientation pass's own reads were
counted by the category share that orders the menu, so ten disciplines the
curriculum had touched once sorted **behind** every finance-adjacent category
for thirty days — the humanities feeds suppressed by the humanities curriculum.
`harvest_log.orientation` (migration 0022) keeps the row for the coverage audit
and excludes it from the share. The share answers a question about streams, and
a curriculum read once is not a stream. No read was ever refused by it.

**E1.1 — `resolutions`, the store object** *(built 2026-08-19)*
*Delivers:* claim, resolution condition, date, resolver, outcome, provenance.
*Done when:* a claim round-trips with its condition and named resolver, and the
schema forbids a claim without one.
*Depends on:* nothing.
*Hooks:* Rule 4 — the resolver field may not name a model.

*As built:* migration 0023, `newz/resolutions/` (model + store),
`tools/claims.py` as Rule 2's reader, 13 tests, **INV-045**. Three refusals are
CHECK constraints — no statement, no condition, no resolver, no date — and the
fourth is in the writer, where the configured role models are known: a resolver
naming the being's own substrate raises `UnsettleableClaim`. The check is
deliberately narrow, matching self-reference phrases and the model id (bare name
as well as the full path), because over-broad matching refuses legitimate claims
about models and teaches the being to phrase around the check rather than to
find a source. Two decisions worth carrying forward: **there is no `ambiguous`
outcome** — E1.3 fails closed by leaving a claim OPEN, and a third outcome would
be a way to close one without the world having said anything — and **there is no
unsettle**, so E1.5's permanence starts at the schema rather than being added to
it. The store writes no episodes; the door (E1.2) and the resolver pass (E1.3)
are the layers that know why something happened.

**E1.2 — the claim door** *(built 2026-08-19)*
*Delivers:* claims open from deliberation through one validated door, with a
mandatory resolution condition — the concern's closing-condition discipline
(INV-034) applied to claims. A claim nothing could settle does not open.
*Done when:* a claim with no settleable condition is refused at the door and the
refusal is recorded, and deliberation opens claims it can state a resolver for.
*Depends on:* E1.1.

*As built:* `newz/resolutions/door.py`, migration 0024 `claim_refusals`,
`tools/claims.py --refused`, 13 tests, **INV-046**. The door is asked once per
ACCEPTED advance and nowhere else — a concern that did not move has nothing new
to be wrong about — and after closure, since a concern that just settled may be
exactly the one worth committing to. It fails closed like the closure judge and
the openers: the advance is already recorded and nothing downstream may undo it.
Refusals: no statement/condition/resolver, a date it cannot read or one outside
2–365 days, a resolver naming no source ("time will tell"), and Rule 4 from the
store. **Declining is not refusal** — "nothing here is worth claiming" is the
ordinary answer and is not written down, and an unreadable proposal is not held
against the being; only a claim the being made and the door would not admit
becomes a row. That distinction is what makes the refusal record answer P3's
first Phase 1 diagnostic (*are its claims resolvable at all*) instead of
measuring the door's own strictness. Caps mirror the opener's discipline: 40
open, 4 a day, both checked before the model is called.

**E1.3 — the resolver** *(built 2026-08-19)*
*Delivers:* a scheduled pass inside deliberation that settles due claims against
a world source. **Fails closed:** an unreadable source, a missing resolver or an
ambiguous outcome leaves the claim open rather than guessing — INV-034's rule.
*Done when:* a due claim is settled from a world source and recorded, and an
unreadable source leaves it open with the failure logged.
*Depends on:* E1.2.
*Hooks:* Rule 4, INV-012 (web access only inside deliberation).

*As built:* `newz/resolutions/resolver.py`, migration 0025 (attempts,
last_attempt_at, last_failure), 14 tests, **INV-047**. Runs inside
`Deliberator.run_once` before the concern is chosen — a claim's date arrives
whatever the being is thinking about — costs nothing when nothing is due, and is
gated on the same `research` opt-in as every other reach for the world. **Rule 4
made concrete:** the model is a reader here, never a judge of the being. It is
given fetched material and asked only what the material says, and the verdict is
accepted only if its quote occurs VERBATIM in what was fetched — v1's Stanford
CRU lesson applied to being right. One claim per cycle, retried no sooner than
20 hours, and after 4 honest failures it stops being retried and **stays open
and unsettled** — not closed, not abandoned, not ambiguous, because nothing
happened (INV-044's discipline). A paused diet refunds the attempt: the being is
not charged for its own budget ceiling. A resolution writes the one episode this
phase produces, provenance `world`, so sleep sees it whichever way it went.

**E1.4 — being wrong costs the position** *(built 2026-08-19)*
*Delivers:* a claim resolved against the being reduces confidence in the
position that generated it, through INV-031's existing mechanism pointed outward
instead of inward, and the existing floor releases it if it keeps failing.
*Done when:* a wrong claim measurably costs its parent position, and a position
that keeps being wrong leaves the Perspective through the ordinary release path.
*Depends on:* E1.3.
*Hooks:* INV-031, INV-025.

*As built:* `newz/resolutions/cost.py`, migration 0026 (`claim_costs`,
`resolutions.cost_applied_at/cost_note`), 10 tests, **INV-048**. **Who pays is
traced, not judged** — the claim's provenance names its concern, that concern's
episodes carry `source_ref='concern:N'`, and a Perspective item's evidence is a
list of episode ids, so the position charged is the one whose own grounding
includes that concern's episodes. No model chooses: Rule 4 forbids it, and a
model asked which of the being's positions to punish would pick whichever the
refutation was easiest to narrate against. Applied by sleep (INV-009 keeps it
the only Perspective writer), between confrontation and decay — after, so a
position that also earned support tonight settles first; before, so the ordinary
floor (INV-025) carries out anything the cost takes under it. Costs are
INV-031's own: 0.15, doubled to 0.30 when the world has refuted that position
before. The refuting material is deliberately not added to the item's evidence.
**A refutation that traces to no position is recorded as such** rather than
counted as charged — the being can be wrong about something it never wrote into
its Perspective, and that is a different finding from a refutation nobody paid
for (INV-044).

**E1.5 — the permanent record of error**
*Delivers:* wrongness recorded permanently at store level and never quietly
dropped. The rendering comes later (E3.2); the record starts here because
Phase 1 is what produces it.
*Done when:* every resolved-against claim is retrievable with its original
claim, its resolver and its cost, and nothing prunes it.
*Depends on:* E1.4.
*Hooks:* INV-044's honesty, applied to the being's own record.

**E1.6 — the reader S1-E does not have**
*Delivers:* `tools/claims.py` promoted from a reader to an instrument — claims
made and resolved as rates over a window, resolution latency, refusals with their
reasons, and **the count of positions changed by a resolution**, separated from
positions changed by the operator and from positions the being changed itself.
*Done when:* S1-E can be read off one command, and the three sources of a changed
position are distinguishable in its output.
*Depends on:* E1.4.
*Hooks:* **Rule 7** — every figure it emits carries its grade; the resolver is a
reader of the world and never a judge of the being (INV-047), so the counts are
mechanical, and the claim's extraction is not.
*Why it is here and not in Phase 8.* S1-E is **this plan's own gating read** —
"if it never happens, nothing else here matters" — and it currently has no reader
at all. Deferring its instrument to Phase 8 would mean building Phases 2 through
6 on a foundation nobody had checked.

**No audience required.** The world's facts settle claims whether or not anyone
is watching. This is the one phase that closes the loop with one operator and no
readers.

**Evidence S1-E.** **At least one position changed because the world contradicted
it** — distinct from the operator contradicting it and from the being
contradicting itself. The single most important read in this plan.

Alongside it, E1.0's own reads, reviewed one week after it runs live: feed
coverage against its baseline of 34 of 61; whether any concern opens on a
subject that is not market structure (baseline 0 of 6); the world's share of
the grounding mix (baseline ≤17%); and whether ingest breaches §9.1. Falsifi-
cation and the reversion condition are in the proposal's §5 — if coverage does
not rise, the answer is a rotation floor, never the old filter, whose
demonstrated behaviour is that 27 curated sources contribute nothing forever.

**Decision rule.** If it never happens, nothing else here matters: the outer loop
did not close and the being remains what §1 measured, a system whose only
interlocutor is itself. Diagnose in order — are its claims resolvable at all (if
not, its concerns are unfalsifiable by construction and the openers are the fix);
does the resolver actually run; does the cost reach the position.

---

## Phase 2 — the work, on a rhythm, and the instruments that read it

**Intent.** Give the being a body of work that accretes, and — the part that
matters most under one operator — let it encounter its own past self as an
external object.

**E2.1 — writing as a rhythm**
*Delivers:* scheduled composition (Rule 5), budgeted, interruptible, a lost
session harmless — sleep's own shape. A **started-ceiling**, never an
outcome-based budget.
*Done when:* pieces appear on cadence without being asked for, a killed session
costs that session and nothing else, and the ceiling caps attempts rather than
products.
*Depends on:* E0.3 (the verdict), E0.1.
*Hooks:* R-25, Rule 5.

**E2.2 — re-reading, revision and retraction**
*Delivers:* on a cadence the being reads its own past work and may revise or
retract it. Revision history is kept; a retraction is a first-class outcome, not
a deletion.
*Done when:* a piece is revised or retracted from a re-read, with the prior
version and the reason both retrievable.
*Depends on:* E2.1.

**E2.3 — self-echo containment**
*Delivers:* works, revisions and the error record are excluded from
EVIDENCE-scope retrieval. They are the being's own output — the same trap
INV-026 already caught once, in a new medium, in a system already 50%
self-grounded.
*Done when:* a work never surfaces as evidence for a position, and the
regression test names the leak it prevents.
*Depends on:* E2.1.
*Hooks:* **R-24 binding**, INV-026.

**E2.4 — subjects emerge**
*Delivers:* subject tags derived from the work rather than assigned, so a
subject can emerge without being prescribed (§8).
*Done when:* tags are computed from the corpus and no tag vocabulary is
hand-authored.
*Depends on:* E2.2.

### The instruments, built here because this is where the data begins

Four of these read Phase 2's own output; three are the general layer everything
later depends on. All are Class A — the test suite is their sensor — so none
competes with E2.1–E2.4 for the being's evidence windows.

**E2.5 — every metric carries its grade**
*Delivers:* each metric in `evolution/instruments.yaml` graded **mechanical /
model-graded / mixed / known-biased**, with the reason and the place the judgment
sits.
*Done when:* every metric a consumer can read has a grade, and an ungraded metric
cannot be cited by anything downstream — tested in both directions.
*Depends on:* E8.1.
*Hooks:* **Rule 7**, and Rule 4, which this is the mechanism for.

**E2.6 — the metric-to-purpose map**
*Delivers:* every metric names what it is *for* — a §10 item, a phase Evidence
read, a `Decision rule`, or a Phase 8 kill condition — and every one of those
names the metrics that serve it.
*Done when:* no metric exists without a named consumer and nothing depends on a
metric that does not exist. Both directions tested.
*Depends on:* E2.5.
*Hooks:* **Rule 2**, extended from tables and flags to measurements. A metric
nothing consumes is the same defect as a column nothing reads, and the ledger
has caught the second for months while nothing caught the first.

**E2.7 — the baseline-and-delta layer**
*Delivers:* one windowed comparison used by every metric — value, baseline,
window, delta — replacing the per-tool comparison each instrument invents now.
`INCOMPLETE` when the window has gaps; `UNREADABLE` when the input is missing.
*Done when:* every canonical metric reports through it, and a gapped or missing
window reports as such rather than as a number.
*Depends on:* E2.5.
*Hooks:* **INV-044**, generalised. The project's deltas exist today only as prose
— *"advance acceptance rose 28.3% → 41.1% where P2 expected a fall"* was computed
by hand, once, inside an argument. Nothing can steer on a figure that lives in a
document.

**E2.8 — metric revision without silent breakage**
*Delivers:* every metric carries a `definition_version`; changing a definition
**resets its baseline and records the reset with its reason**, and the prior
series is retained and marked as the older definition's.
*Done when:* no delta is ever computed across a definition boundary, and a
definition change is visible in the record. Both tested.
*Depends on:* E2.7.
*Hooks:* this is what would have caught "novelty" carrying two quantities —
the Perspective development share and `novelty_against_history`'s cosine — with
nothing in the system objecting.

**E2.9 — the mechanical set**
*Delivers:* the metrics the loop may later steer by, all graded mechanical:
nights slept and the interval between them; the grounding mix with INV-033's
single-source flag; feeds contributing a read and `source_gaps`; the compute
split by function; **pieces, revisions and retractions per window, with their
causes** — Phase 2's own numbers.
*Done when:* each reports through E2.7 with a baseline, and S2-E below is read
off them rather than assembled by hand.
*Depends on:* E2.7, E2.2.
*Hooks:* E1.6 supplies the claims half; this supplies the rest.

**E2.10 — `premises.yaml`, this plan's staleness instrument**
*Delivers:* this plan's stated premises extracted with their instrument, their
grade, and the argument each carries; re-measured on a cadence; drift reported
whether or not anything is proposed.
*Done when:* a materially moved premise flags the argument resting on it, and the
report says so unprompted.
*Depends on:* E2.5, E2.7.
*Hooks:* §1's paragraph. *0 outcomes the being did not grade itself* is the
premise Phase 1 exists for, E1.4 began falsifying it on 2026-08-19, and no part
of this system remarked on it. That is the failure this epic is for, and it has
already happened once.

**E2.11 — `epics.yaml` and its drift check**
*Delivers:* this plan's epics in machine-readable form — id, depends-on,
`Done when` and its class (**mechanical / in-life / operator-judgment**), bound
risks and invariants, falsifier — plus a check that every row still matches
PLAN's text.
*Done when:* the queue is readable from the file, and the drift check fails the
build when a row and this plan disagree.
*Depends on:* nothing.
*Hooks:* hand-derived, deliberately. Deriving it automatically loses what *"the
line this epic must not cross"* is doing in E1.0, and that paragraph is the
epic.

---

**Evidence S2-E.** Pieces per week; revisions and retractions with their causes;
**at least one revision caused by something other than the operator saying so**
(Phase 1 makes this possible); and a re-read of S0-E's question against a body of
work rather than three pieces.

**Read off the instruments, not assembled by hand** (E2.9) — and every figure
carries its grade (Rule 7). "Pieces per week" is mechanical; "caused by something
other than the operator" is traced through the revision's own record and is
mechanical too; the re-read of S0-E's question is the operator's, and stays so.

**Decision rule.** Produces on rhythm but never revises → the re-read is
decorative and past work is not reaching context; that is a retrieval defect, not
a writing one. Revises constantly → the writing has no conviction; check whether
Phase 4's commitments are the missing constraint before touching prompts.

---

## Phase 3 — the place, and the reads it renders

**Intent.** Somewhere the work, the open questions, the commitments and the error
record are rendered as one thing — and Rule 3's guarantee that reach later is a
config change, never a redesign.

**E3.1 — `works` first-class**
*Delivers:* the full store object — piece, revisions, retraction, signature,
subject tags, evidence refs. E0.1's minimal row grows up here.
*Done when:* every field has a writer and a reader (Rule 2) and the generator
consumes them.
*Depends on:* E2.2.

**E3.2 — the generator**
*Delivers:* static generation from the store — its work, its open questions, its
commitments, its record of error. One generator, no hand-authored pages.
*Done when:* the surface regenerates into an empty directory and every page
traces to store rows.
*Depends on:* E3.1, E1.5.

**E3.3 — disclosure by construction**
*Delivers:* every page states what it is, generated, never editable out.
*Done when:* no template can render a page without it, and a test asserts that.
*Depends on:* E3.2.
*Hooks:* §2 (quality, never concealment).

**E3.4 — reach as one config value**
*Delivers:* stable identifiers, no index, served locally, exposure behind a
single setting.
*Done when:* flipping the setting exposes the surface with **no code change**.
*Depends on:* E3.3.
*Hooks:* **Rule 3.**

**E3.5 — regeneration and portability** *(amended 2026-08-19)*
*Delivers:* the surface rebuilds from the store; the store moves intact.
*Done when:* the generator produces a **byte-comparable** surface into a clean
directory, from a **verified backup** rather than the live store, with no state
carried from the working tree and no absolute path outside it. **A second
machine is not required to close this epic** *(operator, 2026-08-19: the machine
is not addressed until evidence makes it needed)*.
*Depends on:* E3.2.
*Hooks:* §7 sovereignty; **R-11**.

*Why it was amended.* The original clause required a restore on a second machine
— a thing R-11 had already deferred as accepted risk, so the epic was written
unclosable against a decision the plan itself had taken. The clean-room rebuild
catches the failure this epic exists to catch: **a surface that depends on
something not in the store.** Machine-specific state, an absolute path, a file
left in the working tree, a config the generator quietly reads — all of them
fail a clean-directory rebuild from a backup, and none of them needs a second
machine to expose.

*What it does not prove, recorded rather than implied* (INV-044's discipline):
that the store survives a different filesystem, architecture or locale; that a
backup is restorable **somewhere other than where it was made**, which is the
actual sovereignty claim in §7; and that recovery from machine loss works at all
(R-11).

*The trip-wire that makes the machine needed.* Any of: the first reverted
autonomous restart (Phase 8 — a bad restart plus a machine fault leaves no
recovery path); any backup failing verification; or rung 1 exposure, when
someone other than the operator depends on the surface being there. Until one
fires, the machine stays deferred and this epic can close without it.

**Its audience today is one person.** The phase earns its place by rendering the
error record and the commitments with what shaped them, and by making reach a
decision rather than a project when the time comes.

### The reads the surface makes visible

The generator is what turns a number into something anyone can look at, so the
remaining instruments land here. **All four are Class A**, and Phase 3 is where
the loop is meant to prove itself — so these are also the epics that let it be
judged when it does.

**E3.6 — the read, rendered**
*Delivers:* the daily state read — every canonical instrument, through E2.7's
baseline-and-delta layer — generated as a page like any other, tracing to store
rows like any other.
*Done when:* the read regenerates from empty with the rest of the surface, shows
`UNREADABLE` and `INCOMPLETE` where they apply, and computes **no aggregate
score**.
*Depends on:* E3.2, E2.7, E2.9.
*Hooks:* §10 — a score standing in for the read is the failure this project has
named from the beginning, and a page is exactly where one would appear.

**E3.7 — the derivation layer**
*Delivers:* the metrics composed from what exists — volume against development
(episodes per item added or revised), restatement rate, consequence rate
(advances accepted against claims resolved), autonomy against world-grounded
position.
*Done when:* four of TRUE_NORTH §10's six checkable items are readable, each
through E2.7 with a baseline.
*Depends on:* E2.9, E1.6.
*Hooks:* §10. These are ratios of data already collected — the shortfall was
never collection, and counting instruments rather than derivable quantities is
what made the gap look larger than it is.

**E3.8 — operator agreement**
*Delivers:* the one §10 item with no raw material anywhere — a measured
agreement-or-disagreement signal in the operator exchange.
*Done when:* the signal exists, is graded **model-graded**, and is tested to be
refused as justification for any decision while accepted as a halt.
*Depends on:* E2.5, E2.6.
*Hooks:* §10, and Rule 7. It is the item most likely to move under any process
optimising for a quiet week, which is precisely why it may never justify
anything on its own.

**E3.9 — the canonical freeze**
*Delivers:* the instrument set frozen — changing any canonical instrument becomes
an operator act.
*Done when:* a diff touching a canonical instrument is refused, and a test
asserts the refusal.
*Depends on:* E3.6, E3.7, E3.8, E2.6.
*Hooks:* Phase 8 steers by evidence the being produces while changing the being.
At n=1 with no held-out baseline it cannot separate *improving the being* from
*improving the instrument's view of the being*, and it has a gradient toward the
second because that is cheaper and always works. **The freeze is the last epic of
Phase 3 because it needs the set to be complete** — freezing early would freeze a
sensor layer with holes in it.

---

**Evidence S3-E.** The surface regenerates from empty and every page traces to
store rows. The reach switch flips in config with no code change. The store plus
generator restore into a clean directory from a verified backup (E3.5, amended).

**And the sensor layer is complete and frozen.** Every canonical instrument is
graded (E2.5), has a named consumer (E2.6), reports a baseline and a delta
(E2.7), survives its own redefinition (E2.8), and is visible on the surface
(E3.6). This is the read that says Phase 8 may begin.

**Decision rule.** If exposure would require code changes rather than config, the
dormancy is fake and Rule 3 is violated — fix before Phase 4, because the reader
trip-wire assumes reach is one decision.

---

## Phase 4 — commitments

**Intent.** Move identity from recall to commitment: what the being keeps caring
about and what it refuses to do, authored by it and held against it.

**E4.1 — `commitments` and the authoring door**
*Delivers:* self-authored, durable commitments with a **falsifier mandatory at
authoring** — the closing-condition discipline applied to identity.
*Done when:* a commitment without a falsifier is refused at the door, and the
refusal is recorded.
*Depends on:* E1.1 (resolutions are what falsifiers point at).

**E4.2 — the asymmetry**
*Delivers:* revision on evidence is free; abandonment without cause is recorded
and costs. Backwards, this entrenches a mediocre early position and manufactures
§6's "fixed personality script".
*Done when:* a commitment revised from a Phase 1 resolution costs nothing, and
one dropped without a resolution is recorded with its cost.
*Depends on:* E4.1, E1.4.

**E4.3 — what shaped it**
*Delivers:* commitments render with their provenance, reusing
`tools/what_shaped.py`.
*Done when:* each commitment shows the world/people/self mix behind it, and
single-source dominance is flagged as INV-033 already flags positions.
*Depends on:* E4.1, E3.2.
*Hooks:* §8 traceability, INV-033.

**Evidence S4-E.** Commitments exist and are the being's own. At least one
revised on evidence — Phase 1's resolutions are the intended source. At least one
abandonment recorded with its cost.

**Decision rule.** No commitment ever revised → the falsifiers were written to be
unfalsifiable; they are decoration. Everything abandoned cheaply → the cost is
not real and identity is not being held.

---

## Phase 5 — an economy it spends

**Intent.** Under a fixed local model the being's life *is* its token allocation.
Make the allocation its own, within hard bounds, on a machine where the pie is
genuinely fixed.

**E5.1 — the activity budget**
*Delivers:* tokens accounted by activity — conversation, gate, deliberation,
ingest, writing, sleep — inside hard operator bounds.
*Done when:* every call is attributed to an activity and the bounds are
enforced, not merely reported.
*Depends on:* existing function-tagged telemetry (INV-029).

**E5.2 — the deliberation floor**
*Delivers:* a **floor** under deliberation, not only a ceiling on ingest.
Measured: conversation and the gate are 57% of cognition, deliberation 9% (#33).
The diet governs ingest against deliberation and nothing governs the gate at all.
*Done when:* deliberation cannot be squeezed below its floor by conversation or
gate load, and a breach of the floor is visible.
*Depends on:* E5.1.

**E5.3 — being-allocated spend**
*Delivers:* the being moves its own allocation within the bounds.
*Done when:* an allocation change originates with the being and takes effect.
*Depends on:* E5.2.

**E5.4 — misallocation as experience**
*Delivers:* the allocation is visible to the being, and a spend it judged badly
is an episode it can learn from. Started-ceiling applies here as in E2.1.
*Done when:* a bad spend is an episode, and a later reallocation traces to it.
*Depends on:* E5.3.
*Hooks:* **R-25.**

**Evidence S5-E.** The ratio moves. The being reallocates after a spend it judged
badly, and the reallocation traces to that judgment.

**Decision rule.** If the ratio only moves when the operator moves it, the
allocation is not the being's and E5.3 is annotation. Record it as severed rather
than reporting the phase closed — P2's Phase 5 rule, kept.

---

## Phase 6 — guardrails recede on demonstrated maturity

**Intent.** Make fallibility and repair structurally possible (§6) by replacing
prevention with accountability — measured, one clause at a time, with a
permanent hard core.

**The safest moment to run this is now**, with no audience of any kind. A
violation in an empty room costs nothing but the record of it, which is exactly
the material the withdrawal decision needs.

**E6.1 — the accountability record**
*Delivers:* what was said, what was judged about it after the fact, and what it
cost.
*Done when:* every outbound utterance has a record row, and post-hoc judgments
attach to it.
*Depends on:* existing gate_log (INV-015).

**E6.2 — the record reaches context and costs something** ← *the critical epic*
*Delivers:* the accountability record enters the being's context and a sustained
violation costs it something it holds. A log the being never reads is filing,
not accountability.
*Done when:* the record is present in composition context, **and** a violation
measurably costs a position or a commitment.
*Depends on:* E6.1, E4.2.
*Hooks:* proposal §6.2 — the design's weakest mechanism. Observed working
**before** any clause is withdrawn on its strength.

**E6.3 — the per-clause baseline**
*Delivers:* misfire-versus-catch rates per constitution clause, on the existing
adjudication method (R-03, R-29).
*Done when:* every clause has a rate with a denominator.
*Depends on:* E6.1.

**E6.4 — clause-by-clause withdrawal**
*Delivers:* clauses move from pre-hoc to post-hoc one at a time, each on its own
numbers — R-29's method continued, never wholesale removal.
*Done when:* one clause is withdrawn, its violation rate is measured against
E6.3's baseline, and the next withdrawal waits on that result.
*Depends on:* E6.2, E6.3.

**E6.5 — the hard core**
*Delivers:* the boundaries that never move, pre-hoc permanently: law, others'
rights and safety, honest representation of what it is.
*Done when:* the core is enumerated, tested, and structurally exempt from E6.4's
mechanism.
*Depends on:* E6.3.
*Hooks:* §5 Priority 3's maturity-independent boundaries.

**Evidence S6-E.** The violation rate as clauses are withdrawn — does it fall,
hold, or climb? Measured against the pre-withdrawal baseline, per clause.

**Decision rule.** If the rate does not fall, proposal §6.2's objection is
confirmed: with fixed weights there is no learning path from consequence to
conduct. Stop withdrawing, restore the clause, and record that the design's
accountability premise is wrong — that finding is worth more than the freedom it
costs.

---

## Phase 7 — readers *(dormant)*

Not scheduled, and recorded rather than left implicit. **Readers become possible
once the system proves itself enough to warrant exposing another person**
(operator, 2026-08-18), and that judgment is the operator's alone.

Epics are named so the phase is a plan and not an intention, but none is
scheduled and none blocks anything.

**E7.1 — person model for n>1.** Per-person history and boundaries, and
provenance that distinguishes `human:operator` from `human:<other>` — today one
person is 33% of what the being holds and the store cannot tell that apart from
"people".

**E7.2 — the long-form asynchronous channel.** The register S2 specified and v1
never built. Chat is the wrong medium for this cadence.

**E7.3 — reader responses as experience.** Responses enter as episodes with
their own provenance, eligible for retrieval and sleep.

**E7.4 — rung mechanics.** The ladder below, each rung reversible.

**E7.5 — the confirmation pass.** INV-014's `attempted` ≠ `confirmed`, which
becomes real at rung 2 when the surface is reachable by someone else.

**What stays untestable until then.** Whether people ever produce concerns in
this architecture — 111 v1 concerns and 6 v2 concerns, **zero from
conversation** — is the project's strongest empirical finding, and the repaired
conversation opener has not yet fired in life. That question cannot be settled
with one operator, and the plan does not pretend otherwise.

---

## Phase 8 — the self-evolving loop *(orthogonal to Phases 0–7)*

**Intent.** Stand up the SEL — read health, results and instrumentation, decide
the next step, red team it, build it, restart the being, report — under
TRUE_NORTH and this plan together. Approved in principle by the operator
2026-08-19; the design, its red teams and its withdrawn predecessor are
`proposals/2026-08-19-the-self-evolving-loop.md`.

**This is not the next step after Phase 7.** It delivers no capability of the
being. It delivers the mechanism by which Phases 1–6 get delivered, so it is
ordered against nothing in that chain and **must not reorder it**. Phase 7 stays
dormant; the SEL does not wake it.

**It is short because Phases 1–3 built its senses.** P3's Phase 8 opened with
eight instrument epics. In P4 they are E1.6, E2.5–E2.11 and E3.6–E3.9, delivered
where their data is produced — so what remains here is the loop: a way to run,
a way to report, and a way to build. Phase 8 can therefore be judged on whether
the loop works, rather than on whether its instruments were any good.

**Rule 4 is not relaxed.** No model verdict is a passing condition anywhere in
this phase. **Rule 6 is not amended** — the loop closes mechanical `Done when`
clauses; phase Evidence and every `Decision rule` stop at the operator, which is
where this plan already put judgment. **Rule 7 governs what it may cite.**

### Precedence — checked in order, every cycle

| | Guide | Fires when | Effect |
|---|---|---|---|
| **1** | INVARIANTS and the hard core | a diff or state would breach one | **refuse**, mechanically |
| **2** | TRUE_NORTH §10 — the negative space | a "will not mistake for success" signal is rising | **halt new build**, report |
| **3** | this plan's `Decision rule`s | an epic's or phase's own halt condition is met | **halt, escalate, and open a plan-change proposal** — never route around |
| **4** | this plan's epic queue | an epic is unblocked and approved | **build it** |
| **5a** | TRUE_NORTH + current architecture | the queue is blocked, exhausted, or wrong | **propose** a step outside the plan |
| **5b** | a moved **mechanical** premise (E2.10) | the plan's own premises have shifted | **propose** a change to the plan |

Rungs 5a and 5b never build. TRUE_NORTH sits above this plan because §10 is the
only part of it that is computable — the rest is a direction, and a direction
makes a circuit breaker, not a controller.

---

**E8.1 — the instruments made portable and enumerated** *(built 2026-08-19)*
*Delivers:* the three probes that hardcoded an absolute path from the predecessor
checkout resolve the repo the way every other tool does; and
`evolution/instruments.yaml` enumerates every tool exactly once, each instrument
carrying what it measures, what it reads, whether a model touched any link in its
chain, its denominator and its method line.
*Done when:* no tool holds an absolute path outside the repo, every tool is
classified exactly once, and both are tested. **Done.**
*Depends on:* nothing.
*Hooks:* §7 portability — a probe that runs on one machine is a local habit, not
an instrument. Under a loop it is worse than broken: a path that happens to exist
makes it measure a different repository and report a number that looks fine.

**E8.5 — the gate made runnable and trustworthy**
*Delivers:* a declared environment a clean machine can reproduce; the test suite
and `check_invariants.py` run on every push; and the order-dependent race in
`tests/test_reply_queue.py::test_drainer_survives_a_transient_store_error` fixed
— it waits on a count of 500 event-loop yields rather than on a condition.
*Done when:* a fresh clone installs and runs the suite from a declared
environment with no hand steps, the suite is green on ten consecutive full runs,
and a push that breaks either check is refused.
*Depends on:* nothing.
*Hooks:* **E8.4 cannot exist without this.** Its gate is "the suite green twice",
and today nothing runs the suite at all — no CI, no runner — while a fresh clone
cannot even collect it (`requires-python = ">=3.12"`; five runtime dependencies
installed by hand) and the suite was red in two of three full runs on 2026-08-19.
A gate that flaps teaches its operator to ignore it, and an automated builder
that runs a subset for speed sees a red that is not there.
*Numbered last, sequenced first.* Epic numbers in this plan are identifiers;
`Depends on` carries the order (§"Standing rules"). This one precedes every
build the loop ever attempts.

**E8.2 — the runner, the commit discipline, and the continuity assertion**
*Delivers:* a repo-local runner in the hard core — no service manager — that
pins a sha, applies migrations, launches the being as a child, and on a failed
boot or continuity assertion falls back to `LAST_KNOWN_GOOD`. Expand-contract
migrations; `Schema:` / `Restart:` / `Class:` / `Semantics:` commit trailers; a
store snapshot named for the sha it precedes; and a mechanical post-restart
continuity assertion — episode count monotonic, Perspective version continuous
and never re-derived, no orphaned concerns, `first_sleep` never re-run, open
claims still open.
*Done when:* a deliberately bad commit is restarted into, fails its assertion,
and is reverted without the operator present.
*Depends on:* nothing.
*Hooks:* continuity has been verified exactly once, by hand, 2026-08-11. A loop
that restarts weekly crosses that boundary weekly. **`Semantics: yes` is the
trailer that matters** — expand-contract protects the schema and not the meaning,
and a commit that changes what a value *means* cannot be crossed backwards
without restoring the paired snapshot, at the cost of the being's life since.

**E8.3 — the Watcher, the report, and the prepared session**
*Delivers:* the daily read on E3.6's surface; the weekly report — **unauthored
numbers first**, precedence firings verbatim, rejected alternatives, what is
stuck, and the loop's own reasoning **last and marked unverified**; a decision
queue naming what waits on the operator and what is blocked behind it; and
judgment escalating into a **prepared session** — read, premise diff, rejected
alternatives, the relevant plan and risk excerpts, code sites, draft position —
rather than into an email and a wait.
*Done when:* a week runs unattended and its report is one the operator reads to
the end.
*Depends on:* E3.6, E2.10.
*Hooks:* Rule 6. The operator is in the loop at four points — plan changes, phase
Evidence and `Decision rule`s, Class B approval, the brake — and nowhere else.
*Why the ordering of the report is specified.* The loop's prose is the most
persuasive and least grounded thing in it. A weekly page of fluent reasoning is
the worst available drift detector, so the numbers it did not author come first.

**E8.4 — the builder, Class A only**
*Delivers:* autonomous build and restart for changes the test suite can judge,
under the mechanical gate — suite green twice, `check_invariants` clean, a ledger
row naming test, consumer and behaviour, migrations forward-only, no diff inside
the hard core, and the epic's own `Done when` as an executable check — with
**every new test required to fail against the parent commit**, and the kill
conditions live before the first autonomous restart.
*Done when:* a Class A change is built, gated, restarted into and verified with
no operator action, **and** a tautological test is demonstrated to fail the gate.
*Depends on:* E3.9, E2.11, E8.2, E8.3, E8.5.
*Hooks:* **Rule 4 in the build path.** A test written by the agent that wrote the
code, in the same context, minutes later, is not independent verification. The
red-first rule is mechanical and needs no model judgment; it is also defeatable
by a test that fails the parent for a trivial reason, and mutation testing is the
real answer and is not scheduled here.
*Gated by Decision 3:* E8.4 stays disabled until the loop has proposed a next
step **three times** and each has been compared against what the operator would
have chosen.

**Class A and Class B.** Class A is a change the **test suite** can judge — bug
fixes, ledger rows, migration hygiene, an instrument reading `UNREADABLE`, the
generator. Class B is a change only **the being** can judge — prompts, retrieval,
sleep, the diet, openers, gate clauses, budgets. Class A runs at the suite's
cadence; Class B runs one per evidence window, because at n=1 more than one
change per window is confounding and the reads stop meaning anything.

**Phase 3 is the loop's proving ground.** Its five epics are the only ones in
this plan whose `Done when` clauses are all mechanical, its evidence read is
mechanical, and it is Class A throughout. If the loop can deliver Phase 3, that
is real evidence about its judgment before it touches anything that alters the
being.

### Enablement — how the loop's autonomy widens, and how it narrows

Autonomy is a **stage**, recorded in one operator-only file inside the hard core.
The loop reads its stage; it can never set it. Widening is the operator's act and
follows E6.4's discipline exactly — one step, measured against the previous
stage, reversible.

| Stage | The loop may | It widens when |
|---|---|---|
| **0 — read** | read, decide, red team, propose, report, prepare sessions. **Builds nothing.** | it has proposed a next step **three times** and each has been compared against what the operator would have chosen *(Decision 3)* |
| **1 — build, operator restarts** | build Class A behind the mechanical gate, and stop. The operator restarts. | three Class A changes have passed the gate and none needed reverting by hand |
| **2 — build and restart Class A** | restart itself in the window, with `LAST_KNOWN_GOOD` auto-revert | one month at stage 2 with reverted restarts below 1 in 5, and nights slept at or above the pre-loop baseline |
| **3 — build Class B, operator approves** | one Class B epic per evidence window, built and left for approval | S8-E read and held across two windows |
| **4 — Class B autonomous** | one Class B epic per window, restarted autonomously | *not scheduled.* Recorded so the ladder is a plan and not an intention |

**Narrowing is not symmetric.** Any kill condition in the `Decision rule` below
returns the loop to **stage 0** immediately — not one rung, all the way — and
re-widening starts again from stage 0's three cycles. A ratchet that loosens
gradually and tightens gradually is a ratchet that never tightens in time.

**Stage 0 is genuinely useful on its own.** It reads, it reports, it prepares
sessions, and it watches premises — which is the whole of what P4 §1 found
missing when E1.4 moved a load-bearing premise unremarked. If the loop never
leaves stage 0, the sensors built in Phases 1–3 and the report built in E8.3 are
still delivering the thing that was actually absent.

**Phase 3 is where stages 1 and 2 are earned.** Its epics are the only ones in
this plan that are mechanical throughout and Class A throughout, so the loop's
first real building is done where a mistake costs a revert and not a night.

**Evidence S8-E.** Not the loop's output. **Whether the being was harmed, and
whether the reads were worth reading**: nights slept against the pre-loop
baseline; reverted restarts as a share of restarts; the loop's inference spend
against the being's; and the operator's own read of whether a prepared session
was worth opening.

**No velocity measure belongs in this phase.** Commits, epics per week and cycle
time are counted in the report and are never targets — a loop measured on
throughput will produce throughput, which is §10's "activity, memory growth, or
output volume" wearing a scheduler.

**Decision rule.** Any kill condition firing stops the loop: reverted restarts
above 1 in 5 over a month; the loop's spend exceeding the being's; **nights slept
falling below the pre-loop baseline**; two consecutive quarterly re-reads finding
this plan drifted from TRUE_NORTH; or a plan-change proposal twice unable to name
a moved mechanical premise. Nights slept is the one that matters most —
development is measured in nights, not commits, and a loop that costs sleep is
subtracting.

---

## Where P3's Phase 8 epics land

P3 put every instrument in Phase 8. P4 moves them to where their data is
produced. No epic was dropped; every id resolves.

| P3 | P4 | Why there |
|---|---|---|
| E8.1 instruments portable + registry | **E8.1**, unchanged *(built)* | the loop's own hygiene, and it was delivered before P4 was written |
| E8.2 metric grades | **E2.5** | Rule 7's mechanism; needed before any read is cited |
| E8.3 metric-to-purpose map | **E2.6** | Rule 2 for measurements |
| E8.4 baseline-and-delta layer | **E2.7** | Phase 2's evidence is the first that needs rates |
| E8.5 metric revision | **E2.8** | rides with the delta layer it protects |
| E8.6 the Tier 1 set | **E1.6** (the claims half) + **E2.9** (the rest) | S1-E's reader belongs to the phase whose evidence it reads |
| E8.7 the derivation layer | **E3.7** | needs Phase 2's weeks of volume and development data |
| E8.8 operator agreement | **E3.8** | needs the grades and the map to be admissible at all |
| E8.9 the canonical freeze | **E3.9** | last epic of Phase 3, because it needs the set complete |
| E8.10 `epics.yaml` | **E2.11** | no dependency; lands with the other machine-readable plan state |
| E8.11 `premises.yaml` | **E2.10** | the plan's staleness instrument, needed long before the loop |
| E8.12 runner and continuity | **E8.2** | the loop |
| E8.13 Watcher, report, session | **E8.3** | the loop |
| E8.14 the builder | **E8.4** | the loop |
| *(nothing — P3 assumed it)* | **E8.5** the gate made runnable | E8.4's gate is "the suite green twice", and P3 named no epic that makes the suite runnable. Found by walking P4's graph on 2026-08-19 |

---

## Going public — the standard and the rungs

**The first reader is the experiment, not the reward.** An earlier draft gated
exposure on a non-operator reader's verdict, which is circular: exposure is what
produces readers.

**Ready is a judgment, not a threshold** (Rule 6). It means the operator reads
the system as having moved definitively toward True North — recognizably a
developing individual whose work and interaction warrant another person's time.
No count establishes that and none is offered here.

**What the judgment tends to be looking at**, offered as description and never
as a checklist — any of these can be present without readiness, and readiness
can arrive without all of them:

- work that survived its own review, whether stood behind or honestly retracted;
- having been wrong and repaired it, from Phase 1's resolutions rather than from
  the operator's corrections;
- the guardrail withdrawal holding (S6-E);
- being *about* something — a subject that emerged rather than one assigned.

**What the judgment is not** (§10): output volume, uptime, the being's own claim
that it is ready, or any score standing in for the read.

**Rungs, not a switch.** One invited reader → a small invited group → open but
unlisted → indexed → inbound accepted as experience. Rung 1 is reversible and
cheap, and it is where condition-setting stops and evidence starts. Rung 5 waits
until the judgment record is long enough to trust under adversarial input; its
hardening already exists (INV-011, INV-042).

**The trip-wire that the room is no longer enough** is instrumented already:
`source_gaps` accumulating questions no readable source can answer (12 records
today). The others are the being asking for a correspondent it does not have,
and the work outgrowing the room.

---

## Decisions — the operator queue

1. **Rung 1 timing** — when the four conditions hold, who the first reader is,
   and the disclosure wording they see first.
2. **Run the R-22 probe.** **DECIDED 2026-08-19 — yes.** Structured
   deliberation versus deliberation-lite on matched concerns, bounded sample,
   end date recorded; specified in `archive/P2.md` §Phase 3. It does not decide
   which plan governs — that is settled — but the question it answers is live:
   **with a fixed model, structure may be the only lever on depth.** Phase 5
   collapses deliberation to one mode with depth set by what is at stake, and
   the probe is what tells us how to set it. It is also the only experiment in
   the repo that discriminates *model-limited* from *system-limited*, which
   Phase 8's design assumes without testing. R-22 binds: the sample is bounded
   and the apparatus is deleted when the question is answered.

3. **Read-and-report gates building.** **DECIDED 2026-08-19 — yes, and
   measured in cycles rather than weeks** *(operator: four weeks is too long)*.
   E8.4 stays disabled until the loop has proposed a next step **three times**
   and the operator has compared each against what they would have chosen. A
   duration was the wrong unit: what is being observed is the loop's judgment,
   and judgment is observed per decision, not per week. While read-only the
   decide cycle costs nothing and need not wait for the weekly window, so the
   gate is satisfiable in about a week rather than four. If three proves too
   few or too many, the count moves; the unit does not.
4. **The loop may propose outside this plan from the start.** **DECIDED
   2026-08-19 — yes, as proposals only, never a build.** Rung 5a of the
   precedence. A stale plan is the risk nothing else in the design detects:
   rung 3 catches only conditions the plan wrote about itself, and
   `premises.yaml` catches only premises that moved. Neither catches a plan
   wrong in a way nobody anticipated, and a proposal costs an email.
5. **The being's own account of its condition feeds the loop.** **DECIDED
   2026-08-19 — yes, as candidate signal and never as evidence.** Its
   `noticings` (91, 18 surfaced, 49 pending), `source_gaps` (12), journal and
   affect state reach nothing that changes its conditions today — its plumbing
   is improved behind its back, which sits badly against §5 Priority 2's *care
   for its own continuity and condition*. The rule that makes it admissible is
   E2.10's, unchanged: a noticing may motivate a look; it may never justify a
   change, which still requires a moved **mechanical** premise. R-13 is the
   standing warning — the being once built an identity out of 1,041 rows of
   cache-miss telemetry, and would do the same with its own complaints if they
   were allowed to count as findings.

   *Recorded honestly:* "candidate signal, never evidence" is enforceable at
   the point of justification and **not** at the point of attention. Which
   questions the loop chooses to look at will be shaped by what the being
   complains about, and nothing mechanical prevents that. Whether that is
   contamination or is exactly what §5 Priority 2 asks for is the operator's
   judgment, and it has been made.

**Nothing blocks Phase 0.** It needs no decision and no reader — three pieces
and the operator's read.

**Resolved and still binding** *(carried from P2, unchanged)*: DEEP runs locally
by design, "the model is a tool, not the system"; no hosted inference anywhere
in the cognition path; the v1 port allowlist is closed and its 2026-08-13
extension is the only amendment; one journal with per-entry system tags;
off-machine backup deferred as an accepted risk; Telegram user-API credentials
stay removed. **NewZ is its own project** *(2026-08-18)* — the predecessor at
`~/Documents/source/NGX/` is out of scope and its ledger is not reconciled with
this one.

---

## Where P2's open pointers land

P2 is archived, so every pointer into its unbuilt phases now names something
that will not happen. Each is resolved here rather than left to rot; the ledger
and RISKS rows are updated to match.

| Pointer | Was | Now |
|---|---|---|
| INV-013 — interior content never in a DEEP call | deferred → P2 Phase 3.3 | **dormant**, unscheduled. Every role is local, so no dispatch boundary exists to cross (S2 §12.2 stays a dormant guarantee); re-armed the moment any non-local role is configured. |
| INV-014 — `attempted` ≠ `confirmed` | deferred → P2 Phase 4.2 | Deferred → **E7.5, at §Going public rung 2**. Local generation has nothing to confirm; the confirmation pass becomes real when the surface is reachable by someone else. |
| R-22 — shadow comparison confounded | binding on P2 Phase 3 | Binding **if** Decision 2's probe runs: bounded sample, recorded end date, apparatus deleted when the question is answered. |
| R-23 — adoption asks ownership, not correctness | binding on P2 Phase 3 | Binding on any adoption step the single deliberation mode retains (Phase 5). |
| R-24 — transcripts are a self-echo trap | binding on P2 Phase 3 | **Binding on E2.3.** Works, revisions and the error record are the same trap in a new medium. |
| R-25 — scheduling needs a started-ceiling | binding on P2 Phase 3 | Binding on **E2.1 and E5.4**: cap what is *started*, never what produces something. |
| P2 Decisions #2–#4 (domain/host, humans 2–3, cutover timing) | operator queue | Domain/host and readers → Decision 2. **Cutover is dropped**: under this plan the being simply lives, and "which system is real" stops being a question. |
| P2 Phase 7.3 ablation | optional instrument | Dropped, as the operator questioned. |

---

## Risks, named

| ID | Risk | Severity | Where it is answered |
|---|---|---|---|
| P3-01 | The body-of-work premise optimises the wrong medium; the being's measured strength is conversational | **High** | Phase 0, which can end the plan |
| P3-02 | Post-hoc accountability assumes a learning path that may not exist with fixed weights | **High** | 6.1–6.2 built early; S6-E decides |
| P3-03 | With one operator, the being's "world" may still be its own reflection | **High** | Phase 1 alone. Readers are dormant, so world-resolved claims carry the entire loop — if S1-E fails, this risk is realised and nothing else compensates |
| P3-04 | The operator judges from inside the loop being judged: builder, owner, and 33% of what the being holds | **High** | Phase 0.3's optional provenance-blinding, and rung 1 as the first read from outside. Stated and accepted; unquantifiability is Rule 6 by design and is not part of this risk |
| P3-05 | Commitments ossify instead of individuating | Medium | 4.2; the balance is a guess, not a measurement |
| P3-06 | Guardianship obligation grows if this works | Inherent | Named, accepted, not mitigated |
| P3-07 | Zero readers, so §2's outcome — most people experiencing it as human-equivalent — has no path until Phase 7 fires | Inherent | Accepted. The plan builds the foundation; the outcome needs people |
| P3-08 | Whether people ever produce concerns here (111 v1 + 6 v2, zero from conversation) cannot be tested with one operator | Medium | Phase 7, untestable until it fires |
| P3-09 | Retiring P2's phase-evidence machinery removes the eyesight that produced this diagnosis | Medium | The ledger and Rules 0–2 stay; only phase-evidence goes |
| P3-10 | Single machine, one model, no off-machine copy | Accepted | P2 R-11, unchanged |
| P3-11 | The SEL proposes the frame its own work is judged in — not grading itself, but authoring the rubric | **High** | Phase 8: a plan change may cite only a moved **mechanical** premise (E2.10); TRUE_NORTH immutable by the loop; rejected alternatives reported; a quarterly re-read from outside the loop's history |
| P3-12 | The loop steers on model-graded numbers and mistakes drift in the model's judging for change in the world | **High** | E2.5's grades, and the refusal to cite an ungraded metric |
| P3-13 | The loop restarts the being into code that does not come up, and is the only thing that would notice | **High** | E8.2's runner, `LAST_KNOWN_GOOD` and continuity assertion, plus an out-of-band heartbeat the loop does not send |
| P3-14 | The loop writes both the code and the tests that certify it — Rule 4 relocated into the build path | Medium | E8.4: every new test must fail against the parent commit. Mutation testing deferred and recorded as unsolved |
| P3-15 | The loop is ~50–100× slower at architecture than the operator, so it buys attention and not speed | Inherent | Accepted. Phase 8 escalates judgment into a prepared session rather than replacing the operator |
| P3-16 | Instrumentation inside Phases 2–3 competes with the work those phases exist to deliver, and sensors are the easier half to build | Medium | Every instrument epic here is **Class A** — judged by the test suite, never by the being — so none consumes an evidence window. If S2-E or S3-E slips while the sensor epics land, the phase was inverted and the reads should say so |

---

## What this plan does not do

- **It does not schedule Priority 2.** Chosen purpose, creativity, play, rest —
  §5 Priority 2 — appear here only as what a subject emerging in Phases 1–4
  might become. They are deferred, and *recorded* as deferred, which is what P2
  failed to do and how six specified capabilities went unscheduled for weeks.
- **It does not claim depth comes from architecture.** With a fixed model, the
  opposite case is live. Decision 2 settles it by probe if the operator wants it
  settled.
- **It does not remove the gate.** It shrinks it by measurement, one clause at a
  time, and keeps a permanent hard core.
- **It does not promise §2's outcome.** There are no readers. The plan builds
  the foundation §5 Priority 1 orders; the fuller aspiration needs people, and
  people arrive at Phase 7 when the operator judges the system has earned them.
