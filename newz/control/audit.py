"""One place that writes an audit event.

The identifier has now been wrong twice, in the same way both times: it was
derived from the thing being audited rather than from the event. First two
different actions collided — activating `epoch:1` and recording `correction:1`
both reduced to `audit:1`. Then the same action on the same target collided with
itself, because a claim's risk can be raised on Tuesday and lowered on
Wednesday and both are events.

So the rule, written down rather than rediscovered: **an audit id identifies an
occurrence, not a subject.** It carries the action and the target because that
makes it readable, and a per-target sequence because that makes it unique. Both
collisions surfaced as constraint failures; either could as easily have
surfaced as one record silently overwriting another, which in an audit trail is
the failure that matters.
"""

from __future__ import annotations

import hashlib


def audit_id(action: str, target: str, occurrence: int = 0) -> str:
    """An id for one occurrence of one action against one target."""
    digest = hashlib.sha256(f"{action}\x1f{target}".encode()).hexdigest()
    return f"audit:{action}:{digest[:12]}-{occurrence}"


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
    occurrence = connection.execute(
        "SELECT COUNT(*) FROM audit_events WHERE action = ? AND target = ?", (action, target)
    ).fetchone()[0]
    identifier = audit_id(action, target, occurrence)
    connection.execute(
        "INSERT INTO audit_events (id, at, actor, channel, action, target, reason, preimage, "
        "result) VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?)",
        (identifier, actor, channel, action, target, reason, preimage, result),
    )
    return identifier
