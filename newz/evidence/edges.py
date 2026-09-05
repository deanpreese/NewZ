"""Admitting an edge, and writing down why.

The decision is `newz.policy.promotion.evaluate_edge`, which is pure and knows
nothing about a store. This module loads what it needs, asks, and records the
answer along with an attestation per named predicate — so a refusal is a row
with its inputs rather than a code path somebody has to re-run in their head.

An edge event is append-only. Withdrawal is a later event, so an admitted edge
and its withdrawal both stay readable, which is what makes a retraction a fact
in the record instead of an absence in it.
"""

from __future__ import annotations

import json
from dataclasses import replace

from newz.domain.enums import AssertionKind, ClaimKind, EdgeRelation, RiskTier, SourceRole
from newz.domain.records import Assertion, Claim, EdgeEvent, Span
from newz.evidence.bases import load_bases
from newz.policy.promotion import AdmissionResult, evaluate_edge
from newz.store.db import Store
from newz.version import POLICY_VERSION


def load_assertion(store: Store, assertion_id: str) -> Assertion | None:
    row = store.one(
        "SELECT a.*, r.role FROM assertions a "
        "JOIN source_revisions r ON r.id = a.source_revision_id WHERE a.id = ?",
        assertion_id,
    )
    if row is None:
        return None
    span = Span(
        artifact_id=row["artifact_id"],
        segment_id=row["segment_id"],
        start=row["offset_start"],
        end=row["offset_end"],
        quote=row["quote"],
        locator=row["locator"],
        # An assertion exists only because its quotation verified at extraction.
        # Re-verification against the segment happens in the inspection path.
        verified=True,
    )
    return Assertion(
        id=row["id"],
        kind=AssertionKind(row["kind"]),
        spans=(span,),
        source_revision_id=row["source_revision_id"],
        role=SourceRole(row["role"]),
        live=bool(row["live"]),
    )


def load_claim(store: Store, claim_id: str) -> Claim | None:
    row = store.one("SELECT * FROM claims WHERE id = ?", claim_id)
    if row is None:
        return None
    return Claim(
        id=row["id"],
        kind=ClaimKind(row["kind"]),
        wording=row["wording"],
        risk=RiskTier(row["risk"]) if row["risk"] else None,
        resolution_horizon=row["resolution_horizon"],
        resolver=row["resolver"],
        withdrawn=bool(row["withdrawn"]),
    )


def admit_edge(
    store: Store,
    *,
    edge_id: str,
    assertion_id: str,
    claim_id: str,
    relation: EdgeRelation,
    basis_id: str,
    risk: RiskTier | None,
    declared_scope: str = "",
    topic: str = "",
    adjudicative_scope_covers_claim: bool | None = None,
    policy_version: str = POLICY_VERSION,
) -> tuple[EdgeEvent, AdmissionResult]:
    """Evaluate one proposed edge and record the event, admitted or refused."""
    assertion = load_assertion(store, assertion_id)
    claim = load_claim(store, claim_id)
    if claim is None:
        raise KeyError(claim_id)
    if assertion is None:
        raise KeyError(assertion_id)
    basis = load_bases(store).get(basis_id)

    edge = EdgeEvent(
        id=edge_id,
        assertion_id=assertion_id,
        claim_id=claim_id,
        relation=relation,
        basis_id=basis_id,
        role=assertion.role,
        assertion_kind=assertion.kind,
        risk=risk,
        policy_version=policy_version,
        admitted=False,
        declared_scope=declared_scope,
        topic=topic,
        adjudicative_scope_covers_claim=adjudicative_scope_covers_claim,
    )
    result = evaluate_edge(edge, claim, assertion, basis)

    with store.write() as connection:
        connection.execute(
            "INSERT INTO edge_events (id, assertion_id, claim_id, relation, basis_id, role, "
            "assertion_kind, risk, policy_version, admitted, live, refusal_reason, "
            "declared_scope, topic, adjudicative_scope_covers_claim, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, datetime('now'))",
            (
                edge_id,
                assertion_id,
                claim_id,
                relation.value,
                basis_id,
                assertion.role.value,
                assertion.kind.value,
                risk.value if risk else None,
                policy_version,
                int(result.admitted),
                result.reason.value if result.reason else None,
                declared_scope,
                topic,
                None
                if adjudicative_scope_covers_claim is None
                else int(adjudicative_scope_covers_claim),
            ),
        )
        connection.executemany(
            "INSERT INTO predicate_attestations (edge_event_id, predicate, held, inputs_json) "
            "VALUES (?, ?, ?, ?)",
            [
                (
                    edge_id,
                    attestation.predicate.value,
                    int(attestation.held),
                    json.dumps(dict(attestation.inputs), sort_keys=True),
                )
                for attestation in result.attestations
            ],
        )

    recorded = replace(
        edge,
        admitted=result.admitted,
        refusal_reason=result.reason,
        attestations=result.attestations,
    )
    return recorded, result


def withdraw_edge(store: Store, edge_id: str, reason: str) -> None:
    """Withdrawal is a later event, never an edit: the admission stays readable."""
    with store.write() as connection:
        cursor = connection.execute(
            "UPDATE edge_events SET live = 0 WHERE id = ? AND live = 1", (edge_id,)
        )
        if cursor.rowcount != 1:
            raise KeyError(f"{edge_id} is not a live edge")
        connection.execute(
            "INSERT INTO outbox (at, kind, subject, payload) VALUES (datetime('now'), ?, ?, ?)",
            ("edge_withdrawn", edge_id, json.dumps({"reason": reason}, sort_keys=True)),
        )


def load_edges(store: Store, claim_id: str) -> tuple[EdgeEvent, ...]:
    """Every live, admitted edge on a claim, in a fixed order."""
    return tuple(
        EdgeEvent(
            id=row["id"],
            assertion_id=row["assertion_id"],
            claim_id=row["claim_id"],
            relation=EdgeRelation(row["relation"]),
            basis_id=row["basis_id"],
            role=SourceRole(row["role"]),
            assertion_kind=AssertionKind(row["assertion_kind"]),
            risk=RiskTier(row["risk"]) if row["risk"] else None,
            policy_version=row["policy_version"],
            admitted=bool(row["admitted"]),
            live=bool(row["live"]),
            declared_scope=row["declared_scope"],
            topic=row["topic"],
            adjudicative_scope_covers_claim=(
                None
                if row["adjudicative_scope_covers_claim"] is None
                else bool(row["adjudicative_scope_covers_claim"])
            ),
        )
        for row in store.query(
            "SELECT * FROM edge_events WHERE claim_id = ? AND live = 1 AND admitted = 1 "
            "ORDER BY id",
            claim_id,
        )
    )
