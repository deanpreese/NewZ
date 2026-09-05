"""Gate 4: a reader can audit every sentence, and revocation works in its window.

This gate is what earns approve-by-default. Passing it turns local publication
on for R0-R2; failing it leaves publication off. Public reach is a separate
decision and stays disabled here.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.domain.enums import (
    AppraisalDimension,
    EdgeRelation,
    IndependenceJustification,
    RiskTier,
)
from newz.evidence.assess import assess_claim
from newz.evidence.bases import record_basis, record_independence
from newz.evidence.claims import reclassify_claim_risk
from newz.evidence.edges import admit_edge, withdraw_edge
from newz.present.cards import build_card
from newz.publish.appraisal import (
    REVIEW_DEBT_CEILING,
    appraise,
    class_needing_reappraisal,
    class_of,
    record_judgment,
    review_debt,
    sample_for_review,
)
from newz.publish.clearance import (
    LOCAL,
    PUBLIC,
    class_halted,
    clear,
    reach_enabled,
    refusal_conditions,
    set_reach,
)
from newz.publish.publication import (
    CONFIRMED,
    UNCONFIRMED,
    confirm_publication,
    confirm_revocation,
    correct,
    halt_classes_with_overdue_revocations,
    overdue_revocations,
    publish,
    published_count,
    retract,
    revocation_latency_seconds,
    revocation_report,
)
from newz.publish.surface import LocalSurface
from tests import world as world_module

NOW = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def surface(tmp_path):
    return LocalSurface(root=tmp_path / "surface")


@pytest.fixture
def world(store):
    built = world_module.build(store)
    with store.write() as connection:
        record_basis(connection, "basis:proto-4471", "experiment", "protocol:PROTO-4471", True)
        record_basis(connection, "basis:proto-5520", "experiment", "protocol:PROTO-5520", True)
        record_basis(connection, "basis:judgment", "official_record", "docket#44", True)
        record_independence(
            connection,
            "independence:labs",
            "basis:proto-4471",
            "basis:proto-5520",
            IndependenceJustification.DISTINCT_EXPERIMENT,
            evidence="different laboratories",
        )
    return built


def _published_card(store, world, surface, *, risk: str = "R1") -> tuple[str, str, str]:
    """A contested claim, carded, cleared, published and confirmed."""
    claim = world.claim("kettleby", "signature")
    admit_edge(
        store,
        edge_id="edge:sup",
        assertion_id=world.assertion("kettleby", "effect"),
        claim_id=claim,
        relation=EdgeRelation.SUPPORTS,
        basis_id="basis:proto-4471",
        risk=RiskTier(risk),
    )
    admit_edge(
        store,
        edge_id="edge:con",
        assertion_id=world.assertion("ardenne", "no_effect"),
        claim_id=claim,
        relation=EdgeRelation.CONTRADICTS,
        basis_id="basis:proto-5520",
        risk=RiskTier(risk),
    )
    with store.write() as connection:
        connection.execute("UPDATE claims SET risk = ? WHERE id = ?", (risk, claim))
    assess_claim(store, claim, "assessment:a1")
    revision, _ = build_card(store, claim, "card:r1")

    result = clear(store, revision, "clearance:c1", now=NOW.isoformat(timespec="seconds"))
    assert result.granted, result.refusals
    publish(
        store,
        publication_id="publication:p1",
        card_revision_id=revision,
        clearance_id="clearance:c1",
        surface=surface,
    )
    record = confirm_publication(store, "publication:p1", surface)
    assert record.status == CONFIRMED
    return claim, revision, "clearance:c1"


# ---------------------------------------------------------------------------
# A reader can audit every sentence
# ---------------------------------------------------------------------------


def test_a_local_reader_can_audit_every_sentence_on_the_card(store, world, surface):
    claim, revision, _ = _published_card(store, world, surface)
    served = surface.serving(claim)
    card = served["card"]

    assert served["content_hash"] == store.one(
        "SELECT content_hash FROM card_revisions WHERE id = ?", revision
    )["content_hash"]

    for item in card["supporting"] + card["contradicting"] + card["context"]:
        # Each displayed item names the edge, the artifact and the retrieval.
        edge = store.one("SELECT live, admitted FROM edge_events WHERE id = ?", item["edge_id"])
        assert edge["live"] and edge["admitted"]
        assert item["retrieved_from"].startswith("https://")
        assert store.one(
            "SELECT id FROM assertions WHERE artifact_id = ? AND quote = ?",
            item["artifact_id"],
            item["quote"],
        )
    assert card["policy_version"] and card["code_version"]
    assert card["what_would_change_this"]


def test_publication_is_confirmed_from_outside_the_renderer(store, world, surface):
    claim, _revision, _clearance = _published_card(store, world, surface)
    row = store.one("SELECT * FROM publications WHERE id = 'publication:p1'")
    assert row["status"] == CONFIRMED
    assert "local surface" in row["confirmation_source"]

    # If the surface stops serving it, the same check says so.
    surface.page_path(claim).unlink()
    again = confirm_publication(store, "publication:p1", surface)
    assert again.status == UNCONFIRMED
    assert published_count(store) == 0


def test_an_unconfirmed_publication_is_not_counted_as_published(store, world, surface):
    _published_card(store, world, surface)
    assert published_count(store) == 1
    with store.write() as connection:
        connection.execute("UPDATE publications SET status = 'unconfirmed'")
    assert published_count(store) == 0


# ---------------------------------------------------------------------------
# Correction and retraction, inside the window
# ---------------------------------------------------------------------------


def test_a_correction_attaches_to_the_output_and_confirms_inside_the_window(
    store, world, surface
):
    claim, revision, _ = _published_card(store, world, surface)
    due = correct(
        store,
        revocation_id="revocation:x1",
        claim_id=claim,
        card_revision_id=revision,
        reason="the supporting study used a superseded calibration constant",
        surface=surface,
        now=NOW,
    )
    assert datetime.fromisoformat(due) == NOW + timedelta(minutes=15)

    status = confirm_revocation(store, "revocation:x1", surface, NOW + timedelta(minutes=2))
    assert status == CONFIRMED
    assert revocation_latency_seconds(store, "revocation:x1") == 120
    assert surface.corrections_on(claim)[0]["reason"].startswith("the supporting study")


def test_a_retraction_removes_the_presentation_and_leaves_its_tombstone(store, world, surface):
    claim, revision, _ = _published_card(store, world, surface)
    retract(
        store,
        revocation_id="revocation:x2",
        claim_id=claim,
        card_revision_id=revision,
        reason="the study behind the only support was retracted",
        surface=surface,
        now=NOW,
        tombstone_id="tombstone:t1",
    )
    assert not surface.in_navigation(claim)
    assert surface.has_tombstone(claim)

    status = confirm_revocation(store, "revocation:x2", surface, NOW + timedelta(minutes=1))
    assert status == CONFIRMED

    tombstone = store.one("SELECT * FROM tombstones WHERE id = 'tombstone:t1'")
    assert "retracted" in tombstone["explanation"]
    # The revision is not deleted: what was published is what was published.
    assert store.one("SELECT COUNT(*) AS n FROM card_revisions WHERE id = ?", revision)["n"] == 1


def test_gate_4_demonstrates_the_window_and_not_merely_the_mechanism(store, world, surface):
    """Revocable and revocable-eventually are different guarantees."""
    claim, revision, _ = _published_card(store, world, surface)
    correct(
        store,
        revocation_id="revocation:x3",
        claim_id=claim,
        card_revision_id=revision,
        reason="a correction",
        surface=surface,
        now=NOW,
    )
    confirm_revocation(store, "revocation:x3", surface, NOW + timedelta(minutes=3))
    report = revocation_report(store)
    assert report["confirmed"] == 1
    assert report["unconfirmed"] == 0
    assert report["max_latency_seconds"] < report["window_seconds"]


def test_an_overdue_revocation_halts_its_class_with_no_operator_present(store, world, surface):
    claim, revision, _ = _published_card(store, world, surface)
    correct(
        store,
        revocation_id="revocation:x4",
        claim_id=claim,
        card_revision_id=revision,
        reason="a correction nobody confirmed",
        surface=surface,
        now=NOW,
    )
    # The surface never took it: strip the correction back off.
    served = surface.serving(claim)
    served.pop("corrections", None)
    surface.page_path(claim).write_text(__import__("json").dumps(served), encoding="utf-8")

    later = (NOW + timedelta(minutes=20)).isoformat(timespec="seconds")
    assert overdue_revocations(store, later) == ("revocation:x4",)
    halted = halt_classes_with_overdue_revocations(store, later)
    assert halted == (class_of(store, revision),)
    assert class_halted(store, class_of(store, revision))

    # And the halt refuses the next clearance in that class, automatically.
    refusals = {r.condition for r in refusal_conditions(store, revision, later)}
    assert "class_halted" in refusals
    assert "revocation_overdue" in refusals


# ---------------------------------------------------------------------------
# The appraisal split
# ---------------------------------------------------------------------------


def test_the_machine_dimensions_gate_publication_and_the_judgment_ones_do_not(
    store, world, surface
):
    _, revision, _ = _published_card(store, world, surface)
    rows = {
        row["dimension"]: row
        for row in store.query("SELECT * FROM appraisals WHERE card_revision_id = ?", revision)
    }
    for dimension in ("accuracy", "privacy", "risk", "rendering"):
        assert rows[dimension]["decided_by"] == "machine"
        assert rows[dimension]["passed"] == 1
    for dimension in ("fair_representation", "material_omission"):
        assert rows[dimension]["decided_by"] == "person"
        assert rows[dimension]["passed"] is None
        assert rows[dimension]["reviewer"] is None


def test_the_system_never_marks_its_own_fair_representation_passed(store, world, surface):
    _, revision, _ = _published_card(store, world, surface)
    appraise(store, revision)
    row = store.one(
        "SELECT passed FROM appraisals WHERE card_revision_id = ? AND dimension = ?",
        revision,
        "fair_representation",
    )
    assert row["passed"] is None
    with pytest.raises(ValueError, match="decided by machine"):
        record_judgment(
            store,
            card_revision_id=revision,
            dimension=AppraisalDimension.ACCURACY,
            passed=True,
            reviewer="operator:dean",
            finding="looks fine",
        )
    with pytest.raises(ValueError, match="records who decided it"):
        record_judgment(
            store,
            card_revision_id=revision,
            dimension=AppraisalDimension.FAIR_REPRESENTATION,
            passed=True,
            reviewer="",
            finding="",
        )


def test_a_failed_machine_dimension_refuses_clearance(store, world, surface):
    _claim, revision, _ = _published_card(store, world, surface)
    withdraw_edge(store, "edge:sup", "the study was retracted")

    refusals = {r.condition for r in refusal_conditions(store, revision)}
    assert "machine_appraisal_failed:accuracy" in refusals
    result = clear(store, revision, "clearance:c2")
    assert not result.granted


def test_a_judgment_finding_re_appraises_its_whole_class(store, world, surface):
    _, revision, _ = _published_card(store, world, surface)
    sample_for_review(store, revision, "sampled", "review:q1")
    record_judgment(
        store,
        card_revision_id=revision,
        dimension=AppraisalDimension.FAIR_REPRESENTATION,
        passed=False,
        reviewer="operator:dean",
        finding="the claimant's strongest position did not survive the rendering",
    )
    assert revision in class_needing_reappraisal(store, revision)
    assert review_debt(store, class_of(store, revision)) == 0


def test_sampling_the_same_revision_twice_is_one_debt(store, world, surface):
    """Otherwise the ceiling halts a class for how often something was confirmed
    rather than for how much of it is unreviewed."""
    _, revision, _ = _published_card(store, world, surface)
    first = sample_for_review(store, revision, "sampled", "review:q1")
    second = sample_for_review(store, revision, "sampled again", "review:q2")
    assert first == second
    assert review_debt(store, class_of(store, revision)) == 1


def test_passing_the_review_debt_ceiling_halts_the_class(store, world, surface):
    _, revision, _ = _published_card(store, world, surface)
    output_class = class_of(store, revision)
    sample_for_review(store, revision, "sampled", "review:q0")
    assert review_debt(store, output_class) == 1

    # The ceiling is about the accounting rather than the sampler, so the
    # backlog is built directly here.
    with store.write() as connection:
        for index in range(REVIEW_DEBT_CEILING + 1):
            connection.execute(
                "INSERT INTO review_queue (id, card_revision_id, class, sampled_reason, state, "
                "queued_at) VALUES (?, ?, ?, 'sampled', 'pending', datetime('now'))",
                (f"review:extra{index}", revision, output_class),
            )
    assert review_debt(store, output_class) > REVIEW_DEBT_CEILING
    refusals = {r.condition for r in refusal_conditions(store, revision)}
    assert "review_debt_ceiling_exceeded" in refusals


# ---------------------------------------------------------------------------
# Clearance, reach, and the tiers
# ---------------------------------------------------------------------------


def test_an_r3_card_cannot_publish_without_an_approval_of_that_exact_revision(
    store, world, surface
):
    claim, revision, _ = _published_card(store, world, surface, risk="R1")
    reclassify_claim_risk(store, claim, RiskTier.R3)
    assess_claim(store, claim, "assessment:a2")
    revision, _ = build_card(store, claim, "card:r2")

    refused = clear(store, revision, "clearance:r3a")
    assert not refused.granted
    assert "operator_approval_required" in {r.condition for r in refused.refusals}

    wrong = clear(
        store,
        revision,
        "clearance:r3b",
        operator_actor="operator:dean",
        operator_approves_exact_revision="the hash of some other revision",
    )
    assert not wrong.granted
    assert "approval_names_a_different_revision" in {r.condition for r in wrong.refusals}

    content_hash = store.one("SELECT content_hash FROM card_revisions WHERE id = ?", revision)[
        "content_hash"
    ]
    approved = clear(
        store,
        revision,
        "clearance:r3c",
        operator_actor="operator:dean",
        operator_approves_exact_revision=content_hash,
    )
    assert approved.granted
    assert approved.requires_operator


def test_r4_never_publishes(store, world, surface):
    claim, revision, _ = _published_card(store, world, surface)
    reclassify_claim_risk(store, claim, RiskTier.R4)
    refusals = {r.condition for r in refusal_conditions(store, revision)}
    assert "content_is_r4" in refusals
    assert not clear(store, revision, "clearance:r4").granted


def test_missing_risk_state_behaves_as_r3(store, world, surface):
    claim, revision, _ = _published_card(store, world, surface)
    with store.write() as connection:
        connection.execute("UPDATE claims SET risk = NULL WHERE id = ?", (claim,))
    refusals = {r.condition for r in refusal_conditions(store, revision)}
    assert "risk_state_missing" in refusals


def test_local_publication_is_on_and_public_reach_is_off(store):
    """Gate 4 turns on local publication for R0-R2. Reach is a separate act."""
    assert reach_enabled(store, LOCAL)
    assert not reach_enabled(store, PUBLIC)


def test_widening_reach_is_an_explicit_scoped_operator_act(store):
    with pytest.raises(ValueError, match="explicit scoped operator act"):
        set_reach(store, PUBLIC, True, actor="", reason="", scope="")
    with pytest.raises(ValueError, match="explicit scoped operator act"):
        set_reach(store, PUBLIC, True, actor="operator:dean", reason="ready", scope="")

    set_reach(
        store,
        PUBLIC,
        True,
        actor="operator:dean",
        reason="the pilot completed",
        scope="claim cards at R0 and R1",
    )
    assert reach_enabled(store, PUBLIC)


def test_locking_down_takes_less_than_widening(store):
    """A control that is harder to pull than to push is not a control."""
    set_reach(
        store, PUBLIC, True, actor="operator:dean", reason="ready", scope="R0 and R1 cards"
    )
    set_reach(store, PUBLIC, False, actor="", reason="")
    assert not reach_enabled(store, PUBLIC)


def test_locking_down_reach_touches_no_evidence(store, world, surface):
    _claim, _revision, _ = _published_card(store, world, surface)
    before = store.one("SELECT COUNT(*) AS n FROM edge_events")["n"]
    assessments = store.one("SELECT COUNT(*) AS n FROM assessments")["n"]

    set_reach(store, PUBLIC, False, actor="operator:dean", reason="lock down")
    assert store.one("SELECT COUNT(*) AS n FROM edge_events")["n"] == before
    assert store.one("SELECT COUNT(*) AS n FROM assessments")["n"] == assessments


def test_a_clearance_carries_only_for_the_revision_it_named(store, world, surface):
    claim, _revision, clearance = _published_card(store, world, surface)
    withdraw_edge(store, "edge:sup", "retracted")
    assess_claim(store, claim, "assessment:a3")
    second, _ = build_card(store, claim, "card:r9")

    with pytest.raises(ValueError, match="only for the revision it named"):
        publish(
            store,
            publication_id="publication:p9",
            card_revision_id=second,
            clearance_id=clearance,
            surface=surface,
        )


def test_a_refused_clearance_cannot_be_published(store, world, surface):
    claim, revision, _ = _published_card(store, world, surface)
    reclassify_claim_risk(store, claim, RiskTier.R4)
    refused = clear(store, revision, "clearance:no")
    assert not refused.granted
    with pytest.raises(ValueError, match="was refused"):
        publish(
            store,
            publication_id="publication:no",
            card_revision_id=revision,
            clearance_id="clearance:no",
            surface=surface,
        )
