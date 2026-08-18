"""SQL migrations runner.

Ported with review from v1 (`ngbeing/operational/migrations_runner.py`,
S2 §16 allowlist). Review changes: aiosqlite → sync sqlite3 (v2's storage
layer is synchronous at Phase 0; SQLite calls are sub-millisecond here), and
the interior single-schema path is folded into the same runner (interior
gets its own migrations dir rather than a special-cased schema file).

Conventions (v1's, kept):
  - Forward-only; each migration is one atomic transaction.
  - A failed migration aborts boot — the system refuses to start with an
    inconsistent schema.
  - Filenames: `NNNN_description.sql`. Applied versions tracked in the
    target DB's `schema_versions` table.

P2 Rule 2 (no dead schema) is enforced at review time: a migration ships
only alongside its writer and reader.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Raised when a migration fails to apply."""


_MIGRATION_FILENAME = re.compile(r"^(\d{4})_(.+)\.sql$")


def current_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied schema version, or 0 if none."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_versions'"
    ).fetchone()
    if row is None:
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_versions").fetchone()
    return row[0] if row and row[0] is not None else 0


def apply_pending(conn: sqlite3.Connection, migrations_dir: str | Path) -> list[int]:
    """Apply all migrations in `migrations_dir` with version greater than current.

    Returns a list of versions applied (empty if already up to date).

    Each migration runs in its own atomic transaction. If one fails, the
    transaction rolls back and a MigrationError is raised with the version
    that failed; later migrations are not attempted.
    """
    migrations_dir = Path(migrations_dir)
    if not migrations_dir.is_dir():
        raise MigrationError(f"Migrations directory not found: {migrations_dir}")

    have = current_version(conn)
    pending: list[tuple[int, str, Path]] = []

    for path in sorted(migrations_dir.iterdir()):
        if not path.is_file():
            continue
        match = _MIGRATION_FILENAME.match(path.name)
        if match is None:
            continue
        version = int(match.group(1))
        description = match.group(2).replace("_", " ")
        if version > have:
            pending.append((version, description, path))

    if not pending:
        logger.info("schema up to date at version %d", have)
        return []

    applied: list[int] = []
    for version, description, path in pending:
        logger.info("applying migration %04d: %s", version, description)
        sql = path.read_text()
        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_versions (version, applied_at, description) VALUES (?, ?, ?)",
                (version, time.time(), description),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise MigrationError(
                f"migration {version:04d} ({description}) failed: {e}"
            ) from e
        applied.append(version)

    logger.info("applied %d migration(s): %s", len(applied), applied)
    return applied
