"""The plan's own staleness instrument (P4 epic E2.10).

**The failure this exists for has already happened.** PLAN §1 records *"0
outcomes the being did not grade itself"* as measured state, and Phase 1 exists
to change it. E1.4 shipped on 2026-08-19 at 06:47 and began changing it —
and nothing in this system remarked on that, because a plan's premises lived in
prose and prose does not notice when it stops being true.

**Drift is reported whether or not anything is proposed.** A premise that moves
is news on its own; waiting for someone to be drafting a change before checking
is how a plan goes stale between drafts.

**What a premise carries is part of the record.** A figure moving is a
measurement; the argument that rested on it needing re-reading is the finding.
So each premise names what depends on it, and a moved premise reports that
sentence rather than a number.

**Unmeasurable premises are recorded, not dropped.** `metric: null` says the
project is holding that one on faith, which is worth knowing and is better than
inventing an instrument to cover it.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml

REGISTRY = Path(__file__).resolve().parent.parent.parent / "evolution" / "premises.yaml"


@dataclass(frozen=True)
class Drift:
    premise: str
    states: str
    stated_value: float | None
    now: float | None
    metric: str | None
    carries: str
    unreadable: str = ""
    material_change: float = 0.0

    @property
    def measurable(self) -> bool:
        return self.metric is not None

    @property
    def moved(self) -> bool:
        if not self.measurable or self.now is None or self.stated_value is None:
            return False
        return abs(self.now - self.stated_value) >= self.material_change

    def render(self) -> str:
        if not self.measurable:
            return (f"  · {self.premise}\n"
                    f"      {self.states}\n"
                    f"      HELD ON FAITH — {self.unreadable}")
        if self.now is None:
            return (f"  · {self.premise}\n"
                    f"      {self.states}\n"
                    f"      UNREADABLE — {self.unreadable}")
        mark = "MOVED" if self.moved else "holds"
        line = (f"  {'!' if self.moved else ' '} {self.premise}\n"
                f"      {self.states}\n"
                f"      {mark}: was {self.stated_value:g}, now {self.now:g}"
                f"  [{self.metric}]")
        if self.moved:
            line += f"\n      what rested on it: {' '.join(self.carries.split())}"
        return line


def _registry() -> dict:
    return (yaml.safe_load(REGISTRY.read_text()) or {}).get("premises") or {}


def check(conn: sqlite3.Connection, repo_root: Path, *, now: float,
          hours: float = 168.0) -> list[Drift]:
    """Re-measure every premise. Reports holds, moves and holes alike."""
    from newz.evidence.consequence import read as read_consequence
    from newz.evidence.mechanical import all_values

    values = {n: v for n, v in
              all_values(conn, repo_root, now=now, hours=hours).items()}
    c = read_consequence(conn, repo_root, now=now, hours=hours)
    from newz.evidence.mechanical import Value

    values["claims_opened"] = Value(float(c.door.opened))
    values["positions_changed_by_world"] = Value(float(c.positions.by_world))

    out: list[Drift] = []
    for name, row in sorted(_registry().items()):
        metric = row.get("metric")
        carries = (row.get("carries") or "").strip()
        if metric is None:
            out.append(Drift(name, row["states"], row.get("stated_value"), None,
                             None, carries,
                             unreadable=" ".join((row.get("why_unmeasured") or "").split())))
            continue
        v = values.get(metric)
        if v is None:
            out.append(Drift(name, row["states"], row.get("stated_value"), None,
                             metric, carries,
                             unreadable=f"{metric} is not produced by any writer"))
            continue
        out.append(Drift(name, row["states"], row.get("stated_value"), v.value,
                         metric, carries,
                         unreadable=v.unreadable or "",
                         material_change=float(row.get("material_change", 0))))
    return out


def moved(conn: sqlite3.Connection, repo_root: Path, *, now: float,
          hours: float = 168.0) -> list[Drift]:
    """Only the premises that have shifted materially.

    §12.6's rule reads this: a plan-change proposal must name a moved
    **mechanical** premise, and may not be justified by preference or elegance.
    """
    from newz.evidence.grades import grade_of

    return [d for d in check(conn, repo_root, now=now, hours=hours)
            if d.moved and grade_of(d.metric) == "mechanical"]


def validate() -> list[str]:
    """Every way the premise registry can be wrong."""
    from newz.evidence.grades import UngradedMetric, grade_of

    errors: list[str] = []
    for name, row in _registry().items():
        if not (row.get("states") or "").strip():
            errors.append(f"{name}: says nothing about what it asserts")
        if not (row.get("carries") or "").strip():
            errors.append(f"{name}: names nothing that rests on it")
        if not (row.get("source") or "").strip():
            errors.append(f"{name}: does not say where the plan states it")
        metric = row.get("metric")
        if metric is None:
            if not (row.get("why_unmeasured") or "").strip():
                errors.append(f"{name}: unmeasured and does not say why")
            continue
        try:
            grade_of(metric)
        except UngradedMetric:
            errors.append(f"{name}: measured by {metric!r}, which is not a registered metric")
        if row.get("stated_value") is None:
            errors.append(f"{name}: measurable and states no value to move from")
    return errors
