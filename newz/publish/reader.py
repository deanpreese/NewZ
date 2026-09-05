"""The reader surface, and the controls that ship with it.

`SPEC.md` section 2.2 puts authentication, rate limiting and abuse controls in
the same delivery as the surface itself, and the reason is the ordering: a
surface that exists before its controls do is a surface that gets used before
they arrive.

Three controls, and each answers a different failure. **Authentication** so a
read is attributable — the token is stored as a hash, so the store never holds
the credential. **Rate limiting** measured against the recorded access log
rather than a counter in memory, so restarting the process does not reset it.
And **enumeration control**: a reader who may not see an R3 card is not told
that one exists, because a list of the things being kept from you is most of
the thing being kept from you.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from newz.domain.enums import RiskTier
from newz.publish.surface import LocalSurface
from newz.store.db import Store

#: Pilot values. A local reader is one person, and these are abuse controls
#: rather than capacity controls.
READS_PER_MINUTE = 60
READS_PER_HOUR = 600

#: Tiers a reader surface will list at all. R3 is approval-gated per revision
#: and R4 is never published, so neither is enumerable.
LISTABLE_TIERS = frozenset({RiskTier.R0.value, RiskTier.R1.value, RiskTier.R2.value})


class ReaderRefused(Exception):
    """A read that did not happen, and why. Recorded like any other refusal."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(
    store: Store, token_id: str, label: str, audience: str, issued_by: str
) -> str:
    """Mint a reader token and return it once. Only its hash is kept."""
    token = secrets.token_urlsafe(32)
    with store.write() as connection:
        connection.execute(
            "INSERT INTO reader_tokens (id, token_hash, label, audience, revoked, issued_by, "
            "issued_at) VALUES (?, ?, ?, ?, 0, ?, datetime('now'))",
            (token_id, hash_token(token), label, audience, issued_by),
        )
    return token


def revoke_token(store: Store, token_id: str) -> None:
    with store.write() as connection:
        connection.execute(
            "UPDATE reader_tokens SET revoked = 1, revoked_at = datetime('now') WHERE id = ?",
            (token_id,),
        )


@dataclass(frozen=True, slots=True)
class Reader:
    store: Store
    surface: LocalSurface
    token: str

    def _authenticate(self) -> dict[str, Any]:
        row = self.store.one(
            "SELECT * FROM reader_tokens WHERE token_hash = ?", hash_token(self.token)
        )
        if row is None:
            raise ReaderRefused("unknown token")
        if row["revoked"]:
            raise ReaderRefused("token revoked")
        return dict(row)

    def _rate_check(self, token_id: str, now: datetime) -> None:
        minute = (now - timedelta(minutes=1)).isoformat(timespec="seconds")
        hour = (now - timedelta(hours=1)).isoformat(timespec="seconds")
        recent = self.store.one(
            "SELECT COUNT(*) AS n FROM reader_access WHERE token_id = ? AND accessed_at > ?",
            token_id,
            minute,
        )["n"]
        hourly = self.store.one(
            "SELECT COUNT(*) AS n FROM reader_access WHERE token_id = ? AND accessed_at > ?",
            token_id,
            hour,
        )["n"]
        if recent >= READS_PER_MINUTE:
            raise ReaderRefused("rate limit: reads per minute")
        if hourly >= READS_PER_HOUR:
            raise ReaderRefused("rate limit: reads per hour")

    def _log(self, token_id: str, target: str, outcome: str, now: datetime) -> None:
        with self.store.write() as connection:
            connection.execute(
                "INSERT INTO reader_access (token_id, surface, target, outcome, accessed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (token_id, str(self.surface.root), target, outcome, now.isoformat(timespec="seconds")),
            )

    def read(self, claim_id: str, now: datetime | None = None) -> dict[str, Any]:
        """Serve one card from the surface, or refuse and say why."""
        now = now or datetime.now()
        token = self._authenticate()
        self._rate_check(token["id"], now)

        document = self.surface.serving(claim_id)
        if document is None:
            self._log(token["id"], claim_id, "not_served", now)
            if self.surface.has_tombstone(claim_id):
                raise ReaderRefused("this presentation was retracted")
            raise ReaderRefused("not found")

        risk = document["card"]["risk"]
        if risk not in LISTABLE_TIERS:
            # Not "forbidden": a reader who may not see it is not told it exists.
            self._log(token["id"], claim_id, "withheld", now)
            raise ReaderRefused("not found")

        self._log(token["id"], claim_id, "served", now)
        return document

    def browse(self, now: datetime | None = None, **filters: str) -> list[dict[str, Any]]:
        """The index, filtered, with nothing listed that could not be read."""
        now = now or datetime.now()
        token = self._authenticate()
        self._rate_check(token["id"], now)

        entries = [
            entry for entry in self.surface.index() if entry["risk"] in LISTABLE_TIERS
        ]
        for field, value in sorted(filters.items()):
            entries = [entry for entry in entries if entry.get(field) == value]
        self._log(token["id"], f"browse:{sorted(filters.items())}", "served", now)
        return entries


def access_report(store: Store, token_id: str) -> dict[str, Any]:
    rows = store.query(
        "SELECT outcome, COUNT(*) AS n FROM reader_access WHERE token_id = ? GROUP BY outcome",
        token_id,
    )
    return {row["outcome"]: row["n"] for row in rows}
