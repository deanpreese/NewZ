# ADR-0004: One parsing dependency, and where the dependency floor still holds

**Status:** Accepted
**Date:** 2026-09-05
**Governs:** `SPEC.md` section 6 item 4, `PLAN.md` Phase 2

## Context

ADR-0003 kept the dependency floor at zero. Phase 2 has to turn retained bytes
into addressable segments for HTML, PDF, plain text and structured data, and one
of those four is not a format a person should implement from the specification
on a Tuesday. A PDF text extractor has to handle the cross-reference table,
object streams, `FlateDecode`, content-stream operators, font encodings and
inherited page resources before it reads a single sentence correctly.

The material is hostile by assumption. `ARCHITECTURE.md` puts parsing behind its
own trust boundary for exactly that reason.

## Decision

**HTML, plain text, JSON and CSV are parsed with the standard library** —
`html.parser`, `json`, `csv`. They are formats where the standard library is
adequate and where a hand-written segmenter is a day's work rather than a
project.

**PDF text extraction uses `pypdf`.** It is the one place the package takes a
third-party dependency.

**The deciding packages stay at zero dependencies.** `newz/policy`,
`newz/domain` and `newz/graph` import nothing outside the standard library, and
the Gate 0 suite enforces that separately from the package-wide check, which now
allows exactly the names listed here.

## Alternatives considered

**A hand-written PDF extractor.** Rejected. The failure mode is not that it
would not work; it is that it would work on the fixtures and misread real
documents, and a parser that silently drops half a page produces spans that
verify byte-exact against text the document does not really contain in that
order. That is worse than no PDF support, because it is wrong quietly.

**Dropping PDF from the pilot.** Rejected: `SPEC.md` section 5.2 needs primary
records and adjudicative records, and those arrive as PDFs more often than as
anything else.

**`lxml` for HTML.** Rejected as unnecessary rather than unwanted. `html.parser`
is forgiving, does not recurse on nesting depth, and the segmenter needs block
text rather than a queryable tree.

## Consequences

The parser plane now has a supply-chain surface that the rest of the system does
not. Three things follow, and the first is the one that matters:

1. **A parser is never trusted with meaning.** It produces bytes-to-segments and
   nothing else. No parser output grants capability, resolves a basis, or
   reaches an assessment; that path runs through span verification and the
   capability matrix, neither of which asks which parser ran.
2. **Parser identity and version are recorded on every parse execution**, so a
   segment set can be reproduced or attributed to the code that produced it, and
   a parser upgrade that changes segmentation is visible as a new execution
   rather than as drift.
3. **The dependency is pinned**, and upgrading it is a code version change under
   `SPEC.md` section 13.

## What would reverse this

`pypdf` becoming unmaintained or acquiring a dependency tree of its own, or a
PDF corpus narrow enough that the subset actually needed is small and stable.
Reversal is contained: the dependency lives behind the parser registry's PDF
entry, and nothing above it knows which library produced a segment.
