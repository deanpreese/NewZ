"""The plan's epics, machine-readable, with a drift check (P4 epic E2.11).

Done-when: the loop reads the queue from `epics.yaml`, and the drift check fails
the build when a row and PLAN disagree.

A copy of a document is a liability the moment it stops agreeing with it, and
this one is the queue an autonomous builder would work from.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from newz.evidence import epics as E

REPO = Path(__file__).resolve().parent.parent


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


def test_an_epic_a_test_cannot_close_is_not_offered_to_a_builder():
    """Rule 6's distinction, made machine-readable. Behavior: an in-life or
    operator-judgment epic can be BUILT autonomously and cannot be CLOSED that
    way, so the builder's queue is narrower than the ready queue."""
    assert set(E.closable_by_test()) <= set(E.ready())
    for eid in E.closable_by_test():
        assert E.epics()[eid]["done_when"] == "mechanical"

    judged = [e for e, r in E.epics().items()
              if r["done_when"] in ("in-life", "operator-judgment")]
    assert judged, "no epic needs judgment, which cannot be true of this plan"
    assert not (set(judged) & set(E.closable_by_test()))
