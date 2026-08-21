"""The plan's epics, machine-readable, with a drift check (P4 epic E2.11).

Done-when: the loop reads the queue from `epics.yaml`, and the drift check fails
the build when a row and PLAN disagree.

A copy of a document is a liability the moment it stops agreeing with it, and
this one is the queue an autonomous builder would work from.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from newz.evidence import epics as E

REPO = Path(__file__).resolve().parent.parent
PLAN = REPO / "PLAN.md"


def test_the_registry_matches_the_plan():
    """The Done-when's second half, as one call. Behavior: ids, titles,
    dependencies and built-status are re-derived from PLAN and compared."""
    assert E.drift() == []


def test_a_registry_that_falls_behind_the_plan_fails_the_build():
    """Behavior: the check is not decorative. An epic PLAN marks built while
    the registry still calls it open is caught — the drift that would let a
    builder skip work it had not done.

    The subject is chosen at runtime rather than named: an earlier version
    hardcoded E3.1 and broke the day E3.1 shipped, which in a repo whose queue
    moves daily is a test that fails for being right."""
    victim = next(e for e, r in E.epics().items() if r["status"] == "open")
    title = E.epics()[victim]["title"]
    plan = REPO.joinpath("PLAN.md").read_text().replace(
        f"**{victim} — {title}**", f"**{victim} — {title}** *(built 2026-08-20)*", 1)

    errors = E.drift(plan)

    assert any(victim in e and "built" in e for e in errors)


def test_a_dependency_the_plan_does_not_state_is_caught():
    """The mistake the first scaffold made. E1.0's `Depends on:` reads "nothing.
    **E5.2's deliberation floor is pulled forward with it**", and a regex read
    that as a dependency on E5.2. A reader does not; a generator does — which is
    why the judgment half of this file is authored and only the mechanical half
    is re-derived."""
    reg = yaml.safe_load((REPO / "evolution" / "epics.yaml").read_text())["epics"]

    assert reg["E1.0"]["depends_on"] == [], \
        "E1.0 depends on nothing; E5.2 is pulled forward, not depended on"


def test_every_epic_says_how_its_done_when_can_be_closed():
    """The judgment this file exists to carry. Behavior: each epic is classed
    mechanical, in-life, operator-judgment or dormant."""
    for eid, row in E.epics().items():
        assert row.get("done_when") in E.CLASSES, f"{eid}: {row.get('done_when')!r}"


def test_phase_seven_is_dormant_and_has_no_done_when():
    """Behavior: the classes and PLAN agree about the phase that is deliberately
    unscheduled — a dormant epic with a Done-when would mean work in flight
    nothing owns, which is the INV-044 principle applied to the ledger itself."""
    for eid, row in E.epics().items():
        if eid.startswith("E7."):
            assert row["done_when"] == "dormant" and row["status"] == "dormant"


def test_the_queue_is_the_epics_whose_dependencies_are_built():
    """E2.11's first half. Behavior: `ready` is the computation done by hand
    three times on 2026-08-19, now standing."""
    ready = set(E.ready())

    assert ready, "no epic is available, which cannot be true mid-plan"
    blocked = {e for e, r in E.epics().items()
               if r["status"] == "open"
               and any(E.epics()[d]["status"] != "built" for d in r["depends_on"])}
    assert not (ready & blocked), "an epic with an unbuilt dependency is not ready"
    for eid in ready:
        assert E.epics()[eid]["status"] == "open"
        assert all(E.epics()[d]["status"] == "built"
                   for d in E.epics()[eid]["depends_on"])


def test_the_builders_queue_went_with_the_builder():
    """P4 E3A.4. `closable_by_test` existed to tell an autonomous builder which
    ready epics a test could close. Phase 8 is struck, there is no builder, and
    a reader with nothing reading it is the Rule 2 defect the ledger has caught
    in tables for months. Behavior: it is gone, and Rule 6's distinction lives
    where it always did — in `done_when`, which `ready()` reports and a person
    reads."""
    assert not hasattr(E, "closable_by_test")

    judged = [e for e, r in E.epics().items()
              if r["done_when"] in ("in-life", "operator-judgment")]
    assert judged, "no epic needs judgment, which cannot be true of this plan"


def test_an_epic_id_may_carry_a_letter():
    """P4 Phase 3A. Behavior: `E3A.1` parses out of PLAN and sorts between
    `E3.9` and `E4.1`. The regex read `E\\d+\\.\\d+` and the sort key read
    `int(e.split(".")[0][1:])`, so the first lettered phase was invisible to
    the drift check and raised ValueError in the queue — a plan the drift check
    cannot see is the failure this file exists to prevent."""
    assert "E3A.1" in E.from_plan()
    assert E._order("E3.9") < E._order("E3A.1") < E._order("E4.1")


# ── the acceptance criterion is pinned (P4 W9) ──────────────────────────

def test_every_epic_with_a_done_when_pins_it():
    """W9. Behavior: hard_core.yaml records that PLAN is protected by section
    and that no check reads sections — the loop may append completion records
    and may never edit an epic's `Done when`, and nothing enforced the second
    half. A loop that can soften its own acceptance criterion has none."""
    plan = E.from_plan()
    reg = E.epics()

    for eid, row in plan.items():
        if row["has_done_when"]:
            assert reg[eid].get("done_when_sha") == row["done_when_sha"], eid


def test_softening_a_done_when_is_caught():
    """A check that cannot fail proves nothing. Behavior: the clause moves in
    PLAN, the hash in the registry does not, and drift says which epic and what
    the two are."""
    text, n = re.subn(r"\*Done when:\* a diff touching a canonical instrument\s+"
                      r"is\s+refused,\s+and\s+a\s+test\s+asserts\s+the\s+refusal\.",
                      "*Done when:* a diff touching a canonical instrument is noted.",
                      PLAN.read_text())
    assert n == 1, "the E3.9 clause this test softens has moved"

    errors = E.drift(text)

    assert any("E3.9" in e and "does not match the hash" in e for e in errors), errors


def test_reflowing_a_clause_is_not_an_amendment():
    """Behavior: PLAN is prose the operator rewraps. A hash that moved on a
    line break would fire on edits that changed nothing, and a check that cries
    wolf is one people learn to update without reading (RT7)."""
    clause = "a fresh clone installs and runs the suite\nfrom a declared environment"

    assert E.sha_of(clause) == E.sha_of(
        "a fresh clone installs   and runs the suite from a declared environment")


def test_only_the_done_when_is_pinned():
    """Behavior: the narrowing is deliberate. Intent, Hooks and Decision rules
    stay convention, because hashing prose the operator edits constantly would
    fail the gate on ordinary work — and hard_core.yaml says so rather than
    implying the whole file is held."""
    body = PLAN.read_text()
    changed = re.sub(r"\*Hooks:\* §7 portability[^\n]*\n[^\n]*",
                     "*Hooks:* something else entirely.", body)

    assert changed != body, "the Hooks line this test edits has moved"
    assert E.drift(changed) == []
