"""The hard core is enumerated, and the enumeration lost nothing (SEL §5).

Three failures this catches:

  - a path is named in the core and does not exist. A boundary that resolves to
    nothing refuses nothing, and it reads as protection until the day it is
    tested.

  - the frozen instrument set drifts back to §5.2's hand list. §5.2 names ten
    instruments; the canonical tools import nine `newz/evidence` modules and it
    names two of them. Freezing `tools/evidence.py` while
    `newz/evidence/pursuit.py` stays writable freezes a filename and not a
    measurement.

  - the registry stops saying it is unenforced while it still is. E8.0 is the
    gate. Until E8.0 is built, a registry that looks enforced and is not is
    worse than no registry (INV-044).
"""

from pathlib import Path

import yaml

from newz.evidence import epics, hard_core

REPO = Path(__file__).resolve().parent.parent

# §5.2 of proposals/2026-08-19-the-self-evolving-loop.md, verbatim. Eight tools
# and two newz/evidence modules — the list this registry was transcribed from.
SECTION_5_2 = (
    "evidence.py", "what_shaped.py", "gate_report.py", "claims.py", "budget.py",
    "health.py", "check_invariants.py", "source_review.py",
    "perspective_window.py", "pursuit.py",
)


def test_the_registry_is_structurally_clean():
    assert hard_core.validate() == []


def test_every_protected_path_exists():
    for path in hard_core.protected_paths():
        assert (REPO / path).exists(), f"{path} is in the hard core and is not in the tree"


def test_the_derivation_covers_every_instrument_section_5_2_named():
    """The transcription is a superset of the prose it came from."""
    derived = {Path(p).name for p in hard_core.canonical_paths()}
    missing = [n for n in SECTION_5_2 if n not in derived]
    assert not missing, f"§5.2 named these and the derived set does not freeze them: {missing}"


def test_the_two_module_instruments_resolve_as_modules_not_tools():
    """§5.2 lists perspective_window and pursuit among instruments; they are
    newz/evidence modules, and the registry resolves them there rather than
    looking for tools that do not exist."""
    derived = hard_core.canonical_paths()
    assert "newz/evidence/perspective_window.py" in derived
    assert "newz/evidence/pursuit.py" in derived
    assert not (REPO / "tools/perspective_window.py").exists()
    assert not (REPO / "tools/pursuit.py").exists()


def test_a_canonical_tools_measurement_code_is_frozen_with_it():
    """The point of deriving rather than copying: tools/evidence.py is frozen
    and so is the module that computes its numbers."""
    assert "tools/evidence.py" in hard_core.canonical_paths()
    assert "newz/evidence/pursuit.py" in hard_core.canonical_paths()


def test_the_registry_protects_itself():
    """A boundary the constrained party can widen is not a boundary."""
    assert hard_core.contains("evolution/hard_core.yaml")
    assert hard_core.contains("evolution/instruments.yaml")


def test_ordinary_build_surface_is_outside_the_core():
    assert not hard_core.contains("newz/works/compose.py")
    assert not hard_core.contains("tests/test_hard_core.py")


def test_directories_match_by_prefix():
    assert hard_core.contains("constitution/v6.yaml")
    assert hard_core.contains("constitution/")


def test_plan_is_section_protected_and_says_nothing_checks_it():
    """PLAN.md cannot be a protected path — the loop is expected to append to
    it — so its protection is by section, and no check reads sections."""
    files = [s.get("file") for s in hard_core.sections()]
    assert "PLAN.md" in files
    assert not hard_core.contains("PLAN.md")
    assert any("section" in g["what"] or "section" in g["detail"]
               for g in hard_core.open_gaps())


def test_the_registry_admits_it_is_unenforced_while_e8_0_is_open():
    """The honesty clause, tied to the plan rather than to a comment: while the
    gate is unbuilt, the registry must still say nothing enforces it."""
    if epics.epics()["E8.0"]["status"] != "built":
        assert any("enforc" in g["what"] or "enforc" in g["detail"]
                   for g in hard_core.open_gaps()), \
            "E8.0 is not built and the registry no longer records that nothing enforces it"


def test_the_registry_is_valid_yaml_with_reasons_on_every_path():
    reg = yaml.safe_load((REPO / "evolution" / "hard_core.yaml").read_text())
    assert reg["version"] == 1
    for row in reg["paths"]:
        assert row["why"].strip(), f"{row['path']} is in the core with no reason given"
