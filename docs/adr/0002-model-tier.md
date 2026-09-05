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

## The pin

**Model:** `qwen/qwen3.6-35b-a3b`, served by LM Studio over its
OpenAI-compatible HTTP API on the operator's local network.

**Size:** a mixture-of-experts model of roughly 35B total parameters with about
3B active per token. Both numbers matter and they say different things. The
active count is what the boundary is about: the model that proposes is doing
about three billion parameters' worth of work per token, which is not a model
anyone will be tempted to hand the system's judgment to. The total is what the
host must hold in memory, and it is the number that constrains the local
inference ceiling in `SPEC.md` section 13.

**Serving path:** an OpenAI-compatible endpoint at `/v1` on port 1234, reached
over plain HTTP on the LAN by the model worker and by nothing else in the
system. As of 2026-09-05 the host is `10.0.0.214`; it was `10.0.0.50` before
that. **`.env` is authoritative, not this document** — the address has already
moved once, and an ADR that pins an IP becomes wrong quietly. What this ADR
pins is the model, the tier, and the fact that the endpoint is local.

**Embeddings** run against the same endpoint using
`text-embedding-nomic-embed-text-v1.5@q8_0`. They serve retrieval only.
`ARCHITECTURE.md` already forbids search, embeddings, prose, and prior NewZ
output from being external evidence, and nothing about having a vector index
softens that: an embedding can decide what the system looks at next and can
never contribute to an assessment.

### What the implementation reads

The variables in `.env` are role-keyed from the superseded system —
`LLM_ENDPOINT_AMBIENT`, `LLM_ENDPOINT_DEEP`, `LLM_ENDPOINT_VOICE`, and their
`LLM_MODEL_*` counterparts — because that architecture had three cognitive
roles at different tiers. This system has one model role: `SPEC.md` section 2.3
gives the model a single job, to propose. All three endpoints and all three
model names in `.env` currently hold the same value, which is the shape of that
collapse already having happened in practice.

The model worker therefore reads one endpoint and one model name. It is wired
in P08, the first work that sends a prompt, and until then nothing in the
repository reads `.env` at all: the Phase 0 policy engine imports no networking
module, and the Gate 0 suite proves it.

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
