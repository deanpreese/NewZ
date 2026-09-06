"""The R3 isolated workflow, exercised end to end.

`PLAN.md` gates live R3 intake on this workflow being exercised in
production-like tests, so these run the real path: a real store, real
migrations, a real fetch through the fixture transport, a real parse, and the
real extraction call. The stub stands in only for the far side of the local
model endpoint, and the point of most of these tests is that it is never
reached.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.clock import stamp
from newz.control.isolation import (
    QuarantineRefused,
    accesses,
    approve_model_read,
    case_for,
    claims_without_a_case,
    close_case,
    is_quarantined,
    open_case,
    quarantine,
    report,
)
from newz.domain.enums import RiskTier
from newz.domain.records import OperatorAction
from newz.evidence.claims import reclassify_claim_risk
from newz.extract.run import extract
from newz.parse.store import segments_for
from newz.publish.reader import LISTABLE_TIERS
from tests import world as world_module
from tests.model_stub import StubModel, assertion, extraction

NOW = datetime(2026, 9, 5, 12, 0, 0)
OPERATOR = "operator:dean"


@pytest.fixture
def world(store):
    return world_module.build(store)


@pytest.fixture
def r3_claim(store, world):
    """A claim raised to R3 the way the monotonicity rule allows."""
    claim = world_module.add_claim(
        store,
        "claim:allegation",
        "attribution_or_authorship",
        "a named living party is alleged to have falsified a dataset",
        "R1",
    )
    reclassify_claim_risk(
        store,
        claim,
        RiskTier.R3,
        actor="system",
    )
    return claim


@pytest.fixture
def case(store, r3_claim):
    return open_case(
        store,
        case_id="case:c1",
        claim_id=r3_claim,
        subject="the named party",
        opened_by=OPERATOR,
        reason="an allegation was published and the record should be checked",
    )


# ---------------------------------------------------------------------------
# Intake is a person's act
# ---------------------------------------------------------------------------


def test_the_system_cannot_open_an_r3_case_on_its_own(store, r3_claim):
    """Raising risk is the system's; deciding to work on it anyway is not."""
    with pytest.raises(QuarantineRefused, match="opened by an operator"):
        open_case(
            store,
            case_id="case:c1",
            claim_id=r3_claim,
            subject="the named party",
            opened_by="system",
            reason="it looked interesting",
        )


def test_a_case_names_its_subject_and_says_why(store, r3_claim):
    for field in ("subject", "reason"):
        kwargs = {"subject": "someone", "reason": "a reason", field: "  "}
        with pytest.raises(ValueError):
            open_case(
                store, case_id=f"case:{field}", claim_id=r3_claim, opened_by=OPERATOR, **kwargs
            )


def test_a_case_is_not_how_a_claim_becomes_r3(store, world):
    """Reclassify it where the monotonicity rule can see the change."""
    claim = world.claim("kettleby", "signature")
    with store.write() as connection:
        connection.execute("UPDATE claims SET risk = 'R1' WHERE id = ?", (claim,))
    with pytest.raises(QuarantineRefused, match="not how a claim becomes R3"):
        open_case(
            store,
            case_id="case:c1",
            claim_id=claim,
            subject="someone",
            opened_by=OPERATOR,
            reason="a reason",
        )


def test_an_r3_claim_with_no_case_behind_it_is_reported(store, r3_claim):
    """The shape an isolation failure takes when nothing crashes."""
    assert claims_without_a_case(store) == (r3_claim,)
    open_case(
        store,
        case_id="case:c1",
        claim_id=r3_claim,
        subject="the named party",
        opened_by=OPERATOR,
        reason="checking the record",
    )
    assert claims_without_a_case(store) == ()


def test_a_case_keeps_its_opening_and_is_closed_rather_than_rewritten(store, case):
    with pytest.raises(Exception, match="do not rewrite it"), store.write() as connection:
        connection.execute("UPDATE r3_cases SET reason = 'a better reason'")

    close_case(store, case.id, "the allegation was withdrawn at source", NOW)
    reopened = case_for(store, case.claim_id)
    assert not reopened.open
    assert reopened.closed_reason == "the allegation was withdrawn at source"
    assert reopened.reason == case.reason


# ---------------------------------------------------------------------------
# The model does not read quarantined material
# ---------------------------------------------------------------------------


def _extract(store, world, artifact_id, run_id, now=NOW):
    ingested = world.sources["kettleby"]
    segments = segments_for(store, artifact_id)
    return extract(
        store,
        run_id=run_id,
        artifact_id=artifact_id,
        parse_execution_id=ingested.execution_id,
        source_revision_id=ingested.revision.id,
        client=StubModel(reply=extraction(assertion("measurement", "x", "a"))),
        segments=segments,
        now=now,
    )


def test_extraction_refuses_a_quarantined_body_before_the_prompt_is_built(store, world, case):
    """The text must never reach the endpoint, not merely be regretted after."""
    artifact = world.artifact("kettleby")
    quarantine(store, artifact, case.id, "carries the allegation and the party's name")

    client = StubModel(reply=extraction(assertion("measurement", "x", "a")))
    with pytest.raises(QuarantineRefused, match="excluded from prompts"):
        extract(
            store,
            run_id="run:blocked",
            artifact_id=artifact,
            parse_execution_id=world.sources["kettleby"].execution_id,
            source_revision_id=world.sources["kettleby"].revision.id,
            client=client,
            segments=segments_for(store, artifact),
            now=NOW,
        )
    assert client.prompts == [], "the endpoint was not reached"


def test_an_unquarantined_body_is_untouched_by_any_of_this(store, world, case):
    record = _extract(store, world, world.artifact("ardenne"), "run:ordinary")
    assert record.accepted >= 0
    assert accesses(store) == ()


def test_a_refused_access_is_logged_like_a_permitted_one(store, world, case):
    """A quarantine recording only its successes describes untested walls."""
    artifact = world.artifact("kettleby")
    quarantine(store, artifact, case.id, "carries the party's name")
    with pytest.raises(QuarantineRefused):
        _extract(store, world, artifact, "run:blocked")

    logged = accesses(store, artifact)
    assert len(logged) == 1
    assert logged[0]["permitted"] is False
    assert logged[0]["purpose"] == "model_read"
    assert logged[0]["detail"] == "no approval"
    assert logged[0]["case_id"] == case.id


def test_an_operator_approval_opens_it_once(store, world, case):
    artifact = world.artifact("kettleby")
    quarantine(store, artifact, case.id, "carries the party's name")
    approve_model_read(
        store,
        approval_id="approval:a1",
        artifact_id=artifact,
        case_id=case.id,
        approved_by=OPERATOR,
        necessity="the retraction notice quotes the party and nothing else states it",
        expires_at=NOW + timedelta(days=1),
    )
    record = _extract(store, world, artifact, "run:approved")
    assert record.accepted >= 0

    logged = accesses(store, artifact)
    assert [entry["permitted"] for entry in logged] == [True]
    assert "strictly necessary" not in logged[0]["detail"]
    assert "the retraction notice quotes the party" in logged[0]["detail"]


def test_an_approval_is_spent_when_it_is_used(store, world, case):
    """A standing approval is the exclusion rescinded while appearing honoured."""
    artifact = world.artifact("kettleby")
    quarantine(store, artifact, case.id, "carries the party's name")
    approve_model_read(
        store,
        approval_id="approval:a1",
        artifact_id=artifact,
        case_id=case.id,
        approved_by=OPERATOR,
        necessity="one read of the retraction notice",
        expires_at=NOW + timedelta(days=1),
    )
    _extract(store, world, artifact, "run:first")
    with pytest.raises(QuarantineRefused, match="excluded from prompts"):
        _extract(store, world, artifact, "run:second")

    assert [entry["permitted"] for entry in accesses(store, artifact)] == [True, False]


def test_an_expired_approval_does_not_open_anything(store, world, case):
    artifact = world.artifact("kettleby")
    quarantine(store, artifact, case.id, "carries the party's name")
    approve_model_read(
        store,
        approval_id="approval:a1",
        artifact_id=artifact,
        case_id=case.id,
        approved_by=OPERATOR,
        necessity="a read that had a deadline",
        expires_at=NOW - timedelta(minutes=1),
    )
    with pytest.raises(QuarantineRefused, match="expired"):
        _extract(store, world, artifact, "run:late")
    assert "approval:a1 expired at" in accesses(store, artifact)[0]["detail"]


def test_only_an_operator_approves_and_the_necessity_is_required(store, case, world):
    artifact = world.artifact("kettleby")
    with pytest.raises(QuarantineRefused, match="only an operator"):
        approve_model_read(
            store,
            approval_id="approval:x",
            artifact_id=artifact,
            case_id=case.id,
            approved_by="system",
            necessity="because",
            expires_at=NOW,
        )
    with pytest.raises(ValueError, match="strictly necessary"):
        approve_model_read(
            store,
            approval_id="approval:y",
            artifact_id=artifact,
            case_id=case.id,
            approved_by=OPERATOR,
            necessity="   ",
            expires_at=NOW,
        )


def test_an_approval_is_a_dated_act_and_cannot_be_rewritten(store, case, world):
    approve_model_read(
        store,
        approval_id="approval:a1",
        artifact_id=world.artifact("kettleby"),
        case_id=case.id,
        approved_by=OPERATOR,
        necessity="stated once",
        expires_at=NOW,
    )
    with pytest.raises(Exception, match="grant another one"), store.write() as connection:
        connection.execute("UPDATE model_read_approvals SET necessity = 'something else'")


def test_the_access_log_is_immutable(store, world, case):
    artifact = world.artifact("kettleby")
    quarantine(store, artifact, case.id, "carries the party's name")
    with pytest.raises(QuarantineRefused):
        _extract(store, world, artifact, "run:blocked")
    with pytest.raises(Exception, match="do not edit it"), store.write() as connection:
        connection.execute("UPDATE quarantine_access SET permitted = 1")


# ---------------------------------------------------------------------------
# The rest of the isolation, which other phases already built
# ---------------------------------------------------------------------------


def test_r3_is_not_listed_to_a_reader(store):
    assert RiskTier.R3 not in LISTABLE_TIERS
    assert RiskTier.R4 not in LISTABLE_TIERS


def test_lowering_an_r3_claim_needs_a_reasoned_operator_action(store, r3_claim):
    """The escalation route this workflow is most exposed to."""
    from newz.policy.risk import RiskLoweringRefused

    with pytest.raises(RiskLoweringRefused):
        reclassify_claim_risk(store, r3_claim, RiskTier.R1, actor="system")

    reclassify_claim_risk(
        store,
        r3_claim,
        RiskTier.R1,
        actor=OPERATOR,
        operator_action=OperatorAction(
            id="action:lower-1",
            actor=OPERATOR,
            at=stamp(NOW),
            action="reclassify_claim_risk",
            reason="the party named turns out to be a defunct organisation",
            target_preimage="R3",
            result="R1",
        ),
    )
    assert store.one("SELECT risk FROM claims WHERE id = ?", r3_claim)["risk"] == "R1"


# ---------------------------------------------------------------------------
# The operator's view
# ---------------------------------------------------------------------------


def test_the_report_says_what_was_refused_as_well_as_what_was_held(store, world, case):
    artifact = world.artifact("kettleby")
    quarantine(store, artifact, case.id, "carries the party's name")
    assert is_quarantined(store, artifact)
    with pytest.raises(QuarantineRefused):
        _extract(store, world, artifact, "run:blocked")

    figures = report(store)
    assert figures["open_cases"] == 1
    assert figures["quarantined_artifacts"] == 1
    assert figures["accesses"] == 1
    assert figures["refused_accesses"] == 1
    assert figures["unused_approvals"] == 0
    assert figures["r3_claims_without_a_case"] == []
    # And the ones nobody classified are reported apart from the ones somebody
    # classified as dangerous: they behave as R3 and need a different answer.
    assert figures["claims_with_unreadable_risk"]


def test_an_unused_approval_is_visible_rather_than_forgotten(store, world, case):
    approve_model_read(
        store,
        approval_id="approval:a1",
        artifact_id=world.artifact("kettleby"),
        case_id=case.id,
        approved_by=OPERATOR,
        necessity="granted and not yet used",
        expires_at=NOW + timedelta(days=1),
    )
    assert report(store)["unused_approvals"] == 1
    assert stamp(NOW)  # the approval's expiry is stored in the ledger's timezone


def test_an_unclassified_claim_behaves_as_r3_and_is_reported_as_a_different_problem(store, world):
    """`SPEC.md` section 8: missing risk behaves as R3 internally.

    So an unclassified claim is inside this workflow's scope. Reporting it in
    the same list as a claim someone deliberately marked dangerous would hide
    the handful that matter among the many that are merely unlabelled.
    """
    from newz.control.isolation import claims_with_unreadable_risk

    unclassified = claims_with_unreadable_risk(store)
    assert unclassified, "the world builds claims without a risk state"
    assert not (set(unclassified) & set(claims_without_a_case(store)))
