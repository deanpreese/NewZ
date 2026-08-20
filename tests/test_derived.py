"""The derivation layer (P4 epic E3.7).

Done-when: four of TRUE_NORTH §10's six checkable items are readable, each
through E2.7 with a baseline.

The shortfall was never collection. These are ratios of figures the store
already held, and counting instruments rather than derivable quantities is what
made the gap look larger than it was.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import yaml

from newz.evidence import derived as D
from newz.evidence import mechanical as M
from newz.evidence.baseline import baselined_metrics, record_all
from newz.evidence.grades import grade_of
from newz.evidence.mechanical import Value
from newz.evidence.perspective_window import read_window
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


def test_a_ratio_with_no_denominator_is_unreadable_not_zero():
    """INV-044 in the place it is easiest to get wrong. Behavior: no
    development in the window means the volume ratio has no denominator —
    reporting the episode count alone would be exactly the volume figure §10
    warns about, with nothing to divide it by."""
    v = D.volume_against_development(D.Inputs("volume_against_development", {
        "episodes_recorded": Value(41.0),
        "perspective_items_developed": Value(0.0),
    }))

    assert v.value is None
    assert "no denominator" in v.unreadable


def test_an_unreadable_input_makes_the_derivation_unreadable_and_says_which():
    """Behavior: a ratio over a figure that was not measured was not measured
    either — and the reason travels, so the read says what is missing rather
    than that something is."""
    v = D.consequence_rate(D.Inputs("consequence_rate", {
        "claims_settled": Value(2.0),
        "advances_offered": Value(unreadable="the door's log is absent"),
    }))

    assert v.value is None
    assert v.unreadable == "the door's log is absent"


def test_a_derivation_cannot_read_an_input_it_does_not_declare():
    """R-37c's fix, as a behavior rather than a promise: the declaration is the
    function's argument list. Reaching past it raises — which is what makes the
    grade computed from that row trustworthy."""
    i = D.Inputs("restatement_rate", {
        "perspective_novelty": Value(0.2),
        "advances_offered": Value(9.0),
    })

    assert D.restatement_rate(i).value == 0.8
    with pytest.raises(D.UndeclaredInput):
        i["advances_offered"]


def test_a_declared_input_the_nightly_pass_does_not_produce_is_refused():
    """The other direction. Behavior: a derivation cannot declare a figure
    nobody computes — the Rule 2 discipline E2.6 applies to purposes, applied
    to composition."""
    with pytest.raises(KeyError):
        D.Inputs("consequence_rate", {"claims_settled": Value(1.0)})


def test_consequence_rate_is_s1e_stated_as_a_ratio():
    """Behavior: claims settled per advance accepted. Advances accumulating
    while nothing is settled is §10's third item, and it is what the live store
    reads today."""
    v = D.consequence_rate(D.Inputs("consequence_rate", {
        "claims_settled": Value(0.0),
        "advances_offered": Value(110.0),
    }))

    assert v.value == 0.0, "an advance with nothing settled is a consequence rate of zero"


def test_autonomy_is_measured_against_the_world_share_not_a_position_count():
    """Behavior: the denominator is what came from outside, because a being can
    hold a great many positions and still be talking to itself — which is the
    §10 item, not a proxy for it. Halving the world share doubles the ratio;
    the count of positions held does not enter it."""
    def read(self_share):
        return D.autonomy_against_world_grounding(
            D.Inputs("autonomy_against_world_grounding", {
                "advances_offered": Value(8.0),
                "pieces_written": Value(2.0),
                "self_grounding_share": Value(self_share),
            })).value

    assert read(0.5) == 20.0
    assert read(0.75) == 40.0


def test_nothing_grounded_outside_the_being_is_unreadable_not_infinite():
    """Behavior: a world share of zero is the finding itself, not a division."""
    v = D.autonomy_against_world_grounding(
        D.Inputs("autonomy_against_world_grounding", {
            "advances_offered": Value(8.0),
            "pieces_written": Value(2.0),
            "self_grounding_share": Value(1.0),
        }))

    assert v.value is None
    assert "itself the finding" in v.unreadable


def test_the_window_reaches_the_perspective_read(store):
    """The half of R-37c that produced a wrong number rather than a wrong
    declaration. Behavior: a night outside the window is not in the window —
    `read_window` took a `since` from its caller and dropped it, so both
    Perspective-derived metrics were all-time figures filed nightly under a
    168-hour label."""
    now = time.time()
    for version, ts in ((1, now - 30 * DAY), (2, now - DAY)):
        store.execute(
            "INSERT INTO perspective (version, ts, content, diff_json,"
            " token_count) VALUES (?,?,?,?,?)",
            (version, ts, "p", json.dumps(
                {"carried": 10, "added": ["a"], "revised": []}), 100))
    store.commit()

    assert read_window(store).nights and len(read_window(store).nights) == 2
    assert len(read_window(store, since=now - 7 * DAY).nights) == 1
    assert M.perspective_items_developed(store, since=now - 7 * DAY).value == 1.0
