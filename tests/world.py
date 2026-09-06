"""A small world built the long way, for Gate 2.

Seven sources are fetched through the scheduler, parsed, extracted from, and
turned into bases, edges and assessments — every step through the real code
path, with a stub model standing in only for the far side of the local endpoint.
The quotations the stub proposes are located in the actual parsed segments at
build time, so a fixture whose text drifts fails loudly here rather than
producing a world that quietly means something else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from newz.acquisition.run import acquire
from newz.catalog import epochs
from newz.catalog.sources import Publisher, Source, SourceRevision
from newz.control.budget import DailyBudget
from newz.control.scheduler import reserve
from newz.domain.enums import (
    DeliveryKind,
    EvidenceLane,
    OperationKind,
    ReadLane,
    RetentionPolicy,
    RiskTier,
    SourceRole,
    TaskState,
)
from newz.extract.run import extract
from newz.parse.store import parse_artifact, record_parse, segments_for
from tests.canaries import Canary
from tests.model_stub import StubModel, assertion, claim, extraction
from tests.transport import FixtureTransport

CORPUS = Path(__file__).parent / "fixtures" / "corpus"
#: The pipeline below runs against the real clock -- every row it writes is
#: stamped with SQLite's `datetime('now')` -- so the day it labels its
#: reservations with has to be the same day, or a report that counts
#: reservations by their local label and fetches by their timestamp sees a
#: pipeline that reserved and never read. A frozen date here agreed with the
#: clock only by coincidence, and only until the date rolled.
DAY = datetime.now().date().isoformat()

LANES = (
    ReadLane.DISCOVERY,
    ReadLane.DISCOVERY,
    ReadLane.DISCOVERY,
    ReadLane.VERIFICATION,
    ReadLane.VERIFICATION,
    ReadLane.VERIFICATION,
    ReadLane.VERIFICATION,
    ReadLane.VERIFICATION,
    ReadLane.CORRECTION,
)


def _canary(
    key: str,
    publisher: str,
    role: SourceRole,
    fixture: str,
    content_type: str,
    scope: str,
    topic: str = "metascience_methods_and_replication",
    group: str | None = None,
) -> Canary:
    return Canary(
        publisher=Publisher(id=f"publisher:{key}", name=publisher, independence_group=group),
        source=Source(
            id=f"source:{key}", publisher_id=f"publisher:{key}", name=publisher, topic=topic
        ),
        revision=SourceRevision(
            id=f"srcrev:{key}-1",
            source_id=f"source:{key}",
            revision=1,
            endpoint_url=f"https://{key}.example/document",
            delivery_kind=DeliveryKind.PAGE,
            role=role,
            declared_scope=scope,
            risk_floor=RiskTier.R1,
            retention_policy=RetentionPolicy.FULL_TEXT,
            expected_mime=content_type.split(";")[0],
        ),
        fixture=fixture,
        content_type=content_type,
    )


SOURCES: tuple[Canary, ...] = (
    _canary(
        "harbour", "Harbour Dispatch", SourceRole.FIRSTHAND_WITNESS,
        "html/witness_report.html", "text/html; charset=utf-8",
        "first-person aviation sighting accounts", "uap_and_aerospace_anomalies",
    ),
    _canary(
        "meridian", "Meridian Wire", SourceRole.CLAIMANT,
        "html/syndicated_copy.html", "text/html; charset=utf-8",
        "syndicated wire copy", "uap_and_aerospace_anomalies",
        group="grp:meridian-holdings",
    ),
    _canary(
        "registry", "National Aviation Safety Registry", SourceRole.PRIMARY_RECORD,
        "pdf/registry_record.pdf", "application/pdf",
        "civil aviation occurrence records for the national sector",
        "uap_and_aerospace_anomalies",
    ),
    _canary(
        "patents", "Patent Office", SourceRole.PRIMARY_RECORD,
        "text/patent_abstract.txt", "text/plain",
        "granted patents and their examination record",
        "alternative_physics_and_energy",
    ),
    _canary(
        "complaint", "Northern District filings", SourceRole.PRIMARY_RECORD,
        "text/complaint_filing.txt", "text/plain",
        "civil filings received by the district",
    ),
    _canary(
        "court", "Northern District Court", SourceRole.ADJUDICATOR,
        "structured/docket.json", "application/json",
        "civil matters within the Northern District",
    ),
    _canary(
        "ardenne", "Ardenne Institute", SourceRole.EMPIRICAL_STUDY,
        "text/replication_failure.txt", "text/plain",
        "registered replication studies in metrology",
    ),
    _canary(
        "kettleby", "Kettleby Metrology", SourceRole.EMPIRICAL_STUDY,
        "structured/measurements.csv", "text/csv",
        "instrument measurement runs under registered protocols",
    ),
    _canary(
        "journal", "Journal of Applied Field Metrology", SourceRole.PRIMARY_RECORD,
        "text/retraction_notice.txt", "text/plain",
        "the journal's own record of what it has published and withdrawn",
    ),
)


@dataclass
class Ingested:
    key: str
    revision: SourceRevision
    artifact_id: str
    execution_id: str
    segments: tuple
    assertions: dict[str, str] = field(default_factory=dict)
    claims: dict[str, str] = field(default_factory=dict)


@dataclass
class World:
    store: object
    sources: dict[str, Ingested] = field(default_factory=dict)

    def assertion(self, key: str, name: str) -> str:
        return self.sources[key].assertions[name]

    def artifact(self, key: str) -> str:
        return self.sources[key].artifact_id

    def claim(self, key: str, name: str) -> str:
        return self.sources[key].claims[name]


def transport_for() -> FixtureTransport:
    transport = FixtureTransport()
    for canary in SOURCES:
        transport.serve_bytes(
            canary.revision.endpoint_url,
            (CORPUS / canary.fixture).read_bytes(),
            canary.content_type,
        )
    return transport


def install(store) -> None:
    with store.write() as connection:
        for canary in SOURCES:
            connection.execute(
                "INSERT OR IGNORE INTO publishers (id, name, independence_group, recorded_at) "
                "VALUES (?, ?, ?, datetime('now'))",
                (canary.publisher.id, canary.publisher.name, canary.publisher.independence_group),
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
                "delivery_kind, role, declared_scope, risk_floor, retention_policy, "
                "expected_mime, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
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
    plan = epochs.plan(store, [c.revision.id for c in SOURCES], DailyBudget())
    epochs.activate(store, plan, "epoch:1", "the Gate 2 world", "operator:dean")


#: Claims each source is asked to propose: a name, a claim kind, the wording,
#: and the fragment the claim arises from. Claims enter the registry through
#: extraction like everything else — Gate 3 asks that no step need a manual edit.
CLAIM_PROPOSALS: dict[str, tuple[tuple[str, str, str, str], ...]] = {
    "registry": (
        (
            "radar",
            "event_or_observation",
            "An uncorrelated radar return accompanied the Coral Ridge sighting of 2 March 2026.",
            "Radar correlation: none found in the recorded window.",
        ),
    ),
    "kettleby": (
        (
            "signature",
            "measurement_or_association",
            "The RX-9 sensor array shows a thermal signature above baseline under protocol conditions.",
            "run_id=RX9-A-001, laboratory=Kettleby Metrology",
        ),
    ),
    "complaint": (
        (
            "falsified",
            "identity_or_wrongdoing_allegation",
            "Meridian Instruments Inc. knowingly falsified calibration records for the RX-9 sensor.",
            "defendant knowingly falsified calibration records",
        ),
    ),
}

#: What each source is asked to extract: a name for the assertion, its kind, and
#: a fragment that must appear exactly once in the parsed segments.
EXTRACTIONS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "harbour": (
        ("sighting", "testimony", "It held station off the right wing"),
    ),
    "meridian": (
        ("sighting", "testimony", "It held station off the right wing"),
    ),
    "registry": (
        ("no_radar", "documented_event", "Radar correlation: none found in the recorded window."),
    ),
    "patents": (
        ("thrust", "documented_event", "the apparatus is said to produce a net directional thrust"),
    ),
    "complaint": (
        ("alleges", "allegation", "defendant knowingly falsified calibration records"),
    ),
    "court": (
        ("judgment", "documented_event", "The court finds no evidence that calibration records were falsified."),
    ),
    "ardenne": (
        ("no_effect", "measurement", "we observe an effect of -0.01 (95% CI -0.15 to 0.13), consistent with no effect"),
    ),
    "kettleby": (
        ("effect", "measurement", "run_id=RX9-A-001, laboratory=Kettleby Metrology"),
    ),
    "journal": (
        ("retracted", "documented_event", "The editors retract \"Anomalous thermal signature in the RX-9 sensor array\""),
    ),
}


def build(store) -> World:
    """Fetch, parse and extract every source, the long way through."""
    install(store)
    transport = transport_for()
    world = World(store=store)

    for index, canary in enumerate(SOURCES):
        key = canary.source.id.split(":", 1)[1]
        operation = reserve(
            store,
            operation_id=f"operation:{key}",
            reservation_id=f"reservation:{key}",
            kind=OperationKind.FETCH,
            lane=LANES[index],
            source_revision_id=canary.revision.id,
            epoch_id="epoch:1",
            policy_version="1.0.0",
            intent=f"read {key}",
            idempotency_key=f"{DAY}:{key}",
            local_day=DAY,
        )
        record = acquire(store, operation, canary.revision, transport)
        assert record.retained, (key, record.refusal)

        # In-process on purpose. This fixture is the pipeline nine other test
        # files build on, and it is about what the pipeline produces rather
        # than about which interpreter parsed it. Spawning a worker per source
        # per test file buys nothing here; the boundary itself is tested in
        # `tests/test_isolate.py`, which is where it belongs.
        result = parse_artifact(store, record.artifact_id, isolated=False)
        execution = record_parse(store, result, f"parse:{key}")
        segments = segments_for(store, record.artifact_id)

        wanted = EXTRACTIONS[key]
        blocks = []
        for name, kind, fragment in wanted:
            exact = _exact_quote(segments, fragment)
            assert exact, f"{key}: {fragment!r} is not in the parsed segments exactly once"
            blocks.append(assertion(kind, exact, f"{key}:{name}"))

        proposed_claims = CLAIM_PROPOSALS.get(key, ())
        for _, kind, wording, fragment in proposed_claims:
            exact = _exact_quote(segments, fragment)
            assert exact, f"{key}: claim quote {fragment!r} is not in the segments exactly once"
            blocks.append(claim(kind, wording, exact))

        extracted = extract(
            store,
            run_id=f"run:{key}",
            artifact_id=record.artifact_id,
            parse_execution_id=execution,
            source_revision_id=canary.revision.id,
            client=StubModel(reply=extraction(*blocks)),
            segments=segments,
        )
        assert extracted.accepted == len(wanted) + len(proposed_claims), (key, extracted.refusals)

        world.sources[key] = Ingested(
            key=key,
            revision=canary.revision,
            artifact_id=record.artifact_id,
            execution_id=execution,
            segments=segments,
            assertions=dict(zip([n for n, _, _ in wanted], extracted.assertion_ids, strict=True)),
            claims=dict(
                zip([n for n, _, _, _ in proposed_claims], extracted.claim_ids, strict=True)
            ),
        )
    return world


def _exact_quote(segments, fragment: str) -> str:
    """The fragment as it actually appears, if it appears exactly once."""
    hits = [segment for segment in segments if fragment in segment.text]
    if len(hits) != 1 or hits[0].text.count(fragment) != 1:
        return ""
    return fragment


def add_claim(store, claim_id: str, kind: str, wording: str, risk: str | None = None) -> str:
    with store.write() as connection:
        connection.execute(
            "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
            "withdrawn, recorded_at) VALUES (?, ?, ?, ?, NULL, NULL, 0, datetime('now'))",
            (claim_id, kind, wording, risk),
        )
    return claim_id


def add_task(
    store,
    task_id: str,
    claim_id: str,
    lane: EvidenceLane,
    state: TaskState,
    described: bool = True,
    state_reason: str = "",
) -> None:
    fields = ("the record sought", "the competent repository", "the query", "2026", "the scope")
    with store.write() as connection:
        connection.execute(
            "INSERT INTO tasks (id, claim_id, lane, state, owner, reason, due, retry_budget, "
            "state_reason, expected_record, repository, query, time_window, searched_scope, "
            "recorded_at) VALUES (?, ?, ?, ?, 'worker:evidence', 'gate 2', "
            "'2026-10-01T00:00:00Z', 0, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                task_id,
                claim_id,
                lane.value,
                state.value,
                state_reason,
                *(fields if described else ("", "", "", "", "")),
            ),
        )
