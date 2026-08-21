"""The plan's own staleness instrument (P4 epic E2.10).

Done-when: a materially moved premise flags the argument resting on it, and the
report says so unprompted.

The hook is a failure that already happened. PLAN §1 records "0 outcomes the
being did not grade itself", Phase 1 exists to change it, E1.4 shipped on
2026-08-19 and began changing it — and nothing remarked on that, because a
plan's premises lived in prose and prose does not notice when it stops being
true.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from newz.evidence import premises as P
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "p.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def test_the_premise_registry_is_well_formed():
    """Every premise says what it asserts, where the plan states it, and what
    rests on it — a premise with no consequence recorded is a number, and the
    number was never the point."""
    assert P.validate() == []


def test_every_measurable_premise_points_at_a_registered_metric():
    """E2.5 and E2.10 holding each other honest: a premise cannot be checked
    against a figure nobody graded."""
    from newz.evidence.grades import known

    reg = yaml.safe_load((REPO / "evolution" / "premises.yaml").read_text())["premises"]
    for name, row in reg.items():
        if row.get("metric"):
            assert row["metric"] in known(), f"{name} -> {row['metric']}"


def test_a_moved_premise_reports_what_rested_on_it(store, tmp_path):
    """E2.10's Done-when. Behavior: the finding is not that a figure moved, it
    is that an argument needs re-reading — so the render carries the sentence."""
    now = time.time()
    store.execute(
        "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
        " resolver, due_at, provenance, status) VALUES (?,?,?,?,?,?, 'open')",
        (now, "the index prints below 40", "the March release",
         "the statistical office", now + 30 * 86400, "concern:1"))
    store.commit()

    drifts = {d.premise: d for d in P.check(store, tmp_path, now=now)}
    d = drifts["no-ungraded-outcomes"]

    assert d.moved, "one claim falsifies '0 outcomes the being did not grade itself'"
    assert "the whole of phase 1" in d.render().lower()


def test_a_premise_that_holds_does_not_shout(store, tmp_path):
    now = time.time()

    d = {x.premise: x for x in P.check(store, tmp_path, now=now)}["no-ungraded-outcomes"]

    assert not d.moved
    assert "what rested on it" not in d.render()


def test_an_unmeasurable_premise_is_recorded_as_held_on_faith(store, tmp_path):
    """Behavior: `metric: null` is a real answer. A figure the plan asserts that
    nothing can re-measure is a premise held on faith, and saying so is better
    than inventing an instrument to cover it."""
    d = {x.premise: x for x in P.check(store, tmp_path, now=time.time())}["one-person"]

    assert not d.measurable and not d.moved
    assert "HELD ON FAITH" in d.render()
    assert "counts rows, not relationships" in d.render()


def test_only_mechanical_premises_can_justify_a_plan_change(store, tmp_path):
    """§12.6's load-bearing rule. Behavior: `moved()` filters to mechanical
    premises, so a plan change cannot be justified by a figure a model judged —
    drift in the model's judging would otherwise be indistinguishable from
    change in the world."""
    from newz.evidence.grades import grade_of

    now = time.time()
    store.execute(
        "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
        " resolver, due_at, provenance, status) VALUES (?,?,?,?,?,?, 'open')",
        (now, "c", "w", "r", now + 30 * 86400, "concern:1"))
    store.commit()

    for d in P.moved(store, tmp_path, now=now):
        assert grade_of(d.metric) == "mechanical", d.premise


def test_the_rule_is_authoritys_and_not_a_second_copy_of_it(store, tmp_path,
                                                            monkeypatch):
    """W4. Behavior: `moved()` asks `authority.may_justify` rather than
    re-implementing it. INV-073 states the rule once; this line stated it
    twice, in a system whose complaint about DERIVED_FROM was a second copy
    drifting from the first — and `authority.py` had no production caller at
    all until this one."""
    import newz.evidence.authority as authority

    asked = []
    monkeypatch.setattr(authority, "may_justify",
                        lambda m: asked.append(m) or False)

    now = time.time()
    store.execute(
        "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
        " resolver, due_at, provenance, status) VALUES (?,?,?,?,?,?, 'open')",
        (now, "c", "w", "r", now + 30 * 86400, "concern:1"))
    store.commit()

    assert P.moved(store, tmp_path, now=now) == []
    assert asked, "moved() consults authority rather than the grade directly"


def test_a_premise_pointed_at_a_near_neighbour_metric_is_the_bug_e28_guards():
    """Recorded because it happened here, on 2026-08-20, while building this.

    `grounding-is-mostly-self` states a share of episodes by provenance and was
    first pointed at `single_source_positions`, which counts positions with a
    dominant source. Different quantities, one plausible name apart, and it
    reported a false MOVED of 0.5 -> 0.83. The fix was a metric that measures
    what the premise states."""
    reg = yaml.safe_load((REPO / "evolution" / "premises.yaml").read_text())["premises"]

    assert reg["grounding-is-mostly-self"]["metric"] == "self_grounding_share"


def test_drift_is_reported_without_being_asked_for():
    """E2.10's second clause. Behavior: an ordinary evidence read prints the
    premises, because waiting until someone is drafting a change before checking
    is how a plan goes stale between drafts."""
    src = (REPO / "tools" / "evidence.py").read_text()

    assert "report_premises(conn, cfg.repo_root)" in src
    assert src.count("report_premises(conn, cfg.repo_root)") >= 2, \
        "premises must print on the default read, not only on request"
