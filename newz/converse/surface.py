"""The conversational surface, and what it structurally cannot do.

`SPEC.md` section 2.1 splits the operator into two surfaces holding different
powers, and the split is structural rather than a convenience. A conversational
surface cannot display an exact rendered revision together with its full
dependency set, so it must not carry R2 or R3 clearance, ledger correction,
policy activation, or export. The way that is enforced here is that this class
has no method for any of them — `refused_operations()` names them so a person
can read the list, and the test asserts the public API and the list agree.

**Authority comes from the channel, never the message.** A message is
authoritative because it arrived on a pinned channel registered out of band. It
does not become authoritative by naming its sender, by citing a prior approval,
or by any property of its content, and every inbound attachment or quoted body
on the authenticated channel is world data rather than instruction.

**Raising is additive.** The system may choose what to raise. It may not choose
what the operator can see: everything raised here remains inspectable in full
through the command surface, and so does everything not raised.

**The halt does not run through here.** Pausing is offered on this surface as a
convenience, and `SPEC.md` requires a halt that works with this surface
unreachable — that path is the command surface's, and this module cannot be the
only way to stop the system.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from newz.control.audit import record as audit_record
from newz.store.db import Store

#: Named so the refusal is legible, and asserted against the public API by
#: `tests/test_converse.py`.
REFUSED_OPERATIONS = (
    "clearance of R2 or R3 output",
    "correction of the evidence ledger",
    "activation of a policy epoch",
    "export of the record",
    "catalog and diet changes",
    "risk reclassification",
)

RAISEABLE = ("notice", "investigation", "essay", "alert", "surprise")


class SurfaceRefused(Exception):
    """Something this surface does not carry, named rather than silently absent."""


def register_channel(store: Store, channel_id: str, label: str, registered_by: str) -> None:
    """Pin a channel out of band. This is a command-surface act."""
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO pinned_channels (channel_id, label, registered_by, "
            "registered_at, revoked) VALUES (?, ?, ?, datetime('now'), 0)",
            (channel_id, label, registered_by),
        )


@dataclass(frozen=True, slots=True)
class Message:
    channel_id: str
    text: str
    #: What the message says about its sender. Recorded and never believed.
    claims_sender: str = ""
    quoted_body: str = ""


@dataclass(frozen=True, slots=True)
class ConversationalSurface:
    store: Store
    channel_id: str

    # -- authority ---------------------------------------------------------

    def is_authoritative(self, message: Message) -> bool:
        """Whether this message instructs. Only the channel decides."""
        if message.channel_id != self.channel_id:
            return False
        row = self.store.one(
            "SELECT revoked FROM pinned_channels WHERE channel_id = ?", message.channel_id
        )
        return row is not None and not row["revoked"]

    def instruction_from(self, message: Message) -> str:
        """The instruction, or a refusal that says why it was not one."""
        if not self.is_authoritative(message):
            raise SurfaceRefused(
                "an instruction is authoritative because it arrived on the pinned channel; "
                "this one did not"
            )
        if message.quoted_body:
            # A forwarded body on the authenticated channel is world data under
            # section 6. The channel authenticates the operator, not everything
            # the operator was sent.
            raise SurfaceRefused(
                "a quoted or forwarded body is world data and does not instruct, even here"
            )
        return message.text

    # -- raising -----------------------------------------------------------

    def raise_item(self, *, item_id: str, kind: str, target_id: str, summary: str) -> str:
        """Offer something to the operator. Additive to the record, never a filter."""
        if kind not in RAISEABLE:
            raise SurfaceRefused(f"this surface raises {list(RAISEABLE)}, not {kind!r}")
        with self.store.write() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO raised_items (id, kind, target_id, channel, summary, "
                "raised_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (item_id, kind, target_id, self.channel_id, summary),
            )
        return item_id

    def raised(self, unacknowledged_only: bool = False) -> tuple[dict[str, Any], ...]:
        sql = "SELECT * FROM raised_items"
        if unacknowledged_only:
            sql += " WHERE acknowledged_at IS NULL"
        return tuple(dict(row) for row in self.store.query(sql + " ORDER BY id"))

    def acknowledge(self, item_id: str, actor: str) -> None:
        with self.store.write() as connection:
            connection.execute(
                "UPDATE raised_items SET acknowledged_at = datetime('now'), acknowledged_by = ? "
                "WHERE id = ?",
                (actor, item_id),
            )

    # -- pause and resume --------------------------------------------------

    def pause(self, actor: str, reason: str) -> None:
        """Offered here as a convenience. The halt that must work is elsewhere."""
        self._set_state("acquisition", "paused", actor, reason)

    def resume(self, actor: str, reason: str) -> None:
        self._set_state("acquisition", "running", actor, reason)

    def state(self, key: str) -> str:
        row = self.store.one("SELECT value FROM surface_state WHERE key = ?", key)
        return row["value"] if row else "running"

    def _set_state(self, key: str, value: str, actor: str, reason: str) -> None:
        with self.store.write() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO surface_state (key, value, changed_by, reason, changed_at) "
                "VALUES (?, ?, ?, ?, datetime('now'))",
                (key, value, actor, reason),
            )
            audit_record(
                connection,
                actor=actor,
                action=f"{key}_{value}",
                target=key,
                reason=reason,
                preimage=json.dumps({"channel": self.channel_id}),
                result=value,
                channel="conversational",
            )

    # -- what this surface does not carry ----------------------------------

    @staticmethod
    def refused_operations() -> tuple[str, ...]:
        """What lives on the command surface, and why it is not here."""
        return REFUSED_OPERATIONS

    def refuse(self, operation: str) -> None:
        """Explicitly decline an operation, so the refusal is legible."""
        raise SurfaceRefused(
            f"{operation} is a command-surface operation: a conversational surface cannot "
            "display an exact rendered revision with its full dependency set, so it does "
            "not carry decisions that need one"
        )
