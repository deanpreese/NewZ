"""The canonical freeze (P4 epic E3.9).

Done-when: a diff touching a canonical instrument is refused, and a test
asserts the refusal.

**Why freeze at all.** The loop steers by evidence the being produces while
changing the being. At n=1 with no held-out baseline it cannot separate
improving the being from improving the instrument's view of the being, and it
has a gradient toward the second because that is cheaper and always works.

**It constrains the loop, not the operator** — a boundary the constrained party
can widen is not a boundary, and the constrained party is the loop.
"""

from __future__ import annotations

import pytest

from newz.evidence import hard_core
from newz.evidence.freeze import (
    FrozenTouched,
    Refusal,
    enforce,
    metrics_affected,
    refusals,
)


def test_a_diff_touching_a_canonical_instrument_is_refused():
    """E3.9's Done-when."""
    with pytest.raises(FrozenTouched, match="canonical instrument"):
        enforce(["newz/evidence/mechanical.py"], actor="loop")

    with pytest.raises(FrozenTouched):
        enforce(["tools/claims.py", "README.md"], actor="loop")


def test_an_ordinary_change_is_not_refused():
    """Behavior: the freeze is narrow. Most of the codebase is the loop's to
    change — that is the point of naming a small set rather than a large one."""
    assert refusals(["newz/works/compose.py", "tools/write_piece.py"]) == []
    assert enforce(["newz/surface/generate.py"], actor="loop") == []


def test_the_operator_is_recorded_and_not_blocked():
    """E3.9's own words: "changing any canonical instrument becomes an operator
    act". The operator changing one is not a breach — it is the act the freeze
    exists to require."""
    found = enforce(["newz/evidence/mechanical.py"], actor="operator")

    assert [f.path for f in found] == ["newz/evidence/mechanical.py"]
    assert isinstance(found[0], Refusal)


def test_the_operators_path_carries_e28s_obligation():
    """The reason the operator path returns a list rather than nothing.

    Changing a canonical instrument is precisely when a metric's meaning moves.
    A freeze that only said "no" to the loop would leave the operator free to
    change a measurement while its series quietly continued across the change —
    the exact silent breakage E2.8 exists to prevent, arriving through the one
    door the freeze leaves open."""
    affected = metrics_affected(["newz/evidence/mechanical.py"])

    assert "newz/evidence/mechanical.py" in affected
    assert "nights_slept" in affected["newz/evidence/mechanical.py"]

    with pytest.raises(FrozenTouched, match="definition_version"):
        enforce(["newz/evidence/mechanical.py"], actor="loop")


def test_measurement_code_is_frozen_however_far_from_a_tool_it_sits():
    """The gap E3.9 found in its own boundary. Behavior: the closure is
    transitive.

    One level from the canonical tools left derived.py, agreement.py,
    authority.py and definitions.py writable — all measurement code, reached
    through baseline.py and premises.py rather than directly. A frozen tool
    whose measurement code is writable is not frozen, and that is as true two
    hops out as one."""
    canonical = set(hard_core.canonical_paths())

    for two_hops in ("newz/evidence/derived.py", "newz/evidence/agreement.py",
                     "newz/evidence/definitions.py"):
        assert two_hops in canonical, two_hops


def test_the_freeze_covers_every_module_that_emits_a_registered_metric():
    """The property that matters, stated independently of how it is derived:
    if a file emits a metric, changing it changes a number the loop steers by."""
    import yaml
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    rows = yaml.safe_load((repo / "evolution" / "instruments.yaml").read_text())["metrics"]
    emitters = {r["emitted_by"] for r in rows.values() if r.get("emitted_by")}
    canonical = set(hard_core.canonical_paths())

    assert emitters <= canonical, f"emits a metric and is not frozen: {sorted(emitters - canonical)}"


def test_nothing_enforces_this_automatically_and_that_is_stated():
    """INV-044's discipline applied to a guard, after Phase 8 was struck.

    A guard that looks enforced and is not is worse than no guard, so the
    module says which it is — and what it says changed on 2026-08-21. It used
    to name a gate and a builder as consumers that did not exist yet;
    they will not exist at all, and `tools/gate.py` runs `freeze_check
    --operator`, which lists and does not refuse. Behavior: the module states
    the standing fact and names the party it constrains."""
    from newz.evidence import freeze

    doc = freeze.__doc__ or ""
    assert "Nothing calls this automatically" in doc
    assert "operator's agents" in doc
    assert "E8." not in doc
