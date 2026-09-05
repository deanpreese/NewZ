"""The reader surface and its controls, browse, the composer, and export."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.domain.enums import EdgeRelation, IndependenceJustification, RiskTier
from newz.evidence.assess import assess_claim
from newz.evidence.bases import record_basis, record_independence
from newz.evidence.claims import reclassify_claim_risk
from newz.evidence.edges import admit_edge, withdraw_edge
from newz.present.cards import build_card
from newz.publish.browse import assessment_history_of, search_claims, search_entities, topics
from newz.publish.clearance import clear
from newz.publish.export import export_claims, export_corpus, verify_export
from newz.publish.publication import confirm_publication, publish, retract
from newz.publish.reader import (
    READS_PER_MINUTE,
    Reader,
    ReaderRefused,
    access_report,
    issue_token,
    revoke_token,
)
from newz.publish.reports import CONNECTIVES, Cited, Connective, compose
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
        record_independence(
            connection,
            "independence:labs",
            "basis:proto-4471",
            "basis:proto-5520",
            IndependenceJustification.DISTINCT_EXPERIMENT,
            evidence="different laboratories",
        )
    return built


@pytest.fixture
def published(store, world, surface):
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
    return claim, revision


# ---------------------------------------------------------------------------
# The reader surface
# ---------------------------------------------------------------------------


def test_a_reader_needs_a_token(store, surface, published):
    claim, _ = published
    with pytest.raises(ReaderRefused, match="unknown token"):
        Reader(store, surface, "not-a-real-token").read(claim, NOW)


def test_only_the_hash_of_a_token_is_stored(store):
    token = issue_token(store, "token:t1", "the operator's laptop", "local", "operator:dean")
    row = store.one("SELECT * FROM reader_tokens WHERE id = 'token:t1'")
    assert token not in row["token_hash"]
    assert len(row["token_hash"]) == 64


def test_a_reader_with_a_token_can_read_a_published_card(store, surface, published):
    claim, revision = published
    token = issue_token(store, "token:t1", "reader", "local", "operator:dean")
    document = Reader(store, surface, token).read(claim, NOW)
    assert document["revision_id"] == revision
    assert document["card"]["state"] == "contested"


def test_a_revoked_token_stops_working(store, surface, published):
    claim, _ = published
    token = issue_token(store, "token:t1", "reader", "local", "operator:dean")
    reader = Reader(store, surface, token)
    reader.read(claim, NOW)
    revoke_token(store, "token:t1")
    with pytest.raises(ReaderRefused, match="revoked"):
        reader.read(claim, NOW)


def test_the_rate_limit_is_measured_against_the_recorded_log(store, surface, published):
    """A counter in memory resets when the process does."""
    claim, _ = published
    token = issue_token(store, "token:t1", "reader", "local", "operator:dean")
    reader = Reader(store, surface, token)
    for _ in range(READS_PER_MINUTE):
        reader.read(claim, NOW)
    with pytest.raises(ReaderRefused, match="reads per minute"):
        reader.read(claim, NOW)
    # A fresh Reader object is not a fresh allowance.
    with pytest.raises(ReaderRefused, match="reads per minute"):
        Reader(store, surface, token).read(claim, NOW)
    # The next minute is.
    assert Reader(store, surface, token).read(claim, NOW + timedelta(minutes=2))


def test_an_r3_card_is_not_listed_and_reads_as_absent(store, surface, published):
    """A list of what is being kept from you is most of what is being kept."""
    claim, _ = published
    token = issue_token(store, "token:t1", "reader", "local", "operator:dean")
    reader = Reader(store, surface, token)
    assert [entry["claim_id"] for entry in reader.browse(NOW)] == [claim]

    reclassify_claim_risk(store, claim, RiskTier.R3)
    document = surface.serving(claim)
    document["card"]["risk"] = "R3"
    surface.page_path(claim).write_text(__import__("json").dumps(document), encoding="utf-8")
    surface._reindex()

    with pytest.raises(ReaderRefused, match="not found"):
        reader.read(claim, NOW)
    assert reader.browse(NOW) == []
    assert access_report(store, "token:t1")["withheld"] == 1


def test_a_retracted_presentation_tells_the_reader_it_was_retracted(store, surface, published):
    claim, revision = published
    retract(
        store,
        revocation_id="revocation:r1",
        claim_id=claim,
        card_revision_id=revision,
        reason="the support was retracted",
        surface=surface,
        now=NOW,
        tombstone_id="tombstone:t1",
    )
    token = issue_token(store, "token:t1", "reader", "local", "operator:dean")
    with pytest.raises(ReaderRefused, match="retracted"):
        Reader(store, surface, token).read(claim, NOW)


def test_every_read_is_logged_with_its_outcome(store, surface, published):
    claim, _ = published
    token = issue_token(store, "token:t1", "reader", "local", "operator:dean")
    reader = Reader(store, surface, token)
    reader.read(claim, NOW)
    with pytest.raises(ReaderRefused):
        reader.read("claim:absent", NOW)
    assert access_report(store, "token:t1") == {"served": 1, "not_served": 1}


# ---------------------------------------------------------------------------
# Browse, over the whole record
# ---------------------------------------------------------------------------


def test_the_operator_can_search_the_record_and_not_only_the_surface(store, world, published):
    claim, _ = published
    everything = search_claims(store)
    assert len(everything) >= 3
    assert any(row["id"] == claim and row["state"] == "contested" for row in everything)

    assert search_claims(store, state="contested")[0]["id"] == claim
    assert search_claims(store, kind="identity_or_wrongdoing_allegation")
    assert search_claims(store, text="thermal signature")[0]["id"] == claim
    assert search_claims(store, risk="R1")


def test_entities_are_searchable_as_addresses_rather_than_dossiers(store, world, published):
    with store.write() as connection:
        connection.execute(
            "INSERT INTO entities (id, name, kind, disambiguation, recorded_at) "
            "VALUES ('entity:e1', 'Kettleby Metrology', 'organisation', 'the laboratory', "
            "datetime('now'))"
        )
    found = search_entities(store, "Kettleby")
    assert found[0]["name"] == "Kettleby Metrology"
    assert set(found[0]) == {"id", "name", "kind", "disambiguation", "claims_naming"}


def test_assessment_history_is_browsable(store, world, published):
    claim, _ = published
    withdraw_edge(store, "edge:sup", "retracted")
    assess_claim(store, claim, "assessment:a2")
    history = assessment_history_of(store, claim)
    assert [entry["state"] for entry in history] == ["contested", "provisional_contradiction"]


def test_topics_come_from_the_catalog(store, world):
    assert {row["topic"] for row in topics(store)} >= {"uap_and_aerospace_anomalies"}


# ---------------------------------------------------------------------------
# The report composer
# ---------------------------------------------------------------------------


def test_a_report_needs_a_citation_for_every_factual_block(store, published):
    claim, _ = published
    report = compose(
        store,
        "report:r1",
        "The RX-9 thermal signature",
        [
            Connective(CONNECTIVES[0]),
            Cited("Two laboratories measured the array.", claim, ("edge:sup", "edge:con")),
        ],
    )
    assert report.composed
    assert "edge:sup" in report.render()

    refused = compose(
        store,
        "report:r2",
        "The RX-9 thermal signature",
        [Cited("The array plainly works.", claim, ())],
    )
    assert not refused.composed
    assert refused.failures[0].reason == "prose_without_citation"


def test_a_connective_outside_the_composers_vocabulary_is_refused(store, published):
    _claim, _ = published
    refused = compose(
        store,
        "report:r3",
        "title",
        [Connective("The evidence overwhelmingly shows the effect is real.")],
    )
    assert refused.failures[0].reason == "prose_without_citation"


def test_a_report_cannot_omit_material_counterevidence(store, published):
    claim, _ = published
    refused = compose(
        store,
        "report:r4",
        "title",
        [Cited("The array shows a signature.", claim, ("edge:sup",))],
    )
    assert not refused.composed
    assert refused.failures[0].reason == "material_counterevidence_omitted"


def test_a_report_citing_a_withdrawn_edge_fails_to_compose(store, published):
    claim, _ = published
    withdraw_edge(store, "edge:sup", "retracted")
    assess_claim(store, claim, "assessment:a2")
    refused = compose(
        store,
        "report:r5",
        "title",
        [Cited("The array shows a signature.", claim, ("edge:sup", "edge:con"))],
    )
    assert refused.failures[0].reason == "cited_edge_not_live"
    with pytest.raises(ValueError, match="not rendered"):
        refused.render()


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_exporting_one_claim_carries_its_artifacts_and_verifies(store, published, tmp_path):
    claim, _ = published
    manifest = export_claims(store, tmp_path / "export", [claim])
    assert manifest.claims == (claim,)
    assert manifest.artifacts

    ok, problems = verify_export(tmp_path / "export")
    assert ok, problems
    assert (tmp_path / "export" / "policy" / "bundle.json").exists()

    exported = __import__("json").loads(
        (tmp_path / "export" / f"claims/{claim.replace(':', '_')}.json").read_text()
    )
    assert exported["assessments"]
    assert exported["edges"]
    assert exported["card"]["state"] == "contested"


def test_an_export_carries_the_retained_bytes_not_a_description_of_them(
    store, published, tmp_path
):
    claim, _ = published
    manifest = export_claims(store, tmp_path / "export", [claim])
    for artifact_id in manifest.artifacts:
        row = store.one("SELECT content_hash, stored_path FROM artifacts WHERE id = ?", artifact_id)
        exported = tmp_path / "export" / "artifacts" / row["content_hash"]
        assert exported.read_bytes() == (store.artifact_root / row["stored_path"]).read_bytes()


def test_a_tampered_export_fails_its_own_verification(store, published, tmp_path):
    claim, _ = published
    export_claims(store, tmp_path / "export", [claim])
    target = tmp_path / "export" / f"claims/{claim.replace(':', '_')}.json"
    target.write_text('{"claim": "something else"}', encoding="utf-8")

    ok, problems = verify_export(tmp_path / "export")
    assert not ok
    assert any("checksum mismatch" in problem for problem in problems)


def test_the_whole_corpus_exports(store, world, published, tmp_path):
    manifest = export_corpus(store, tmp_path / "corpus")
    assert len(manifest.claims) >= 3
    ok, problems = verify_export(tmp_path / "corpus")
    assert ok, problems
