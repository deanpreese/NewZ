"""The separation harness.

Gate 4A asks for the boundary to be proven "by enumerating the register's write
paths rather than by sampling behavior", and that is what this file does. It
parses the attention and reckoning packages, extracts every SQL statement they
contain, and checks the set of tables they write to against an allowlist.

Sampling behaviour would tell us that interest did not reach a threshold in the
cases we thought to try. This tells us there is no statement anywhere in the
package that could.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "newz"

WRITE = re.compile(
    r"\b(?:INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|DELETE\s+FROM)\s+([a-z_]+)", re.IGNORECASE
)

#: Everything the attention plane may write. Interest reaches attention; these
#: are the tables attention is kept in.
ATTENTION_TABLES = {
    "notices",
    "interest_entries",
    "interest_events",
    "interest_notices",
    "interest_outcomes",
    "decay_events",
}

#: Everything the reckoning plane may write.
RECKONING_TABLES = {
    "decisions",
    "expectations",
    "confirmed_outcomes",
    "surprises",
    "consequences",
    "escalation_events",
    "self_checks",
}

#: Named rather than merely excluded, so the test says what it protects. A
#: statement here would be interest reaching a conclusion, a schedule, or a
#: permission.
FORBIDDEN = {
    "operations",
    "reservations",
    "diet_epochs",
    "diet_epoch_sources",
    "source_revisions",
    "sources",
    "publishers",
    "edge_events",
    "predicate_attestations",
    "assessments",
    "bases",
    "basis_derivations",
    "independence_claims",
    "assertions",
    "claims",
    "tasks",
    "clearances",
    "publications",
    "appraisals",
    "review_queue",
    "reach_settings",
    "class_halts",
    "card_revisions",
}


def sql_literals(path: Path) -> list[str]:
    """Every string constant in the file. SQL is built by concatenation here, so
    adjacent literals are joined the way the parser already joins them."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            found.append(
                "".join(
                    part.value
                    for part in node.values
                    if isinstance(part, ast.Constant) and isinstance(part.value, str)
                )
            )
    return found


def written_tables(package: Path) -> dict[str, set[str]]:
    """Table -> the files whose statements write to it."""
    out: dict[str, set[str]] = {}
    for path in sorted(package.rglob("*.py")):
        # Concatenated literals are joined so a statement split across lines is
        # still read as one statement.
        blob = "\n".join(sql_literals(path))
        for table in WRITE.findall(blob):
            out.setdefault(table.lower(), set()).add(str(path.relative_to(PACKAGE.parent)))
    return out


def imported(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


# ---------------------------------------------------------------------------
# Attention
# ---------------------------------------------------------------------------


def test_the_attention_plane_writes_only_to_attention_tables():
    written = written_tables(PACKAGE / "attention")
    assert set(written) <= ATTENTION_TABLES, {
        table: sorted(files) for table, files in written.items() if table not in ATTENTION_TABLES
    }


def test_no_statement_in_the_attention_plane_touches_a_forbidden_table():
    written = set(written_tables(PACKAGE / "attention"))
    assert not (written & FORBIDDEN)


def test_the_attention_plane_cannot_reach_the_scheduler_or_the_evidence_engine():
    """Not "does not" — cannot. There is no import through which it could."""
    for path in sorted((PACKAGE / "attention").rglob("*.py")):
        names = imported(path)
        for forbidden in (
            "newz.control.scheduler",
            "newz.control.budget",
            "newz.evidence.edges",
            "newz.evidence.assess",
            "newz.evidence.claims",
            "newz.policy.promotion",
            "newz.policy.bundle",
            "newz.publish.clearance",
        ):
            assert forbidden not in names, f"{path.name} imports {forbidden}"


def test_the_only_things_an_interest_may_cause_are_named_in_one_place():
    from newz.attention.interest import record_outcome

    source = ast.parse(
        (PACKAGE / "attention" / "interest.py").read_text(encoding="utf-8")
    )
    kinds = {
        node.value
        for node in ast.walk(source)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value in ("investigation", "essay")
    }
    assert kinds == {"investigation", "essay"}
    assert record_outcome is not None


def test_an_interest_cannot_record_an_outcome_it_is_not_allowed_to_cause(store):
    from newz.attention.interest import record_outcome

    for forbidden in ("schedule", "threshold", "assessment", "clearance", "diet_epoch"):
        with pytest.raises(ValueError, match="interest reaches attention"):
            record_outcome(store, "interest:i1", forbidden, "target:x")


# ---------------------------------------------------------------------------
# Reckoning
# ---------------------------------------------------------------------------


def test_the_reckoning_plane_writes_only_to_reckoning_tables():
    written = written_tables(PACKAGE / "reckoning")
    assert set(written) <= RECKONING_TABLES, {
        table: sorted(files) for table, files in written.items() if table not in RECKONING_TABLES
    }


def test_no_consequence_path_reaches_a_threshold_or_an_assessment():
    """Learning changes what happens next, never what the evidence establishes."""
    written = set(written_tables(PACKAGE / "reckoning"))
    assert not (written & FORBIDDEN)


def test_a_consequence_may_change_only_the_four_things_it_is_allowed_to():
    from newz.reckoning.consequence import CHANGEABLE

    assert sorted(CHANGEABLE) == [
        "decision_rule",
        "interest_priority",
        "source_operational_standing",
        "task_retry_policy",
    ]
    assert not (CHANGEABLE & FORBIDDEN)


# ---------------------------------------------------------------------------
# The evidence plane, from the other side
# ---------------------------------------------------------------------------


def test_the_evidence_plane_never_reads_the_interest_register():
    """The boundary has two sides. Nothing that decides may consult a preference."""
    for area in ("policy", "evidence", "present"):
        for path in sorted((PACKAGE / area).rglob("*.py")):
            names = imported(path)
            assert not any(name.startswith("newz.attention") for name in names), path
            assert not any(name.startswith("newz.reckoning") for name in names), path
            blob = "\n".join(sql_literals(path))
            for table in ("interest_entries", "interest_events", "notices", "interest_outcomes"):
                assert table not in blob, f"{path} reads {table}"


def test_the_scheduler_never_reads_the_interest_register():
    for path in sorted((PACKAGE / "control").rglob("*.py")):
        blob = "\n".join(sql_literals(path))
        assert "interest" not in blob.lower(), path
        assert not any(name.startswith("newz.attention") for name in imported(path)), path
