"""A metric's meaning is pinned, and changing it breaks the series on purpose
(P4 epic E2.8).

**This has already happened once.** "Novelty" named two different quantities in
this codebase — the Perspective development share (added+revised over held) and
`novelty_against_history`'s embedding cosine against prior advances. Both were
reported, and nothing objected, because a metric's meaning lived only in the
head of whoever last read the code. The 3.2% quoted throughout P3 is the first
one; the second is a different number with the same name.

**A version pins the meaning, and a change ends the series.** Comparing a figure
to one computed a different way is not a delta, it is two numbers subtracted.
So the baseline lookup is scoped to the current definition, the prior readings
stay in the store labelled with the definition that produced them, and the seam
is recorded with the reason it exists.

**A version bump requires a reason.** A silent bump would reset a baseline with
no account of why the old one stopped meaning anything, which is the failure
this epic exists to prevent wearing a smaller hat.
"""

from __future__ import annotations

import sqlite3
import time

import yaml

from newz.evidence.grades import REGISTRY, grade_of


class UnexplainedRevision(ValueError):
    """A definition changed and the registry does not say why."""


def _metrics() -> dict:
    return (yaml.safe_load(REGISTRY.read_text()) or {}).get("metrics") or {}


def version_of(metric: str) -> int:
    """The definition the registry currently pins for this metric."""
    grade_of(metric)                       # unregistered metrics cannot be read at all
    return int(_metrics()[metric].get("definition_version", 1))


def reason_for(metric: str, version: int) -> str:
    """Why this version exists. Version 1 needs no defence; later ones do."""
    if version <= 1:
        return "the original definition"
    for entry in _metrics()[metric].get("definition_history") or []:
        if int(entry.get("version", 0)) == version:
            return (entry.get("why") or "").strip()
    return ""


def recorded_version(conn: sqlite3.Connection, metric: str) -> int | None:
    row = conn.execute(
        "SELECT to_version FROM metric_definition_changes WHERE metric=?"
        " ORDER BY ts DESC LIMIT 1", (metric,)).fetchone()
    if row:
        return int(row[0])
    row = conn.execute(
        "SELECT definition_version FROM metric_readings WHERE metric=?"
        " ORDER BY ts DESC LIMIT 1", (metric,)).fetchone()
    return int(row[0]) if row else None


def sync(conn: sqlite3.Connection, metric: str, *, now: float | None = None) -> bool:
    """Record a definition change if the registry has moved. True if it had.

    Refuses a bump with no stated reason: resetting a baseline without saying
    why the old one stopped meaning anything is the silent breakage this epic
    is named for.
    """
    current = version_of(metric)
    seen = recorded_version(conn, metric)
    if seen is None or seen == current:
        return False
    if current < seen:
        raise UnexplainedRevision(
            f"{metric}: registry pins definition {current}, store has already "
            f"recorded {seen}. A definition does not go backwards.")
    why = reason_for(metric, current)
    if not why:
        raise UnexplainedRevision(
            f"{metric}: definition moved {seen} -> {current} and the registry "
            "gives no reason. Add a definition_history entry saying what "
            "changed and why the old series stopped meaning anything.")
    conn.execute(
        "INSERT INTO metric_definition_changes (ts, metric, from_version,"
        " to_version, reason) VALUES (?,?,?,?,?)",
        (now or time.time(), metric, seen, current, why))
    conn.commit()
    return True


def changes(conn: sqlite3.Connection, metric: str | None = None) -> list[sqlite3.Row]:
    """Every seam in every series — why a delta stops at a particular date."""
    if metric:
        return conn.execute(
            "SELECT * FROM metric_definition_changes WHERE metric=? ORDER BY ts",
            (metric,)).fetchall()
    return conn.execute(
        "SELECT * FROM metric_definition_changes ORDER BY ts").fetchall()
