"""Gate 0: policy decisions are deterministic and versioned, and no network
access exists yet.

The network test is static rather than behavioural. Phase 0 has no fetcher, so
the honest assertion is not that nothing was called but that nothing could be:
the package imports no networking module at all.
"""

from __future__ import annotations

import ast
import random
from pathlib import Path

import pytest

from newz.canonical import dumps
from newz.domain.enums import EdgeRelation
from newz.policy.bundle import BUNDLE
from newz.policy.promotion import assess
from tests import builders as b
from tests.casefiles import build, case_paths, load_raw

PACKAGE = Path(__file__).resolve().parents[1] / "newz"

FORBIDDEN_MODULES = {
    "socket",
    "ssl",
    "http",
    "urllib",
    "urllib3",
    "ftplib",
    "smtplib",
    "telnetlib",
    "asyncio",
    "requests",
    "httpx",
    "aiohttp",
    "webbrowser",
    "subprocess",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


@pytest.mark.parametrize(
    "path", sorted(PACKAGE.rglob("*.py")), ids=lambda p: str(p.relative_to(PACKAGE.parent))
)
def test_no_network_access_exists(path):
    assert not (_imported_modules(path) & FORBIDDEN_MODULES), path


def test_the_policy_engine_depends_on_nothing_outside_the_standard_library():
    """ADR-0003 keeps the dependency floor at zero for the part that decides."""
    third_party = set()
    stdlib = {"ast", "dataclasses", "enum", "hashlib", "json", "pathlib", "re", "sys", "typing"}
    for path in PACKAGE.rglob("*.py"):
        for module in _imported_modules(path):
            if module not in stdlib and module not in {"newz", "collections", "__future__"}:
                third_party.add(module)
    assert third_party == set()


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
