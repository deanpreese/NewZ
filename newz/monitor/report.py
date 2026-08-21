"""The daily state, as text (P4 E3A.3).

**No sentence in here is authored.** Every line is a number, the method behind
it, or a heading — and a test asserts that. The SEL's §7 ordered the loop's
prose last and marked it unverified, because *"a weekly page of fluent reasoning
is the worst available drift detector"* (R-R1). There is no prose to order here,
which is the stronger form of the same answer.

Rules 0 and 7: every figure carries its method and its grade. A measurement that
could not be taken prints UNREADABLE with the reason, never a zero (INV-044).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

W = 34


def _h(title: str) -> list[str]:
    return ["", title, "-" * len(title)]


def _stamp(ts: float | None) -> str:
    return "never" if ts is None else time.strftime(
        "%Y-%m-%d %H:%M", time.localtime(ts))


def _liveness(conn, backups_dir: Path, now: float) -> list[str]:
    from newz.monitor.liveness import read

    return _h("THE BEING") + [f"  {s.line(now)}" for s in read(
        conn, backups_dir, now=now)]


def _cadence(mon: sqlite3.Connection, now: float) -> list[str]:
    out = _h("THE MONITOR")
    row = mon.execute(
        "SELECT MAX(ts) FROM monitor_log WHERE kind='reading' AND ok=1").fetchone()
    last = row[0] if row else None
    if last is None:
        out.append(f"  {'last reading':<{W}} never")
    else:
        out.append(f"  {'last reading':<{W}} {(now - last) / 3600.0:>6.1f}h ago"
                   f"   {_stamp(last)}")
    day = now - 86_400.0
    taken = mon.execute(
        "SELECT COUNT(*) FROM monitor_log WHERE kind='reading' AND ok=1"
        " AND ts >= ?", (day,)).fetchone()[0]
    out.append(f"  {'readings in the last 24h':<{W}} {taken:>6} of 24")
    failed = mon.execute(
        "SELECT ts, kind, note FROM monitor_log WHERE ok=0 AND ts >= ?"
        " ORDER BY ts", (day,)).fetchall()
    for f in failed:
        out.append(f"  FAILED  {_stamp(f['ts'])}  {f['kind']}  {f['note']}")
    if not failed:
        out.append(f"  {'failures in the last 24h':<{W}} {0:>6}")
    return out


def _metrics(conn: sqlite3.Connection, now: float) -> list[str]:
    from newz.evidence.baseline import baselined_metrics, peek
    from newz.evidence.grades import UngradedMetric, grade_of

    out = _h("THE INSTRUMENTS  (value / baseline / delta / grade, 168h window)")
    latest = conn.execute(
        "SELECT r.* FROM mon.metric_readings r JOIN (SELECT metric, MAX(ts) t"
        " FROM mon.metric_readings GROUP BY metric) x"
        " ON x.metric = r.metric AND x.t = r.ts ORDER BY r.metric").fetchall()
    if not latest:
        return out + ["  UNREADABLE — no readings recorded"]
    known = set(baselined_metrics())
    for r in latest:
        name = r["metric"]
        try:
            grade = grade_of(name)
        except UngradedMetric:
            # Rule 7: an ungraded measurement is not shown rather than shown
            # without its provenance.
            continue
        if r["status"] != "ok":
            out.append(f"  {name:<{W}} {r['status'].upper():>10}   {r['note']}")
            continue
        base = peek(conn, name, r["value"], window_hours=r["window_hours"],
                    now=r["ts"])
        out.append(f"  {name:<{W}} {r['value']:>10}   {base.note or 'no baseline yet'}"
                   f"   [{grade}]")
    missing = sorted(known - {r["metric"] for r in latest})
    for name in missing:
        out.append(f"  {name:<{W}} {'UNREADABLE':>10}   no reading in the series")
    return out


def _premises(conn: sqlite3.Connection, repo_root: Path, now: float) -> list[str]:
    from newz.evidence.premises import check

    out = _h("PREMISES  (E2.10 — what the plan asserts, re-measured)")
    for d in check(conn, repo_root, now=now):
        if d.unreadable:
            out.append(f"  {d.premise:<{W}} UNREADABLE   {d.unreadable}")
        elif d.moved:
            out.append(f"  {d.premise:<{W}} MOVED        stated {d.stated_value}"
                       f", now {d.now}  ({d.metric})")
        else:
            out.append(f"  {d.premise:<{W}} holds        stated {d.stated_value}"
                       f", now {d.now}")
    return out


def _plan(now: float) -> list[str]:
    from newz.evidence import epics

    out = _h("THE PLAN  (E2.11)")
    drift = epics.drift()
    out.append(f"  {'epic drift':<{W}} {len(drift):>6}")
    out += [f"    {e}" for e in drift]
    ready = epics.ready()
    out.append(f"  {'ready to build':<{W}} {len(ready):>6}   {', '.join(ready)}")
    return out


def _repo() -> list[str]:
    from newz.evidence import freeze, hard_core

    out = _h("THE REPO")
    try:
        changed = freeze.changed_paths()
        touched = freeze.refusals(changed)
        out.append(f"  {'uncommitted paths':<{W}} {len(changed):>6}")
        out.append(f"  {'frozen instruments touched':<{W}} {len(touched):>6}")
        out += [f"    {r}" for r in touched]
    except Exception as e:                       # not a git checkout, or no git
        out.append(f"  {'freeze':<{W}} UNREADABLE   {e}")
    out.append(f"  {'hard core paths':<{W}} {len(hard_core.protected_paths()):>6}")
    out.append(f"  {'canonical instruments':<{W}} "
               f"{len(hard_core.canonical_paths()):>6}")
    return out


def compose(conn: sqlite3.Connection, mon: sqlite3.Connection, repo_root: Path,
            backups_dir: Path, *, now: float | None = None) -> str:
    """The whole state, in one page of text. Calls no model."""
    now = now or time.time()
    lines = [f"NewZ — state at {_stamp(now)}",
             "=" * 46,
             "Every figure carries its method and its grade (Rules 0 and 7).",
             "A measurement that could not be taken says UNREADABLE, never 0."]
    lines += _liveness(conn, backups_dir, now)
    lines += _cadence(mon, now)
    lines += _metrics(conn, now)
    lines += _premises(conn, repo_root, now)
    lines += _plan(now)
    lines += _repo()
    lines += ["", f"-- tools/monitor.py, {_stamp(now)}"]
    return "\n".join(lines) + "\n"
