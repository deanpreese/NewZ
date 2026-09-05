"""The store's obligations, and the triggers that make immutability structural."""

from __future__ import annotations

import sqlite3

import pytest

from newz.store.db import integrity_report, migrate, open_store
from newz.store.schema import MIGRATIONS


def test_the_pragmas_adr_0001_requires_are_actually_set(store):
    assert store.one("PRAGMA journal_mode")[0] == "wal"
    assert store.one("PRAGMA synchronous")[0] == 2  # FULL
    assert store.one("PRAGMA foreign_keys")[0] == 1
    assert store.one("PRAGMA busy_timeout")[0] >= 1000


def test_migrations_are_recorded_and_applying_twice_is_a_no_op(store):
    """Asserted against the migration list rather than a literal, so adding one
    is a schema decision and not also a test edit."""
    applied = [row["version"] for row in store.query("SELECT version FROM schema_migrations")]
    assert applied == [version for version, _, _ in MIGRATIONS]
    assert applied == sorted(applied), "migrations apply in order"
    assert migrate(store.connection) == 0


def test_a_fresh_store_passes_its_own_integrity_checks(store):
    report = integrity_report(store.connection)
    assert report["integrity_check"] == ["ok"]
    assert report["foreign_key_check"] == []


def test_foreign_keys_are_enforced_not_merely_declared(store):
    with pytest.raises(sqlite3.IntegrityError), store.write() as connection:
        connection.execute(
            "INSERT INTO sources (id, publisher_id, name, topic, recorded_at) "
            "VALUES ('source:x', 'publisher:absent', 'x', 't', datetime('now'))"
        )


def test_strict_tables_refuse_a_value_of_the_wrong_type(store):
    """STRICT converts losslessly where it can, and refuses where it cannot.

    An integer into a TEXT column is a conversion; text into an INTEGER column is
    a risk tier arriving as a word and coming back as one.
    """
    with pytest.raises(sqlite3.IntegrityError), store.write() as connection:
        connection.execute(
            "INSERT INTO schema_migrations (version, name, applied_at) "
            "VALUES ('one', 'x', datetime('now'))"
        )


def test_a_source_revision_cannot_be_edited_or_deleted(catalog):
    store = catalog
    with pytest.raises(sqlite3.IntegrityError, match="immutable"), store.write() as connection:
        connection.execute("UPDATE source_revisions SET role = 'adjudicator' WHERE id = ?",
                           ("srcrev:harbour-uap-1",))
    with pytest.raises(sqlite3.IntegrityError, match="immutable"), store.write() as connection:
        connection.execute("DELETE FROM source_revisions WHERE id = ?", ("srcrev:harbour-uap-1",))


def test_a_diet_epoch_and_its_membership_cannot_be_edited(catalog):
    store = catalog
    with pytest.raises(sqlite3.IntegrityError, match="immutable"), store.write() as connection:
        connection.execute("UPDATE diet_epochs SET note = 'rewritten' WHERE id = 'epoch:1'")
    with pytest.raises(sqlite3.IntegrityError, match="immutable"), store.write() as connection:
        connection.execute("DELETE FROM diet_epoch_sources WHERE epoch_id = 'epoch:1'")


def test_a_write_transaction_rolls_back_on_failure(store):
    with pytest.raises(RuntimeError), store.write() as connection:
        connection.execute(
            "INSERT INTO publishers (id, name, independence_group, recorded_at) "
            "VALUES ('publisher:x', 'x', NULL, datetime('now'))"
        )
        raise RuntimeError("something went wrong after the insert")
    assert store.one("SELECT COUNT(*) AS n FROM publishers")["n"] == 0


def test_nested_write_transactions_are_refused(store):
    # Deliberately nested: flattening these into one `with` would stop the
    # second transaction being opened while the first is still held, which is
    # the whole thing under test.
    with store.write():  # noqa: SIM117
        with pytest.raises(RuntimeError, match="already open"), store.write():
            pass


def test_two_connections_see_one_database(tmp_path):
    first = open_store(tmp_path / "newz.db")
    second = open_store(tmp_path / "newz.db")
    with first.write() as connection:
        connection.execute(
            "INSERT INTO publishers (id, name, independence_group, recorded_at) "
            "VALUES ('publisher:x', 'x', NULL, datetime('now'))"
        )
    assert second.one("SELECT COUNT(*) AS n FROM publishers")["n"] == 1
    first.close()
    second.close()
