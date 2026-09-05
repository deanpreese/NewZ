"""Artifact to span to assertion to edge to claim to assessment, and back.

Gate 2 asks that every state be explainable without reading model
chain-of-thought or trusting generated prose. This is what that looks like in
practice: a traversal over rows, where every step names the record it came from,
and where the quotation is re-verified against the retained segment at read time
rather than believed because a column says it verified once.
"""

from __future__ import annotations

import json
from typing import Any

from newz.domain.records import Span
from newz.evidence.assess import assessment_history, current_assessment
from newz.parse.spans import verify_span
from newz.parse.store import segments_for
from newz.store.db import Store


def trace_claim(store: Store, claim_id: str) -> dict[str, Any]:
    """Everything behind one claim's current state, in one readable structure."""
    claim = store.one("SELECT * FROM claims WHERE id = ?", claim_id)
    if claim is None:
        raise KeyError(claim_id)

    assessment = current_assessment(store, claim_id)
    countable = set(assessment.countable_edge_ids) if assessment else set()

    edges: list[dict[str, Any]] = []
    for row in store.query(
        "SELECT * FROM edge_events WHERE claim_id = ? ORDER BY id", claim_id
    ):
        assertion = store.one("SELECT * FROM assertions WHERE id = ?", row["assertion_id"])
        entry: dict[str, Any] = {
            "edge_id": row["id"],
            "relation": row["relation"],
            "role": row["role"],
            "assertion_kind": row["assertion_kind"],
            "basis_id": row["basis_id"],
            "risk": row["risk"],
            "admitted": bool(row["admitted"]),
            "live": bool(row["live"]),
            "refusal_reason": row["refusal_reason"],
            "counted": row["id"] in countable,
            "policy_version": row["policy_version"],
            "predicates": {
                attestation["predicate"]: {
                    "held": bool(attestation["held"]),
                    "inputs": json.loads(attestation["inputs_json"]),
                }
                for attestation in store.query(
                    "SELECT * FROM predicate_attestations WHERE edge_event_id = ? "
                    "ORDER BY predicate",
                    row["id"],
                )
            },
        }
        if assertion is not None:
            entry["assertion"] = _assertion_entry(store, assertion)
        edges.append(entry)

    basis_ids = sorted({edge["basis_id"] for edge in edges})
    bases = [
        dict(store.one("SELECT * FROM bases WHERE id = ?", basis_id) or {}) for basis_id in basis_ids
    ]

    return {
        "claim": {
            "id": claim["id"],
            "kind": claim["kind"],
            "wording": claim["wording"],
            "risk": claim["risk"],
        },
        "assessment": (
            {
                "state": assessment.state.value,
                "supporting_bases": assessment.supporting_bases,
                "contradicting_bases": assessment.contradicting_bases,
                "explanation": assessment.explanation,
                "policy_version": assessment.policy_version,
                "code_version": assessment.code_version,
                "blocked_lanes": [
                    [lane.value, state.value, reason]
                    for lane, state, reason in assessment.blocked_lanes
                ],
            }
            if assessment
            else None
        ),
        "history": [
            {"state": entry.state.value, "explanation": entry.explanation}
            for entry in assessment_history(store, claim_id)
        ],
        "edges": edges,
        "bases": bases,
        "independence": [
            dict(row)
            for row in store.query(
                "SELECT * FROM independence_claims WHERE basis_a IN "
                f"({','.join('?' * len(basis_ids))}) OR basis_b IN "
                f"({','.join('?' * len(basis_ids))}) ORDER BY id",
                *basis_ids,
                *basis_ids,
            )
        ]
        if basis_ids
        else [],
        "tasks": [
            {"lane": row["lane"], "state": row["state"], "reason": row["state_reason"]}
            for row in store.query(
                "SELECT * FROM tasks WHERE claim_id = ? ORDER BY lane, id", claim_id
            )
        ],
    }


def _assertion_entry(store: Store, assertion) -> dict[str, Any]:
    """One assertion, with its quotation checked against the segment right now."""
    span = Span(
        artifact_id=assertion["artifact_id"],
        segment_id=assertion["segment_id"],
        start=assertion["offset_start"],
        end=assertion["offset_end"],
        quote=assertion["quote"],
        locator=assertion["locator"],
        verified=True,
    )
    verification = verify_span(span, segments_for(store, assertion["artifact_id"]))
    sighting = store.one(
        "SELECT s.id, s.observed_at, r.final_url FROM sightings s "
        "JOIN responses r ON r.id = s.response_id WHERE s.artifact_id = ? "
        "ORDER BY s.observed_at LIMIT 1",
        assertion["artifact_id"],
    )
    return {
        "id": assertion["id"],
        "kind": assertion["kind"],
        "quote": assertion["quote"],
        "locator": assertion["locator"],
        "artifact_id": assertion["artifact_id"],
        "segment_id": assertion["segment_id"],
        "source_revision_id": assertion["source_revision_id"],
        "live": bool(assertion["live"]),
        # Re-checked at read time. A column asserting that a quotation verified
        # once is a claim about the past; this is the check itself.
        "quote_verifies_now": bool(verification),
        "quote_failure": verification.failure.value if verification.failure else None,
        "first_seen_at": sighting["observed_at"] if sighting else None,
        "retrieved_from": sighting["final_url"] if sighting else None,
    }


def explain(store: Store, claim_id: str) -> str:
    """The same thing as prose, for a person reading rather than a program.

    Composed entirely from rows. Nothing here asks a model to explain anything,
    which is what Gate 2 means by explainable without trusting generated prose.
    """
    trace = trace_claim(store, claim_id)
    claim = trace["claim"]
    assessment = trace["assessment"]
    lines = [f"{claim['id']} ({claim['kind']}, risk {claim['risk'] or 'unset'})", claim["wording"], ""]

    if assessment is None:
        lines.append("No assessment has been derived.")
        return "\n".join(lines)

    lines.append(
        f"State: {assessment['state']} — {assessment['explanation']} "
        f"(policy {assessment['policy_version']}, code {assessment['code_version']})"
    )
    lines.append(
        f"Independent bases: {assessment['supporting_bases']} supporting, "
        f"{assessment['contradicting_bases']} contradicting"
    )
    lines.append("")

    for edge in trace["edges"]:
        assertion = edge.get("assertion")
        head = f"  [{'counted' if edge['counted'] else 'not counted'}] {edge['relation']}"
        if not edge["admitted"]:
            head += f" — refused: {edge['refusal_reason']}"
        elif not edge["live"]:
            head += " — withdrawn"
        lines.append(head)
        if assertion:
            lines.append(f"      {assertion['kind']} by {edge['role']} at {assertion['locator']}")
            lines.append(f"      “{assertion['quote']}”")
            lines.append(
                f"      basis {edge['basis_id']}; quote verifies now: "
                f"{assertion['quote_verifies_now']}"
            )

    if trace["tasks"]:
        lines.append("")
        lines.append("  Evidence lanes:")
        for task in trace["tasks"]:
            suffix = f" ({task['reason']})" if task["reason"] else ""
            lines.append(f"      {task['lane']}: {task['state']}{suffix}")

    return "\n".join(lines)
