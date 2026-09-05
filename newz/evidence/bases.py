"""The basis registry, and the lineage that collapses two bases into one.

Derivation is the mechanism the independence rules exist for. When a second
publication carries the same witness, the two bases are not two origins; they
are one origin reached twice. Recording that as a derivation link is how the
system knows, and the closure over those links becomes an effective
independence group — so the existing rule that group membership blocks
independence does the work, and no justification, operator-verified included,
can make the pair count twice.
"""

from __future__ import annotations

import json

from newz.control import audit
from newz.domain.enums import IndependenceJustification
from newz.domain.records import Basis, IndependenceClaim
from newz.store.db import Store


def record_basis(
    connection,
    basis_id: str,
    origin_kind: str,
    origin_identifier: str,
    resolved: bool,
    independence_group: str | None = None,
) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO bases (id, origin_kind, origin_identifier, resolved, "
        "independence_group, recorded_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        (basis_id, origin_kind, origin_identifier, int(resolved), independence_group),
    )


def record_derivation(connection, basis_id: str, derived_from: str, reason: str) -> None:
    """This basis is downstream of that one. Lineage, not evidence."""
    connection.execute(
        "INSERT OR IGNORE INTO basis_derivations (basis_id, derived_from_basis_id, reason, "
        "recorded_at) VALUES (?, ?, ?, datetime('now'))",
        (basis_id, derived_from, reason),
    )


def record_independence(
    connection,
    claim_id: str,
    basis_a: str,
    basis_b: str,
    justification: IndependenceJustification,
    evidence: str = "",
    operator_actor: str | None = None,
    operator_reason: str | None = None,
) -> None:
    a, b = sorted((basis_a, basis_b))
    connection.execute(
        "INSERT OR IGNORE INTO independence_claims (id, basis_a, basis_b, justification, "
        "evidence, operator_actor, operator_reason, recorded_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
        (claim_id, a, b, justification.value, evidence, operator_actor, operator_reason),
    )


def correct_basis(
    store: Store,
    correction_id: str,
    basis_id: str,
    actor: str,
    reason: str,
    resolved: bool | None = None,
    independence_group: str | None = None,
) -> None:
    """An operator correcting what a basis is, append-only and reasoned.

    Identity — the origin kind and identifier — cannot be edited even here; a
    basis that turns out to be a different origin is a different basis. What a
    correction may change is whether the origin is resolved and which group it
    belongs to, which are judgments about the same origin.
    """
    if not reason:
        raise ValueError("a basis correction records its reason")
    row = store.one("SELECT * FROM bases WHERE id = ?", basis_id)
    if row is None:
        raise KeyError(basis_id)

    preimage = json.dumps(
        {"resolved": bool(row["resolved"]), "independence_group": row["independence_group"]},
        sort_keys=True,
    )
    new_resolved = row["resolved"] if resolved is None else int(resolved)
    new_group = row["independence_group"] if independence_group is None else independence_group

    with store.write() as connection:
        connection.execute(
            "UPDATE bases SET resolved = ?, independence_group = ? WHERE id = ?",
            (new_resolved, new_group, basis_id),
        )
        connection.execute(
            "INSERT INTO basis_corrections (id, basis_id, actor, reason, preimage, result, "
            "corrected_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                correction_id,
                basis_id,
                actor,
                reason,
                preimage,
                json.dumps(
                    {"resolved": bool(new_resolved), "independence_group": new_group},
                    sort_keys=True,
                ),
            ),
        )
        audit.record(
            connection,
            actor=actor,
            action="correct_basis",
            target=basis_id,
            reason=reason,
            preimage=preimage,
            result="corrected",
        )
        # A correction does not revive a refused edge. Admission was a decision
        # under a policy version against the basis as it stood, and rewriting it
        # would rewrite the decision; the edge is re-evaluated by emitting a new
        # event. What the correction owes is that somebody knows to do it, so
        # the affected edges are named on the outbox rather than remembered.
        affected = [
            row["id"]
            for row in connection.execute(
                "SELECT id FROM edge_events WHERE basis_id = ? AND admitted = 0 ORDER BY id",
                (basis_id,),
            ).fetchall()
        ]
        connection.execute(
            "INSERT INTO outbox (at, kind, subject, payload) VALUES (datetime('now'), ?, ?, ?)",
            (
                "basis_corrected",
                basis_id,
                json.dumps(
                    {"reason": reason, "edges_to_re_evaluate": affected}, sort_keys=True
                ),
            ),
        )


def _derivation_groups(store: Store) -> dict[str, str]:
    """Collapse each derivation lineage into one effective group id.

    Union-find over the links, with the smallest id as the representative so the
    grouping does not depend on the order rows come back in.
    """
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            low, high = sorted((ra, rb))
            parent[high] = low

    for row in store.query(
        "SELECT basis_id, derived_from_basis_id FROM basis_derivations "
        "ORDER BY basis_id, derived_from_basis_id"
    ):
        union(row["basis_id"], row["derived_from_basis_id"])

    return {node: f"lineage:{find(node)}" for node in sorted(parent)}


def load_bases(store: Store) -> dict[str, Basis]:
    """Every basis, with derivation lineage folded into its independence group."""
    lineage = _derivation_groups(store)
    bases: dict[str, Basis] = {}
    for row in store.query("SELECT * FROM bases ORDER BY id"):
        group = row["independence_group"] or lineage.get(row["id"])
        bases[row["id"]] = Basis(
            id=row["id"],
            origin_kind=row["origin_kind"],
            origin_identifier=row["origin_identifier"],
            resolved=bool(row["resolved"]),
            independence_group=group,
        )
    return bases


def load_independence(store: Store) -> tuple[IndependenceClaim, ...]:
    return tuple(
        IndependenceClaim(
            basis_a=row["basis_a"],
            basis_b=row["basis_b"],
            justification=IndependenceJustification(row["justification"]),
            evidence=row["evidence"],
            operator_actor=row["operator_actor"],
            operator_reason=row["operator_reason"],
        )
        for row in store.query("SELECT * FROM independence_claims ORDER BY id")
    )
