# ADR-0005: `cryptography` for erasure by key destruction

**Status:** Accepted
**Date:** 2026-09-05
**Governs:** `SPEC.md` section 8

## Context

`SPEC.md` section 8 reconciles two requirements that ordinarily contradict each
other. The ledger is append-only and no event is ever removed or rewritten. And
an erasure obligation over private personal data has to be satisfiable.

The specification's answer is to make them not contradict: private personal data
is stored encrypted under a **per-subject key held outside the ledger**, and
erasure destroys the key. The ledger event survives with an unreadable payload
plus a tombstone recording that erasure happened, its reason and its date.

That requires authenticated encryption. Python's standard library has hashing
and HMAC and no cipher.

## Decision

Use **`cryptography`** (`Fernet`) for the protected-payload store. One key per
subject, generated on first write, stored as a file under a key directory that
is not the database and not the artifact tree.

The dependency floor moves from one to two. ADR-0003 set it at zero, ADR-0004
raised it by one for PDF text, and this raises it by one for a cipher.

## Alternatives considered

**Writing a stream cipher over `hashlib`.** Rejected, and not narrowly. This is
the same shape as the hand-written PDF parser rejected in ADR-0004 — it would
work on the tests and fail in ways nobody notices — except that the failure mode
is a person's private data being readable rather than a page being misparsed.
Erasure that does not actually erase is worse than no erasure claim at all,
because somebody relies on it.

**Deleting the rows instead.** Rejected: it is the thing the append-only ledger
exists to prevent, and it would make every audit trail conditional on nobody
having asked to be forgotten.

**Filesystem or full-disk encryption.** Rejected as the wrong granularity. It
protects the store from someone without the disk; it cannot satisfy an erasure
obligation for one subject while keeping the rest of the record readable.

## Consequences

**A destroyed key is destroyed.** There is no recovery path, and the tests
assert that the ciphertext does not decrypt afterwards. That is the point rather
than a limitation, and it means the key directory must be excluded from backups
that outlive an erasure — otherwise a restore quietly un-erases somebody.

**Keys live outside the database file.** A backup of the store therefore does
not carry the keys, which is deliberate: `SPEC.md` requires the key to be held
outside the ledger, and the restore drill checks that a restored store cannot
read protected payloads without the key directory it was given.

**The ledger stays whole.** An erased payload leaves its row, its foreign keys
and its history in place, so a claim card's dependency graph does not develop
holes when somebody exercises a right.

## What would reverse this

A standard-library AEAD, or a requirement that erasure be reversible — which
would be a change of purpose rather than of implementation, because a reversible
erasure is not one.
