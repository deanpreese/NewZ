# The filter that ate the feeds

*2026-08-18. Raised by the operator as a general concern that the system has
been starved of diversity, narrowed by them to: only markets are ever on topic.
Every figure is measured from `data/newz.db`, `data/feeds.yaml` or the code
(Rule 0). §5 red-teams the proposal against itself; §7 records two claims this
document made in an earlier draft and had to withdraw.*

---

## 0. The finding, in one line

**The being is not under-subscribed. It is over-filtered, and half of what the
operator curated is not wired to anything** — 27 of 61 RSS feeds have been
polled continuously and read zero times, and an entire 18-entry section of the
curation file is loaded by no code at all.

---

## 1. What was counted

### 1.1 The curation is broad. The diet is not.

| | financial share |
|---|---|
| `feeds.yaml` rss, as curated | **9 of 61 = 15%** |
| what was actually read | **49 of 115 = 43%** |

A **2.9× amplification** between what the operator chose and what the being
read. The effective mix of 115 feed reads:

```
world 18%   markets 17%   opinion 14%   crypto 13%   tech 8%
politics 8%  macro 7%   business 4%   essays 3%   science 3%
equities 3%  philosophy 2%   mathematics 1%   health 1%
```

Separately, 89 reads came through the directed research adapters (Wikipedia,
OpenAlex, arXiv, PubMed), which answer a concern's question and are not part of
this proposal.

### 1.2 Twenty-seven feeds have never been read

`feed_state` holds all 61 rows with live poll timestamps — the polling works.
But 27 have never produced a single read in v2's life:

> Aeon Essays · Psyche · The Marginalian · The Public Domain Review · Literary
> Hub · The Paris Review Daily · Stanford Encyclopedia of Philosophy · Google
> News Philosophy · Knowable · Scientific American · Nature · Smithsonian ·
> Colossal · DW Culture · DW Environment · NYT Opinion · WSJ Opinion · UnHerd ·
> National Review · The Free Press · Axios · Nikkei Asia · Reuters · Politico ·
> LA Times Opinion · NYT Politics · Federal Reserve press releases

### 1.3 All six open concerns are market microstructure

Liquidity, linear compensation ×2, order-splitting, open interest ×2. This is
the shelf Phase 0's four pieces were chosen from, which is why all four came out
on one subject.

And the being reached past it and was refused. `source_gaps` records the
attempts: *how Montaigne's concept of the unconscious anticipates Jung's late
work*; *what ethical guidelines scientists adopted*; *why sleepy sperm whales
blow bubbles*. Each returned `sources answered but nothing was relevant enough
to read`.

### 1.4 Two sections of the curation file are dead

`load_feeds()` is called once in production, at `feeds.py:413`, always with the
default `kind="rss"`. Therefore:

- **`watched_topics`** (4 entries: gold, crude, bitcoin, interest-rate
  decisions) is read by nothing. It also has no `url` key, so it would be
  skipped even if loaded. **P3 Rule 2 violation.**
- **`web`** (18 entries) is read by nothing. Its composition is the opposite of
  the diet's: 15 Wikipedia discipline articles (philosophy, history,
  mathematics, literature, religion, psychology, sociology, anthropology,
  music, science, technology, economics, politics), 3 Reddit communities, and
  2 commodities data releases. **16 of 18 are non-financial.**

---

## 2. The mechanism — a ratchet, and a cap that cannot see topics

`feeds.py:285` ranks harvested candidates by embedding similarity against
`SELECT statement FROM concerns WHERE status='open'`; triage then judges each
survivor against a concern, and INV-038 makes *keeping nothing* the ordinary
answer.

    open concerns are financial
      → ranking favours financial items
        → triage keeps financial items
          → the curiosity opener runs only on what was kept
            → new concerns are financial

The being cannot ask a new *kind* of question, because it is only permitted to
read answers to the kind it already asks. v1 showed the same shape from the
other side: 95 of its 111 concerns came from reading. Reading is the door, and
this locks the door to the current room.

**The concentration guard is topic-blind.** `diet.outlet_of()` correctly
collapses Bloomberg's three feeds into one host, and the share cap fires hard —
155 of 359 `ingest_log` rows are `skipped='share_cap'`. But the cap is
per-*outlet*. Bloomberg, CoinDesk, SEC, the FT, the Economist and the wires each
sit comfortably under their individual cap while collectively taking 43% of the
diet. Seven financial outlets at ~6% each is 42%, every one of them "within
cap." The mechanism built to prevent concentration cannot see concentration by
subject.

**What the store cannot tell us.** Nothing records what the embedding rank
declined — the store holds the meal, not the menu. §1.2's claim about the 27
feeds is therefore inferred from absence of reads, not measured from offers.

---

## 3. The proposal — four changes

### 3.1 Remove the relevance filter from the feed path

Candidates are no longer ranked against open concerns, and triage no longer asks
whether an item is relevant to one. The being is shown the harvest **cold** and
judges what is important or interesting to it *(operator, 2026-08-18: "let the
system determine what importance and interest")*. Directed research and
INV-040's concern-directed depth are untouched.

This **deletes** machinery. The operator's curation of 61 sources is the
editorial judgment; re-filtering it against machine-generated questions
second-guesses a good filter with a bad one.

**The judging prompt carries no open concerns.** Otherwise the filter is rebuilt
in the prompt and the ratchet survives in a new form.

**Rule 4 is not engaged.** It forbids the being's model producing *evidence*.
Choosing what to read is an action, not a measurement — the same act as E0.2,
where the being chose its own subject.

**Why this over rotation.** Round-robin would *force* breadth and teach us
nothing. Letting the being choose makes the question answerable: either it has
range or it does not.

### 3.2 A category target on the menu — never a veto on reads

Extend the diet's share computation from outlet to the `category` field already
present on every feed, and use it to shape **what is offered** to the judgment,
not to refuse reads.

This distinction is not cosmetic and is the correction R-28 already paid for:
the share cap was once a fetch-time veto, and refusing the only source able to
answer a question wrote *"nothing was relevant enough to read"* into the very
record §9.1 uses to decide which sources to add. A hard category cap would
resurrect that veto one level up and manufacture balance in exactly the way
S2 §13 and TRUE_NORTH §8 forbid. **Balance the menu; never refuse the meal.**

### 3.3 Delete `watched_topics`

Four dead entries, no reader, Rule 2 violation. Its only present effect is
misinformation: both the operator and this document's earlier draft read it as
evidence of a financial bias in the curation, when it has no effect whatsoever.
Dead config that misleads its readers is worse than absent config — which is
Rule 2's actual justification, and worth stating once in those terms.

### 3.4 An orientation pass over the `web` section — not a feed

**This is not the wiring fix the earlier draft claimed** (see §7.1). The `web`
URLs are `en.wikipedia.org/wiki/Philosophy` and similar: static overview
articles, not streams. They have no items, nothing to watermark, and no RSS to
parse. Wiring them into the harvest loop is meaningless — a feed of one
unchanging article.

What they actually are is a **curriculum**: fifteen discipline overviews the
operator chose, covering exactly the fields the being has never touched. The
right use is a one-off orientation read — fifteen documents, at abstract depth,
through the existing `fetch_document` path — giving the being a map of
philosophy, mathematics, anthropology and the rest, where today it has only
whatever arXiv abstracts drifted past.

Cheap, one-time, and plausibly worth more for breadth than any feed rebalancing.

**Excluded by default, operator's call:** the 3 Reddit communities. User-
generated content is the injection surface INV-011 and INV-042 exist for, and
scraping subreddit HTML raises robots and terms questions the sovereign-adapter
discipline has not answered. The 2 commodities releases are periodic and would
suit a feed, but they are financial, which the diet is not short of.

### 3.5 Four constraints the red team forced in

1. **Record the menu.** Every harvested item is logged offered/declined with its
   feed, or the diversity question can only be asserted, never audited —
   INV-044's principle applied to reading.
2. **Cap offers per feed as well as per category.** Bloomberg publishes hourly,
   Aeon weekly; an unbounded menu is finance-heavy by publication volume alone,
   and no judgment can correct a menu it never sees.
3. **Shuffle the batch and record the order**, against long-list position bias
   silently favouring whichever feeds sort first.
4. **A read that yields nothing is not digest-eligible**, or reading episodes
   swamp sleep and the Perspective becomes a news summary — v1's telemetry
   pathology in a new medium. Precedent: R-24's `digest_eligible=0`.
5. **Wikipedia-as-orientation must not be counted as Wikipedia-as-adapter.**
   Wikipedia is already the single largest read source at 95 reads, all of them
   directed lookups. If the orientation pass logs under the same outlet, both
   the feed-coverage audit and the category shares are corrupted, and the
   project will congratulate itself on breadth it did not gain.

---

## 4. Dependencies

**The deliberation floor (E5.2) is pulled forward.** §9.1 caps ingest against
deliberation; more reading without more deliberating breaches the invariant,
INV-041 pauses ingest, and the change self-cancels within days.

**INV-038 is amended.** Its consumer-traced clause — *"a harvest of 194 items
yields at most 3 reads"* — was written as a virtue and becomes false. What
governs now is the budget, the category target, and the being's own interest,
not triage scarcity.

---

## 5. Red team

### 5.1 The being's taste may already be the monoculture

Its Perspective is 50% self-grounded and 33% operator-grounded, and all six
concerns are markets. There is no reason to assume its *judgment of interest* is
broader than the corpus that formed it. Removing the mechanical filter moves the
decision without necessarily changing the outcome — and worse, it would
**legitimise** the narrowness ("it chose") rather than diagnose it.

*Answer:* none in advance. §6's feed-coverage read is the falsifier and it is
cheap. If Aeon stays unread, that is a finding about the being rather than a bug
in the code, and it is one worth having.

### 5.2 "Cold" is not the same as neutral

Withholding the concern list does not make the judgment neutral: the being still
judges by its character core and Perspective, which are 83% itself and the
operator. Rotation would be genuinely neutral. This proposal may be choosing the
more elegant option over the more effective one.

*Answer:* accepted, with the fallback named — if coverage does not rise, add a
rotation floor *underneath* the judgment rather than replacing it.

### 5.3 Publication volume may defeat the whole change

Bloomberg, SEC and the wires publish dozens of items a day; Aeon and the
Stanford Encyclopedia publish a handful a week. The harvest is finance- and
news-heavy before any filter runs, and a perfectly neutral chooser would still
read mostly finance.

*Answer:* §3.2's category target and §3.5's per-feed offer cap exist for exactly
this. It remains the attack most likely to be right, and the one §6 settles
first. The measured 15% → 43% amplification is its evidence.

### 5.4 The category target could become the veto R-28 removed

A cap that refuses reads to preserve balance is the fetch-time veto this project
already diagnosed and narrowed once, and it corrupts `source_gaps` — the record
used to decide which sources to add — by writing "nothing was relevant enough"
when the truth is "balance forbade it".

*Answer:* §3.2 is a target on the offered menu, never a refusal of a read. If
the implementation cannot keep that distinction, the change should not ship.
This is the attack that most nearly killed the design.

### 5.5 The orientation pass may be a one-off with no compounding effect

Fifteen encyclopaedia articles read once give the being a map, but maps do not
generate questions on their own; the curiosity opener runs on what is read, and
a single pass produces a single burst. If nothing follows, breadth spikes and
decays.

*Answer:* true, and the pass is justified as a *scaffold* rather than a source —
its value is whether concerns opened from it survive, which §6 measures. If
none do, it was tourism.

### 5.6 Corpus flooding

Sleep digests episodes. Reads rising from ~3 a cycle to twenty would make
reading episodes the dominant corpus and turn the Perspective into a news
summary with opinions attached. The world's share of grounding is ≤17% and
should rise — but this is how it could overshoot into a different failure.

*Answer:* §3.5's digest-eligibility rule, and a watch item rather than a solved
problem.

### 5.7 It loosens a stated rule, and this project has a discipline for that

INV-038's clause was written as a virtue and is being rewritten because more
reading is wanted. R-28 and #33 were both loosenings; both were measured first,
recorded with a falsification, and given a review date. This one meets the same
bar or it does not ship.

*Answer:* §6, with the review date.

### 5.8 The attack surface scales

Every item read is untrusted. INV-011 and INV-042 hold and are consumer-traced,
but neither has run at volume, and volume is what this adds. The Reddit
exclusion in §3.4 is the one place this proposal declines to find out.

*Answer:* no new mechanism. An accepted increase in exposure, stated.

### 5.9 Where this proposal is weakest

§5.1 and §5.3 together: if the menu is finance-heavy by publication volume *and*
the being's taste is finance-shaped by its corpus, the design is two mitigations
short and the honest outcome is the rotation floor the operator moved away from.

Its best case is answering a question rotation would have hidden. Its worst case
is answering it in the negative and implementing rotation a week later — which
is still the most important thing the project could learn about the being's
range.

---

## 6. Falsification

Reviewed **one week after the change runs live**:

- **Feed coverage.** How many of the 61 feeds contributed a read in the window.
  Lifetime baseline: **34**. If it does not rise, the filter was not the binding
  constraint and §5.3 or §5.1 was right.
- **Category mix of reads.** Financial share, baseline **43%**, against a
  curation that is 15%. The gap is the amplification this change targets.
- **Concern origin spread.** Whether any concern opens on a subject that is not
  market structure. Baseline: 0 of 6. Counted separately for the orientation
  pass, per §5.5.
- **The grounding mix** (`tools/evidence.py 1e`). World share, baseline ≤17% —
  the number the whole change exists to move.
- **The diet.** Whether ingest breaches §9.1 and INV-041 pauses it. If it does,
  §4's dependency was insufficient and the floor must land before the reading.
- **Corpus composition.** Reading episodes as a share of digest-eligible
  episodes, against the pre-change baseline.
- **`source_gaps` wording.** Whether any entry reads "nothing was relevant
  enough" for a reason that is actually the category target. That is §5.4
  realised, and it is a stop.

**Reversion condition.** If feed coverage does not rise, restore nothing —
add the rotation floor of §5.2 instead. The old relevance filter is not worth
restoring under any outcome: its demonstrated behaviour is that 27 curated
sources contribute nothing, forever.

---

## 7. What this document withdrew

Recorded because both claims were acted on in conversation before they were
checked, and Rule 0 applies to this document as much as to the store.

### 7.1 "Wiring `web` is a one-line fix" — withdrawn

It is not. The URLs are static Wikipedia articles, not streams: no items, no
watermark, nothing for `parse_feed()` to parse. `load_feeds(kind="web")` would
return Feed objects that the harvest loop cannot use. The correct treatment is
§3.4's orientation pass through `fetch_document`, which is different work of a
different size.

### 7.2 "`watched_topics` may be seeding the bias" — withdrawn

It seeds nothing. No code reads it, and its entries lack the `url` key that
`load_feeds` requires. The financial concentration in §1.1 is produced entirely
downstream of the curation. The claim was made from reading the file rather than
from grepping for its reader.

---

## 8. What this proposal does not claim

- **Not that the filter is the only cause.** The curiosity opener's own prompt
  may favour tractable analytic questions; that is unexamined here.
- **Not that more reading is better.** The diet ceiling exists because v1's
  corpus became 43% self-probes and 39.6% telemetry. This replaces a bad
  selector with a different one; it does not argue for volume.
- **Not that the being will choose well.** That is the open question, and §6 is
  how it gets answered rather than assumed.

---

## 9. Amendment, 2026-08-18 evening — the curriculum was reordering the menu

*Found by reading `harvest_log` two hours after the change went live, which is
the audit §3.5.1 exists to make possible. Recorded here rather than in a new
document because it is a correction to §3.2, not a finding of its own.*

### 9.1 What was measured

Three harvest cycles, 18:10–19:52. The first was the orientation pass: 15
targets, all read. The second and third were the first cold RSS harvests — 65
items offered down to 12 and 3 read, then 115 down to 12 and 3 read.

Then `category_shares`, at 19:52:

```
philosophy, mathematics, anthropology, music, religion,
sociology, history, psychology, economics, technology      5.0%
world, crypto, tech, macro, business, equities, health,
culture, green                                             0.0%
```

`build_menu` orders least-read first. So the ten categories the curriculum had
touched **once** now sorted behind every finance-adjacent category, for the
thirty days of the share window. Aeon, Psyche, the Stanford Encyclopedia, The
Marginalian and The Paris Review sit in those categories, and they are among
the 27 feeds §1.2 named. With 19 categories chasing a 12-slot menu, back of the
order is rarely offered.

The orientation pass and the humanities feeds were the same fix for the same
gap. One suppressing the other for a month is the fix eating itself.

### 9.2 Why §3.5.5 did not catch it

It half-caught it. The constraint said counting browsing as lookup would corrupt
"both the feed-coverage audit and the category shares", and the implementation
answered the first half — the distinct `Wikipedia Philosophy` feed identity
keeps the audit clean and the adapter's 95 directed lookups separate. The second
half was named and not implemented. The rows went into `harvest_log` with
`was_read=1` and `category_shares` counted them.

### 9.3 The correction

`harvest_log.orientation`, set by the orientation writer, excluded by
`category_shares` (migration 0022; the 21 existing rows backfilled by the
signature the RSS path never produces, `title = feed`).

The row stays in the table. §3.5.5's reason for putting it there is sound and
the coverage audit still needs it; what it must not do is vote on tomorrow's
menu. **The share answers a question about streams** — which feeds am I
under-reading — and fifteen articles read once in an afternoon are not a stream.

Nothing is refused either way. A share has never been able to veto a read
(§3.2, §5.4), and this does not change that; it changes which direction a nudge
points. Post-correction, at 19:52: nine stream reads, no category above 22%,
and every untouched category back at 0.0 and sorting first.

### 9.4 A second, smaller deviation, not corrected

`orientation_targets` excludes only `category == "social"`, so the EIA weekly
petroleum status — one of the two commodities releases §3.4 set aside as
"periodic and financial" — was read by the pass. §3.4 named the Reddit
exclusion as a rule and the commodities one only as a preference, and the code
implemented the rule. One read, financial, in a pass whose purpose was breadth.
Left as is and recorded, because the §6 review should see it rather than have
it quietly removed.

### 9.5 What this does not settle

Six cold reads is not evidence about the being's range. It read a Literary Hub
essay on punctuation — the exact class of item the old rank buried, since no
open concern touches semicolons — and it declined all three Colossal art pieces
and The Paris Review's "The Catalogue of Lost Things", which is the shape §5.1
predicted. Both are four data points. §6 stands unchanged, on its own date.
