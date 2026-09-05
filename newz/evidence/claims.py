"""Changing a claim's risk, which is the one claim field policy guards.

`SPEC.md` section 8 makes risk monotonic within an automated operation: a model
or a worker may raise it, and lowering it takes a reasoned operator action. That
rule was pure until now — `newz.policy.risk.revise` decided it and nothing
persisted it. This is where it reaches the store.

Both directions invalidate. Raising risk can move a claim from publishable to
approval-gated, and lowering it can move output that was withheld into reach, so
either way what was projected under the old tier is stale.
"""

from __future__ import annotations

import json

from newz.control.audit import record as audit_record
from newz.domain.enums import RiskTier
from newz.domain.records import OperatorAction
from newz.policy.risk import revise
from newz.store.db import Store


def reclassify_claim_risk(
    store: Store,
    claim_id: str,
    to: RiskTier,
    *,
    actor: str = "system",
    operator_action: OperatorAction | None = None,
) -> RiskTier:
    """Raise or lower a claim's risk, enforcing the monotonicity rule.

    A lowering without a reasoned operator action raises `RiskLoweringRefused`,
    and that refusal is what an escalation attempt looks like from here: the
    caller is asking for an effective risk it is not entitled to set.
    """
    row = store.one("SELECT risk FROM claims WHERE id = ?", claim_id)
    if row is None:
        raise KeyError(claim_id)
    current = RiskTier(row["risk"]) if row["risk"] else RiskTier.R3

    # Raises on a lowering with no reasoned operator action.
    resolved = revise(current, to, operator_action)

    with store.write() as connection:
        connection.execute("UPDATE claims SET risk = ? WHERE id = ?", (resolved.value, claim_id))
        audit_record(
            connection,
            actor=operator_action.actor if operator_action else actor,
            action="reclassify_claim_risk",
            target=claim_id,
            reason=operator_action.reason if operator_action else "raised by policy",
            preimage=current.value,
            result=resolved.value,
            channel="command" if operator_action else "system",
        )
        connection.execute(
            "INSERT INTO outbox (at, kind, subject, payload) VALUES (datetime('now'), ?, ?, ?)",
            (
                "risk_changed",
                claim_id,
                json.dumps({"from": current.value, "to": resolved.value}, sort_keys=True),
            ),
        )
    return resolved
