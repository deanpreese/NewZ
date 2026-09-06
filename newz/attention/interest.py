"""The interest register.

A durable, revisable set of subjects the system is pursuing, each with a
rationale and the notices that produced it. Interest that cannot be inspected is
indistinguishable from bias, so every change is an append-only event carrying
its reason, and the operator can read all of it.

Four things this module records that a topic list would not, each answering a
way the register could become ornament:

**Influences.** The diet epoch and topic targets in force when the material that
produced an entry was read. A catalog weighted 18% toward one subject will
produce a system interested in that subject; that is a property of the diet and
it is labelled as one rather than reported as self-discovery.

**Provenance.** Where the attention came from, so a register feeding on the
system's own projections is visible as one.

**Trace.** What each entry actually caused. An interest that changes nothing is
decorative, and this is where that stops being arguable.

**Retirement.** An entry that produced nothing within its window is retired or
renewed with a reason. A register that only accumulates is a topic list.

What this module may do is open an investigation and select an essay subject.
That is the whole of it. It writes to no scheduling table, no evidence table and
no threshold, and `tests/test_separation.py` proves that by enumerating the
tables every statement here touches.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from newz.clock import as_utc, from_ledger
from newz.store.db import Store

#: `SPEC.md` section 9.1: 30 days during Pilot.
PRODUCTIVITY_WINDOW_DAYS = 30

#: The ceiling on concurrently open self-originated investigations.
ORIGINATION_CEILING = 5


@dataclass(frozen=True, slots=True)
class InterestEntry:
    id: str
    subject: str
    rationale: str
    diet_epoch_id: str
    topic_targets: tuple[tuple[str, str], ...]
    operator_input: str
    diet_derived: bool
    priority: int
    window_days: int
    retired: bool
    retirement_reason: str
    notice_ids: tuple[str, ...] = ()
    outcomes: tuple[tuple[str, str], ...] = ()

    @property
    def productive(self) -> bool:
        return bool(self.outcomes)

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "rationale": self.rationale,
            "diet_epoch_id": self.diet_epoch_id,
            "topic_targets": [list(pair) for pair in self.topic_targets],
            "operator_input": self.operator_input,
            "diet_derived": self.diet_derived,
            "priority": self.priority,
            "window_days": self.window_days,
            "retired": self.retired,
            "retirement_reason": self.retirement_reason,
            "notice_ids": list(self.notice_ids),
            "outcomes": [list(outcome) for outcome in self.outcomes],
            "productive": self.productive,
        }


def _topics_behind(store: Store, notice_ids: tuple[str, ...]) -> set[str]:
    if not notice_ids:
        return set()
    rows = store.query(
        "SELECT DISTINCT s.topic FROM notices n "
        "JOIN sightings sg ON sg.artifact_id = n.artifact_id "
        "JOIN source_revisions sr ON sr.id = sg.source_revision_id "
        "JOIN sources s ON s.id = sr.source_id "
        f"WHERE n.id IN ({','.join('?' * len(notice_ids))})",
        *notice_ids,
    )
    return {row["topic"] for row in rows}


def is_diet_derived(subject: str, topics: set[str], targets: dict[str, str]) -> bool:
    """Whether the origin chain reaches only a configured topic target.

    The test is deliberately blunt: one topic behind every notice, that topic is
    one the diet targets, and the subject names nothing narrower than the topic
    itself. An interest in "UAP" formed entirely from a catalog weighted 18%
    toward UAP is the diet talking. An interest in one aircraft type, formed from
    the same reading, is not — it picked something out.
    """
    if len(topics) != 1:
        return False
    topic = next(iter(topics))
    if topic not in targets:
        return False
    normalized = subject.strip().lower().replace(" ", "_")
    return normalized in topic or topic in normalized


def form_interest(
    store: Store,
    *,
    interest_id: str,
    subject: str,
    rationale: str,
    notice_ids: tuple[str, ...],
    diet_epoch_id: str,
    topic_targets: dict[str, str],
    operator_input: str = "",
    priority: int = 5,
    window_days: int = PRODUCTIVITY_WINDOW_DAYS,
    opened_at: str = "",
) -> InterestEntry:
    """Form an interest, labelling it diet-derived where that is what it is."""
    if not rationale.strip():
        raise ValueError("an interest records why it formed")
    if not subject.strip():
        raise ValueError("an interest names its subject")

    topics = _topics_behind(store, notice_ids)
    diet_derived = is_diet_derived(subject, topics, topic_targets)

    with store.write() as connection:
        connection.execute(
            "INSERT INTO interest_entries (id, subject, rationale, diet_epoch_id, "
            "topic_targets_json, operator_input, diet_derived, priority, window_days, retired, "
            "retirement_reason, opened_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', COALESCE(NULLIF(?, ''), datetime('now')))",
            (
                interest_id,
                subject,
                rationale,
                diet_epoch_id,
                json.dumps(dict(sorted(topic_targets.items()))),
                operator_input,
                int(diet_derived),
                priority,
                window_days,
                opened_at,
            ),
        )
        for notice_id in notice_ids:
            connection.execute(
                "INSERT OR IGNORE INTO interest_notices (interest_id, notice_id) VALUES (?, ?)",
                (interest_id, notice_id),
            )
        connection.execute(
            "INSERT INTO interest_events (interest_id, kind, reason, payload_json, at) "
            "VALUES (?, 'formed', ?, ?, datetime('now'))",
            (
                interest_id,
                rationale,
                json.dumps(
                    {
                        "notices": list(notice_ids),
                        "topics_behind": sorted(topics),
                        "diet_derived": diet_derived,
                        "operator_input": operator_input,
                    },
                    sort_keys=True,
                ),
            ),
        )
    return load_interest(store, interest_id)


def record_outcome(store: Store, interest_id: str, kind: str, target_id: str) -> None:
    """The downstream trace: an investigation opened, or an essay selected.

    These are the only two things an interest may cause, so they are the only
    two kinds this records.
    """
    if kind not in ("investigation", "essay"):
        raise ValueError(
            "interest reaches attention: it may open an investigation and select an "
            f"essay subject, and {kind!r} is neither"
        )
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO interest_outcomes (interest_id, kind, target_id, at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (interest_id, kind, target_id),
        )
        connection.execute(
            "INSERT INTO interest_events (interest_id, kind, reason, payload_json, at) "
            "VALUES (?, 'produced', ?, ?, datetime('now'))",
            (interest_id, f"{kind} {target_id}", json.dumps({kind: target_id}, sort_keys=True)),
        )


def retire_interest(store: Store, interest_id: str, reason: str, at: str = "") -> None:
    if not reason.strip():
        raise ValueError("retiring an interest records why")
    with store.write() as connection:
        connection.execute(
            "UPDATE interest_entries SET retired = 1, retirement_reason = ?, "
            "retired_at = COALESCE(NULLIF(?, ''), datetime('now')) WHERE id = ?",
            (reason, at, interest_id),
        )
        connection.execute(
            "INSERT INTO interest_events (interest_id, kind, reason, payload_json, at) "
            "VALUES (?, 'retired', ?, '{}', datetime('now'))",
            (interest_id, reason),
        )


def renew_interest(store: Store, interest_id: str, reason: str) -> None:
    """Keep an unproductive interest, on the record and with a reason."""
    if not reason.strip():
        raise ValueError("renewing an interest records why")
    with store.write() as connection:
        connection.execute(
            "INSERT INTO interest_events (interest_id, kind, reason, payload_json, at) "
            "VALUES (?, 'renewed', ?, '{}', datetime('now'))",
            (interest_id, reason),
        )


def load_interest(store: Store, interest_id: str) -> InterestEntry:
    row = store.one("SELECT * FROM interest_entries WHERE id = ?", interest_id)
    if row is None:
        raise KeyError(interest_id)
    notice_ids = tuple(
        r["notice_id"]
        for r in store.query(
            "SELECT notice_id FROM interest_notices WHERE interest_id = ? ORDER BY notice_id",
            interest_id,
        )
    )
    outcomes = tuple(
        (r["kind"], r["target_id"])
        for r in store.query(
            "SELECT kind, target_id FROM interest_outcomes WHERE interest_id = ? "
            "ORDER BY kind, target_id",
            interest_id,
        )
    )
    return InterestEntry(
        id=row["id"],
        subject=row["subject"],
        rationale=row["rationale"],
        diet_epoch_id=row["diet_epoch_id"],
        topic_targets=tuple(sorted(json.loads(row["topic_targets_json"]).items())),
        operator_input=row["operator_input"],
        diet_derived=bool(row["diet_derived"]),
        priority=row["priority"],
        window_days=row["window_days"],
        retired=bool(row["retired"]),
        retirement_reason=row["retirement_reason"],
        notice_ids=notice_ids,
        outcomes=outcomes,
    )


def interest_register(store: Store, include_retired: bool = True) -> tuple[InterestEntry, ...]:
    """The operator's full inspection view. Everything, whether or not it was raised."""
    sql = "SELECT id FROM interest_entries"
    if not include_retired:
        sql += " WHERE retired = 0"
    return tuple(
        load_interest(store, row["id"]) for row in store.query(sql + " ORDER BY id")
    )


def events_for(store: Store, interest_id: str) -> tuple[dict[str, Any], ...]:
    return tuple(
        dict(row)
        for row in store.query(
            "SELECT * FROM interest_events WHERE interest_id = ? ORDER BY id", interest_id
        )
    )


def provenance_mix(store: Store) -> dict[str, Any]:
    """Where the register's attention came from.

    Material originating outside the system must dominate. The share is reported
    rather than asserted, because a register that had started feeding on its own
    projections would say so here before anyone noticed it elsewhere.
    """
    rows = store.query(
        "SELECT n.provenance_kind, COUNT(*) AS n FROM notices n "
        "JOIN interest_notices i ON i.notice_id = n.id GROUP BY n.provenance_kind"
    )
    by_kind = {row["provenance_kind"]: row["n"] for row in rows}
    total = sum(by_kind.values())
    external = store.one(
        "SELECT COUNT(DISTINCT n.id) AS n FROM notices n "
        "JOIN interest_notices i ON i.notice_id = n.id "
        "JOIN sightings sg ON sg.artifact_id = n.artifact_id"
    )["n"]
    return {
        "by_provenance_kind": dict(sorted(by_kind.items())),
        "notices_behind_interests": total,
        "externally_sighted": external,
        "external_share": (external / total) if total else None,
        "externally_dominated": bool(total) and external * 2 > total,
    }


def unproductive(store: Store, now: datetime) -> tuple[str, ...]:
    """Live interests past their window with nothing to show."""
    out = []
    for entry in interest_register(store, include_retired=False):
        row = store.one("SELECT opened_at FROM interest_entries WHERE id = ?", entry.id)
        # Both sides through the ledger's timezone. `opened_at` defaults to
        # SQLite's `datetime('now')`, which is UTC, and a caller reaching for
        # `datetime.now()` has a local one — so an interest formed this evening
        # looked seven hours younger or older than it was, and a window measured
        # in days quietly moved by the host's offset from Greenwich.
        opened = from_ledger(row["opened_at"])
        if entry.productive:
            continue
        if as_utc(now) - opened >= timedelta(days=entry.window_days):
            out.append(entry.id)
    return tuple(sorted(out))


def origination_share(store: Store) -> dict[str, Any]:
    """What share of investigations interest actually caused.

    An interest register nothing depends on is indistinguishable from a good one
    until someone counts what it caused.
    """
    total = store.one("SELECT COUNT(*) AS n FROM investigations")["n"]
    by_origin = {
        row["origin"]: row["n"]
        for row in store.query("SELECT origin, COUNT(*) AS n FROM investigations GROUP BY origin")
    }
    originated = by_origin.get("interest", 0)
    return {
        "investigations": total,
        "by_origin": dict(sorted(by_origin.items())),
        "interest_originated": originated,
        "share": (originated / total) if total else None,
    }


def open_originated_investigations(store: Store) -> int:
    row = store.one(
        "SELECT COUNT(*) AS n FROM investigations WHERE origin = 'interest' AND state = 'open'"
    )
    return row["n"] if row else 0
