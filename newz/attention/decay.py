"""Decay: attention is let go of, and the letting go is on the record.

Notices are retained in full for 90 days and reduced to a summary thereafter.
Interest entries are retained in full while live, and reduced 90 days after
retirement. Nothing in the evidence graph decays — artifacts, spans, assertions,
edges and assessments are immutable, and the register is the only place
forgetting happens.

The shape is the same as erasure in `SPEC.md` section 8: a superseding event
carries the summary and cites what it covers, the superseded row remains, and
what goes is the payload. Silent truncation, where a record simply stops being
there, is forbidden — so this module can say what it no longer holds in detail.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from newz.clock import stamp
from newz.store.db import Store

NOTICE_FULL_DAYS = 90
RETIRED_INTEREST_FULL_DAYS = 90


def decayable_notices(store: Store, now: datetime) -> tuple[str, ...]:
    cutoff = stamp(now - timedelta(days=NOTICE_FULL_DAYS))
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM notices WHERE superseded_by IS NULL AND noticed_at <= ? ORDER BY id",
            cutoff,
        )
    )


def decayable_interests(store: Store, now: datetime) -> tuple[str, ...]:
    cutoff = stamp(now - timedelta(days=RETIRED_INTEREST_FULL_DAYS))
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT id FROM interest_entries WHERE retired = 1 AND superseded_by IS NULL "
            "AND retired_at <= ? ORDER BY id",
            cutoff,
        )
    )


def decay_notices(store: Store, notice_ids: tuple[str, ...], event_id: str, reason: str) -> str:
    """Reduce these notices to a summary and discard their payload."""
    if not notice_ids:
        raise ValueError("decay cites what it covers")
    rows = store.query(
        f"SELECT * FROM notices WHERE id IN ({','.join('?' * len(notice_ids))}) ORDER BY id",
        *notice_ids,
    )
    summary = (
        f"{len(rows)} notices from "
        f"{len({row['artifact_id'] for row in rows})} artifacts, reduced to this summary. "
        f"Reasons given at the time: "
        + "; ".join(sorted({row["reason"][:60] for row in rows})[:5])
    )
    with store.write() as connection:
        connection.execute(
            "INSERT INTO decay_events (id, covers_json, summary, reason, at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (event_id, json.dumps(sorted(notice_ids)), summary, reason),
        )
        # The row survives; its payload does not.
        connection.executemany(
            "UPDATE notices SET quote = '', reason = '[decayed]', superseded_by = ? WHERE id = ?",
            [(event_id, notice_id) for notice_id in sorted(notice_ids)],
        )
    return event_id


def decay_interests(store: Store, interest_ids: tuple[str, ...], event_id: str, reason: str) -> str:
    if not interest_ids:
        raise ValueError("decay cites what it covers")
    rows = store.query(
        "SELECT * FROM interest_entries WHERE id IN "
        f"({','.join('?' * len(interest_ids))}) ORDER BY id",
        *interest_ids,
    )
    summary = f"{len(rows)} retired interests: " + "; ".join(row["subject"] for row in rows)
    with store.write() as connection:
        connection.execute(
            "INSERT INTO decay_events (id, covers_json, summary, reason, at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (event_id, json.dumps(sorted(interest_ids)), summary, reason),
        )
        connection.executemany(
            "UPDATE interest_entries SET rationale = '[decayed]', superseded_by = ? WHERE id = ?",
            [(event_id, interest_id) for interest_id in sorted(interest_ids)],
        )
    return event_id


def what_is_no_longer_held(store: Store) -> tuple[dict[str, Any], ...]:
    """What the system can no longer say in detail, and what it says instead."""
    return tuple(
        {
            "event": row["id"],
            "covers": json.loads(row["covers_json"]),
            "summary": row["summary"],
            "reason": row["reason"],
            "at": row["at"],
        }
        for row in store.query("SELECT * FROM decay_events ORDER BY id")
    )


def evidence_is_untouched(store: Store) -> bool:
    """Nothing in the evidence graph decays. Asserted here so it is testable."""
    return (
        store.one("SELECT COUNT(*) AS n FROM assertions WHERE quote = ''")["n"] == 0
        and store.one("SELECT COUNT(*) AS n FROM segments WHERE text = ''")["n"] == 0
    )
