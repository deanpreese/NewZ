"""What a card rests on, and what happens when one of those things moves.

`SPEC.md` section 10: a renderer resolves cited ids at build time and refuses
stale, withdrawn or uncleared dependencies. The validator here is the refusal,
and it is deliberately a check against the live graph rather than a flag somebody
set — a card marked fresh is a claim about the world, and this goes and looks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from newz.store.db import Store


@dataclass(frozen=True, slots=True)
class DependencyFailure:
    kind: str
    dependency_id: str
    reason: str

    def as_record(self) -> dict[str, Any]:
        return {"kind": self.kind, "dependency_id": self.dependency_id, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class DependencyReport:
    revision_id: str
    ok: bool
    failures: tuple[DependencyFailure, ...] = ()

    def as_record(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "ok": self.ok,
            "failures": [failure.as_record() for failure in self.failures],
        }


def validate_dependencies(store: Store, revision_id: str) -> DependencyReport:
    """Walk what the revision cited and check each one is still what it was."""
    row = store.one("SELECT * FROM card_revisions WHERE id = ?", revision_id)
    if row is None:
        raise KeyError(revision_id)

    failures: list[DependencyFailure] = []
    for dependency in store.query(
        "SELECT kind, dependency_id FROM card_dependencies WHERE card_revision_id = ? "
        "ORDER BY kind, dependency_id",
        revision_id,
    ):
        kind, identifier = dependency["kind"], dependency["dependency_id"]
        if kind == "edge":
            edge = store.one("SELECT live, admitted FROM edge_events WHERE id = ?", identifier)
            if edge is None:
                failures.append(DependencyFailure(kind, identifier, "edge no longer exists"))
            elif not edge["live"]:
                failures.append(DependencyFailure(kind, identifier, "edge withdrawn"))
            elif not edge["admitted"]:
                failures.append(DependencyFailure(kind, identifier, "edge not admitted"))
        elif kind == "claim":
            claim = store.one("SELECT withdrawn FROM claims WHERE id = ?", identifier)
            if claim is None:
                failures.append(DependencyFailure(kind, identifier, "claim no longer exists"))
            elif claim["withdrawn"]:
                failures.append(DependencyFailure(kind, identifier, "claim withdrawn"))
        elif kind == "assessment":
            claim_id, _, policy_version = identifier.partition("@")
            current = store.one(
                "SELECT policy_version, state FROM assessments WHERE claim_id = ? "
                "ORDER BY rowid DESC LIMIT 1",
                claim_id,
            )
            if current is None:
                failures.append(DependencyFailure(kind, identifier, "no assessment"))
            elif current["policy_version"] != policy_version:
                failures.append(
                    DependencyFailure(
                        kind,
                        identifier,
                        f"assessment now under policy {current['policy_version']}",
                    )
                )
            elif current["state"] != row["state"]:
                failures.append(
                    DependencyFailure(kind, identifier, f"state is now {current['state']}")
                )
        elif kind == "artifact":
            artifact = store.one("SELECT id FROM artifacts WHERE id = ?", identifier)
            if artifact is None:
                failures.append(DependencyFailure(kind, identifier, "artifact missing"))

    # Risk is not a dependency row; it is a property of the claim the card
    # rendered under, and a card built at R1 that is now R3 is stale in the way
    # that matters most.
    claim_risk = store.one(
        "SELECT risk FROM claims WHERE id = ?", row["claim_id"]
    )
    if claim_risk is not None and (claim_risk["risk"] or "R3") != row["risk"]:
        failures.append(
            DependencyFailure(
                "risk", row["claim_id"], f"risk is now {claim_risk['risk'] or 'R3'}"
            )
        )

    return DependencyReport(revision_id=revision_id, ok=not failures, failures=tuple(failures))


def dependents_of(store: Store, kind: str, dependency_id: str) -> tuple[str, ...]:
    """Live card revisions that cited this thing."""
    return tuple(
        row["card_revision_id"]
        for row in store.query(
            "SELECT d.card_revision_id FROM card_dependencies d "
            "JOIN card_revisions r ON r.id = d.card_revision_id "
            "WHERE d.kind = ? AND d.dependency_id = ? AND r.live = 1 "
            "ORDER BY d.card_revision_id",
            kind,
            dependency_id,
        )
    )


def invalidate_dependents(
    store: Store, kind: str, dependency_id: str, reason: str
) -> tuple[str, ...]:
    """Mark every live card that cited this thing as needing a rebuild.

    Invalidation does not delete the revision. The page that was published is
    what was published, and a correction says so; removing it would leave the
    reader with no way to know what they had read.
    """
    affected = dependents_of(store, kind, dependency_id)
    if not affected:
        return ()
    with store.write() as connection:
        connection.execute(
            "INSERT INTO outbox (at, kind, subject, payload) VALUES (datetime('now'), ?, ?, ?)",
            (
                "cards_invalidated",
                dependency_id,
                json.dumps({"reason": reason, "revisions": list(affected)}, sort_keys=True),
            ),
        )
    return affected


def pending_rebuilds(store: Store) -> tuple[str, ...]:
    """Live revisions whose dependencies no longer validate."""
    stale = []
    for row in store.query("SELECT id FROM card_revisions WHERE live = 1 ORDER BY id"):
        if not validate_dependencies(store, row["id"]).ok:
            stale.append(row["id"])
    return tuple(stale)
