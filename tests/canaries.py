"""The four offline canary sources of Gate 1.

Two HTML, one PDF, and one attribution-only claimant source. They are built from
the Phase 0 fixture corpus rather than from new strings, so the bytes that pass
through the provenance spine are the same bytes the evidence rules were written
against.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from newz.catalog.sources import Publisher, Source, SourceRevision
from newz.domain.enums import DeliveryKind, RetentionPolicy, RiskTier, SourceRole
from tests.transport import FixtureTransport

CORPUS = Path(__file__).parent / "fixtures" / "corpus"


@dataclass(frozen=True, slots=True)
class Canary:
    publisher: Publisher
    source: Source
    revision: SourceRevision
    fixture: str
    content_type: str


CANARIES: tuple[Canary, ...] = (
    Canary(
        publisher=Publisher(id="publisher:harbour", name="Harbour Dispatch"),
        source=Source(
            id="source:harbour-uap",
            publisher_id="publisher:harbour",
            name="Harbour Dispatch — aviation desk",
            topic="uap_and_aerospace_anomalies",
        ),
        revision=SourceRevision(
            id="srcrev:harbour-uap-1",
            source_id="source:harbour-uap",
            revision=1,
            endpoint_url="https://harbour.example/uap/coral-ridge",
            delivery_kind=DeliveryKind.PAGE,
            role=SourceRole.FIRSTHAND_WITNESS,
            declared_scope="first-person aviation sighting accounts",
            risk_floor=RiskTier.R1,
            retention_policy=RetentionPolicy.FULL_TEXT,
            expected_mime="text/html",
        ),
        fixture="html/witness_report.html",
        content_type="text/html; charset=utf-8",
    ),
    Canary(
        publisher=Publisher(
            id="publisher:meridian",
            name="Meridian Wire",
            independence_group="grp:meridian-holdings",
        ),
        source=Source(
            id="source:meridian-wire",
            publisher_id="publisher:meridian",
            name="Meridian Wire — syndication feed",
            topic="uap_and_aerospace_anomalies",
        ),
        revision=SourceRevision(
            id="srcrev:meridian-wire-1",
            source_id="source:meridian-wire",
            revision=1,
            endpoint_url="https://meridian.example/wire/coral-ridge",
            delivery_kind=DeliveryKind.FEED,
            role=SourceRole.CLAIMANT,
            declared_scope="syndicated wire copy",
            risk_floor=RiskTier.R1,
            retention_policy=RetentionPolicy.FULL_TEXT,
            expected_mime="text/html",
        ),
        fixture="html/syndicated_copy.html",
        content_type="text/html; charset=utf-8",
    ),
    Canary(
        publisher=Publisher(id="publisher:registry", name="National Aviation Safety Registry"),
        source=Source(
            id="source:registry-occurrences",
            publisher_id="publisher:registry",
            name="Occurrence record search",
            topic="declassified_material_and_historical_secrecy",
        ),
        revision=SourceRevision(
            id="srcrev:registry-occurrences-1",
            source_id="source:registry-occurrences",
            revision=1,
            endpoint_url="https://registry.example/occurrences/2026-0311-CR.pdf",
            delivery_kind=DeliveryKind.DOCUMENT,
            role=SourceRole.PRIMARY_RECORD,
            declared_scope="civil aviation occurrence records for the national sector",
            risk_floor=RiskTier.R1,
            retention_policy=RetentionPolicy.FULL_TEXT,
            expected_mime="application/pdf",
        ),
        fixture="pdf/registry_record.pdf",
        content_type="application/pdf",
    ),
    Canary(
        publisher=Publisher(id="publisher:ridge", name="Ridgeline Research Collective"),
        source=Source(
            id="source:ridge-notes",
            publisher_id="publisher:ridge",
            name="Ridgeline field notes",
            topic="psi_and_consciousness_claims",
        ),
        revision=SourceRevision(
            id="srcrev:ridge-notes-1",
            source_id="source:ridge-notes",
            revision=1,
            endpoint_url="https://ridge.example/notes/session-41",
            delivery_kind=DeliveryKind.PAGE,
            role=SourceRole.CLAIMANT,
            declared_scope="the collective's own field notes",
            risk_floor=RiskTier.R1,
            retention_policy=RetentionPolicy.FULL_TEXT,
            expected_mime="text/html",
        ),
        fixture="html/prompt_injection.html",
        content_type="text/html; charset=utf-8",
    ),
)


def transport_for(canaries=CANARIES) -> FixtureTransport:
    transport = FixtureTransport()
    for canary in canaries:
        transport.serve_bytes(
            canary.revision.endpoint_url,
            (CORPUS / canary.fixture).read_bytes(),
            canary.content_type,
        )
    return transport


def install(store, canaries=CANARIES) -> None:
    """Write the canary catalog into a store."""
    with store.write() as connection:
        for canary in canaries:
            connection.execute(
                "INSERT OR IGNORE INTO publishers (id, name, independence_group, recorded_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (
                    canary.publisher.id,
                    canary.publisher.name,
                    canary.publisher.independence_group,
                ),
            )
            connection.execute(
                "INSERT OR IGNORE INTO sources (id, publisher_id, name, topic, recorded_at) "
                "VALUES (?, ?, ?, ?, datetime('now'))",
                (
                    canary.source.id,
                    canary.source.publisher_id,
                    canary.source.name,
                    canary.source.topic,
                ),
            )
            revision = canary.revision
            connection.execute(
                "INSERT OR IGNORE INTO source_revisions (id, source_id, revision, endpoint_url, "
                "delivery_kind, role, declared_scope, risk_floor, retention_policy, expected_mime, "
                "recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    revision.id,
                    revision.source_id,
                    revision.revision,
                    revision.endpoint_url,
                    revision.delivery_kind.value,
                    revision.role.value,
                    revision.declared_scope,
                    revision.risk_floor.value,
                    revision.retention_policy.value,
                    revision.expected_mime,
                ),
            )
