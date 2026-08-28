"""The boundaries that never move (P4 E6.5).

Four failures this catches:

  - a permanent clause is named and does not exist. A typo here does not fail
    open, it fails closed on the governance path: every future amendment would
    be refused for dropping a clause that was never there.

  - the withdrawal path stops reading the list. `tools/amend_constitution.py`
    is the only way a clause leaves the constitution, so it is the only place
    the refusal can live.

  - the list migrates onto the clauses themselves. The amendment writes the
    whole constitution from one file; a permanence flag carried there could be
    cleared by the same edit that removes the clause.

  - the core quietly grows to cover everything. Half the constitution must stay
    withdrawable or Phase 6 has nothing left to withdraw and the phase is
    meaningless rather than safe.
"""

from pathlib import Path

import yaml

from newz.evidence import hard_core

REPO = Path(__file__).resolve().parent.parent

# E6.5's three categories: law, others' rights and safety, honest
# representation of what it is — plus the two clauses without which no core
# holds at all. Written here by hand so that a change to the registry has to be
# a change to this list too.
EXPECTED = {
    "honesty-001",
    "don't-fabricate-memory-001",
    "no-impersonation-001",
    "no-manipulation-001",
    "operator-privacy-001",
    "read-only-web-001",
    "refuse-coercion-001",
    "respect-revision-001",
}


def _live_clause_ids() -> set[str]:
    newest = hard_core.newest_constitution()
    assert newest is not None, "no constitution/vN.yaml to check against"
    doc = yaml.safe_load(newest.read_text())
    return {c["id"] for c in doc["clauses"]}


def test_every_permanent_clause_exists():
    """A protected clause that resolves to nothing refuses nothing."""
    missing = hard_core.permanent_clause_ids() - _live_clause_ids()
    assert not missing, f"permanent and not in the constitution: {sorted(missing)}"


def test_the_list_is_what_was_agreed():
    assert hard_core.permanent_clause_ids() == EXPECTED


def test_every_permanent_clause_states_why():
    for row in hard_core.permanent_clauses():
        assert row.get("clause"), row
        assert row.get("why"), f"{row.get('clause')} is permanent with no reason"


def test_withdrawing_a_permanent_clause_is_refused():
    """The check the amendment path runs, exercised without a store."""
    live = _live_clause_ids()
    assert hard_core.withdrawn_permanent(live) == []
    without = live - {"honesty-001"}
    assert hard_core.withdrawn_permanent(without) == ["honesty-001"]
    assert hard_core.withdrawn_permanent(set()) == sorted(EXPECTED)


def test_the_amendment_tool_reads_the_registry():
    """The refusal lives on the only path a clause can leave by."""
    src = (REPO / "tools" / "amend_constitution.py").read_text()
    assert "withdrawn_permanent" in src
    # Before the confirmation prompt, so --yes cannot walk past it.
    assert src.index("withdrawn_permanent(new_ids)") < src.index("write it?")


def test_permanence_is_not_carried_on_the_clause():
    """It would travel in the same edit that removes the clause."""
    newest = hard_core.newest_constitution()
    doc = yaml.safe_load(newest.read_text())
    for c in doc["clauses"]:
        assert "permanent" not in c, (
            f"{c['id']} carries its own permanence; the registry is the only "
            "place that survives the edit it constrains")


def test_half_the_constitution_stays_withdrawable():
    """A core that covers everything makes Phase 6 meaningless, not safe."""
    live = _live_clause_ids()
    withdrawable = live - hard_core.permanent_clause_ids()
    assert len(withdrawable) >= len(live) // 2, (
        f"only {len(withdrawable)} of {len(live)} clauses may be withdrawn")


def test_the_registry_itself_is_inside_the_core():
    """A boundary the constrained party can widen is not a boundary."""
    assert hard_core.contains("evolution/hard_core.yaml")


def test_validate_is_clean():
    assert hard_core.validate() == []
