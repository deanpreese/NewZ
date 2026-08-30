# The quote it could not point at

*2026-08-30. The first claim this project has ever settled was settled on a
sentence its source does not contain. The outcome may well be right, and that
is what makes it worth stopping for. §5 is the red team and it argues the fix
could take S1-E from one to zero and keep it there.*

---

## 0. The claim under test

Whether INV-047 — *a verdict is accepted only if its quote occurs VERBATIM in
what was fetched* — is doing what it was written to do.

It was written for one purpose, stated in the code: *"The Stanford CRU lesson,
applied to being right. A verdict the material does not contain is the model's
opinion wearing the world's clothes, and Rule 4 forbids exactly that."*

## 1. What happened

At **11:32:45** claim 32 settled `held` — the first settlement in the project's
history. The mechanism ran end to end: due, fetched, extracted, judged,
verbatim-checked, settled, and the one `resolution` episode written with
provenance `world`.

**The claim:**

> countries suspending the gold standard in 1931 or earlier (e.g., UK, Sweden,
> Germany) experienced a **statistically significant** earlier recovery in
> industrial production or price levels compared to countries remaining on the
> standard until 1933 or later (e.g., US, France, Belgium) between 1931 and 1933

**The quote that settled it,** recorded in `settled_note`:

> Countries that suspended the gold standard in 1931 or earlier (specifically
> citing the UK, Sweden, and Germany) experienced a **statistically
> significant** earlier recovery in industrial production or price levels
> compared to countries remaining on the standard until 1933 or later
> (specifically citing the US, France, and Belgium) between 1931 and 1933.

That is the claim with `(e.g.,` swapped for `(specifically citing`.

**What the source actually says.** `settled_by` is Wikipedia's *Great
Depression*. Fetched today through the being's own `fetch_document`:

```
statistically significant   ABSENT
Sweden                      ABSENT
earlier recovery            ABSENT
gold standard               present
Belgium                     present
```

> *"Britain, Argentina, and Brazil, all of which devalued their currencies
> early and returned to normal patterns of growth faster than countries that
> stuck to the gold standard, such as France or Belgium."*

**So the substance is broadly supported and the evidence is manufactured.** The
article makes a qualitative statement about Britain, Argentina and Brazil
against France and Belgium. The settlement asserts a *statistically
significant* result about the UK, **Sweden** and Germany against the US, France
and Belgium. The direction is right. The statistical qualifier and half the
countries were supplied by the question, not by the world.

## 2. Why the gate let it through

`resolver.py:210`:

```python
material = "\n".join(f"- {t}" for t, _ in found.claims)
...
if not quote or _normalise(quote) not in _normalise(material):
```

**`material` is not the document.** It is the list of assertions the extractor
produced. And `extract_claims` is called with `question=query` — the claim
itself — under `_DIRECTED`: *"Extract only claims that BEAR ON that question."*

So the chain is:

1. the extractor is shown a page and asked what it says **about this claim**
2. it emits an assertion phrased in the claim's own terms
3. the verdict quotes that assertion
4. the verbatim check compares **the model's paraphrase against the model's
   paraphrase**

The gate written to stop *"the model's opinion wearing the world's clothes"*
compared the model to itself. Rule 4's exact prohibition, one indirection deep.

**And it is narrower than "the extractor confabulates."** On 2026-08-29
`resolver_probe --settleable` settled a matched pair 2-of-2 in *both*
directions against an Ars Technica page — because that page plainly said the
thing, so the extractor's assertion was faithful. **Directed extraction
confabulates agreement precisely when the document is silent on the question**,
which is exactly when the verbatim check is the only thing standing.

## 3. What this does and does not mean

**S1-E is not met and is not closer.** It needs a position changed *because the
world contradicted it*. This was `held`; no cost applied, `cost_applied_at` is
empty, correctly. INV-031 charges contradictions, not confirmations.

**The mechanism is not broken.** Every stage ran. E1.3's fail-closed paths, the
attempt booking, the episode, all correct.

**The record cannot be corrected.** `resolutions_verdict_is_final` forbids
restating a settled claim, and there is no unsettle — both deliberate, both
right. So the project's first and only settlement is permanently one whose
quote its source does not contain. That is a cost of finding this on 30 August
rather than in December, and it is cheaper than the alternative.

**The outcome being plausibly correct is the danger, not the consolation.** A
wrong settlement would have been caught by reading it. A right-for-the-wrong-
reason settlement becomes the project's first piece of consequence evidence and
nothing objects.

## 4. The proposal

**The verdict is shown the fetched document, and quotes from it.**

`DeepRead` keeps `claims`, `chunks`, `quarantined`, `hostile` — and discards
the body. `ResearchOutcome` has no body field. So today the resolver *cannot*
check against the document even in principle.

- `ResearchOutcome` retains the fetched text per source, bounded by the
  existing `MAX_DOC_CHARS`.
- `resolve_claim` builds `material` from that text rather than from extracted
  claims, so INV-047's check runs against what the world published.
- A document `extract.py` quarantined as hostile contributes no body, exactly
  as it contributes no claims today.

Nothing else moves: the adapters, the floor, triage, the share caps, the
attempt accounting and the fail-closed paths are untouched. The extractor keeps
its job for the ordinary reading path, where directedness is a virtue and no
verdict rests on it.

**One defect to fix in passing:** `settled_by` recorded `wikipedia] Great
Depression` — a bracketed source label echoed by the model and stored raw.

## 5. Red team

**R1 — this could take S1-E from one to zero and hold it there.** The strongest
objection. If a settlement now requires a verbatim sentence from a document,
and the being writes syntheses across a literature, nothing will ever settle.
Against it: the probe settled 2-of-2 on a document that said the thing, so the
constraint does not forbid settlement — it forbids settlement *without a
source*. It pushes toward claims a document can confirm, which is the
claim-shape finding I proposed on 29 August and withdrew for want of evidence,
now arriving as a consequence of a check rather than as a prompt instruction.
**That is a better route to it**, because it cannot be satisfied by rephrasing.

**R2 — is this making the bar higher than the world can meet?** For a claim
about *what a source says*, no: the source says it or it does not. For a claim
about the world that no single document states — most of what the being writes
— yes, and that is INV-047's stated position rather than a new one. If the
operator's judgment is that a synthesis across sources should be settleable,
that is a change to INV-047 and belongs in front of them, not smuggled in
through what `material` happens to contain.

**R3 — untrusted text reaches the DEEP verdict call.** Today the verdict sees
extracted claims, which have passed `extract.py`'s manipulation check. Raw body
text has not. The hostile-document quarantine must gate the retained body or
this widens the injection surface INV-042 exists to narrow. Stated as a
requirement rather than a hope, and it is the part I would build first.

**R4 — cost.** Up to 12,000 characters into one DEEP call per resolution
attempt, against ~2.9s average and 2% machine utilisation. Real and small.

**R5 — truncation.** `MAX_DOC_CHARS` caps at 12,000 and the answer may be past
it. Then the claim fails closed and stays open, which is correct and will look
like the mechanism not working. Worth expecting rather than rediscovering.

**R6 — am I sure the fault is extraction rather than the verdict?** The verdict
quoted `material` faithfully; `material` was the paraphrase. Both are the same
model, so the distinction only matters for where to fix — and the fix is the
same either way, because it removes the paraphrase from the loop entirely.

**R7 — the objection I cannot answer.** If, with the document in front of it,
the model still produces quotes that pass a normalised substring check while
misrepresenting what the document meant — a real sentence, lifted out of a
context that reverses it — then verbatim matching was never the guarantee it
looked like, and INV-047 needs a different kind of check entirely. Nothing in
this proposal would catch that. Recorded now so it is checked then rather than
rediscovered.

---

**Schema:** none.
**Restart:** yes — `research.py` and `resolver.py`.
**Class:** one retained field, one changed input to a check that already exists.
