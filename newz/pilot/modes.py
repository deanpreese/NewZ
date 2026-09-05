"""Deployment modes, and the one transition that does not need an operator.

`ARCHITECTURE.md`'s mode table, made executable. Transitions are explicit,
audited and reversible — with two exceptions that run in opposite directions.

**Lockdown may be entered automatically**, on a policy or integrity breach, with
no operator present. `SPEC.md` section 2.1 requires that, and requires equally
that the system cannot clear its own halt: a system that could would be a system
whose halt is a suggestion.

**Shadow is not skippable on the way to Pilot.** The path from Fixture to live
authority runs through a stage where assessments are computed and compared and
nothing is authoritative, because the alternative is discovering a divergence
after it has been believed.
"""

from __future__ import annotations

from enum import StrEnum, unique
from typing import Any

from newz.control.audit import record as audit_record
from newz.store.db import Store
from newz.version import CODE_VERSION


@unique
class DeploymentMode(StrEnum):
    FIXTURE = "fixture"
    SHADOW = "shadow"
    PILOT = "pilot"
    PRODUCTION = "production"
    LOCKDOWN = "lockdown"


#: What each mode does with what it computes. Lockdown is historical inspection
#: only; Shadow computes and withholds everything.
MODE_BEHAVIOUR: dict[DeploymentMode, dict[str, Any]] = {
    DeploymentMode.FIXTURE: {
        "live_acquisition": False,
        "authoritative": True,
        "presentation": "local test output",
    },
    DeploymentMode.SHADOW: {
        "live_acquisition": True,
        "authoritative": False,
        "presentation": "withheld",
    },
    DeploymentMode.PILOT: {
        "live_acquisition": True,
        "authoritative": True,
        "presentation": "local only",
    },
    DeploymentMode.PRODUCTION: {
        "live_acquisition": True,
        "authoritative": True,
        "presentation": "cleared R0-R2; R3 exact-review only",
    },
    DeploymentMode.LOCKDOWN: {
        "live_acquisition": False,
        "authoritative": False,
        "presentation": "historical inspection only",
    },
}

#: The permitted moves. Shadow sits between Fixture and Pilot on purpose.
TRANSITIONS: dict[DeploymentMode, frozenset[DeploymentMode]] = {
    DeploymentMode.FIXTURE: frozenset({DeploymentMode.SHADOW, DeploymentMode.LOCKDOWN}),
    DeploymentMode.SHADOW: frozenset(
        {DeploymentMode.PILOT, DeploymentMode.FIXTURE, DeploymentMode.LOCKDOWN}
    ),
    DeploymentMode.PILOT: frozenset(
        {DeploymentMode.PRODUCTION, DeploymentMode.SHADOW, DeploymentMode.LOCKDOWN}
    ),
    DeploymentMode.PRODUCTION: frozenset({DeploymentMode.PILOT, DeploymentMode.LOCKDOWN}),
    # Leaving lockdown is an operator act and returns to the mode that is safe
    # to resume in, never straight back to production.
    DeploymentMode.LOCKDOWN: frozenset({DeploymentMode.FIXTURE, DeploymentMode.SHADOW}),
}


class TransitionRefused(Exception):
    """A move the mode machine does not have, or one the system may not make."""


def current_mode(store: Store) -> DeploymentMode:
    row = store.one("SELECT to_mode FROM mode_transitions ORDER BY rowid DESC LIMIT 1")
    return DeploymentMode(row["to_mode"]) if row else DeploymentMode.FIXTURE


def transition(
    store: Store,
    *,
    transition_id: str,
    to: DeploymentMode,
    actor: str,
    reason: str,
    automatic: bool = False,
) -> DeploymentMode:
    """Move modes, or refuse and say why.

    Every transition but the automatic entry into lockdown needs an operator.
    Leaving lockdown needs one absolutely: the system may not clear its own halt.
    """
    from newz.pilot.violations import open_violations

    now = current_mode(store)
    if to not in TRANSITIONS[now]:
        raise TransitionRefused(f"{now.value} -> {to.value} is not a transition")
    if not reason.strip():
        raise TransitionRefused("a mode transition records why")

    if now is DeploymentMode.LOCKDOWN:
        if automatic or not actor or actor.startswith("system"):
            raise TransitionRefused(
                "the system cannot clear its own halt: leaving lockdown is an operator act"
            )
        unresolved = open_violations(store)
        if unresolved:
            raise TransitionRefused(
                f"{len(unresolved)} violation(s) have no recorded cause, fix and fixture; "
                "release requires a correction, not an argument"
            )

    if automatic and to is not DeploymentMode.LOCKDOWN:
        raise TransitionRefused("lockdown is the only mode the system may enter on its own")

    if to is DeploymentMode.PILOT and now is not DeploymentMode.SHADOW:
        raise TransitionRefused(
            "the path to authoritative live assessment runs through shadow, where a "
            "divergence is found before it is believed"
        )

    with store.write() as connection:
        connection.execute(
            "INSERT INTO mode_transitions (id, from_mode, to_mode, actor, reason, automatic, "
            "code_version, at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (transition_id, now.value, to.value, actor, reason, int(automatic), CODE_VERSION),
        )
        audit_record(
            connection,
            actor=actor,
            action="mode_transition",
            target=to.value,
            reason=reason,
            preimage=now.value,
            result=to.value,
            channel="system" if automatic else "command",
        )
    return to


def enter_lockdown(store: Store, transition_id: str, reason: str) -> DeploymentMode:
    """The automatic halt. No operator, and the system cannot undo it."""
    now = current_mode(store)
    if now is DeploymentMode.LOCKDOWN:
        return now
    return transition(
        store,
        transition_id=transition_id,
        to=DeploymentMode.LOCKDOWN,
        actor="system",
        reason=reason,
        automatic=True,
    )


def behaviour(store: Store) -> dict[str, Any]:
    return {"mode": current_mode(store).value, **MODE_BEHAVIOUR[current_mode(store)]}


def may_publish(store: Store) -> bool:
    return MODE_BEHAVIOUR[current_mode(store)]["presentation"] not in (
        "withheld",
        "historical inspection only",
    )


def assessments_are_authoritative(store: Store) -> bool:
    return bool(MODE_BEHAVIOUR[current_mode(store)]["authoritative"])


def history(store: Store) -> tuple[dict[str, Any], ...]:
    return tuple(
        dict(row) for row in store.query("SELECT * FROM mode_transitions ORDER BY rowid")
    )
