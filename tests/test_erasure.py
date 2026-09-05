"""Erasure by key destruction: how an append-only ledger forgets."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.domain.enums import RiskTier
from newz.store import erasure
from newz.store.erasure import KeyDestroyed, KeyStore

NOW = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def keys(tmp_path):
    return KeyStore(root=tmp_path / "keys")


def _protect(store, keys, payload_id="payload:p1", subject="entity:person-1", now=NOW):
    return erasure.protect(
        store,
        keys,
        payload_id=payload_id,
        subject_id=subject,
        kind="allegation_detail",
        payload={"name": "A Named Person", "detail": "held for review"},
        risk=RiskTier.R3,
        reason="an R3 allegation under operator review",
        now=now,
    )


def test_protected_data_round_trips_while_the_key_exists(store, keys):
    _protect(store, keys)
    read = erasure.read(
        store, keys, "payload:p1", actor="operator:dean", reason="review", now=NOW
    )
    assert read["name"] == "A Named Person"


def test_the_ciphertext_is_not_the_plaintext(store, keys):
    _protect(store, keys)
    stored = store.one("SELECT ciphertext FROM protected_payloads")["ciphertext"]
    assert b"A Named Person" not in stored


def test_the_key_lives_outside_the_ledger(store, keys, tmp_path):
    """A column in the same file is not outside anything."""
    _protect(store, keys)
    assert keys.subjects() == ("entity_person-1",)
    assert keys.root != store.path.parent / "artifacts"
    assert not str(keys.path_for("entity:person-1")).startswith(str(store.path))
    columns = {row["name"] for row in store.query("PRAGMA table_info(protected_payloads)")}
    assert "key" not in columns


def test_a_key_file_is_readable_only_by_its_owner(store, keys):
    _protect(store, keys)
    mode = keys.path_for("entity:person-1").stat().st_mode & 0o777
    assert mode == 0o600


def test_erasure_destroys_the_key_and_leaves_the_row(store, keys):
    """The row keeps its id, its foreign keys and its place in the history, so a
    dependency graph does not develop a hole when somebody exercises a right."""
    _protect(store, keys)
    count = erasure.erase(
        store,
        keys,
        "entity:person-1",
        reason="the subject asked",
        actor="operator:dean",
        tombstone_id="tombstone:e1",
        now=NOW,
    )
    assert count == 1
    assert store.one("SELECT COUNT(*) AS n FROM protected_payloads")["n"] == 1
    with pytest.raises(KeyDestroyed):
        erasure.read(store, keys, "payload:p1", actor="operator:dean", reason="review", now=NOW)


def test_a_destroyed_key_stays_destroyed(store, keys):
    """There is no recovery path, and that is the point rather than a limitation."""
    _protect(store, keys)
    erasure.erase(
        store, keys, "entity:person-1", reason="asked", actor="operator:dean",
        tombstone_id="tombstone:e1", now=NOW,
    )
    # Creating a key again does not recover what the old one protected.
    keys.create("entity:person-1")
    with pytest.raises(KeyDestroyed, match="does not decrypt"):
        erasure.read(store, keys, "payload:p1", actor="operator:dean", reason="review", now=NOW)


def test_the_tombstone_records_that_erasure_happened(store, keys):
    _protect(store, keys)
    erasure.erase(
        store, keys, "entity:person-1", reason="the subject asked", actor="operator:dean",
        tombstone_id="tombstone:e1", now=NOW,
    )
    row = store.one("SELECT * FROM erasure_tombstones")
    assert row["subject_id"] == "entity:person-1"
    assert row["reason"] == "the subject asked"
    assert row["payload_count"] == 1
    assert erasure.erased(store) == ("entity:person-1",)


def test_a_tombstone_cannot_be_rewritten(store, keys):
    import sqlite3

    _protect(store, keys)
    erasure.erase(
        store, keys, "entity:person-1", reason="asked", actor="operator:dean",
        tombstone_id="tombstone:e1", now=NOW,
    )
    with pytest.raises(sqlite3.IntegrityError, match="record that erasure happened"), store.write() as connection:
        connection.execute("UPDATE erasure_tombstones SET reason = 'something else'")


def test_erasure_records_who_asked_and_why(store, keys):
    _protect(store, keys)
    for actor, reason in (("", "asked"), ("operator:dean", "")):
        with pytest.raises(ValueError, match="who asked and why"):
            erasure.erase(
                store, keys, "entity:person-1", reason=reason, actor=actor,
                tombstone_id="tombstone:e1", now=NOW,
            )


# ---------------------------------------------------------------------------
# Access
# ---------------------------------------------------------------------------


def test_every_read_is_logged_including_the_ones_that_found_nothing(store, keys):
    """A read that found nothing is still someone having looked."""
    _protect(store, keys)
    erasure.read(store, keys, "payload:p1", actor="operator:dean", reason="review", now=NOW)
    erasure.erase(
        store, keys, "entity:person-1", reason="asked", actor="operator:dean",
        tombstone_id="tombstone:e1", now=NOW,
    )
    with pytest.raises(KeyDestroyed):
        erasure.read(store, keys, "payload:p1", actor="worker:x", reason="a later look", now=NOW)

    outcomes = [row["outcome"] for row in store.query("SELECT outcome FROM protected_access ORDER BY id")]
    assert outcomes == ["read", "erased"]
    actors = {row["actor"] for row in store.query("SELECT actor FROM protected_access")}
    assert actors == {"operator:dean", "worker:x"}


def test_a_read_records_its_actor_and_reason(store, keys):
    _protect(store, keys)
    for actor, reason in (("", "review"), ("operator:dean", "")):
        with pytest.raises(ValueError, match="actor and the reason"):
            erasure.read(store, keys, "payload:p1", actor=actor, reason=reason, now=NOW)


def test_low_risk_data_is_refused_rather_than_protected(store, keys):
    """Putting it here would make an erasure obligation look satisfied for data
    sitting in the clear somewhere else."""
    with pytest.raises(ValueError, match="not held under a subject key"):
        erasure.protect(
            store, keys, payload_id="payload:p2", subject_id="entity:x", kind="note",
            payload={"a": "b"}, risk=RiskTier.R1, reason="a reason", now=NOW,
        )


# ---------------------------------------------------------------------------
# Retention that expires on its own
# ---------------------------------------------------------------------------


def test_retention_expires_without_anyone_deciding_to_let_go(store, keys):
    """Continuing to hold personal data is the thing that takes a decision."""
    _protect(store, keys)
    assert erasure.expiring(store, NOW) == ()
    later = NOW + timedelta(days=erasure.DEFAULT_RETENTION_MONTHS * 30 + 1)
    assert erasure.expiring(store, later) == ("entity:person-1",)

    expired = erasure.expire(store, keys, later)
    assert expired == ("entity:person-1",)
    with pytest.raises(KeyDestroyed):
        erasure.read(store, keys, "payload:p1", actor="operator:dean", reason="review", now=later)
    tombstone = store.one("SELECT * FROM erasure_tombstones")
    assert "no extension" in tombstone["reason"]
    assert tombstone["actor"] == "system"


def test_a_legitimate_review_restarts_the_clock(store, keys):
    _protect(store, keys)
    later = NOW + timedelta(days=erasure.DEFAULT_RETENTION_MONTHS * 30 + 1)
    erasure.record_review(store, "payload:p1", later - timedelta(days=10))
    assert erasure.expiring(store, later) == ()


def test_an_extension_holds_and_records_why(store, keys):
    _protect(store, keys)
    later = NOW + timedelta(days=erasure.DEFAULT_RETENTION_MONTHS * 30 + 1)
    with pytest.raises(ValueError, match="who decided and why"):
        erasure.extend_retention(
            store, "entity:person-1", until=later + timedelta(days=365), actor="", reason="",
            now=NOW,
        )
    erasure.extend_retention(
        store,
        "entity:person-1",
        until=later + timedelta(days=365),
        actor="operator:dean",
        reason="the matter is still before a court",
        now=NOW,
    )
    assert erasure.expiring(store, later) == ()
    assert erasure.expiring(store, later + timedelta(days=400)) == ("entity:person-1",)


def test_an_already_erased_subject_is_not_expired_again(store, keys):
    _protect(store, keys)
    erasure.erase(
        store, keys, "entity:person-1", reason="asked", actor="operator:dean",
        tombstone_id="tombstone:e1", now=NOW,
    )
    later = NOW + timedelta(days=1000)
    assert erasure.expiring(store, later) == ()
    assert erasure.expire(store, keys, later) == ()
