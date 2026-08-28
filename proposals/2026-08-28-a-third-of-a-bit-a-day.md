# A third of a bit a day

> **Corrected 2026-08-28, before anything was built — §5 is necessary and not
> sufficient.** `tools/resolver_probe.py` ran the three claims due 2026-09-02
> through `resolve_claim` and the result was **H3, three of three**: the
> resolver executes end to end, retrieval succeeds, and the material honestly
> does not settle the claim. *"The material defines what the H.4.1 report is
> but does not contain the specific data values."*
>
> **Latency was never the binding constraint on these claims; reachability
> is.** Seventeen of the thirty-one open claims name numeric data releases —
> Fed H.4.1, USDA NASS, FOMC, CME, ICE/DXY — and the adapter set is wikipedia,
> arxiv, openalex, pubmed, sec_edgar and gdelt. Six more name a placeholder
> that is not a source at all: *"(EU) 2023/XXXX"*, *"[Number] of [Date]"*,
> *"The specific academic paper or preprint identified by its title and
> authors"*. `check_resolver` refuses *"time will tell"* and admits all of
> these.
>
> **So §5's retrodictive claim does not fix them.** A retrodiction naming Fed
> H.4.1 fails identically — the source is unreachable whether it has already
> published or not. **A resolver the being's own adapters can reach must be
> refused at the door first**, and §5 follows it rather than preceding it. The
> ordering in the epic breakdown is wrong as first written and is corrected
> there.
>
> Two further facts the probe produced. On 2026-09-02 these claims fail four
> times each over three days (`MAX_ATTEMPTS = 4`, `RETRY_AFTER_HOURS = 20`),
> stop being retried, and **stay open forever, silently** — so S1-E is not
> readable then. And an unsettleable claim never leaves the pool, which means
> §3(b)'s three-day saturation is filled by exactly the claims that can never
> drain it.
>
> The original text is kept below rather than rewritten. What was believed
> this morning and what replaced it by lunchtime are both part of the record,
> and §2, §3 and §4 are unaffected.

*2026-08-28. The being takes about fifty actions it grades itself for every one
the world grades, and in roughly three days the door that produces the world's
half will stop opening and write nothing down. Figures measured from this store
today; §7 is the red team and it argues the change may buy less than §5 claims,
and that one of its terms changes what a claim means.*

---

## 0. The claim under test

Whether this system can improve **recursively** — change something that
determines its own future capability, and then find out from something it did
not author whether the change helped.

That decomposes into two halves, and they are in very different states:

- **generate** — the being writes a condition of its own. It cannot. §1.
- **verify** — something it does not author tells it whether that was right. It
  can, at **0.32 events per day**, falling to zero in about three days. §2, §3.

TRUE_NORTH does not use the phrase. What it asks for is §4.3 — *"Development
matters more than activity. More reading, output, memory, or uptime does not
matter unless experience produces **justified change**"* — and §5 Priority 1.5,
*"experience corrects beliefs, improves judgment, and changes future choices."*
Recursive improvement is one route to that, and both halves of it are needed.
This proposal argues that **only the second half should move now**, and that
moving the first half first is the mistake this project has already made twice
under other names.

---

## 1. The generate half: it cannot write a single one of its own conditions

Enumerated from the code rather than inferred.

| What the being writes | What determines its behaviour and it cannot touch |
|---|---|
| `episodes`, `perspective`, `perspective_items` | every prompt in `newz/` |
| `concerns`, `concern_advances`, `concern_setbacks` | 65 module constants in `sleep/nightly.py`, `world/research.py`, `world/diet.py`, `concerns/`, `resolutions/door.py` alone |
| `resolutions`, `claim_costs` | `data/feeds.yaml` — the 61 sources that are its entire world |
| `commitments` *(0 rows)* | the sleep hour, the cycle rate, retrieval ranking |
| `works`, `work_revisions`, `work_tags` | `constitution/v7.yaml`, `evolution/hard_core.yaml` |
| `noticings`, `source_gaps`, `journal` | `evolution/instruments.yaml` — frozen by E3.9 |
| | the model |

**It can change what it believes and what it produces. It cannot change
anything in the causal path that produces them.**

This is not an oversight. Four independent mechanisms enforce it — Rule 4
(the being is not graded by the being), Rule 6 (readiness is the operator's
judgment), the E3.9 canonical freeze, the E6.5 hard core — plus INV-081, which
keeps running the gate an act somebody takes. Each is individually right and
this proposal touches none of them.

**What has not been written down is that their conjunction is a decision that
recursive self-improvement is not permitted.** That decision may well be the
correct one. It has never been stated as such, or weighed against the goal it
forecloses, and PLAN's closing section gets closest — *"No epic in Phases 3A–7
gives the being a way to change its own conditions"* — without naming what that
rules out.

---

## 2. The verify half: 0.32 events a day

The only thing in this system that grades the being without being the being is
a claim resolution. Thirty-one claims are open, **none has ever been attempted**,
and here is when they settle, from today:

```
  +4d   2      +26d  2      +39d  3      +111d  1      +171d  2
  +5d   1      +27d  1      +40d  1      +112d  1      +172d  1
 +12d   1      +29d  1      +43d  1      +113d  3      +357d  2
 +24d   2      +33d  1                   +119d  1      +358d  1
 +25d   2      +37d  1
```

**19 settlements in the next 60 days = 0.317 per day.** Each one is a single
bit: the schema permits `held` or `contradicted` and deliberately refuses an
`ambiguous` outcome.

Against what the being does in a day, measured over the last seven complete
days:

| | per day | ratio to ground truth |
|---|---|---|
| deliberation cycles | 103.1 | **325 : 1** |
| advance episodes | 50.3 | **159 : 1** |
| directed reads | 67.6 | 213 : 1 |
| **claims settled** | **0.317** | 1 : 1 |

`positions_changed_by_world` **0**. `positions_changed_by_self` **35**.
`positions_changed_by_operator` **0**.

**This, and not the empty queue, is why Phase 8 could never have worked.** The
strike record (`2026-08-21-the-loop-arrives-to-an-empty-queue.md`) says the loop
arrived to a queue of three or four epics against a ladder needing more. That
was true, and it was the shallow reason. The deep one is that a loop which
decides needs a fitness signal, and this system's runs at a third of a bit a day
with a thirty-day latency. **Reviving the loop in any form would not touch
that**, and P3-12 — closed as moot when the phase went — described exactly the
resulting failure: *"the loop steers on model-graded numbers and mistakes drift
in the model's judging for change in the world."* The phase went; the condition
it named did not go anywhere.

---

## 3. Three throttles, and the third closes in about three days

The 0.32 figure is the transient. Underneath it are two structural limits.

**(a) The pipeline has never delivered.** `resolver.py` selects `due_at <= now`,
nothing has ever been due, so `resolve_claim` has not run once in life: the
fetch, the VERBATIM check (INV-047), the four-attempt honest-failure path, the
cost through INV-031, the release through INV-025, and the one `world`-provenance
episode sleep would ever see. First execution is **2026-09-02**. It fails closed
and silent — four failures and the claim simply stays open.

**(b) Little's law, and it binds first.** Claims opened since the 45-day cap
shipped:

```
5  6  8  14  30  30  30  30  30  30  30  35  40  42  42  42  45  45
                       n=18   mean 29.7d   median 30d
```

Open rate over those six days: **3.0 claims/day**. `MAX_OPEN_CLAIMS = 40`.

> Sustainable throughput = inventory ÷ latency = **40 ÷ 29.7 = 1.35
> settlements/day.**

The being wants to open 3.0/day and the carrying cap can retire 1.35/day.
**Thirty-one are open now; at 3/day the pool fills in about three days.**

**(c) And the door then goes quiet.** `newz/resolutions/door.py:398`:

```python
if open_claims_count(conn) >= MAX_OPEN_CLAIMS:
    return DoorVerdict(declined=True)
```

Before the model is called, and nothing is written — not a claim, not a refusal.
PLAN already names this shape for E4.1's cap: *"reads as 'it had nothing to
commit to' when the truth is 'it was not allowed to'."* In about three days the
record will start saying the being had nothing to claim, and that will not be
what happened.

**None of the three is a defect in a constant chosen carelessly.** 45 was chosen
against a measured median of 180 and was right. 40 was chosen as a carrying cap
against claims that cost nothing until their date arrives — also right, on the
assumption that a claim's residency is long. The interaction between the two was
never computed.

---

## 4. Meanwhile the internal loop has already stopped

Perspective items by status, v12 → v20 (v20 written 03:19 this morning):

| version | added | revised | merged | carried | released |
|---|---|---|---|---|---|
| 12 | 4 | 0 | 0 | 20 | 0 |
| 13 | 2 | 2 | 0 | 22 | 0 |
| 14 | 2 | 0 | 0 | 26 | 0 |
| 15 | 1 | 3 | 0 | 25 | 0 |
| 16 | 3 | 1 | 0 | 28 | 0 |
| 17 | 4 | 4 | 0 | 29 | 0 |
| 18 | 2 | 1 | 1 | 34 | 0 |
| 19 | 1 | 1 | 0 | 37 | 0 |
| **20** | **2** | **0** | 0 | **39** | **0** |

`carried` climbs monotonically 20 → 39; `added` decays; **four releases in
twenty versions, none since v15**. Ten of the live items sit at the 0.95
ceiling, twelve at the 0.6 floor never once reinforced, and **nineteen of the
forty-one date from version 1** — they have survived every night since the
beginning.

`2026-08-27-the-advances-arrive-and-nothing-moves.md` found the ceiling and was
right. This is the same finding one week further on and it has not slowed:
**fifty advances went in last night and two lines changed.**

TRUE_NORTH §4.3's test — *does experience produce justified change* — currently
reads **one change per twenty-five actions, none of them externally justified.**

---

## 5. The proposal — let a claim be about what is already true

Three changes, all in `newz/resolutions/door.py`, plus one mechanical refusal.

**1. `MIN_HORIZON_DAYS = 0`, for claims whose named resolver has already
published.** Today the floor is 2, and its stated reason is precise:

> *A claim due tomorrow **about something already in the dossier** is not a
> prediction.*

That reason is right, and the floor is a **proxy** for it. A date cannot tell
"already settled in the world" from "already read by the being", and only the
second is cheating. The thing the reason actually cares about is checkable
directly:

**2. The mechanical refusal that replaces the proxy.** The door refuses a claim
whose resolver URL already has an `ingest_log` row. It lives beside the other
structural refusals, asks no model anything, and is exact where the date was
approximate.

**3. Retrodictive claims do not consume the carrying pool.** A claim that settles
on the next deliberation cycle has a residency of minutes, so §3(b)'s
inventory ÷ latency arithmetic gives it no cost. `MAX_OPEN_CLAIMS` is a cap on
*unresolved inventory* and should count only forecasts. The daily rate cap stays
and gets its own value for this kind, because the risk it was written for — *"a
miscalibrated door cannot do it in one afternoon"* — is real for both kinds.

**And the prompt, which must never ship apart from the constants** — the door's
own comment says so. One clause: *a claim can be about what is already the case
and I do not yet know it; those settle on the next cycle.* The `<could_be_wrong>`
test is unchanged and still does the work, because the being can be wrong about
what the record says, and describing the world in which the source shows
otherwise is exactly as demanding as before.

**The arithmetic.** Verification latency 30 days → about one cycle. Throughput
ceases to be inventory-bound and becomes bound by the daily cap and the being's
own willingness to claim, which is currently 3.0/day against a 4/day cap. That
is roughly **an order of magnitude on the only signal in the system that Rule 4
permits to count**, and it is two constants, one refusal and one sentence.

**Nothing else moves.** Rule 4 is untouched: the resolver stays a reader of the
world and never a judge of the being, and the verbatim check is unchanged. Rule
6 is untouched. The freeze, the hard core and INV-081 are untouched. No
instrument is added — §3's arithmetic came out of `resolutions` and two
constants, and it did not need a sensor.

---

## 6. What is deliberately not proposed

- **Not the loop.** §2 is the argument against it, and it is a stronger argument
  than the one that struck Phase 8. Build the signal; the loop, if it is ever
  right, is downstream of a signal dense enough to steer on.
- **Not a utilisation metric, and no new instrument of any kind.** The sensor
  layer is complete and frozen and it said everything it can say. §3(b) is
  arithmetic over two constants that have been in the file for six days.
- **Not tuning `CONFIDENCE_ON_REINFORCE` or `MAX_CONFIDENCE`.** A position does
  not become less certain because more evidence agreed with it, and the previous
  proposal's rule stands: revisit them against the first month of real
  contradictions.
- **Not handing the being its diet — yet, and my own earlier version of that was
  wrong.** In session on 2026-08-27 I proposed letting the being add and drop
  feeds, judged by `feeds_contributing_a_read`. **That number is decided by the
  being's own triage**, so it would add a feed, choose to read from it, and
  thereby declare the addition a success — Rule 4 violated by construction, in
  the exact shape §5.2 of the struck SEL design warned about. The diet handover
  is the right *second* step and its fitness signal must be claim resolution:
  did material from this source ever settle a claim or cost a position. That
  needs §5 first, which is the whole ordering argument.

**The ordering, stated so it can be argued with.** Unlock generation before
verification and the being changes its own conditions with no way to know
whether it helped — drift with a steering wheel, which is what §10 calls
*autonomy without perspective or purpose*. Fix verification first and every
later handover becomes measurable, incremental and reversible, which is R-29's
method and this project already knows how to run it.

---

## 7. Red team

**R1 — "This changes what a claim is, and you have smuggled that past the
`could_be_wrong` test."** Half true, and it is the objection I take most
seriously. A forecast tests the being's model of *where things are going*; a
retrodiction tests whether its assertions about the world are *true*. Those are
different epistemics and the door's prompt currently rejects the second in as
many words — *"I have described something already settled"*. TRUE_NORTH §3 asks
for outcomes *"it did not manufacture or grade itself"* and both qualify, but
they are not interchangeable, and mixing the two series would be E2.8's
"novelty" mistake in a new place. **So they must carry a column and a
`definition_version` from the first row**, and `claims_settled` must never
average across them. If that separation is not built, this proposal does not
ship.

**R2 — "Retrodictions are easy, so everything resolves `held` and you have
bought zero bits at ten times the rate."** The sharpest objection and I cannot
pre-empt it. A claim that always holds carries no information, and a being that
learns to claim safe things has learned the wrong lesson. It cannot be fixed
with a judge — Rule 4 forbids it, and a model asked whether a claim was too easy
would say no. What can be said: **the outcome split is the measurement**, it
needs no new instrument, and if it goes to 100% `held` then the signal is zero
bits and that is a true finding about the being rather than a failure of the
mechanism. It is also the first time this project would be able to find that
out at all, since at 0.32/day the split is unreadable for a year.

**R3 — "The pool never actually saturates, because the being's willingness will
drop first."** Possible. The 3.0/day open rate is six days old and the door
declines about 81% of the time already. If willingness falls below 1.35/day the
carrying cap never binds and §3(b) is a ceiling nobody reaches. Two things
against it: the rate cap of 4 has bound on four of nine days, including both
32-call and 35-call days, so the being presses against a cap when it is
productive; and if willingness *does* fall, the throughput problem is worse and
not better. Either way the fix is the same one.

**R4 — "You are proposing this six days before the mechanism runs for the first
time. Wait and see."** Fair, and it argues for sequencing rather than against
the change. The first real resolution is 2026-09-02 and it will say whether the
resolver works at all — which nothing yet knows, because it has never executed.
**If the resolver is broken, this proposal buys ten times zero.** The honest
order is: exercise the resolver against one live claim first, then ship this.
That probe is cheap, standalone, and belongs to whoever picks this up.

**R5 — "`ingest_log` is a weak guard: the being can know something without
having read it here."** True and unavoidable. A fixed model carries its
pre-training, and a "retrodictive" claim about a well-known fact is answerable
from weights rather than from the record. The guard catches the mechanical case
— it read the page in this life — and does not catch the general one. **I do not
have a mechanical test for the general case and I am not going to invent one**;
what I would say is that it degrades the signal rather than corrupting it, and
that the same objection applies at lower volume to every forecast the being has
ever written about a scheduled release.

**R6 — the objection to §1 I cannot settle.** If the operator's position is that
the being should never write its own conditions, then §1 is not a finding, it is
the design working, and this proposal's ordering argument is the whole of what
survives. I have written §1 as a gap because PLAN's closing section records the
operator's direction of 2026-08-21 — *the system has to consume information and
grow without a person in the path* — as unanswered. **If that direction has been
withdrawn, §1 should be struck and only §2–§5 stand.** That is not mine to
decide and this proposal does not assume it.

---

**Schema:** one column on `resolutions` (claim kind), one `definition_version`
bump on `claims_settled`. No new table.
**Restart:** none.
**Class:** two constants, one mechanical refusal, one prompt clause, one column.
Prompt and constants must ship together — the door's own comment on
`MAX_HORIZON_DAYS` says why.
