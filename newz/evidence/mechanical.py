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


def self_grounding_share(conn: sqlite3.Connection) -> Value:
    """The share of all supporting episodes whose provenance is the being itself.

    Exactly what PLAN §1 states — "50% self, 33% operator, at most 17% the
    world, across 119 refs" — and deliberately NOT single_source_positions,
    which counts positions with a dominant source and is a different quantity.
    Pointing a premise at a near-neighbour metric is the "novelty" mistake
    (E2.8) in a new place, and it was made and caught here on 2026-08-20.
    """
    from newz.memory.provenance import corpus_concentration

    try:
        counts = corpus_concentration(conn)
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")
    total = sum(counts.values())
    if not total:
        return Value(unreadable="no held position carries resolvable evidence")
    return Value(round(counts.get("self", 0) / total, 4))


def episodes_recorded(conn: sqlite3.Connection, *, since: float) -> Value:
    """Episodes written in the window. Nothing judges what becomes one.

    It lived inline in `record_all` while the registry named `derived.py` as its
    emitter — a small instance of the fault E3.7's whole layer had (R-37c): a
    declaration that nobody could be wrong about loudly.
    """
    return _scalar(conn, "SELECT COUNT(*) FROM episodes WHERE ts >= ?", (since,))


def claims_settled(conn: sqlite3.Connection, *, since: float) -> Value:
    """FORECASTS the resolver settled in the window.

    `consequence_rate`'s numerator, which had no registered metric behind it
    until 2026-08-20 — the derivation queried `resolutions` directly while
    declaring it derived from `claims_opened`, which is a different quantity
    entirely.

    **Scoped to forecasts, and the series is unbroken by that (E1.10).** Every
    claim written before migration 0045 was a forecast in fact, because
    `MIN_HORIZON_DAYS = 2` forbade anything settleable now — so restricting the
    count to `kind='forecast'` returns exactly what it always returned for
    every reading already taken, and no version bump is owed. What would have
    broken the series is leaving it unscoped: from 2026-08-28 it would silently
    have begun counting two quantities that test different things.
    """
    return _scalar(conn, "SELECT COUNT(*) FROM resolutions"
                         " WHERE kind='forecast' AND settled_at IS NOT NULL"
                         " AND settled_at >= ?", (since,))


def retrodictions_settled(conn: sqlite3.Connection, *, since: float) -> Value:
    """Retrodictions the resolver settled in the window (E1.9, E1.10).

    A separate series because it is a separate quantity. A forecast tests the
    being's model of where things are going; a retrodiction tests whether its
    assertions about the world are true. Averaging them would read a change of
    mechanism as a change in the being, which is E2.8's "novelty" mistake, and
    the whole reason `resolutions.kind` exists.

    It starts at zero on 2026-08-28 with no history behind it, and that is
    honest rather than a gap: nothing before that date could have been one.
    """
    return _scalar(conn, "SELECT COUNT(*) FROM resolutions"
                         " WHERE kind='retrodiction' AND settled_at IS NOT NULL"
                         " AND settled_at >= ?", (since,))


def perspective_items_developed(conn: sqlite3.Connection, *, since: float) -> Value:
    """Items added or revised across the window's nights.

    `volume_against_development`'s denominator. The derivation declared
    `perspective_novelty` — a *share* — and divided by this, a *count*.
    """
    from newz.evidence.perspective_window import read_window

    try:
        w = read_window(conn, since=since)
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")
    return Value(float(sum(n.developed for n in w.nights)))


def perspective_novelty(conn: sqlite3.Connection, *, since: float) -> Value:
    """Pooled development share across the window's nights: developed / held.

    The quantity `tools/evidence.py` prints per era; here it is windowed and
    filed nightly, which is what gives it a series. Pooled rather than averaged
    for the reason `perspective_window` states — a night carrying twelve
    positions does not deserve the same vote as one carrying two hundred.
    """
    from newz.evidence.perspective_window import read_window

    try:
        w = read_window(conn, since=since)
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")
    weighed = sum(n.weighed for n in w.nights)
    if not weighed:
        return Value(unreadable=(
            "no night in the window held anything — the share has no "
            "denominator, and 0.0 would read as 'restated everything'"))
    return Value(round(w.novelty, 4))


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
        "self_grounding_share": self_grounding_share(conn),
        "feeds_contributing_a_read": feeds_contributing_a_read(
            conn, repo_root / "data" / "feeds.yaml"),
        # The four E3.7 derives from. They are primitives rather than inline
        # queries inside the derivations so that a declared input is a real
        # metric with a grade, a series and a definition version (R-37c).
        "episodes_recorded": episodes_recorded(conn, since=since),
        "claims_settled": claims_settled(conn, since=since),
        "retrodictions_settled": retrodictions_settled(conn, since=since),
        "perspective_items_developed": perspective_items_developed(conn, since=since),
        "perspective_novelty": perspective_novelty(conn, since=since),
    }
    out.update(compute_split(repo_root, hours=hours))
    return out
