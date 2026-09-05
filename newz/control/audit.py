"""One place that writes an audit event.

The identifier is built from the action and the target rather than carved out of
whichever id happened to be to hand. Two different actions once produced the
same audit id here — activating `epoch:1` and recording `correction:1` both
reduced to `audit:1` — and the collision surfaced as a unique-constraint
failure. It could as easily have surfaced as one action's record overwriting
another's, which in an audit trail is the failure that matters.
"""

from __future__ import annotations

import hashlib


def audit_id(action: str, target: str) -> str:
    """A stable, collision-resistant id for one action against one target."""
    digest = hashlib.sha256(f"{action}\x1f{target}".encode()).hexdigest()
    return f"audit:{action}:{digest[:12]}"


def record(
    connection,
    *,
    actor: str,
    action: str,
    target: str,
    reason: str,
    preimage: str,
    result: str,
    channel: str = "command",
) -> str:
    """Actor, time, reason, target preimage and result — the same from either
    surface, so the trail does not depend on which one was used."""
    identifier = audit_id(action, target)
    connection.execute(
        "INSERT INTO audit_events (id, at, actor, channel, action, target, reason, preimage, "
        "result) VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?)",
        (identifier, actor, channel, action, target, reason, preimage, result),
    )
    return identifier
