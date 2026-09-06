"""Deployment modes, pause conditions, shadow, and the pilot reports.

Gate 5 itself cannot pass here: it wants thirty elapsed days, live network
reads, and the operator's approval. What these tests hold is the machinery that
makes those countable — and, at the end, an honest statement of what is still
outstanding.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from newz.pilot import catalog_review, reports, shadow
from newz.pilot.modes import (
    MODE_BEHAVIOUR,
    DeploymentMode,
    TransitionRefused,
    assessments_are_authoritative,
    current_mode,
    enter_lockdown,
    history,
    may_publish,
    transition,
)
from newz.pilot.violations import (
    PAUSE_CONDITIONS,
    acknowledge_day,
    eligible_dates,
    gate_5_status,
    open_violations,
    record_day,
    record_route,
    record_violation,
    resolve_violation,
    routes_outstanding,
    unacknowledged_days,
)
from tests import world as world_module

#: The same day the world fixture reserves under, which is today: see
#: `tests/world.py`.
DAY = world_module.DAY


@pytest.fixture
def world(store):
    return world_module.build(store)


def _to_shadow(store, actor="operator:dean"):
    return transition(
        store,
        transition_id="transition:t1",
        to=DeploymentMode.SHADOW,
        actor=actor,
        reason="the fixtures pass; time to see live material",
    )


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def test_the_system_starts_in_fixture_mode(store):
    assert current_mode(store) is DeploymentMode.FIXTURE
    assert not MODE_BEHAVIOUR[DeploymentMode.FIXTURE]["live_acquisition"]


def test_the_path_to_authoritative_live_assessment_runs_through_shadow(store):
    with pytest.raises(TransitionRefused, match="not a transition"):
        transition(
            store,
            transition_id="transition:t1",
            to=DeploymentMode.PILOT,
            actor="operator:dean",
            reason="skip ahead",
        )
    _to_shadow(store)
    assert current_mode(store) is DeploymentMode.SHADOW
    transition(
        store,
        transition_id="transition:t2",
        to=DeploymentMode.PILOT,
        actor="operator:dean",
        reason="shadow exited cleanly",
    )
    assert current_mode(store) is DeploymentMode.PILOT


def test_shadow_computes_and_withholds(store):
    _to_shadow(store)
    assert not assessments_are_authoritative(store)
    assert not may_publish(store)


def test_lockdown_is_the_only_mode_the_system_may_enter_on_its_own(store):
    _to_shadow(store)
    with pytest.raises(TransitionRefused, match="only mode"):
        transition(
            store,
            transition_id="transition:t9",
            to=DeploymentMode.PILOT,
            actor="system",
            reason="I think it is fine",
            automatic=True,
        )
    enter_lockdown(store, "transition:lock", "an admitted edge was missing its span")
    assert current_mode(store) is DeploymentMode.LOCKDOWN
    assert not may_publish(store)


def test_the_system_cannot_clear_its_own_halt(store):
    _to_shadow(store)
    enter_lockdown(store, "transition:lock", "a publication path violation")
    with pytest.raises(TransitionRefused, match="cannot clear its own halt"):
        transition(
            store,
            transition_id="transition:out",
            to=DeploymentMode.SHADOW,
            actor="system",
            reason="it looks fine now",
            automatic=True,
        )


def test_leaving_lockdown_needs_the_violations_resolved_first(store):
    _to_shadow(store)
    record_violation(
        store,
        violation_id="violation:v1",
        condition="missing_artifact_or_span_on_admitted_edge",
        detail="edge:e1 cites a span that is not there",
        detected_at=f"{DAY}T10:00:00",
    )
    enter_lockdown(store, "transition:lock", "integrity breach")
    with pytest.raises(TransitionRefused, match="cause, fix and fixture"):
        transition(
            store,
            transition_id="transition:out",
            to=DeploymentMode.FIXTURE,
            actor="operator:dean",
            reason="looks fine",
        )
    resolve_violation(
        store,
        "violation:v1",
        cause="the extractor accepted a span whose segment had been re-parsed",
        fix="span verification re-runs against the current segmentation at admission",
        fixture="tests/test_parse.py::test_span_verification_refuses_every_way_a_quotation_can_be_wrong",
        resolved_at=f"{DAY}T12:00:00",
    )
    transition(
        store,
        transition_id="transition:out",
        to=DeploymentMode.FIXTURE,
        actor="operator:dean",
        reason="the cause is understood and fixtured",
    )
    assert current_mode(store) is DeploymentMode.FIXTURE


def test_lockdown_never_returns_straight_to_production(store):
    _to_shadow(store)
    transition(
        store, transition_id="t2", to=DeploymentMode.PILOT, actor="operator:dean", reason="r"
    )
    transition(
        store, transition_id="t3", to=DeploymentMode.PRODUCTION, actor="operator:dean", reason="r"
    )
    enter_lockdown(store, "t4", "a breach")
    with pytest.raises(TransitionRefused, match="not a transition"):
        transition(
            store,
            transition_id="t5",
            to=DeploymentMode.PRODUCTION,
            actor="operator:dean",
            reason="carry on",
        )


def test_every_transition_is_recorded_with_its_code_version(store):
    _to_shadow(store)
    enter_lockdown(store, "transition:lock", "a breach")
    rows = history(store)
    assert [row["to_mode"] for row in rows] == ["shadow", "lockdown"]
    assert rows[1]["automatic"] == 1
    assert all(row["code_version"] for row in rows)


# ---------------------------------------------------------------------------
# Pause conditions
# ---------------------------------------------------------------------------


def test_every_pause_condition_the_plan_names_exists():
    assert len(PAUSE_CONDITIONS) == 7
    assert "claimant_only_factual_promotion" in PAUSE_CONDITIONS
    assert "critical_backup_or_restore_failure" in PAUSE_CONDITIONS


def test_an_unknown_pause_condition_is_refused(store):
    with pytest.raises(ValueError, match="a pause condition is one of"):
        record_violation(
            store,
            violation_id="violation:v1",
            condition="something_went_a_bit_wrong",
            detail="",
            detected_at=f"{DAY}T10:00:00",
        )


def test_resumption_takes_a_cause_a_fix_and_a_fixture(store):
    record_violation(
        store,
        violation_id="violation:v1",
        condition="false_independence_count",
        detail="two syndicated copies counted twice",
        detected_at=f"{DAY}T10:00:00",
    )
    for cause, fix, fixture in (
        ("", "", ""),
        ("a cause", "", ""),
        ("a cause", "a fix", ""),
    ):
        with pytest.raises(ValueError, match="cause, a fix, and a permanent"):
            resolve_violation(
                store, "violation:v1", cause=cause, fix=fix, fixture=fixture, resolved_at=DAY
            )
    resolve_violation(
        store,
        "violation:v1",
        cause="the derivation link was never recorded",
        fix="lineage is folded into the independence group at load",
        fixture="tests/test_gate2.py::test_a_syndicated_copy_is_not_a_second_basis",
        resolved_at=f"{DAY}T12:00:00",
    )
    assert open_violations(store) == ()


def test_dates_during_a_pause_are_not_eligible(store):
    record_day(store, "2026-09-01", retained_reads=6)
    record_violation(
        store,
        violation_id="violation:v1",
        condition="unbounded_or_unauthorized_fetch",
        detail="a fetch left the catalog",
        detected_at="2026-09-02T09:00:00",
    )
    record_day(store, "2026-09-02", retained_reads=2)
    record_day(store, "2026-09-03", retained_reads=0)
    resolve_violation(
        store,
        "violation:v1",
        cause="an adapter built a URL from retained content",
        fix="leads are checked against the URL policy before they are recorded",
        fixture="tests/test_research.py::test_a_lead_the_fetcher_would_refuse_is_not_recorded",
        resolved_at="2026-09-03T15:00:00",
    )
    record_day(store, "2026-09-04", retained_reads=5)

    assert eligible_dates(store) == ("2026-09-01", "2026-09-04")
    row = store.one("SELECT * FROM pilot_days WHERE local_day = '2026-09-02'")
    assert "unbounded_or_unauthorized_fetch" in row["paused_reason"]


def test_a_fix_that_touches_evidence_resets_the_route_requirement(store):
    resetting = record_violation(
        store,
        violation_id="violation:v1",
        condition="claimant_only_factual_promotion",
        detail="a claimant edge promoted a factual claim",
        detected_at=f"{DAY}T10:00:00",
    )
    not_resetting = record_violation(
        store,
        violation_id="violation:v2",
        condition="critical_backup_or_restore_failure",
        detail="the restore drill failed on artifact hashes",
        detected_at=f"{DAY}T11:00:00",
    )
    assert resetting.resets_routes
    assert not not_resetting.resets_routes


def test_the_first_seven_clean_days_need_the_operators_eyes(store):
    for day in range(1, 9):
        record_day(store, f"2026-09-0{day}", retained_reads=5)
    assert len(unacknowledged_days(store)) == 7
    acknowledge_day(store, "2026-09-01", "operator:dean")
    assert "2026-09-01" not in unacknowledged_days(store)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def test_routes_are_tracked_per_stage_and_code_version(store, world):
    outstanding_before = routes_outstanding(store, "shadow")
    assert len(outstanding_before) == 9  # the world's nine sources

    for canary in world_module.SOURCES:
        record_route(store, canary.revision.id, canary.revision.expected_mime, "shadow", DAY)
    assert routes_outstanding(store, "shadow") == ()
    # Pilot is a separate stage: shadow exercise does not satisfy it.
    assert len(routes_outstanding(store, "pilot")) == 9


# ---------------------------------------------------------------------------
# Shadow
# ---------------------------------------------------------------------------


def test_a_shadow_assessment_is_computed_and_not_recorded(store, world):
    from newz.evidence.assess import assess_claim, current_assessment

    claim = world.claim("registry", "radar")
    assess_claim(store, claim, "assessment:a1")
    before = current_assessment(store, claim).state.value
    _to_shadow(store)

    result = shadow.shadow_assess(store, claim, before, "shadow:s1")
    assert result.matched
    # Exactly one authoritative assessment still, and it is the one from before.
    assert store.one("SELECT COUNT(*) AS n FROM assessments WHERE claim_id = ?", claim)["n"] == 1


def test_shadow_assessment_only_runs_in_shadow(store, world):
    from newz.evidence.assess import assess_claim

    claim = world.claim("registry", "radar")
    assess_claim(store, claim, "assessment:a1")
    with pytest.raises(shadow.NotInShadow):
        shadow.shadow_assess(store, claim, "reported", "shadow:s1")


def test_every_divergence_needs_a_recorded_cause_before_shadow_exits(store, world):
    from newz.evidence.assess import assess_claim

    claim = world.claim("registry", "radar")
    assess_claim(store, claim, "assessment:a1")
    _to_shadow(store)
    result = shadow.shadow_assess(store, claim, "supported", "shadow:s1")
    assert not result.matched
    assert shadow.unexplained_divergences(store) == ("shadow:s1",)

    criteria = shadow.exit_criteria(store)
    assert not criteria["satisfied"]

    with pytest.raises(ValueError, match="records its cause"):
        shadow.record_cause(store, "shadow:s1", "")
    shadow.record_cause(
        store, "shadow:s1", "the fixture expectation predated the counterpart lane being required"
    )
    assert shadow.unexplained_divergences(store) == ()


def test_shadow_exits_only_when_all_three_conditions_hold(store, world):
    from newz.evidence.assess import assess_claim

    claim = world.claim("registry", "radar")
    assess_claim(store, claim, "assessment:a1")
    state = store.one("SELECT state FROM assessments WHERE claim_id = ?", claim)["state"]
    _to_shadow(store)
    for canary in world_module.SOURCES:
        record_route(store, canary.revision.id, canary.revision.expected_mime, "shadow", DAY)
    shadow.shadow_assess(store, claim, state, "shadow:s1")

    criteria = shadow.exit_criteria(store)
    assert criteria["satisfied"], criteria

    record_violation(
        store,
        violation_id="violation:v1",
        condition="false_independence_count",
        detail="something",
        detected_at=f"{DAY}T10:00:00",
    )
    assert not shadow.exit_criteria(store)["satisfied"]


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def test_every_funnel_stage_lands_on_the_operators_day(store, world):
    """The ledger stamps UTC; the funnel reports the operator's local date.

    `reserved` reads a local `local_day` column and every other stage reads a
    UTC timestamp. West of Greenwich those name different days for the hours
    between local midnight and UTC midnight, and the funnel showed nine
    reservations and zero fetches for work that had plainly run.
    """
    attempt = store.one("SELECT id, operation_id, url FROM attempts LIMIT 1")
    stamped = "2026-03-14T23:30:00"  # UTC; a different date in most of the world
    with store.write() as connection:
        connection.execute(
            "INSERT INTO attempts (id, operation_id, url, started_at, outcome, "
            "refusal_reason, http_status, bytes_read, redirects_json, detail) "
            "VALUES ('attempt:tz', ?, ?, ?, 'retained', NULL, 200, 10, '[]', '')",
            (attempt["operation_id"], attempt["url"], stamped),
        )

    local_day = (
        datetime.fromisoformat(stamped).replace(tzinfo=UTC).astimezone().date().isoformat()
    )
    assert reports.funnel(store, local_day)["fetched"] == 1

    # And the two halves of the funnel agree with each other, which is the
    # property that actually broke: a reservation and its own fetch are the
    # same day's work in every timezone.
    counted = reports.funnel(store, DAY)
    assert counted["reserved"] == counted["fetched"] == 9


def test_the_funnel_counts_every_stage_separately(store, world):
    day = datetime.now().date().isoformat()
    counted = reports.funnel(store, day)
    assert counted["reserved"] == 9
    assert counted["fetched"] == 9
    assert counted["retained"] == 9
    assert counted["parsed"] == 9
    assert counted["asserted"] >= 9
    assert set(counted) >= {
        "leads",
        "reserved",
        "fetched",
        "retained",
        "refused",
        "errored",
        "parsed",
        "asserted",
        "edges_admitted",
        "edges_refused",
        "assessments",
        "cards_invalidated",
    }


def test_offered_and_retained_shares_are_reported_separately(store, world):
    shares = reports.offered_and_retained_shares(store)
    assert shares["offered_role_share"]
    assert shares["retained_role_share"]
    assert "different questions" in shares["note"]


def test_concentration_is_measured_over_retained_reads(store, world):
    figures = reports.concentration(store)
    assert figures["retained_reads"] == 9
    assert figures["top_publisher_share"] == round(1 / 9, 4)


def test_the_unknown_independence_share_escalates_rather_than_being_absorbed(store, world):
    from newz.domain.enums import EdgeRelation, RiskTier
    from newz.evidence.assess import assess_claim
    from newz.evidence.bases import record_basis
    from newz.evidence.edges import admit_edge

    claim = world.claim("kettleby", "signature")
    with store.write() as connection:
        record_basis(connection, "basis:a", "experiment", "protocol:A", True)
        record_basis(connection, "basis:b", "experiment", "protocol:B", True)
        connection.execute("UPDATE claims SET risk = 'R1' WHERE id = ?", (claim,))
    for index, basis in enumerate(("basis:a", "basis:b")):
        admit_edge(
            store,
            edge_id=f"edge:u{index}",
            assertion_id=world.assertion("kettleby", "effect"),
            claim_id=claim,
            relation=EdgeRelation.SUPPORTS,
            basis_id=basis,
            risk=RiskTier.R1,
        )
    assess_claim(store, claim, "assessment:u1")

    figures = reports.held_below_by_unknown_independence(store)
    assert claim in figures["held_below_by_unknown_independence"]
    assert figures["share"] == 1.0
    assert figures["escalate"]
    assert "design finding" in figures["finding"]


def test_the_daily_report_carries_what_is_withheld_from_the_system(store, world):
    report = reports.daily_report(store, DAY)
    assert set(report) >= {
        "funnel",
        "concentration",
        "shares",
        "unknown_independence",
        "overdue_counterparts",
        "parser_failures",
        "open_violations",
        "system_metrics",
    }
    assert "interest_origination_share" in report["system_metrics"]
    assert "calibration" in report["system_metrics"]


# ---------------------------------------------------------------------------
# The catalog review
# ---------------------------------------------------------------------------


def _slot(index: int, kind: str, topic: str, publisher: str = "") -> catalog_review.ProposedSlot:
    from newz.domain.enums import RetentionPolicy, RiskTier

    role = sorted(catalog_review.SLOT_ROLES[kind], key=lambda r: r.value)[0]
    claimant = role.value in ("claimant", "firsthand_witness")
    return catalog_review.ProposedSlot(
        source_id=f"source:s{index}",
        publisher=publisher or f"publisher:p{index}",
        topic=topic,
        role=role,
        declared_scope="what this source speaks to",
        risk_floor=RiskTier.R1,
        retention_policy=RetentionPolicy.FULL_TEXT,
        observed_mime="text/html",
        full_text_capable=True,
        retention_rights="terms permit full retention for research",
        counterpart_behaviour="a counterpart task within 72 hours" if claimant else "",
    )


def _valid_slate() -> list[catalog_review.ProposedSlot]:
    topics = list(catalog_review.REQUIRED_TOPICS)
    slots: list[catalog_review.ProposedSlot] = []
    index = 0
    for kind, count in catalog_review.REQUIRED_SLOTS.items():
        for _ in range(count):
            slots.append(_slot(index, kind, topics[index % len(topics)]))
            index += 1
    return slots


def test_a_slate_that_meets_the_specification_is_acceptable():
    result = catalog_review.review(_valid_slate())
    assert result.acceptable, result.problems
    assert result.by_kind() == dict(catalog_review.REQUIRED_SLOTS)


def test_the_review_reports_every_problem_rather_than_the_first():
    slots = _valid_slate()[:18]
    slots[0] = replace(slots[0], retention_rights="", observed_mime="")
    result = catalog_review.review(slots)
    assert not result.acceptable
    assert any("20 reviewed slots" in problem for problem in result.problems)
    assert any("retention rights" in problem for problem in result.problems)
    assert any("MIME not observed" in problem for problem in result.problems)


def test_no_more_than_two_sources_from_one_publisher():
    slots = _valid_slate()
    for index in range(3):
        slots[index] = replace(slots[index], publisher="publisher:same")
    result = catalog_review.review(slots)
    assert any("at most 2 permitted" in problem for problem in result.problems)


def test_every_topic_must_be_covered():
    slots = [replace(slot, topic="uap_and_aerospace_anomalies") for slot in _valid_slate()]
    result = catalog_review.review(slots)
    assert any("topics not covered" in problem for problem in result.problems)


def test_a_claimant_source_must_state_its_counterpart_behaviour(store):
    slots = _valid_slate()
    slots[0] = replace(slots[0], counterpart_behaviour="")
    result = catalog_review.review(slots)
    assert any("counterpart" in problem for problem in result.problems)


# ---------------------------------------------------------------------------
# What is outstanding
# ---------------------------------------------------------------------------


def test_gate_5_counts_and_does_not_judge(store, world):
    status = gate_5_status(store)
    assert status["eligible_dates"] == 0
    assert status["eligible_dates_required"] == 30
    assert status["distinct_retained_reads_required"] == 100
    assert status["operator_approval"] == "not recorded"
    assert "the approval at the end is the operator's" in status["note"]


def test_the_catalog_the_operator_must_supply_is_stated_as_a_checklist():
    outstanding = catalog_review.outstanding_for_operator()
    assert any("claimant or firsthand" in item for item in outstanding)
    assert any("eight initial topics" in item for item in outstanding)
    assert any("retention rights" in item for item in outstanding)
