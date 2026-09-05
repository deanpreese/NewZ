"""Claim cards, entity cards, and the dependency validator."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from newz.domain.enums import (
    EdgeRelation,
    EvidenceLane,
    IndependenceJustification,
    RiskTier,
    TaskState,
)
from newz.evidence.assess import assess_claim
from newz.evidence.bases import record_basis, record_independence
from newz.evidence.claims import reclassify_claim_risk
from newz.evidence.edges import admit_edge, withdraw_edge
from newz.present.cards import build_card, claim_card, load_card, render_card
from newz.present.dependencies import (
    invalidate_dependents,
    pending_rebuilds,
    validate_dependencies,
)
from newz.present.entities import entity_card
from tests import world as world_module
from tests.world import add_task

NOW = datetime(2026, 9, 5, 12, 0, 0)


@pytest.fixture
def world(store):
    built = world_module.build(store)
    with store.write() as connection:
        record_basis(connection, "basis:witness", "witness", "witness:alvarado-r", True)
        record_basis(connection, "basis:proto-4471", "experiment", "protocol:PROTO-4471", True)
        record_basis(connection, "basis:proto-5520", "experiment", "protocol:PROTO-5520", True)
        record_basis(connection, "basis:judgment", "official_record", "docket#44", True)
        record_basis(connection, "basis:complaint", "filing", "docket#1", True)
        record_independence(
            connection,
            "independence:labs",
            "basis:proto-4471",
            "basis:proto-5520",
            IndependenceJustification.DISTINCT_EXPERIMENT,
            evidence="different laboratories and registrations",
        )
    return built


def _contested_claim(store, world) -> str:
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
    assess_claim(store, claim, "assessment:c1")
    return claim


# ---------------------------------------------------------------------------
# The claim card
# ---------------------------------------------------------------------------


def test_a_card_carries_every_field_the_spec_names(store, world):
    claim = _contested_claim(store, world)
    add_task(store, "task:p1", claim, EvidenceLane.PRIMARY_RECORD, TaskState.OPEN, described=False)
    card = claim_card(store, claim)

    assert card.wording and card.claim_kind == "measurement_or_association"
    assert card.state == "contested"
    assert card.risk == "R1"
    assert card.supporting and card.contradicting
    assert card.supporting[0].quote and card.supporting[0].locator
    assert card.supporting[0].retrieved_from.startswith("https://")
    assert (card.supporting_bases, card.contradicting_bases) == (1, 1)
    assert card.independence_note
    assert card.what_would_change_this
    assert card.history
    assert card.policy_version and card.code_version
    assert ("primary_record", "open") in card.active_tasks


def test_every_displayed_sentence_traces_to_a_live_edge_and_a_span(store, world):
    """The audit a reader performs: each quoted item names its edge and artifact."""
    claim = _contested_claim(store, world)
    card = claim_card(store, claim)
    for item in card.supporting + card.contradicting + card.context:
        edge = store.one("SELECT live, admitted FROM edge_events WHERE id = ?", item.edge_id)
        assert edge["live"] and edge["admitted"]
        assertion = store.one(
            "SELECT quote FROM assertions WHERE artifact_id = ? AND quote = ?",
            item.artifact_id,
            item.quote,
        )
        assert assertion is not None


def test_a_card_says_when_several_citations_rest_on_one_basis(store, world):
    claim = world.claim("registry", "radar")
    with store.write() as connection:
        record_basis(connection, "basis:one-origin", "witness", "witness:alvarado-r", True)
    for index, (key, name) in enumerate((("harbour", "sighting"), ("meridian", "sighting"))):
        admit_edge(
            store,
            edge_id=f"edge:same{index}",
            assertion_id=world.assertion(key, name),
            claim_id=claim,
            relation=EdgeRelation.SUPPORTS,
            basis_id="basis:one-origin",
            risk=RiskTier.R1,
        )
    assess_claim(store, claim, "assessment:same")
    card = claim_card(store, claim)
    assert card.supporting_bases == 1
    assert "one independent basis" in card.independence_note


def test_a_card_states_its_limitations_rather_than_implying_them(store, world):
    claim = world.claim("registry", "radar")
    with store.write() as connection:
        record_basis(connection, "basis:w", "witness", "witness:alvarado-r", True)
    admit_edge(
        store,
        edge_id="edge:test",
        assertion_id=world.assertion("harbour", "sighting"),
        claim_id=claim,
        relation=EdgeRelation.SUPPORTS,
        basis_id="basis:w",
        risk=RiskTier.R1,
    )
    assess_claim(store, claim, "assessment:lim")
    card = claim_card(store, claim)
    assert any("testimony" in note for note in card.limitations)


def test_a_card_needs_an_assessment_to_be_a_view_of(store, world):
    with pytest.raises(ValueError, match="no assessment"):
        claim_card(store, world.claim("registry", "radar"))


def test_rendering_produces_prose_composed_only_from_the_projection(store, world):
    claim = _contested_claim(store, world)
    text = render_card(claim_card(store, claim))
    assert "contested" in text
    assert "What would change this:" in text
    assert "counted" in text


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


def test_building_an_unchanged_card_twice_is_one_revision(store, world):
    """Every rebuild looking like a correction would make corrections worthless."""
    claim = _contested_claim(store, world)
    first, built = build_card(store, claim, "card:r1")
    assert built
    second, rebuilt = build_card(store, claim, "card:r2")
    assert second == first
    assert not rebuilt
    assert store.one("SELECT COUNT(*) AS n FROM card_revisions")["n"] == 1


def test_a_changed_assessment_produces_a_new_revision_and_supersedes_the_old(store, world):
    claim = _contested_claim(store, world)
    build_card(store, claim, "card:r1")
    withdraw_edge(store, "edge:sup", "the study was retracted")
    assess_claim(store, claim, "assessment:c2")
    second, built = build_card(store, claim, "card:r2")

    assert built and second == "card:r2"
    old = store.one("SELECT * FROM card_revisions WHERE id = 'card:r1'")
    assert old["live"] == 0
    assert old["superseded_by"] == "card:r2"
    assert load_card(store, "card:r2")["state"] == "provisional_contradiction"
    assert len(load_card(store, "card:r2")["history"]) == 2


def test_a_card_revision_cannot_be_rewritten(store, world):
    import sqlite3

    claim = _contested_claim(store, world)
    build_card(store, claim, "card:r1")
    with pytest.raises(sqlite3.IntegrityError, match="immutable"), store.write() as connection:
        connection.execute("UPDATE card_revisions SET content_json = '{}' WHERE id = 'card:r1'")


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def test_a_fresh_card_validates(store, world):
    claim = _contested_claim(store, world)
    build_card(store, claim, "card:r1")
    assert validate_dependencies(store, "card:r1").ok


def test_a_withdrawn_edge_makes_its_card_refuse_to_publish(store, world):
    claim = _contested_claim(store, world)
    build_card(store, claim, "card:r1")
    withdraw_edge(store, "edge:sup", "retracted")

    report = validate_dependencies(store, "card:r1")
    assert not report.ok
    assert any(failure.reason == "edge withdrawn" for failure in report.failures)
    assert pending_rebuilds(store) == ("card:r1",)


def test_a_changed_risk_makes_a_card_stale(store, world):
    """A card built at R1 that is now R3 is stale in the way that matters most."""
    claim = _contested_claim(store, world)
    build_card(store, claim, "card:r1")
    reclassify_claim_risk(store, claim, RiskTier.R3)

    report = validate_dependencies(store, "card:r1")
    assert not report.ok
    assert any(failure.kind == "risk" for failure in report.failures)


def test_a_reassessment_under_a_new_policy_makes_a_card_stale(store, world):
    claim = _contested_claim(store, world)
    build_card(store, claim, "card:r1")
    assess_claim(store, claim, "assessment:c9", policy_version="2.0.0")

    report = validate_dependencies(store, "card:r1")
    assert not report.ok
    assert any("policy 2.0.0" in failure.reason for failure in report.failures)


def test_invalidation_names_the_revisions_and_deletes_nothing(store, world):
    claim = _contested_claim(store, world)
    build_card(store, claim, "card:r1")
    affected = invalidate_dependents(store, "edge", "edge:sup", "retracted")

    assert affected == ("card:r1",)
    assert store.one("SELECT COUNT(*) AS n FROM card_revisions WHERE id = 'card:r1'")["n"] == 1
    event = store.one("SELECT * FROM outbox WHERE kind = 'cards_invalidated'")
    assert json.loads(event["payload"])["revisions"] == ["card:r1"]


# ---------------------------------------------------------------------------
# Entity cards
# ---------------------------------------------------------------------------


def _entity(store, name: str) -> str:
    row = store.one("SELECT id FROM entities WHERE name = ?", name)
    return row["id"] if row else ""


def test_an_entity_card_is_computed_and_never_stored(store, world):
    """No dossier exists at rest to leak, to compel, or to outlive its sources."""
    _contested_claim(store, world)
    tables = {
        row["name"]
        for row in store.query("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert "entity_cards" not in tables
    entity_columns = {row["name"] for row in store.query("PRAGMA table_info(entities)")}
    assert entity_columns == {"id", "name", "kind", "disambiguation", "recorded_at"}


def test_an_entity_card_shows_one_basis_where_many_claims_share_one(store, world):
    """Ten claims resting on one origin display as one basis, not as a pattern."""
    with store.write() as connection:
        connection.execute(
            "INSERT INTO entities (id, name, kind, disambiguation, recorded_at) "
            "VALUES ('entity:e1', 'Meridian Instruments Inc.', 'organisation', '', datetime('now'))"
        )
        record_basis(connection, "basis:single", "filing", "docket#1", True)

    for index in range(3):
        claim_id = f"claim:multi{index}"
        with store.write() as connection:
            connection.execute(
                "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
                "withdrawn, recorded_at) VALUES (?, 'event_or_observation', ?, 'R1', NULL, NULL, "
                "0, datetime('now'))",
                (claim_id, f"an allegation numbered {index}"),
            )
        admit_edge(
            store,
            edge_id=f"edge:multi{index}",
            assertion_id=world.assertion("complaint", "alleges"),
            claim_id=claim_id,
            relation=EdgeRelation.CLAIMANT_SAYS,
            basis_id="basis:single",
            risk=RiskTier.R1,
        )
        assess_claim(store, claim_id, f"assessment:multi{index}")
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO assertion_entities (assertion_id, entity_id) VALUES (?, ?)",
            (world.assertion("complaint", "alleges"), "entity:e1"),
        )

    card = entity_card(store, "entity:e1")
    assert len(card.claims) == 3
    assert card.independent_bases == 1
    assert card.distinct_basis_citations == 1


def test_an_entity_card_says_first_when_nothing_is_established(store, world):
    with store.write() as connection:
        connection.execute(
            "INSERT INTO entities (id, name, kind, disambiguation, recorded_at) "
            "VALUES ('entity:e2', 'A Named Party', 'person', 'the one in the docket', datetime('now'))"
        )
    card = entity_card(store, "entity:e2")
    assert card.nothing_established
    assert "no assessed claim" in card.notice


def test_an_r3_entity_card_cannot_publish(store, world):
    with store.write() as connection:
        connection.execute(
            "INSERT INTO entities (id, name, kind, disambiguation, recorded_at) "
            "VALUES ('entity:e3', 'A Living Person', 'person', '', datetime('now'))"
        )
        record_basis(connection, "basis:r3", "filing", "docket#1", True)
        connection.execute(
            "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
            "withdrawn, recorded_at) VALUES ('claim:r3', "
            "'identity_or_wrongdoing_allegation', 'an allegation', 'R3', NULL, NULL, 0, "
            "datetime('now'))"
        )
    admit_edge(
        store,
        edge_id="edge:r3",
        assertion_id=world.assertion("court", "judgment"),
        claim_id="claim:r3",
        relation=EdgeRelation.CONTRADICTS,
        basis_id="basis:r3",
        risk=RiskTier.R3,
        adjudicative_scope_covers_claim=True,
    )
    assess_claim(store, "claim:r3", "assessment:r3")
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO assertion_entities (assertion_id, entity_id) VALUES (?, ?)",
            (world.assertion("court", "judgment"), "entity:e3"),
        )

    card = entity_card(store, "entity:e3", actor="operator:dean", reason="review", living_person=True)
    assert card.effective_risk == "R3"
    assert not card.publishable
    assert "not published" in card.refusal
    assert card.access_logged

    logged = store.one("SELECT * FROM entity_card_access WHERE entity_id = 'entity:e3'")
    assert logged["actor"] == "operator:dean"
    assert logged["reason"] == "review"
    assert logged["risk"] == "R3"


def test_reading_a_living_persons_card_without_an_actor_is_refused(store, world):
    test_an_r3_entity_card_cannot_publish(store, world)
    with pytest.raises(ValueError, match="logs actor and reason"):
        entity_card(store, "entity:e3", living_person=True)


def test_an_entity_card_never_shows_a_claim_with_no_assessment(store, world):
    """A bare allegation is exactly what this view may not carry."""
    with store.write() as connection:
        connection.execute(
            "INSERT INTO entities (id, name, kind, disambiguation, recorded_at) "
            "VALUES ('entity:e4', 'Another Party', 'organisation', '', datetime('now'))"
        )
        record_basis(connection, "basis:unassessed", "filing", "docket#1", True)
        connection.execute(
            "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
            "withdrawn, recorded_at) VALUES ('claim:unassessed', 'event_or_observation', "
            "'never assessed', 'R1', NULL, NULL, 0, datetime('now'))"
        )
    admit_edge(
        store,
        edge_id="edge:unassessed",
        assertion_id=world.assertion("complaint", "alleges"),
        claim_id="claim:unassessed",
        relation=EdgeRelation.CLAIMANT_SAYS,
        basis_id="basis:unassessed",
        risk=RiskTier.R1,
    )
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO assertion_entities (assertion_id, entity_id) VALUES (?, ?)",
            (world.assertion("complaint", "alleges"), "entity:e4"),
        )
    card = entity_card(store, "entity:e4")
    assert card.claims == ()
    assert card.nothing_established
