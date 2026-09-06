"""Investigations, tasks, the brake, leads, and resolvers."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.clock import as_utc, from_ledger, stamp
from newz.control.scheduler import ReservationRefused, reserve
from newz.domain.enums import (
    ClaimKind,
    EvidenceLane,
    FetchRefusal,
    OperationKind,
    ReadLane,
    TaskState,
)
from newz.research import investigations, leads
from newz.research.packets import evidence_packet
from newz.research.resolution import RESOLVERS, record_resolution
from newz.research.tasks import (
    COUNTERPART_BACKLOG_LIMIT,
    TaskTransitionRefused,
    discovery_brake,
    generate_tasks,
    open_counterparts,
    overdue_counterparts,
    transition_task,
)
from tests import world as world_module
from tests.world import add_claim

NOW = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def world(store):
    return world_module.build(store)


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------


def test_an_investigation_states_what_would_close_it_before_any_work(store):
    investigation = investigations.open_investigation(
        store,
        investigation_id="investigation:i1",
        question="Was there an uncorrelated radar return over Coral Ridge?",
        rationale="a claimant account with no primary record behind it",
        exit_conditions=("the registry answers", "the window is exhausted"),
        closing_observation="a registry record for the sector and window, or its documented absence",
        origin="assessment",
        claim_ids=("claim:radar",) if False else (),
    )
    assert investigation.state == "open"
    loaded = investigations.load(store, "investigation:i1")
    assert loaded.exit_conditions == ("the registry answers", "the window is exhausted")


@pytest.mark.parametrize(
    "missing", ["question", "exit_conditions", "closing_observation", "origin"]
)
def test_an_investigation_that_cannot_say_what_would_end_it_is_refused(store, missing):
    kwargs = dict(
        investigation_id="investigation:i1",
        question="a question",
        rationale="a reason",
        exit_conditions=("something",),
        closing_observation="an observation",
        origin="operator",
    )
    kwargs[missing] = "" if missing != "exit_conditions" else ()
    with pytest.raises(ValueError):
        investigations.open_investigation(store, **kwargs)


def test_closing_an_investigation_records_why(store):
    investigations.open_investigation(
        store,
        investigation_id="investigation:i1",
        question="a question",
        rationale="a reason",
        exit_conditions=("something",),
        closing_observation="an observation",
        origin="operator",
    )
    with pytest.raises(ValueError, match="records why"):
        investigations.close_investigation(store, "investigation:i1", "")
    investigations.close_investigation(store, "investigation:i1", "the registry answered")
    assert investigations.load(store, "investigation:i1").state == "closed"
    assert investigations.open_investigations(store) == ()
    with pytest.raises(KeyError):
        investigations.close_investigation(store, "investigation:i1", "again")


def test_an_investigations_question_cannot_be_rewritten(store):
    import sqlite3

    investigations.open_investigation(
        store,
        investigation_id="investigation:i1",
        question="the original question",
        rationale="a reason",
        exit_conditions=("something",),
        closing_observation="an observation",
        origin="operator",
    )
    with pytest.raises(sqlite3.IntegrityError, match="fixed"), store.write() as connection:
        connection.execute("UPDATE investigations SET question = 'a better question'")


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def test_a_task_is_generated_for_every_required_lane(store):
    claim = add_claim(store, "claim:e", "event_or_observation", "something happened", "R1")
    generated = generate_tasks(store, claim, ClaimKind.EVENT_OR_OBSERVATION, NOW)
    lanes = {task.lane for task in generated}
    assert lanes == {
        EvidenceLane.CLAIMANT_ORIGIN,
        EvidenceLane.PRIMARY_RECORD,
        EvidenceLane.INDEPENDENT_COUNTERPART,
        EvidenceLane.SKEPTICAL_ANALYSIS,
    }
    assert all(task.created for task in generated)


def test_the_counterpart_task_is_due_within_seventy_two_hours(store):
    claim = add_claim(store, "claim:e", "event_or_observation", "something happened", "R1")
    generated = {task.lane: task for task in generate_tasks(store, claim, ClaimKind.EVENT_OR_OBSERVATION, NOW)}
    counterpart = generated[EvidenceLane.INDEPENDENT_COUNTERPART]
    # Read back the way the ledger stores it: UTC, whatever zone NOW is in.
    assert from_ledger(counterpart.due) == as_utc(NOW) + timedelta(hours=72)
    other = generated[EvidenceLane.PRIMARY_RECORD]
    assert from_ledger(other.due) > as_utc(NOW) + timedelta(hours=72)


def test_tasks_are_not_generated_twice_for_the_same_question(store):
    claim = add_claim(store, "claim:e", "event_or_observation", "something happened", "R1")
    generate_tasks(store, claim, ClaimKind.EVENT_OR_OBSERVATION, NOW)
    again = generate_tasks(store, claim, ClaimKind.EVENT_OR_OBSERVATION, NOW)
    assert not any(task.created for task in again)
    assert store.one("SELECT COUNT(*) AS n FROM tasks")["n"] == 4


def test_a_satisfied_lane_is_not_reopened(store):
    claim = add_claim(store, "claim:e", "attribution", "someone said something", "R1")
    generated = generate_tasks(store, claim, ClaimKind.ATTRIBUTION, NOW)
    task_id = generated[0].id
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.IN_PROGRESS)
    transition_task(store, task_id, TaskState.SATISFIED)
    assert not any(task.created for task in generate_tasks(store, claim, ClaimKind.ATTRIBUTION, NOW))


def test_the_lifecycle_refuses_a_move_it_does_not_have(store):
    claim = add_claim(store, "claim:e", "attribution", "someone said something", "R1")
    task_id = generate_tasks(store, claim, ClaimKind.ATTRIBUTION, NOW)[0].id
    with pytest.raises(TaskTransitionRefused, match="not a transition"):
        transition_task(store, task_id, TaskState.SATISFIED)
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.IN_PROGRESS)
    transition_task(store, task_id, TaskState.EXHAUSTED)
    with pytest.raises(TaskTransitionRefused, match="already terminal"):
        transition_task(store, task_id, TaskState.SATISFIED)


def test_a_blocked_task_returns_to_scheduled_rather_than_ending(store):
    """A source outage is not a permanent gap in the record."""
    claim = add_claim(store, "claim:e", "attribution", "someone said something", "R1")
    task_id = generate_tasks(store, claim, ClaimKind.ATTRIBUTION, NOW)[0].id
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.BLOCKED, "the source returned 503 all day")
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.IN_PROGRESS)
    assert transition_task(store, task_id, TaskState.SATISFIED) is TaskState.SATISFIED


def test_a_terminal_incomplete_state_must_say_why(store):
    claim = add_claim(store, "claim:e", "attribution", "someone said something", "R1")
    task_id = generate_tasks(store, claim, ClaimKind.ATTRIBUTION, NOW)[0].id
    transition_task(store, task_id, TaskState.SCHEDULED)
    with pytest.raises(TaskTransitionRefused, match="records why"):
        transition_task(store, task_id, TaskState.CANCELLED)
    transition_task(store, task_id, TaskState.CANCELLED, "the operator closed the investigation")
    assert store.one("SELECT state_reason FROM tasks WHERE id = ?", task_id)["state_reason"]


# ---------------------------------------------------------------------------
# The discovery brake
# ---------------------------------------------------------------------------


def _counterparts(store, count: int, due: datetime = NOW + timedelta(days=3), start: int = 0) -> None:
    with store.write() as connection:
        for index in range(start, start + count):
            claim_id = f"claim:brake{index}"
            connection.execute(
                "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
                "withdrawn, recorded_at) VALUES (?, 'event_or_observation', 'a claim', 'R1', "
                "NULL, NULL, 0, datetime('now'))",
                (claim_id,),
            )
            connection.execute(
                "INSERT INTO tasks (id, claim_id, lane, state, owner, reason, due, retry_budget, "
                "state_reason, recorded_at) VALUES (?, ?, ?, 'open', 'w', 'r', ?, 0, '', "
                "datetime('now'))",
                (
                    f"task:brake{index}",
                    claim_id,
                    EvidenceLane.INDEPENDENT_COUNTERPART.value,
                    stamp(due),
                ),
            )


def test_the_brake_is_off_when_counterparts_are_current(store):
    _counterparts(store, 5)
    brake = discovery_brake(store, NOW)
    assert not brake.engaged
    assert brake.open_counterparts == 5


def test_the_brake_engages_above_the_counterpart_backlog(store):
    _counterparts(store, COUNTERPART_BACKLOG_LIMIT)
    assert not discovery_brake(store, NOW).engaged
    # One more is one too many: the limit is what may be open, not what may be added.
    _counterparts(store, 1, start=COUNTERPART_BACKLOG_LIMIT)
    brake = discovery_brake(store, NOW)
    assert brake.engaged
    assert "exceeds 12" in brake.reason


def test_one_overdue_counterpart_engages_the_brake_on_its_own(store):
    """A backlog says verification is behind; an overdue counterpart says one
    claim was left half-investigated, which is worse."""
    _counterparts(store, 1, due=NOW - timedelta(hours=1))
    brake = discovery_brake(store, NOW)
    assert brake.engaged
    assert "overdue" in brake.reason
    assert overdue_counterparts(store, NOW) == ("task:brake0",)


def test_a_satisfied_counterpart_stops_counting_against_the_brake(store):
    _counterparts(store, 1, due=NOW - timedelta(hours=1))
    transition_task(store, "task:brake0", TaskState.SCHEDULED)
    transition_task(store, "task:brake0", TaskState.IN_PROGRESS)
    transition_task(store, "task:brake0", TaskState.SATISFIED)
    assert open_counterparts(store) == ()
    assert not discovery_brake(store, NOW).engaged


def test_the_brake_refuses_a_discovery_reservation_and_not_the_others(catalog):
    def take(lane: ReadLane, index: int, paused: str):
        return reserve(
            catalog,
            operation_id=f"operation:o{index}",
            reservation_id=f"reservation:r{index}",
            kind=OperationKind.FETCH,
            lane=lane,
            source_revision_id="srcrev:harbour-uap-1",
            epoch_id="epoch:1",
            policy_version="1.0.0",
            intent="read",
            idempotency_key=f"key{index}",
            local_day="2026-09-05",
            discovery_paused=paused,
        )

    with pytest.raises(ReservationRefused) as raised:
        take(ReadLane.DISCOVERY, 1, "2 counterpart task(s) overdue")
    assert raised.value.refusal is FetchRefusal.DISCOVERY_PAUSED

    # Verification and correction are untouched: the brake stops opening new
    # claims, not closing the ones already open.
    assert take(ReadLane.VERIFICATION, 2, "2 counterpart task(s) overdue")
    assert take(ReadLane.CORRECTION, 3, "2 counterpart task(s) overdue")


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------


def test_a_directed_search_produces_leads_and_nothing_else(store):
    leads.register_adapter(
        "test_adapter",
        lambda question, lane: (
            ("https://registry.example/search?q=coral", "the registry indexes this sector"),
            ("https://harbour.example/document", "the originating publication"),
        ),
    )
    claim = add_claim(store, "claim:e", "event_or_observation", "something happened", "R1")
    produced = leads.propose_leads(
        store,
        adapter="test_adapter",
        claim_id=claim,
        task_id=None,
        question="coral ridge",
        lane="primary_record",
        id_prefix="lead:l",
    )
    assert len(produced) == 2
    assert leads.unconsumed(store, claim) == produced
    # Nothing else moved: a lead is a place to look.
    for table in ("assertions", "edge_events", "assessments", "bases"):
        assert store.one(f"SELECT COUNT(*) AS n FROM {table}")["n"] == 0


def test_a_lead_the_fetcher_would_refuse_is_not_recorded(store):
    leads.register_adapter(
        "hostile_adapter",
        lambda question, lane: (
            ("file:///etc/passwd", "a local file"),
            ("https://user:pw@example.org/", "credentials in the url"),
            ("https://registry.example/ok", "a real place"),
        ),
    )
    claim = add_claim(store, "claim:e", "event_or_observation", "something happened", "R1")
    produced = leads.propose_leads(
        store,
        adapter="hostile_adapter",
        claim_id=claim,
        task_id=None,
        question="q",
        lane="primary_record",
        id_prefix="lead:h",
    )
    assert [lead.url for lead in produced] == ["https://registry.example/ok"]


def test_a_lead_that_names_a_known_source_carries_its_revision(store, world):
    leads.register_adapter(
        "known", lambda question, lane: (("https://harbour.example/document", "known source"),)
    )
    claim = add_claim(store, "claim:e", "event_or_observation", "something happened", "R1")
    produced = leads.propose_leads(
        store,
        adapter="known",
        claim_id=claim,
        task_id=None,
        question="q",
        lane="claimant_origin",
        id_prefix="lead:k",
    )
    assert produced[0].source_revision_id == "srcrev:harbour-1"


def test_an_unknown_adapter_is_refused(store):
    with pytest.raises(KeyError):
        leads.propose_leads(
            store,
            adapter="nothing_registered_here",
            claim_id=None,
            task_id=None,
            question="q",
            lane="primary_record",
            id_prefix="lead:x",
        )


# ---------------------------------------------------------------------------
# Resolvers
# ---------------------------------------------------------------------------


def test_every_resolver_class_the_plan_names_exists():
    assert set(RESOLVERS) == {
        "competent_registry",
        "docket",
        "publication_status",
        "retraction_notice",
        "replication_record",
        "forecast_resolver",
    }


def test_a_resolver_that_found_nothing_must_say_what_it_looked_for(store):
    claim = add_claim(store, "claim:e", "forecast", "it will happen", "R1")
    task_id = generate_tasks(store, claim, ClaimKind.FORECAST, NOW)[0].id
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.IN_PROGRESS)

    for sought, searched, window in (
        ("", "", ""),
        ("a record", "", ""),
        ("a record", "a repository", ""),  # a search with no window has no scope in time
    ):
        with pytest.raises(ValueError, match="records what was sought"):
            record_resolution(
                store,
                attempt_id="attempt:a1",
                task_id=task_id,
                claim_id=claim,
                resolver="forecast_resolver",
                outcome=TaskState.EXHAUSTED,
                detail="nothing found",
                sought=sought,
                searched=searched,
                time_window=window,
            )


def test_an_unreachable_resolver_is_recorded_as_competent_and_empty(store):
    claim = add_claim(store, "claim:e", "forecast", "it will happen", "R1")
    task_id = generate_tasks(store, claim, ClaimKind.FORECAST, NOW)[0].id
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.IN_PROGRESS)

    resolution = record_resolution(
        store,
        attempt_id="attempt:a1",
        task_id=task_id,
        claim_id=claim,
        resolver="forecast_resolver",
        outcome=TaskState.UNREACHABLE,
        detail="no authority publishes this window",
        sought="a published sector window",
        searched="the national registry disclosure log",
        time_window="2026-01-01/2026-12-01",
    )
    assert resolution.outcome is TaskState.UNREACHABLE
    row = store.one("SELECT * FROM tasks WHERE id = ?", task_id)
    assert row["state"] == "unreachable"
    assert row["expected_record"] == "a published sector window"
    assert row["searched_scope"] == "the national registry disclosure log"


def test_a_resolution_attempt_cannot_be_rewritten(store):
    import sqlite3

    claim = add_claim(store, "claim:e", "forecast", "it will happen", "R1")
    task_id = generate_tasks(store, claim, ClaimKind.FORECAST, NOW)[0].id
    transition_task(store, task_id, TaskState.SCHEDULED)
    transition_task(store, task_id, TaskState.IN_PROGRESS)
    record_resolution(
        store,
        attempt_id="attempt:a1",
        task_id=task_id,
        claim_id=claim,
        resolver="docket",
        outcome=TaskState.SATISFIED,
        detail="the docket answered",
        sought="a final judgment",
        searched="the district docket",
    )
    with pytest.raises(sqlite3.IntegrityError, match="immutable"), store.write() as connection:
        connection.execute("UPDATE resolution_attempts SET outcome = 'exhausted'")


# ---------------------------------------------------------------------------
# Evidence packets
# ---------------------------------------------------------------------------


def test_a_packet_names_the_missing_lanes_and_what_would_change_the_state(store):
    claim = add_claim(store, "claim:e", "event_or_observation", "something happened", "R1")
    generate_tasks(store, claim, ClaimKind.EVENT_OR_OBSERVATION, NOW)
    packet = evidence_packet(store, claim)
    assert packet.state == "unassessed"
    assert set(packet.missing_lanes) == {
        "claimant_origin",
        "independent_counterpart",
        "primary_record",
        "skeptical_analysis",
    }
    assert packet.what_would_change_it == "an answer from the claimant_origin lane"
    assert packet.support.edges == 0


# ---------------------------------------------------------------------------
# Expiry and risk
# ---------------------------------------------------------------------------


def test_expiry_is_offered_rather_than_applied(store):
    """A sweep that expired tasks on time would clear the counterpart backlog by
    declaring it over, and the brake would never engage."""
    from newz.research.tasks import expirable

    _counterparts(store, 1, due=NOW - timedelta(hours=1))
    assert expirable(store, NOW) == ("task:brake0",)
    # Still live, still braking: nothing expired itself.
    assert discovery_brake(store, NOW).engaged

    transition_task(store, "task:brake0", TaskState.EXPIRED, "the window closed unanswered")
    assert expirable(store, NOW) == ()
    assert not discovery_brake(store, NOW).engaged
    assert store.one("SELECT state FROM tasks WHERE id = 'task:brake0'")["state"] == "expired"


def test_an_expired_lane_never_produces_indeterminate(store):
    """It is terminal-incomplete: the search did not happen."""
    from newz.domain.enums import AssessmentState
    from newz.evidence.assess import assess_claim

    claim = add_claim(store, "claim:exp", "attribution", "someone said something", "R1")
    task_id = generate_tasks(store, claim, ClaimKind.ATTRIBUTION, NOW)[0].id
    transition_task(store, task_id, TaskState.EXPIRED, "nobody picked it up")
    result = assess_claim(store, claim, "assessment:exp")
    assert result.state is AssessmentState.REPORTED
    assert result.blocked_lanes[0][1] is TaskState.EXPIRED


def test_risk_may_be_raised_by_policy_and_lowered_only_by_an_operator(store):
    import json as _json

    from newz.domain.enums import RiskTier
    from newz.domain.records import OperatorAction
    from newz.evidence.claims import reclassify_claim_risk
    from newz.policy.risk import RiskLoweringRefused

    claim = add_claim(store, "claim:r", "identity_or_wrongdoing_allegation", "an allegation", "R1")
    assert reclassify_claim_risk(store, claim, RiskTier.R3) is RiskTier.R3

    with pytest.raises(RiskLoweringRefused):
        reclassify_claim_risk(store, claim, RiskTier.R1)

    reasoned = OperatorAction(
        id="action:1",
        actor="operator:dean",
        at="2026-09-05T12:00:00Z",
        action="reclassify",
        reason="the named party is a company, not a living person",
        target_preimage="R3",
        result="R1",
    )
    assert reclassify_claim_risk(store, claim, RiskTier.R1, operator_action=reasoned) is RiskTier.R1

    events = [
        _json.loads(row["payload"])
        for row in store.query("SELECT payload FROM outbox WHERE kind = 'risk_changed' ORDER BY id")
    ]
    assert events == [{"from": "R1", "to": "R3"}, {"from": "R3", "to": "R1"}]
    actions = {
        row["actor"]
        for row in store.query("SELECT actor FROM audit_events WHERE action = 'reclassify_claim_risk'")
    }
    assert actions == {"system", "operator:dean"}


def test_an_audit_id_identifies_an_occurrence_not_a_subject(store):
    """The same action on the same target happens more than once. It has done so
    twice in this codebase's history and collided both times."""
    from newz.control.audit import record as audit_record

    with store.write() as connection:
        for index in range(3):
            audit_record(
                connection,
                actor="operator:dean",
                action="reclassify_claim_risk",
                target="claim:same",
                reason=f"occurrence {index}",
                preimage="R1",
                result="R3",
            )
    rows = store.query(
        "SELECT id, reason FROM audit_events WHERE target = 'claim:same' ORDER BY id"
    )
    assert len(rows) == 3
    assert len({row["id"] for row in rows}) == 3
    assert [row["reason"] for row in rows] == ["occurrence 0", "occurrence 1", "occurrence 2"]
