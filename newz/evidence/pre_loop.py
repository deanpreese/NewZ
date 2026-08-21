"""What the being was like before the loop, and whether it still is (P4 W10).

**"The pre-loop baseline" had no definition.** PLAN uses the phrase three times
— the condition for holding stage 2, S8-E's read, and *nights slept falling
below the pre-loop baseline*, which Phase 8 calls the kill condition that
matters most — and nothing said what it was, over what window, or who took it.
A halt whose threshold is a phrase fires when somebody decides it should.

**Measured, never imputed.** The values come from the being's own nightly
series in `metric_readings`, over a stated window, with the reading ids that
produced them. That is the difference between this and the spend condition the
operator kept unbased on 2026-08-20: inventing a denominator so a kill
condition can fire is the failure §10 names, and reading one off a series the
being wrote is not inventing it.

**The loop may read this and may never write it.** `evolution/pre_loop_baseline.yaml`
is inside the hard core. A loop that takes its own baseline is not being judged
by one.

**Absent is UNREADABLE, not fine.** Before the baseline is taken there is
nothing to fall below, and `compare` says so rather than returning "nothing has
fallen". `may_widen` is the same discipline pointed at autonomy: the loop may
not leave stage 0 while the thing that would catch it costing the being sleep
does not exist.
"""

from __future__ import annotations

import functools
import sqlite3
import statistics
from pathlib import Path

import yaml

REGISTRY = (Path(__file__).resolve().parent.parent.parent / "evolution"
            / "pre_loop_baseline.yaml")

# Below this the "baseline" is one week seen once: the metrics are themselves
# 168-hour windows, so consecutive nightly readings overlap almost entirely and
# a handful of them describe a few days rather than a month.
MIN_READINGS = 7


@functools.lru_cache(maxsize=1)
def registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text()) or {}


def taken() -> bool:
    """Has the operator taken it? Everything else follows from this."""
    return bool(registry().get("taken_at"))


def baseline(metric: str) -> float | None:
    """The pre-loop median for one metric, or None if it was never taken."""
    row = (registry().get("metrics") or {}).get(metric)
    return None if row is None else float(row["median"])


def propose(conn: sqlite3.Connection, metrics: list[str], *, now: float,
            window_days: int | None = None) -> dict:
    """What the file should say, computed from the series. Writes nothing.

    The median rather than the mean: one night the being did not sleep because
    the operator was restarting it should not lower the bar the loop is later
    held to, and one unusually productive week should not raise it.
    """
    window_days = window_days or int(registry().get("window_days") or 28)
    since = now - window_days * 86400.0
    out: dict[str, dict] = {}
    for metric in metrics:
        rows = conn.execute(
            "SELECT id, ts, value FROM metric_readings WHERE metric=?"
            " AND status='ok' AND ts >= ? ORDER BY ts", (metric, since)).fetchall()
        if len(rows) < MIN_READINGS:
            out[metric] = {"unreadable": (
                f"{len(rows)} reading(s) in {window_days} days, and a baseline "
                f"needs {MIN_READINGS} — below that it is one week seen once, "
                "since the metric is itself a 168-hour window")}
            continue
        out[metric] = {
            "median": round(statistics.median(r["value"] for r in rows), 4),
            "readings": len(rows),
            "from": round(rows[0]["ts"], 3),
            "to": round(rows[-1]["ts"], 3),
            "reading_ids": [int(r["id"]) for r in rows],
        }
    return out


def compare(conn: sqlite3.Connection, metric: str, *, now: float,
            window_hours: float = 168.0) -> dict:
    """Where the metric stands against its pre-loop median.

    Returns `{"unreadable": why}` when the baseline was never taken or the
    metric has no current reading. Falling below is not computed as False when
    there is nothing to fall below.
    """
    if not taken():
        return {"unreadable": (
            "the pre-loop baseline has not been taken — there is nothing to "
            "fall below, and reporting that nothing has fallen would be a pass "
            "the measurement never made")}
    base = baseline(metric)
    if base is None:
        return {"unreadable": f"{metric} is not in the pre-loop baseline"}
    row = conn.execute(
        "SELECT value FROM metric_readings WHERE metric=? AND status='ok'"
        " ORDER BY ts DESC, id DESC LIMIT 1", (metric,)).fetchone()
    if row is None:
        return {"unreadable": f"{metric} has no measured reading to compare"}
    current = float(row["value"])
    return {"metric": metric, "current": current, "baseline": base,
            "below": current < base, "delta": round(current - base, 4)}


def may_widen() -> str | None:
    """Why the loop may not leave stage 0, or None.

    Stage 0 is read-only and needs no baseline. Every stage above it is
    permitted on the promise that a cost to the being would be caught, and
    *nights slept below the pre-loop baseline* is how that promise is kept.
    Widening without it is widening on an unreadable condition.
    """
    if not taken():
        return ("the pre-loop baseline has not been taken "
                f"({REGISTRY.name}: taken_at is null), so the kill condition "
                "that matters most cannot be read. Stage 0 needs no baseline; "
                "nothing above it may be entered without one")
    return None


def validate() -> list[str]:
    """Structural errors in the file. Empty is clean, taken or not."""
    errors: list[str] = []
    reg = registry()
    for key in ("version", "taken_at", "taken_by", "window_days", "metrics"):
        if key not in reg:
            errors.append(f"pre_loop_baseline is missing {key!r}")
    if not isinstance(reg.get("metrics") or {}, dict):
        errors.append("metrics must be a mapping of metric -> values")
        return errors
    if reg.get("taken_at") and not reg.get("taken_by"):
        errors.append("a baseline was taken and does not say who took it")
    if reg.get("taken_at") and not (reg.get("metrics") or {}):
        errors.append("a baseline was taken and holds no metric")
    for metric, row in (reg.get("metrics") or {}).items():
        from newz.evidence.grades import grade_of

        try:
            grade_of(metric)
        except Exception:                              # noqa: BLE001
            errors.append(f"{metric} is in the baseline and is not a registered metric")
        if "unreadable" in row:
            continue
        missing = [k for k in ("median", "readings", "from", "to", "reading_ids")
                   if k not in row]
        if missing:
            errors.append(f"{metric}: baseline row is missing {missing}")
        elif row["readings"] < MIN_READINGS:
            errors.append(
                f"{metric}: {row['readings']} readings is below the {MIN_READINGS} "
                "a baseline needs")
        elif len(row["reading_ids"]) != row["readings"]:
            errors.append(
                f"{metric}: says {row['readings']} readings and names "
                f"{len(row['reading_ids'])} ids — the ids are what make it "
                "checkable rather than asserted")
    return errors
