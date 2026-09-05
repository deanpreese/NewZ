"""Opening the store, and the obligations ADR-0001 attached to that choice.

WAL with `synchronous = FULL`, enforced foreign keys, one writer, a bounded busy
timeout, and `IMMEDIATE` for any read-modify-write. The last one is the
non-obvious one: SQLite's default deferred transaction takes its write lock
lazily, so two writers can both read, both decide, and one gets `SQLITE_BUSY` at
commit having already made its decision. `IMMEDIATE` takes the lock up front and
turns that race into a wait.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from newz.store.schema import MIGRATIONS

BUSY_TIMEOUT_MS = 5_000


@dataclass(frozen=True, slots=True)
class Store:
    """One database file and the artifact tree beside it."""

    connection: sqlite3.Connection
    path: Path
    artifact_root: Path

    def query(self, sql: str, *params: Any) -> list[sqlite3.Row]:
        return list(self.connection.execute(sql, params))

    def one(self, sql: str, *params: Any) -> sqlite3.Row | None:
        rows = self.query(sql, *params)
        return rows[0] if rows else None

    def execute(self, sql: str, *params: Any) -> sqlite3.Cursor:
        return self.connection.execute(sql, params)

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """A write transaction that takes its lock before it reads.

        Commits on success, rolls back on any exception. Nested use is a bug,
        not a feature: a transaction that can be entered twice is a transaction
        whose boundary nobody can point to.
        """
        if self.connection.in_transaction:
            raise RuntimeError("a write transaction is already open on this connection")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()


def _configure(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row
    # isolation_level=None hands transaction control to us; the pragmas below
    # must not run inside an implicit transaction.
    connection.isolation_level = None
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")


def migrate(connection: sqlite3.Connection) -> int:
    """Apply every unapplied migration, each in its own transaction."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            applied_at  TEXT NOT NULL
        ) STRICT
        """
    )
    applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
    count = 0
    for version, name, sql in MIGRATIONS:
        if version in applied:
            continue
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.executescript(sql)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) "
                "VALUES (?, ?, datetime('now'))",
                (version, name),
            )
        except BaseException:
            connection.rollback()
            raise
        connection.commit()
        count += 1
    return count


def open_store(path: Path | str, artifact_root: Path | str | None = None) -> Store:
    """Open (creating if needed) the database and the artifact tree beside it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    root = Path(artifact_root) if artifact_root is not None else path.parent / "artifacts"
    root.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1000)
    _configure(connection)
    migrate(connection)
    return Store(connection=connection, path=path, artifact_root=root)


def integrity_report(connection: sqlite3.Connection) -> dict[str, list[str]]:
    """What the backup verification path must run and read, not merely run."""
    integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    foreign_keys = [
        f"{row['table']}.rowid={row['rowid']} -> {row['parent']}"
        for row in connection.execute("PRAGMA foreign_key_check")
    ]
    return {"integrity_check": integrity, "foreign_key_check": foreign_keys}
