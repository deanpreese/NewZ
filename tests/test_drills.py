"""The Gate 6 drills, run against a real store rather than attested to.

Each drill is tested twice: once that it passes on a healthy store, and once
that it fails on a store with the specific defect it exists to catch. A drill
that has only ever been seen passing is a drill nobody has tested.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.domain.enums import (
    EdgeRelation,
    IndependenceJustification,
    RiskTier,
)
from newz.evidence.assess import assess_claim, load_assessment
from newz.evidence.bases import record_basis, record_independence
from newz.evidence.edges import admit_edge, withdraw_edge
from newz.pilot.drills import (
    correction_drill,
    gate_6_status,
    policy_drift,
    policy_replay,
    record_policy_version,
    restore_drill,
    run_drills,
)
from newz.policy.bundle import BUNDLE
from newz.present.cards import build_card
from newz.publish.clearance import clear
from newz.publish.publication import confirm_publication, publish
from newz.publish.surface import LocalSurface
from newz.store.erasure import KeyStore
from newz.version import CODE_VERSION
from tests import world as world_module

NOW = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def surface(tmp_path):
    return LocalSurface(root=tmp_path / "surface")


@pytest.fixture
def assessed(store):
    """A world with one contested claim carried all the way to a published card."""
    world = world_module.build(store)
    with store.write() as connection:
        record_basis(connection, "basis:proto-4471", "experiment", "protocol:PROTO-4471", True)
        record_basis(connection, "basis:proto-5520", "experiment", "protocol:PROTO-5520", True)
        record_independence(
            connection,
            "independence:labs",
            "basis:proto-4471",
            "basis:proto-5520",
            IndependenceJustification.DISTINCT_EXPERIMENT,
            evidence="different laboratories",
        )
    claim = world.claim("kettleby", "signature")
    admit_edge(
        store,
        edge_id="edge:sup",
        assertion_id=world.assertion("kettleby", "effect"),
        claim_id=claim,
        relation=EdgeRelation.SUPPORTS,
        basis_id="basis:proto-4471",
        risk=RiskTier.R1,
    )
    admit_edge(
        store,
        edge_id="edge:con",
        assertion_id=world.assertion("ardenne", "no_effect"),
        claim_id=claim,
        relation=EdgeRelation.CONTRADICTS,
        basis_id="basis:proto-5520",
        risk=RiskTier.R1,
    )
    with store.write() as connection:
        connection.execute("UPDATE claims SET risk = 'R1' WHERE id = ?", (claim,))
    assess_claim(store, claim, "assessment:a1")
    return world, claim


# ---------------------------------------------------------------------------
# What a policy version contained
# ---------------------------------------------------------------------------


def test_a_policy_version_is_recorded_once(store):
    first = record_policy_version(store)
    second = record_policy_version(store)
    assert first == second == BUNDLE.digest
    assert store.one("SELECT COUNT(*) AS n FROM policy_versions")["n"] == 1


def test_a_recorded_policy_version_cannot_be_rewritten(store):
    record_policy_version(store)
    with pytest.raises(Exception, match="what it was"), store.write() as connection:
        connection.execute("UPDATE policy_versions SET digest = 'other'")


def test_a_policy_edited_without_a_version_bump_is_drift(store):
    record_policy_version(store)
    assert policy_drift(store) == ()
    with store.write() as connection:
        connection.execute(
            "DELETE FROM policy_versions WHERE version = ?", (BUNDLE.version,)
        )
        connection.execute(
            "INSERT INTO policy_versions (version, digest, code_version, recorded_at) "
            "VALUES (?, 'a-different-policy-entirely', ?, datetime('now'))",
            (BUNDLE.version, CODE_VERSION),
        )
    drift = policy_drift(store)
    assert len(drift) == 1
    assert "was not bumped" in drift[0]


# ---------------------------------------------------------------------------
# Policy replay
# ---------------------------------------------------------------------------


def test_replay_reproduces_every_assessment(store, assessed):
    record_policy_version(store)
    result = policy_replay(store)
    assert result.passed, result.findings
    assert "1 reproduced" in result.detail


def test_replay_reports_drift_even_when_every_assessment_reproduces(store, assessed):
    with store.write() as connection:
        connection.execute(
            "INSERT INTO policy_versions (version, digest, code_version, recorded_at) "
            "VALUES (?, 'not-what-the-code-produces', ?, datetime('now'))",
            (BUNDLE.version, CODE_VERSION),
        )
    result = policy_replay(store)
    assert not result.passed
    assert any("was not bumped" in finding for finding in result.findings)


def test_replay_refuses_an_assessment_from_a_superseded_policy(store, assessed):
    _, claim = assessed
    record_policy_version(store)
    assess_claim(store, claim, "assessment:old", policy_version="0.0.1")
    result = policy_replay(store)
    assert "1 not replayable" in result.detail
    assert any("assessment:old" in finding for finding in result.findings)
    # Unreplayable is not divergence: nothing was shown to be wrong.
    assert result.passed


def test_replay_catches_a_claim_whose_evidence_moved_under_it(store, assessed):
    """The finding replay exists for: a card still showing a conclusion the
    ledger stopped supporting, because nobody reassessed after a withdrawal."""
    record_policy_version(store)
    assert policy_replay(store).passed
    withdraw_edge(store, "edge:con", "the second laboratory retracted")

    result = policy_replay(store)
    assert not result.passed
    assert "1 owe a reassessment" in result.detail
    assert any("owes a reassessment" in finding for finding in result.findings)
    assert any("contradicting_bases" in finding for finding in result.findings)


def test_a_reassessment_settles_what_replay_found(store, assessed):
    _, claim = assessed
    record_policy_version(store)
    withdraw_edge(store, "edge:con", "the second laboratory retracted")
    assert not policy_replay(store).passed
    assess_claim(store, claim, "assessment:a2")
    assert policy_replay(store).passed


def test_a_forecast_replays_against_the_horizon_it_was_given(store, assessed):
    """The horizon was an input; replaying without it would guess."""
    world, _ = assessed
    claim = world_module.add_claim(
        store, "claim:forecast", "forecast", "the craft will be identified by 2030", "R0"
    )
    admit_edge(
        store,
        edge_id="edge:forecast",
        assertion_id=world.assertion("kettleby", "effect"),
        claim_id=claim,
        relation=EdgeRelation.SUPPORTS,
        basis_id="basis:proto-4471",
        risk=RiskTier.R0,
    )
    assess_claim(store, claim, "assessment:f1", horizon_reached=True)
    before = load_assessment(store, "assessment:f1")
    record_policy_version(store)
    assert policy_replay(store).passed

    # And the flag is what makes it replay: the same claim without it is a
    # different assessment, so a store that had not recorded it would have to
    # pick one and be wrong half the time.
    assess_claim(store, claim, "assessment:f2", horizon_reached=False)
    assert load_assessment(store, "assessment:f2").state is not before.state
    assert policy_replay(store).passed


# ---------------------------------------------------------------------------
# Disaster recovery
# ---------------------------------------------------------------------------


def test_the_restore_drill_rebuilds_cards_and_histories(store, assessed, tmp_path):
    _, claim = assessed
    build_card(store, claim, "card:r1")
    result = restore_drill(store, tmp_path / "backup")
    assert result.passed, result.findings
    assert "1 claim cards and histories rebuilt" in result.detail


def test_the_restore_drill_reads_from_the_copy_and_not_the_original(store, assessed, tmp_path):
    """A backup that only restores while the original is present is not a backup."""
    _, claim = assessed
    build_card(store, claim, "card:r1")
    destination = tmp_path / "backup"
    restore_drill(store, destination)
    assert (destination / store.path.name).exists()
    assert (destination / "artifacts").exists()


def test_the_restore_drill_fails_on_a_corrupted_artifact(store, assessed, tmp_path):
    _, claim = assessed
    build_card(store, claim, "card:r1")
    destination = tmp_path / "backup"
    restore_drill(store, destination)  # a first, clean run

    row = store.one("SELECT id FROM artifacts ORDER BY id LIMIT 1")
    path = next(p for p in store.artifact_root.rglob("*") if p.is_file())
    path.write_bytes(b"not what was hashed")
    result = restore_drill(store, destination)
    assert not result.passed
    assert any("artifact" in finding for finding in result.findings), (row, result.findings)


def test_the_restore_drill_refuses_when_the_keys_would_travel(store, assessed, tmp_path):
    """Erasure by key destruction, undone by an operations procedure."""
    build_card(store, assessed[1], "card:r1")
    inside = store.artifact_root / "keys"
    KeyStore(root=inside).create("subject:1")

    result = restore_drill(store, tmp_path / "backup", keys_root=inside)
    assert not result.passed
    assert any("un-erase" in finding for finding in result.findings)
    assert result.detail == "refused before taking a backup"
    # And it refused before doing anything, rather than after.
    assert not (tmp_path / "backup").exists()


def test_the_restore_drill_accepts_keys_kept_outside_the_backup_set(store, assessed, tmp_path):
    build_card(store, assessed[1], "card:r1")
    outside = tmp_path / "elsewhere" / "keys"
    KeyStore(root=outside).create("subject:1")

    result = restore_drill(store, tmp_path / "backup", keys_root=outside)
    assert result.passed, result.findings
    assert not list((tmp_path / "backup").rglob("*.key"))


# ---------------------------------------------------------------------------
# Public correction
# ---------------------------------------------------------------------------


def test_the_correction_drill_confirms_from_the_surface(store, assessed, surface):
    _, claim = assessed
    revision, _ = build_card(store, claim, "card:r1")
    clear(store, revision, "clearance:c1")
    publish(
        store,
        publication_id="publication:p1",
        card_revision_id=revision,
        clearance_id="clearance:c1",
        surface=surface,
    )
    confirm_publication(store, "publication:p1", surface)

    result = correction_drill(
        store,
        surface,
        claim_id=claim,
        card_revision_id=revision,
        now=NOW,
        confirmed_at=NOW + timedelta(minutes=4),
    )
    assert result.passed, result.findings
    assert "confirmed after 240s" in result.detail


def test_the_correction_drill_fails_outside_the_window(store, assessed, surface):
    _, claim = assessed
    revision, _ = build_card(store, claim, "card:r1")
    clear(store, revision, "clearance:c1")
    publish(
        store,
        publication_id="publication:p1",
        card_revision_id=revision,
        clearance_id="clearance:c1",
        surface=surface,
    )
    confirm_publication(store, "publication:p1", surface)

    result = correction_drill(
        store,
        surface,
        claim_id=claim,
        card_revision_id=revision,
        now=NOW,
        confirmed_at=NOW + timedelta(minutes=40),
    )
    assert not result.passed
    assert any("past the 900s window" in finding for finding in result.findings)


# ---------------------------------------------------------------------------
# What the drills add up to
# ---------------------------------------------------------------------------


def test_gate_6_names_what_a_person_still_has_to_supply(store, assessed, tmp_path):
    build_card(store, assessed[1], "card:r1")
    results = run_drills(store, tmp_path / "backup")
    status = gate_6_status(store, results)
    assert all(drill["passed"] for drill in status["drills"]), status
    assert status["policy_digest"] == BUNDLE.digest
    assert any("security review" in item for item in status["operator_supplied"])
    assert any("service objectives" in item for item in status["operator_supplied"])
