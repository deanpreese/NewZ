"""Rule 7's mechanism (P4 epic E2.5).

Done-when, in two directions: every metric a consumer can read has a grade, and
an ungraded metric cannot be cited by anything downstream. The second half is
what makes Rule 7 a mechanism rather than a convention — a rule asking people to
state the grade is a rule; a function that refuses to render a number whose
provenance nobody recorded is a guarantee.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from newz.evidence import grades
from newz.evidence.grades import GRADES, UngradedMetric, grade_of, known, reason_of, tag

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "evolution" / "instruments.yaml"


def test_every_registered_metric_has_a_grade_and_a_reason():
    """Direction one. Behavior: a grade with no stated reason is a label, and a
    label is what Rule 7 exists to replace."""
    metrics = yaml.safe_load(REGISTRY.read_text())["metrics"]

    assert metrics, "the registry has no metrics block"
    for name, row in metrics.items():
        assert row["grade"] in GRADES, f"{name}: {row['grade']!r}"
        assert row.get("reason", "").strip(), f"{name} has a grade and no reason"
        assert row.get("emitted_by"), f"{name} names no instrument"


def test_an_ungraded_metric_cannot_be_cited(): 
    """Direction two, and the point of the epic. Consumer: tools/claims.py.
    Behavior: citing a number nobody graded raises instead of printing."""
    with pytest.raises(UngradedMetric, match="cannot be cited"):
        grade_of("a_number_nobody_graded")
    with pytest.raises(UngradedMetric):
        tag("a_number_nobody_graded")


def test_the_read_takes_its_labels_from_the_registry_not_from_itself():
    """Consumer: tools/claims.py. Behavior: the grades printed beside figures
    come from evolution/instruments.yaml, so changing a grade changes the read
    and no hardcoded label can drift away from the record.

    Before E2.5 the tool printed "[mechanical]" as a string literal — true at
    the time it was typed, and answerable to nothing."""
    src = (REPO / "tools" / "claims.py").read_text()

    assert "from newz.evidence.grades import tag" in src
    for literal in ("[mechanical]", "[mixed", "[model-graded", "[known-biased"):
        assert literal not in src, f"{literal!r} is hardcoded rather than looked up"


def test_a_model_graded_metric_says_where_the_judgment_sits():
    """Rule 4's mechanism. Behavior: for every model-graded metric the registry
    names the judge, so "a model decided this" is checkable rather than
    remembered."""
    metrics = yaml.safe_load(REGISTRY.read_text())["metrics"]
    judged = {n: r for n, r in metrics.items() if r["grade"] == "model-graded"}

    assert judged, "no metric is model-graded, which cannot be true of this system"
    for name, row in judged.items():
        assert re.search(r"judge|gate|triage|model", row["reason"], re.I), \
            f"{name} is model-graded and does not say which judgment"


def test_advance_acceptance_is_graded_model_graded():
    """The specific inconsistency that produced Rule 7: P3 cited this figure as
    part of the evidence that produced it, two pages after Rule 4 says a model
    judge produces operation and never evidence."""
    assert grade_of("advance_acceptance") == "model-graded"
    assert "Rule 4" in reason_of("advance_acceptance")


def test_the_self_column_carries_its_known_bias():
    """R-15. Behavior: imported v1 episodes are uniformly provenance='self', so
    the metric is mechanical AND distorted, and the grade says the second part
    rather than letting "mechanical" imply trustworthy."""
    assert grade_of("positions_changed_by_self") == "known-biased"
    assert "R-15" in reason_of("positions_changed_by_self")


def test_a_bad_grade_in_the_registry_is_refused_at_load(tmp_path, monkeypatch):
    """Behavior: the registry itself is validated, so a typo cannot silently
    become a fifth grade nobody defined."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("metrics:\n  x:\n    grade: probably-fine\n    reason: hmm\n")
    grades._registry.cache_clear()
    monkeypatch.setattr(grades, "REGISTRY", bad)

    with pytest.raises(ValueError, match="expected one of"):
        grades.known()

    grades._registry.cache_clear()


def test_every_metric_the_read_cites_is_registered():
    """Rule 2 for measurements: a metric the tool names must exist in the
    registry, so the two cannot drift apart."""
    src = (REPO / "tools" / "claims.py").read_text()
    cited = set(re.findall(r"tag\(\s*'([a-z_]+)'", src))

    assert cited, "no metric is cited through the registry"
    assert cited <= known(), f"cited but ungraded: {sorted(cited - known())}"
