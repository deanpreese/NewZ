"""The gate (P4 E8.0 / W5).

Done-when: a fresh clone installs and runs the suite from a declared
environment with no hand steps, the suite is green on ten consecutive runs, and
a commit that breaks either check is refused.

The first two are facts about a machine and a clock. The third had a local
`pre-commit` hook and **the operator removed it on 2026-08-20** — a hook that
runs on every commit was not wanted, and it was never a boundary against the
loop anyway (RT5). What is left is one command that runs the three checks, and
CI running it on a machine that is not the operator's. What a test can hold is
that the command exists and runs all three, and that the environment is
declared rather than remembered.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def test_the_environment_is_declared_and_matches_the_package(tmp_path):
    """Behavior: "conda agent13" was a fact about one machine — the interpreter
    was 3.13 while pyproject asked for >=3.12 and five dependencies were
    installed by hand, so a fresh clone could not collect the suite."""
    env = yaml.safe_load((REPO / "environment.yml").read_text())
    pinned = {line.split("==")[0].lower()
              for dep in env["dependencies"] if isinstance(dep, dict)
              for line in dep["pip"]}

    declared = (REPO / "pyproject.toml").read_text()
    for package in ("python-dotenv", "pyyaml", "httpx", "trafilatura",
                    "beautifulsoup4", "pytest"):
        assert package in pinned, f"{package} is in pyproject and not declared here"
        assert package.lower() in declared.lower()


def test_the_gate_runs_the_three_checks_that_existed_separately():
    """Behavior: on 2026-08-19 a commit went in red because nothing ran the
    suite. One command runs all three, and running it is the operator's act."""
    source = (REPO / "tools" / "gate.py").read_text()

    assert "pytest" in source
    assert "check_invariants.py" in source
    assert "freeze_check.py" in source
