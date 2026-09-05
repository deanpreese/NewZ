"""Catalog validation and the diet epoch dry run."""

from __future__ import annotations

import pytest

from newz.catalog import epochs
from newz.catalog.sources import CatalogError, SourceRevision, validate_revision
from newz.control.budget import DailyBudget
from newz.domain.enums import DeliveryKind, RetentionPolicy, RiskTier, SourceRole
from tests import canaries


def revision(**overrides) -> SourceRevision:
    base = dict(
        id="srcrev:example-1",
        source_id="source:example",
        revision=1,
        endpoint_url="https://example.org/feed",
        delivery_kind=DeliveryKind.PAGE,
        role=SourceRole.PRIMARY_RECORD,
        declared_scope="records of the thing it records",
        risk_floor=RiskTier.R1,
        retention_policy=RetentionPolicy.FULL_TEXT,
        expected_mime="text/html",
    )
    return SourceRevision(**{**base, **overrides})


def test_a_well_formed_revision_validates():
    validate_revision(revision())


def test_validation_reports_every_problem_at_once():
    with pytest.raises(CatalogError) as raised:
        validate_revision(
            revision(
                id="not an id",
                revision=0,
                declared_scope="  ",
                expected_mime="",
                endpoint_url="ftp://example.org/x",
            )
        )
    assert len(raised.value.problems) == 5


def test_an_endpoint_that_the_fetcher_would_refuse_is_refused_at_the_catalog():
    for url in ("http://user:pw@example.org/", "https://example.org:9999/", "not-a-url"):
        with pytest.raises(CatalogError, match="endpoint refused"):
            validate_revision(revision(endpoint_url=url))


def test_an_adjudicator_must_say_what_it_settles():
    with pytest.raises(CatalogError, match="declared scope must say"):
        validate_revision(revision(role=SourceRole.ADJUDICATOR, declared_scope="courts"))
    validate_revision(
        revision(role=SourceRole.ADJUDICATOR, declared_scope="civil matters in the district")
    )


def test_retention_decides_whether_material_can_ever_be_evidence():
    assert revision(retention_policy=RetentionPolicy.FULL_TEXT).may_retain_evidence
    assert not revision(retention_policy=RetentionPolicy.METADATA_ONLY).may_retain_evidence
    assert not revision(retention_policy=RetentionPolicy.LEAD_ONLY).may_retain_evidence


def test_the_dry_run_shows_the_exact_effect_before_activation(store):
    canaries.install(store)
    ids = [c.revision.id for c in canaries.CANARIES]
    plan = epochs.plan(store, ids, DailyBudget())
    assert plan.epoch == 1
    assert len(plan.added) == 4
    assert plan.removed == ()
    assert plan.is_activatable
    rendered = plan.render()
    assert "3 discovery, 5 verification, 2 correction" in rendered
    assert "+ srcrev:harbour-uap-1" in rendered
    # Nothing was written by looking.
    assert store.one("SELECT COUNT(*) AS n FROM diet_epochs")["n"] == 0


def test_the_dry_run_names_what_a_second_epoch_would_remove(catalog):
    keep = [c.revision.id for c in canaries.CANARIES[:2]]
    plan = epochs.plan(catalog, keep, DailyBudget())
    assert plan.epoch == 2
    assert len(plan.removed) == 2
    assert "- srcrev:registry-occurrences-1" in plan.render()


def test_an_epoch_naming_an_unknown_revision_is_refused(store):
    canaries.install(store)
    plan = epochs.plan(store, ["srcrev:absent-1"], DailyBudget())
    assert not plan.is_activatable
    assert "unknown source revision" in plan.render()
    with pytest.raises(ValueError, match="not activatable"):
        epochs.activate(store, plan, "epoch:1", "note", "operator:dean")


def test_an_empty_epoch_is_refused_because_it_would_stop_acquisition_silently(store):
    plan = epochs.plan(store, [], DailyBudget())
    assert not plan.is_activatable
    assert "stop acquisition silently" in plan.render()


def test_a_budget_that_inverts_the_lane_rule_is_refused(store):
    canaries.install(store)
    plan = epochs.plan(
        store,
        [c.revision.id for c in canaries.CANARIES],
        DailyBudget(discovery=6, verification=2, correction=2),
    )
    assert not plan.is_activatable
    assert "inverts the rule" in plan.render()


def test_activation_records_an_audit_event_with_its_preimage(catalog):
    row = catalog.one("SELECT * FROM audit_events WHERE action = 'activate_diet_epoch'")
    assert row["actor"] == "operator:dean"
    assert row["channel"] == "command"
    assert "srcrev:harbour-uap-1" in row["preimage"]
    assert "4 sources" in row["result"]


def test_the_epoch_reads_back_as_what_was_activated(catalog):
    record = epochs.as_record(catalog, "epoch:1")
    assert record["epoch"] == 1
    assert record["budget"] == {"discovery": 3, "verification": 5, "correction": 2}
    assert len(record["sources"]) == 4
