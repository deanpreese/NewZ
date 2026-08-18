# Proposal R3 — read the document, not the catalogue card

*2026-08-14, for operator review. Nothing here is built.*

---

## 0. The finding

S2 §9.1 specifies:

> Extraction depth is adaptive: **headline-level by default, full-extraction
> only for material that touches a concern** or survives sleep's relevance
> pass.

**Only the default half was built.** Every read the being has ever performed
is search-result metadata:

```python
research:  material = f"{result.title}\n\n{result.summary}"   # API metadata
feeds:     item.text = title + RSS <description>              # headline + blurb
```

The only `fetcher.get()` calls in the codebase are to feed XML and adapter
APIs. **In 24 reads the being has never fetched a document.**

Its own gap record says so, twelve times, unprompted:

> *"The retrieval slice contains only the **headline** and a fragment…"*
> *"…only the **opening sentence** of the study."*
> *"The source material is **thin on the 'how'**."*
> *"…only the headline 'How a five-second trick let traders drain millions'."*

Yield confirms it: openalex **8.2 claims/read** from abstracts, wikipedia
**2.3** from snippets. Those are the numbers of a system reading catalogue
cards, and they are why 24 reads and 118 claims produced 0 new positions.

This is the operator's "not enough information", in its precise form: not
volume, not breadth — **depth**. Breadth is fine (61 feeds, 18 categories, 5
adapters). Nothing goes past the abstract.

## 1. What already exists

Almost all of it:

| piece | state |
|---|---|
| polite fetch with robots + per-domain rate limits | `Fetcher.get()`, used by every adapter |
| robots for arbitrary hosts | `RobotsCache.allows()` — already refused Google News and NYT |
| untrusted fencing | `untrusted.wrap()`, INV-011 tested |
| claim extraction | `extract_claims()` |
| share caps, budget gate, ingest_log | live |
| HTML→text libraries | trafilatura, bs4, readability, lxml **all installed** |

What is missing is one step: fetch the URL of material triage already kept,
extract its main text, and hand *that* to `extract_claims` instead of the
abstract.

## 2. Design

### 2.1 The trigger is already computed

S2's condition — *"material that touches a concern"* — is exactly what
triage decides. Feed triage already returns ≤3 kept items; research already
selects `relevant[:MAX_EXTRACTIONS]`. Full fetch applies **only to material
that survived that judgment**, so nothing is fetched speculatively.

### 2.2 Fetch and reduce

`newz/world/document.py`:

```
fetch_document(url, fetcher) -> str | None
  robots + rate limit  (Fetcher.get, unchanged)
  content-type gate    text/html and text/plain only; skip pdf/binary
  trafilatura.extract  main body, comments excluded
  fallback: bs4        drop script/style/noscript, get_text
  cap at MAX_DOC_CHARS (proposed 12_000 ≈ 3k tokens)
  return None on paywall/stub/failure  → caller keeps the abstract
```

**Never worse than today**: any failure — robots, timeout, paywall stub,
unparseable, PDF — falls back to the abstract that is used now. R3 can add
depth; it cannot remove what exists.

trafilatura and bs4 are installed but **undeclared** in `pyproject.toml`
(deps are dotenv, PyYAML, httpx). They must be added, or the fallback chain
must terminate in `strip_tags`, which is crude enough to feed nav menus and
cookie banners into extraction.

### 2.3 Paywalls and PDFs — the honest coverage limit

Of the 24 sources read so far:

```
wikipedia                     7   full text: yes
doi.org → publisher           8   mostly paywalled
news / feed items             7   varies; Bloomberg and NYT paywalled
arxiv                         2   yes
```

So R3 helps roughly **9 of 24** outright, some of the news, and **not** the
openalex/DOI half. Anyone reading this later should not expect it to unblock
every concern. A paywall stub must be *detected* (short body, known markers)
and treated as a failed fetch, or the being will extract claims about
subscription offers.

## 3. The cost, which is the real decision

```
extraction today   median   597 tok/call    max 4,179
with full text     est.   3–4k tok/call     ≈ 5–6×
diet headroom now         3,515 tok
```

**R3 makes the §9.1 diet bind immediately** — roughly one full extraction
before ingest pauses. That is not an argument against it; it is the shape of
the trade:

> 24 shallow reads → 118 claims → **0 positions**

Fewer, deeper reads is the only version of this that has not already been
tried and failed. The ratio stays untouched; what changes is claims-per-token
and, one hopes, positions-per-claim.

Two consequences to accept explicitly:

1. **Reading becomes rare.** At ~3.5k tokens per full extraction the being
   will read a handful of documents a day, not dozens. The governor will
   pause ingest often, and deliberation will continue and rebuild headroom —
   the self-balancing loop already established.
2. **The 20-minute interval mostly will not read.** Most cycles will run on
   the dossier alone. That is fine if R1 lands (they fail honestly as
   `blocked` rather than falsely as `restated`); without R1 it makes the
   stall risk in R-24 worse, not better.

**R1 and R2 are therefore preconditions, not companions.**

## 4. Risks

**Injection surface grows by orders of magnitude.** A headline offers a
sentence to hide an instruction in; a full page offers thousands. INV-011's
fencing and hostile fixtures exist and are tested, but they were written
against feed-item-sized text. The fixture set should gain a full-page hostile
document before this ships, not after.

**Boilerplate as evidence.** Without trafilatura, nav/footer/cookie text
reaches extraction and the being records claims about newsletters. This is
the argument for declaring the dependency rather than relying on
`strip_tags`.

**Rate limits and citizenship.** Fetching article bodies is heavier traffic
than API calls. The per-domain limiter covers it, but the polite-pool
identification in `NEWZ_USER_AGENT` still lacks a contact address — Wikipedia
already 403s on that account. Fixing that is arguably a precondition for
fetching more from anyone.

**Cache/staleness.** A fetched document should be stored (or at least
hashed) so R1's dedup can recognise it. Otherwise the same page is
re-fetched at full cost every cycle — the duplicate-read problem, five times
more expensive.

## 5. What I would build, in order

1. **R1 + R2 first** (already recommended, small) — otherwise R3 pays full
   price to re-read the same four URLs.
2. **`document.py`** — fetch, extract, cap, fall back. Pure function, no
   store, easy to test with fixtures.
3. **Wire it behind triage** in `research()` and `harvest()`, with the
   abstract as fallback.
4. **A full-page hostile fixture** in the injection suite before it is
   enabled.
5. **Store the fetched text** on the reading episode's `content_json`, so
   sleep digests the document rather than the abstract, and so R1 can dedup
   on it.

Estimate: half a day for 2–4, plus the dependency decision.

## 6. What I am not proposing

- **Canon.** Books are a different mechanism — chunking with overlap, read
  across many nights (v1's `canon.py` chunked at 1500 chars/150 overlap).
  R3 is articles and papers. Canon should be argued separately and probably
  after, since it will consume the same budget.
- **Loosening the diet ratio.** It becomes the active governor here, which
  is what it is for.
- **More sources.** Breadth is not the constraint, and the source review
  above says so: the gaps are all "the slice is too thin", never "no source
  answered".

## 7. Approval requested

1. **R3 as scoped in §5**, with the abstract-fallback guarantee in §2.2.
2. **Declaring trafilatura + bs4** in `pyproject.toml`, or an explicit
   decision to accept `strip_tags` quality instead.
3. **The full-page hostile fixture as a precondition**, not a follow-up.
4. Acknowledgement of §3: **reading becomes rare and deep**, ingest will
   pause regularly, and that is the intended behaviour rather than a fault.

---

# STAMPED 2026-08-17 — built, and the thesis held

Built as #28 (`7f901e1`). Measured over the following two nights:

```
full-text reads   13 reads   →  11.6 claims per read
abstract reads    74 reads   →   1.4 claims per read
```

**Roughly eight times the yield per read**, and concern 108 closed *seconds*
after a full-text read on 2026-08-15 at 20:39 — the first closure in v2's
history that came from reading rather than from establishing an absence.

The §3 cost projection was close: *"a handful of documents a day"* against a
measured 9 in the first full night.

## Three corrections to what this proposal claimed

**1. "Never worse than today: any failure falls back to the abstract" was
false as written.** It was scoped to FETCH failures. A successful fetch whose
extraction truncated returned 0 claims where the abstract returns 2, with
nothing telling the caller it had failed. Fixed by `Extraction.failed` (#5)
and by returning `None` from `read_document` on *any* barren read, not only a
fetch error. Now INV-040.

**2. Full text in one call cannot work.** 12,000 characters exceeded the
900-token output cap, the XML truncated mid-element, and extraction returned
nothing where the abstract returned two claims. Chunking at 2000/150 was not
an implementation detail; it was a precondition.

**3. Undirected chunked extraction is v1's accretion with better sources** —
64 claims per document, measured. Direction (#5) brought that to 2 per chunk,
about 18 per document. The claim-volume backstops proposed as #31 were closed
unnecessary as a result: a per-document cap of 20 never fires against an
observed maximum of 16.

## And one worry this proposal raised that was answered elsewhere

§3 warned that *"without R1 it makes the stall risk in R-24 worse"*, because
most 20-minute cycles would not read and would book restatements. That is
answered by the diet proposal's amended §4.2: a setback from a cycle that
could not read is recorded but charges neither counter. The two proposals are
complementary, and R3's "a handful of documents a day" matches the measured
rate rather than contradicting it.

## Not vindicated yet

R3's own falsification (#10) is the citation rate, and it has moved from
**0/54 to 17/189 (9.0%)** in two days, with 25 of 32 recent advances carrying
evidence refs. That is the right direction and not yet a week of data. The
verdict on whether deeper reading produces justified change rather than more
reading stays open, tracked as #36.
