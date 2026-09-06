"""The publisher concentration cap, enforced at reservation.

`SPEC.md` section 5.1 says three things that pull against each other, and each
one gets a test: the cap binds before the read rather than after it, the refusal
is written down rather than merely raised, and the cap never reaches evidence.
"""

from __future__ import annotations

import pytest

from newz.control.budget import DailyBudget
from newz.control.concentration import (
    WINDOW_DAYS,
    Share,
    cap_for,
    grant_exception,
    record_refusal,
    refusals,
    report,
    share_if_retained,
    would_exceed,
)
from newz.control.scheduler import ReservationRefused, reserve
from newz.domain.enums import FetchRefusal, OperationKind, ReadLane
from newz.evidence.assess import assess_claim, current_assessment
from newz.pilot.modes import DeploymentMode, current_mode, transition
from tests import world as world_module

#: The same day the world fixture reserves under, which is today: see
#: `tests/world.py`.
DAY = world_module.DAY
FUTURE = "2026-12-31"


@pytest.fixture
def world(store):
    return world_module.build(store)


def _to_pilot(store) -> None:
    transition(
        store,
        transition_id="transition:t1",
        to=DeploymentMode.SHADOW,
        actor="operator:dean",
        reason="the fixtures pass",
    )
    transition(
        store,
        transition_id="transition:t2",
        to=DeploymentMode.PILOT,
        actor="operator:dean",
        reason="shadow exited cleanly",
    )


def _add_sightings(store, source_revision_id: str, count: int, prefix: str) -> None:
    """More reads of the same source, sharing one body.

    A sighting is one observation of a body at a source and a time; SPEC's own
    definition allows duplicate bodies to share storage while never sharing
    sightings, so this is the shape a repeatedly-read source actually takes.
    """
    row = store.one(
        "SELECT response_id, artifact_id FROM sightings WHERE source_revision_id = ? LIMIT 1",
        source_revision_id,
    )
    assert row is not None, f"{source_revision_id} was never read"
    with store.write() as connection:
        for index in range(count):
            connection.execute(
                "INSERT INTO sightings (id, response_id, source_revision_id, artifact_id, "
                "observed_at) VALUES (?, ?, ?, ?, datetime('now'))",
                (
                    f"sighting:{prefix}-{index}",
                    row["response_id"],
                    source_revision_id,
                    row["artifact_id"],
                ),
            )


def _reserve(store, key: str, revision: str):
    return reserve(
        store,
        operation_id=f"operation:{key}",
        reservation_id=f"reservation:{key}",
        kind=OperationKind.FETCH,
        lane=ReadLane.VERIFICATION,
        source_revision_id=revision,
        epoch_id="epoch:1",
        policy_version="1.0.0",
        intent="read it again",
        idempotency_key=f"{DAY}:{key}",
        local_day=DAY,
        budget=DailyBudget(),
    )


# ---------------------------------------------------------------------------
# The tiers
# ---------------------------------------------------------------------------


def test_the_cap_tightens_from_pilot_to_production():
    assert cap_for(DeploymentMode.PILOT) == 0.20
    assert cap_for(DeploymentMode.PRODUCTION) == 0.10
    assert cap_for(DeploymentMode.SHADOW) == 0.20, "shadow reads live sources"
    assert cap_for(DeploymentMode.FIXTURE) is None
    assert cap_for(DeploymentMode.LOCKDOWN) is None


# ---------------------------------------------------------------------------
# A cap that cannot be satisfied is not a cap
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("total", [0, 1, 2, 3])
def test_the_cap_does_not_bind_before_it_could_be_satisfied(total):
    """The first retained read is 100% of a 30-day window, the second 50%."""
    share = Share("publisher:p", "P", retained=total, total=total, cap=0.20)
    assert share.prospective > share.cap
    assert not share.binds, "a cap enforced here would refuse the reads that satisfy it"
    assert not share.exceeded


def test_the_floor_is_the_point_where_the_cap_becomes_reachable():
    assert Share("p", "P", retained=4, total=4, cap=0.20).binds
    assert Share("p", "P", retained=0, total=4, cap=0.20).prospective == pytest.approx(0.2)
    # At 10% it takes twice as many reads before the cap means anything.
    assert not Share("p", "P", retained=4, total=8, cap=0.10).binds
    assert Share("p", "P", retained=4, total=9, cap=0.10).binds


def test_a_cold_start_refuses_nothing(store, world):
    """Nine reads across nine publishers: nobody is near a fifth of them."""
    _to_pilot(store)
    for ingested in world.sources.values():
        assert would_exceed(store, ingested.revision.id, DAY) == ""


def test_the_cap_binds_once_the_window_can_hold_it(store, world):
    _to_pilot(store)
    revision = world.sources["kettleby"].revision.id
    _add_sightings(store, world.sources["ardenne"].revision.id, 20, "filler")

    share = share_if_retained(store, revision, DAY)
    assert share.binds
    # kettleby has one read of its own; ardenne's twenty are somebody else's.
    assert share.prospective == pytest.approx(2 / 30, abs=0.001)
    assert not share.exceeded


# ---------------------------------------------------------------------------
# Enforced before the read, not after it
# ---------------------------------------------------------------------------


def test_a_read_that_would_breach_the_cap_is_refused_a_reservation(store, world):
    _to_pilot(store)
    revision = world.sources["kettleby"].revision.id
    _add_sightings(store, revision, 10, "kettleby-extra")

    share = share_if_retained(store, revision, DAY)
    assert share.exceeded, share.as_record()
    with pytest.raises(ReservationRefused) as raised:
        _reserve(store, "over", revision)
    assert raised.value.refusal is FetchRefusal.PUBLISHER_CONCENTRATION

    # And the operation was never created: refused before the read, not after.
    assert store.one("SELECT 1 FROM operations WHERE id = 'operation:over'") is None


def test_the_refusal_names_the_publisher_the_window_and_the_figure(store, world):
    _to_pilot(store)
    revision = world.sources["kettleby"].revision.id
    _add_sightings(store, revision, 10, "kettleby-extra")
    with pytest.raises(ReservationRefused):
        _reserve(store, "over", revision)

    recorded = refusals(store, DAY)
    assert len(recorded) == 1
    detail = recorded[0]["detail"]
    assert recorded[0]["refusal"] == FetchRefusal.PUBLISHER_CONCENTRATION.value
    assert "Kettleby" in detail or store.one(
        "SELECT name FROM publishers WHERE id = 'publisher:kettleby'"
    )["name"] in detail
    assert f"{WINDOW_DAYS} days" in detail
    assert "%" in detail


def test_a_publisher_under_the_cap_still_reads(store, world):
    _to_pilot(store)
    _add_sightings(store, world.sources["ardenne"].revision.id, 20, "filler")
    operation = _reserve(store, "fine", world.sources["kettleby"].revision.id)
    assert operation.id == "operation:fine"


# ---------------------------------------------------------------------------
# Every reservation refusal is written down, not only this one
# ---------------------------------------------------------------------------


def test_a_refused_reservation_is_recorded_whatever_refused_it(store, world):
    with pytest.raises(ReservationRefused):
        _reserve(store, "absent", "srcrev:not-in-the-diet")
    recorded = refusals(store, DAY)
    assert [r["refusal"] for r in recorded] == [FetchRefusal.HOST_NOT_IN_CATALOG.value]


def test_a_budget_refusal_survives_the_transaction_it_refused(store, world):
    """It is decided under the write lock; recording it there would roll back."""
    revision = world.sources["kettleby"].revision.id
    for index in range(20):
        try:
            _reserve(store, f"v{index}", revision)
        except ReservationRefused as refused:
            assert refused.refusal is FetchRefusal.BUDGET_EXHAUSTED
            break
    else:  # pragma: no cover - the day is ten reads
        pytest.fail("the day never ran out")
    assert [r["refusal"] for r in refusals(store, DAY)] == [
        FetchRefusal.BUDGET_EXHAUSTED.value
    ]


def test_a_recorded_refusal_cannot_be_edited(store, world):
    record_refusal(
        store,
        idempotency_key=f"{DAY}:x",
        source_revision_id=world.sources["kettleby"].revision.id,
        lane=ReadLane.VERIFICATION.value,
        refusal=FetchRefusal.RATE_LIMITED.value,
        detail="the host asked us to wait",
        local_day=DAY,
    )
    with pytest.raises(Exception, match="record another"), store.write() as connection:
        connection.execute("UPDATE reservation_refusals SET detail = 'never mind'")


# ---------------------------------------------------------------------------
# The scoped exception
# ---------------------------------------------------------------------------


def test_a_scoped_exception_lifts_the_cap_for_one_publisher(store, world):
    _to_pilot(store)
    revision = world.sources["kettleby"].revision.id
    _add_sightings(store, revision, 10, "kettleby-extra")
    assert would_exceed(store, revision, DAY)

    grant_exception(
        store,
        exception_id="exception:e1",
        publisher_id="publisher:kettleby",
        cap=0.60,
        granted_by="operator:dean",
        reason="the retraction notice is only carried here",
        expires_at=FUTURE,
    )
    assert would_exceed(store, revision, DAY) == ""
    assert share_if_retained(store, revision, DAY).exception_id == "exception:e1"
    # And it does not travel: another publisher is unaffected by it.
    other = share_if_retained(store, world.sources["ardenne"].revision.id, DAY)
    assert other.cap == 0.20
    assert not other.exception_id


def test_an_expired_exception_does_not_lift_anything(store, world):
    _to_pilot(store)
    revision = world.sources["kettleby"].revision.id
    _add_sightings(store, revision, 10, "kettleby-extra")
    grant_exception(
        store,
        exception_id="exception:e1",
        publisher_id="publisher:kettleby",
        cap=0.60,
        granted_by="operator:dean",
        reason="a reason that had a deadline",
        expires_at="2026-09-04",
    )
    assert would_exceed(store, revision, DAY)


def test_an_exception_needs_an_operator_a_reason_and_an_end(store, world):
    for missing in ("granted_by", "reason", "expires_at"):
        fields = {
            "granted_by": "operator:dean",
            "reason": "because",
            "expires_at": FUTURE,
            **{missing: ""},
        }
        with pytest.raises(ValueError, match="operator, a reason and an expiry"):
            grant_exception(
                store,
                exception_id=f"exception:{missing}",
                publisher_id="publisher:kettleby",
                cap=0.6,
                **fields,
            )


def test_an_exception_is_a_dated_act_and_cannot_be_rewritten(store, world):
    grant_exception(
        store,
        exception_id="exception:e1",
        publisher_id="publisher:kettleby",
        cap=0.60,
        granted_by="operator:dean",
        reason="stated once",
        expires_at=FUTURE,
    )
    with pytest.raises(Exception, match="grant another"), store.write() as connection:
        connection.execute("UPDATE concentration_exceptions SET cap = 0.9")


# ---------------------------------------------------------------------------
# The cap governs acquisition and nothing else
# ---------------------------------------------------------------------------


def test_an_exceeded_cap_never_touches_retained_evidence(store, world):
    """`TRUE_NORTH.md`: a diet property may not reach a conclusion."""
    _to_pilot(store)
    revision = world.sources["kettleby"].revision.id
    claim = world.claim("kettleby", "signature")
    assess_claim(store, claim, "assessment:a1")
    before = current_assessment(store, claim)
    artifacts = store.one("SELECT COUNT(*) AS n FROM artifacts")["n"]
    live_edges = store.one("SELECT COUNT(*) AS n FROM edge_events WHERE live = 1")["n"]

    _add_sightings(store, revision, 10, "kettleby-extra")
    with pytest.raises(ReservationRefused):
        _reserve(store, "over", revision)

    assert store.one("SELECT COUNT(*) AS n FROM artifacts")["n"] == artifacts
    assert store.one("SELECT COUNT(*) AS n FROM edge_events WHERE live = 1")["n"] == live_edges
    assert current_assessment(store, claim) == before


def test_fixture_mode_has_no_share_to_exceed(store, world):
    assert current_mode(store) is DeploymentMode.FIXTURE
    revision = world.sources["kettleby"].revision.id
    _add_sightings(store, revision, 30, "kettleby-extra")
    assert would_exceed(store, revision, DAY) == ""
    assert share_if_retained(store, revision, DAY).cap is None


# ---------------------------------------------------------------------------
# The operator's view
# ---------------------------------------------------------------------------


def test_the_report_shows_every_enabled_publisher_against_the_cap(store, world):
    _to_pilot(store)
    _add_sightings(store, world.sources["kettleby"].revision.id, 10, "kettleby-extra")
    with pytest.raises(ReservationRefused):
        _reserve(store, "over", world.sources["kettleby"].revision.id)

    figures = report(store, DAY)
    assert figures["mode"] == DeploymentMode.PILOT.value
    assert figures["cap"] == 0.20
    assert figures["window_days"] == WINDOW_DAYS
    assert figures["binding"]
    assert any(entry["exceeded"] for entry in figures["publishers"].values())
    assert len(figures["refusals_today"]) == 1
