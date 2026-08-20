"""The metric-to-purpose map (P4 epic E2.6).

Rule 2 extended from tables and flags to measurements. Done-when: no metric
exists without a named consumer and nothing depends on a metric that does not
exist — **both directions tested**, which is what the two asymmetric tests below
are for.
"""

from __future__ import annotations

import pytest
import yaml

from newz.evidence.grades import known as graded
from newz.evidence.purpose import (
    REGISTRY,
    UnknownPurpose,
    check,
    metrics,
    purposes,
    served_by,
    unserved,
)


def test_the_map_holds_in_both_directions():
    """E2.6's Done-when, as one call. Behavior: every metric names a purpose
    that exists, every purpose says what it is, and nothing needs a metric
    nobody produces."""
    assert check() == []


def test_no_metric_exists_without_a_named_consumer():
    """Direction one — Rule 2's own clause. A metric nothing consumes is the
    same defect as a column nothing reads, and the ledger has caught the second
    for months while nothing caught the first."""
    for name, row in metrics().items():
        assert row.get("serves"), f"{name} serves nothing"


def test_nothing_depends_on_a_metric_that_does_not_exist():
    """Direction two. A read depending on a figure nobody produces is a plan for
    a measurement, not a measurement."""
    for pid, row in purposes().items():
        for needed in (row or {}).get("needs") or []:
            assert needed in metrics(), f"{pid} needs unregistered {needed!r}"


def test_a_purpose_with_no_metric_is_reported_and_not_an_error():
    """The gap list is the useful output. Six of TRUE_NORTH §10's ten items are
    not measurable — a compelling demonstration, fluent language, evidence
    scores disconnected from sustained quality — and manufacturing a proxy for
    them would be §10's own failure mode.

    So this asserts the gaps EXIST and are visible, rather than asserting there
    are none."""
    gaps = set(unserved())

    assert gaps, "a map with no gaps means proxies were invented for the unmeasurable"
    assert "tn10:demonstration" in gaps
    assert "tn10:scores" in gaps


def test_the_kill_condition_that_matters_most_now_has_one():
    """P4 Phase 8 calls nights-slept the kill condition that matters most —
    "development is measured in nights, not commits, and a loop that costs
    sleep is subtracting".

    From 2026-08-20 this test asserted the gap, so that closing it would fail
    here and whoever was standing there would read why it mattered. E2.9 closed
    it the same day. The assertion is inverted rather than deleted, because the
    sentence above is the reason the metric exists."""
    served = set(served_by("kill:nights-slept"))

    assert "nights_slept" in served
    assert "kill:nights-slept" not in set(unserved())


def test_every_metric_is_both_graded_and_purposed():
    """E2.5 and E2.6 are one discipline: a number carries its grade AND says
    what it is for. Neither half is worth much alone."""
    assert set(metrics()) == graded()


def test_asking_about_an_unregistered_purpose_raises():
    with pytest.raises(UnknownPurpose):
        served_by("purpose:invented-on-the-spot")


def test_every_true_north_section_ten_item_is_represented():
    """Behavior: the map covers §10 completely, so an item cannot be quietly
    dropped by never being written down."""
    tn10 = {p for p in purposes() if p.startswith("tn10:")}

    assert len(tn10) == 10, f"§10 has ten items; the map has {len(tn10)}"
