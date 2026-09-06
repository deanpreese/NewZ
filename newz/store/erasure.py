"""Erasure by key destruction, which is how an append-only ledger forgets.

`SPEC.md` section 8 reconciles two rules that ordinarily contradict each other:
no ledger event is ever removed or rewritten, and an erasure obligation over
private personal data has to be satisfiable. The reconciliation is that the
payload is encrypted under a **per-subject key held outside the ledger**, and
erasure destroys the key. The row stays, its foreign keys stay, the history
stays — and what was in it is gone.

Three properties this module is built around.

**A destroyed key is destroyed.** There is no recovery path and the tests assert
the ciphertext no longer decrypts. That is the point, and it has a consequence
worth stating out loud: a backup taken before an erasure and restored after one
un-erases somebody, so the key directory is deliberately not inside the store or
the artifact tree, and a restore drill checks that a restored store cannot read
protected payloads without being handed keys.

**Every read is recorded.** `SPEC.md` requires access to R3 quarantined material
to be logged; this logs every access to anything protected, including the ones
that failed because the key was gone. A read that found nothing is still someone
having looked.

**Retention expires on its own.** R4 material and R3 quarantined personal data
carry a default of 24 months from last legitimate review, after which the key is
destroyed automatically unless an operator records a reasoned extension. The
default is expiry; continuing to hold something is the thing that takes a
decision.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from newz.clock import as_utc, from_ledger, stamp
from newz.domain.enums import RiskTier
from newz.store.db import Store

#: `SPEC.md` section 8.
DEFAULT_RETENTION_MONTHS = 24

#: Tiers whose personal data is held under a key at all.
PROTECTED_TIERS = frozenset({RiskTier.R3.value, RiskTier.R4.value})


class KeyDestroyed(Exception):
    """The key for this subject is gone. Not an error to work around."""


@dataclass(frozen=True, slots=True)
class KeyStore:
    """Per-subject keys, on disk and outside the ledger.

    A directory rather than a table, because `SPEC.md` says outside the ledger
    and a column in the same file is not outside anything.
    """

    root: Path

    def path_for(self, subject_id: str) -> Path:
        safe = subject_id.replace("/", "_").replace(":", "_")
        return self.root / f"{safe}.key"

    def create(self, subject_id: str) -> bytes:
        from cryptography.fernet import Fernet

        self.root.mkdir(parents=True, exist_ok=True)
        path = self.path_for(subject_id)
        if path.exists():
            return path.read_bytes()
        key = Fernet.generate_key()
        # Written with an owner-only mode: a key readable by anything on the
        # host is a key held outside the ledger and inside everything else.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, key)
        finally:
            os.close(descriptor)
        return key

    def get(self, subject_id: str) -> bytes:
        path = self.path_for(subject_id)
        if not path.exists():
            raise KeyDestroyed(f"no key for {subject_id}")
        return path.read_bytes()

    def destroy(self, subject_id: str) -> bool:
        path = self.path_for(subject_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def subjects(self) -> tuple[str, ...]:
        if not self.root.exists():
            return ()
        return tuple(sorted(path.stem for path in self.root.glob("*.key")))


def protect(
    store: Store,
    keys: KeyStore,
    *,
    payload_id: str,
    subject_id: str,
    kind: str,
    payload: dict[str, Any],
    risk: RiskTier,
    reason: str,
    now: datetime,
) -> str:
    """Store personal data encrypted under its subject's key.

    Refuses a tier that should not be holding personal data under a key at all:
    if something is R0, it does not belong here, and putting it here would make
    an erasure obligation look satisfied for data that is sitting in the clear
    somewhere else.
    """
    from cryptography.fernet import Fernet

    if risk.value not in PROTECTED_TIERS:
        raise ValueError(
            f"{risk.value} personal data is not held under a subject key; only "
            f"{sorted(PROTECTED_TIERS)} are, and pretending otherwise would make an "
            "erasure obligation look satisfied when it is not"
        )
    if not reason.strip():
        raise ValueError("holding personal data records why it is held")

    token = Fernet(keys.create(subject_id)).encrypt(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    )
    with store.write() as connection:
        connection.execute(
            "INSERT INTO protected_payloads (id, subject_id, kind, ciphertext, risk, reason, "
            "recorded_at, last_review) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                payload_id,
                subject_id,
                kind,
                token,
                risk.value,
                reason,
                stamp(now),
                stamp(now),
            ),
        )
    return payload_id


def read(
    store: Store, keys: KeyStore, payload_id: str, *, actor: str, reason: str, now: datetime
) -> dict[str, Any]:
    """Read protected data, recording who read it and why — or that they could not."""
    if not actor or not reason:
        raise ValueError("reading protected data records the actor and the reason")
    row = store.one("SELECT * FROM protected_payloads WHERE id = ?", payload_id)
    if row is None:
        raise KeyError(payload_id)

    def log(outcome: str) -> None:
        with store.write() as connection:
            connection.execute(
                "INSERT INTO protected_access (payload_id, subject_id, actor, reason, outcome, "
                "accessed_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    payload_id,
                    row["subject_id"],
                    actor,
                    reason,
                    outcome,
                    stamp(now),
                ),
            )

    try:
        key = keys.get(row["subject_id"])
    except KeyDestroyed:
        # A read that found nothing is still someone having looked.
        log("erased")
        raise

    from cryptography.fernet import Fernet, InvalidToken

    try:
        clear = Fernet(key).decrypt(row["ciphertext"])
    except InvalidToken as error:
        log("undecryptable")
        raise KeyDestroyed(
            f"{payload_id} does not decrypt under the key for {row['subject_id']}"
        ) from error
    log("read")
    return json.loads(clear.decode("utf-8"))


def erase(
    store: Store,
    keys: KeyStore,
    subject_id: str,
    *,
    reason: str,
    actor: str,
    tombstone_id: str,
    now: datetime,
) -> int:
    """Destroy a subject's key and leave the tombstone that says so.

    Returns how many payloads became unreadable. The rows are untouched: an
    erased payload keeps its id, its foreign keys and its place in the history,
    so a claim's dependency graph does not develop a hole when somebody
    exercises a right.
    """
    if not reason.strip() or not actor.strip():
        raise ValueError("erasure records who asked and why")

    count = store.one(
        "SELECT COUNT(*) AS n FROM protected_payloads WHERE subject_id = ?", subject_id
    )["n"]
    keys.destroy(subject_id)
    with store.write() as connection:
        connection.execute(
            "INSERT INTO erasure_tombstones (id, subject_id, reason, payload_count, actor, "
            "erased_at) VALUES (?, ?, ?, ?, ?, ?)",
            (tombstone_id, subject_id, reason, count, actor, stamp(now)),
        )
    return count


def erased(store: Store) -> tuple[str, ...]:
    return tuple(
        row["subject_id"]
        for row in store.query("SELECT subject_id FROM erasure_tombstones ORDER BY subject_id")
    )


# ---------------------------------------------------------------------------
# Retention that expires on its own
# ---------------------------------------------------------------------------


def record_review(store: Store, payload_id: str, now: datetime) -> None:
    """A legitimate review restarts the clock, which is what the clock measures."""
    with store.write() as connection:
        connection.execute(
            "UPDATE protected_payloads SET last_review = ? WHERE id = ?",
            (stamp(now), payload_id),
        )


def extend_retention(
    store: Store, subject_id: str, *, until: datetime, actor: str, reason: str, now: datetime
) -> None:
    """Keep something past its expiry, on the record and with a reason."""
    if not reason.strip() or not actor.strip():
        raise ValueError("extending retention records who decided and why")
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO retention_extensions (subject_id, until, actor, reason, "
            "recorded_at) VALUES (?, ?, ?, ?, ?)",
            (
                subject_id,
                stamp(until),
                actor,
                reason,
                stamp(now),
            ),
        )


def _expiry(last_review: str, months: int = DEFAULT_RETENTION_MONTHS) -> datetime:
    return from_ledger(last_review) + timedelta(days=months * 30)


def expiring(store: Store, now: datetime) -> tuple[str, ...]:
    """Subjects whose retention has run out and who hold no extension.

    `now` is normalised into the ledger's timezone before anything is compared
    against it: a retention clock that ran seven hours fast or slow depending on
    the host would destroy a key early somewhere, which is not a fault a
    tombstone can undo.
    """
    now = as_utc(now)
    extensions = {
        row["subject_id"]: from_ledger(row["until"])
        for row in store.query("SELECT subject_id, until FROM retention_extensions")
    }
    already = set(erased(store))
    due: set[str] = set()
    for row in store.query("SELECT subject_id, last_review FROM protected_payloads"):
        subject = row["subject_id"]
        if subject in already:
            continue
        if subject in extensions and now < extensions[subject]:
            continue
        if now >= _expiry(row["last_review"]):
            due.add(subject)
    return tuple(sorted(due))


def expire(store: Store, keys: KeyStore, now: datetime, id_prefix: str = "tombstone:expiry") -> tuple[str, ...]:
    """Destroy the keys of everything past its retention. The default is expiry.

    Automatic on purpose: `SPEC.md` makes continuing to hold personal data the
    thing that takes a decision, not letting go of it.
    """
    done: list[str] = []
    for subject in expiring(store, now):
        erase(
            store,
            keys,
            subject,
            reason=f"{DEFAULT_RETENTION_MONTHS} months from last legitimate review, no extension",
            actor="system",
            tombstone_id=f"{id_prefix}:{subject.replace(':', '_')}",
            now=now,
        )
        done.append(subject)
    return tuple(done)
