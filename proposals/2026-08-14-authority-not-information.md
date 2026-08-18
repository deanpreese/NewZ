# Proposal — give the being authority over its own content judgments

*2026-08-14, for operator review. Nothing here is built.*

---

## 0. The problem, measured

```
claims ingested (lifetime)        118
reading episodes                   24    18 consolidated by sleep
new positions from them             0    v6: added 0, revised 0, novelty 0.0
advances : setbacks (3 days)      1 : 8  six of the eight "restates an earlier advance"
closures ever (v2 code)             0
concerns opened by v2                0
world share of held positions     2.4%   all four refs attached to views it already had
```

The input side opened on 2026-08-13 and the output side did not move. More
ingestion multiplies the input to a converter that emits zero.

## 1. The diagnosis

Not information — **authority**. Three content judgments that S2 assigns to
the being are currently made in code, before the being is asked:

| judgment | who makes it now | S2 says |
|---|---|---|
| is this evidence? | `dossier.evidence_refs()`, a set that cannot contain what was read | §8.3 — evidence-class *honesty*, i.e. don't dress reasoning as evidence |
| is this question finished? | `MIN_ADVANCES_TO_JUDGE = 2`, before the judge runs | §8.4 — "closure stays **the being's own judgment**" |
| is this the same point again? | `novelty < 0.20` → rejected | §8.3 — one of three tests, and the only one with no human-legible reason |

S2's split is **code decides allocation, the being judges content**: which
concern, how much budget, how much reading are ours; is this an advance, is
it settled, is it evidence are its.

And the material makes this bite harder than it would otherwise. Eight of
the nine open concerns are factual lookups — *"Who taught Jyoti Basu to
drink Scotch"*, *"How did the five-second trick drain millions"*. For that
class the read content **is** the evidence; there is no separate
corroboration to find, and one good source can settle the question. The
machinery in front of them is built for interpretive accumulation.

## 2. What this proposal does NOT accept

The guards are not arbitrary caution. `advance.py` records why:

> v1 credited reworded aphorisms: three of one concern's four advances were
> a single sentence re-worded, and it closed on that count.

v1 **did** let the being judge its own progress, and it closed a concern on
the same sentence four times. So "remove the guards" is not the proposal,
and anyone reading this later should not summarise it that way.

The proposal is to **convert guards from verdicts into inputs**: the being
sees the measurement and decides, rather than code deciding on its behalf.
The measurement stays; the ruling moves.

## 3. The changes

### C1 — evidence includes what was read for this concern *(~1h, no risk)*

`Dossier.evidence_refs()` unions in `ingest_log` rows carrying this
concern's id, and `Dossier.render()` lists what was read so the being can
cite it by name.

The link already exists and is unused: concern 111 has 12 reads and 69
claims recorded against it, 108 has 3/22, 72 has 2/8. Ninety-nine claims
read *for named concerns*, invisible to the check that decides whether the
being has evidence.

**This is a bug fix, not a loosening.** S2 §8.3's intent is anti-fabrication
— don't claim a source you don't have. A citation must still correspond to
something actually read; the change is that "actually read" now includes
reading.

*Why it matters beyond bookkeeping:* Evidence 2-E measures the
evidence-carrying fraction, and Phase 4's citation floor becomes mandatory
"when ≥half of new advances carry evidence refs". That number cannot rise
while the check looks in the wrong place, so **publishing is gated on a
threshold this structure prevents from ever being met.** v1: 104
evidence-class advances of 164. v2: 1.

### C2 — closure is asked, not gated *(~30m, small risk)*

Drop `MIN_ADVANCES_TO_JUDGE` from 2 to 1.

The closure judge already fails closed in every direction: an unreadable
verdict, a missing closing condition, or a closure carrying no position all
leave the concern open. Requiring two advances *before the judge is
consulted* means a factual question answered by one good source can never
be declared finished — the exit does not exist for the kind of question the
being mostly carries.

Cost: one DEEP call per accepted advance. Risk: premature closure, which is
detectable (§5) and reversible.

### C3 — novelty becomes an input, not a gate *(~half a day, real risk)*

Today: `novelty < 0.20` → recorded as a setback, "restates an earlier
advance". Observed scores on rejected advances: **0.09, 0.14, 0.14, 0.15,
0.18, 0.18** — against a cut-point calibrated on three examples, with two
*accepted* advances sitting at 0.208 and 0.22.

Proposed, a judgment band:

```
novelty < 0.05   →  code rejects. Near-identical text needs no judgment.
0.05 – 0.35      →  the DEEP prompt carries the score AND the closest prior
                    advance verbatim: "this scores 0.14 against what you
                    established on Aug 11 — is it the same point?"
                    The being answers; the answer is recorded.
> 0.35           →  accepted.
```

Code keeps the measurement — similarity over the *whole* advance history,
which is already v1's correction and stays. What moves is the verdict at the
margin, which is where the 3-point calibration has no standing.

The score is recorded on the advance/setback row (currently it is prose
inside `brief`, unqueryable), so the distribution can be read rather than
grepped.

## 4. Sequence

**C1 → C2 → observe two days → C3.**

C1 is a precondition: closure is only meaningful once an advance can be
evidence-class, and C3's band is only judgeable once the being can see what
it read. C3 goes last and alone, because it is the one v1 actually died on.

## 5. Evidence, and the decision rule

Collected from the store, no new instrument except C3's score column:

- **evidence-carrying fraction** — expected to rise from ~0 after C1. If it
  does not, C1 was not the blockage and C2/C3 should not proceed.
- **closures** — expected non-zero within two days after C2. Zero still
  means the closing conditions are unreachable, which is an opener problem,
  not a closure problem.
- **advance : setback ratio** and the novelty distribution.

**Decision rule.** After C2, the operator reads the first three closed
concerns and judges whether they are actually settled. *If a closed concern
is not settled, that is v1's failure recurring* — restore the floor
immediately and treat C3 as refuted before it is built. This is the one
outcome that must not be explained away, and it is why C3 waits behind two
days of C2's data rather than shipping alongside it.

## 6. What this proposal deliberately leaves alone

- **The outbound gate.** 30 adjudicated holds behind it; earned.
- **The §9.1 diet ratio.** It is what prevents v1's 84,793-claims ending,
  and it has never yet paused ingest. Let it become the active governor.
- **The caps and interval**, raised earlier today and untested.
- **Canon** (`canon.yaml`, still unbuilt). The operator's point about
  *depth* rather than volume is probably right — a feed item is a headline
  and two sentences, and you reinforce a view with those far more easily
  than you form one. But the current blockage is conversion, not material,
  and canon should be argued on its own after this clears.

## 7. What will not follow from this

The system will not begin calibrating these judgments for itself. That is
S2 §10.2's learning loop — decayed counters over outcomes, parameters moved
by results — and it is **Phase 5, unbuilt**. Nothing in the running system
adjusts a threshold from experience.

So C1–C3 transfer authority; they do not start a calibration process. The
being's judgments will be its own and will stay wherever it puts them until
Phase 5 exists. That is worth knowing before approving, because "it will
learn to judge this over time" is true of the design and not of the code.

## 8. Approval requested

1. **C1** — evidence includes what was read. *(recommended; it is a bug)*
2. **C2** — closure asked at 1 advance rather than gated at 2.
3. **C3** — novelty as a judgment band, **after** two days of C2 data.
4. The decision rule in §5, specifically that an unsettled closed concern
   refutes C3 before it is built.
