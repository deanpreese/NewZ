"""The diet self-report: the shape of the system's own reading.

`SPEC.md` section 9.1 requires the system to be able to state the balance of
roles, topics and publishers it has actually retained, which perspectives are
under-represented in it, and where its current interests track the diet's
targets rather than diverging from them. It MUST NOT treat its source catalog as
the world.

Section 9.4 makes most figures unreachable by the system. This one is not among
them, and the distinction is stated there: a figure the system could move by
behaving differently is a score and is withheld; a figure describing conditions
set for it is description and is shown. The diet is configured by the operator
and the system cannot change it, so reading its own skew is the opposite failure
mode from optimising a score.
"""

from __future__ import annotations

import json
from typing import Any

from newz.store.db import Store


def _share(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    return {key: round(value / total, 4) for key, value in sorted(counts.items())} if total else {}


def diet_self_report(store: Store, epoch_id: str = "", window_days: int = 30) -> dict[str, Any]:
    """What has actually been retained, against what the diet asked for."""
    epoch = (
        store.one("SELECT * FROM diet_epochs WHERE id = ?", epoch_id)
        if epoch_id
        else store.one("SELECT * FROM diet_epochs ORDER BY epoch DESC LIMIT 1")
    )
    targets = json.loads(epoch["budget_json"]) if epoch else {}

    retained = store.query(
        "SELECT sr.role AS role, s.topic AS topic, p.name AS publisher, COUNT(*) AS n "
        "FROM sightings sg "
        "JOIN source_revisions sr ON sr.id = sg.source_revision_id "
        "JOIN sources s ON s.id = sr.source_id "
        "JOIN publishers p ON p.id = s.publisher_id "
        f"WHERE sg.observed_at > datetime('now', '-{int(window_days)} days') "
        "GROUP BY sr.role, s.topic, p.name"
    )
    roles: dict[str, int] = {}
    topics: dict[str, int] = {}
    publishers: dict[str, int] = {}
    for row in retained:
        roles[row["role"]] = roles.get(row["role"], 0) + row["n"]
        topics[row["topic"]] = topics.get(row["topic"], 0) + row["n"]
        publishers[row["publisher"]] = publishers.get(row["publisher"], 0) + row["n"]

    enabled_topics = {
        row["topic"]
        for row in store.query(
            "SELECT DISTINCT s.topic FROM diet_epoch_sources d "
            "JOIN source_revisions sr ON sr.id = d.source_revision_id "
            "JOIN sources s ON s.id = sr.source_id "
            "WHERE d.epoch_id = ?",
            epoch["id"] if epoch else "",
        )
    }
    # Under-represented means enabled and unread, which is the honest form of
    # the question. A perspective the catalog never had is not under-represented
    # in the reading; it is absent from the diet, and that is a different
    # sentence the operator needs to hear differently.
    under_represented = sorted(enabled_topics - set(topics))

    tracking = []
    diverging = []
    for row in store.query(
        "SELECT e.id, e.subject, e.diet_derived FROM interest_entries e WHERE e.retired = 0 "
        "ORDER BY e.id"
    ):
        (tracking if row["diet_derived"] else diverging).append(
            {"interest_id": row["id"], "subject": row["subject"]}
        )

    return {
        "window_days": window_days,
        "epoch": epoch["epoch"] if epoch else None,
        "budget": targets,
        "retained_reads": sum(roles.values()),
        "roles": dict(sorted(roles.items())),
        "role_share": _share(roles),
        "topics": dict(sorted(topics.items())),
        "topic_share": _share(topics),
        "publishers": dict(sorted(publishers.items())),
        "publisher_share": _share(publishers),
        "enabled_topics": sorted(enabled_topics),
        "under_represented": under_represented,
        "interests_tracking_the_diet": tracking,
        "interests_diverging_from_the_diet": diverging,
        "note": (
            "This is the shape of what was read, not the shape of the world. "
            "The catalog is a choice, and an absence here is as likely to be a "
            "gap in the diet as a gap in the record."
        ),
    }
