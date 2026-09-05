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

```text
newz/domain       the frozen enumerations and record shapes
newz/policy       the capability matrix, promotion, risk, independence, the bundle
newz/graph        claim merge and split
newz/store        SQLite in WAL, the migrations, backup and clean restore
newz/catalog      source revisions and immutable diet epochs with a dry run
newz/control      the daily budget, lanes, reservations, leases, retry, pacing
newz/acquisition  URL policy, the transport, the fetcher, artifacts, instruction
policy/           the emitted machine-readable policy (regenerate, never hand-edit)
tests/fixtures    the hostile corpus and the controlled cases
docs/adr          ADR-0001 storage, ADR-0002 model tier, ADR-0003 runtime
```

Exactly one module — `newz/acquisition/transport.py` — may open a socket, and
the test suite enforces it. The part of the system that decides anything
(`policy`, `domain`, `graph`) can reach neither the network nor the store, so a
policy decision cannot depend on either.

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
python -m newz.policy.emit               # regenerate policy/ after a policy change
```

A change to the capability matrix, the promotion thresholds, the independence
justifications, the required evidence lanes, or the task-state classification is
a **policy version change**: bump `POLICY_VERSION` in `newz/version.py`,
regenerate `policy/`, and expect every assessment derived under the superseded
version to be reassessed.
