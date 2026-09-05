"""Gate 0: policy decisions are deterministic and versioned, and the network
lives behind one door.

The network test is static rather than behavioural — the honest assertion is not
that nothing was called but that nothing *could* be. Phase 0 had no fetcher at
all, so it asserted that the package imported no networking module anywhere.
Phase 1 has one, so the assertion moved rather than weakened: exactly one module
may open a socket, and the part of the system that decides anything still cannot
reach the network to decide it.
"""

from __future__ import annotations

import ast
import random
import sys
from pathlib import Path

import pytest

from newz.canonical import dumps
from newz.domain.enums import EdgeRelation
from newz.policy.bundle import BUNDLE
from newz.policy.promotion import assess
from tests import builders as b
from tests.casefiles import build, case_paths, load_raw

PACKAGE = Path(__file__).resolve().parents[1] / "newz"

#: Modules that can reach the network, by their full dotted name. `urllib.parse`
#: is deliberately absent: parsing a URL is not opening one, and the URL policy
#: needs it precisely so that nothing further down has to.
NETWORK_MODULES = {
    "socket",
    "ssl",
    "http",
    "http.client",
    "urllib.request",
    "urllib.error",
    "ftplib",
    "smtplib",
    "asyncio",
    "requests",
    "httpx",
    "aiohttp",
    "webbrowser",
}

#: The modules allowed through, and why each is its own door rather than a
#: shared HTTP helper. The acquisition transport fetches URLs the system did not
#: choose and treats everything it receives as hostile. The model client talks
#: to exactly one endpoint, configured by the operator and checked to be local.
#: They are separate risks, and one helper serving both would let either inherit
#: the other's assumptions.
NETWORK_BOUNDARY = frozenset(
    {"newz/acquisition/transport.py", "newz/model/client.py"}
)

#: Shelling out is not an evidence path, and a package that can start a process
#: can reach the network without importing any of the names above.
FORBIDDEN_EVERYWHERE = {"subprocess", "multiprocessing", "ctypes"}


def _imported_modules(path: Path) -> set[str]:
    """Every module a file imports, by full dotted name and by root."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
            found.add(node.module.split(".")[0])
    return found


@pytest.mark.parametrize(
    "path", sorted(PACKAGE.rglob("*.py")), ids=lambda p: str(p.relative_to(PACKAGE.parent))
)
def test_only_the_transport_can_reach_the_network(path):
    relative = str(path.relative_to(PACKAGE.parent))
    imported = _imported_modules(path)
    if relative in NETWORK_BOUNDARY:
        # A door exists, and this is one of them.
        assert imported & NETWORK_MODULES
        return
    assert not (imported & NETWORK_MODULES), relative


@pytest.mark.parametrize(
    "path", sorted(PACKAGE.rglob("*.py")), ids=lambda p: str(p.relative_to(PACKAGE.parent))
)
def test_nothing_in_the_package_starts_a_process(path):
    assert not (_imported_modules(path) & FORBIDDEN_EVERYWHERE), path


DECIDING_PACKAGES = ("policy", "domain", "graph")


@pytest.mark.parametrize("area", DECIDING_PACKAGES)
def test_the_part_that_decides_cannot_reach_the_network_or_the_store(area):
    """Policy is a pure function of its inputs, and stays reachable only that way."""
    for path in sorted((PACKAGE / area).rglob("*.py")):
        imported = _imported_modules(path)
        assert not (imported & NETWORK_MODULES), path
        assert "sqlite3" not in imported, path
        assert not any(module.startswith("newz.store") for module in imported), path
        assert not any(module.startswith("newz.acquisition") for module in imported), path
        assert not any(module.startswith("newz.model") for module in imported), path


def test_the_model_cannot_be_reached_from_anywhere_that_decides():
    """`SPEC.md` 2.3: a model proposes and never grants capability. The clearest
    form of that is the deciding packages having no way to call one."""
    for area in DECIDING_PACKAGES:
        for path in sorted((PACKAGE / area).rglob("*.py")):
            assert "newz.model" not in " ".join(_imported_modules(path)), path


def test_extraction_validates_without_reaching_the_model_or_the_store():
    """The half that decides what survives a proposal is pure, so a proposal can
    be replayed against the same segments and validate identically."""
    path = PACKAGE / "extract" / "proposal.py"
    imported = _imported_modules(path)
    assert not (imported & NETWORK_MODULES)
    assert "sqlite3" not in imported
    assert not any(module.startswith("newz.model") for module in imported)
    assert not any(module.startswith("newz.store") for module in imported)


#: The complete third-party surface, one ADR each. Adding a name here is a
#: decision that needs its own ADR, which is what makes this list worth having.
ALLOWED_DEPENDENCIES = {"pypdf", "cryptography"}

#: Where each is allowed to be imported. A supply-chain surface is contained by
#: staying in one place, and a cipher reachable from the policy engine would be
#: a cipher somebody eventually uses to decide something.
DEPENDENCY_HOMES = {
    "pypdf": {"newz/parse/pdf.py"},
    "cryptography": {"newz/store/erasure.py"},
}


def test_the_package_takes_only_the_dependencies_an_adr_records():
    """ADR-0003 set the floor at zero; ADR-0004 and ADR-0005 each raised it by one."""
    third_party = set()
    for path in PACKAGE.rglob("*.py"):
        for module in _imported_modules(path):
            root = module.split(".")[0]
            if root in ("newz", "__future__") or root in sys.stdlib_module_names:
                continue
            third_party.add(root)
    assert third_party == ALLOWED_DEPENDENCIES


@pytest.mark.parametrize("dependency", sorted(ALLOWED_DEPENDENCIES))
def test_each_dependency_lives_only_where_it_is_needed(dependency):
    for path in sorted(PACKAGE.rglob("*.py")):
        if dependency in _imported_modules(path):
            assert (
                str(path.relative_to(PACKAGE.parent)) in DEPENDENCY_HOMES[dependency]
            ), f"{dependency} imported in {path}"


@pytest.mark.parametrize("path", case_paths(), ids=lambda p: p.stem)
def test_a_case_reproduces_exactly_under_shuffled_input(path):
    """Determinism is not a property of the inputs arriving in a good order."""
    case = load_raw(path)
    baseline = dumps(assess(build(case)))
    rng = random.Random(20260905)
    for _ in range(5):
        shuffled = dict(case)
        for key in ("bases", "assertions", "edges", "independence", "tasks"):
            if key in shuffled:
                items = list(shuffled[key])
                rng.shuffle(items)
                shuffled[key] = items
        assert dumps(assess(build(shuffled))) == baseline


def test_an_assessment_reproduces_across_processes_by_construction():
    """Nothing in a derivation reads a clock, a hash seed, or an environment."""
    claim = b.claim()
    a1 = b.assertion("assertion:a1")
    payload = dict(
        assertions={a1.id: a1},
        bases={"basis:b1": b.basis("basis:b1")},
    )
    first = assess(
        b.inputs(claim, b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1"), **payload)
    )
    second = assess(
        b.inputs(claim, b.edge("edge:e1", a1, claim, EdgeRelation.SUPPORTS, "basis:b1"), **payload)
    )
    assert dumps(first) == dumps(second)
    assert first.policy_version == BUNDLE.version
    assert first.code_version == BUNDLE.code_version


def test_the_policy_is_versioned_and_hashed():
    assert BUNDLE.version == "1.0.0"
    assert len(BUNDLE.digest) == 64
    assert len(BUNDLE.matrix) == 2016
