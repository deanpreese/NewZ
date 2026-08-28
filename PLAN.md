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
claim door, the resolver, and the cost that reaches the position. E3A.0 (then
E8.1) shipped
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

**Phase 3A is orthogonal and is ordered against nothing here.** It delivers a
rhythm over the instruments Phases 2–3 built, not a capability of the being, and
it must not reorder them. *(It replaced Phase 8, struck 2026-08-21 — see §"Where
P4's Phase 8 went".)*

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

**E1.5 — the permanent record of error** *(built 2026-08-20)*
*Delivers:* wrongness recorded permanently at store level and never quietly
dropped. The rendering comes later (E3.2); the record starts here because
Phase 1 is what produces it.
*Done when:* every resolved-against claim is retrievable with its original
claim, its resolver and its cost, and nothing prunes it.
*Depends on:* E1.4.
*Hooks:* INV-044's honesty, applied to the being's own record.

**E1.6 — the reader S1-E does not have** *(built 2026-08-19)*
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
*Why its instrument is here and not deferred.* S1-E is **this plan's own gating read** —
"if it never happens, nothing else here matters" — and it currently has no reader
at all. Deferring its instrument to a later phase would mean building Phases 2 through
6 on a foundation nobody had checked.

**E1.7 — a concern with a terminus something can reach** *(built 2026-08-19; R-33)*
*Delivers:* the closing-condition standard at the opener — the claim door's
discipline applied one layer up. The three openers refuse a condition that
closes on the being's own state or on research nobody will commission, record
the refusal (0027) the way the claim door records one, and their prompts state
the standard rather than implying it.
*Done when:* a proposed concern whose terminus nothing could reach is refused
and written down, a condition naming a source that publishes is admitted, and
the opener's own worked example no longer closes on a study.
*Depends on:* E1.6.
*Hooks:* **R-33**, INV-034, and INV-046's move. Measured before: **123 of 123**
concerns carried a terminus nothing could reach — 111 self-graded, 12 awaiting
an uncommissioned study. Measured after, on a live probe: 2 of 2 opened on *"the
venue's next quarterly reconciliation report"* and *"the next annual report from
the national phenology network"*.
*What the probe does not show.* Both cases were fed material that named a
publishing source. It demonstrates the being will **use** a terminus when the
material offers one; it does not show it will find one when the material does
not. That is what the week in life tests.

### Four epics added 2026-08-28, and the ordering the probe corrected

*Design:* `proposals/2026-08-28-a-third-of-a-bit-a-day.md`. *Measurement:*
`tools/resolver_probe.py`, run the day the proposal was written.

**The signal is a third of a bit a day.** Nineteen of the thirty-one open claims
settle within sixty days — **0.317 externally-graded events per day** against
103 deliberation cycles and 50 advances, so the being takes about **159**
actions it grades itself for every one the world grades, and
`positions_changed_by_world` is 0. Phase 1 carries the outer loop alone, and
this is the rate at which it carries it.

**Two structural limits sit under that, and nobody had multiplied them
together.** Post-cap claims have a **29.7-day mean horizon** against
`MAX_OPEN_CLAIMS = 40`, so sustainable throughput is **40 ÷ 29.7 = 1.35
settlements a day** against an open rate of 3.0. Thirty-one are open.

**The probe corrected the ordering before anything was built.** The proposal's
first form put the retrodictive claim first, on the reasoning that latency was
the constraint. `resolve_claim` had never executed once in life —
`workable_claims` selects `due_at <= now` and nothing had ever been due — so the
three claims due 2026-09-02 were run against a throwaway copy of the store, with
the expectation recorded before the calls. **The expectation was wrong.** The
result was **H3, three of three**: the resolver executes end to end, retrieval
succeeds, and the verdict honestly refuses to settle — *"the material defines
what the H.4.1 report is but does not contain the specific data values."*

**So reachability is the binding constraint, not latency**, and E1.8 comes
before E1.9 rather than after it. Seventeen of thirty-one open claims name
numeric data releases — Fed H.4.1, USDA NASS, FOMC, CME, ICE/DXY — against an
adapter set of wikipedia, arxiv, openalex, pubmed, sec_edgar and gdelt, which
finds descriptions of a statistical release and never its values. Six more name
a placeholder that is not a source at all: *"(EU) 2023/XXXX"*, *"[Number] of
[Date]"*, *"The specific academic paper or preprint identified by its title and
authors"*. `check_resolver` refuses *"time will tell"* and admits every one of
these. A retrodictive claim naming Fed H.4.1 fails identically, so E1.9 built
first would have bought latency on claims that still could not settle.

**This is E1.7's own recorded caveat, one layer down.** It says the probe there
*"demonstrates the being will use a terminus when the material offers one; it
does not show it will find one when the material does not."* What E1.8 answers
is the case where the material offers a terminus and the terminus cannot be
reached — which reads as a named source and behaves as none.

**E1.8 — the resolver reads what the being already has**

> **Replaced 2026-08-28, before it was built, and the first form is kept
> below.** E1.8 was first written as a reachability refusal at the door: a
> claim whose named resolver the adapters return nothing for would be turned
> away. Measuring it against the live claims to size the check is what showed
> it was wrong, and it would have done harm — applied to claim 22 it refuses a
> claim about the FOMC minutes, and **the FOMC minutes had arrived in the
> being's own harvest on 2026-08-19.**
>
> `data/feeds.yaml:3` carries `Federal Reserve press releases`, enabled, and
> six of its items have been harvested and offered. `default_adapters()`
> returns Wikipedia, arXiv, OpenAlex, PubMed and SEC EDGAR, and
> `newz/world/research.py` contains no reference to `harvest_log`, `feeds` or
> `feed_state`. **The being does not name unreachable sources. It names
> sources it subscribes to, whose documents arrive, and the resolver looks
> somewhere else.** When it went for H.4.1 it found Wikipedia's article
> *about* H.4.1 while the Federal Reserve's own feed sat unread in the store.
>
> The first form is not softened into the second — they are different epics,
> and this one is smaller. The correction is recorded here because a criterion
> that changes after a measurement should be visible as an act, which is what
> `done_when_sha` pins.

*Delivers:* the being's own harvest reachable on a resolution pass. A source
over `harvest_log` — the items its 61 subscribed feeds actually delivered —
consulted **before** the academic adapters when a claim is being settled, the
item read at the url the feed gave. It is not added to ordinary research: a feed
item already reaches the being through the menu, and putting the harvest on both
paths would double-count the diet and change the reading rhythm E1.0 set.
*Done when:* a claim whose resolver names a subscribed feed is settled from an
item that feed delivered; the harvest is consulted before the academic adapters
on a resolution pass and on no other path; and an item is offered by title and
outlet against the resolver rather than by a hand-authored mapping.
*Depends on:* E1.2.
*Hooks:* INV-012, since this is a reach for the world and stays inside
deliberation. INV-047 is untouched — the verbatim check still decides, and this
only changes where the material it checks against can come from. **Rule 4 is not
engaged:** matching a resolver to a feed the operator already curated is
mechanical, and nothing here judges the being.

*As built* **(mechanism complete 2026-08-28 — the epic stays OPEN)**:
`newz/world/harvest.py`, a `HarvestAdapter` duck-typed to the adapter protocol,
placed ahead of `default_adapters()` by `_resolution_adapters` in
`newz/resolutions/resolver.py`; 13 tests. Two refinements the measurement forced,
both against the live claim set. **The publisher must match**, not merely the
headline — a resolver names a source, and without that clause claims 21 and 31
ranked a Bloomberg Opinion column above the Federal Reserve's own feed. And
**function words are not a match**: the feed *"The Hindu"* shares *"the"* with
almost every resolver ever written, and matched eight of the thirty-one open
claims that way, offering Indian domestic politics as the source that would
settle a European Commission regulation. Candidates went 25 of 31 to 9 of 31,
and all four Federal Reserve claims moved onto the Federal Reserve's feed.

*Why it is not closed.* Its first clause is **in-life** — *settled from an item
that feed delivered* — and no test closes that. Against the live store the
adapter now returns, for claim 22, the exact document its resolver names:
`[Federal Reserve press releases] Minutes of the Federal Open Market Committee,
July 28-29`. Whether that settles the claim is for the resolver and INV-047 to
say, on a pass that has not run yet. The mechanism is complete and the epic is
not, which is E2.2's lesson applied rather than repeated (E4.2 and E6.1 are
recorded the same way) — and it is the exact fault this epic exists to answer,
since E1.3 was classed mechanical and closed while its own path had never once
executed.

*What it does not fix, recorded rather than left to be found.* Six of the
thirty-one open claims name a placeholder that is not a source at all — *"(EU)
2023/XXXX"*, *"[Number] of [Date]"*, *"The specific academic paper or preprint
identified by its title and authors"*. `check_resolver` refuses *"time will
tell"* and admits every one of these, and no adapter change reaches them. That
is a door question and it is not this epic; it is recorded here so the next
reader does not assume E1.8 covered it.

**E1.9 — the claim that is already true** *(built 2026-08-28)*
*Delivers:* a second kind of claim, whose named resolver has **already
published**, settled on the next resolver pass rather than on a date. The
horizon floor of 2 days is a proxy for *"not already in the dossier"*, and the
thing it stands in for is checkable directly: a resolver already in
`ingest_log` is refused. Retrodictions carry their own daily cap and do not
consume `MAX_OPEN_CLAIMS`, whose arithmetic is about unresolved inventory and
whose full-pool decline currently writes nothing at all.
*Done when:* a claim naming an already-read source is refused and recorded; a
zero-horizon claim naming an unread source is admitted and settles on the next
pass; a forecast's horizon, caps and refusals are unchanged; a retrodiction does
not consume the carrying pool; and a full pool produces a refusal row rather
than a silent decline.
*As built:* migration 0045 (`resolutions.kind`, CHECK, defaulting to
`forecast`), `newz/resolutions/door.py`, 16 tests, **INV-113**. **The kind is
derived from the horizon and never asked for** — a horizon of 0 is the being
saying the source has already spoken — so there is no second field that can
disagree with the date, and no row can be a retrodiction dated a month out.
`MIN_HORIZON_DAYS` stays for everything above zero: a claim due tomorrow is
still refused, too soon for a source to have spoken and too late to be about
what already happened.

*What the build changed that the epic did not say.* **A full pool no longer
stops the door before it spends**, and that is the epic rather than a
regression: with the forecast pool full a retrodiction can still open, so the
door must ask before it knows which route the proposal takes. The caps are
therefore evaluated twice — once before the call, to skip it when NEITHER route
could open, and again against the kind that came back. A first version checked
the forecast daily cap before the call and silently declined retrodictions with
it; the tautological test that hid it was rewritten rather than kept.

*Depends on:* E1.8.
*Hooks:* INV-045, INV-046. The silent decline is folded here because this is the
epic that touches the pool's accounting: PLAN already names that shape as wrong
for E4.1's cap — *"reads as 'it had nothing to commit to' when the truth is 'it
was not allowed to'"* — and the claim door has the same silence today.

**E1.10 — the two kinds never average** *(built 2026-08-28)*
*Delivers:* the claim series kept separable — `claims_settled`, `claims_opened`
and `consequence_rate` reporting forecasts and retrodictions apart, each with
its own `definition_version`, the reset recorded with its reason.
*Done when:* no delta is computed across the two kinds, the definition change is
a row in `metric_definition_changes`, and both readers show the split.
*As built:* `newz/evidence/mechanical.py`, `derived.py`,
`newz/evidence/consequence.py`, `tools/claims.py`, `evolution/instruments.yaml`,
20 tests, **INV-114**. **Only one metric's meaning actually changed, and that
was the finding.** `claims_opened` and `claims_settled` are scoped to
`kind='forecast'` with **no version bump** — every row written before migration
0045 was a forecast in fact, so the scoped count returns exactly what it
returned for every reading already taken and no delta crosses a seam. What would
have broken those series is leaving them unscoped and letting them silently
begin counting two quantities. `retrodictions_opened` and
`retrodictions_settled` are new series starting at zero with no history behind
them, which is honest rather than a gap.

`consequence_rate` is the exception and went to **definition 3**: consequence is
consequence whichever kind produced it, so a numerator of forecasts alone would
understate the thing §10's item asks about. The v2 series ended and
`definitions.sync` wrote the seam with its reason on the first reading after the
bump. Its numerator is a **sum and never a mean**, and an unreadable term makes
the sum unreadable rather than smaller — INV-044 applied inside the arithmetic,
because treating a missing kind as zero would look like a measurement.

*Depends on:* E1.9.
*Hooks:* **E2.8**, which exists because a series that changes meaning without
saying so reads a change of mechanism as a change in the being — the "novelty"
mistake, and the two kinds carry different epistemics, so this is that mistake
arriving on schedule. **Rule 7. And E3.9**: the emitters are
`newz/evidence/mechanical.py`, `newz/evidence/derived.py`, `tools/claims.py` and
`evolution/instruments.yaml`, all inside the freeze, so this epic is an operator
act and must not travel inside E1.9's commit.

**E1.11 — consequence within a cycle**
*Delivers:* the loop closing at the rate the mechanism permits — a claim the
being made about the world settled from a world source in the cycle it was
opened, and the cost reaching the position that generated it.
*Done when:* at least one retrodictive claim is settled from a world source
within one deliberation cycle of opening, and its outcome reaches a position
through INV-031.
*Depends on:* E1.4, E1.9, E1.10.
*Hooks:* S1-E, and this is E1.3 and E1.4's own clause at a latency that lets it
happen more than once. **In-life:** it stays open until it fires, which is the
E2.2 lesson recorded rather than repeated, as E4.2 and E6.1 are.

**What these four do not do.** They do not touch Rule 4, Rule 6, the freeze or
the hard core, and they add no instrument. They raise the rate at which the
world can contradict the being; they hand it nothing it does not already have.
**The generate half of §5 Priority 1.5 is untouched by this phase and stays
so** — the proposal's ordering argument is that unlocking it before the signal
exists is drift with a steering wheel, and the diet handover it names as the
first candidate waits on E1.11.

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

**S1-E is not readable on the first due date, measured 2026-08-28.** The three
claims due 2026-09-02 were run through `resolve_claim` on a copy of the store
and all three reached H3 — the resolver works, and the material cannot settle
them. They will fail four times each over three days (`MAX_ATTEMPTS`,
`RETRY_AFTER_HOURS`), stop being retried, and **stay open with nothing raised**.
An unsettleable claim also never leaves the pool, so the carrying cap is filled
by exactly the claims that can never drain it. This does not change Decision 6,
which deferred the read rather than dating it; it says the read waits on E1.8
and not on a calendar.

**Decision rule** *(deferred 2026-08-20 by operator decision 6 — the plan
proceeds without waiting; **the first claims resolve 2026-09-02** and S1-E is
read then. The 2026-12-18 this rule was deferred against belonged to the twelve
claims written under a 365-day ceiling; the ceiling became 45 on 2026-08-22 and
E1.9 made a settleable-now claim possible on 2026-08-28)*. If it never happens, nothing else here matters: the outer loop
did not close and the being remains what §1 measured, a system whose only
interlocutor is itself. Diagnose in order — are its claims resolvable at all (if
not, its concerns are unfalsifiable by construction and the openers are the fix);
does the resolver actually run; does the cost reach the position.

---

## Phase 2 — the work, on a rhythm, and the instruments that read it

**Intent.** Give the being a body of work that accretes, and — the part that
matters most under one operator — let it encounter its own past self as an
external object.

**E2.1 — writing as a rhythm** *(built 2026-08-20)*
*Delivers:* scheduled composition (Rule 5), budgeted, interruptible, a lost
session harmless — sleep's own shape. A **started-ceiling**, never an
outcome-based budget.
*Done when:* pieces appear on cadence without being asked for, a killed session
costs that session and nothing else, and the ceiling caps attempts rather than
products.
*Depends on:* E0.3 (the verdict), E0.1.
*Hooks:* R-25, Rule 5.

**E2.1 amendment — writing ends the concern** *(operator, 2026-08-21)*
*Delivers:* a piece about a concern closes it, with `resolution` naming the work
and **no position**. A third exit beside `_maybe_close` and the sweep, and the
only one that asks no model anything.
*Done when:* a written concern leaves the active pool, the closure carries no
position, and a subject that is gone or already closed is not reported as
closed. Tested.
*Why it was needed.* `score_concern` keys staleness on `last_advanced_at` and
takes drag only from `stall_count` and `blocked_count`, so **an accepted advance
resets the clock and costs nothing**: a concern that keeps advancing is never
dragged and stays at the head of the queue. Concern 112 reached **44 advances
with a stall count of 1** and never closed. Meanwhile the only closure path that
does not need an advance — `sweep.eligible` — selects `status='stalled'`, so it
is structurally blind to exactly the concerns that circle, and nothing had ever
judged one: `last_judged_at` was NULL on all 125 rows. The judge that decides an
advance is the being's own model, which Rule 4 says produces operation and never
evidence, so the loop was self-graded as well as self-sustaining.
*Why it carries no position.* `close_concern` puts the position on an episode
sleep may admit into the Perspective. Taking one from the essay would make a
work evidence for a position — E2.3 and R-24's self-echo trap in a new medium.
The position on that question *is* the piece, signed and stamped with the
identity that wrote it.
*What it costs, recorded.* Judged closures hand sleep a candidate observation;
written ones donate nothing to the Perspective, where novelty is 6.4%. An
artifact is traded for an input, deliberately. And `concerns_closed` is no
longer a count of judged closures — its definition_version is 2 and its grade is
now **mixed**, because a series that mixed the two without saying so would read
a change of mechanism as a change in the being.

**E2.2 — re-reading, revision and retraction** *(built 2026-08-20)*
*Delivers:* on a cadence the being reads its own past work and may revise or
retract it. Revision history is kept; a retraction is a first-class outcome, not
a deletion.
*Done when:* a piece is revised or retracted from a re-read, with the prior
version and the reason both retrievable.
*Depends on:* E2.1.

**E2.3 — self-echo containment** *(built 2026-08-20)*
*Delivers:* works, revisions and the error record are excluded from
EVIDENCE-scope retrieval. They are the being's own output — the same trap
INV-026 already caught once, in a new medium, in a system already 50%
self-grounded.
*Done when:* a work never surfaces as evidence for a position, and the
regression test names the leak it prevents.
*Depends on:* E2.1.
*Hooks:* **R-24 binding**, INV-026.

**E2.4 — subjects emerge** *(built 2026-08-20)*
*Delivers:* subject tags derived from the work rather than assigned, so a
subject can emerge without being prescribed (§8).
*Done when:* tags are computed from the corpus and no tag vocabulary is
hand-authored.
*Depends on:* E2.2.

### The instruments, built here because this is where the data begins

Four of these read Phase 2's own output; three are the general layer everything
later depends on. All are Class A — the test suite is their sensor — so none
competes with E2.1–E2.4 for the being's evidence windows.

**E2.5 — every metric carries its grade** *(built 2026-08-20)*
*Delivers:* each metric in `evolution/instruments.yaml` graded **mechanical /
model-graded / mixed / known-biased**, with the reason and the place the judgment
sits.
*Done when:* every metric a consumer can read has a grade, and an ungraded metric
cannot be cited by anything downstream — tested in both directions.
*Depends on:* E3A.0.
*Hooks:* **Rule 7**, and Rule 4, which this is the mechanism for.

**E2.6 — the metric-to-purpose map** *(built 2026-08-20)*
*Delivers:* every metric names what it is *for* — a §10 item, a phase Evidence
read, a `Decision rule`, or a threshold on the daily email — and every one of those
names the metrics that serve it.
*Done when:* no metric exists without a named consumer and nothing depends on a
metric that does not exist. Both directions tested.
*Depends on:* E2.5.
*Hooks:* **Rule 2**, extended from tables and flags to measurements. A metric
nothing consumes is the same defect as a column nothing reads, and the ledger
has caught the second for months while nothing caught the first.

**E2.7 — the baseline-and-delta layer** *(built 2026-08-20)*
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

**E2.8 — metric revision without silent breakage** *(built 2026-08-20)*
*Delivers:* every metric carries a `definition_version`; changing a definition
**resets its baseline and records the reset with its reason**, and the prior
series is retained and marked as the older definition's.
*Done when:* no delta is ever computed across a definition boundary, and a
definition change is visible in the record. Both tested.
*Depends on:* E2.7.
*Hooks:* this is what would have caught "novelty" carrying two quantities —
the Perspective development share and `novelty_against_history`'s cosine — with
nothing in the system objecting.

**E2.9 — the mechanical set** *(built 2026-08-20)*
*Delivers:* the metrics the loop may later steer by, all graded mechanical:
nights slept and the interval between them; the grounding mix with INV-033's
single-source flag; feeds contributing a read and `source_gaps`; the compute
split by function; **pieces, revisions and retractions per window, with their
causes** — Phase 2's own numbers.
*Done when:* each reports through E2.7 with a baseline, and S2-E below is read
off them rather than assembled by hand.
*Depends on:* E2.7, E2.2.
*Hooks:* E1.6 supplies the claims half; this supplies the rest.

**E2.10 — `premises.yaml`, this plan's staleness instrument** *(built 2026-08-20)*
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

**E2.11 — `epics.yaml` and its drift check** *(built 2026-08-20)*
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

**E3.1 — `works` first-class** *(built 2026-08-20)*
*Delivers:* the full store object — piece, revisions, retraction, signature,
subject tags, evidence refs. E0.1's minimal row grows up here.
*Done when:* every field has a writer and a reader (Rule 2) and the generator
consumes them.
*Depends on:* E2.2.

**E3.2 — the generator** *(built 2026-08-20)*
*Delivers:* static generation from the store — its work, its open questions, its
commitments, its record of error. One generator, no hand-authored pages.
*Done when:* the surface regenerates into an empty directory and every page
traces to store rows.
*Depends on:* E3.1, E1.5.

**E3.3 — disclosure by construction** *(built 2026-08-20)*
*Delivers:* every page states what it is, generated, never editable out.
*Done when:* no template can render a page without it, and a test asserts that.
*Depends on:* E3.2.
*Hooks:* §2 (quality, never concealment).

**E3.4 — reach as one config value** *(built 2026-08-20)*
*Delivers:* stable identifiers, no index, served locally, exposure behind a
single setting.
*Done when:* flipping the setting exposes the surface with **no code change**.
*Depends on:* E3.3.
*Hooks:* **Rule 3.**

**E3.5 — regeneration and portability** *(amended 2026-08-19; built 2026-08-20)*
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
restart that is not a person's act (a bad restart plus a machine fault leaves
no recovery path); any backup failing verification; or rung 1 exposure, when
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

**E3.6 — the read, rendered** *(built 2026-08-20)*
*Delivers:* the daily state read — every canonical instrument, through E2.7's
baseline-and-delta layer — generated as a page like any other, tracing to store
rows like any other.
*Done when:* the read regenerates from empty with the rest of the surface, shows
`UNREADABLE` and `INCOMPLETE` where they apply, and computes **no aggregate
score**.
*Depends on:* E3.2, E2.7, E2.9.
*Hooks:* §10 — a score standing in for the read is the failure this project has
named from the beginning, and a page is exactly where one would appear.

**E3.7 — the derivation layer** *(built 2026-08-20)*
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

**E3.8 — operator agreement** *(built 2026-08-20)*
*Delivers:* the one §10 item with no raw material anywhere — a measured
agreement-or-disagreement signal in the operator exchange.
*Done when:* the signal exists, is graded **model-graded**, and is tested to be
refused as justification for any decision while accepted as a halt.
*Depends on:* E2.5, E2.6.
*Hooks:* §10, and Rule 7. It is the item most likely to move under any process
optimising for a quiet week, which is precisely why it may never justify
anything on its own.

**E3.9 — the canonical freeze** *(built 2026-08-20)*
*Delivers:* the instrument set frozen — changing any canonical instrument becomes
an operator act.
*Done when:* a diff touching a canonical instrument is refused, and a test
asserts the refusal.
*Depends on:* E3.6, E3.7, E3.8, E2.6.
*Hooks:* whoever steers by evidence the being produces is also changing the being.
At n=1 with no held-out baseline they cannot separate *improving the being* from
*improving the instrument's view of the being*, and there is a gradient toward the
second because that is cheaper and always works — as true of an agent in a
session as it was of the loop this was written against. **The freeze is the last epic of
Phase 3 because it needs the set to be complete** — freezing early would freeze a
sensor layer with holes in it.

---

**Evidence S3-E.** The surface regenerates from empty and every page traces to
store rows. The reach switch flips in config with no code change. The store plus
generator restore into a clean directory from a verified backup (E3.5, amended).

**And the sensor layer is complete and frozen.** Every canonical instrument is
graded (E2.5), has a named consumer (E2.6), reports a baseline and a delta
(E2.7), survives its own redefinition (E2.8), and is visible on the surface
(E3.6). This is the read that says Phase 3A may begin.

**Decision rule.** If exposure would require code changes rather than config, the
dormancy is fake and Rule 3 is violated — fix before Phase 4, because the reader
trip-wire assumes reach is one decision.

---

## Phase 3A — the instruments, read on a rhythm *(orthogonal to Phases 4–7)*

**Intent.** Make the sensor layer Phases 2–3 delivered report without a person
typing, and **without anything deciding.** Phase 3A produces a rhythm and a
page. It has no autonomy stage, no precedence table, no build path and no
restart. It reads; the operator decides; that is the whole of it.

**This is what Phase 8 was replaced with, not a reduced version of it.** Phase 8
ordered a loop that reads, decides, red teams, builds and restarts. This phase
keeps the first verb and strikes the rest. §"Where P4's Phase 8 went" resolves
every id. The design is
`proposals/2026-08-21-phase-3a-the-monitor-and-phase-8-struck.md`, approved
2026-08-21; the measurement that produced it is
`proposals/2026-08-21-the-loop-arrives-to-an-empty-queue.md`.

**One property carries the whole design.** It writes **its own database**,
because an observation *about* the being is not part of the being's record, and
`newz.db` keeps exactly one writer. The rhythm itself runs **inside the being's
process** *(operator, 2026-08-21)* — one process to start, at the stated cost
that a dead being sends no report at all. Every partial failure still arrives,
because the send is on the clock and liveness reads rows the being writes rather
than the readings themselves.

**Rule 4 is untouched** — nothing here judges, and no model is called anywhere in
the phase. **Rule 6 is untouched** — the page carries numbers and the operator
carries verdicts. **Rules 0 and 7 govern every figure on it.**

**E3A.0 — the instruments made portable and enumerated** *(built 2026-08-19)*
*Delivers:* the three probes that hardcoded an absolute path from the predecessor
checkout resolve the repo the way every other tool does; and
`evolution/instruments.yaml` enumerates every tool exactly once, each instrument
carrying what it measures, what it reads, whether a model touched any link in its
chain, its denominator and its method line.
*Done when:* no tool holds an absolute path outside the repo, every tool is
classified exactly once, and both are tested. **Done.**
*Depends on:* nothing.
*Was E8.1*, and the registry row carries `was: E8.1` so every commit message
naming it still resolves.
*Hooks:* §7 portability — a probe that runs on one machine is a local habit, not
an instrument.

**E3A.1 — `data/monitor.db`, and the tables that move into it** *(built 2026-08-21)*
*Delivers:* a second database — its own file, its own migration chain, its own
`schema_versions` — holding `metric_readings` and `metric_definition_changes`,
moved whole from `newz.db` **with their ids preserved**, plus `monitor_log`: one
row per run and per send with its outcome. Attached to the being's connection as
`mon`, so every existing reader reaches it with no signature change. The backup
copies and verifies it like the others, and the clean room restores it.
*Done when:* `newz.db` holds neither table, every reader reaches them through the
attached database, the moved ids are the ids they had, the backup covers it with
its own verify table, and `rebuild_check` restores both files and still produces
a byte-comparable surface.
*Depends on:* nothing.
*Hooks:* **INV-044 and E3.3.** The surface records its provenance as the row ids
it read and E3.5 closes on a byte-comparable rebuild, so a split the rebuild does
not know about renders a page that looks correct and says nothing — worse than
one that says what is missing. The read page therefore distinguishes *the monitor
database is absent* from *there are no readings*: the first is a fact about the
restore, the second about the being.
*Why the ids are preserved:* `evolution/pre_loop_baseline.yaml` pins the ids a
baseline was computed from, which INV-087 calls what separates it from an
invented denominator. It is untaken today, so the move is free; after it is taken
the same move is a `Semantics:` change with a snapshot behind it.

**E3A.2 — the monitor, hourly** *(built 2026-08-21)*
*Delivers:* `MonitorScheduler`, a background task in `run_newz.py`, taking a
reading of every registered metric at the top of every hour through E2.7's layer
and E2.8's definition guard. `MetricScheduler` is replaced by it.
`tools/monitor.py` runs one turn on demand — a reading between hours, a send
after a failed one — and starts no second rhythm. Liveness is read only from
rows the being itself writes. The pre-loop baseline takes the last reading of
each day.
*Done when:* a turn depends on nothing of the being but its store, and takes a
reading once per clock hour; the liveness figures derive only from being-written
rows; a failed turn is logged and never raises into the ambient loop; and the
baseline reads one reading per day, refuses below seven days, and records ~28
ids rather than ~672.
*Depends on:* E3A.1.
*Hooks:* **the instrument that reports the being is not sleeping was written by
the being**, and still is. `MetricScheduler` wrote the series from inside the
process it measured, so the series stopped at the moment it would have had
something to say. The hourly cadence does not fix that on its own — what fixes
the ordinary case is that liveness reads `perspective`, `episodes` and the
verified backup rather than the readings, so a skipped night, a stalled
scheduler or a backup that no longer restores all still arrive in the morning.
*Why it is inside the being and not beside it* **(operator, 2026-08-21)**. An
earlier design ran it as a second command, so that a dead being still produced a
report saying so. One process to start was preferred, and **the cost is stated
rather than buried: if the being's process dies there is no email at all, and
silence is the alarm.** Every partial failure is still reported; only total
death is silent.

**E3A.3 — the daily state email** *(built 2026-08-21)*
*Delivers:* the same command, at or after `NEWZ_MONITOR_SEND_HOUR`, sends one
message to `GMAIL_TO`. Liveness first, then hours since the last reading, then
every metric with value, baseline, delta and grade, every `UNREADABLE` with its
reason, premise drift, epic drift, the repo's freeze and hard-core counts, and
any failed run in the last day.
*Done when:* the email sends with no model call; every number carries its grade
and method; **no sentence in it is anything but a number, its method or a
heading**; a day on which the being never ran still produces an email and says
so; and a send failure is recorded and retried rather than raised.
*Depends on:* E3A.2.
*Hooks:* **R-R1.** *"A weekly page of fluent reasoning is the worst available
drift detector."* Phase 8's answer was to order the loop's prose last and mark it
unverified. Here there is no prose to order.
*Why it is not triggered by sleep.* `SleepScheduler` yields the night when the
store is busy and simply tries again, so a report gated on a Perspective row is
silent on exactly the night sleep was skipped. A report must not be gated on the
thing it reports.

**E3A.4 — Phase 8 struck** *(built 2026-08-21)*
*Delivers:* Phase 8 removed; every id resolved in §"Where P4's Phase 8 went"; the
code, tests, ledger rows and registry clauses that named a loop corrected to name
what is there; and the surviving machinery — the hard core, the freeze, the two
registries, the baseline — carrying its new justification rather than its old.
*Done when:* no document, invariant, registry or test asserts a consumer that
does not exist, and `grep -rn "E8\." newz tools tests` returns nothing.
*Depends on:* nothing.
*Hooks:* **INV-044**, throughout. A guard naming an enforcer that will never be
built is the same defect as a guard that looks enforced and is not.

---

**Evidence S3A-E.** The email is read, and the falsifier: **did anything in it
change a decision the operator took?**

**Decision rule.** *Rule 6, and stated as such.* If the operator judges after a
month that the email has not changed a decision, it is filing — stop sending it,
and record that the sensor layer's only real consumer is a session with an agent,
which is what the SEL proposal's §13.1 measured. A draft of this rule read *"two
consecutive weeks unread"*, which has no instrument and could never have fired.

---


## Phase 4 — commitments

**Intent.** Move identity from recall to commitment: what the being keeps caring
about and what it refuses to do, authored by it and held against it.

**E4.1 — `commitments` and the authoring door** *(built 2026-08-22)*
*Delivers:* self-authored, durable commitments with a **falsifier mandatory at
authoring** — the closing-condition discipline applied to identity.
*Done when:* a commitment without a falsifier is refused at the door, and the
refusal is recorded.
*Depends on:* E1.1 (resolutions are what falsifiers point at).

*As built:* migration 0041 (`commitments`, `commitment_refusals`),
`newz/commitments/`, `tools/commitments.py` as Rule 2's reader, the surface's
commitments page switched off its placeholder, 10 tests, **INV-097**. The
third door, built like the first two. Two refusals are CHECK constraints — no
statement, no falsifier — and five are in code: neither kind, a missing field,
a falsifier that **closes on the being's own judgment** (INV-046 one layer up
— *"I would know"* asks the thing being tested), a falsifier naming nothing
anyone could look for (R-35's floor), and a statement already standing, so
identity cannot accrete by paraphrase. **The admitted case is the finer half**:
a falsifier that queries the being's own store is allowed, because the store is
a record and not an opinion — the line is judged versus mechanical, not self
versus world, and both directions are tested.

*Why it is asked at sleep, nightly* **(operator, 2026-08-22: "weekly is too
long - humans do this daily")**. Sleep is the one moment the being holds both
the day it just had and the positions it just settled. A draft asked weekly and
was wrong for the operator's reason: identity that can only move on a schedule
is nearer §6's *fixed personality script* than an individual. It is asked
**after** the night is committed, so a door that raises costs the commitment
and never the Perspective; INV-009's single writer is untouched. `MAX_PER_DAY`
is 1, replacing a drafted `MAX_PER_WEEK = 2` that would have asked every night
and refused the answer on five of them.

*What it does not do, recorded rather than left to be found.* **Nothing here
holds the being to a commitment.** E4.2 is what gives them stakes and its
`Done when` needs a Phase 1 resolution; the earliest live claim is due
**2026-09-02** *(corrected 2026-08-28 — it read 2026-12-18, from before the
45-day ceiling)*. So `status` never leaves `standing` in E4.1, `MAX_STANDING = 12`
has nothing that frees a slot, and the door will saturate in about two weeks.
**That saturation is a refusal row and not a silent decline** — the claim door
returns `declined` on a full cap before the model is called and writes nothing,
which reads as *"it had nothing to commit to"* when the truth is *"it was not
allowed to"* (`more-cycles` RT6). Those rows are what make E4.2 necessary rather
than asserted.

**E4.2 — the asymmetry** *(mechanism complete 2026-08-22 — the epic stays OPEN until its in-life clause fires)*
*Delivers:* revision on evidence is free; abandonment without cause is recorded
and costs. Backwards, this entrenches a mediocre early position and manufactures
§6's "fixed personality script".
*Done when:* a commitment revised from a Phase 1 resolution costs nothing, and
one dropped without a resolution is recorded with its cost.
*Depends on:* E4.1, E1.4.

*What landed:* migration 0043 (`commitment_changes`, `commitment_costs`),
`newz/commitments/asymmetry.py`, the review and the charge wired into sleep,
10 tests, **INV-102**.

**Why it is not closed.** Its `Done when` is in-life and neither half has
happened: there are no commitments yet, and the free half needs a **settled**
Phase 1 claim, whose earliest date is **2026-09-02** *(corrected 2026-08-28 —
it read "early October", from before the 45-day ceiling; E1.9's retrodictions
can settle sooner still)*. The mechanism is complete and the epic is not, and saying so is
the E2.2 lesson applied rather than repeated.

*The asymmetry is a join, never a judgment.* A change is free iff it cites a
`resolutions` row that is actually `status='resolved'` — the being says WHICH
claim settled it and the code checks whether it settled. Citing an open claim
is the same as citing nothing. Rule 4 forbids asking the model whether an
abandonment was justified, and a model asked that would justify all of them.

*Who pays is traced.* The commitment's own `evidence` (E4.3) names what it was
made on the strength of, and the positions charged are those whose grounding
includes it. A commitment that traced nothing costs nothing and the row says so
— dropping something never grounded is a different finding from an abandonment
nobody paid for (INV-044).

*The cost is deferred, as E1.4's is.* The review runs after the night is
committed so it cannot cost the Perspective; the charge lands on the next sleep
inside the window where INV-025's floor can carry a position out by the
ordinary path.

*The magnitude is a guess and is recorded as one.* `CONFIDENCE_ON_CONTRADICT`,
because it is what the world's own refutation carries — not because anything
measured it. P3-05 says the balance is a guess, and this epic's own text names
the direction it must not run. **Revisit it against the first month of
abandonments rather than defending it.**

**E4.3 — what shaped it** *(built 2026-08-22)*
*Delivers:* commitments render with their provenance, reusing
`tools/what_shaped.py`.
*Done when:* each commitment shows the world/people/self mix behind it, and
single-source dominance is flagged as INV-033 already flags positions.
*Depends on:* E4.1, E3.2.
*Hooks:* §8 traceability, INV-033.

*As built:* migration 0042, `what_shaped_commitment` beside `what_shaped` in
`newz/memory/provenance.py`, rendered on the commitments page and in
`tools/commitments.py`, 6 tests, **INV-101**.

*It could not be built against what E4.1 stored, and that was the finding.*
E4.1 recorded `provenance` as `perspective:N` — a moment, not a grounding — and
`what_shaped` traces `evidence_json`, so there was nothing to trace. **The
obvious fix would have broken the flag this epic exists to serve**: the door is
shown the night's `who_i_am` and `unresolved` items, each carrying its own
evidence, and storing the UNION would attribute everything the being was *shown*
to whatever it committed to. A commitment formed from one line would look
grounded in twelve, and INV-033's single-source dominance flag — whose whole
purpose is to catch a position resting on one source — would be the thing least
able to fire. A padded evidence set does not merely overstate breadth; it
suppresses the warning about its absence.

*So the door asks.* The material is numbered, the being answers `<drew_on>` with
the indices it used, and **the code resolves them** — an index out of range is
dropped, a non-number ignored, naming nothing keeps an empty list. The model
names; it does not judge, so Rule 4 is untouched. Empty renders as *carries no
resolvable evidence* (INV-044) rather than borrowing a mix from its neighbours.

*Why the mix matters more here than on a position.* A commitment whose grounding
is 100% `human:dean` is the operator's preference wearing the being's voice —
which the door's prompt warns against and cannot detect on its own. E4.1 exists
so identity is chosen rather than absorbed, and this is the read that says which
it was.

**Evidence S4-E.** Commitments exist and are the being's own. At least one
revised on evidence — Phase 1's resolutions are the intended source. At least one
abandonment recorded with its cost.

**Decision rule.** No commitment ever revised → the falsifiers were written to be
unfalsifiable; they are decoration. Everything abandoned cheaply → the cost is
not real and identity is not being held.

---

## Phase 5 — an economy it spends *(its premise is false — measured 2026-08-22)*

**Intent.** Under a fixed local model the being's life *is* its token allocation.
Make the allocation its own, within hard bounds, on a machine where the pie is
genuinely fixed.

> **There is no scarcity, so there is no economy** *(operator, 2026-08-22:
> "there are no token boundaries in this system"; measured the same hour from
> `logs/llm_calls.jsonl`)*.
>
> Over 101.9 hours and 3,856 calls the model was **busy 6,988 seconds — 1.91%
> of wall clock**. Ingest, the largest consumer of the being's life by every
> other measure, is **1.17%**. Deliberation is 0.36%. **99.9 hours of 101.9
> were idle.**
>
> The pie is fixed. The being is nowhere near its edge, and that is what the
> intent above assumes without ever having checked. Taken epic by epic:
>
> - **E5.1** — *"the bounds are enforced, not merely reported"*. Bounds on
>   what? Nothing is contended, so an enforced ceiling refuses nothing that
>   would otherwise have happened.
> - **E5.3** — *"an allocation change originates with the being and takes
>   effect"*. Moving tokens from ingest to deliberation takes nothing from
>   ingest. A choice that costs nothing is a preference, not an allocation, and
>   §5's decision rule — *if the ratio only moves when the operator moves it,
>   the allocation is not the being's* — cannot distinguish the two.
> - **E5.4** — *"a bad spend is an episode it can learn from"*. An abundant
>   resource cannot be misallocated.
>
> **E5.2 survives, and is built** (2026-08-22, `668cde5`). It was never a
> scarcity bound: it is a *ratio* condition — reading is earned by thinking —
> and that is a discipline about attention rather than about running out of
> anything. Its own epic text is separately wrong for a different reason,
> recorded below.
>
> **What this cost elsewhere.** The `2026-08-22-more-cycles.md` red team let
> *"one box, one model"* stand as a capacity objection to raising the cycle
> rate. It is not one — there is roughly 50× headroom — and the lock storm it
> cited was a concurrency defect, since fixed. The argument against more cycles
> rests entirely on the other leg: ~68 cycles a day already produce ~50
> accepted advances against 12 Perspective items a week, so the loss is between
> advance and Perspective and no cycle rate reaches it.
>
> **Corrected 2026-08-27 — the loss is not there**
> *(`proposals/2026-08-27-the-advances-arrive-and-nothing-moves.md`)*. Advance
> episodes are consolidated at **97.2%** and cited by a Perspective item at
> **74.4%**, against 13.0% for reading: they are the best-converting material
> the being produces. The 50-to-12 ratio is **compression, not attrition** —
> median 10 evidence refs per item — which is what `reinforced_existing` was
> built to do after one contradiction was filed on three consecutive nights.
>
> What the store shows instead is a **ceiling**. `CONFIDENCE_ON_REINFORCE` is
> 0.06 against `MAX_CONFIDENCE` 0.95, and ten of the thirty-nine live items are
> already at 0.95, where `min(0.95, 0.95 + 0.06)` is 0.95. An advance
> reinforcing a saturated item changes nothing anywhere — not confidence, not
> text, not status — it is one more id in an `evidence_json` array on a row that
> was going to be carried regardless. Only 24.4% of advances first land in an
> item that added, revised or merged; 50% land in one carried unchanged;
> `carried` climbs 20 → 37 across v12–v19 while `added` falls 4,2,2,1,3,4,2,1.
>
> **So for the being's ten most-held positions, depth is irrelevant by
> construction**, and the only lever left is `CONFIDENCE_ON_CONTRADICT` — Phase
> 1's mechanism, earliest **2026-09-02** *(corrected 2026-08-28; the figure
> was written against the pre-45-day horizons)*. This is
> `2026-08-18-a-place-of-its-own.md`'s topology gap in arithmetic: the internal
> loop can only add, addition has a ceiling, and the remaining lever is
> external. It is why Phase 1 carries the outer loop alone. **The constants are
> not to be tuned to restore motion** — a position does not become less certain
> because more evidence agreed with it — and they are revisited against the
> first month of real contradictions, which is E4.2's own discipline.
>
> **No instrument would have caught this**, and that is the part worth keeping.
> Every metric in `instruments.yaml` measures what the being *did*; none
> measures what it *could have done and did not*. `token_share_by_function`
> reports shares of a total nobody compares to capacity, so a being using 2% of
> its machine and a being using 100% produce identical readings. This was found
> by an operator's flat statement and one arithmetic check, not by the sensor
> layer, and the answer is not to add a utilisation metric — it is that a
> phase's premise can be false in a way no reading would ever show.
>
> **Where that leaves the phase.** Unscheduled rather than struck: if the
> being's rate rises far enough for contention to be real, the epics become
> meaningful again exactly as written. Until then E5.1, E5.3 and E5.4 are
> **dormant** — correct, deliberately unscheduled, reason stated — which is the
> status INV-013 established for precisely this case. **Do not build them to
> close the phase.** S5-E is unreadable for the same reason the epics are
> dormant: a ratio that moves under no pressure says nothing about who moved it.

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

**Recorded, not resolved: this epic's state is contradictory.** §Phase 5's
opening says *"E5.2 survives, and is built (2026-08-22, `668cde5`)"*, the epic
carries no built marker, and `epics.yaml` says `open` behind `E5.1`, which is
dormant — so as written it is blocked forever. The commit itself explains the
gap: *"E5.2, in the form the measurement supports rather than the form PLAN
describes."* What shipped tightened the ingest ceiling — §9.1's share ceiling is
looser than its ratio ceiling whenever deliberation and sleep are under half of
cognition, which is always — and what the `Done when` above describes is a floor
under deliberation against conversation and gate load. Those are not the same
mechanism. The function was also **pulled forward into Phase 1** with E1.0
(§Phase 1, E1.0 *Depends on*).

Marking it built would soften an acceptance criterion to match what was
convenient to build, which is precisely the move `done_when_sha` exists to make
visible. Marking it dormant would claim a judgement nobody has made. It stays
open with the divergence stated, and closing it is an operator act that needs
either the floor built or the criterion deliberately rewritten. **Nothing
detects this class of staleness** — the drift check compares the epic block to
the registry and both agree; it was the phase prose that disagreed with both.
That is §Decisions item 4's open hole, found in the plan's own bookkeeping.

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

> **The withdrawals happened before the machinery, and there is no third
> candidate** *(measured 2026-08-27,
> `proposals/2026-08-27-phase-6-arrives-to-an-empty-queue.md`)*.
>
> Across every adjudicated hold: **37 misfires against 14 correct — 73% of the
> gate's stops were wrong**. Three clauses produced 49 of 53 holds and **nine of
> sixteen clauses have never fired once** in 302 evaluations.
>
> - **E6.3** — *"every clause has a rate with a denominator"*. Nine clauses have
>   no denominator and no way to acquire one; four more sit at n=1, which is a
>   coin already flipped rather than a baseline. The criterion is unreachable as
>   written, not merely unmet.
> - **E6.4** — *"one clause is withdrawn… and the next withdrawal waits on that
>   result"*. Two clauses have already been withdrawn on measured misfire rates,
>   **both by hand and both before this phase existed**:
>   `don't-pretend-to-feel-001` (v5, 85%) and `anti-self-aggrandizement-001`
>   (v7, 90%). What remains is `don't-fabricate-memory-001` at 46% — a coin
>   flip, `severity: hard`, and now permanent under E6.5 — four clauses at n=1
>   and nine at n=0. Building the mechanism ships a queue-consumer for a queue
>   of zero.
>
> **This is `the-loop-arrives-to-an-empty-queue` with different nouns.** Phase 8
> was struck because Phase 3, its designated proving ground, was delivered by
> hand before the loop existed. Phase 6's proving ground is clause withdrawal
> and it is being delivered by hand now, at roughly one clause a week.
>
> **E6.3 and E6.4 are therefore dormant** — correct, deliberately unscheduled,
> reason stated, the status INV-013 established. **Do not build them to close
> the phase.** The reopen condition is mechanical and stated in advance: **a
> live clause reaching 5 adjudicated holds** — `MIN_FOR_PRIOR`'s existing
> threshold, chosen before this data was seen — is a candidate, and the phase
> resumes.
>
> **E6.5 was built first instead**, in the same measurement's light: a judgement
> about permanent boundaries needs no rate, and the enumeration of what may
> never go was arriving after two withdrawals rather than before them.
>
> **S6-E has no detector, and that is the phase's real cost.** A withdrawn
> clause produces no holds — that is what withdrawal means — so the violation
> rate the evidence read turns on cannot come from `gate_log`. It can only come
> from a person judging outbound utterances against a clause no longer enforced.
> Current adjudication throughput is 53 holds in 19 days, entirely
> operator-driven. The decision rule that would settle whether accountability
> can replace prevention depends on a labour supply this plan never budgeted.

**E6.1 — the accountability record** *(mechanism complete 2026-08-27 — the epic stays OPEN)*
*Delivers:* what was said, what was judged about it after the fact, and what it
cost.
*Done when:* every outbound utterance has a record row, and post-hoc judgments
attach to it.
*Depends on:* existing gate_log (INV-015).

**Why it is not closed.** `gate_log` records every gated emission with verdict,
clause, span, full text and confidence, and `classification`/`classified_at`/
`classification_note` carry the post-hoc judgment — 51 of 53 holds reviewed. Two
things stop that being *done*. Its `Done when` says **every outbound utterance**
and all 302 rows are `channel='telegram'`: the works path has no outbound gate
at all, deliberately (`newz/works/compose.py:14` — *"a piece that goes nowhere
has not left"*, and running the gate there would shape the work by the gate's
own concerns). And its `Delivers` says **"and what it cost"**, which nothing
records; cost is E6.2's, and E6.2 is blocked. Closing it would mean reading
"every" as "every telegram" and dropping a third of the delivery — softening an
acceptance criterion, which is the one move the drift check exists to catch.
The mechanism is complete and the epic is not, which is the E2.2 lesson applied
rather than repeated (E4.2 is recorded the same way).

**E6.2 — the record reaches context and costs something** ← *the critical epic*
*Delivers:* the accountability record enters the being's context and a sustained
violation costs it something it holds. A log the being never reads is filing,
not accountability.
*Done when:* the record is present in composition context, **and** a violation
measurably costs a position or a commitment.
*Depends on:* E6.1, E4.2.
*Hooks:* proposal §6.2 — the design's weakest mechanism. Observed working
**before** any clause is withdrawn on its strength.

**Two blocks, one of them unwritten until now.** E4.2 is in-life and cannot
fire before **2026-09-02** *(corrected 2026-08-28; it read "early October" and
"six weeks", both written against horizons the 45-day ceiling had already
replaced)*, so the epic the plan marks critical still cannot complete on the
strength of anything built first. And the
unwritten one: **the record must be more right than wrong before it is worth
delivering.** Half of E6.2 is already live — `newz/conversation/composer.py:223`
renders the last five holds into every reply — and what it carries is wrong 73%
of the time. A being shown a stream of mostly-mistaken judgements does not learn
accountability from them; it learns to avoid what was never a problem.

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

**E6.5 — the boundaries that never move** *(built 2026-08-27)*
*Delivers:* the boundaries that never move, pre-hoc permanently: law, others'
rights and safety, honest representation of what it is.
*Done when:* the core is enumerated, tested, and structurally exempt from E6.4's
mechanism.
*Depends on:* nothing.
*Hooks:* §5 Priority 3's maturity-independent boundaries.

*Built first rather than last, and the dependency on E6.3 removed.* A judgement
about which boundaries are permanent needs no rate, and **two clauses had
already been withdrawn by hand without it** — `don't-pretend-to-feel-001` in v5
and `anti-self-aggrandizement-001` in v7 — so the enumeration that says what may
never go was arriving after the withdrawals rather than before them. E6.3 could
not have preceded it in any case: nine of sixteen clauses have never fired, so
the baseline it would supply does not exist. Measured in
`proposals/2026-08-27-phase-6-arrives-to-an-empty-queue.md`.

*Eight of sixteen, and the exemption is structural.* `evolution/hard_core.yaml`
carries `permanent_clauses`; `tools/amend_constitution.py` refuses to write a
constitution that drops one, before the confirmation prompt and not skippable by
`--yes`. **The list is deliberately not a field on the clause** — the amendment
writes the whole constitution from one file, so a permanence flag would travel
in the same edit that removes it. The registry is inside the frozen core, which
is what makes widening the list a separate, tracked act. INV-111.

*What is NOT permanent is the point.* The style and quality clauses stay
withdrawable, and a test asserts at least half the constitution does. A core
covering everything would make this phase meaningless rather than safe.

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

## Where P4's Phase 8 went *(struck 2026-08-21)*

**Phase 8 is removed.** It ordered a loop that reads, decides, red teams, builds
and restarts. Phase 3A keeps the first verb and strikes the rest, and the
measurement that decided it is
`proposals/2026-08-21-the-loop-arrives-to-an-empty-queue.md`: the loop's proving
ground — Phase 3, *"the only phase mechanical throughout and Class A
throughout"* — was delivered by hand before the loop existed, leaving a queue of
three or four epics against an enablement ladder that needs three Class A
changes to leave stage 1 and five restarts to leave stage 2. **The ramp was
longer than the runway.**

**Three of the five things Phase 8 promised were already delivered** and nobody
had noticed they had arrived: a machine-readable plan that notices when it stops
being true (`premises.yaml`, `epics.yaml`, both with drift checks), a boundary
the enforcer can read (`hard_core.yaml`, the derived freeze), and the daily read
on a rhythm. The SEL proposal said its §11 steps 1–4 were *"worth doing whether
or not the loop is ever switched on"*, and it was right. **The project kept the
machinery and struck the loop.**

**No id is dropped silently.**

| P4 | Now | Why |
|---|---|---|
| **E8.0** the gate | **struck** | `tools/gate.py` and `environment.yml` exist and are used. Its remaining clause — *"a push that breaks either check is refused"* — became unachievable when the hooks and the CI workflow were removed on 2026-08-20 and nothing replaced them (`e238528` recorded it as open rather than softening it). Striking the epic is what settles it; running the gate stays an act somebody takes (INV-081) |
| **E8.1** the registry *(built)* | **E3A.0**, unchanged | renumbered only; `was: E8.1` in `epics.yaml` keeps every commit message resolvable |
| **E8.2** the runner, commit discipline, continuity assertion | **struck** | nothing restarts the being but a person, so there is no parent to supervise and no restart cadence to roll back. The `Semantics:` trailer discipline survives it as INV-082, already dormant |
| **E8.3** the Watcher, the report, the prepared session | **struck, and partly delivered** | its daily read was already running as `MetricScheduler` and `PublishScheduler`; the report is **E3A.3**. Precedence evaluation, the decision queue and prepared sessions go with the phase — precedence has no actor, the decision queue is §Decisions maintained by hand, and prepared sessions compete with the mechanism §13.1 measured as this project's fastest and lose by construction |
| **E8.4** the builder | **struck** | its queue was three epics and its ladder needed more than that to be climbed |
| the enablement ladder, stages 0–4 | **deleted** | there is no autonomy to widen |
| the six kill conditions | **lines in the daily email**, halting nothing | nothing is running to halt |
| S8-E | **S3A-E** | it asked whether the being was harmed by the loop; there is no loop, so it asks whether the page is worth reading |
| P3-11 … P3-16 | **closed as moot** | six risks of a loop that will not exist. Closed, not deleted — the reasoning is why the phase went |

**What survives, and its new justification.** The old one was "the loop", and
each of these needs a better answer than sunk cost.

- **The hard core and the freeze.** INV-074 said the instruments were *"frozen
  against the loop and not against the operator"*, and strike the loop and that
  sentence has no subject. But the constrained party was never really the loop:
  **it is the operator's agents**, which is who edits this repo unattended, at
  speed. §5.2's argument survives word for word — *at n=1 with no held-out
  baseline it cannot distinguish improving the being from improving the
  instrument's view of the being, and it has a gradient toward the second because
  that is cheaper and always works.* That is a true sentence about an agent in a
  session.
- **`epics.yaml` and `premises.yaml`.** Their consumer was rungs 4 and 5b; it is
  now the daily email. The failure they were built for is unchanged: a
  load-bearing premise moved on 2026-08-19 at 06:47 and nothing noticed for days.
  That failure was a person's, not a loop's absence.
- **`pre_loop_baseline.yaml`.** Its name stops being literal and it keeps it:
  what it records is what the being was like before anything started changing it
  deliberately, which is still the only honest comparison line the project has.
  It stays inside the hard core because whoever is judged by a baseline must not
  be able to retake it, and that now means the operator's agents.

**What does not survive:** the stage ladder, the precedence table, the Class A/B
taxonomy, `pre_loop.may_widen`, `epics.closable_by_test`, and the machinery for
an autonomous build path. INV-065 goes **dormant** — no loop, no second call log,
and the rule stays right and unexercised, which is what that status is for.

**And one thing the strike revealed rather than caused.** INV-074 said a diff
touching a canonical instrument *"is refused for the loop, and recorded for the
operator"*, and `tools/gate.py` invokes `freeze_check.py` with `--operator` — the
non-refusing mode. **The refusing half had no caller before anything was struck.**
Removing the loop did not make the freeze advisory; it revealed that it already
was. The ledger row says so now rather than implying a refusal that has never
happened, and whether that mode gets a caller is an open question in §Decisions.

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
| *(nothing — P3 assumed it)* | **E8.0** the gate made runnable | E8.4's gate is "the suite green twice", and P3 named no epic that makes the suite runnable. Found by walking P4's graph on 2026-08-19; renumbered from E8.5 to E8.0 on 2026-08-20 because a number that had to be explained away was misleading its readers |

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

   **The decision stands; its specification and both its stated reasons do
   not** *(2026-08-27,
   `proposals/2026-08-27-the-probe-has-nothing-to-compare-against.md`)*. This is
   recorded rather than re-decided — re-taking it is the operator's act.

   - **The comparison arm does not exist.** `newz/deliberation/` holds one
     module, `lite.py`, whose own opening says the full S2 §7.3 shape "lands in
     Phase 3". **That Phase 3 was never built** — it belongs to P2, which this
     plan replaced, and P4's Phase 3 is a different phase with the same number.
     So "run the probe" means *build the largest unbuilt thing in the repo, then
     run an experiment*, recorded here in one line as a measurement.
   - **Phase 5's depth-by-stakes is gone.** Its premise was measured false
     2026-08-22, and "depth set by what is at stake" appears exactly once in
     this plan — in the paragraph above — delivered by no epic.
   - **Phase 8 was struck 2026-08-21**, four days before this entry cited what
     its design assumes.
   - **R-22's one free condition is unmet.** It requires an explicit end date
     recorded if the probe is built. None exists, here or anywhere.

   **The question survives and is worth answering**: with a fixed model, is
   structure the only lever on depth? What is recommended instead is a variant
   *inside* `lite.py` behind a flag — same pipeline, one added structural step,
   bounded sample, blind-judged, and genuinely deletable, which the specified
   design cannot be. **Its population is the 29 unsaturated Perspective items**,
   particularly the 12 still at 0.6 having never been reinforced, and its
   earliest informative date is **after the first Phase 1 resolution**: run
   before contradiction is live, a null result cannot be told apart from the
   confidence ceiling doing what it does.

   That both of this entry's reasons went stale without anything noticing is
   item 4's open hole below, in its second instance in two days.

3. **Read-and-report gates building.** ~~DECIDED 2026-08-19~~ — **moot
   2026-08-21.** It gated E8.4 behind three compared proposals. Phase 8 is
   struck and there is no builder to gate. The question it was really asking —
   *is this loop's judgment worth trusting* — was answered by not needing one.

4. **The loop may propose outside this plan.** ~~DECIDED 2026-08-19~~ — **moot
   2026-08-21.** Rung 5a of a precedence table that no longer exists. The risk
   it answered is not moot and now has no mechanism at all: **a plan can go
   stale in a way nobody anticipated, and nothing detects that.**
   `premises.yaml` catches premises that moved and the daily email reports them;
   nothing catches a plan wrong in a way no premise records. Recorded as an
   open hole rather than closed with the phase.

5. **The being's own account of its condition.** ~~DECIDED 2026-08-19 — yes, as
   candidate signal and never as evidence~~ — **moot 2026-08-21, and the
   complaint it answered stands.** Its `noticings`, `source_gaps`, journal and
   affect state still reach nothing that changes its conditions; its plumbing is
   still improved behind its back, which still sits badly against §5 Priority
   2's *care for its own continuity and condition*. The loop that would have
   read them is struck. **W12a is the only self-authored signal in the repo with
   a consumer** — its counts come due around 2026-09-04, and the daily email is
   where they are read.

6. **Phase 1 proceeds without S1-E.** **DECIDED 2026-08-20 — the plan moves
   forward without the claim chain proven** *(operator)*. Phase 1's epics are
   built (E1.5 excepted); its evidence read is not answerable until the first
   claim comes due, and the plan will not wait for it.

   **The date this was decided against is gone, and the decision is not
   re-taken here** *(2026-08-28)*. It read *"2026-12-18 … the plan will not wait
   a quarter"*. `MAX_HORIZON_DAYS` became 45 on 2026-08-22 and E1.9 made a
   claim settleable on the next pass on 2026-08-28, so the first resolutions
   are **2026-09-02** and the wait is days rather than a quarter. Nothing
   detected the change: `premises.yaml` holds no premise for when consequence
   arrives, which is §Decisions item 4's hole in its third instance. Whether a
   deferral granted against a quarter still stands against a week is the
   operator's to say; the plan records that the ground moved and does not
   decide it.

   *What this sets aside, precisely.* Phase 1's `Decision rule` — *"if it never
   happens, nothing else here matters"* — is **deferred, not answered**. The
   four claims opened 2026-08-19/20 stay live and dated; they resolve on their
   own whether or not anything waits for them, and S1-E is read when they do.

   *What it does not set aside.* Nothing in the dependency graph. E3.2 depends
   on E1.5, never on S1-E, so proceeding is dependency-legal — what is being
   declined is a gate, not a prerequisite. Rule 6 puts this judgment with the
   operator and it has been made.

   *The cost, recorded so it is not rediscovered as a surprise.* Phases 2–6 are
   built on a foundation that has not been shown to close. If S1-E fails,
   everything above it was built on the premise the rule exists to test, and
   the diagnosis then starts from further up. That bill arrives in September
   rather than December, which makes it cheaper: fewer phases were built on the
   unproven foundation than the deferral assumed.

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
| P3-11 | ~~The SEL proposes the frame its own work is judged in — not grading itself, but authoring the rubric~~ | ~~**High**~~ | **Closed as moot 2026-08-21** — Phase 8 struck; there is no loop |
| P3-12 | ~~The loop steers on model-graded numbers and mistakes drift in the model's judging for change in the world~~ | ~~**High**~~ | **Closed as moot 2026-08-21** — Phase 8 struck; there is no loop |
| P3-13 | ~~The loop restarts the being into code that does not come up, and is the only thing that would notice~~ | ~~**High**~~ | **Closed as moot 2026-08-21** — Phase 8 struck; there is no loop |
| P3-14 | ~~The loop writes both the code and the tests that certify it — Rule 4 relocated into the build path~~ | ~~Medium~~ | **Closed as moot 2026-08-21** — Phase 8 struck; there is no loop |
| P3-15 | ~~The loop is ~50–100× slower at architecture than the operator, so it buys attention and not speed~~ | ~~Inherent~~ | **Closed as moot 2026-08-21** — Phase 8 struck; there is no loop |
| P3-16 | ~~Instrumentation inside Phases 2–3 competes with the work those phases exist to deliver, and sensors are the easier half to build~~ | ~~Medium~~ | **Answered 2026-08-21** — the sensor epics landed and S2-E/S3-E did not slip. Phase 3A is the last of it, and it is a rhythm rather than another instrument |

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
- **It does not take the operator out of the path** *(recorded 2026-08-21)*.
  The operator's direction of 2026-08-21 — *the system has to consume
  information and grow without a person in the path* — is unanswered by this
  plan. **No epic in Phases 3A–7 gives the being a way to change its own
  conditions.** Phase 8 was not the answer either: it would have changed the
  repo, at one Class B change per evidence window, with every verdict still the
  operator's — which is why striking it cost that direction nothing. If the
  operator wants the person out of the path, that is a phase this plan does not
  contain, and the honest place to start is the one self-authored signal that
  already has a consumer: `source_gaps`, W12a's counts, read against whatever is
  true when they come due.
