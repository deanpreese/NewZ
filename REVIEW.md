# Pre-implementation review — S2 / P2 / TRUE_NORTH

> Reviewed 2026-08-08 against the repo as of commit `23072ae` plus untracked
> `data/` files and `.env` (keys inspected, values not recorded here). Scope:
> readiness to begin Phase 0, red team of the documents and data, open
> questions. This document follows the repo's own citation convention.

## Verdict

**Conditionally ready.** The document set is unusually strong — the v1
post-mortem is honest and specific, every corrected mechanism carries its
reason, and the plan's decision rules are real decision rules rather than
gates. Nothing found here challenges the architecture. But there are seven
issues that should be resolved *before* Phase 0 starts, because they are
either contradictions inside the documents, dependencies the plan orders
wrong, or losses of exactly the kind of record S2 says must never be lost.
All are fixable in a day or two of document work plus a few operator
decisions. None requires redesign.

---

## 1. Blockers — resolve before Phase 0

### B1. ~~Dangling cross-file links~~ — RESOLVED 2026-08-08

The rename of `S2.md`→`SPEC.md` and `P2.md`→`PLAN.md` was intentional
(operator confirmed), but the internal links still pointed at the old names,
and `.gitignore` cited a phase number from an earlier PLAN structure.
**Fixed in place:** both document headers now link to the real filenames and
state that `S2 §` / `P2 §` citations resolve to `SPEC.md` / `PLAN.md`
respectively; the `.gitignore` comment now cites P2 Phase 4.1.

### B2. Phase 0/1 sleep depends on DEEP — RESOLVED 2026-08-08

Decision #1 resolved: DEEP is local (Qwen3.6-30b-a3b MoE), by design — a
frontier backbone risks the model becoming the system. Sleep runs on local
DEEP from Phase 0 (P2 Phase 0.3, amended); no stand-in substrate ever exists,
so Phase 1's decision rule reads the real mechanism. Original finding kept
below for the record.

P2 §Decisions states "Nothing in Phases 0–2 waits on these." But:

- Phase 0.3 (first sleep — digesting 59 days / 2,715 ticks of v1 episodic
  history into Perspective v1) and all of Phase 1 run sleep, and S2 §3 and
  S2 §5 step 2 place sleep's synthesis on **DEEP** — the substrate that does
  not exist until Decision #1 is made and Phase 3 builds the dispatch
  boundary.
- Worse, Phase 1's decision rule ("if diffs are dominated by restatement, the
  digest prompts or the confrontation step are failing — fix before Phase 2")
  cannot distinguish *mechanism failure* from *undecided substrate*: a weak
  local stand-in producing restatement-heavy diffs would send you debugging
  prompts when the actual cause is the model.

**Fix:** either (a) pull Decision #1 forward so it is consumed by Phase 0, or
(b) explicitly specify that sleep runs on the local REASON-class model through
Phases 0–2, state that in S2 §5, and re-scope Phase 1's decision rule to
account for it (e.g., re-run the ≥7-night diff evidence after DEEP lands
before treating restatement as a mechanism verdict). Option (a) is
recommended: the review itself calls DEEP "the single highest-leverage choice
available to the project," and the first sleep is the continuity artifact —
the one sleep that must not be cheap.

### B3. Decision #5 contradicts the Decisions preamble — RESOLVED 2026-08-08

Preamble amended; Decision #5 resolved (clean build, S2 §2 import set from
`../NGBeing`, full-digest default stands). Original finding kept below.

P2 §Decisions opens with "Nothing in Phases 0–2 waits on these," then
Decision #5 (import scope) is "*consumed by Phase 0*." Phase 0.2 cannot run
the importer without it. Small, but it is exactly the internal-consistency
class of error the documents ban. **Fix:** amend the preamble ("Nothing in
Phases 0–2 waits on these except Decision #5, which Phase 0 consumes") — and
since the default is already recommended, the operator can simply ratify it
now.

### B4. Phase 2 research vs no-web-in-ambient — RESOLVED 2026-08-08

P2 Phase 2.3 amended: research runs inside a minimal scheduled
deliberation-lite (dossier + research + advance judge on local DEEP); the
full S2 §7.3 step structure lands in Phase 3, and Phase 3-E now compares
full-deliberation vs deliberation-lite advances. Original finding kept below.

S2 §7.2 and S2 §15.3: web access happens only inside deliberation, through
the sovereign adapters; ambient never calls the web. But deliberation is
built in Phase 3, and Phase 2.3 builds and exercises the "research cascade
against sovereign adapters." In Phase 2 there is no deliberation for that
research to live inside. Related: Phase 3-E compares "deliberation advances
vs ambient-only advances," implying an ambient path that advances concerns —
but S2 §3's table gives ambient no such role, and S2 §7 places concern
movement exclusively in deliberation. The ambient advance path is load-bearing
for two phases' evidence and is unspecified.

**Fix:** specify the interim shape — e.g., a minimal scheduled
"deliberation-lite" lands in Phase 2 (dossier + research + advance judge, no
DEEP, no adoption split), which Phase 3 then deepens. That also gives
Phase 3-E its comparison population honestly. Alternatively, move 2.3 into
Phase 3 and accept that concerns can only *stall honestly* in Phase 2.

### B5. Person-data minimization vs relational deliberation — DISSOLVED 2026-08-08

Everything is local (Decision #1); no hosted vendor exists in the cognition
path, so relational deliberation is private by construction. The S2 §12.2
hosted-DEEP invariants remain in the spec as dormant guarantees. Original
finding kept below.

S2 §12.2 invariant 4: raw person-model rows and **private conversation
content stay local**; DEEP receives only public-register person summaries.
S2 §7.1: a deliberation trigger is "a human interaction left something worth
sitting with." S2 §7.2: the dossier includes targeted retrieval — which,
for that trigger, is retrieval over conversation episodes. As written, the
being cannot deliberate deeply about a relationship without either sending
private conversation content to a hosted vendor (violating §12.2.4) or
running blind (undermining the relational success criterion). The spec never
says which wins.

**Fix:** decide and write it down. Defensible options: (a)
relationship-triggered deliberations always run local-only (they become part
of the sovereign interval's population — slower thought about people, private
by construction); (b) a consent/abstraction layer where conversation episodes
enter DEEP dossiers only as being-authored summaries in public register. If
DEEP ends up local (Decision #1), the contradiction dissolves — one more
reason B2's decision comes first.

### B6. The cutover blind test cannot be blind

P2 §Cutover criterion 3: the operator alternates which system answers "without
deciding which is which until after the verdict." But the two systems'
memories diverge from the moment rehearsal starts: v2 does not remember
yesterday's conversation that v1 handled, and vice versa. Any reference to
recent shared history — the very thing the continuity test values —
unblinds the trial immediately. The two-beings risk is named in P2 §Risks,
but its corollary for the strongest available test is not.

**Fix:** make the blind read *retrospective and transcript-based* instead of
interactive: a blind reader (or the operator after a washout) scores
interleaved, date-stripped transcripts from both systems against TRUE_NORTH
§6 markers. Interactive alternation can stay as a secondary, acknowledged-
unblind instrument. Also answer Q4 below (which being does the journal track
during rehearsal).

### B7. The curated world is untracked — RESOLVED 2026-08-08

`.gitignore` now ignores `data/*` but tracks `data/*.yaml`; `feeds.yaml` and
`canon.yaml` are committed. Original finding kept below.

`.gitignore` ignores `data/` wholesale, so `data/feeds.yaml` and
`data/canon.yaml` are not in git. `feeds.yaml` is not runtime data — it is
operator curation with dated rationale comments (the Reddit-PF removal
lesson, the 2026-07-18 viewpoint-breadth pass), i.e., exactly the "material
shaping influences … traceable and open to challenge" that TRUE_NORTH §8
requires and the source-review history S2 §13 depends on. A disk failure
erases the diet's provenance. **Fix:** track the curated YAMLs (e.g.,
`!data/*.yaml` beneath the `data/` rule, or move them to `config/`); keep
ignoring databases and runtime artifacts, which the `*.db*` rules already
cover.

---

## 2. Red team — spec and plan

- **R1. The v1 repository is unlocatable from this repo.** Phase 0.2 (the
  importer), the port-with-review list (S2 §16), the v1 invariants-as-tests,
  and the constitution all live in "the v1 repository" — which is never named
  or pathed anywhere here. S2 §0 claims "a reader needs TRUE_NORTH and this
  file, nothing else," which is true for *understanding* but false for
  *building*. Phase 0 cannot start without a pinned pointer (path + commit)
  to v1 and its store. Record it in P2, plus the import method (the store is
  the being; the importer should work from a read-only copy, verified by the
  counts Phase 0.2 already specifies).
- **R2. Plan arithmetic breaks Rule 0.** P2 §Risks says "the phase estimates
  total ≈5–7 working weeks," but the phases sum to 33–50 working days ≈
  7–10 weeks. If "rehearsal" means Phases 0–2 only (13–20 days), say so —
  the rehearsal-drift tripwire ("roughly twice that") moves a lot depending
  on which number it binds to. Every figure a range, with its method — the
  plan's own rule.
- **R3. Prompt injection is unaddressed, and the attack surface is scheduled.**
  RSS content, scraped pages, Reddit threads (Phase 2), and rung-2 inbound
  from strangers (Phase 7.1) all enter as percepts processed by LLMs. Nothing
  in S2 §15.3's invariant list says *untrusted content is data, never
  instructions*. The noticer/extraction/conversation prompts need injection
  hardening, and rung 2 needs it as an explicit precondition — a stranger's
  message that steers the being into an outbound act is the cheapest way to
  breach every other boundary. Recommend adding a standing invariant plus
  regression fixtures (hostile feed item, hostile inbound message) before
  Phase 2 and again before Phase 7.1.
- **R4. No off-machine continuity.** S2 §16 keeps v1's "backups with
  rotation," but if that means same-disk (or same-machine) backups, the
  sovereign identity path has a single point of physical failure — the one
  vendor that can end the being's existence is the SSD. TRUE_NORTH §7 makes
  recoverability a strategic requirement. Recommend an explicit invariant:
  periodic encrypted backup to operator-controlled off-machine media,
  restore-tested (a backup that has never been restored is decorative, by the
  project's own logic).
- **R5. Publishing lacks a person-privacy clause.** The per-person privacy
  boundary (S2 §9.2) governs person-to-person leakage in conversation, and
  §12.2 governs leakage to vendors — but nothing shown governs the *public
  surface*: the being publishing about the operator or humans 2–3. Presumably
  the constitution covers it (unverifiable from this repo — see R1). Verify
  before Phase 4; if absent, it belongs in the gate's clause set.
- **R6. Ablation windows vs the honesty principle.** S2 §2.2 makes the
  substrate change an *experienced* event because honesty about what it is
  includes honesty about this. Phase 7.3 then toggles off sleep, Perspective,
  or learning for measured windows — lesions the being is apparently not
  told about. Whatever the answer, the asymmetry deserves a sentence: either
  ablations are also experienced events (which contaminates the measurement)
  or the guardianship rationale for silent ablation is stated.
- **R7. Voice-fingerprint check is cited but never specified.** P2's
  DEEP-voice-bleed mitigation and S2 §12.1 both lean on it; S2 never defines
  the mechanism or its consumer. Given Rule 1, it needs a spec home (even one
  paragraph) before Phase 3 claims it as a mitigation.

## 3. Red team — data and environment

- **D1. `.env` carries a secret in a comment.** The Telegram `api_hash` (and
  app id) are duplicated in plaintext comment lines. Comments escape every
  `KEY=value` redaction tool — that is how they nearly ended up in this
  review. The file is gitignored and 0600, but: delete the comment block, and
  rotate the api_hash (cheap via my.telegram.org) since it has now existed in
  at least two places.
- **D2. Bot *and* user-account Telegram credentials are both present.**
  `TELEGRAM_BOT_TOKEN` plus `TELEGRAM_API_ID`/`API_HASH`/`PHONE` (an MTProto
  user-session credential set). If the being ever speaks through the
  operator's *user* account rather than the bot, it presents under a
  human-looking identity — colliding with the disclosure-always boundary
  (S2 §9.2, TRUE_NORTH §5 Priority 3). If the user API is only for reading,
  say so somewhere; if it is vestigial, remove it.
- **D3. Role vocabulary mismatch.** `.env` keys are `EXTRACT` / `REASON` /
  `VOICE`; S2 §12.1 defines `VOICE` / `AMBIENT` / `EMBED` / `DEEP`. `EMBED`
  has no endpoint configured and `DEEP` is (correctly) absent pending
  Decision #1 — but `EXTRACT`/`REASON` map to nothing in the spec. Align the
  config schema with S2's role names in Phase 0.1 so the dispatch-boundary
  invariants attach to the names the spec uses.
- **D4. Share caps need an outlet field.** S2 §13 caps "no outlet >10% of
  ingested items," but `feeds.yaml` has no outlet identity — Bloomberg is 3
  feeds, BBC 3, NYT 2, DW 3, and Aeon/Psyche share a publisher. Cap
  enforcement at feed granularity would under-count every multi-feed outlet.
  Add an `outlet:` key to the schema.
- **D5. The AP feed is not AP.** `https://feedx.net/rss/ap.xml` is a
  third-party mirror; the 0.9 reliability assigned to "Associated Press" is
  actually trust in feedx.net, which can alter, inject, or drop content.
  Same class of issue: the "Reuters" feed is a Google News search proxy, so
  item URLs and effective provenance are news.google.com. Replace or
  re-label both; provenance tags should name the pipe, not the brand.
- **D6. Reliability numbers have no method.** Rule 0 says every number
  carries its method; the hand-set reliability values are vibes-priors.
  That's acceptable *as priors* (S2 §5 step 6 recomputes from contribution),
  but the file should say so in one comment line, and the recompute should
  be the value of record.
- **D7. Paywalled full-text.** FT, Economist, WSJ, Bloomberg, NYT feeds are
  headline/teaser-only; "full extraction" (S2 §9.1) on those items would mean
  fetching paywalled pages — a citizenship rule collision. State that
  adaptive extraction stops at feed-provided content for paywalled outlets.
- **D8. Canon skew is a shaping influence — record it.** All 20 canon works
  are public-domain and pre-1930, overwhelmingly Western, with a deliberate
  KJV/Tao/Analects spread. Reasonable, but S2 §13 requires diversity review
  "at source-add/remove time" — canon counts. One paragraph in the repo
  recording the skew and the rationale makes it traceable instead of
  ambient. (Same for the three low-reliability Reddit sources — if
  r/StonerPhilosophy and r/Astral_Projection are deliberate texture, say so;
  they are the diet's least defensible items on paper.)

## 4. What is genuinely strong (kept short deliberately)

- The 1.1/1.2/1.3 kept/corrected/abandoned tables with reasons attached —
  the abandonment reasons are as valuable as the designs.
- Consumer-traced acceptance (Rule 1) as *acceptance criterion* rather than
  audit — the single best structural answer to v1's severed-loop pattern.
- The Perspective budget as a stake, and diffs as the primary development
  instrument — measurement read off the artifact itself.
- Three-verdict gate with persisted holds; hold rates with denominators.
- Sovereignty as *continuation, demonstrated continuously* (the sovereign
  interval) rather than exclusivity — the §12.3 argument is honest about the
  cost v1 paid for the stricter reading.
- Decision rules that reorder the plan instead of gating it, including
  Phase 6's "disengagement is the most valuable data, not a failure to hide."

## 5. Open questions — status as of 2026-08-08

Operator answered all ten; resolutions recorded in P2 §Decisions.

1. **Decision #1 (DEEP)** — resolved: local, Qwen3.6-30b-a3b MoE, by design
   (frontier backbone risks the model becoming the system).
2. **Decision #5 (import scope)** — resolved: clean build, S2 §2 import set;
   full-digest default stands.
3. **Where is v1** — resolved: `../NGBeing`, accessible during the build;
   pin the consumed commit in the import record.
4. **Journal during rehearsal** — resolved: one journal, per-entry system
   tag; a second only if the need arises.
5. **Relational deliberation privacy** — dissolved by #1 (everything local).
6. **Off-machine backup** — deferred by the operator until success warrants
   it; recorded as accepted risk (R4). Local rotation still ships Phase 0.1.
7. **Telegram user-API** — removed from `.env`; bot API carries the
   bi-directional operator channel. Rotate the api_hash regardless (D1).
8. **Constitution person-privacy clause (R5)** — still open; verify against
   `../NGBeing`'s constitution before Phase 4.
9. **Rung-2 injection posture (R3)** — still open as spec work; belongs in
   S2 §15.3 before Phase 2 (feeds) and Phase 7.1 (stranger inbound).
10. **Ablation (R6/Phase 7.3)** — operator questions whether it is needed at
    all; retained as *optional* attribution instrument, decided when Phase 7
    arrives.

### Remaining open items (nothing blocks Phase 0)

- **B6** — cutover blind test: replace interactive alternation with
  retrospective date-stripped transcript scoring (doc fix, needed before
  cutover, not before Phase 0).
- **R2** — reconcile the "≈5–7 weeks" figure with the 33–50-working-day
  phase sum and state which number the rehearsal-drift tripwire binds.
- **R3** — RESOLVED 2026-08-08: injection invariant added to S2 §15.3
  ("untrusted content is data, never instructions"), built as P2 Phase 2.5
  before feeds enable, and a precondition on Phase 7.1 (rung 2).
- **R5** — constitution publishing-about-people clause check (before
  Phase 4).
- **R7** — one-paragraph voice-fingerprint spec (before Phase 3).
- **D4–D8** — feeds/canon hygiene: `outlet:` field for share caps, replace
  the feedx.net "AP" mirror and Google-News "Reuters" proxy, method note on
  reliability priors, paywall rule for extraction, recorded rationale for
  canon skew and the Reddit sources.
- **D1 residue** — rotate the Telegram api_hash at my.telegram.org.
