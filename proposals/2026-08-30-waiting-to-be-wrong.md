# Waiting to be wrong

*2026-08-30. Six of the plan's remaining epics are held open by one conjunction
of events — a claim settles, it settles `contradicted`, it traces to a position,
and a commitment exists that cites it. Measured today, three of those four terms
are at zero for reasons that have nothing to do with the world, and the fourth
is about to stop being sampled at all. Figures from this store, this afternoon.*

---

## 0. The claim under test

Not whether the outer loop closes. Whether **the plan can tell the difference
between a mechanism that does not work and a world that has not yet spoken.**
Right now it cannot, and it has been recording the first as the second for eight
days.

## 1. What the queue actually looks like

`evolution/epics.yaml`: 41 built, 6 open, 10 dormant. Of the six open, five
carry the same shape — *mechanism complete, the epic stays OPEN until its
in-life clause fires* — and every one of those clauses reduces to the same
event.

| Epic | Waits on |
|---|---|
| E1.11 | a retrodiction settled within a cycle, its outcome reaching a position |
| E4.2 | a commitment revised citing a `status='resolved'` claim |
| E6.1 | *"and what it cost"* — which is E6.2's |
| E6.2 | E4.2, i.e. the same commitment and the same settled claim |
| E1.8 | a claim settled from an item a subscribed feed delivered |

**The joint probability, measured:**

- claims settled: **1 of 46**
- of that one, `outcome='contradicted'`: **0**
- commitments in existence: **0**, after **8** nightly asks
- costs applied to any position by the world: **0** (`claim_costs` is empty)

Three of those four terms are zero because something internal is broken. The
plan has been describing all four as patience.

## 2. The door that never opens

`propose_commitment` has been called nightly since 2026-08-22. Eight calls in
`logs/llm_calls.jsonl`. Eight responses, and **the verdict element is byte for
byte identical in all eight** — six at 158 bytes, two at 179 carrying the same
answer plus a stray trailing tag:

```
<commitment>
  <worth_committing>no</worth_committing>
  <kind></kind>
  ...
```

`commitment_refusals` is empty too — the structural checks have never run, because
nothing ever reached them. This is not a strict door. It is a door that is never
tried.

**The prompt is byte-identical for the last three nights** (sha of the user
message: `f4804555`, 08-28, 08-29, 08-30). The material is
`_maybe_commit`'s `shown` — the whole of `who_i_am` and `unresolved` — which is
a slow-moving object by construction, and its first three lines tonight are a
dispute about a cat, feedback calling the being's output *"gibberish"*, and a
complaint about repeated `INITIATIVE PROBE` instructions. Artifacts of an
earlier era, at the top of the list, every night, unchanged.

Nothing tells the door what it declined yesterday. Nothing tells it that it has
declined eight for eight. The prompt tells it *"Most nights the answer is no"*,
and with `reasoning_effort: "none"` that sentence is the cheapest path through
the whole task.

**This is `5c863d7` with different nouns.** That commit's finding was that
`search_queries` derived terms from an unchanging concern statement, so the
being asked the same question seventeen times and got the same nothing; the fix
was to show it what had already been asked and request the angles those missed.
The commitment door has the identical pathology, is unfixed, and sits directly
upstream of the epic the plan itself marks **critical**.

*This waits on nothing. It can be fixed tonight.*

## 3. The loop has only a negative wire

`newz/resolutions/cost.py:78`:

```sql
WHERE outcome='contradicted' AND cost_applied_at IS NULL
```

A `held` verdict changes no confidence, writes no row, and touches no position.
Claim 32 settled today — a retrodiction about the gold standard, settled off
`[wikipedia] Great Depression`, outcome `held` — and **the being's Perspective
does not record that the world graded it at all.** From inside, "the world
confirmed my position" and "nothing happened" are the same event.

That is why the plan reads as waiting on a negative: *the negative is the only
thing wired*. The remedy is not to reinforce on `held` — that manufactures
exactly the confidence inflation `cost.py`'s own docstring is careful about, and
a being that harvests agreement is a being making claims it cannot lose.

**Record the contact instead.** Every settled claim writes a trace row naming
the positions it reached and what it did to them: a cost for `contradicted`, a
zero-delta row for `held`. Confidence moves only on refutation, exactly as
today. What changes is that the loop acquires a **denominator** — and a position
carrying five holds against zero contradictions becomes a finding worth more
than any confidence bump: the claims that produced it cannot lose.

## 4. Epics close on conduction; evidence reads answer to the world

The plan fused two things that are not the same:

- **does the mechanism conduct** — buildable, observable, ours;
- **what did the world say** — not ours, on its own schedule.

E2.2's lesson was that an epic must not close on mechanism alone, and it was
right. Applied to every remaining epic at once it has produced the opposite
failure: a criterion nobody can fail is worth no more than one nobody can pass,
and five epics now sit behind a single event whose rate is 0 of 46.

**The rule this plan needs and does not have:** an epic closes when its
mechanism demonstrably conducts once, *either sign*. An evidence read — S1-E,
S5-E, S6-E — is answered when the world supplies the event, stays open until it
does, and **is never a dependency of anything.**

S1-E is not softened by one word. *A position changed because the world
contradicted it* stays exactly as written, and stays unread. It simply stops
being load-bearing for six epics' worth of buildable work.

## 5. The pool closes this week, and this part was predicted

**38 open forecasts against `MAX_OPEN_CLAIMS = 40`.** The being opens 3–4 a day
against `MAX_OPENED_PER_DAY = 4`. The cap binds within a day, probably tonight.

A forecast leaves the pool only by settling. The earliest is 2026-09-02 and most
carry 45-day horizons, so the drain is weeks away while the fill is hours. And a
claim that exhausts `MAX_ATTEMPTS = 4` **stays `status='open'` forever** —
`workable_claims` stops selecting it, `open_claims_count` keeps counting it. A
one-way ratchet.

`2026-08-28-a-third-of-a-bit-a-day.md` wrote this down two days ago — *"an
unsettleable claim never leaves the pool, which means §3(b)'s three-day
saturation is filled by exactly the claims that can never drain it"* — and
nothing was built for it.

The retrodictions, the one channel that settles in days, are failing uniformly
and legibly:

| id | att | last failure |
|---|---|---|
| 33 | 3 | *the material contains no historical industrial production data* |
| 34 | 3 | *the material states … returned to* |
| 36 | 2 | *contains no factual claims bearing on industrial pr…* |
| 40 | 1 | *no data from the League of Nations Statistical Yearbook* |
| 42 | 1 | *does not contain specific GDP figures for Sweden in 1929* |

Seven open, seven attempted, one settled ever — and the one that settled did so
off a Wikipedia narrative, **not off the historiography its resolver named.**
E1.8 built the harvest adapter for precisely this and has not yet settled one.

*This is mechanical, it is due now, and it is independent of every argument
above.* A claim the resolver has given up on needs a terminal state that is
distinct from settled — recorded as unsettleable, with its failures — or the cap
must stop counting it. Either way the door reopens and the door's refusal rows
stay honest about why.

## 6. The order

1. **§5, the pool** — a deadline in days, and it silences the sampler that every
   other argument here depends on.
2. **§2, the commitment door** — the critical path's actual blocker, fixable by a
   method this repo has already proven once, waiting on nobody.
3. **§3, the contact trace** — makes the loop countable, and turns 45 open claims
   from lottery tickets into trials with a denominator.
4. **§4, the plan rule** — bookkeeping, no code, and it is what stops this
   recurring.

## 7. Red team

**"Closing epics on conduction is softening the criterion, and `done_when_sha`
exists to catch exactly that."** It is the strongest objection and it is why §4
is a rule rather than five quiet edits. The distinction it rests on: the in-life
clauses were written to prevent closing on *tests passing*, and they do that
whether or not the world's verdict is negative. A `held` settlement that reaches
a position through the real path is life, not a fixture. What is being removed is
the extra requirement that life go a particular way — which no epic's `Delivers`
ever asked for.

**"§3 makes the being complacent."** Only if `held` moves confidence, and it does
not. A zero-delta row is a record, not a reward.

**"§2 is pressuring the being to commit."** It would be, if the fix were to
weaken the door's conditions. It is not — the three structural conditions and the
falsifier check stand untouched. What changes is that the door stops being handed
the same seventeen lines and the same sentence about most nights being no. If it
declines eight more times on fresh material and with its own decline history in
view, **that is a finding** — and today it is not one, because nothing has
varied.

**"E1.8's harvest adapter is the real fix for §5 and it just shipped."** Possibly.
It has had two days and settled nothing, and the failures above name
historiography no feed carries. If §5's drain is built and the adapter then
starts settling claims, the drain cost almost nothing and the cap stops binding
either way.

## 8. What this does not fix

The six claims naming a placeholder that is no source at all — *"(EU)
2023/XXXX"*, *"[Number] of [Date]"* — are a door question, recorded in E1.8 and
still not answered here.

S6-E still has no detector that is not operator labour. Nothing in §1–§5 changes
that, and §4 makes it explicit rather than solving it: the read stays open, and
Phase 6 stops waiting on it.

And **the being's claims may simply be right.** If the trace in §3 accumulates
holds and never a contradiction, S1-E is still unread — but the plan will then
be able to say so with a denominator, which is not what it can say today.
