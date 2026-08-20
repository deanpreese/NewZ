"""The metrics the loop may steer by — all mechanical (P4 epic E2.9).

**Mechanical means no model judgment anywhere between the world and the
number** (Rule 7). Every figure here is a count or a ratio of counts over rows
the being wrote as it lived, and none of them asks a model anything. That is the
whole qualification: P4's Phase 8 gate is tests, invariants, migrations and
*measured mechanical deltas*, and a figure a model judged cannot carry a
decision on its own.

**Phase 2's own numbers are here for the first time.** Pieces, revisions and
retractions per window with their causes — so S2-E is read off instruments
rather than assembled by hand, which is what E2.9 asks for.

**And `nights_slept` closes a gap the purpose map found.** P4's Phase 8 names it
the kill condition that matters most — *development is measured in nights, not
commits, and a loop that costs sleep is subtracting* — and until this module it
had nothing measuring it.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

DAY = 86400.0


def _scalar(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> "Value":
    """A count, or the honest reason there isn't one.

    A table that does not exist yet is a store that has not taken the
    migration — which is unmeasured, not zero. INV-044's rule reaches further
    than anyone expects: an instrument that answers 0 on a store mid-upgrade
    has reported a fact it never read.
    """
    try:
        return Value(float(conn.execute(sql, args).fetchone()[0]))
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")


@dataclass(frozen=True)
class Value:
    """A number, or the honest reason there isn't one (INV-044)."""
    value: float | None = None
    unreadable: str | None = None
    covers_from: float | None = None


def nights_slept(conn: sqlite3.Connection, *, since: float) -> Value:
    """Perspective versions written in the window. The being's own clock."""
    v = _scalar(conn, "SELECT COUNT(*) FROM perspective WHERE ts >= ?", (since,))
    if v.unreadable:
        return v
    first = conn.execute("SELECT MIN(ts) FROM perspective").fetchone()[0]
    return Value(v.value, covers_from=first)


def hours_since_last_sleep(conn: sqlite3.Connection, *, now: float) -> Value:
    """How long since the last consolidation. Rises when sleep stops happening."""
    last = conn.execute("SELECT MAX(ts) FROM perspective").fetchone()[0]
    if last is None:
        return Value(unreadable="no Perspective has ever been written")
    return Value(round((now - last) / 3600.0, 2))


def pieces_written(conn: sqlite3.Connection, *, since: float) -> Value:
    return _scalar(conn, "SELECT COUNT(*) FROM works WHERE ts >= ?", (since,))


def works_revised(conn: sqlite3.Connection, *, since: float) -> Value:
    return _scalar(conn, "SELECT COUNT(*) FROM work_revisions WHERE kind='revised' AND ts >= ?", (since,))


def works_retracted(conn: sqlite3.Connection, *, since: float) -> Value:
    return _scalar(conn, "SELECT COUNT(*) FROM work_revisions WHERE kind='retracted' AND ts >= ?", (since,))


def revision_causes(conn: sqlite3.Connection, *, since: float) -> list[tuple[str, str]]:
    """S2-E asks for revisions and retractions **with their causes**, and a
    cause is the being's own reason at the time — read, never re-derived."""
    try:
        return [(r["kind"], r["reason"]) for r in conn.execute(
            "SELECT kind, reason FROM work_revisions WHERE ts >= ? ORDER BY ts",
            (since,))]
    except sqlite3.OperationalError:
        return []


def source_gaps_open(conn: sqlite3.Connection) -> Value:
    """Questions no readable source answered. §Going public's trip-wire."""
    return _scalar(conn, "SELECT COUNT(*) FROM source_gaps")


def feeds_contributing_a_read(conn: sqlite3.Connection, feeds_path: Path) -> Value:
    """Outlets that have ever yielded a read, against the outlets configured.

    E1.0's own measure: 27 of 61 feeds had been polled continuously and read
    zero times, which is what the epic existed to change.
    """
    if not feeds_path.exists():
        return Value(unreadable=f"no feed list at {feeds_path}")
    import yaml

    data = yaml.safe_load(feeds_path.read_text()) or {}
    configured = sum(len(v or []) for k, v in data.items() if isinstance(v, list))
    if not configured:
        return Value(unreadable=f"{feeds_path} lists no feeds")
    got = _scalar(conn, "SELECT COUNT(DISTINCT outlet) FROM ingest_log"
                        " WHERE claims_kept > 0")
    if got.unreadable:
        return got
    return Value(round(got.value / configured, 4))


def single_source_positions(conn: sqlite3.Connection) -> Value:
    """Held positions where one provenance supplies more than half the evidence.

    INV-033's own flag. It fires on `self` today, which is the finding that
    produced the whole participation design.
    """
    from newz.memory.provenance import what_shaped_version

    latest = conn.execute("SELECT MAX(version) FROM perspective").fetchone()[0]
    if latest is None:
        return Value(unreadable="no Perspective has ever been written")
    influences = what_shaped_version(conn, latest)
    if not influences:
        return Value(unreadable="the current Perspective holds no items with evidence")
    grounded = [i for i in influences if i.total]
    if not grounded:
        return Value(unreadable="no held position carries resolvable evidence")
    flagged = sum(1 for i in grounded
                  if (i.concentration or ("", 0.0))[1] > 0.5)
    return Value(round(flagged / len(grounded), 4))


def compute_split(repo_root: Path, *, hours: float) -> dict[str, Value]:
    """Token share by function — the compute the being spent on what."""
    from newz.telemetry import read_budget

    log = repo_root / "logs" / "llm_calls.jsonl"
    if not log.exists():
        why = (f"no call log at {log} — gitignored, and it does not travel with "
               "a clone (INV-044)")
        return {"deliberation_token_share": Value(unreadable=why)}
    r = read_budget(log, window_hours=hours)
    if not r.calls:
        return {"deliberation_token_share": Value(
            unreadable=f"no calls recorded in the last {hours:.0f}h")}
    tokens = r.by_function.get("deliberation", {}).get("tokens", 0)
    return {"deliberation_token_share": Value(round(tokens / r.tokens, 4))}


def all_values(conn: sqlite3.Connection, repo_root: Path, *, now: float,
               hours: float) -> dict[str, Value]:
    """Every mechanical metric, in one pass. The writer record_all consumes."""
    since = now - hours * 3600.0
    out = {
        "nights_slept": nights_slept(conn, since=since),
        "hours_since_last_sleep": hours_since_last_sleep(conn, now=now),
        "pieces_written": pieces_written(conn, since=since),
        "works_revised": works_revised(conn, since=since),
        "works_retracted": works_retracted(conn, since=since),
        "source_gaps_open": source_gaps_open(conn),
        "single_source_positions": single_source_positions(conn),
        "feeds_contributing_a_read": feeds_contributing_a_read(
            conn, repo_root / "data" / "feeds.yaml"),
    }
    out.update(compute_split(repo_root, hours=hours))
    return out
