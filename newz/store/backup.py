"""Backup, and the verification that makes a backup a backup.

`PLAN.md` cross-cutting operations: a restore drill MUST verify byte-exact
reproduction of claim cards, histories, and artifact hashes, not merely that the
service starts. Phase 1 has no cards yet, so what it verifies is everything that
exists: the database passes integrity and foreign-key checks, every artifact row
resolves to bytes, and every artifact's bytes still hash to its recorded hash.

`sqlite3`'s online backup API is used rather than copying the file, because a
copy taken while a writer is mid-transaction is a copy of a torn state.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from newz.acquisition.artifacts import missing_artifacts, verify_hashes
from newz.store.db import Store, integrity_report, open_store


@dataclass(frozen=True, slots=True)
class VerificationReport:
    ok: bool
    integrity: list[str] = field(default_factory=list)
    foreign_keys: list[str] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    corrupted_artifacts: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def as_record(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "integrity": self.integrity,
            "foreign_keys": self.foreign_keys,
            "missing_artifacts": self.missing_artifacts,
            "corrupted_artifacts": self.corrupted_artifacts,
            "counts": self.counts,
        }


COUNTED_TABLES = (
    "source_revisions",
    "diet_epochs",
    "operations",
    "reservations",
    "attempts",
    "responses",
    "sightings",
    "artifacts",
    "instruction_observations",
    "audit_events",
)


def counts(store: Store) -> dict[str, int]:
    return {
        table: store.one(f"SELECT COUNT(*) AS n FROM {table}")["n"] for table in COUNTED_TABLES
    }


def back_up(store: Store, destination: Path) -> Path:
    """Take an online backup of the database and copy the artifact tree beside it.

    Refuses a connection that is mid-transaction. SQLite's backup API reads
    pages from the source connection, and asking a connection that is holding
    its own write lock to do that waits for a lock it already owns — a deadlock
    that presents as a backup which simply never returns, which is the worst way
    for a backup to fail. Back up from a connection of its own.
    """
    if store.connection.in_transaction:
        raise RuntimeError(
            "a backup cannot be taken from a connection that is inside a transaction; "
            "open a second connection to the same file"
        )
    destination.mkdir(parents=True, exist_ok=True)
    database_copy = destination / store.path.name
    target = sqlite3.connect(database_copy)
    try:
        store.connection.backup(target)
    finally:
        target.close()

    artifact_copy = destination / "artifacts"
    if artifact_copy.exists():
        shutil.rmtree(artifact_copy)
    shutil.copytree(store.artifact_root, artifact_copy)
    return database_copy


def verify(store: Store) -> VerificationReport:
    """Read the checks, do not merely run them."""
    report = integrity_report(store.connection)
    integrity = [line for line in report["integrity_check"] if line != "ok"]
    missing = list(missing_artifacts(store))
    corrupted = [i for i in verify_hashes(store) if i not in missing]
    return VerificationReport(
        ok=not (integrity or report["foreign_key_check"] or missing or corrupted),
        integrity=integrity,
        foreign_keys=report["foreign_key_check"],
        missing_artifacts=missing,
        corrupted_artifacts=corrupted,
        counts=counts(store),
    )


def restore_and_verify(backup_dir: Path, database_name: str = "newz.db") -> tuple[Store, VerificationReport]:
    """Open a backup as a store in its own right and verify it end to end.

    The clean room: nothing from the live store is consulted, so a backup that
    only restores while the original is present would fail here.
    """
    restored = open_store(backup_dir / database_name, backup_dir / "artifacts")
    return restored, verify(restored)
