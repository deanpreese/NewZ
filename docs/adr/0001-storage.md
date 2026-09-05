# ADR-0001: SQLite in WAL mode with a local content-addressed artifact store

**Status:** Accepted
**Date:** 2026-09-04
**Governs:** `ARCHITECTURE.md` § Storage architecture

## Context

The storage choice follows from the stated concurrency requirement, which is
deliberately small:

- one operator, one host;
- a ceiling of 10 retained full reads per local day (`SPEC.md` § 5.2);
- a handful of local worker processes, none latency-critical;
- no multi-writer, multi-machine, or horizontal-scale requirement anywhere in
  `SPEC.md`.

Against that, the invariants the store must carry are demanding: append-only
events, content hashes, worker leases, a transactional outbox, and a clean
restore that reproduces claim cards, histories, and artifact hashes byte for
byte (`SPEC.md` § 13).

## Decision

Structured state lives in **SQLite in WAL mode**, one file. Retained artifacts
live in a **local content-addressed filesystem** tree.

The implementation MUST meet these SQLite obligations: WAL mode with
`synchronous = FULL`, enforced foreign keys, one writer connection with a
bounded busy timeout, `IMMEDIATE` transactions for any read-modify-write,
integrity and foreign-key checks in the backup verification path, and artifact
writes that land as fsynced temporary files renamed into place before the
referencing row commits.

## Alternatives considered

**PostgreSQL with an S3-compatible object store.** Rejected as unearned
operational cost for a single-operator system with a ten-read daily ceiling, and
as the largest avoidable obstacle to Gate 1 — two services to run, secure, back
up and restore before the first byte is attributable.

## Consequences

Backup, export and byte-exact restore verification are operations on one file
plus one tree, which is what makes the Gate 1 restore drill affordable enough to
run often. Concurrency is bounded deliberately: readers are concurrent under
WAL, and a single writer is sufficient at ten reads per day.

The domain contract names no SQLite-specific behaviour. Nothing above the
storage adapter may depend on SQLite semantics.

## What would reverse this

A concurrency requirement that is no longer small: multi-writer, multi-machine,
or a read ceiling large enough that a single writer becomes the bottleneck.
Because the domain contract is storage-agnostic, that reversal is a
storage-adapter change and not a redesign.
