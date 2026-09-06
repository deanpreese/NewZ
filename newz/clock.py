"""One timezone for the ledger, and the conversion into it.

Every row SQLite stamps with `datetime('now')` is UTC. Rows stamped by a caller
are whatever the caller had, and callers reach for `datetime.now()`, which is
local. A ledger that mixes the two cannot be read in order: an access logged at
17:00 and the publication it read, logged at 00:00, are the same instant seven
hours apart on the page.

Worse, code that compares one to the other subtracts a UTC offset without
noticing. The per-host politeness floor did exactly that and stopped pacing
anything east of Greenwich while refusing every read west of it — and looked
correct from inside either.

`stamp` is what a caller-supplied moment must pass through before it is written
down, and `as_utc` is what a comparison must pass both sides through. A naive
value is taken as local, which is what `astimezone` does and what a caller
writing `datetime.now()` means.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Now, aware, in the ledger's timezone."""
    return datetime.now(UTC)


def as_utc(moment: datetime) -> datetime:
    """The same instant, in the ledger's timezone."""
    return moment.astimezone(UTC) if moment.tzinfo else moment.astimezone().astimezone(UTC)


def stamp(moment: datetime) -> str:
    """How a caller-supplied moment is written down.

    Exactly the shape SQLite's `datetime('now')` writes: UTC, second resolution,
    a space between the date and the time, no offset suffix. The separator is
    not cosmetic. Timestamps are compared as text, and `'T'` sorts after `' '`,
    so `'2026-09-06T00:00:00' < '2026-09-06 00:00:01'` is false — a column
    holding both shapes orders wrongly, silently, and only for the rows written
    by the other path. One function rather than a convention, for that reason.
    """
    return as_utc(moment).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")


def from_ledger(value: str) -> datetime:
    """Read a ledger timestamp back as the aware UTC instant it records.

    Accepts both separators: rows written before this module existed carry the
    other one, and a reader that refused them would turn a formatting mistake
    into unreadable history.
    """
    parsed = datetime.fromisoformat(value)
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
