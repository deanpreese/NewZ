"""The gate, and the trailers a recovery reads (P4 E8.0 / W5, W6).

Done-when: a fresh clone installs and runs the suite from a declared
environment with no hand steps, the suite is green on ten consecutive runs, and
a commit that breaks either check is refused.

The first two are facts about a machine and a clock; what a test can hold is
the third — that the refusal exists, that it names what is wrong, and that the
environment is declared rather than remembered.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
HOOKS = REPO / ".githooks"

GOOD = """W1: a change that says what it costs to cross backwards

Schema: 0039
Restart: required
Class: A
Semantics: yes
"""


def _commit_msg(tmp_path, text: str) -> subprocess.CompletedProcess:
    f = tmp_path / "COMMIT_EDITMSG"
    f.write_text(text)
    return subprocess.run([sys.executable, str(HOOKS / "commit-msg"), str(f)],
                          capture_output=True, text=True)


def test_a_complete_message_passes(tmp_path):
    assert _commit_msg(tmp_path, GOOD).returncode == 0


@pytest.mark.parametrize("drop", ["Schema", "Restart", "Class", "Semantics"])
def test_a_missing_trailer_refuses_the_commit_and_names_it(tmp_path, drop):
    """Behavior: E8.2 makes git the whole recovery story, and a trailer that is
    sometimes there is a trailer the runner cannot read. All four or none."""
    text = "\n".join(l for l in GOOD.splitlines() if not l.startswith(f"{drop}:"))

    r = _commit_msg(tmp_path, text)

    assert r.returncode == 1
    assert drop in r.stdout


def test_a_malformed_value_is_not_a_trailer(tmp_path):
    """Behavior: `Semantics: probably` answers nothing. The point of the field
    is that a recovery can act on it without reading the diff."""
    r = _commit_msg(tmp_path, GOOD.replace("Semantics: yes", "Semantics: probably"))

    assert r.returncode == 1
    assert "Semantics" in r.stdout


def test_a_merge_or_fixup_is_left_alone(tmp_path):
    """Behavior: a merge has no change of its own to classify, and refusing one
    teaches the operator to reach for --no-verify, which is the flag that makes
    the whole hook optional."""
    for text in ("Merge branch 'x'\n", "fixup! W1: something\n"):
        assert _commit_msg(tmp_path, text).returncode == 0


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
    suite. One command runs all three, and the hook runs the command."""
    source = (REPO / "tools" / "gate.py").read_text()

    assert "pytest" in source
    assert "check_invariants.py" in source
    assert "freeze_check.py" in source
    assert (HOOKS / "pre-commit").read_text().count("tools/gate.py") == 1


def test_the_hook_is_executable():
    """Behavior: git runs these directly. A hook without the bit is a hook that
    silently never fires, which is worse than not having one."""
    for hook in ("pre-commit", "commit-msg"):
        assert (HOOKS / hook).stat().st_mode & 0o111, hook
