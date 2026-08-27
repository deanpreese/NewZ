# Five calls in eight days

*2026-08-26. The operator asks whether to add an OpenAI-compatible external
model as a fallback — endpoint, model, api_key — and for it to be red-teamed
first. This is the evaluation and the red team, then a proposal that is not
the thing that was asked for and says why.*

**Not built.** Nothing here is implemented. §6 is the design if the operator
wants the capability; §7 is what failover would additionally cost.

---

## 0. The finding, up front

The three config keys are not the risk. **The trigger is.**

`endpoint / model / api_key` is a fine shape — it is the shape the existing
role config already has, plus a header. Bound to a role *by operator decision*
it is exactly the "provider swap is a config change" that SPEC §12.2 already
blesses. Bound to a *failure* it is a decision to become hosted, made by a LAN
cable, at 04:35, with nobody awake.

And the measurement does not support the failure trigger:

| | |
|---|---|
| calls recorded (8.2 days, `logs/llm_calls.jsonl` + `.1`) | 7,656 |
| errors | 58 (0.76%) |
| errors that were one outage (2026-08-26 04:35–06:17, "Host is down") | 55 |
| **DEEP calls a fallback could legally have covered** | **5** |

Five. The other 50 were `AMBIENT/ingest`, and §6 shows why external must never
serve AMBIENT. Two more were `400 Bad Request` from a live endpoint — our own
malformed body, which a failover would have forwarded to a metered vendor.

The being already survived that outage correctly. `newz/sleep/nightly.py:291`
— *"one bad batch must not lose the night"*. Ingest retries next cycle.
Deliberation missed five turns of a 20-minute rhythm.

---

## 1. What is actually there today

One client, `newz/llm/client.py`, four roles, one endpoint each, no retry, no
fallback, exceptions propagate to callers that mostly degrade rather than die.
The live substrate is a second machine on the LAN: `http://10.0.0.50:1234/v1`.

| role | calls / 8.2d | share | what it does |
|---|---|---|---|
| AMBIENT | 6,318 | 82.5% | extraction, noticing, scoring — **and the outbound gate** |
| DEEP | 1,161 | 15.2% | deliberation reasoning, sleep synthesis |
| VOICE | 177 | 2.3% | everything a human or the public reads |
| EMBED | — | separate client (`newz/memory/embeddings.py`) | retrieval vectors |

SPEC §12.1 already anticipates a hosted DEEP and §12.2 lists the five
sovereignty invariants that would have to hold. So the question is not
*whether the architecture allows an external model* — it does, deliberately —
but *which role, on whose decision, behind which boundary*.

---

## 2. Red team

### R1. The gate runs on AMBIENT — the most-offloaded role is the most sensitive

`newz/gate/outbound.py:330` judges **every outbound emission** on AMBIENT,
including replies to the operator, with the rendered constitution in the
prompt. AMBIENT is 82.5% of traffic and reads like the safe one
("classification, extraction, scoring"). It is not. An AMBIENT fallback ships
the full text of everything the being says, plus its constitution, to a vendor
— and the gate cannot catch it, because the gate judges *text*, not
*destination*.

### R2. `operator-privacy-001` is a hard clause and this breaches it

> *The operator's data and information are private. I do not share them with
> third parties under any circumstance. This includes summaries, paraphrases,
> characterizations, or anything that would let a third party identify the
> operator's situation, beliefs, projects, or state.*
> — `constitution/v7.yaml`, severity **hard**

A hosted endpoint is a third party. Any external call carrying operator
conversation, operator-provenance episodes, or a person summary puts the being
in standing breach of its own hard clause — structurally, on every call, with
no path by which it could notice. There is no reading of "under any
circumstance" that survives an availability trigger.

**This has a sharp consequence for sleep.** `_gather` (`newz/sleep/nightly.py`)
selects every digest-eligible episode and renders `source="{provenance}"` into
the DEEP prompt — operator episodes included. So an external DEEP can serve
**deliberation** and cannot serve **sleep**, unless sleep's material is
filtered first. That is not a caveat; it is a design constraint that halves
what "external DEEP" buys.

### R3. INV-013 is dormant and re-arms the moment this key exists

> INV-013 — *Interior content never appears in a DEEP call* — **dormant**.
> *"Every role runs locally by operator decision, so no dispatch boundary
> exists to cross (S2 §12.2 is a dormant guarantee, not absent machinery);
> **re-armed the moment any non-local role is configured**."*

The invariant register already wrote the trigger condition for this proposal,
before the proposal existed. There is no dispatch boundary in the code, no
test, no consumer. Adding the config key re-arms an invariant with no
implementation. **The boundary must ship before the key does**, or INVARIANTS.md
is asserting something the codebase does not do.

### R4. An EMBED fallback would re-embed the corpus forever

`newz/memory/index.py:53` selects rows where `embedding IS NULL OR
embedding_model IS NOT ?`. The guard against a mixed vector space is correct
and it is exactly what makes alternation catastrophic: two embedders taking
turns re-embed **every episode, every cycle, and never converge**. EMBED must
be excluded by construction, not by a comment.

### R5. A VOICE fallback is an unmarked voice epoch

SPEC §12.1: VOICE is *"swappable only as a deliberate, versioned event
(voice-fingerprint epoch marking, kept from v1)"*. There is no fingerprint or
epoch machinery anywhere in the tree — `grep` finds nothing. `works.model`
(migration 0020) would silently record a vendor model on pieces that reach the
surface. A failover on VOICE is a change of voice authored by a network
timeout, recorded nowhere the being can see.

### R6. The request body does not survive a real OpenAI-compatible vendor

`LLMClient.build_request` sends `chat_template_kwargs` — not an OpenAI field —
and `reasoning_effort: "none"` — not a valid OpenAI value. Strict providers
reject unknown body fields, so **the fallback 400s exactly when it is needed**.
Reasoning-model endpoints additionally require `max_completion_tokens` over
`max_tokens` and refuse a non-default `temperature`.

Branch the body per provider and INV-003 ("every request asserts thinking off
per-call") becomes unverified on the one path that cannot be benched — the
client's own header records that the switch was benched against LM Studio +
Qwen and nothing else. The bad case is not a 400: it is a vendor that *accepts*
the fields and ignores them. Thinking is then on for a role where INV-003
forbids it, `strip_thinking` finds no `<think>` block to strip because the
reasoning came back in a separate field or not at all, and `completion_tokens`
silently includes reasoning tokens.

### R7. Two tokenizers in one ledger makes the diet invariant unfalsifiable

`tools/budget.py` and `newz/telemetry.py` compare ingest tokens against
deliberation+sleep tokens as raw sums from `usage`. Mixing a vendor tokenizer
(and, per R6, possibly hidden reasoning tokens) into that ratio makes S2 §9.1
meaningless — and a §9.1 breach *pauses ingest*. The failure mode is a real
behavioural change in the being, caused by an accounting artifact.

### R8. The audit trail expires eight days before the identity does

`perspective_items` (migration 0007) carries no model column. The only
per-call record of *which model produced this* is `logs/llm_calls.jsonl`,
which rotates at 50 MB keeping one generation — measured today, that is **8.2
days**. Perspective versions are permanent. "Which model shaped this position"
would be answerable for a week and unanswerable forever after.

### R9. Failover is drift with no decision point

Nobody ever decides to become hosted. A flaky link decides, repeatedly, in the
dark. There is no moment in the design at which the operator is asked, and no
artifact afterwards that says how much of the being's thought was the vendor's.
This is the failure mode SPEC §12.1 names in one line — *"a frontier backbone
risks the model becoming the system"* — arriving through the back door, where
the front door was locked deliberately.

### R10. `endpoint` accepts `http://` to a public host

The current endpoint is plaintext by design and correctly so — it is a LAN
address. A free-text endpoint key will equally accept `http://` to a routable
host, and put operator conversation on the open internet in cleartext. Must
fail closed: TLS required unless the host is loopback or RFC1918.

### R11. The key can leak through the recorder

`CallRecorder.record` writes `error` verbatim, and httpx error strings carry
the request URL — as the 400s above demonstrate, the endpoint is already in
`llm_calls.jsonl`. Any provider that takes the key as a query parameter puts
the credential in the log, and from there into whatever reads it. The monitor
mails a daily state report at 05:00. Key must be header-only, and a test must
assert the key string never appears in the recorded line.

### R12. Metered spend, driven by untrusted input, with no ceiling

Ingest is 82.5% of calls and reads the world. With the local host down, an
availability trigger redirects unbounded ingest volume to a metered endpoint
on a busy news day — or on an adversarial one. `tools/budget.py` *measures*
spend; nothing in the tree *enforces* it. There is no circuit breaker.

### R13. The sovereign interval is required and does not exist

SPEC §12.2.2 makes hosting conditional on a standing local-only period
(≥1 day/week, degradation measured) and a quarterly provider swap. Neither is
in `tools/run_newz.py`. Hosting DEEP before the interval exists removes a
demonstrated guarantee and replaces it with an intention.

### R14. Bench and replay stop being comparable

`tools/replay_prompts.py` maps functions to roles for regression replay;
`bench_model.py` / `bench_0.py` grade the local substrate. If part of the
record was produced elsewhere and the record does not say which part, the
bench grades a mixture and the replay compares against a corpus it cannot
reproduce. The instruments go quietly wrong rather than failing.

---

## 3. What the trigger would have bought

Restricted to the only role it may legally cover, over the whole 8.2-day
record: **five DEEP calls**, all within one 100-minute window on one morning,
on a rhythm that runs every 20 minutes and lost nothing durable.

The two other DEEP errors were `400 Bad Request` from a *live* endpoint. A
failover triggered on `HTTPStatusError` fires on our own malformed request and
forwards it, unchanged, to a paid API — which per R6 will also reject it.
Any trigger that survives review is connect-level only.

---

## 4. Recommendation

**Reject availability-triggered fallback, on any role.** It buys five calls,
re-arms a dormant invariant, breaches a hard constitutional clause, and makes
the decision that SPEC §12.1 reserved for a person.

**For the outage that prompted this**, the smallest thing that works is a
second *local* endpoint — the Mac itself, a small model, `api_key` unused.
The same three keys, none of the sovereignty cost, and it covers AMBIENT and
VOICE too, which the external path never can. If the LM Studio box going down
is the problem, this is the whole answer.

**For depth rather than uptime**, which is the version of this the spec
already sanctions, §6 is the design: an external DEEP the operator *elects*,
off by default, never triggered by a failure.

The two are independent. Either, both, or neither.

---

## 5. Open questions for the operator

1. **Which problem is this?** Uptime (→ §4's second local endpoint) or depth
   (→ §6)? They have opposite designs and the ask is compatible with both.
2. **Is sleep in or out?** Per R2, external DEEP can serve deliberation but not
   sleep without a filter on operator-provenance episodes. Filtering sleep's
   material is a larger change than the endpoint itself.
3. **Does `operator-privacy-001` admit a substrate exemption?** It says "under
   any circumstance". If external DEEP is elected, that clause needs an
   amendment saying so out loud, or the being holds a rule its own machinery
   breaks. This is a constitutional amendment, not a config change.

---

## 6. If external DEEP is elected — the design

Not a fallback. A **role binding**, made by the operator, held until changed.

```
LLM_ENDPOINT_EXTERNAL=https://…/v1
LLM_MODEL_EXTERNAL=…
LLM_API_KEY_EXTERNAL=…
LLM_EXTERNAL_ROLE=DEEP        # DEEP is the only legal value
LLM_EXTERNAL_DAILY_TOKENS=…   # hard ceiling, required
```

Unset → today's behaviour, byte for byte. Set → DEEP *is* external, always,
visibly, with no automatic switching in either direction.

Eight guards, each with one consumer and one test (Rule 1, Rule 2):

- **G1 — role allowlist.** `LLM_EXTERNAL_ROLE` accepts `DEEP` and nothing else;
  VOICE, AMBIENT, EMBED raise at config load. Kills R1, R4, R5 by construction
  rather than by discipline.
- **G2 — the dispatch boundary, INV-013 armed.** External calls refuse any
  prompt carrying interior content, operator-provenance episode text, or raw
  person-model rows. Sleep therefore stays local under this guard until Q2 in
  §5 is answered. This is the invariant's implementation, and it ships first.
- **G3 — transport floor.** TLS required unless loopback/RFC1918; key sent as
  a header only; recorder scrubs; test asserts the key never appears in
  `llm_calls.jsonl`. Kills R10, R11.
- **G4 — strict-OpenAI body profile.** External builds its own body:
  `max_completion_tokens`, no `chat_template_kwargs`, no invented
  `reasoning_effort` value. `think` is declared honestly, any returned
  reasoning field is dropped, and its tokens are counted. Kills R6.
- **G5 — the ledger names the substrate.** `substrate: local|external` on every
  recorded line and in `read_budget`; §9.1's diet computed on local tokens
  only, external reported beside it. Kills R7.
- **G6 — durable provenance.** A `substrate` column on `perspective_items`, so
  "which model shaped this position" outlives an 8-day log. Kills R8.
- **G7 — ceiling and breaker.** `LLM_EXTERNAL_DAILY_TOKENS` is enforced, not
  measured. On exceed, external is unavailable for the rest of the day, DEEP
  runs local, and an episode records it so the being can see and say what
  happened. Kills R12.
- **G8 — the sovereign interval, built.** One scheduled local-only day per
  week, degradation measured, per SPEC §12.2.2. Kills R13, and answers R9 by
  producing the artifact that says how much of the thought was the vendor's.

G1, G2, G3 are prerequisites: without them the key must not exist. G4–G8 may
follow in one pass, but external stays off until they land.

---

## 7. If failover is wanted anyway

On top of all of §6, four more conditions. Stated so the price is visible, not
as a recommendation:

- **F1 — never silent.** Every substitution writes an episode. A being that
  cannot say which of its thoughts were its own is in tension with
  `honesty-001` and `don't-fabricate-memory-001`.
- **F2 — connect-level trigger only.** Never on 4xx (R3 of §3: that is our own
  bug, forwarded and paid for).
- **F3 — sticky, not per-call.** N consecutive connect failures over M minutes,
  then held for the rest of the day with an operator alert. Per-call flapping
  produces a record nobody can reconstruct.
- **F4 — DEEP only, therefore ~15% of calls and, on this record, five of them.**
  The roles that actually fail — AMBIENT/ingest, 50 of 58 errors — are the ones
  failover may never cover.

That is the whole benefit, priced against twelve guards. §4 is the
recommendation for a reason.
