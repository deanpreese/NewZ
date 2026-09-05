"""Search and browse over the record, for the operator rather than the reader.

The reader browses the surface — only what is published. This browses the store,
which is everything, and is therefore a command-surface facility: `SPEC.md`
section 2.1 keeps the whole record inspectable whether or not it was ever
raised, and that is what this is for.
"""

from __future__ import annotations

from typing import Any

from newz.store.db import Store


def search_claims(
    store: Store,
    *,
    text: str = "",
    state: str = "",
    risk: str = "",
    kind: str = "",
    topic: str = "",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Claims with their current state, filtered by anything that identifies them."""
    sql = [
        "SELECT c.id, c.kind, c.wording, c.risk, c.withdrawn,",
        "  (SELECT a.state FROM assessments a WHERE a.claim_id = c.id",
        "   ORDER BY a.rowid DESC LIMIT 1) AS state,",
        "  (SELECT COUNT(*) FROM edge_events e WHERE e.claim_id = c.id AND e.live = 1",
        "   AND e.admitted = 1) AS live_edges",
        "FROM claims c WHERE 1 = 1",
    ]
    params: list[Any] = []
    if text:
        sql.append("AND c.wording LIKE ?")
        params.append(f"%{text}%")
    if kind:
        sql.append("AND c.kind = ?")
        params.append(kind)
    if risk:
        sql.append("AND c.risk = ?")
        params.append(risk)
    if topic:
        sql.append(
            "AND EXISTS (SELECT 1 FROM edge_events e WHERE e.claim_id = c.id AND e.topic = ?)"
        )
        params.append(topic)
    sql.append("ORDER BY c.id LIMIT ?")
    params.append(limit)

    rows = [dict(row) for row in store.query(" ".join(sql), *params)]
    if state:
        rows = [row for row in rows if row["state"] == state]
    return rows


def search_entities(store: Store, text: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """Entities by name. Returns disambiguation data and a count, never a dossier."""
    rows = store.query(
        "SELECT e.id, e.name, e.kind, e.disambiguation, "
        "  (SELECT COUNT(DISTINCT ed.claim_id) FROM assertion_entities ae "
        "   JOIN edge_events ed ON ed.assertion_id = ae.assertion_id "
        "   WHERE ae.entity_id = e.id AND ed.live = 1) AS claims_naming "
        "FROM entities e WHERE e.name LIKE ? ORDER BY e.name LIMIT ?",
        f"%{text}%",
        limit,
    )
    return [dict(row) for row in rows]


def assessment_history_of(store: Store, claim_id: str) -> list[dict[str, Any]]:
    return [
        {
            "state": row["state"],
            "explanation": row["explanation"],
            "supporting_bases": row["supporting_bases"],
            "contradicting_bases": row["contradicting_bases"],
            "policy_version": row["policy_version"],
            "derived_at": row["derived_at"],
        }
        for row in store.query(
            "SELECT * FROM assessments WHERE claim_id = ? ORDER BY rowid", claim_id
        )
    ]


def topics(store: Store) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in store.query(
            "SELECT s.topic, COUNT(DISTINCT sr.id) AS sources FROM sources s "
            "JOIN source_revisions sr ON sr.source_id = s.id GROUP BY s.topic ORDER BY s.topic"
        )
    ]
