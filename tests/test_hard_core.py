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


def test_the_registry_says_plainly_that_nothing_refuses_a_diff():
    """The honesty clause, after Phase 8 was struck (P4 E3A.4).

    It used to be tied to E8.0's status — *unenforced until the gate is built*.
    There is no gate coming: `tools/gate.py` runs `freeze_check --operator`,
    the non-refusing mode, so the refusing half has had no caller from the
    start. Behavior: the registry records that as a standing fact rather than
    as a pending epic, because a boundary that looks enforced and is not is
    worse than none (INV-044)."""
    assert "E8.0" not in epics.epics()
    gaps = hard_core.open_gaps()
    enforcement = [g for g in gaps
                   if "enforc" in g["what"] or "enforc" in g["detail"]]
    assert enforcement, "the registry no longer records that nothing refuses a diff"
    assert not any("E8." in g["detail"] for g in gaps), \
        "a gap still waits on an epic that was struck"


def test_the_registry_is_valid_yaml_with_reasons_on_every_path():
    reg = yaml.safe_load((REPO / "evolution" / "hard_core.yaml").read_text())
    assert reg["version"] == 1
    for row in reg["paths"]:
        assert row["why"].strip(), f"{row['path']} is in the core with no reason given"


def test_measurement_code_outside_newz_evidence_is_named_by_hand():
    """The derivation reaches `newz/evidence` and stops, which was too narrow
    the day it was written. `newz/telemetry.py` computes §9.1's ceilings for
    two canonical tools and `newz/memory/provenance.py` computes the grounding
    mix; neither is an evidence module, and either could be rewritten while
    every frozen file stayed byte-identical and every canonical number moved."""
    assert hard_core.contains("newz/telemetry.py")
    assert hard_core.contains("newz/memory/provenance.py")


def test_mechanisms_stay_outside_the_core():
    """The line is measurement in, mechanism out. `newz/world/diet.py` is
    imported by two canonical tools and is not frozen: it shapes what the being
    reads, and R-28 is the record of that cap being narrowed on evidence — work
    the freeze must not put out of reach. The store and config are
    infrastructure for the same reason."""
    assert not hard_core.contains("newz/world/diet.py")
    assert not hard_core.contains("newz/store/db.py")
    assert not hard_core.contains("newz/config.py")


# ── nothing enters the closure unclassified (P4 W8) ─────────────────────

def test_every_module_a_canonical_tool_reaches_is_classified():
    """W8. Behavior: `known_incomplete` says measurement code outside
    `newz/evidence` must be named by hand and **nothing detects a failure to do
    so** — `telemetry.py` and `provenance.py` were found by reading, and the
    next one would not have been. An import graph cannot draw the line between
    measurement and mechanism, but it can insist somebody has drawn it."""
    assert hard_core.unclassified() == []
    assert set(hard_core.mechanisms()) < set(hard_core.reachable())


def test_a_new_module_in_the_closure_fails_the_gate(tmp_path, monkeypatch):
    """A check that cannot fail proves nothing. Behavior: a module a canonical
    tool reaches, called neither measurement nor mechanism, is an error naming
    the tools that reach it — so the classification is made with its
    consequence in view rather than as a formality (RT6)."""
    reachable = hard_core.reachable()
    monkeypatch.setattr(hard_core, "reachable",
                        lambda: [*reachable, "newz/world/feeds.py"])
    monkeypatch.setattr(hard_core, "reached_by", lambda m: ["tools/evidence.py"])

    errors = hard_core.validate()

    assert any("newz/world/feeds.py" in e and "tools/evidence.py" in e
               for e in errors), errors


def test_a_mechanism_must_say_why_it_is_not_measurement():
    """Behavior: the cheapest way past this gate is to write `mechanism` and
    move on, so the row carries a reason and an empty one is an error."""
    for path, why in hard_core.mechanisms().items():
        assert why.strip(), f"{path} is called a mechanism and does not say why"


def test_a_module_cannot_be_both_frozen_and_a_mechanism():
    """Behavior: a contradiction here is a boundary nobody can read."""
    for path in hard_core.mechanisms():
        assert not hard_core.contains(path), path


def test_the_closure_is_transitive_and_not_one_hop():
    """Behavior: the fault the freeze already had once. A tool's measurement
    code reached two hops out is as writable as one hop out, and the file stays
    byte-identical while the number changes."""
    reach = set(hard_core.reachable())

    # health.py -> cleanroom.verify, which no canonical tool imported until W7
    assert "newz/surface/cleanroom.py" in reach
    # claims.py -> resolutions.store -> the model it reads
    assert "newz/resolutions/model.py" in reach


def test_gitignore_is_inside_the_core():
    """Behavior: `changed_paths()` reads `git diff` and `git ls-files --others
    --exclude-standard`, so an ignored file is in neither — which makes
    'ignore it, then edit it' a two-step path to invisibility. The file is
    tracked, so closing the first step costs nothing."""
    assert hard_core.contains(".gitignore")


def test_both_import_forms_reach_the_freeze():
    """W10's accident, kept as a test. Behavior: `from newz.evidence import X`
    and `from newz.evidence.X import y` are the same dependency, and only the
    second used to pull X into the frozen set — an import style decided whether
    measurement code was writable."""
    frozen = set(hard_core.canonical_paths())

    # tools/pre_loop_baseline.py imports it the package way
    assert "newz/evidence/pre_loop.py" in frozen
    # and the package itself, which states the rules every module in it holds
    assert "newz/evidence/__init__.py" in frozen
