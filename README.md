# NewZ

A rigorous investigator of contested claims: fringe science, anomalous
phenomena, conspiracy allegations, suppressed-history narratives, and adjacent
subjects that ordinary information systems dismiss, sensationalize, or flatten.

> Encounter anything. Investigate almost anything. Believe only what has earned
> promotion. Always show the work.

## The documents govern

Read them in this order; where they disagree, the earlier one wins.

1. [`TRUE_NORTH.md`](TRUE_NORTH.md) — purpose and permanent boundaries
2. [`SPEC.md`](SPEC.md) — required behaviour and acceptance criteria
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — system shape and technical invariants
4. [`PLAN.md`](PLAN.md) — delivery order and rollout gates

`docs/architecture.html` renders the spine of the first three for reading rather
than for reference. `docs/adr/` holds the decisions the documents left open.

## What is built

**Phase 0 — the contract.** Versioned executable policy, and nothing else:
no network, no store, no model. The point of building it first is that every
later phase is persistence and plumbing around concepts that are already
decided.

**Phase 1 — the provenance spine.** Every byte attributable to an authorized
operation. One scheduler, one operation ledger, immutable diet epochs, a safe
fetcher, and a content-addressed artifact store.

**Phase 2 — the evidence graph.** The only path from retained material to an
assessment: five versioned parsers, byte-exact span verification, model
extraction that proposes into a shape with nowhere to put a permission, the
basis registry and its derivation lineage, edge admission with an attestation
per predicate, and append-only assessments.

**Phase 3 — the investigation loop.** What the system does about a gap once it
sees one: investigations that state what would close them before any work
starts, a task per required evidence lane, the counterpart brake that stops
discovery outrunning verification, directed search that produces leads and only
leads, and resolvers whose silence is recorded as carefully as their answers.

**Phase 4 — safe output.** Claim cards and entity cards, the split appraisal
with its review debt ceiling, clearance of an exact revision, a local reader
surface with its own controls, and correction and retraction that confirm from
outside the renderer inside a bounded window. Gate 4 is what earns
approve-by-default: local publication is on for R0–R2, public reach is off.

**Phase 4A — the investigator.** The faculty that decides what is worth
investigating: noticing over retained spans, an inspectable interest register,
investigations the system opens itself, essays whose subject interest chooses
and whose verdict it does not, the reckoning records, and the conversational
surface. Gate 4A is proven by a static audit rather than by sampling — see
`tests/test_separation.py`.

**Phase 5 — the pilot.** *Machinery built; the gate is not passable here.*
Deployment modes with shadow between fixture and live, the seven pause
conditions and what resumption costs, eligible-date and route-exercise
accounting, the daily funnel, and the catalog review. Gate 5 wants thirty
elapsed days, a hundred live retained reads and the operator's approval, so
this counts and does not judge — `newz/pilot/catalog_review.py` states what is
outstanding as a checklist rather than choosing it.

```text
newz/domain       the frozen enumerations and record shapes
newz/policy       the capability matrix, promotion, risk, independence, the bundle
newz/graph        claim merge and split
newz/store        SQLite in WAL, the migrations, backup and clean restore
newz/catalog      source revisions and immutable diet epochs with a dry run
newz/control      the daily budget, lanes, reservations, leases, retry, pacing, audit
newz/acquisition  URL policy, the transport, the fetcher, artifacts, instruction
newz/parse        the parser registry, segments, and span verification
newz/model        where the model lives, and the client that talks to it
newz/extract      the prompt, the proposal shape, and what survives validation
newz/evidence     bases and lineage, edge admission, assessments, inspection
newz/research     investigations, tasks and the brake, leads, resolvers, packets
newz/present      claim cards, entity cards, dependency validation
newz/publish      appraisal, clearance, reach, the surface, the reader, export
newz/attention    noticing, the interest register, the diet self-report, decay
newz/reckoning    decisions, surprise, consequence, escalation, the four checks
newz/converse     the conversational surface and what it structurally cannot do
newz/pilot        deployment modes, pause conditions, shadow, the daily reports
policy/           the emitted machine-readable policy (regenerate, never hand-edit)
tests/fixtures    the hostile corpus and the controlled cases
docs/adr          ADR-0001 storage, 0002 model tier, 0003 runtime, 0004 parsers
```

Exactly two modules may open a socket, and the test suite enforces it:
`newz/acquisition/transport.py`, which fetches URLs the system did not choose,
and `newz/model/client.py`, which talks to one operator-configured local
endpoint. The part of the system that decides anything (`policy`, `domain`,
`graph`) can reach neither the network nor the store nor the model, so a policy
decision cannot depend on any of them.

The capability matrix is 2,016 cells — 8 source roles x 9 claim kinds x 7
assertion kinds x 4 relations — derived from about ten stated principles by
thirteen ordered rules. Every cell records the rule that decided it, and every
rule that rests on a judgment call names the decision that settled it in
`newz/policy/decisions.py`. Deriving it was a design task, not a transcription,
and the decisions say what each call costs.

## Running it

Environment: conda `agent13` (Python 3.13). No third-party dependency is
required to run the policy engine; `pytest` and `ruff` run the checks.

```sh
conda activate agent13
python tools/gate.py                     # ruff, policy artifact freshness, pytest
python -m pytest tests/test_cases.py -v  # the controlled cases, by name
python -m pytest tests/test_gate1.py -v  # the provenance spine, end to end
python -m pytest tests/test_gate2.py -v  # the evidence graph, corpus to assessment
python -m pytest tests/test_gate3.py -v  # three investigations, three outcomes
python -m pytest tests/test_gate4.py -v  # publication, revocation, and its window
python -m pytest tests/test_gate4a.py -v # an investigation nobody asked for
python -m pytest tests/test_separation.py -v  # interest reaches attention, not conclusion
python -m newz.policy.emit               # regenerate policy/ after a policy change
```

A change to the capability matrix, the promotion thresholds, the independence
justifications, the required evidence lanes, or the task-state classification is
a **policy version change**: bump `POLICY_VERSION` in `newz/version.py`,
regenerate `policy/`, and expect every assessment derived under the superseded
version to be reassessed.
