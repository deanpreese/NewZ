"""The daily reports, and the one figure that must escalate rather than be absorbed.

`PLAN.md` Phase 5 items 5 through 8. The funnel is the spine: lead, reserved,
fetched, retained, parsed, asserted, edge admitted or refused, assessment
changed, presentation invalidated. Each stage is counted separately because a
system that reports "reads" has hidden the place where the loss happened.

Offered and retained shares are reported **separately**, because they answer
different questions: the offered menu is what the diet put in front of the
system, and the retained share is what became capable of being evidence.

One figure escalates rather than being absorbed: the share of claims held below
`supported` or `refuted` **solely** by unknown basis independence. Sustained
above 90%, that is not a strict system working; it is a design finding that the
evidence rules are unsatisfiable in practice, and `PLAN.md` requires it be put
in front of the operator rather than reported into a dashboard nobody reads.
"""

from __future__ import annotations

from typing import Any

from newz.store.db import Store

UNKNOWN_INDEPENDENCE_ESCALATION_SHARE = 0.90


def funnel(store: Store, local_day: str) -> dict[str, int]:
    """One local day, stage by stage."""
    day = f"{local_day}%"

    def count(sql: str, *params: Any) -> int:
        row = store.one(sql, *params)
        return row["n"] if row else 0

    return {
        "leads": count("SELECT COUNT(*) AS n FROM leads WHERE created_at LIKE ?", day),
        "reserved": count("SELECT COUNT(*) AS n FROM reservations WHERE local_day = ?", local_day),
        "fetched": count("SELECT COUNT(*) AS n FROM attempts WHERE started_at LIKE ?", day),
        "retained": count(
            "SELECT COUNT(*) AS n FROM attempts WHERE started_at LIKE ? AND outcome = 'retained'",
            day,
        ),
        "refused": count(
            "SELECT COUNT(*) AS n FROM attempts WHERE started_at LIKE ? AND outcome = 'refused'",
            day,
        ),
        "errored": count(
            "SELECT COUNT(*) AS n FROM attempts WHERE started_at LIKE ? AND outcome = 'error'", day
        ),
        "parsed": count(
            "SELECT COUNT(*) AS n FROM parse_executions WHERE executed_at LIKE ?", day
        ),
        "asserted": count("SELECT COUNT(*) AS n FROM assertions WHERE recorded_at LIKE ?", day),
        "edges_admitted": count(
            "SELECT COUNT(*) AS n FROM edge_events WHERE recorded_at LIKE ? AND admitted = 1", day
        ),
        "edges_refused": count(
            "SELECT COUNT(*) AS n FROM edge_events WHERE recorded_at LIKE ? AND admitted = 0", day
        ),
        "assessments": count("SELECT COUNT(*) AS n FROM assessments WHERE derived_at LIKE ?", day),
        "cards_invalidated": count(
            "SELECT COUNT(*) AS n FROM outbox WHERE kind = 'cards_invalidated' AND at LIKE ?", day
        ),
    }


def concentration(store: Store, window_days: int = 30) -> dict[str, Any]:
    """Publisher and basis concentration over retained reads. An operator figure."""
    publishers = store.query(
        "SELECT p.name AS publisher, COUNT(*) AS n FROM sightings sg "
        "JOIN source_revisions sr ON sr.id = sg.source_revision_id "
        "JOIN sources s ON s.id = sr.source_id "
        "JOIN publishers p ON p.id = s.publisher_id "
        f"WHERE sg.observed_at > datetime('now', '-{int(window_days)} days') "
        "GROUP BY p.name ORDER BY n DESC"
    )
    total = sum(row["n"] for row in publishers)
    bases = store.query(
        "SELECT basis_id, COUNT(*) AS n FROM edge_events WHERE live = 1 AND admitted = 1 "
        "GROUP BY basis_id ORDER BY n DESC"
    )
    edges = sum(row["n"] for row in bases)
    return {
        "retained_reads": total,
        "publisher_shares": {
            row["publisher"]: round(row["n"] / total, 4) for row in publishers
        }
        if total
        else {},
        "top_publisher_share": round(publishers[0]["n"] / total, 4) if total else None,
        "basis_shares": {row["basis_id"]: round(row["n"] / edges, 4) for row in bases}
        if edges
        else {},
        "top_basis_share": round(bases[0]["n"] / edges, 4) if edges else None,
    }


def offered_and_retained_shares(store: Store) -> dict[str, Any]:
    """Two different questions, reported as two different answers."""
    offered = store.query(
        "SELECT sr.role AS role, s.topic AS topic, COUNT(*) AS n FROM diet_epoch_sources d "
        "JOIN source_revisions sr ON sr.id = d.source_revision_id "
        "JOIN sources s ON s.id = sr.source_id "
        "WHERE d.epoch_id = (SELECT id FROM diet_epochs ORDER BY epoch DESC LIMIT 1) "
        "GROUP BY sr.role, s.topic"
    )
    retained = store.query(
        "SELECT sr.role AS role, s.topic AS topic, COUNT(*) AS n FROM sightings sg "
        "JOIN source_revisions sr ON sr.id = sg.source_revision_id "
        "JOIN sources s ON s.id = sr.source_id GROUP BY sr.role, s.topic"
    )

    def shares(rows, key):
        totals: dict[str, int] = {}
        for row in rows:
            totals[row[key]] = totals.get(row[key], 0) + row["n"]
        total = sum(totals.values())
        return {k: round(v / total, 4) for k, v in sorted(totals.items())} if total else {}

    return {
        "offered_role_share": shares(offered, "role"),
        "offered_topic_share": shares(offered, "topic"),
        "retained_role_share": shares(retained, "role"),
        "retained_topic_share": shares(retained, "topic"),
        "note": (
            "Offered is what the diet put in front of the system. Retained is what "
            "became capable of being evidence. They are different questions."
        ),
    }


def held_below_by_unknown_independence(store: Store) -> dict[str, Any]:
    """The leading indicator that the evidence rules are unsatisfiable in practice.

    A claim counts here when it has countable edges in one direction, more
    distinct bases cited than counted, and a state below `supported` or
    `refuted`. Sustained above 90% this is a design finding, and `PLAN.md`
    requires it be escalated to the operator rather than absorbed.
    """
    from newz.evidence.assess import evidence_input
    from newz.policy.independence import count_independent_bases

    below = []
    considered = []
    for row in store.query("SELECT id FROM claims ORDER BY id"):
        claim_id = row["id"]
        assessment = store.one(
            "SELECT state FROM assessments WHERE claim_id = ? ORDER BY rowid DESC LIMIT 1",
            claim_id,
        )
        if assessment is None:
            continue
        if assessment["state"] in ("supported", "refuted", "withdrawn"):
            continue
        inputs = evidence_input(store, claim_id)
        for relation in ("supports", "contradicts"):
            edges = [edge for edge in inputs.edges if edge.relation.value == relation]
            if not edges:
                continue
            considered.append(claim_id)
            counted, _ = count_independent_bases(
                [edge.basis_id for edge in edges], inputs.bases, inputs.independence
            )
            distinct = len({edge.basis_id for edge in edges})
            if distinct > counted:
                below.append(claim_id)
            break

    unique_considered = sorted(set(considered))
    share = (len(set(below)) / len(unique_considered)) if unique_considered else None
    escalate = share is not None and share > UNKNOWN_INDEPENDENCE_ESCALATION_SHARE
    return {
        "claims_considered": len(unique_considered),
        "held_below_by_unknown_independence": sorted(set(below)),
        "share": round(share, 4) if share is not None else None,
        "escalation_threshold": UNKNOWN_INDEPENDENCE_ESCALATION_SHARE,
        "escalate": escalate,
        "finding": (
            "the evidence rules may be unsatisfiable in practice rather than merely "
            "strict; this is a design finding and must reach the operator"
        )
        if escalate
        else "",
    }


def daily_report(store: Store, local_day: str) -> dict[str, Any]:
    """The operator's daily view. Everything, including what is withheld from
    the system itself."""
    from datetime import datetime

    from newz.pilot.modes import current_mode
    from newz.pilot.violations import open_violations
    from newz.reckoning.checks import operator_report
    from newz.research.tasks import overdue_counterparts

    return {
        "local_day": local_day,
        "mode": current_mode(store).value,
        "funnel": funnel(store, local_day),
        "concentration": concentration(store),
        "shares": offered_and_retained_shares(store),
        "unknown_independence": held_below_by_unknown_independence(store),
        "overdue_counterparts": list(
            overdue_counterparts(store, datetime.fromisoformat(f"{local_day}T23:59:59"))
        ),
        "parser_failures": store.one(
            "SELECT COUNT(*) AS n FROM parse_executions WHERE failures_json != '[]'"
        )["n"],
        "open_violations": [violation.as_record() for violation in open_violations(store)],
        "system_metrics": operator_report(store),
    }
