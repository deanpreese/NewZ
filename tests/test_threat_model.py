"""The threat model cites controls; this checks the citations are real.

`docs/threat-model.md` is what a Gate 6 security review reads against. A threat
model whose entries drift from the code is worse than none: it tells a reviewer
a control exists, and the reviewer ticks the box. So every `**Code:**` path and
every `**Test:**` function named in it must exist here, and a control deleted
from the code fails this test rather than quietly outliving its entry.

What this cannot check is whether the control is any good, or whether the
threats are the right ones. That is the review, and it is a person's.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "docs" / "threat-model.md"

ENTRY = re.compile(r"^### (T-\d+) — (.+)$", re.M)
FIELD = re.compile(r"^\*\*([\w ]+):\*\* (.+?)(?=\n\*\*|\n\n|\n---|\Z)", re.M | re.S)
CITED = re.compile(r"`([^`]+)`")


def _entries() -> dict[str, dict[str, str]]:
    text = MODEL.read_text(encoding="utf-8")
    found: dict[str, dict[str, str]] = {}
    marks = list(ENTRY.finditer(text))
    for index, match in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        body = text[match.end() : end]
        fields = {name: value.strip() for name, value in FIELD.findall(body)}
        fields["title"] = match.group(2)
        found[match.group(1)] = fields
    return found


ENTRIES = _entries()


def _test_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


def test_the_threat_model_has_entries_at_all():
    assert len(ENTRIES) >= 20, sorted(ENTRIES)
    assert not set(ENTRIES) - {f"T-{n:02d}" for n in range(1, len(ENTRIES) + 1)}


@pytest.mark.parametrize("threat", sorted(ENTRIES))
def test_every_entry_names_a_control_and_its_residual(threat):
    entry = ENTRIES[threat]
    if "Requirement" in entry:  # section 7: a control that was or is unmet
        for field in ("Requirement", "Actual", "Test"):
            assert entry.get(field), (threat, field, sorted(entry))
        # Either it still stands open, and says why and what would close it, or
        # it has been closed and carries the code and residual of any other
        # entry. What it may not do is stop saying which of those it is.
        unmet = entry.get("Why it stands") and entry.get("Closing it")
        closed = entry.get("Code") and entry.get("Residual")
        assert unmet or closed, (threat, sorted(entry))
        return
    for field in ("Vector", "Control", "Code", "Test", "Residual"):
        assert entry.get(field), (threat, field)
    assert entry["Residual"] != "", threat


@pytest.mark.parametrize("threat", sorted(ENTRIES))
def test_every_cited_module_exists(threat):
    cited = ENTRIES[threat].get("Code", "")
    if not cited:
        return
    for path in CITED.findall(cited):
        assert (ROOT / path).is_file(), (threat, path)


@pytest.mark.parametrize("threat", sorted(ENTRIES))
def test_every_cited_test_exists(threat):
    cited = ENTRIES[threat].get("Test", "")
    assert cited, threat
    for reference in CITED.findall(cited):
        assert "::" in reference, (threat, reference)
        path, name = reference.split("::", 1)
        assert (ROOT / path).is_file(), (threat, path)
        assert name in _test_functions(ROOT / path), (threat, reference)


def test_every_area_the_plan_names_is_covered():
    """`PLAN.md` names seven; a model that skipped one would still look complete."""
    text = MODEL.read_text(encoding="utf-8")
    for area in (
        "## 1. Acquisition",
        "## 2. Document parsing",
        "## 3. Prompt injection",
        "## 4. Model data exfiltration",
        "## 5. Sensitive-person data",
        "## 6. Publication abuse",
        "## 7. Unmet controls",
    ):
        assert area in text, area


def test_the_unmet_controls_are_stated_rather_than_omitted():
    """A threat model listing only what is built describes strengths."""
    unmet = {t for t, entry in ENTRIES.items() if "Requirement" in entry}
    assert unmet, "the section exists because there are unmet controls"
    for threat in unmet:
        assert ENTRIES[threat]["Actual"], threat


def test_the_architecture_no_longer_claims_process_isolation():
    """T-19: the document asserted a control the system does not have.

    A reviewer reading that sentence ticks the box, which makes the wrong
    document more dangerous than no document.
    """
    architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Fetch and parse run as separate processes" not in architecture
    assert "T-19" in architecture or "one process" in architecture


def test_gate_6_reports_the_same_unmet_controls_the_model_does():
    """A status that lags the document it summarises is worse than none.

    `gate_6_status` listed T-19 as open for a day after it was closed. It is a
    hand-kept list on purpose — the package does not read its own documentation
    at runtime — so this is what keeps it honest.
    """
    from newz.pilot.drills import gate_6_status

    class _NoStore:
        def query(self, *args):
            return []

        def one(self, *args):
            return {"n": 0}

    reported = {line.split()[0] for line in gate_6_status(_NoStore())["unmet_controls"]}
    still_open = {
        threat
        for threat, entry in ENTRIES.items()
        if entry.get("Why it stands") and entry.get("Closing it")
    }
    assert reported == still_open, (reported, still_open)
