"""Backup, clean restore, and the verification that makes them mean something."""

from __future__ import annotations

import pytest

from newz.acquisition.run import acquire, trace
from newz.domain.enums import ReadLane
from newz.store.backup import back_up, restore_and_verify, verify
from newz.store.db import open_store
from tests import canaries
from tests.test_acquisition import operation_for

#: Three discovery slots and one verification read: four canaries do not fit in
#: one lane, and the budget refusing them would be the budget working.
LANES = (ReadLane.DISCOVERY, ReadLane.DISCOVERY, ReadLane.DISCOVERY, ReadLane.VERIFICATION)


def _populate(store, transport):
    for index, canary in enumerate(canaries.CANARIES):
        acquire(
            store,
            operation_for(store, canary, index, LANES[index]),
            canary.revision,
            transport,
        )


def test_a_live_store_verifies(catalog, transport):
    _populate(catalog, transport)
    report = verify(catalog)
    assert report.ok, report.as_record()
    assert report.counts["sightings"] == 4
    assert report.counts["artifacts"] == 4


def test_a_restored_backup_reproduces_the_store_byte_for_byte(catalog, transport, tmp_path):
    _populate(catalog, transport)
    before = {c.revision.id: trace(catalog, f"operation:o{i}") for i, c in enumerate(canaries.CANARIES)}
    live_counts = verify(catalog).counts

    back_up(catalog, tmp_path / "backup")
    restored, report = restore_and_verify(tmp_path / "backup")

    assert report.ok, report.as_record()
    assert report.counts == live_counts
    after = {c.revision.id: trace(restored, f"operation:o{i}") for i, c in enumerate(canaries.CANARIES)}
    assert after == before
    restored.close()


def test_the_restored_store_is_a_clean_room(catalog, transport, tmp_path):
    """Nothing from the live store is consulted, and the artifacts came too."""
    _populate(catalog, transport)
    back_up(catalog, tmp_path / "backup")
    catalog.close()

    restored, report = restore_and_verify(tmp_path / "backup")
    assert report.ok
    hashes = {row["content_hash"] for row in restored.query("SELECT content_hash FROM artifacts")}
    for content_hash in hashes:
        path = restored.artifact_root / "sha256" / content_hash[:2] / content_hash[2:4] / content_hash
        assert path.exists()
    restored.close()


def test_verification_notices_an_artifact_whose_bytes_changed(catalog, transport, tmp_path):
    _populate(catalog, transport)
    back_up(catalog, tmp_path / "backup")
    restored, _ = restore_and_verify(tmp_path / "backup")

    row = restored.one("SELECT id, stored_path FROM artifacts ORDER BY id LIMIT 1")
    (restored.artifact_root / row["stored_path"]).write_bytes(b"substituted")

    report = verify(restored)
    assert not report.ok
    assert report.corrupted_artifacts == [row["id"]]
    restored.close()


def test_verification_notices_an_artifact_that_went_missing(catalog, transport, tmp_path):
    _populate(catalog, transport)
    back_up(catalog, tmp_path / "backup")
    restored, _ = restore_and_verify(tmp_path / "backup")

    row = restored.one("SELECT id, stored_path FROM artifacts ORDER BY id LIMIT 1")
    (restored.artifact_root / row["stored_path"]).unlink()

    report = verify(restored)
    assert not report.ok
    assert report.missing_artifacts == [row["id"]]
    # Missing is reported once, as missing, rather than twice as missing and corrupt.
    assert report.corrupted_artifacts == []
    restored.close()


def test_a_backup_taken_mid_write_sees_no_uncommitted_row(catalog, transport, tmp_path):
    """The online backup API rather than a file copy: a copy taken while a
    writer is mid-transaction would otherwise be a copy of a torn state.

    The backup runs on its own connection, which is how a backup job runs.
    """
    _populate(catalog, transport)
    backup_connection = open_store(catalog.path, catalog.artifact_root)
    with catalog.write() as connection:
        connection.execute(
            "INSERT INTO outbox (at, kind, subject, payload) "
            "VALUES (datetime('now'), 'uncommitted', 'x', '{}')"
        )
        back_up(backup_connection, tmp_path / "backup")
    backup_connection.close()

    restored, report = restore_and_verify(tmp_path / "backup")
    assert report.ok
    assert restored.one("SELECT COUNT(*) AS n FROM outbox WHERE kind = 'uncommitted'")["n"] == 0
    restored.close()


def test_a_backup_from_a_connection_inside_a_transaction_is_refused(catalog, tmp_path):
    """It would wait for a lock it already holds, and never return."""
    with catalog.write(), pytest.raises(RuntimeError, match="inside a transaction"):
        back_up(catalog, tmp_path / "backup")
