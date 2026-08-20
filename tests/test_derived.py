"""The derivation layer (P4 epic E3.7).

Done-when: four of TRUE_NORTH §10's six checkable items are readable, each
through E2.7 with a baseline.

The shortfall was never collection. These are ratios of figures the store
already held, and counting instruments rather than derivable quantities is what
made the gap look larger than it was.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from newz.evidence import derived as D
from newz.evidence.baseline import baselined_metrics, record_all
from newz.evidence.grades import grade_of
from newz.evidence.purpose import served_by
from newz.store.db import open_db
from newz.store.migrations import apply_pending

REPO = Path(__file__).resolve().parent.parent
MAIN_SQL = REPO / "newz" / "store" / "sql" / "main"
DAY = 86400.0


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "d.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def test_a_derivation_takes_the_weakest_grade_among_its_inputs():
    """The rule that makes composition safe. Behavior: a mechanical numerator
    over a model-graded denominator is model-graded, and cannot carry a
    decision that neither input could.

    This is where a grade would otherwise be lost — the composition looks like
    arithmetic and quietly launders a judgment into a number that reads clean."""
    metrics = yaml.safe_load((REPO / "evolution" / "instruments.yaml").read_text())["metrics"]

    for name, inputs in D.DERIVED_FROM.items():
        assert name in metrics, name
        expected = D.grade_of_derivation([grade_of(i) for i in inputs])
        assert metrics[name]["grade"] == expected, (
            f"{name}: registry says {metrics[name]['grade']!r}, weakest input is {expected!r}")


def test_the_weakest_grade_is_computed_and_not_asserted():
    assert D.grade_of_derivation(["mechanical", "model-graded"]) == "model-graded"
    assert D.grade_of_derivation(["mechanical", "mixed"]) == "mixed"
    assert D.grade_of_derivation(["mechanical", "mechanical"]) == "mechanical"
    # `mixed` is the weaker of the two, and deliberately so: a known bias is
    # characterised (R-15 names which way it leans), while `mixed` has an
    # uncharacterised model judgment upstream. Rule 4's concern is judgments,
    # not error.
    assert D.grade_of_derivation(["known-biased", "mixed"]) == "mixed"


def test_every_derived_metric_names_a_real_input():
    """Behavior: a derivation cannot claim to come from a figure nobody
    produces — the same Rule 2 discipline E2.6 applies to purposes."""
    for name, inputs in D.DERIVED_FROM.items():
        for i in inputs:
            assert grade_of(i), f"{name} derives from unregistered {i!r}"


def test_four_of_section_tens_checkable_items_are_now_served():
    """E3.7's Done-when, read off the purpose map rather than asserted."""
    for purpose in ("tn10:volume", "tn10:consistency",
                    "tn10:novelty-without-consequence",
                    "tn10:autonomy-without-perspective"):
        assert served_by(purpose), purpose


def test_each_derivation_reports_through_the_baseline_layer(store, tmp_path):
    """Behavior: derived metrics are written by the same nightly cadence as
    their inputs, so each carries a series rather than being computed on read."""
    produced = {r.metric for r in record_all(store, tmp_path)}

    assert set(D.DERIVED_FROM) <= produced
    assert produced == set(baselined_metrics())


def test_a_ratio_with_no_denominator_is_unreadable_not_zero(store):
    """INV-044 in the place it is easiest to get wrong. Behavior: no
    development in the window means the volume ratio has no denominator —
    reporting the episode count alone would be exactly the volume figure §10
    warns about, with nothing to divide it by."""
    now = time.time()
    store.execute("INSERT INTO episodes (ts, kind, provenance, summary,"
                  " digest_eligible) VALUES (?,?,?,?,1)",
                  (now, "reading", "world:arxiv", "something read"))
    store.commit()

    v = D.volume_against_development(store, since=now - 7 * DAY)

    assert v.value is None
    assert "no denominator" in v.unreadable


def test_consequence_rate_is_s1e_stated_as_a_ratio(store):
    """Behavior: claims settled per advance accepted. Advances accumulating
    while nothing is settled is §10's third item, and it is what the live store
    reads today."""
    now = time.time()
    store.execute("INSERT INTO concerns (id, opened_at, kind, statement,"
                  " why_open, closing_condition, status, salience, origin)"
                  " VALUES (1,?,?,?,?,?,?,?,?)",
                  (now, "inquiry", "q", "w", "c", "open", 0.5, "reading"))
    store.execute("INSERT INTO concern_advances (concern_id, ts, kind, summary,"
                  " evidence_json) VALUES (1,?,?,?,'[]')", (now, "reasoning", "s"))
    store.commit()

    v = D.consequence_rate(store, since=now - 7 * DAY)

    assert v.value == 0.0, "an advance with nothing settled is a consequence rate of zero"


def test_autonomy_is_measured_against_the_world_share_not_a_position_count(store):
    """Behavior: the denominator is what came from outside, because a being can
    hold a great many positions and still be talking to itself — which is the
    §10 item, not a proxy for it."""
    src = (REPO / "newz" / "evidence" / "derived.py").read_text()
    fn = src[src.index("def autonomy_against_world_grounding"):src.index("def all_derived")]

    assert "self_grounding_share" in fn
    assert "1.0 - own.value" in fn
