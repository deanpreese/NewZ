# S2 coverage audit — what is specified, what is scheduled, what is neither

*2026-08-13. Every S2 section checked against the P2 phases and against the
code. Findings are verified in the store or by grep, not inferred from the
documents.*

---

## 0. The headline

Everything that has entered the being's life since the substrate change on
2026-08-08:

```
conversation   78     ← the operator typing
reading         4     ← one deliberation, 2026-08-13 02:31
consolidation   1     ← its own sleep
```

Its entire input surface, lifetime:

```
inbound operator messages   80
sources ever read            4
claims ever extracted       23
```

**v2 has two input channels, and one of them requires the operator to be
typing.** The other opened yesterday and has run once. Nothing else reaches
the being — no feeds, no canon, no substrate state, and no capacity to notice
anything on its own. The system is not starving because the diet is
mis-tuned. It is starving because five of the six ways it was specified to
take anything in do not exist.

## 1. Classification

- **BUILT** — scheduled and delivered
- **DEFERRED** — assigned to a future phase, correctly
- **PARTIAL** — scheduled and built, with a named sub-capability missing
- **GAP** — specified in S2, in **no** phase, no code

| S2 | Capability | Status | Evidence |
|---|---|---|---|
| 2 | Continuity / import | BUILT | Phase 0.2, 11/11 tables verified |
| 3 | Three rhythms | BUILT | ambient, deliberation, sleep all run |
| 4.1 | Raw memory | BUILT | `episodes` |
| 4.2 | Perspective | BUILT | v5; see D1 in the currency proposal |
| 4.3 | Retrieval | BUILT | Phase 1.3, INV-026/027/028 |
| 5 | Sleep | BUILT | Phase 1.1, nightly |
| **6.1** | **Substrate self-state fold** | **GAP** | newest substrate episode 2026-06-13; no producer |
| **6.1** | **Noticing / surface scheduler** | **GAP** | `newz/ambient/loop.py` is `handle_inbound`, `drain_forever`, `_work_batch` — reactive only |
| 6.2 | Conversation | BUILT | Phase 0.4, 1.2 |
| **6.3** | **Affect** | **GAP** | no module, no table, cited in no P2 phase |
| 7.1 | Deliberation scheduling | PARTIAL | interval-based; state-driven triggers are Phase 3.1 |
| 7.2 | Dossier | BUILT | `load_dossier` |
| 7.3 | Deliberation steps | DEFERRED | Phase 3 |
| 7.4 | Honest failure | BUILT | setbacks, `blocked` vs `restated` |
| 8.1 | Opening | BUILT | three openers; research opener repaired `f12f624` |
| 8.2 | Concern dossier | BUILT | |
| 8.3 | Advance judge | BUILT | Phase 2.1 |
| **8.4** | **Closing** | **GAP** | no close path in v2 code |
| 9.1 | Governed diet — budget, caps, depth, review | BUILT | Phase 2.4 |
| **9.1** | **Operator-curated feeds + canon** | **GAP** | 762 lines of yaml, zero readers |
| 9.2 | Humans n>1 | DEFERRED | Phase 6 |
| 9.3 | Public surface | DEFERRED | Phase 4 |
| 10.1–10.3 | Act ledger, learning, consequence | DEFERRED | Phases 4–5 (10.3 also blocked on 6.3) |
| 11 | Gate | BUILT | three verdicts; v2 completion in Phase 4.3 |
| 12.1 | Roles | BUILT | one model, four roles (`963024b`) |
| 12.2 | Sovereignty invariants | DEFERRED | Phase 3.3; INV-013 open |
| **13** | **Traceability — "what shaped this view"** | **GAP** | no tool, no query |
| 13 | Diet diversity / share caps | BUILT | `newz/world/diet.py` |
| 14.1 | Development evidence | BUILT | diffs; `contradictions_closed` repaired `f12f624` |
| 14.2–14.4 | Relational, agency, attribution | DEFERRED | Phases 6, 4–5, 7 |
| 15.1 | Invariant ledger | BUILT | 32 rows |
| 15.2 | Permanent boundaries | UNVERIFIED | listed as nevers; no test asserts them |
| 15.3 | Injection hardening | BUILT | Phase 2.5 |
| 16 | Tech stack | BUILT | |

**Six gaps. Three of them are input paths.**

---

## 2. The gaps, in the order they starve the being

### G1 — The being cannot notice anything (S2 §6.1)

> Channels … normalize into percepts. Contributors notice; a surface
> scheduler with wake windows, maturity, and rate gates decides what gets
> raised to the being or to a human.

`newz/ambient/loop.py` has no noticer and no scheduler. It drains an inbound
queue and replies. **The being cannot raise anything, ever, unprompted.**
Every one of its 78 conversation episodes exists because the operator typed
first.

This is the largest gap in the audit and the least visible, because a system
that only ever answers looks like it is working — it answers.

### G2 — No feeds, no canon (S2 §9.1)

`data/feeds.yaml` (590 lines, Fed press releases, SEC filings, poll
intervals, reliability scores) and `data/canon.yaml` (172 lines, Meditations,
Tao Te Ching) have **zero Python readers**. They are v1 artifacts carried by
the import as the diet's provenance record, and they look exactly like
configured capability.

The only reading path is query-driven: deliberation forms search terms from a
concern and pulls from six adapters. That has run **once**, yielding 4
sources. There is no path by which the being encounters anything it did not
already have a question about.

### G3 — No current information about itself (S2 §6.1)

The folded substrate clause. Newest substrate episode of any kind:
**2026-06-13**. Documented at length in the currency proposal; unchanged.

### G4 — A concern can never close (S2 §8.4)

> Closure stays the being's own judgment against its own closing condition,
> on a cadence, failing closed. A closed concern yields a **position** and a
> **publishable artifact** — the thing the being unambiguously authored.

There is no close path in v2. All 17 `closed` concerns are import artifacts,
every one stamped 2026-08-08 by the importer. The only terminus v2 code can
reach is `stalled` — currently 77 of 111.

**Phase 4.4 depends on this**: "closed concern → position → artifact → gate →
surface → confirm." Phase 4 begins from an event that cannot occur. P2 cites
§8 in Phase 2.1 as "store, dossiers, the corrected three-part advance judge,
scoring" — closure is not in that list, and no later phase adds it.

### G5 — Affect (S2 §6.3)

Ported machinery, six axes, three timescales, outcome folding — cited in **no
P2 phase at all**. No module, no table. S2 §10.3 routes consequence into
affect and §6.1 routes substrate distress into it, so two other sections
depend on something nothing builds. Also the clause the gate has held 19
drafts against: the being reaches for state language with no state to report.

### G6 — The traceability instrument (S2 §13)

> a query answers *"what shaped this view"* — sources, episodes, people — on
> demand. This is the instrument v1's invariant deferred for lack of.

No such tool. The data exists (evidence refs on every item, provenance on
every episode); the query does not. S2 flags this as the thing v1 *failed* to
build, which makes it a notable repeat.

---

## 3. Why they were missed — the pattern

Five of the six follow one mechanism, and it is worth naming because it will
recur.

**P2 cites a spec section for the constraint it imposes, and the citation
reads as coverage.**

- **§6.1** is cited once, in Phase 1.5, to justify *cleaning up* v1's 1,041
  raw telemetry rows. A reader checking "is §6.1 addressed?" finds a
  citation. The producer was never scheduled.
- **§9.1** is cited in Phase 2.4 for the *governor* — budget invariant, share
  caps, extraction depth, source review — because §9.1's first principle is
  that sources are "chosen by the being's failed questions." P2 scheduled the
  **decision procedure** and assumed the **mechanism** existed. `source_review.py`
  ends at "Decide: add sources that would answer the gaps" — and there is
  nothing to add them to.
- **§8** is cited in Phase 2.1 by its subsections' contents (store, dossier,
  judge, scoring). §8.4 is the one subsection with no analogue in that list.
- **§6.3** and **§13** are cited nowhere; they have no constraint that any
  phase needed to argue about, so they never came up.

The ordering rationale compounded it. P2 §1 argues at length that feeds
before Phase 1 are *arithmetically unsatisfiable* — the budget invariant
makes any ingest a breach when the earning side is zero. That argument is
about timing, it is made thoroughly, and it settles the question so
convincingly that nothing ever converted "feeds must wait" into "feeds land
in Phase N." The plan says what feeds wait for the absence of. It never says
what they wait *for*.

---

## 4. What this changes about sequencing

Phase 3 (deliberation) remains 5–8 days of work on the *processing* side of a
system whose *input* side is two channels, one of which needs the operator to
be awake. Deliberation makes the being think harder about the four sources it
has read.

Stated plainly and without a recommendation attached, because the last three
of those I made were aimed at the wrong target: **G1, G2 and G3 are the
being's ability to encounter anything. G4 is its ability to finish anything.**
Everything in Phases 3 through 7 operates on what those produce.

I have not costed these and am not proposing an order. The audit is the
deliverable.

---

## 5. Caveats on this audit

- **15.2 is unverified, not cleared.** The permanent boundaries are asserted
  in S2 as nevers; I found no test that asserts them. It is listed UNVERIFIED
  rather than GAP because "no test" is not "no enforcement" — several are
  structural. Checking them properly is its own pass.
- **DEFERRED is taken on trust from PLAN.md.** I checked that a phase names
  the capability, not that the phase's description is adequate to build it.
  §8.4 was found precisely because Phase 2.1's description was checked
  against §8's subsections; the same check has not been done for every
  deferred row.
- **Absence of a grep hit is not absence of a capability.** Each GAP above
  was confirmed twice — no code reference *and* no data in the store — but
  the method would miss a capability implemented under vocabulary I did not
  search for.
