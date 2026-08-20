"""What each measurement is FOR (P4 epic E2.6).

Rule 2: no table or flag ships without a writer and a reader. E2.6 extends it to
measurements — **a metric nothing consumes is the same defect as a column
nothing reads**, and the invariant ledger has caught the second for months while
nothing caught the first.

Both directions hold, and they are not symmetrical:

- **No metric may exist without naming a purpose.** A number with no consumer is
  either dead weight or, worse, something that will find a use later without
  anyone deciding it should have one.
- **No purpose may name a metric that does not exist.** A read that depends on a
  figure nobody produces is a plan for a measurement, not a measurement.
- **A purpose with nothing serving it is NOT an error.** Six of TRUE_NORTH §10's
  ten items are not measurable — "a compelling demonstration", "fluent language",
  "evidence scores disconnected from sustained quality" — and manufacturing a
  proxy for them would be §10's own failure mode. Those are the gap list, and
  the gap list is the useful output: it says what the project is steering by
  faith rather than by instrument.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

REGISTRY = Path(__file__).resolve().parent.parent.parent / "evolution" / "instruments.yaml"


class UnknownPurpose(KeyError):
    """A metric claims to serve something the registry does not define."""


@functools.lru_cache(maxsize=1)
def _registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text()) or {}


def purposes() -> dict[str, dict]:
    return _registry().get("purposes") or {}


def metrics() -> dict[str, dict]:
    return _registry().get("metrics") or {}


def serves(metric: str) -> list[str]:
    row = metrics().get(metric)
    if row is None:
        raise KeyError(f"{metric!r} is not a registered metric")
    return list(row.get("serves") or [])


def served_by(purpose: str) -> list[str]:
    """Which metrics answer to this purpose. Empty is a real answer."""
    if purpose not in purposes():
        raise UnknownPurpose(f"{purpose!r} is not a registered purpose")
    return sorted(m for m, row in metrics().items()
                  if purpose in (row.get("serves") or []))


def unserved() -> list[str]:
    """Purposes nothing measures — what the project steers by faith."""
    claimed = {s for row in metrics().values() for s in (row.get("serves") or [])}
    return sorted(p for p in purposes() if p not in claimed)


def check() -> list[str]:
    """Every way the map can be wrong. Empty means both directions hold."""
    errors: list[str] = []
    known_purposes = set(purposes())
    for name, row in metrics().items():
        claims = row.get("serves") or []
        if not claims:
            errors.append(f"{name}: serves nothing — Rule 2, a metric needs a consumer")
        for pid in claims:
            if pid not in known_purposes:
                errors.append(f"{name}: serves {pid!r}, which is not a registered purpose")
    for pid, row in purposes().items():
        if not (row or {}).get("what", "").strip():
            errors.append(f"{pid}: has no description of what it is")
        for needed in (row or {}).get("needs") or []:
            if needed not in metrics():
                errors.append(f"{pid}: needs {needed!r}, which is not a registered metric")
    return errors
