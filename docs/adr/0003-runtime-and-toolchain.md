# ADR-0003: Python 3.13 on conda `agent13`, SQLite 3.51 through the standard library

**Status:** Accepted
**Date:** 2026-09-04
**Governs:** `ARCHITECTURE.md` § Implementation platform, `PLAN.md` Phase 0

## Context

ADR-0001 chose SQLite and a local artifact tree. The runtime that carries them
was undecided, and it was the first undecided thing in the backlog: P01 is a
repository skeleton, which cannot be laid out without it.

## Decision

The implementation is **Python 3.13** in the conda environment **`agent13`**,
against **SQLite 3.51** through the standard library's `sqlite3`. That SQLite
version already carries WAL, `STRICT` tables and `RETURNING`, so ADR-0001 needs
no third-party driver.

The dependency floor is deliberate: the Phase 0 policy engine imports nothing
outside the standard library. Test tooling is `pytest` and `ruff`, both already
in the environment.

## Alternatives considered

**A typed compiled runtime (Rust or Go).** It would make the determinism
obligations below structural rather than disciplined. Rejected: the model
worker, the parsers and the operator tooling are all Python-shaped, and a
second language at the trust boundary buys strictness at the cost of the thing
Gate 0 actually needs, which is a policy matrix that a person can read.

**A property-testing dependency (`hypothesis`) for the Phase 0 invariants.**
Rejected as unnecessary rather than unwanted: the spaces that matter here are
finite and enumerable — 2,016 capability cells, 11 task states, 5 risk tiers —
so the invariant tests enumerate them exhaustively instead of sampling them.
Exhaustive beats generated where exhaustive is affordable, and it keeps the
dependency floor at zero.

## Consequences

Determinism is the obligation this choice must not quietly break. `SPEC.md`
§ 13 requires that assessment and claim-card data reproduce exactly given the
same retained artifacts, policy version, and code version. Therefore, in every
policy, promotion, matrix, and serialization path:

- no dependence on set iteration order, `hash()`, or `PYTHONHASHSEED`;
- no dependence on dictionary ordering that is not explicitly sorted;
- no locale-dependent comparison or formatting;
- no reading of the host clock inside a derivation — times are inputs;
- canonical JSON only (sorted keys, no whitespace, UTF-8) for anything hashed.

A runtime upgrade is a code version change: assessments reproduce under it, or
the divergence is a defect that gets a permanent regression fixture.

## What would reverse this

A measured need the runtime cannot meet — parser throughput at a catalog size
this project does not currently plan for, or a determinism failure that Python
makes unfixable rather than merely easy to get wrong. Neither is in evidence.
