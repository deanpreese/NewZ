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

## What this ADR pins, and what it does not

It pins the **tier** and the **boundary**: the model is small, it is served
locally, it is replaceable, and it sits outside the trust boundary.

It pins **neither the endpoint nor the model name**, and that is deliberate.
Both are operator configuration and both move — the endpoint has already moved
from `10.0.0.50` to `10.0.0.214`, and the model behind an LM Studio name changes
whenever a different one is loaded. `.env` is the authority for both, read at
run time by `newz/model/config.py`. A document that transcribes a value it does
not own becomes wrong quietly, and the endpoint is the proof: the superseded
address is still sitting commented out one line above the current one.

**As configured on 2026-09-05,** for the record and not as the source of truth:
`qwen/qwen3.6-35b-a3b`, served by LM Studio over an OpenAI-compatible endpoint
at `/v1` on port 1234, with `text-embedding-nomic-embed-text-v1.5@q8_0` for
retrieval vectors on the same endpoint.

**Size.** That model is a mixture of experts of roughly 35B total parameters
with about 3B active per token, and the two numbers say different things. The
active count is what the boundary is about: a proposer doing about three billion
parameters' worth of work per token is not a model anyone will be tempted to
hand the system's judgment to. The total is what the host holds in memory, and
it is the number the local inference ceiling in `SPEC.md` section 13 constrains.
A swap to a different local model of a similar tier needs no amendment here; a
swap to one strong enough to carry judgment contradicts this ADR whatever the
configuration says.

**Embeddings** serve retrieval only. `ARCHITECTURE.md` already forbids search,
embeddings, prose, and prior NewZ output from being external evidence, and a
vector index softens none of that: an embedding can decide what the system looks
at next and can never contribute to an assessment.

### What the implementation reads

`newz/model/config.py` reads one endpoint and one model name, preferring
`NEWZ_MODEL_ENDPOINT` and `NEWZ_MODEL_NAME` and falling back to
`LLM_ENDPOINT_AMBIENT` and `LLM_MODEL_AMBIENT`. Those fallbacks are role-keyed
from the superseded system, which had three cognitive tiers; this system has one
model role, and `SPEC.md` section 2.3 gives it a single job. All three endpoints
and all three model names in `.env` currently hold the same value, which is that
collapse having already happened in practice.

Three properties of that loader are the ADR expressed as code rather than as
prose:

1. **Missing configuration raises.** There is no default endpoint. One that
   happened to work would be the system reaching somewhere nobody chose.
2. **A non-local endpoint is refused.** It is the inverse of the acquisition
   rule and deliberately so: the fetcher refuses an address inside the house
   because it is reaching outward on someone else's instruction, and this
   refuses an address outside it because inference leaving the machine is the
   `TRUE_NORTH.md` boundary being crossed whatever the model is called. Lifting
   it takes an explicit argument, so it cannot drift.
3. **Only the keys it needs are parsed.** `.env` also holds a bot token and a
   mail password, and a loader that read the whole file into a dictionary
   somebody later logs is how those leave the machine.

Nothing sends a prompt yet. The worker that uses this configuration is wired in
P08, and the Gate 0 suite still holds: this module reaches no network, resolves
no name, and the only module in the package that may open a socket is the
acquisition transport.

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
