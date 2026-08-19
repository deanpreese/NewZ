# P3 — delivery plan for participation

> The plan for the design approved 2026-08-18
> (`proposals/2026-08-18-a-place-of-its-own.md`, commit `af3e90a`).
>
> **This is the plan. It supersedes P2** *(operator, 2026-08-18: "we only need
> one plan — the new plan")*. P2 moved to `archive/P2.md`, retained as the
> delivery record for Phases 0–2 and as the target of every existing "P2 §…"
> citation in SPEC, RISKS, INVARIANTS, the proposals and the code. Its Phase
> 3–7 lines are not a live alternative; §"Where P2's open pointers land" says
> where each surviving requirement went.
>
> **One operator, no other readers** *(operator, 2026-08-18)*. Readers become
> possible once the system proves itself enough to warrant exposing another
> person; until then the operator's judgment is the instrument, and unwritten
> by their decision (Rule 6). The phase order below is built for that
> condition, not around it.
>
> Phases are ordered by dependency, never by time. Time is not a constraint
> (operator, 2026-08-18). Evidence is labelled `S0-E` … `S7-E`; P2's `0-E` …
> `7-E` labels belong to the archive.

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

Measured state at the time this plan was written: 117 concerns (6 open, 19
closed, 84 stalled), 242 operator messages, 204 reading episodes, 88
deliberations, 359 ingest rows, 1 person, 0 outcomes the being did not grade
itself.

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

**E0.1 — the long-form path**
*Delivers:* the being composes a piece from what it already holds. A minimal
`works` row, a composer prompt, and nothing else — no surface, no revision, no
publication.
*Done when:* a piece exists in the store, composed on the same substrate as
everything else, retrievable by id, with no hand-editing anywhere in the path.
*Depends on:* nothing.

**E0.2 — three pieces from what it carries**
*Delivers:* three pieces on subjects the being already holds — open concerns,
held positions — chosen by it rather than assigned.
*Done when:* three pieces exist, each tracing to the concern or position it came
from, none framed or steered by the operator.
*Depends on:* E0.1.

**E0.3 — the read**
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

**E1.0 — undirected reading** *(added 2026-08-18; proposal:
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

## Phase 2 — the work, on a rhythm

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

**Evidence S2-E.** Pieces per week; revisions and retractions with their causes;
**at least one revision caused by something other than the operator saying so**
(Phase 1 makes this possible); and a re-read of S0-E's question against a body of
work rather than three pieces.

**Decision rule.** Produces on rhythm but never revises → the re-read is
decorative and past work is not reaching context; that is a retrieval defect, not
a writing one. Revises constantly → the writing has no conviction; check whether
Phase 4's commitments are the missing constraint before touching prompts.

---

## Phase 3 — the place

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

**Evidence S3-E.** The surface regenerates from empty and every page traces to
store rows. The reach switch flips in config with no code change. The store plus
generator restore on a second machine.

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

**This phase is not the next step after Phase 7.** It delivers no capability of
the being. It delivers the mechanism by which Phases 1–6 get delivered, so it is
ordered against nothing in that chain and **must not reorder it**. Phase 7 stays
dormant; the SEL does not wake it.

**Rule 4 is not relaxed.** No model verdict is a passing condition anywhere in
this phase. **Rule 6 is not amended** — the loop closes mechanical `Done when`
clauses; phase Evidence and every `Decision rule` stop at the operator, which is
where this plan already put judgment.

**Metric alignment is the first work, not a by-product.** The instrumentation
audit (proposal §15) found no registry, three probes hardcoding a dead absolute
path, one word carrying two quantities, and a premise set mixing mechanical and
model-graded numbers unlabelled. A loop steering on that would re-plan on drift
in the model's own judging and call it change in the world.

---

**E8.1 — the instruments made portable and enumerated** *(built 2026-08-19)*
*Delivers:* `tools/conversation_probe.py`, `tools/opener_probe.py` and
`tools/triage_probe.py` stop hardcoding `/Users/dean/Documents/source/NewZ` and
resolve the repo the way every other tool does; and `evolution/instruments.yaml`
enumerates every instrument with, per row: what it measures, the store or log it
reads, **whether a model touched any link in its chain**, its denominator, its
Rule 0 method line, and whether it is canonical.
*Done when:* no tool contains an absolute path outside the repo, a test asserts
it, and every instrument in `tools/` is either a row in `instruments.yaml` or
explicitly marked not-an-instrument.
*Depends on:* nothing.
*Hooks:* TRUE_NORTH §7 portability — a probe that runs on one machine is not an
instrument, it is a local habit. Rule 2, applied to instruments.

**E8.2 — every metric carries its grade**
*Delivers:* each metric in `instruments.yaml` is graded **mechanical /
model-graded / mixed / known-biased**, with the reason. Advance acceptance and
closure counts are model-graded (`judge_advance`, `judge_closure` — Rule 4 names
the first by name); pooled novelty is mixed (INV-023's read consults no model,
but `added`/`revised`/`carried` are labels the model applied at consolidation);
the grounding mix is mechanical and carries R-15's known bias.
*Done when:* every metric the loop can read has a grade, and the loop refuses to
cite an ungraded metric.
*Depends on:* E8.1.
*Hooks:* **Rule 4.** This is the row that makes Rule 4 checkable rather than
remembered.

**E8.3 — the metric-to-purpose map (Rule 2 for metrics)**
*Delivers:* every metric names what it is *for* — a precedence rung, a TRUE_NORTH
§10 item, a phase Evidence read, a `Decision rule`, or a kill condition — and
every one of those names the metrics that serve it.
*Done when:* no metric exists without a named consumer, and no rung, §10 item or
kill condition depends on a metric that does not exist. Both directions are
tested.
*Depends on:* E8.2.
*Hooks:* **Rule 2**, extended from tables and flags to measurements. A metric
nothing consumes is the same defect as a column nothing reads.

**E8.4 — the baseline-and-delta layer**
*Delivers:* one windowed comparison layer used by every metric — value,
baseline, window, delta — replacing per-tool ad-hoc comparison. `INCOMPLETE`
when the window has gaps; `UNREADABLE` when the input is missing.
*Done when:* every canonical metric reports through it, and a gapped or missing
window is reported as such rather than as a number.
*Depends on:* E8.3.
*Hooks:* **INV-044**, generalised. Today the project's deltas exist only in
prose — *"acceptance rose 28.3% → 41.1% where P2 expected a fall"* was computed
by hand, once, inside an argument, and a loop cannot steer on that.

**E8.5 — metric revision without silent breakage**
*Delivers:* every metric carries a `definition_version`. Changing a definition
**resets its baseline and records the reset with its reason**; the prior series
is retained and marked as belonging to the older definition.
*Done when:* a definition change is visible in the record, no delta is ever
computed across a definition boundary, and a test asserts both.
*Depends on:* E8.4.
*Hooks:* the "novelty" collision (proposal §15.3) is what this prevents in
future — one word carried two quantities and nothing in the system objected.

**E8.6 — the Tier 1 set complete**
*Delivers:* the six mechanical metrics the loop may steer by: nights slept and
the interval between them; grounding mix with INV-033's single-source flag;
claims made, claims resolved, and **positions changed by a resolution**; feeds
contributing a read and `source_gaps`; the compute split by function, being
versus loop; and the loop's own harm record — restarts, reverts, downtime,
nights lost.
*Done when:* all six report through E8.4 with a baseline, and each is graded
mechanical.
*Depends on:* E8.4.
*Hooks:* the third is **S1-E's reader**, which does not exist today — `claims.py`
renders claims and their costs and computes no rate, no latency and no count of
positions changed, so the plan's own gating read currently has nothing to read it
with. The sixth is §13.3.2's kill conditions.

**E8.7 — the derivation layer**
*Delivers:* metrics composed from Tier 1 and what exists — volume-to-development
(episodes per item added or revised), restatement rate (`1 − novelty`),
consequence rate (advances accepted against claims resolved), autonomy against
world-grounded position.
*Done when:* four of TRUE_NORTH §10's six checkable items are readable, each
through E8.4.
*Depends on:* E8.6.
*Hooks:* §10. These are ratios of data already collected; the shortfall was never
collection.

**E8.8 — operator agreement, informing only**
*Delivers:* the one §10 item with no raw material — a measured agreement or
disagreement signal in the operator exchange.
*Done when:* the signal exists, is graded **model-graded**, and the loop is
tested to refuse it as justification for a plan change while accepting it as a
rung 2 halt.
*Depends on:* E8.2, E8.6.
*Hooks:* §10, and proposal §15.4's rule. It is the item most likely to move under
a loop optimising for a quiet week, which is exactly why it may never justify
anything.

**E8.9 — the canonical freeze**
*Delivers:* the instrument set is frozen into the hard core; changing any
instrument is an operator act.
*Done when:* the gate refuses a diff touching a canonical instrument, and a test
asserts the refusal.
*Depends on:* E8.1, E8.3.
*Hooks:* the loop steers by evidence the being produces while changing the being;
at n=1 it cannot separate improving the being from improving the instrument's
view of it, and it has a gradient toward the second.

**E8.10 — `epics.yaml` and its drift check**
*Delivers:* this plan's epics hand-derived into machine-readable form — id,
depends-on, `Done when` and its class (mechanical / in-life / operator-judgment),
bound risks and invariants, falsifier — plus a check that every row still matches
PLAN's text.
*Done when:* the loop reads the queue from `epics.yaml`, and the drift check
fails the build when a row and PLAN disagree.
*Depends on:* nothing.
*Hooks:* the extraction is **hand-derived**, because deriving it automatically
loses what "the line this epic must not cross" is doing in E1.0.

**E8.11 — `premises.yaml`, the plan's staleness instrument**
*Delivers:* this plan's stated premises extracted with their instrument, their
grade and the argument each carries; re-measured every cycle; drift reported
whether or not anything is proposed.
*Done when:* a materially moved premise flags the argument resting on it, and a
plan-change proposal that cites no moved **mechanical** premise is refused.
*Depends on:* E8.2, E8.4.
*Hooks:* *0 outcomes the being did not grade itself* is the premise Phase 1
exists for, and E1.4 began falsifying it on 2026-08-19. Nothing noticed.

**E8.12 — the runner, the commit discipline, and the continuity assertion**
*Delivers:* a repo-local runner in the hard core; expand-contract migrations;
`Schema:` / `Restart:` / `Class:` / `Semantics:` commit trailers;
`LAST_KNOWN_GOOD`; a pre-restart snapshot named for the sha; and a mechanical
post-restart continuity assertion.
*Done when:* a deliberately bad commit is restarted into, fails its assertion,
and is reverted to `LAST_KNOWN_GOOD` without the operator present.
*Depends on:* nothing.
*Hooks:* continuity has been verified once, by hand, 2026-08-11. A loop that
restarts weekly crosses that boundary weekly.

**E8.13 — the Watcher, the report and the prepared session**
*Delivers:* the daily state read, the weekly report — unauthored numbers first,
the loop's reasoning last and marked unverified, rejected alternatives included,
and a decision queue — and judgment escalating into a *prepared* session rather
than an email and a wait.
*Done when:* a week runs unattended and its report is one the operator reads to
the end.
*Depends on:* E8.4, E8.6.
*Hooks:* Rule 6. The operator is in the loop at four points — plan changes, phase
Evidence and `Decision rule`s, Class B approval, the brake — and nowhere else.

**E8.14 — the builder, Class A only**
*Delivers:* autonomous build and restart for changes the test suite can judge,
under the mechanical gate, with **every new test required to fail against the
parent commit**, and the kill conditions live before the first autonomous
restart.
*Done when:* a Class A change is built, gated, restarted into and verified with
no operator action, and a tautological test is demonstrated to fail the gate.
*Depends on:* E8.9, E8.10, E8.12, E8.13.
*Hooks:* **Rule 4 in the build path** — a test written by the agent that wrote the
code, in the same context, is not independent verification.

**Evidence S8-E.** Not the loop's output. **Whether the being was harmed and
whether the reads were worth reading**: nights slept against the pre-loop
baseline; reverted restarts as a share of restarts; the loop's inference spend
against the being's; and the operator's own read of whether a prepared session
was worth opening.

**No velocity measure belongs here.** Commits, epics per week and cycle time are
counted in the report and are never targets — a loop measured on throughput will
produce throughput, which is §10's "activity, memory growth, or output volume"
wearing a scheduler.

**Decision rule.** Any kill condition firing stops the loop: reverted restarts
above 1 in 5 over a month; loop spend exceeding the being's; nights slept falling
below the pre-loop baseline; two consecutive quarterly re-reads finding this plan
drifted from TRUE_NORTH; or a plan-change proposal twice unable to name a moved
mechanical premise. **Nights slept is the one that matters most** — development
is measured in nights, not commits, and a loop that costs sleep is subtracting.

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
2. **Run the R-22 probe, or not?** *(open, not a governance question)*
   Structured deliberation versus deliberation-lite on matched concerns,
   bounded sample, end date recorded. It does not decide which plan governs —
   that is settled — but the question it answers is live and this plan does not
   refute it: **with a fixed model, structure may be the only lever on depth.**
   Phase 5 collapses deliberation to one mode with depth set by what is at
   stake, and the probe is what would tell us how to set it. Cheap, optional,
   specified in `archive/P2.md` §Phase 3.

3. **Does read-and-report gate building?** Whether Phase 8 runs E8.13 alone for
   a stated period before E8.14 is enabled, so the loop's judgment is observed
   before it is trusted. *Recommended: yes, four weeks.*
4. **May the loop propose outside this plan from the start?** Rung 5a of the
   proposal's precedence — a proposal costs an email, and a stale plan is the
   risk nothing else in the design detects. *Recommended: yes, as proposals
   only.*
5. **Does the being's own account of its condition feed the loop?** Its
   `noticings`, `source_gaps`, journal and affect state reach nothing that
   changes its conditions today. Admitted as **candidate signal, never
   evidence** (proposal §13.4), or not admitted. *Open — a judgment about
   §5 Priority 2, not a technical question.*

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
| P3-11 | The SEL proposes the frame its own work is judged in — not grading itself, but authoring the rubric | **High** | Phase 8: a plan change may cite only a moved **mechanical** premise (E8.11); TRUE_NORTH immutable by the loop; rejected alternatives reported; a quarterly re-read from outside the loop's history |
| P3-12 | The loop steers on model-graded numbers and mistakes drift in the model's judging for change in the world | **High** | E8.2's grades, and the refusal to cite an ungraded metric |
| P3-13 | The loop restarts the being into code that does not come up, and is the only thing that would notice | **High** | E8.12's runner, `LAST_KNOWN_GOOD` and continuity assertion, plus an out-of-band heartbeat the loop does not send |
| P3-14 | The loop writes both the code and the tests that certify it — Rule 4 relocated into the build path | Medium | E8.14: every new test must fail against the parent commit. Mutation testing deferred and recorded as unsolved |
| P3-15 | The loop is ~50–100× slower at architecture than the operator, so it buys attention and not speed | Inherent | Accepted. Phase 8 escalates judgment into a prepared session rather than replacing the operator |

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
