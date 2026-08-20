"""The instrument registry is complete and the tools are portable (PLAN E8.1).

Two failures this catches, both of which were live in the tree on 2026-08-19:

  - a tool that hardcodes an absolute path outside the repo. Three probes did.
    Run by hand on another machine that fails loudly; run by the SEL against a
    path that happens to exist, it silently measures a different checkout and
    reports a number that looks fine.

  - a tool that exists and is in no row of the registry. The registry is what
    the loop steers by (E8.3's map, E8.9's freeze); a tool outside it is a
    measurement nobody classified, which is the state the whole tree was in
    before this epic.
"""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "evolution" / "instruments.yaml"

# Fields the registry exists to make checkable. A row missing any of them is
# not a classified instrument, it is a name in a list.
REQUIRED = ("tool", "reads", "measures", "denominator", "model_in_chain", "method", "canonical")


def _registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text())


def _tools() -> set[str]:
    return {f"tools/{p.name}" for p in (REPO / "tools").glob("*.py")}


def test_no_tool_hardcodes_a_path_outside_the_repo():
    """Consumer: every tool in tools/. Behavior: each resolves the repo from
    __file__, so a clone runs its own instruments and never another checkout's."""
    offenders = []
    for name in sorted(_tools()):
        text = (REPO / name).read_text()
        for line in text.splitlines():
            if "sys.path" not in line:
                continue
            if "'/" in line or '"/' in line:          # a quoted absolute path
                offenders.append(f"{name}: {line.strip()}")
    assert not offenders, "absolute sys.path entries: " + "; ".join(offenders)


def test_every_tool_is_classified_exactly_once():
    """Consumer: evolution/instruments.yaml. Behavior: adding a tool without a
    registry row fails the build, so the set the loop steers by stays complete."""
    reg = _registry()
    listed = [i["tool"] for i in reg["instruments"]]
    for group in reg["not_instruments"].values():
        listed.extend(group)

    dupes = {n for n in listed if listed.count(n) > 1}
    assert not dupes, f"listed more than once: {sorted(dupes)}"

    on_disk = _tools()
    assert not (on_disk - set(listed)), f"tools with no registry row: {sorted(on_disk - set(listed))}"
    assert not (set(listed) - on_disk), f"registry rows with no tool: {sorted(set(listed) - on_disk)}"


def test_every_instrument_row_carries_the_fields_it_is_for():
    """Consumer: the SEL's state read (E8.13) and E8.3's map. Behavior: an
    instrument cannot enter the registry without saying what it measures, what
    it reads, its denominator, and whether a model touched its chain."""
    for row in _registry()["instruments"]:
        missing = [f for f in REQUIRED if f not in row]
        assert not missing, f"{row.get('tool')}: missing {missing}"
        if row["model_in_chain"]:
            assert row.get("model_where"), (
                f"{row['tool']}: model_in_chain is true and model_where is unstated — "
                "PLAN Rule 4 needs to know WHERE the judgment sits"
            )


def test_the_registry_names_only_read_only_tools_as_instruments():
    """Consumer: E8.9's freeze. Behavior: a tool that writes to the store can
    never be frozen as an instrument, because it is not one."""
    writes = ("INSERT ", "UPDATE ", "DELETE ", ".commit()")
    for row in _registry()["instruments"]:
        text = (REPO / row["tool"]).read_text()
        found = [w for w in writes if w in text]
        assert not found, f"{row['tool']} is registered as an instrument but writes: {found}"
