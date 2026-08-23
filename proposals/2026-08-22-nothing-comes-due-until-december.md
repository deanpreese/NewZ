# Nothing comes due until December

> **Superseded as a standalone, 2026-08-22.** Folded into
> `2026-08-22-more-cycles.md` §2 on the operator's instruction, and decided
> there alongside the cycle values it interacts with. Kept in full for the
> §1 inventory of what has never executed and for the red team, which the
> fold summarises rather than reproduces.

*2026-08-22. Every claim the being has ever made is dated beyond the point at
which it could learn from it. Figures measured from this clone and store today;
§4 is the red team and it argues the cap may be too tight.*

---

## 0. The measurement

Twelve claims are open. Not one has been attempted, because not one is due.
Their horizons, in days:

```
120  120  120  120  120  128  180  180  180  365  365  365
```

Minimum **120**. Median **180**. The earliest settles **2026-12-18**; the last
**2027-08-22**.

The door permits **2 to 365** (`MIN_HORIZON_DAYS`, `MAX_HORIZON_DAYS`), and its
prompt's worked example is **42**:

```
     resolver: CFTC Commitments of Traders weekly report
     due_in_days: 42
```

**The being took the permission and not the example.** The prompt showed it a
six-week claim and told it the ceiling was a year; it has never once written
anything under four months. `claim_refusals` holds **0 rows** — the door has
never refused a horizon, because nothing has ever come near the limit. The long
dates are volunteered.

Of 64 claim-door calls in the last 168 hours: **52 declined, 12 opened, 0
refused.**

---

## 1. What that costs, precisely

**It is not only that S1-E is unreadable until December.** That is Decision 6,
taken knowingly on 2026-08-20.

It is that **nothing below the door has executed once in life.**
`workable_claims` selects `status='open' AND due_at <= now`, so with no claim
due, `resolve_claim` has never been called. Unexercised, in life, as of today:

- the fetch of a world source and the VERBATIM quote check (INV-047);
- the 4-attempt honest-failure path that leaves a claim open (E1.3);
- the cost that reaches the position through INV-031 (E1.4) — `claim_costs` is
  empty;
- the release of a position that keeps being wrong, through INV-025;
- the one episode a resolution writes, provenance `world`, which is the only
  way sleep ever sees any of it.

All of it is tested. None of it has run. `research=True` is live in
`run_newz.py`, so nothing else is blocking it — only the dates.

**Four months is a long time to wait to find a bug.** The writing rhythm shipped
on 2026-08-20 and its re-read path crashed on the first attempt that had
anything real to do — `work_attempts` #6, `XMLExtractionError: XML parse error
in <review>`. That is the ordinary cost of a path that has never run. Phase 1's
path is five times larger and its first execution is scheduled for December.

---

## 2. The change

Three lines, in `newz/resolutions/door.py`.

| | From | To |
|---|---|---|
| `MAX_HORIZON_DAYS` | 365 | **45** |
| the prompt's stated range | `between 2 and 365` | `between 2 and 45` |
| the prompt | — | **one new instruction, below** |

The instruction, placed with the other guidance on `due_in_days`:

> **Reach for the nearest source that will have spoken.** If what I hold is
> right, something small should be observable soon — not only at the end. A
> thesis about where a market or a rule is going has interim checkpoints: the
> next weekly release, the next monthly print, the next scheduled filing. Claim
> the nearest one that would still surprise me if it went the other way. A claim
> I cannot bring inside the window is usually a claim about the wrong
> observable, not a claim that needs longer.

Nothing else. No new table, no new metric, no new refusal reason — the
out-of-range refusal already exists and already records its reason.

**The worked example does not change.** It is already 42 days and already models
the behaviour wanted; it was simply outvoted by a permitted range eight times
larger.

**The twelve live claims stand.** There is no unsettle (E1.1) and the operator
re-dating the being's own commitments would be a worse thing than waiting.

---

## 3. What it is expected to do, and the falsifier

**Expected.** Claims open at horizons the resolver reaches inside weeks. The
first execution of `resolve_claim` in life moves from **2026-12-18** to roughly
**early October** — sooner if the being finds a weekly or monthly source, which
the prompt now asks it to. S1-E becomes readable in October rather than
December, and then repeatedly, rather than once.

**The falsifier, stated before it runs.**

1. **Within 14 days**, at least one claim opens with a horizon ≤ 45 days, and
   horizon refusals are a *minority* of door calls. `claim_refusals` is 0 rows
   today, so any nonzero count is unambiguous and needs no baseline.
2. **If instead** `claim_refusals` fills with horizon reasons and `claims_opened`
   falls below its current rate, the cap is wrong for this being's subjects —
   **revert to 90**, not to 365, and record which subjects could not reach a
   near source.
3. **The read**, ~60 days out: `resolutions.attempts > 0` on any row. If the
   resolver executes and fails for a reason that is not *the source did not
   say*, that is the finding and it is worth the whole change on its own.
4. **S1-E**, mid-October: `positions_changed_by_world` > 0.

---

## 4. Red team

**R1 — a cap produces refusals, not shorter claims.** The door refuses an
out-of-range horizon and does not ask again; there is no second attempt in
`propose_claim`. So a hard 45 does not convert a 180-day claim into a 45-day
one — it converts it into a `claim_refusals` row and nothing else. If the
being's subjects have no source that speaks inside 45 days, consequence goes
from December to never. **This is the serious objection.** *Decision:* the
prompt is what does the work and the cap only enforces it, so the two ship
together and never separately; and falsifier 2 reads within the week rather than
at the next digest.

**R2 — 45 is the weakest number here.** What speaks inside 45 days: weekly
releases (CFTC COT, EIA inventories, jobless claims), monthly prints (BLS, CPI),
and the next quarterly filing only if it happens to fall near. What does not:
annual reports, most regulatory deadlines, academic publication. The being's
current pool is AI authority, amplification and media regulation — subjects
whose natural sources are quarterly transparency reports (~90 days) and
regulatory calendars (annual). **45 may be genuinely hostile to what it actually
thinks about.** *Counter:* a subject with no near observable is a subject on
which it cannot learn this year, and the honest answers are a nearer proxy or a
decline — it already declines 81% of the time and declining is free. *Recorded
as the number most likely to be wrong.*

**R3 — this buys shallower claims.** A claim about next month's print is cheaper
thinking than a claim about a structural thesis, and INV-031 charges the
position either way, so the cost may land on something more trivial. *Counter:*
the current alternative is a deep claim that costs nothing for a year, and
`could_be_wrong` is already the check on whether a claim is a claim.
*Recorded.*

**R4 — it does not make S1-E readable now.** The twelve stand, so the earliest
S1-E can be read is one new horizon from today — early October, not this month.
The gain is ten weeks and, more importantly, repetition: one settlement in
December is an anecdote, and a settlement every few weeks is a loop.

**R5 — it collides with `more-cycles`.** That proposal opens the claim cap to
unlimited and raises the door to 8/day. With 45-day horizons, claims stop
accumulating harmlessly and start *coming due in volume* — which turns that
proposal's own R5 (unbounded intake against a permanent failure state) from
latent into live, months earlier than it would otherwise arrive. The resolver
attempts one claim per cycle with 20h spacing per claim and stops after 4
failures. *Decision:* **this change lands first and alone.** If both are wanted,
`MAX_OPEN_CLAIMS` does not go unlimited in the same week.

**R6 — the horizon was never the being's fault.** R-31 already found the schema
compelling a fabrication once, and the fix was to ask for a horizon rather than
a date. This is the same shape one layer up: the field is answerable, and the
range told it that a year was a normal answer. That is a prompt defect, and it
is worth saying that the being has done nothing wrong here either time.

**R7 — same hand wrote the finding, the change and this red team.**

---

## 5. The decision asked for

1. **The cap at 45**, with 90 as the recorded revert target and 365 not
   returning.
2. **The prompt instruction**, shipped in the same change as the cap (R1).
3. **The ordering**: this before `more-cycles`, and `MAX_OPEN_CLAIMS` not made
   unlimited in the same week (R5).
