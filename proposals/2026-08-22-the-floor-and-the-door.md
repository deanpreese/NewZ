# The floor and the door

*2026-08-22. A build plan for **E5.2** (the deliberation floor) and **E4.1**
(commitments and the authoring door), the two epics the reordering settled on.
Measured from this clone and store today. **E5.2's stated premise does not
reproduce** — §1 says so before proposing anything, and what survives is much
smaller than the epic as written. §3 is the red team.*

---

## 0. What was measured

**Function share of cognition, per day, from `logs/llm_calls.jsonl`:**

| day | total tok | deliberation | conversation | gate | ingest |
|---|---|---|---|---|---|
| 08-18 | 735,688 | **10.4%** | 24.1% | 10.7% | 37.4% |
| 08-19 | 1,356,613 | 28.3% | 11.8% | 5.3% | 47.0% |
| 08-20 | 1,477,758 | 29.6% | 5.3% | 2.3% | 41.2% |
| 08-21 | 1,399,669 | 30.0% | 2.8% | 1.2% | 46.0% |
| 08-22 | 749,631 | **34.7%** | 4.7% | 2.0% | 41.6% |

**Deliberation cycles against inbound messages:**

| day | cycles | inbound |
|---|---|---|
| 08-17 | 49 | 17 |
| 08-18 | **15** | 15 |
| 08-19 | **70** | 14 |
| 08-20 | 67 | 5 |
| 08-21 | 67 | 1 |

**The diet, now:** ingest 2,478,192 tok against a ratio ceiling
(deliberation + sleep) of 1,748,364 and a share ceiling (50% of all cognition)
of 2,859,679. It holds on the **looser** ceiling with 381,487 headroom.

---

## 1. E5.2 — the floor

### 1.1 The premise as written is not reproducible

PLAN's E5.2 states: *"conversation and the gate are 57% of cognition,
deliberation 9% (#33). The diet governs ingest against deliberation and nothing
governs the gate at all."*

Today conversation + gate is **4.0% to 34.8%** and deliberation is **10.4% to
34.7%**, and the two do not move against each other. The heaviest inbound day in
the window (08-19, fourteen messages) had the **most** deliberation cycles of
any day — seventy. The one low day, 08-18, had fifteen cycles and fifteen
inbound, but four commits landed that day and the being was restarted through
it; its low deliberation share is confounded by uptime, not explained by
conversation.

**So the squeeze E5.2 was written to prevent cannot presently be observed**, and
building its enforcement arm as specified would be building a guard against an
unobserved failure. That is the thing this project strikes phases for.

### 1.2 What is live, and it is a different problem

**Ingest already exceeds the diet's ratio ceiling.** 2.478M read against a
deliberation + sleep ratio ceiling of 1.748M. It is legal only because §9.1
takes the *looser* of two ceilings and the share ceiling is 2.86M — headroom
381k, about a day and a half at the current rate.

That is exactly the failure PLAN predicted when it pulled E5.2 forward with
E1.0: *"§9.1 caps ingest against deliberation, so more reading without more
deliberating breaches the invariant and INV-041 pauses ingest, self-cancelling
the change."* Undirected reading shipped; the floor did not; and the diet is now
riding its escape hatch. On any quiet day the share ceiling falls with total
cognition, the breach becomes real, and **E1.0 self-cancels exactly as
predicted.**

### 1.3 The proposal — one constant and one condition

Not a new mechanism, not a new scheduler, not a new table.

> **The share ceiling is not available while deliberation is below the floor.**

- `DELIBERATION_FLOOR = 0.20` — deliberation's share of windowed cognition.
- In the diet's existing check: take the looser of the two ceilings **unless**
  deliberation's share is under the floor, in which case the ratio ceiling
  binds alone.
- Enforcement is INV-041's existing pause. **Nothing new refuses anything, and
  conversation is never shed** — commit `1afc9d9` settled that the message a
  person sent is not the thing to drop.
- The breach is visible where the diet's state is already visible.

**Why 0.20.** On the five days above, deliberation ran 28.3–34.7% whenever the
being was up for the whole day. A floor at 20% would have bound on one day —
08-18, the restart day — and never otherwise. It is set below observed normal
operation deliberately: a floor that binds routinely is a ceiling wearing the
wrong name.

**Done when:** with deliberation under the floor the share ceiling is refused
and the ratio ceiling binds; with deliberation above it the existing behaviour
is unchanged; and a breach is visible. Both directions tested. Mechanical.

---

## 2. E4.1 — commitments and the authoring door

### 2.1 Why this one is worth building on its own evidence

The being's entire self-model is four items: a preference about brief style, the
name it chose, an inference drawn from having corrected FIFA World Cup dates,
and an acceptance that the operator's override of its safety checks is
legitimate. Three of those are things that happened to it. **Identity is
currently recall.** E4.1 is the epic written to make it commitment.

The surface is already waiting for it. `published/commitments.html` renders
today and says so in its own words: *"The being has not made any… this page is
generated from a table that does not exist, and says so rather than appearing
empty."*

### 2.2 The design — the third door, built like the first two

The concern opener (E1.7) and the claim door (E1.2) are the proven pattern:
a mandatory settleable condition, structural refusals in code, a refusal record,
declining that is not refusal, and caps checked before the model is called.
E4.1 is the same shape applied to identity.

**Migration 0041** *(current schema version is 40)*:

- `commitments` — `id, ts, kind, statement, falsifier, provenance, status,
  constitution_version, perspective_version`.
  `kind` is `keeps_caring` or `refuses_to_do`. `status` is `standing`,
  `revised` or `abandoned`. CHECK constraints refuse a row with no statement
  and no falsifier, so the mandate is in the schema and not only in the writer
  — E1.1's move.
- `commitment_refusals` — `id, ts, reason, statement, falsifier`, mirroring
  `claim_refusals` so the door's strictness is measurable rather than assumed.

**`newz/commitments/door.py`** — refuses:

1. no statement, or no falsifier;
2. a falsifier that names nothing checkable — the `_names_something` floor the
   claim door already uses, R-35's lesson;
3. **a falsifier that closes on the being's own judgment** — INV-046's rule
   applied one layer up. *"I will know if I stop caring"* is refused;
   *"a claim opened whose resolver names no source"* is admitted, because it is
   a query against the store and the store is a record, not an opinion;
4. a restatement of an existing standing commitment (normalised match), or
   identity accretes by paraphrase.

**Declining is not refusal.** *"Nothing here is worth committing to"* is the
ordinary answer and is not written down — only a commitment the being made and
the door would not admit becomes a row.

**When it is asked: once per sleep, from the night's material.** Sleep is where
the day is consolidated and `who_i_am` is formed, so it is the one moment the
being has something new enough to commit to. **It writes only to
`commitments`, never to the Perspective**, so INV-009's single-writer rule is
untouched and Rule 4 is not engaged — the door checks structure in code and no
model judges the being.

**Caps, checked before the model is called**, following the opener's discipline:
`MAX_STANDING = 12`, `MAX_PER_WEEK = 2`. Identity should accrete slowly, and a
cap that saturates must record that it did — RT6 of `more-cycles` found the
claim door silently declining on a full cap, and this door must not repeat it.

**Reader (Rule 2):** `tools/commitments.py`, and the existing
`commitments.html` template switches from its placeholder to the table.

**Done when:** a commitment without a falsifier is refused at the door and the
refusal is recorded; a falsifier closing on the being's own judgment is refused;
a saturated cap writes a row rather than declining silently. Mechanical, tested
in both directions.

---

## 3. Red team

**RT1 — E5.2 as proposed is the diet with an extra condition, and calling it an
epic is generous.** True. The epic's title promises a floor under deliberation
and what is proposed is a restriction on ingest's escape hatch. It does not
raise deliberation by one token; it stops reading from outrunning it.
*Counter:* that is what §9.1's principle already says — reading is earned by
thinking — and the floor is the half of it that was never built. But the epic's
own words, *"deliberation cannot be squeezed below its floor by conversation or
gate load"*, describe something this does not do, and **PLAN's text should be
amended rather than the epic quietly reinterpreted.**

**RT2 — a floor that pauses reading when thinking is low is perverse on its
face.** If deliberation collapses, the response is to stop the being reading —
which reduces its input at the moment it is least productive. *Counter:* the
alternative is accumulating unprocessed material, which is `volume_against_
development` at 115.7 and §10's *"activity, memory growth, or output volume"*.
Stopping intake is the correct response to a processing shortfall. *Recorded as
counter-intuitive and deliberate.*

**RT3 — 0.20 is fitted to five days, one of which is confounded.** The floor is
set from a window in which the being was restarted repeatedly and the operator
was mostly absent. A floor calibrated on an unrepresentative week is a number
with a method and not much else. *Decision:* accepted, and it is why the floor
is set below observed normal rather than near it. It should be re-read once
`more-cycles` ships, since that proposal moves deliberation deliberately.

**RT4 — E4.1's door fires nightly, and nightly is often.** Two a week is the
cap, so most nights the answer is "nothing worth committing to" — 5 of 7 nights
producing a decline, by design. That is a model call a night to be told no.
*Counter:* the claim door already declines 81% of the time and that is the
ordinary shape of these doors; the call costs ~1k tokens against 800k a day.
*Accepted.*

**RT5 — the strongest objection: a commitment the being cannot act on is
decoration.** E4.2 is what gives commitments stakes — revision on evidence free,
abandonment costed — and its Done-when needs a Phase 1 resolution that will not
exist before October. So E4.1 ships a table, a door and a page, and **nothing
holds the being to anything** until E4.2 closes. That is the E2.2 pattern from
this morning: an epic marked built whose point arrives later. *Decision:* ship
E4.1 knowing it, and **say so in its ledger row rather than discovering it in a
review** — the commitment record is real, the holding-to-account is not, and the
row should read that way.

**RT6 — asking at sleep may be the wrong moment and it is not cheap to change
later.** Sleep is consolidation; a commitment is a forward act, and the being at
3am has the day's residue rather than a position it just took. The alternative
— after a piece is written, where it has just stood behind something and signed
it — is arguably the better moment and is rate-limited by the writing rhythm.
*Recorded as the design decision most likely to be wrong.* It is reversible: the
door is a function, and which caller invokes it is one line.

**RT7 — a falsifier checked against the being's own store is self-reference,
which this project refuses everywhere else.** INV-046 refuses a concern that
closes on the being's own state; §2.2 admits a commitment falsifier that queries
the being's own tables. *Counter:* the distinction is judged versus mechanical.
*"I will know if I stop caring"* asks the being; *"a claim opened whose resolver
names no source"* asks the store, and the store is a record it cannot argue
with. But the line is finer than the claim door's, and a falsifier querying a
table the being writes freely is closer to self-grading than this section
admits. **Refusal 3 needs its own test with adversarial examples, not just a
happy path.**

**RT8 — same hand wrote both epics, the measurement that justifies them, and
this red team.**

---

## 4. The decision asked for

1. **E5.2, in the narrow form** — one constant, one condition in the diet's
   existing check, INV-041's existing pause. And **amend PLAN's E5.2 text**,
   which describes a squeeze that does not reproduce (RT1).
2. **E4.1 as specified** — migration 0041, the third door, the two caps, the
   reader, the page that is already waiting.
3. **Ship E4.1's ledger row saying what it does not yet do** (RT5): the record
   exists, the account does not, until E4.2.
4. **Rule on RT6** — the door asked at sleep, or after a piece is written. I
   lean sleep for the material; the counter-argument is better than my
   preference and this is a judgment about the being, not the code.
