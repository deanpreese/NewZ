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
fallen". `may_widen` was the same discipline pointed at autonomy, and it went with
the stages it refused (P4 E3A.4): Phase 8 is struck, there are no autonomy
stages, and a function whose only job was to gate one is a reader with nothing
to read (Rule 2). `compare` survives as the daily email's comparison line.
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
# 168-hour windows, so consecutive readings overlap almost entirely and a
# handful of them describe a few days rather than a month.
#
# **It counts DAYS, and it used to count readings** (P4 E3A.2). Under the
# nightly cadence the two were the same number and the comment above was true
# by accident. The monitor reads hourly, and seven readings became seven hours
# while the sentence explaining the threshold still said a week — a guard that
# keeps passing after its reason has stopped being true, which is INV-044's
# failure introduced by a cadence change rather than by an edit.
#
# The baseline therefore takes the LAST READING OF EACH DAY. That fixes the
# threshold and a second thing with it: `reading_ids` records every id the
# median was computed from, and over 28 days those went from 28 per metric to
# 672 — some 19,000 ids in a hand-readable file inside the hard core. The ids
# are not droppable (INV-087 calls them what separates this from an invented
# denominator), so the series stays hourly and the baseline is a daily thing.
MIN_DAYS = 7


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
        rows = _one_per_day(conn, metric, since)
        if len(rows) < MIN_DAYS:
            out[metric] = {"unreadable": (
                f"{len(rows)} day(s) of readings in {window_days} days, and a "
                f"baseline needs {MIN_DAYS} — below that it is one week seen "
                "once, since the metric is itself a 168-hour window")}
            continue
        out[metric] = {
            "median": round(statistics.median(r["value"] for r in rows), 4),
            "readings": len(rows),
            "from": round(rows[0]["ts"], 3),
            "to": round(rows[-1]["ts"], 3),
            "reading_ids": [int(r["id"]) for r in rows],
        }
    return out


def _one_per_day(conn: sqlite3.Connection, metric: str, since: float) -> list:
    """The last measured reading of each local day. The baseline's unit.

    Local rather than UTC because "a day" here means one of the being's days —
    the same day boundary sleep runs on and `nights_slept` counts.
    """
    return conn.execute(
        "SELECT id, ts, value FROM mon.metric_readings r WHERE metric=?"
        " AND status='ok' AND ts >= ?"
        " AND ts = (SELECT MAX(ts) FROM mon.metric_readings x"
        "           WHERE x.metric = r.metric AND x.status='ok'"
        "           AND date(x.ts, 'unixepoch', 'localtime')"
        "             = date(r.ts, 'unixepoch', 'localtime'))"
        " ORDER BY ts", (metric, since)).fetchall()


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
        "SELECT value FROM mon.metric_readings WHERE metric=? AND status='ok'"
        " ORDER BY ts DESC, id DESC LIMIT 1", (metric,)).fetchone()
    if row is None:
        return {"unreadable": f"{metric} has no measured reading to compare"}
    current = float(row["value"])
    return {"metric": metric, "current": current, "baseline": base,
            "below": current < base, "delta": round(current - base, 4)}


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
        elif row["readings"] < MIN_DAYS:
            errors.append(
                f"{metric}: {row['readings']} day(s) of readings is below the "
                f"{MIN_DAYS} a baseline needs")
        elif len(row["reading_ids"]) != row["readings"]:
            errors.append(
                f"{metric}: says {row['readings']} readings and names "
                f"{len(row['reading_ids'])} ids — the ids are what make it "
                "checkable rather than asserted")
    return errors
