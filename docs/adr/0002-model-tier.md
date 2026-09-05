# ADR-0002: A small, locally served model

**Status:** Accepted
**Date:** 2026-09-04
**Governs:** `SPEC.md` § 2.3

## Context

`TRUE_NORTH.md` forbids letting an external model, vendor, or source become the
authority for the system's identity or judgment. That boundary is not kept by
intending to keep it: a model strong enough to carry the system's judgment will
eventually be trusted with it, whatever the documents say.

## Decision

The model is **small and locally served**, at a local endpoint, replaceable, and
outside the trust boundary. It proposes; deterministic policy and the persisted
evidence graph decide.

The reason of record is the `TRUE_NORTH.md` boundary. Cost and privacy are
consequences of the decision, not its grounds — stating them as the grounds
would make the decision reversible by a cheaper or more private frontier model,
which is exactly the reversal this ADR exists to prevent.

## What is pinned, and what is not

The boundary is decided here. The **serving path** is a local
OpenAI-compatible endpoint on the operator's own network, reached over HTTP by
the model worker and by nothing else in the system.

The **specific model and its parameter count are not pinned by this ADR.**
Phase 0 has no model path at all — the policy engine imports no networking
module, and the Gate 0 suite proves it — so pinning a model here would record a
choice nothing yet exercises. It is pinned before P08, the first work that sends
a prompt, by amending this ADR with the model, its size, its quantization, and
its endpoint. Until then, "small" means small enough that rule 1 below is
uncomfortable to violate, which is the property that matters.

## Alternatives considered

**A hosted frontier model for extraction and noticing.** Rejected: better
proposals are worth little here, and the failure it invites — rigor migrating
into the model where it cannot be replayed, versioned, or audited — is the
failure the whole system is built against.

## Consequences

Two rules bind implementation:

1. No capability, rule, or threshold may be specified in a way that depends on
   model strength. A rule that holds only with a frontier model is a wrong rule
   and MUST be rewritten to hold with a weak proposer and a strict verifier.
2. Model quality MUST NOT be a release gate, a measure of system health, or an
   explanation for an assessment.

Span verification carries the weight the model cannot: every quotation a model
proposes is checked byte-exact against retained text at the recorded offsets, so
a model cannot introduce a quotation that is not already in a retained artifact.

## What would reverse this

Nothing about model capability. Only a change to `TRUE_NORTH.md`'s boundary on
external authority, which is a change of purpose rather than of implementation.
