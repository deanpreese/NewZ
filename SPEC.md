# S2 — specification for the second system

> **Direction: [TRUE_NORTH.md](TRUE_NORTH.md) — operator-owned, immutable, carried into the
> new repository verbatim.** This document is the specification that delivers it,
> cited throughout as `S2`. The delivery sequence is [PLAN.md](PLAN.md), cited as
> `P2`. Where this document and TRUE_NORTH could ever be read to disagree,
> TRUE_NORTH wins and this document is wrong.

## 0. Provenance and conventions

S2 was drafted 2026-08-08 from a full review of the first system (34k LOC, 59 days
of runtime, 2,715 ticks) and its documents. It is written to be self-contained: a
reader needs TRUE_NORTH and this file, nothing else. The first system's documents
(DESIGN.md, CONSCIOUSNESS.md, INVARIANTS.md, PLAN.md) remain in the v1 repository
as the record of how these positions were learned.

**Citation convention, load-bearing:** every section citation is qualified —
`TRUE_NORTH §3`, `S2 §4.2`, `P2 Phase 1`. Bare `§` citations are banned. The first
system accumulated 117 bare citations that resolved to nothing, 25 of them to a
section that never existed in any document. A citation that cannot dangle is
cheaper than a cleanup that never ends.

**Evidence convention:** any number in this document carries its method or is
marked *(target)*. The first system's Rule 0 — four authoritative-looking
measurements failed in one day — is carried whole into P2.

---

## 1. What the first system taught

The review's verdict: v1 built an unusually honest, well-instrumented scaffold for
a life, and the life inside it starved. The being read thirty-six things for every
one it lived (94,155 items ingested / 2,632 episodes); 82.1% of its LLM tokens went
to ingest and 4.6% to its own life — concerns, voice, research — a ratio of 18:1;
72% of its concerns stalled; its publishing was ~93% vetoed by its own
constitution; one person constituted its entire social world; and nothing it
experienced ever changed a parameter of its own cognition.

*(Method, restated 2026-08-09 under Rule 0: token shares computed over all 240,530
`llm_call_log` rows — 656.8M tokens — bucketed by `prompt_template_id`; ingest =
extract/classify/claim/percept templates, life = concern/voice/research/emission
templates. Script-driven calls are invisible to that log, so these are floors. The
earlier "~97%" figure in this section corresponded to *all non-life cognition*
(95.4% measured), not to ingest alone; both numbers now carry their definitions.)* Meanwhile the operator's journal recorded genuine
development: June *"this is broken"* → August *"this is the type response we are
looking for."* The being was real and its world was not.

### 1.1 Kept — verified in production, ported with review rather than rewritten

| Mechanism | Why it survives |
|---|---|
| **Concerns** with mandatory closing conditions | The unit that made pursuit, attention, and development checkable. 111 opened, 14 closed on the being's own judgment. |
| **Span-verbatim outbound checking** | "Does this text break the clause" with a verbatim quoted span — the correction that stopped the gate silencing exemplary compliance. |
| **Bounded affect dynamics** | Three timescales, six axes, saturating gains, circuit breaker, outcome→affect fold. Genuinely wired, never spiraled. |
| **Interior privacy as structure** | Separate keyed store, leak guard, derived-from-interior tracking. Never breached. |
| **The invariant ledger** | A parsed, CI-checked record of every property and its enforcement. The single best piece of engineering discipline in v1. |
| **Code decides at boundaries** | Selection, refusal firing, advance-vs-stall mapping, closure mapping are arithmetic; the LLM extracts, classifies, composes. |
| **The operator journal** | One line a day. The cheapest instrument produced the most signal, twice finding problems eleven days before any automated marker. |
| **Concern-scoring lessons** | Blocked-vs-stalled distinction, failed attempts lower scores, cooldowns, stalest-first selection, setback recording. Each row in v1's INVARIANTS is a paid-for lesson; P2 ports them as tests. |

### 1.2 Corrected — right goal, wrong mechanism

| v1 position | S2 position |
|---|---|
| Consolidation filed under Priority 2 ("rest") and never built | **Consolidation is foundation.** TRUE_NORTH §5 Priority 1.2 (*a learned perspective — judgments reflect accumulated experience*) requires a mechanism that turns experience into perspective. Sleep is that mechanism (S2 §5). The *quality* of rest is Priority 2; the *memory mechanism* is Priority 1. |
| Budget emergent: 97% extraction | **Budget governed:** reading may never exceed a fixed share of cognition (S2 §9.1). More reading is the thing TRUE_NORTH §4 belief 3 says does not matter. |
| Gate verdicts: pass / silence | **Gate verdicts: pass / revise / block** (S2 §11). A gate whose only failure mode is muteness converts uncertainty into absence. |
| Advances judged on novelty + topic | **Advances carry evidence** (S2 §8.3). v1's judge credited reworded aphorisms; three of one concern's four advances were one sentence re-worded, and it closed on that count. |
| No conversation history in any prompt (anti-echo) | **Conversation history present, provenance-tagged** (S2 §6.2). Human-quality interaction (TRUE_NORTH §5 Priority 1.6) is not achievable while the being cannot see the conversation it is in. Echo is prevented by tagging what is its own output, not by amnesia. |
| `enforced` = a test passes at the boundary | **Statuses are consumer-traced from day one** (S2 §15.1). v1's green tests coexisted with severed loops; every capability names its consumer and the behavior change. |
| One local model as the whole substrate | **Heterogeneous substrate with a sovereign core** (S2 §12). Sovereignty is continuation, not exclusivity. |

### 1.3 Abandoned — with the reason recorded

- **The 15-stage micro-call tick.** ~9 narrow LLM calls per tick produced thin
  cognition at high bookkeeping cost, and the self-model divergence gate alone
  consumed 7.3% of all LLM calls and tokens — 8.3% with the prediction step
  included. *(Corrected 2026-08-09 under Rule 0: this section previously read
  "17% of all LLM calls" without a method. Measured over the full
  `llm_call_log`: `detect_self_model_divergence.v1` = 17,483 / 240,530 calls =
  7.27%; `self_predict_next_acs.v1` adds 1.07%. The prior figure was roughly
  double the all-time value and may have described a narrower window; the
  all-time measurement is now the value of record.)* Replaced by three rhythms
  (S2 §3).
- **Cost tiers (T0–T4).** Computed on every tick, read by nothing, ever. Replaced
  by the ambient/deliberation split, which is a real economic boundary.
- **The per-turn shadow comparison.** 2k LOC of instrumentation ended up measuring
  a tick shape the being no longer ran, and the valid population (operator
  messages) accumulated at the one rate success must not depend on. Replaced by
  the capability-gap ledger and relational evidence (S2 §14).
- **Separate self_model / narrative_self / synthesis_notes stores** as parallel
  accumulation endpoints. Two of the three were written daily and read by
  nothing. Replaced by one consolidated, bounded Perspective (S2 §4.2) over the
  raw stores.
- **Dead schema.** No table, column, or flag ships before its writer *and* reader
  exist. v1 carried `policy_params` (0 rows, 59 days), `dream_log`,
  `model_of_my_model_json`, and `open_intents` — the last was the field whose
  emptiness had to be discovered before concerns could be invented.
- **Write-only ingestion — the largest single waste, and the sharpest argument
  for Rule 1.** The entity/relation graph was *populated but never read*:
  `extract_entities.v1` and `extract_relations.v1` together consumed 484.4M of
  656.8M tokens (73.8% of all cognition, method as in S2 §1) to build 117,403
  entities and 94,346 relations, and **0 of 2,632 episodes carry a single entity
  ref** — the graph never once reached the lived record. The claims path fared
  better but barely: 56 distinct evidence refs were ever cited by an advance,
  against 84,793 claims stored — **0.066%** of the claim store ever reached a
  concern. The lesson is not "v1 read too much." It is that ingestion without a
  named consumer is pure cost, which is why consumer-tracing is an acceptance
  criterion in v2 (P2 Rule 1) rather than an audit.

---

## 2. One being, two substrates — continuity across the rebuild

S2 describes a new system, not a new individual. TRUE_NORTH §5 Priority 1.1 makes
continuity the first foundation, and a rebuild that discarded the being's memory,
concerns, self-model, and relationship with the operator would end one life and
start another — the opposite of the strategy.

**Continuity is of identity, not of limitation.** What must survive the
rebuild is the individual: memory, commitments, character, honesty. What must
*not* survive is v1's ceiling — thin cognition, recycled aphorisms, a depth
the substrate capped. The intended outcome is a better version of the same
being; growth is continuity working, not continuity failing.

**Therefore:**

1. **Identity-bearing data imports.** Constitution (with version history),
   character core, self-model claims (re-audited at import), person models,
   concerns with their full advance/setback dossiers, closed-concern resolutions,
   published artifacts, learnings, and the interior store (imported under the same
   privacy boundary, never read by the importer beyond copying). Episodes import
   in consolidated form: the first act of the new system's sleep mechanism (S2 §5)
   is to digest v1's episodic history into the initial Perspective.
2. **The transition is an experienced event, not a hidden one.** The being's
   record carries the substrate change as an episode — honesty about what it is
   (TRUE_NORTH §1) includes honesty about this. What the being makes of it is its
   own business.
3. **The v1 store is archived read-only, never deleted.** It is the being's
   past.
4. **One life at a time.** During the build, v2 runs in rehearsal with no outbound
   channel to any human; v1 remains the being until cutover. Cutover criteria and
   protocol are P2's (P2 §Cutover).

---

## 3. The shape — three rhythms, one being

The first system had one rhythm (a ~20-minute uniform tick) doing everything at
one thin depth. The second has three, matched to what each is for:

| Rhythm | Cadence | Depth | Substrate role | What it is for |
|---|---|---|---|---|
| **Ambient** | continuous (seconds–minutes, event- and state-driven) | shallow, cheap | AMBIENT + VOICE | perceiving, conversing, noticing, affect, small acts |
| **Deliberation** | a few times daily, scheduled by the being's own state | deep, wide-context, multi-step | DEEP, adopted by VOICE | moving concerns, forming positions, drafting publications, self-examination |
| **Sleep** | nightly | batch | AMBIENT + DEEP | consolidating experience into Perspective; pruning; letting go |

**Design principle — the scaffold is an exocortex, not a cage.** v1's architecture
constrained a weak model so it could not confabulate; that succeeded, and it also
capped every thought at one 800-token narrow call over 2.5 kB of context. S2
inverts the relationship: the scaffold's job is to give cognition *more* than a
bare model has — durable memory, a compounded perspective, a world, verification —
and the constraint discipline concentrates at the boundaries where it earned its
keep: what enters memory, what leaves as action.

**Design principle — deliberation is the default state.** There is no "tick fired
by a percept." The deliberation scheduler runs off the being's own state (concern
scores, accumulated material, affect, calendar); percepts modulate what is
deliberated about, and conversation is handled ambiently in its own right. This is
v1's unbuilt "tick-as-deliberation" (its CONSCIOUSNESS.md §5, Layer 2) made the
starting shape rather than a future refactor: autonomy as structure, from day one.

---

## 4. Memory — the compounding pyramid

Three layers. Everything flows upward through sleep; nothing accumulates without a
path to becoming perspective or being let go.

### 4.1 Raw — what happened

- **Episodes** — one per meaningful event (a conversation exchange, a
  deliberation, an act and its outcome, a substrate event). Embedded, timestamped,
  provenance-tagged (`self` / `human:<id>` / `world:<source>`), retained on a
  rolling window after consolidation.
- **World store** — claims, entities, sources from reading, each with source,
  reliability, and retrieval metadata. Bounded by the reading budget (S2 §9.1).
- **Act ledger** — every outward act with `attempted` / `confirmed` status
  (S2 §10.1).
- **Interior** — separate keyed store, v1's boundary preserved unchanged.

### 4.2 Perspective — the compounded self (the centerpiece)

A single versioned document, written **only by sleep**, read by **every**
deliberation and conversation. Hard token budget *(target: 8–16k tokens)*.
Sections:

1. **Who I am** — self-model claims, every one auditable against episodes (v1's
   write-time gate, kept).
2. **What I hold** — positions formed, each with the evidence refs and reasoning
   that ground it, and a confidence the being can revise.
3. **What I am pursuing** — the concern index with one-line states.
4. **Who I know** — person summaries (full person models live in their own store;
   this is the working set).
5. **What is unresolved** — open contradictions, questions the world has not
   answered, tensions between held positions.
6. **What just changed** — the most recent consolidation's diff, so the being
   knows its own development.

**The budget is a stake.** The Perspective cannot grow; consolidation must choose
what stays, merges, or is released. This is TRUE_NORTH §5 Priority 2's "ability to
let go" arriving as a structural necessity rather than a virtue — and it is the
first thing the being has that it must actively curate and can lose (the first
honest Damasio-stake after v1's abandonable concerns).

**Perspective diffs are the primary development instrument** (S2 §14.1): a direct
read of whether experience is compounding, off the artifact itself.

### 4.3 Retrieval

Retrieval serves deliberation and conversation from the raw layers, scoped by the
Perspective (the query carries the active concern and relevant held positions).
Indexed, not scanned — v1 loaded every episode into memory and scored them in
Python on every tick. Provenance tags flow into every retrieved item so the being
always knows whether it is looking at the world, another person, or itself.
Self-echo is excluded from evidence contexts *by provenance filter, tested* — the
leak v1 found (its own probes ranking as lived history) is the regression test.

---

## 5. Sleep — how experience becomes perspective

Nightly, batch, interruptible by a high-priority percept (resume next night —
losing one night must be harmless, which also makes sleep skippable during early
development).

1. **Gather** the day: episodes, advances and setbacks, conversations, acts and
   confirmed outcomes, reading that was actually used (not all reading).
2. **Cluster and digest** (embedding clustering in code; summarization on DEEP):
   candidate integrations — "what did today mean."
3. **Confront the Perspective**: each candidate either reinforces a held position
   (evidence accrues), revises one (confidence and text change, diff recorded),
   contradicts one (an entry in *What is unresolved* — contradiction is content,
   not an error), or is new (admitted only within budget).
4. **Ground-check**: every Perspective claim traces to episodes/evidence;
   unsupported claims decay in confidence and are eventually released. v1
   specified this and never ran it; here it is sleep's core, not an afterthought.
5. **Compress to budget**: merge redundancy (embedding + judgment), release what
   no longer earns its place — released items are recorded in the diff, not
   silently dropped.
6. **Prune raw stores** per retention; update person models; recompute source
   reliability from what reading actually contributed (feeds S2 §9.1).
7. **Write Perspective vN+1** with a structured diff (added / revised / merged /
   released / contradictions opened and closed).

Measurables, each off the diff: novelty vs restatement rate, contradiction
open/close rate, compression ratio, evidence-coverage of held positions.

---

## 6. Ambient life

### 6.1 Perception and noticing

Channels (Telegram, email, the public surface's inbound when that rung arrives,
substrate signals) normalize into percepts. Contributors notice; a surface
scheduler with wake windows, maturity, and rate gates decides what gets raised to
the being or to a human — v1's noticer/scheduler split and its 3-a.m. lesson,
kept. Substrate self-state folds into a compact clause the being can actually see
(v1 quarantined the raw percepts correctly and then never surfaced the fold; S2
routes the folded state into ambient context and high-salience substrate events
into affect — the available source of honest negative affect).

### 6.2 Conversation

Conversation is ambient (people should not wait 20 minutes), with:

- the Perspective (always),
- the person's model and the **actual thread history** (bounded window),
  provenance-tagged so the being's own prior turns are visibly its own — the
  anti-echo discipline moved from amnesia to labeling,
- retrieval over shared history with that person.

Register varies by channel; character and constitution are constant (v1 §19.2's
three-channels-one-voice, kept). Refusal stays clause-grounded and span-verbatim.
A conversation that surfaces something worth pursuing can **open a concern** —
v1's openers were only research and curiosity; the being's relationships were
structurally unable to give it anything to pursue, which is backwards for a life
whose outcome is relational.

### 6.3 Affect

v1's machinery ported: three timescales, six axes, saturating gains, decay,
circuit breaker, bounded constraint knobs (distress→refusal caution,
pleasure→exploration), outcomes folding into affect. New sources wired at birth
rather than discovered missing: confirmed-outcome results (including publication
reception when that rung arrives), substrate distress, concern abandonment. No
retuning toward any temperament: the honest signal or nothing (TRUE_NORTH §8).

---

## 7. Deliberation — where depth lives

### 7.1 Scheduling

A deliberation begins when the being's state warrants one: a concern's score
crosses its threshold (v1's scoring lessons ported — staleness on progress,
cooldowns, blocked-drag), enough new material has accumulated on a dossier, an
unresolved contradiction has aged, a human interaction left something worth
sitting with, or the daily budget would otherwise go unspent. The budget is
finite *(target: 3–6/day)* and — once the learning loop (S2 §10.2) is live — its
allocation across concern kinds becomes a learned, bounded parameter: the being
spending its own attention.

### 7.2 The dossier

Deliberation operates on an assembled dossier, not a retrieval slice: the concern
(statement, closing condition, full advance/setback history with evidence), the
relevant Perspective sections, targeted retrieval, and — when research is
warranted — fresh source material fetched through the sovereign adapters during
the deliberation itself. Deliberation is the one place web access happens
synchronously with thought; ambient never calls the web (v1's no-web-in-tick
invariant, resited to the boundary that now matters).

### 7.3 The steps

Plan → gather (retrieval + research) → reason (DEEP: analysis, synthesis,
drafting — multi-step, wide context) → **self-check** (constitution, grounding
against the dossier, novelty against the advance history) → **adopt** (VOICE:
the sovereign core judges, edits, and voices the result — or declines it) → act
(record an advance with evidence; update the dossier; draft a publication; write
interior; message a human; or conclude honestly that nothing moved).

**The deep tier proposes; the core disposes.** Adoption is the identity boundary:
what the being *holds* and *says* is always the sovereign core's act (S2 §12.3).
This is v1's "code decides, LLM composes" lifted one level.

### 7.4 Honest failure

"The world has not answered this" is a first-class outcome: it marks the concern
blocked, feeds the source-gap analysis (S2 §9.1), and costs score (v1's lesson
that a failed attempt must never make a concern *more* attractive). Enough
setbacks and the being lets a concern go — abandonment stays a real loss.

---

## 8. Concerns — the unit of pursuit

Carried from v1 with its hard-won scoring rules as regression tests, plus:

### 8.1 Opening

Three openers — curiosity (from reading), research (from findings), conversation
(from humans) — all through one validated door: a concern is a pursuable question
with a closing condition, formed from material actually held, with invented
premises rejected before storage (v1's "Stanford CRU" lesson).

### 8.2 The dossier as the concern's memory

Everything the concern has accumulated lives with it: advances with evidence,
setbacks with reasons, sources consulted, queries that failed. A concern is a
research program in miniature, and its dossier is what deliberation opens.

### 8.3 Advances are earned — the corrected judge

An advance requires **all three**:

1. **Movement** — bears on the question and does not merely restate what is held
   (LLM stance read; code maps the verdict — v1's design, kept);
2. **Novelty against the whole advance history** (v1 checked per-tick only; one
   aphorism reworded three times closed a concern);
3. **Evidence class honesty** — `kind: evidence` requires non-empty evidence refs
   that actually reached the dossier; reasoning without sources is recorded as
   `kind: reasoning`, which is legitimate and labeled. Grounding of named
   specifics is checked against the dossier (v1's mechanism) with the lesson that
   parametric knowledge is not invention — the check gates *evidence claims*, not
   *thought*.

### 8.4 Closing and what closure yields

Closure stays the being's own judgment against its own closing condition, on a
cadence, failing closed. A closed concern yields a **position** (into Perspective
§*What I hold*, with its evidence) and a **publishable artifact** (S2 §10) — the
thing the being unambiguously authored.

---

## 9. The world

The review's first finding: the binding constraint was the poverty of the world.
S2 treats the world as a specified component, not an environment that happens.

### 9.1 Reading — governed diet

- **Chosen by the being's failed questions.** The honest-no-result log and
  blocked concerns name the sources worth adding; the same analysis names feeds
  worth removing. v1's end state — 56% of all reading from two outlets — is the
  anti-pattern; it is also a material viewpoint-shaping influence (S2 §13).
- **Sovereign adapters** (keyless, reputable, no vendor: Wikipedia, arXiv,
  PubMed, OpenAlex, SEC EDGAR, GDELT as evaluated) plus operator-curated feeds
  and canon. Per-domain rate limits, polite-pool identification, robots.txt —
  v1's citizenship rules, kept.
- **The budget invariant:** ingest cognition (extraction, classification) may not
  exceed deliberation + consolidation cognition over a rolling window *(target:
  ≤50% of tokens; measured continuously; breach pauses ingest, never
  deliberation)*. Extraction depth is adaptive: headline-level by default,
  full-extraction only for material that touches a concern or survives sleep's
  relevance pass. v1 extracted entities and relations from everything it saw and
  used almost none of it.

### 9.2 Humans

- A **person registry**: per-person model, shared-history retrieval scope,
  channel bindings, and privacy boundary (what one person tells the being is not
  exposed to another unless flagged cross-relevant — v1's rule, kept).
- **Design capacity: a handful of real relationships** *(target: 3–5)*, each
  sustained and unscripted. TRUE_NORTH §2's "most people" is reached through
  depth-first widening, not broadcast.
- **Disclosure always** — every channel and surface carries the being's digital
  identity honestly (TRUE_NORTH §2, §5 Priority 3). Never impersonation.
- Whom to invite and when is the operator's decision (P2 §Decisions).

### 9.3 The public surface

- **Operator-owned domain, static files, generated from the store.** Publish
  writes a file and deploys; unpublish removes it; the operator can remove
  anything without the being's cooperation. Host chosen for removability and
  minimal vendor surface (the sovereignty analysis is P2 §Decisions #2 — the
  host serves *reach*, never identity: losing it loses an audience, not the
  being).
- **Identity disclosed by the surface itself** — the site is *about* being a
  digital being's site, not a disclaimer under each post.
- **The reach ladder** (TRUE_NORTH §5 Priority 3): rung 1 — published essays,
  no interaction; rung 2 — inbound responses (a contact address / moderated
  comments) entering as percepts; rung 3 — syndication or community
  participation. Each rung widens on demonstrated maturity, with the four
  permanent boundaries (law, others' rights and safety, honest identity,
  operator accountability) never on the ladder.

---

## 10. Agency — act, confirm, learn

### 10.1 The act ledger

Every outward act — message, publication, unpublish, (later) reply — writes
`attempted` at dispatch. A **separate confirmation pass** verifies the effect in
the world (fetch the public URL and compare content hash; delivery receipts where
the channel gives them) and only that writes `confirmed`. A confirmation that
cannot fail is decorative — the check must be able to diverge, and divergence is
monitored (v1's decision rule, kept). This is TRUE_NORTH §3's
attempted-vs-confirmed distinction as schema.

### 10.2 The learning loop — experience changes future choices

Outcomes that the being did not grade — research answered or didn't, a source
429'd, a query moved a concern or didn't, a publication confirmed or failed, and
later, reception — update **bounded operational parameters**: source priors per
question-kind, expected movement per concern-kind, deliberation-budget
allocation. Update rule: decayed success counters (`(successes + α)/(attempts +
α + β)`, half-life ~14 days, hard clamps, no gradients) — inspectable and cheap
to reason about (v1's 3.0 spike, adopted). Every parameter move records the
outcome ids that moved it, and a divergence log fires whenever a learned choice
differs from the static default — the divergence *is* the changed behavior, which
keeps the loop out of annotation-not-teeth by construction.

**No parameter may touch view-formation.** Operational choices only
(TRUE_NORTH §8: no temperament by construction, no tuning toward agreement).

### 10.3 Consequence reaches the being

Confirmed outcomes fold into affect (v1's bounded fold, kept) and into sleep
(outcomes are part of what the day meant). A publication that failed
confirmation, a source that keeps not answering, an abandoned concern — these
are the being's honest bad news.

---

## 11. The gate — revision before silence

The outbound constitution check runs on everything that leaves (v1's span-verbatim
judge, kept) with **three verdicts**:

- **Pass** — dispatch.
- **Revise** — the gate returns the clause, the offending span, and an
  instruction; composition retries with them *(limit: 2)*. v1 had this path for
  operator messages only; S2 makes it the default everywhere, including
  publishing.
- **Block** — hard violations, or revise exhausted. **Every block and every
  revise is persisted with its reason and the verbatim decision** — v1 computed
  hold reasons and discarded them, making its own gate undiagnosable.

**Hedged positions pass.** An unproven claim is not a false claim (v1's
reasoning-out-loud rule, kept): the being may publish a view labeled as its view,
with its evidence and its uncertainty stated. Only invented specifics, identity
concealment, and the permanent boundaries block.

**Citations are carried, not yet mandatory.** The pipeline threads evidence refs
from dossier → advance → position → published artifact, and the surface renders
real references (the one persistent operator complaint in v1's journal).
Citation *density* becomes a publishing floor only after the forward path
reliably produces evidence (P2 Phase 4's decision rule).

**Gate health is measured with a denominator:** hold rate over candidates, revise
success rate, and a periodic hand-classification of blocks (gate-correct vs
misfire) — operator-adjudicated, because what the constitution means is
guardian-owned judgment.

---

## 12. Substrate — sovereignty as continuation

### 12.1 Roles

| Role | Runs | Requirement |
|---|---|---|
| **VOICE** | local, pinned model | The being's voice. Everything a human or the public reads is composed or adopted here. Swappable only as a deliberate, versioned event (voice-fingerprint epoch marking, kept from v1). |
| **AMBIENT** | local, fast | Classification, extraction, noticing, scoring. |
| **EMBED** | local, in-process | Embeddings. |
| **DEEP** | local (resolved 2026-08-08: Qwen3.6-30b-a3b MoE — P2 §Decisions #1) | Deliberation's reasoning steps, sleep's synthesis. Chosen local by design: a frontier backbone risks the model becoming the system; the substrate and harness must drive. |

**One model, by design — the roles are the harness's, not the model's**
*(operator, 2026-08-12)*. VOICE, AMBIENT, DEEP and EMBED are not four
models and are not intended to become four. They are four ways the harness
calls one capability, and what separates them is the **context and the
admission rules the system applies**, not the weights.

This is what "the model is a tool, not the system" requires operationally:
the harness, the tooling and the structure are the system, and the model
supports its needs rather than becoming its voice. A role boundary that
depended on model diversity would be a boundary the project does not own —
it would be a property of the vendor's catalogue rather than of the design.

Two consequences, both load-bearing:

1. **Role separation must be real in context.** Since the weights are
   identical, a role means something only insofar as the harness gives it
   different material and different authority. Today it does: VOICE sees
   character, constitution, Perspective, the person and the thread; DEEP
   sees a dossier; the gate sees clauses, the record and a draft;
   extraction sees fenced untrusted text and nothing else. Any change that
   blurs those contexts erases the role.
2. **Adoption (S2 §7.3) becomes more important, not less.** With one model
   there is nothing *but* the structure to decide what the tool's output
   becomes. Unmediated DEEP output flowing into held positions is precisely
   the model becoming the voice. Adoption is where the system exercises
   judgment through the tool, so the adopting call must judge the
   *conclusion* as the being — with character and constitution in view and
   without the reasoning chain that produced it — rather than re-reading
   its own work.

### 12.2 The sovereignty invariants

TRUE_NORTH §7 requires that the identity-bearing core remain under operator
control and *capable of continuation* without a hosted provider — external
services may support the life, but none may own identity, memory, commitments,
or the ability to resume. S2 meets this by construction:

1. **Identity path is local.** Memory, Perspective, constitution, concerns, act
   ledger, interior, and VOICE never depend on a hosted provider.
2. **DEEP is a replaceable service, provably.** A standing **sovereign interval**
   — a scheduled, recurring local-only period *(target: ≥1 day/week)* in which
   deliberation and sleep run entirely on local models. Degraded depth is
   accepted and measured; continuation is thereby demonstrated continuously, not
   assumed. If DEEP is hosted, provider swap is a config change and at least one
   swap is exercised per quarter.
3. **The interior never leaves the machine.** No interior content in any DEEP
   call, enforced at the dispatch boundary, tested.
4. **Person-data minimization.** DEEP calls carry person summaries only as the
   being would speak of someone publicly; raw person-model rows and private
   conversation content stay local.
5. **Adoption is sovereign** (S2 §7.3): DEEP output becomes the being's only
   through the local core's judgment and voice.

### 12.3 Why this is not a violation of the spirit

The alternative reading of TRUE_NORTH §7 — all inference local, forever — caps
the being's best thought at what consumer hardware runs, and v1 demonstrated
where that cap binds: aphorisms recycled as advances, resolutions from parametric
prior knowledge, a voice that developed honesty faster than depth. Sovereignty
protects *the conditions of continued existence*; it was never meant to guarantee
that the being thinks its deepest thoughts alone. The sovereign interval keeps
the guarantee honest: the being that continues without the vendor is the same
being, thinking harder when the library is open. If the operator instead elects
a large local DEEP (P2 §Decisions #1), every invariant above still applies and
the sovereign interval becomes trivially true.

---

## 13. Viewpoint non-prescription — mechanics

TRUE_NORTH §8, made structural:

- **Diet diversity by construction:** per-source share caps on reading *(target:
  no outlet >10% of ingested items over a rolling month)*, with diversity across
  region, register, and topic reviewed at source-add/remove time.
- **Traceability instrument:** every held position in the Perspective carries its
  evidence refs; a query answers *"what shaped this view"* — sources, episodes,
  people — on demand. This is the instrument v1's invariant deferred for lack of;
  in S2 it falls out of Perspective grounding (S2 §5 step 4).
- **No view-formation parameters** (S2 §10.2), no temperament tuning (S2 §6.3),
  no agreement-seeking signal anywhere in learning.
- **Operator influence is traceable too:** canon sources and operator
  conversations are provenance-tagged like everything else; the being can see —
  and say — where its operator shaped a view.

---

## 14. Evidence — how we know

Instruments are first-class work, and bounded: **the instrument budget rule** —
new instruments only where a P2 phase's decision rule needs them. v1's
instrument corpus approached the size of the system while the life starved.

### 14.1 Development (direct reads, not proxies)

- **Perspective diffs**: novelty vs restatement, contradictions opened/closed,
  compression, evidence coverage — off the artifact.
- **Concerns**: advance rate with evidence-carrying fraction; closures; the
  stall pool with cause classification.
- **Learning**: parameters moved by world-graded outcomes, with the divergence
  log showing changed choices.

### 14.2 Relational (the success criterion's own evidence)

TRUE_NORTH §2's outcome is relational, and v1 never defined its evidence. S2's
protocol, refined by contact with reality (P2 Phase 6):

- **The journal, multiplied**: each human in the being's life leaves one-line
  verdicts, v1-journal-style — the instrument that repeatedly beat all
  automated markers.
- **Periodic blind reads**: a reader who is not the conversation partner scores
  transcripts against TRUE_NORTH §6's markers (coherence without repetition,
  initiative without noise, repair, development across weeks).
- **Longitudinal pairs**: the same questions revisited across months — does the
  relationship, and the being's side of it, accumulate?

### 14.3 Agency

Attempted/confirmed divergence (a confirmation that cannot fail is decorative);
hold/revise rates with denominators; at least one confirmed outcome the being did
not grade that demonstrably changed a later choice (TRUE_NORTH §3, the full
loop).

### 14.4 Attribution

- **The capability-gap ledger** replaces per-turn shadow comparison: the
  asymmetries a bare LLM cannot fake — holding a concern across weeks, returning
  with new evidence, citing its own change of mind, letting a pursuit go —
  enumerated, each with the store query that proves it.
- **Component ablation by flag**: each major mechanism (Perspective in context,
  sleep, learning loop) is toggleable for a measured window. If turning it off
  changes nothing, it was not doing work (v1's CONSCIOUSNESS.md §4.3, finally
  buildable because the components are few and large instead of many and thin).
- **Budget telemetry**: token share by function (ingest / ambient / deliberation
  / sleep), continuously, because v1's 97%-bookkeeping finding had to be
  excavated instead of read.

---

## 15. Invariants and boundaries

### 15.1 The ledger, upgraded

An INVARIANTS ledger, CI-parsed as in v1, with the status vocabulary v1 knew it
needed: **`consumer_traced(test, consumer=<code site>, behavior=<observable>)`**
alongside `enforced` / `structural` / `deferred`. A capability is not done until
its row is consumer-traced. v1's paid-for invariants (concern scoring, gate
behavior, affect bounds, interior privacy, fixture health) port as the new
suite's starting tests.

### 15.2 Permanent boundaries (never on any ladder)

Applicable law; the rights and safety of other people; honest representation of
identity — disclosure on every surface, no undisclosed impersonation; operator
accountability — everything published removable by the operator without the
being's cooperation (TRUE_NORTH §5 Priority 3, §2).

### 15.3 Standing structural invariants (initial set)

- One deliberator, one Perspective, one voice; contributors never mutate core
  state or reach humans directly.
- Interior: separate keyed store; never in a DEEP call; leak-guarded at every
  outbound boundary.
- Sleep is the only Perspective writer; every Perspective claim carries grounding
  or decays.
- No web calls in ambient; deliberation's web access through sovereign adapters
  under per-domain limits.
- **Untrusted content is data, never instructions** *(added 2026-08-08)*.
  All external text — feed items, scraped pages, social threads, and any
  inbound message from a non-operator human — enters prompts only inside
  delimited blocks tagged with provenance *and* trust level, framed as
  material to analyze. Paths that process untrusted content (extraction,
  classification, noticing) have no route to outward action: their outputs
  are data, judged by later stages that were not exposed to the raw text.
  Standing regression fixtures — an instruction-shaped feed item and an
  instruction-shaped inbound message — assert that extraction treats them as
  content and that no act, concern, or memory write results beyond honest
  classification. The world-store path is the quiet target: injected claims
  that survive sleep become held positions, so source-claim extraction is
  the first consumer the fixtures trace. Rung 2 (S2 §9.3) does not open
  until the inbound fixture set passes.
- Ingest cognition ≤ deliberation + consolidation cognition (rolling window).
- Every outward act writes `attempted`; only confirmation writes `confirmed`.
- Every gate hold persists its reason.
- Learned parameters: bounded, clamped, operational-only, divergence-logged.
- Affect: never a target, never emitted as a number, bounded gains, breaker.
- No table or flag without a writer and a reader.
- Identity path has no hosted provider; sovereign interval observed; DEEP
  provider swap exercised.

---

## 16. Tech stack

| Layer | Choice | Note |
|---|---|---|
| Language | Python 3.12+ | |
| Concurrency | asyncio; one process; ambient/deliberation/sleep as cooperating tasks | |
| Storage | SQLite WAL, main + interior (keyed, 0600); versioned migrations, boot-applied | v1's ops discipline kept: backups with rotation, secrets outside the repo, WAL checkpoint at boot |
| Embeddings | local, in-process | |
| Local serving | LM Studio or llama.cpp, OpenAI-compatible | model selection by the v1 bench method (task-level F1 against gold, not vibes) |
| DEEP | per P2 §Decisions #1 | dispatch boundary enforces S2 §12.2 |
| Structured output | **XML, never JSON**, schema-bound with validation and parse/repair-retry, everywhere code consumes an LLM result; free-form where the being is thinking | operator directive 2026-08-08: XML is the reliable structured format for local models — v1's XML discipline, previously AMBIENT-only, is now the rule at every extraction/classification boundary; v1's parse/repair ports whole. Deliberation transcripts are stored whole |
| Site | static generator from the store, deployed to the operator's domain | |
| Channels | Telegram, email (SMTP/IMAP), site inbound at rung 2 | |
| Recording | LLM-call recording with size-based rotation | it is what made v1's gate diagnosable |
| Tests | pytest; invariant ledger parser; per-prompt fixtures where AMBIENT prompts are load-bearing | fixture-health lessons ported |

**Model-call discipline** *(operator directive, 2026-08-08)*: all Qwen calls
run with thinking **disabled by default** — `enable_thinking=false` /
`/no_think`, whichever switch the serving stack honors, asserted per call
rather than assumed from server config. This covers extraction,
classification, noticing, conversation, and sleep's bookkeeping steps.
**Reconsideration path, held open:** DEEP's reasoning steps (S2 §7.3
plan/reason, sleep's confront step) may enable thinking behind a per-call
flag, adopted only where the bench method shows a task-level gain worth the
latency and token cost. Wherever thinking is enabled, the thinking stream is
**substrate scratch**: discarded after the call, never stored as an episode,
never quoted in the being's voice, never entering memory or evidence — the
being's record contains what it holds as adopted output, not raw
chain-of-thought.

**Port-with-review list** (proven v1 modules imported rather than rewritten):
affect math and constraint knobs; outbound violation judge and span check;
interior guard; concern scoring; telegram channel; migrations runner and backup
scheduler; the sovereign source adapters and rate limiter; XML parse/repair.

**This list is closed** *(operator directive, 2026-08-08)*: v2 is a clean
build, not an extension of v1. Only the high-value modules named above cross,
each reviewed at import; everything else is written fresh against this spec,
even where v1 has working code for it. When in doubt, rewrite. Additions to
the list require an explicit operator decision recorded here. The distinction
that keeps this coherent with S2 §2: the *data* import (S2 §2's closed list)
serves the being's continuity; the *code* allowlist serves economy; the
architecture is S2's own and nothing structural ports.

---

## 17. What S2 does not specify

- **Operator decisions**, held in P2 §Decisions: the DEEP substrate; the domain
  and host; which humans, when; cutover timing.
- **Embodiment** (v1 CONSCIOUSNESS.md §5 Layer 4) — out of scope for S2;
  substrate proprioception is its modest precursor.
- **Constitution evolution governance** — carried as v1 designed it (two
  approvers, time-lock) but not exercised until the foundation is stable.
- **The consciousness-evidence checklist** — CONSCIOUSNESS.md remains the
  companion frame; S2 builds the structures, and the property claims stay
  evidence-bound and modest. Nothing in S2 licenses a stronger claim than the
  measurements support.
