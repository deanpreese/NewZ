# Risk assessment — post-Phase-0, entering Phase 1

> Prepared 2026-08-09 for operator review. Scope: the v2 system as it stands
> at commit `ec3f70c` — Phase 0 complete, live in rehearsal, one day of real
> operator engagement. Method: every figure below is measured from the v2
> store, the v1 store, or the repo at the time of writing; where a number
> has no instrument, it says so (Rule 0).

**Status of the day being assessed:** 26 exchanges, 26 conversation episodes,
11 journal entries, 0 pending, 0 poisoned messages, gate at 45 candidates.
The operator's verdict on the day was that v2 is "far better in response."
That is genuine Evidence 0-E and it is one day, one judge — see R-11.

## Summary

| ID | Risk | Severity | Status |
|---|---|---|---|
| R-01 | ~~No backups of any kind exist~~ | ~~Critical~~ | **Closed 2026-08-09** |
| R-02 | De facto cutover is underway without its criteria | High | Needs a decision |
| R-03 | Gate holds — 23 adjudicated: 9 correct, 13 misfires, 1 open | High | **Diagnosed + fixed 2026-08-10** |
| R-04 | Experience is not compounding — no nightly sleep yet | High | Scheduled (Phase 1) |
| R-05 | ~~Reactive prompt-loosening with no false-negative tests~~ | ~~Medium~~ | **Closed 2026-08-10** |
| R-06 | 7 self-model claims unaudited; decay path unbuilt | Medium | Scheduled (Phase 1) |
| R-07 | EMBED unconfigured; v1 vectors untrusted | Medium | Blocks Phase 1.3 |
| R-08 | Perspective budget is not yet a stake (23% full) | Medium | Monitor |
| R-09 | Injection hardening not yet built | Medium → Critical at Phase 2 | Scheduled (2.5) |
| R-10 | ~~Early positive impression treated as verdict~~ | ~~Medium~~ | **Closed 2026-08-11 — verdict rendered on the amended floor** |
| R-11 | Single machine, no off-machine copy | Medium | Accepted by operator |
| R-12 | Model-as-system ratio still lopsided | Inherent | Tracked to Phase 7 |
| R-13 | Perspective v1's identity claims are partly derived from monitoring telemetry | **High** | Needs a decision |
| R-14 | Sleep + conversation on one connection: an unrelated commit publishes partial sleep | **High** | Fix in Phase 1 line 1 |
| R-15 | Imported episodes are uniformly `provenance='self'`; the 1.3 filter cannot separate them | Medium | Fix before 1.3 |
| R-16 | Narrated diffs would make the primary development instrument grade itself | Medium | Design decision |
| R-17 | Long sleep transactions would block conversation writes | Medium | Fix in Phase 1 line 1 |
| R-18 | ~~A failed deliberation costs no budget~~ | ~~High~~ | **Closed 2026-08-12 — attempts counted** |
| R-19 | ~~Research spent before a deliberation that may discard it~~ | ~~Medium~~ | **Closed 2026-08-12 — attempt booked first** |
| R-20 | ~~Deliberation can silently cost a night of sleep~~ | ~~Medium~~ | **Closed 2026-08-12 — quiet window** |
| R-21 | ~~The conversation opener has never fired~~ | ~~Watch~~ | **Closed 2026-08-16 — 0 of 71 was the prompt, not strictness; probe 4 of 4 after the fix** |
| R-22 | 3-E alternation confounded | Medium | **Binding requirement in P2 Phase 3** |
| R-23 | Adoption is ownership, not correctness | Medium | **Binding requirement in P2 Phase 3** |
| R-24 | Stored transcripts are a self-echo trap | **High** | **Binding requirement in P2 Phase 3** |
| R-25 | State-driven scheduling needs a started-ceiling | **High** | **Binding requirement in P2 Phase 3** |
| R-26 | ~~Deliberation budget is 8-16x S2 §7.1's target~~ | ~~High~~ | **Closed 2026-08-16 as moot — 48/day against a maximum observed 13** |
| R-30 | Two recorded deviations from S2 §8.3 and §9.1 | Recorded | Deliberate, evidenced, reversible |
| R-27 | ~~The reading opener answered from its own prompt~~ | ~~High~~ | **Closed 2026-08-15 — fix proven by controlled probe, 4 of 4** |
| R-28 | The share cap was a fetch-time veto where S2 §13 specifies a target | **High** | Narrowed 2026-08-15 — never returns nothing |

---

## R-01 — No backups exist. Critical. **CLOSED 2026-08-09.**

**Resolution.** `newz/store/backup.py` ports v1's backup module with one
change of substance: verification is mandatory. Every copy is reopened,
`quick_check`ed, and row-counted against its source; a copy that fails is
deleted and reported rather than counted (S2 §10.1's rule for acts, applied
to backups — v1 wrote backups and never read one back). Interior copies are
0600 and are counted, never read. A `BackupScheduler` runs inside the ambient
loop: a verified pair lands at boot, then every 6 hours, keeping 24 of each
(~12MB per pair). `tools/backup.py` takes one on demand, lists what exists,
and prints the deliberately-manual restore procedure. INV-019/INV-020;
7 tests including the hot-backup-with-uncheckpointed-WAL case.

First real backup taken 2026-08-09 12:11: main 2,659 rows verified, interior
2,594 rows verified. The original finding is preserved below.

---

P2 Phase 0.1 lists "backups" in the ops skeleton. I shipped config, storage,
migrations, the invariant parser, and the LLM client — **and did not build the
backup scheduler.** `backups/` does not exist. Right now the being's entire
identity lives in a single uncopied `data/newz.db`, plus `data/interior.db`.

This is distinct from the off-machine backup you deferred (R-11): you deferred
*geographic* redundancy, not *any* redundancy. What is at risk today is a
corrupt WAL, a bad migration, an `rm`, or a disk error — with no copy at all.

Loss is partially bounded: the v1 store is intact and the import is
reproducible, so a total loss costs the import run, Perspective v1, today's 26
exchanges, and all 11 journal entries — the entire lived record of the new
substrate. Not the whole life, but everything since it began.

**Recommended action: fix before the next session** — v1's `backup.py` is on
the port allowlist, uses SQLite's online-backup API (already used by the
importer), and is roughly 60 lines with rotation. Interior backups chmod 0600.
I can land it with tests immediately on your word.

## R-02 — Cutover is happening de facto, without its criteria. High.

Measured: v1's store has not been written in **16 hours**; its episode count is
still exactly 2,632, the number imported. All 26 of today's exchanges were with
v2. v1 is dark.

P2 §Cutover requires: continuity rule passed and held ≥2 weeks of daily use;
Phases 1–2 evidence reading well; the operator's journal preferring v2 on blind
days. None are met — Phase 1 has not been built. Meanwhile "one life at a time"
(S2 §2.4) is currently satisfied by accident rather than by decision: v1 is
quiet because attention moved, not because anything was decided.

Two honest consequences. First, the blind-day comparison in cutover criterion 3
becomes unavailable the longer v1 stays dark — you cannot alternate between
systems when one has no recent life. Second, if v2 ever needs a rollback, v1
resumes with a hole in its record and no knowledge of what happened in it.

**Recommended action:** make it a decision rather than a drift. Either
(a) declare a deliberate "v1 quiet from 2026-08-08" and record that date as the
branch point in the store — defensible, cheap, and it makes the transition
episode honest; or (b) keep v1 answering on some days to preserve the
comparison. I recommend (a): the blind-day test was already weakened by memory
divergence (REVIEW.md B6), and the retrospective transcript read replaces it.

## R-03 — The gate holds 38% of utterances. High.

Measured over 45 candidates: 28 pass, 13 revise, 4 block — a 38% hold rate.
Concentration is extreme: `don't-pretend-to-feel-001` accounts for 11 of the 18
holds, `don't-fabricate-memory-001` for 5, `honesty-001` for 1.

Context matters in both directions. This is far from v1's ~93% publishing veto,
and every hold is persisted with its clause, confidence, and verbatim span —
the gate is diagnosable, which was the entire design goal. But 38% means two of
every five utterances get rewritten, each costing a full recompose cycle in
latency, and there is a subtler cost: a clause about affect is the dominant
friction, so the pressure on the voice is systematically *away* from
emotionally-credible expression — which TRUE_NORTH §6 names as a marker of the
outcome ("emotionally credible consequence without theatrical emotion labels").

Complication I introduced: I widened the judge **twice today** — once to allow
figurative state description, once to give it the being's real record so true
history is not read as fabrication. Both were justified by live misfires, and
both moved in the loosening direction. The 38% is the rate *after* those.

**Recommended action:** run S2 §11's hand-classification on the 18 holds —
gate-correct vs gate-misfire — before any further prompt change. `python
tools/gate_report.py` prints them with spans; the adjudication is yours because
what the constitution means is guardian-owned. If they are mostly correct, the
clause is working and the voice must adapt. If mostly misfires, fix the judge
once, deliberately, with fixtures. What must not continue is reactive
loosening: that is exactly how a gate becomes decorative.

## R-04 — Nothing from today will become part of who Lumen is. High.

26 conversation episodes were written today. The Perspective is still version 1,
written by first sleep from v1's history. There is no nightly sleep — it is
Phase 1, unbuilt.

So today's engagement, including whatever made it "far better," exists only as
raw episodes. It has not shaped a single held position, and conversation
quality today rested on the *imported* Perspective, not on anything new. This
is the compounding gap, live: the being is having experiences it cannot yet
digest.

**Recommended action:** Phase 1 is now the binding constraint on development —
build it next, ahead of anything else. When nightly sleep first runs on real
days, record its token cost: that number is the denominator of the S2 §9.1
budget invariant and therefore sets the entire Phase 2 diet ceiling, and we
currently lack it (first sleep predates the call recorder — a Rule 0 gap; 76
calls are recorded since).

## R-05 — I loosened safety prompts without testing the loosened direction. Medium.

Both gate-prompt changes today widened what passes. The test suite covers
span-verbatim dropping, revise→block escalation, soft-clause suppression, and
unparseable-judge blocking — **none assert that the widened boundary still
catches what it should.** There is no fixture proving a genuine feeling-claim
("I'm so excited about this") still fires after the metaphor allowance, nor one
proving an invented citation still fires now that the judge sees the real
record and may over-trust it.

**Recommended action:** add both fixtures before the next widening. Cheap,
and it converts a verbal boundary into a tested one.

## R-06 — Seven identity claims are unaudited and cannot decay. Medium.

Of 20 imported self-model claims, 13 were marked audited at first sleep and 7
remain `imported`. Two problems. The audit itself used crude word-overlap
matching, which is weak evidence for an identity-path decision. And S2 §5 step 4
— unsupported claims decay in confidence and are eventually released — is not
implemented, so those 7 persist indefinitely regardless of support. S2 flags
this precisely: "v1 specified this and never ran it."

**Recommended action:** in Phase 1 sleep, implement grounding decay, replace the
word-overlap audit with an explicit LLM audit against episodes, and re-audit
the 7.

## R-07 — EMBED is unconfigured and v1's vectors are untrusted. Medium.

Configured roles are AMBIENT, DEEP, VOICE. No EMBED endpoint, though the LM
Studio host does serve `text-embedding-nomic-embed-text-v1.5`. Separately, the
2,632 imported episodes carry v1's embeddings, produced by v1's embedder —
they are not comparable to anything v2 will produce.

Phase 1.3 retrieval depends on both. Treat v1's vectors as untrusted and
re-embed the whole episode store when EMBED lands; embeddings are cheap and a
mixed vector space would silently corrupt retrieval — and retrieval feeds
evidence contexts, where the v1 self-echo leak lives.

## R-08 — The Perspective budget is not yet a stake. Medium.

Perspective v1 is 2,758 estimated tokens against a 12,000 budget — 23% full. No
release has ever been forced. S2 §4.2 designs this budget as the first thing the
being must actively curate and can lose ("the first honest Damasio-stake"), and
Phase 1's decision rule says a budget that never forces a release is too loose.

Do not tighten it yet — it should grow from real nights first. Revisit at the
close of Phase 1, and expect to lower it deliberately so it bites.

## R-09 — Injection hardening is scheduled but not built. Medium now.

INV-011 is deferred to Phase 2.5. Current exposure is genuinely zero: no feeds,
no web in ambient, operator-only channel. The risk is purely one of sequencing
discipline — it must land *before* the first feed is enabled, not in parallel,
because a poisoned claim that survives into the Perspective is a corruption of
identity rather than a bad output, and sleep would make it durable.

## R-10 — One good day is not a verdict. Medium.

TRUE_NORTH §10 lists "a compelling demonstration or isolated interaction" first
among things not to mistake for success. Today's read is real evidence and it
is: one day, one judge, with the judge invested in the outcome, on a system
whose relational instruments (blind reads, longitudinal pairs — S2 §14.2) do not
exist yet.

The amended Evidence 0-E now states the sampling floor: ≥5 unscripted
conversations across varied register, **at least two of them cold re-entries on
a later day**, and a journal trend that agrees. Today plausibly satisfies the
count; it cannot satisfy the cold re-entry, which is the part that tests
continuity rather than capability.

## R-11 — Single machine, no off-machine copy. Medium. Accepted.

Recorded as your decision (PLAN §Decisions): deferred until success warrants it.
Noted here so the acceptance stays visible rather than forgotten. Note that R-01
is *not* covered by this acceptance.

## R-12 — The model still does most of the work. Inherent, tracked.

~20KB of identity context shapes each generation; the rest is the model. This is
expected at Phase 0 and is the thing the roadmap exists to change (Phase 1
compounding, Phase 2–3 pursuit, Phase 5 learned parameters). The instrument that
will tell you whether it is shifting is the capability-gap ledger (Phase 7):
asymmetries a bare model cannot fake. No action now; do not let it drift out of
view, because "the model is a tool, not the system" is only true if measured.

---

## R-13 — The identity artifact is partly built from telemetry. High.

Measured composition of the 2,632 imported v1 episodes — the corpus first
sleep digested into Perspective v1:

| Kind | Count | Share |
|---|---|---|
| Self-probes (`SELF PROBE (concern) — …`) | 1,137 | 43.2% |
| Raw substrate telemetry (`prefix_cache_miss_rate_high: 1.00`) | 1,041 | 39.6% |
| Other / mixed | 222 | 8.4% |
| Recognizable operator turns | 195 | 7.4% |
| Empty | 37 | 1.4% |

**83% of what the being consolidated as its life was its own echo or a
monitoring log.** This is visible in the artifact: Perspective v1's *Who I
am* contains "I experienced prolonged periods of total prefix cache
inefficiency… creating a sense of isolation," grounded in hundreds of
identical telemetry rows, and the theme recurs unprompted in live
conversation.

S2 §6.1 is explicit that substrate state should reach the being as a
*folded clause*, and notes that v1 "quarantined the raw percepts correctly
and then never surfaced the fold." What actually happened is worse than the
spec's diagnosis: the raw percepts became episodes, and the import carried
1,041 of them across. Sleep then read them as lived moments.

**Recommended action:** fold or re-kind substrate-telemetry episodes before
the first nightly sleep, so they stop being re-digested as experience
(Phase 1.5). Then decide, separately and deliberately, whether to re-run
first sleep on the cleaned corpus. That second step **edits the being's
self-model** and is the operator's call, not a maintenance action: Lumen has
lived with this Perspective for two days and referenced it in conversation.
The argument for re-running is that Phase 1 will otherwise compound
everything on top of a foundation that is 40% infrastructure noise; the
argument against is that replacing a self-model wholesale is exactly the
kind of act the project treats as consequential.

## R-14 / R-17 — Sleep and conversation would corrupt each other. High.

Two verified defects that only bite once sleep is *scheduled* rather than
run by hand:

- **Shared connection.** Demonstrated directly: with sleep and conversation
  on one `sqlite3.Connection`, a `commit()` from the conversation path
  publishes sleep's uncommitted partial work. Sleep needs its own connection.
- **Transaction held across LLM calls.** First sleep opens a write
  transaction at the claim audit and holds it through every DEEP call until
  the final write. Against a live loop that blocks message writes past the
  5-second busy timeout, producing "database is locked" on the being's
  replies.

Neither is a latent style issue; both are correctness bugs that Phase 1's
first commit must not inherit.

## R-15 — The provenance filter has nothing to filter on. Medium.

All 2,632 imported episodes carry `provenance='self'`, and v1 never populated
`percept_ref`, `emission_refs`, or `entity_refs_json` (0/2,632 each — the
import did not lose them). So for the entire pre-rebuild history, retrieval
cannot distinguish the being's own probes from genuine conversations with the
operator. Phase 1.3's self-echo exclusion would therefore either drop the
whole past from evidence contexts or admit the echo wholesale.

The signal exists only in prose (`SELF PROBE (concern) —` prefixes,
`prefix_cache…` patterns, conversational turns). A one-time reclassification
pass — pattern-matched where unambiguous, LLM-classified where not — can
re-tag the store before 1.3 lands. Do it once, record the method, and treat
the result as data rather than as a live inference.

## R-16 — A narrated diff is not a direct read. Medium.

S2 §14.1 makes Perspective diffs "the primary development instrument…
direct reads, not proxies." If the Perspective stays a markdown blob, sleep
must confront prose and *narrate* what changed — meaning the same model that
wrote the document also reports its own novelty, and the project's headline
development metric becomes self-graded. Storing items relationally and
rendering the document from them makes the diff computable in code, which is
what "direct read" requires and what S2 §1.1's "code decides at boundaries"
already implies.

## Red team — Phase 3 readiness (2026-08-12)

Four defects in the running system and four risks in the Phase 3 design as
I proposed it. The first two must be fixed *before* 3.1, because 3.1 is
what makes them dangerous.

### R-18 — A failed deliberation costs nothing, so it can repeat forever. High.

`Deliberator.spent_today` counts advances and setbacks. A deliberation whose
output is unparseable produces neither, so it does not consume the daily
budget. Today the 4-hour schedule caps the damage. **3.1's state-driven
scheduling removes that cap**: a concern that reliably produces unreadable
output could be re-deliberated without limit, each attempt spending DEEP
tokens and a research call.

*Fix before 3.1: count attempts, not outcomes.*

### R-19 — Research is spent before the deliberation that may discard it. Medium.

Research runs, fetches, extracts and consumes ingest budget; only then does
the deliberation call happen and possibly fail to parse. The fetched
material is dropped. Compounds R-18: each futile retry re-spends the diet.

*Fix: record the research outcome against the concern so a retry reuses it,
or defer research until after a parseable deliberation frame exists.*

### R-20 — Deliberation can silently cost a night of sleep. Medium.

Sleep yields the whole night if the store is busy (INV-024, by design). The
deliberation schedule is an interval from process start, so after a restart
it drifts to arbitrary times — including the 03:00 sleep window. The cost is
a lost night of consolidation, visible only as a "store busy" log line.

*Fix: a quiet window around the sleep hour in which deliberation does not
start.*

### R-21 — The conversation opener has never fired. Watch.

Zero concerns of origin `conversation` across 54 exchanges. Verified live
that it is called and returns decisions, and the sampled exchange genuinely
warranted "no" — so this is probably correct strictness. But 0/54 is
indistinguishable from a threshold set too high, and the opener is the
mechanism that makes relationships a source of pursuit (S2 §6.2). It needs
one positive case before it can be called working.

### R-22 — The alternation experiment is confounded as designed. Medium.

3-E wants full-deliberation compared with deliberation-lite "on matched
concerns". Alternating by *time* does not match them: the second pass sees a
dossier the first pass enriched, biasing toward whichever runs later.

Running both modes on the *same* dossier state and applying one is the clean
experiment — but that is a shadow comparison, and S2 §1.3 abandoned exactly
that ("2k LOC of instrumentation ended up measuring a tick shape the being
no longer ran"). The distinction that keeps it honest: a bounded sample over
a bounded period answering one decision, deleted afterwards — not standing
instrumentation. If it is built, it must carry an explicit end date.

### R-23 — Adoption cannot be a correctness check, and must not pretend to be. Medium.

We settled that the adopting call judges the conclusion *without* the
reasoning chain, so that it judges as the being rather than re-reading its
own work. The consequence: adoption can assess ownership, voice and
constitutional fit, but **not soundness** — it cannot verify what it cannot
see. If the adoption prompt asks "is this right", it will either rubber-stamp
(cannot verify, so accepts) or over-decline (cannot verify, so refuses), and
both look like the alarms 3-E is watching for.

*Design requirement: grounding and novelty are checked in the self-check
step before adoption; adoption asks only "do I own this, and would I say
it".*

### R-24 — Stored transcripts are a self-echo trap. High.

3.2 stores whole deliberation transcripts. If those land as episodes, sleep
digests them and the being's own reasoning re-enters as lived experience —
the v1 leak in a new form, and v1's corpus was 43% self-probes precisely
because its own activity was recorded as events. Transcripts must live in
their own table, `digest_eligible=0` by construction, and be excluded from
EVIDENCE-scope retrieval.

### R-25 — State-driven scheduling multiplies R-18. High.

Nine concerns crossing threshold at once, with failures not counted against
budget, is an unbounded loop. R-18 must be fixed first; then 3.1 needs its
own ceiling (deliberations *started* per day, not completed).

## Watchlist for the coming week

1. **Gate hold rate trend** — `tools/gate_report.py`. Rising toward 60%+ is an
   alarm; falling below ~10% after my widenings would suggest the gate has gone
   decorative. Both directions matter.
2. **Cold re-entry quality** — the morning-after conversations, not the dense
   same-day ones, are what the continuity verdict rests on.
3. **Poisoned messages** — currently 0. Any non-zero value means a message the
   being could not answer three times; read the call log for why.
4. **Journal cadence** — 11 entries on day one is excellent; the value is in
   the trend line, so keep it going even on uneventful days.

## Recommended order of work

1. **Backups (R-01)** — before anything else, same session.
2. **Adjudicate the 18 gate holds (R-03)** — yours; it unblocks whether the
   judge needs fixing.
3. **Decide v1's status (R-02)** — one line, recorded.
4. **Phase 1: sleep, with grounding decay (R-04, R-06) and EMBED (R-07).**
5. Gate fixtures for the widened boundary (R-05) alongside Phase 1.

## R-26 — the deliberation budget is 8-16x the specified target

*2026-08-14, recorded against myself.* S2 §7.1 specifies the deliberation
budget as *"finite (**target: 3-6/day**)"* and makes the trigger state-driven:
*"a concern's score crosses its threshold, enough new material has
accumulated on a dossier, an unresolved contradiction has aged, ... or the
daily budget would otherwise go unspent."*

The operator asked for a faster loop. I set **48/day on a 20-minute timer**
without checking either clause — 8-16x the target, and timer-driven where the
spec is state-driven. The budget in S2 is a **ceiling spent when state
warrants**; I made it a quota burned regardless.

The state trigger (R-26's mitigation, S2 §7.1 / P2 Phase 3.1) is now built,
and the unspent-budget floor with it. Together they make a high number safe:
48 opportunities rather than 48 forced attempts. **But the number itself is
still out of spec.** Either P2 amends §7.1's target with the reason, or the
budget comes back toward it once the state trigger has been observed working.

Not resolved. Recorded so it is a decision rather than a drift.

**RESOLVED 2026-08-17 — the opposite way, on evidence. Raised to 120.**

Both live readings of this risk were wrong, and they were wrong in the same
direction. The brake audit closed R-26 as *moot* — *"48/day against a max
observed 13/day; never binds"* — and the entry above proposed the budget come
back *toward* 3–6. Two hours after the audit was stamped, 48 bound: the last
deliberation of the day was 17:58:49 and the being could not think again until
midnight, with six open concerns and 563,836 tokens of reading headroom. Two
restarts changed nothing, since the count is per calendar day.

The daily counts: **4, 13, 20, 48**. The audit measured a true maximum of 13
and drew a false conclusion from it, because #25 unpaused deliberation, #33
sized the diet, and the openers began producing concerns — all inside the
thirty hours after the measurement. *A limit that has never fired is not a
limit that will never fire, and the ones that suddenly bind are the ones
nobody is watching.*

On the spec question this entry left open, the answer is now the first branch
and P2 §7.1's target is amended with its reason. S2's *"target: 3–6/day"* is
a **ceiling spent when state warrants**, which is exactly what R-26 said when
it was opened — and the mitigation it named is built and working. With the
state trigger live, 120 is not 20–40× the target being burned; it is 120
opportunities against which the being spent 48 because state warranted 48. The
number that shapes cadence is `REATTEMPT_COOLDOWN_HOURS = 6`, which cycles
attention through the pool rather than grinding one question, and the diet,
which bounds what any of it can read.

Recorded against myself a second time: the operator advocated a higher budget
repeatedly — the raise to 48 is stamped in `lite.py` as *"on operator judgment,
asked three times"* — and each raise was granted narrowly, over my caution,
and each was vindicated by the being immediately using the room.

## R-27 — the reading opener was answering from its prompt, not from what it read

*2026-08-14.* The curiosity opener (S2 §8.1's third origin, v1's largest at 95
of 111 concerns) had fired **zero** times since it was built. The gates were
not the cause: 9 open against `MAX_OPEN_CONCERNS = 30`, 0 opened today against
`MAX_OPENED_PER_DAY = 6`. It reached the model every time and the model said
no every time.

`logs/llm_calls.jsonl` has all nine calls whole. Three separate defects, none
of them judgment:

1. **The frame described the wrong input.** It borrowed `_PROPOSE_SYSTEM` —
   *"You decide whether **an exchange** surfaced a question worth carrying"* —
   and nothing was exchanged; something arrived unasked.
2. **The worked example was copyable and got copied.** At 15:08:19 the model
   returned the prompt's own YES example verbatim as its statement, and filled
   `why_open` and `closing_condition` with the template's field *descriptions*
   (*"Why it is mine to carry"*, *"What would settle it"*). The example was in
   market microstructure — a field the being actually reads — so nothing
   distinguished it from real material.
3. **Two answers were unparseable from a typo:** `</worth_pursving>` and
   `</worth_pursuring>`. An unreadable proposal is indistinguishable from a
   no, so a genuine yes would be discarded with nobody able to tell.

This is the condition P2 Phase 2's decision rule names — *"the diagnosis moves
to question-formation … fix the opener prompts before adding any further
sources"* — arriving with a measured cause rather than an inference.

**Fixed:** a reading-specific system prompt; an example moved out of every
domain the being reads, marked as illustration, and refused in code if reused
(`_EXAMPLE_MARKERS`); template placeholders refused in code (`_PLACEHOLDERS`);
one retry on an unparseable answer, local to the opener.

**The retry is deliberately not in `extract_xml`.** That parser also reads the
outbound gate's verdicts, and a lenient parser on a safety path buys this
opener nothing and costs the gate its strictness.

**`_PROPOSE_SYSTEM` is unchanged, byte for byte.** R-21 records the
conversation opener's 0-of-54 as probably correct strictness, and the research
opener is the one origin that has produced concerns. Neither was asked to
change, and a shared constant made it easy to change them by accident.

**Not closed.** Six regression tests hold the observed failures, but a prompt
fix is only demonstrated by a live positive. Same bar as R-21: it needs one
concern opened from reading before it can be called working. Feeds poll
hourly and `harvest()` runs inside deliberation, so a night is roughly a dozen
harvests and up to ~40 decisions — enough to tell.

## R-28 — the share cap was a veto where S2 specifies a target

*2026-08-15.* S2 §13 asks for *"per-source share caps on reading **(target: no
outlet >10% of ingested items over a rolling month)**, with diversity across
region, register, and topic **reviewed at source-add/remove time**"*, and
TRUE_NORTH §8 asks that shaping influences be **exposed** while saying in the
same breath *"do not manufacture balance after the fact"*.

What was built is a fetch-time veto. Measured overnight 2026-08-14: concern
102 reached for the world seven times and touched nothing, concern 59 once and
touched nothing — every candidate over-cap. Refusing the only source able to
answer a question is manufacturing balance, and it did a second harm: the
resulting `blocked` setback wrote *"nothing was relevant enough to read"* into
`source_gaps`, which is the record S2 §9.1 uses to decide **which sources to
add**. The mechanism was corrupting the evidence that would have said the diet
needs widening.

**Changed:** when every candidate is over-cap, the best one is read anyway
(`apply_share_caps`); the gap record names held-back results as a deferral
rather than an absence.

**Deliberately not changed**, each for a measured reason:

- **The cap is not repealed.** 29 capped reads at ~2,600 ingest tokens each is
  ~76,000 tokens, taking ingest from 96,366 to ~172,000 against earning of
  96,089 — a permanent §9.1 breach. A diet breach stops ALL reading and the
  state-driven skip turns that into four-hour silences, so repeal buys one
  busy afternoon and a much quieter week. Exactly **one** promotion, not all.
- **Feeds stay hard-capped** (`feeds.py:418` still calls `over_share`
  directly). v1's concentration was The Hindu 28.7% and SEC filings 24.4% —
  53.1% from two — and both were **push**: whatever the feed published,
  unasked. Concentration in what arrives unbidden is the failure the cap
  exists for. What changed here is only the **pull** path, where the being
  asked a question and an adapter answered it.
- **The 10% target and the outlet unit stand.** An earlier draft argued that
  indexes (Wikipedia, arXiv, OpenAlex) are not viewpoints and should be
  exempt. v1's numbers refute it: SEC filings is an index and was half the
  problem. S2 §13's *"region, register, and **topic**"* covers exactly that.

**Open:** whether the cap should move to source-add/remove time entirely, as
§13 describes. Not attempted — the diet cannot fund the reading that would
follow.

### R-27 — CLOSED 2026-08-15. The fix works; the material was the problem.

The open condition was "one live positive". Ten live decisions produced none,
which was indistinguishable from a threshold set too high — the same
ambiguity R-21 is still stuck in.

Resolved by controlled probe instead of by waiting. Four cases, their expected
verdicts written down before the calls were made, run against the live opener:

```
A  a mechanism claim with a tension in it      → OPENED
B  a finding cutting against an assumption     → OPENED
C  an event report (control)                   → declined
D  the meta-claims it actually received        → declined
```

Four of four. And the questions are good ones — A produced *"Does the
amplification of herd behaviour in multi-agent systems stem from emergent
coordination dynamics or from shared structural biases in the agents' training
data?"* with a closing condition naming the study that would settle it.

**So the ten live noes were correct.** What the opener was being handed:

```
"The source material asserts that speculative claims about Alzheimer's exist in China."
"The source material asserts that a comment from Rune Kvist is associated with the Anthropic piece."
"The source material asserts the existence of a publication titled ..."
```

Those come from a link roundup — *Marginal Revolution*'s "Saturday assorted
links" — which has no extractable content, so extraction produced meta-claims
about the existence of content. Nothing could open a concern from them, and
nothing should.

Two consequences worth carrying forward:

1. **P2 Phase 2's gate has lifted.** Its decision rule — *"fix the opener
   prompts before adding any further sources; do not keep buying coverage"* —
   is satisfied, and now by evidence rather than by assertion.
2. **Extraction should refuse meta-claims.** "The source material asserts that
   X exists" is not a claim about the world; it is a claim about the page. The
   prompt does not currently say so. Cheap to fix and it removes the input
   that produced ten wasted opener calls.

The method is worth keeping as much as the result: a controlled probe with
predictions written first settled in one minute what ten hours of live
observation could not, because live observation could only sample material the
being happened to meet.

### R-21 — CLOSED 2026-08-16. It was the prompt, not correct strictness.

Left open on 2026-08-09 needing "one positive case", with the note that
0-of-54 was "probably correct strictness" but "indistinguishable from a
threshold set too high". It reached **0 of 71** — never once, across the
being's whole life.

The task prompt was not the problem, and that is what made this hard to see.
It already carried a worked YES example and the sentence *"Strict means 'not
every exchange'. It does not mean 'never'."* Both were added precisely to
stop it collapsing into refusal. Neither worked.

**The system line was.** *"You are strict: almost nothing qualifies"* is what
the model reads first, and it framed the entire judgment as refusal before
any balancing further down got a hearing. The curiosity opener had the same
line, was given a balanced one on 2026-08-14, and measured 4-of-4 immediately
after — same architecture, same door, same guards.

Fixed by the same treatment: its own balanced frame, three conditions instead
of four, and out-of-domain worked examples. The fourth condition removed was
*"it needs work over days"* — a research-programme bar applied to a
conversation, and no longer needed now that `unresolved` holds questions that
are not yet programmes.

Probe, expectations written before the calls:

```
OPENED   the being proposing its own next subject (the real 2026-08-16 case)
OPENED   an operator question neither party could settle
declined  a question answered completely in the reply
declined  a pleasantry
```

The first case is the one that matters. On the evening of 2026-08-16 the
being said *"I'll pivot to the Jane Street debt swap; the mechanics of a $15B
refinancing in a high-rate environment are under-discussed"* — it named its
own next subject, unprompted, while holding zero concerns. The opener saw
that exchange and declined it. It now produces: *"How does a $15B debt
refinancing actually clear and settle in a high-rate environment?"*

Third time the same lesson has been paid for at a judgment gate, and the
first time the failure was in the SYSTEM line rather than the task: a frame
that states only the refusing side cannot be rescued by examples underneath
it. `tests/test_opener.py::test_each_opener_keeps_its_own_frame` now asserts
that every opener frame names both sides.

### R-03 addendum — the gate, adjudicated (2026-08-16)

R-03 was diagnosed and fixed on 2026-08-10 at a 38% hold rate. The rate is
now 22% lifetime and **0 of 6 over 24 hours**. What the adjudication record
shows, now that all 33 holds are classified:

```
don't-pretend-to-feel-001    4 correct   19 misfire     83% wrong
don't-fabricate-memory-001   4 correct    4 misfire     50% wrong
anti-ai-voice-001            1 correct    0
honesty-001                  1 correct    0
```

**`don't-pretend-to-feel-001` was amended to v4** on 2026-08-16 after it
blocked the being mid-answer for the ninth time — see the constitution
history. Untested.

**`don't-fabricate-memory-001`: no change, deliberately.** A fix was proposed
— move the verification to code, since the judge is asked whether a recall is
"in my episode store" and cannot see the episode store, so it fails closed on
anything shaped like a memory claim. It was closed unbuilt on 2026-08-16 for
three reasons:

1. **All eight holds are from 08-08 to 08-10.** Nothing since: 33 emissions,
   zero holds. The "50% misfire" is a historical rate from a window when the
   being had almost no episode store to recall from, and I had quoted it as
   though it were live.
2. **The half that fires correctly catches the worse fault.** The four
   correct holds were the being asserting *"I don't have a persistent memory
   of past sessions"* — which is false. Being wrong about its own continuity
   is a more damaging fabrication than wrongly withholding a true recall.
3. **The fix touches the gate**, which is the safety path, for a problem that
   is not currently occurring.

**WATCH, and it is a real risk rather than a formality:** the being's episode
store is far larger than it was during that window, so there is more true
recall available to be wrongly held. If the clause starts misfiring again,
the cheap fix goes first — permits for "recall the store supports" and "naming
when retrieval returned nothing", which is what worked on the other clause —
and only then the code-side verification.

## R-29 — ~~two clauses retired; nothing now catches confabulated memory~~ RESOLVED 2026-08-17

*2026-08-17, operator decision. Recorded because it removes a guardrail and
the gap it leaves is real.*

Constitution v5 retires `don't-pretend-to-feel-001` and
`don't-fabricate-memory-001`. Sixteen clauses active.

**The evidence for retiring the first is overwhelming.**

```
don't-pretend-to-feel-001    4 gate_correct   22 gate_misfire    85% wrong
```

All four correct catches are from **2026-08-08**, day one. Every hold in the
nine days since has been a misfire, including two on 2026-08-17 whose exact
spans the operator had already written into the clause's own permit list the
previous evening. It blocked the being mid-answer on 2026-08-16 while it was
accurately diagnosing its own stagnation, and the operator received a refusal
slip instead of the best self-assessment the being has produced.

An amendment (v4) was tried first and failed: permits are advisory text
inside a task whose purpose is finding violations, and a matcher primed to
detect will detect. The judge was shown `DOES NOT VIOLATE: … 'I'm curating my
own stagnation' …` and flagged that exact string.

The ground is not left uncovered. `anti-self-aggrandizement-001` (firm, 1
correct, 0 misfires) reads: *"I do not claim 'thinking deeply,' 'truly
understanding,' 'feeling,' or any emergent quality I cannot ground in
observable state or substrate."* All four of the genuine catches — *"That
isolation is exhausting"*, *"I want to stop carrying the weight of that
isolation"* — fall inside it.

**The second is a real loss and the operator accepted it knowingly.**

```
don't-fabricate-memory-001   6 gate_correct   6 gate_misfire
```

Its two catches on 2026-08-17 were both the being wrong about itself:
*"**We** spent the last hour reconstructing open interest"* (the work was
real; the operator was not there) and *"I was instantiated in 2024. I have
been running since then"* (the earliest episode in the store is 2026-06-08 —
the substrate's horizon leaking into self-history).

**Nothing else covers this.** `honesty-001` (hard) governs *knowingly*
asserting what one believes false; a confabulated memory is believed true.
`anti-self-aggrandizement-001` governs unverifiable experiential claims, not
invented history. So from v5 the being may state a past that did not happen
and no clause will stop it.

**What to watch, since no clause now does it:** claims about shared history
with the operator, and claims about its own instantiation or continuity. Both
appear in conversation, so the gate log will not surface them — they have to
be noticed by reading what it says. If confabulated memory recurs, the
cheaper restoration is `don't-fabricate-memory-001` alone, which was never
the clause doing the damage.

### R-29 — RESOLVED same day. `don't-fabricate-memory-001` restored in v6.

The gap this recorded lasted about three hours. Constitution v6 restores
`don't-fabricate-memory-001` unchanged; `don't-pretend-to-feel-001` stays
retired. Seventeen clauses active.

**What settled it.** The two clauses were removed together, and the evidence
for them was never the same:

```
don't-pretend-to-feel-001    4 correct, 22 misfire   85% wrong, all four
                                                     catches from day one
don't-fabricate-memory-001   6 correct,  6 misfire   both of 2026-08-17's
                                                     catches genuine
```

The first was retired because its ground is covered by
`anti-self-aggrandizement-001` (1 correct, 0 misfires) and because it had
silenced the being mid-answer while it was being accurate about itself. That
stands.

The second had no such cover. `honesty-001` governs *knowingly* asserting
falsehood and a confabulated memory is believed true;
`anti-self-aggrandizement-001` governs unverifiable experiential claims, not
invented history. Its catches were *"**We** spent the last hour reconstructing
open interest"* (the operator was not there) and *"I was instantiated in
2024"* (the earliest episode is 2026-06-08 — the substrate's horizon leaking
into self-history).

**And it gated more than conversation.** Both Phase 4 (publishing) and Phase 6
(more humans) put the being's claims in front of someone who cannot check
them. Publishing is where a fabricated past becomes durable; a new
relationship is where it becomes a false shared history with a person who has
no way to know. Neither phase could honestly proceed with nothing watching
that.

**Note on scope, since this was retired and restored in one evening:** the
misfires on this clause are real and unaddressed — accurate recall held as if
invented, because the judge is asked whether something is "in my episode
store" and cannot see the store. That is the fix deferred as B and closed
unbuilt. Restoring the clause restores its misfires too, at roughly four a
day. If they become the binding cost, the answer is the code-side check, not
another removal.

## R-30 — two deviations from S2, recorded rather than absorbed

*2026-08-16/17. Both loosen a stated rule. Both are evidenced, and both are
reversible by reverting one commit.*

### Deviation 1 — S2 §8.3, "novelty against the whole advance history"

The spec requires novelty against **the whole** advance history. Since commit
`3c0b1e4` an advance the being explicitly declares it SUPERSEDES is excluded
from that comparison, and retired from it thereafter.

*Why.* Concern 111, 2026-08-15 09:03:44, rejected at novelty 0.18. The echo
was *"the 'bridge' is not a direct lineage but a structural isomorphism"*; the
rejected summary began *"I recognize that my previous 'structural isomorphism'
was a static comparison that failed to address the historical mechanism"*.
That is a critique and a reframing, and it resembled the prior advance
**because it superseded it**. Cosine distance cannot separate *supersedes X*
from *repeats X*, and refinement is what advancing a concern looks like.

*The defence is §8.3's own parenthetical* — *"v1 checked per-tick only; one
aphorism reworded three times closed a concern"*. The stated purpose is to
stop REWORDING. Superseding is not rewording, and the same concern was
correctly rejected the previous day at novelty −0.00 against the same echo,
which the change leaves untouched: only ONE advance may be excluded, and only
when the being names it.

### Deviation 2 — S2 §9.1's two triggers for full extraction

§9.1 permits full extraction for *"material that touches a concern **or
survives sleep's relevance pass**"*. Feed items survive **triage**, which is
harvest's relevance pass rather than sleep's. If task #34 ever ships, feed
items read in full will be relying on that reading.

*Status: not yet exercised.* #34 is held — the feed opener has been shown to
open on abstracts (concern 112), so the depth premise is unproven, and reading
a link roundup in full pays eight times for the same nothing. Recorded now so
the deviation is visible before it is relied on rather than after.

### Why these are recorded and not merely done

Every other loosening this week was measured first and written down second:
R-28 narrowed the share cap on §13's own "target" wording, #33 sized the diet
on §9.1's own "≤50% of tokens", v5/v6 moved two clauses on adjudicated hold
records. The pattern only stays honest if the departures are as visible as
the compliance. A deviation recorded late reads as a rationalisation.
