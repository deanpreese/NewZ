"""Rule 7's mechanism: every measurement carries its grade (P4 epic E2.5).

Rule 7 was earned rather than invented. The 2026-08-19 instrumentation audit
found P3's own premise list mixing mechanical numbers with model-graded ones and
nothing distinguishing them — two pages after Rule 4 says a model judge produces
operation and never evidence. Advance acceptance, closure counts, the gate's
hold rate and what was read at all are all model-judged, and P3 cited advance
acceptance as part of the evidence that produced it.

**A grade belongs to a metric, not to a tool.** `evidence.py` emits a mechanical
coverage figure and a mixed novelty figure in the same report.

**Ungraded means uncitable, and that is the whole point.** A convention that
says "please state the grade" is a convention; a function that refuses to render
a number whose provenance nobody recorded is a mechanism. Adding a metric to a
read therefore forces adding it to `evolution/instruments.yaml` first — which is
Rule 2's writer-and-reader discipline pointed at measurements.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

REGISTRY = Path(__file__).resolve().parent.parent.parent / "evolution" / "instruments.yaml"

GRADES = ("mechanical", "model-graded", "mixed", "known-biased")

# Rendered beside a figure. Deliberately not a score and deliberately not
# ranked: a model-graded number is not a worse number, it is a different kind
# of number, and one that may not carry a decision on its own.
LABEL = {
    "mechanical": "mechanical",
    "model-graded": "model-graded",
    "mixed": "mixed",
    "known-biased": "known-biased",
}


class UngradedMetric(KeyError):
    """Raised when something tries to cite a number nobody graded."""


@functools.lru_cache(maxsize=1)
def _registry() -> dict:
    data = yaml.safe_load(REGISTRY.read_text()) or {}
    metrics = data.get("metrics") or {}
    for name, row in metrics.items():
        grade = (row or {}).get("grade")
        if grade not in GRADES:
            raise ValueError(
                f"metric {name!r} has grade {grade!r}; expected one of {GRADES}")
        if not (row or {}).get("reason"):
            raise ValueError(f"metric {name!r} has a grade and no reason for it")
    return metrics


def known() -> set[str]:
    return set(_registry())


def grade_of(metric: str) -> str:
    """The metric's grade, or a refusal to let it be cited at all."""
    row = _registry().get(metric)
    if row is None:
        raise UngradedMetric(
            f"{metric!r} is not in evolution/instruments.yaml — Rule 7: a "
            "measurement with no recorded grade cannot be cited. Add it, with "
            "the reason and where any model judgment sits, then read it.")
    return row["grade"]


def reason_of(metric: str) -> str:
    grade_of(metric)
    return (_registry()[metric].get("reason") or "").strip()


def unreadable_when(metric: str) -> str:
    grade_of(metric)
    return (_registry()[metric].get("unreadable_when") or "").strip()


def tag(metric: str, *, note: str = "") -> str:
    """`[mechanical]`, or `[mixed — dominant provenance]`. For printing beside a figure."""
    label = LABEL[grade_of(metric)]
    return f"[{label}{' — ' + note if note else ''}]"
