"""The content-addressed artifact store.

The ordering obligation from ADR-0001 lives here: artifact bytes land as an
fsynced temporary file and are renamed into place *before* the row that
references them commits. The two failure modes are not symmetric. A crash after
the file and before the row leaves a file nothing points at, which a sweep
collects. A crash the other way round leaves a row pointing at nothing, which is
an evidence ledger citing an artifact that does not exist — so the order is
chosen to make only the first one possible.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from newz.store.db import Store


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    content_hash: str
    byte_size: int
    path: Path
    relative_path: str
    already_present: bool


def path_for(root: Path, content_hash: str) -> Path:
    return root / "sha256" / content_hash[:2] / content_hash[2:4] / content_hash


def store_bytes(root: Path, body: bytes) -> StoredArtifact:
    """Write the body under its own hash, durably, and return where it went.

    Idempotent: the same bytes written twice occupy one file. Duplicate bodies
    share storage and never share a sighting, which is `SPEC.md` section 6 item 5.
    """
    content_hash = hashlib.sha256(body).hexdigest()
    target = path_for(root, content_hash)
    relative = str(target.relative_to(root))

    if target.exists():
        return StoredArtifact(content_hash, len(body), target, relative, True)

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{content_hash}.partial")
    with open(temporary, "wb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)

    # The rename itself must be durable, or a crash can lose a file that a
    # committed row already references.
    directory = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)

    return StoredArtifact(content_hash, len(body), target, relative, False)


def record_artifact(store: Store, connection, artifact_id: str, stored: StoredArtifact, media_type: str) -> str:
    """Insert the artifact row, or return the id of the one already holding it."""
    existing = store.one(
        "SELECT id FROM artifacts WHERE content_hash = ?", stored.content_hash
    )
    if existing is not None:
        return existing["id"]
    connection.execute(
        "INSERT INTO artifacts (id, content_hash, byte_size, media_type, stored_path, stored_at) "
        "VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (artifact_id, stored.content_hash, stored.byte_size, media_type, stored.relative_path),
    )
    return artifact_id


def missing_artifacts(store: Store) -> tuple[str, ...]:
    """Rows pointing at bytes that are not there. This set must always be empty."""
    missing = []
    for row in store.query("SELECT id, stored_path FROM artifacts ORDER BY id"):
        if not (store.artifact_root / row["stored_path"]).exists():
            missing.append(row["id"])
    return tuple(missing)


def orphan_artifacts(store: Store) -> tuple[str, ...]:
    """Files nothing points at. Expected after a crash; collectable, not urgent."""
    known = {row["stored_path"] for row in store.query("SELECT stored_path FROM artifacts")}
    root = store.artifact_root
    found = []
    for path in sorted((root / "sha256").rglob("*")):
        if path.is_file() and str(path.relative_to(root)) not in known:
            found.append(str(path.relative_to(root)))
    return tuple(found)


def verify_hashes(store: Store) -> tuple[str, ...]:
    """Re-hash every stored artifact. Returns the ids whose bytes have changed."""
    corrupted = []
    for row in store.query("SELECT id, content_hash, stored_path FROM artifacts ORDER BY id"):
        path = store.artifact_root / row["stored_path"]
        if not path.exists():
            corrupted.append(row["id"])
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["content_hash"]:
            corrupted.append(row["id"])
    return tuple(corrupted)
