"""Migrations, applied in order and recorded.

`STRICT` tables throughout: SQLite's default type affinity would let a risk tier
arrive as an integer and come back as one, and a store that silently reshapes
what it was given is not an evidence ledger. Foreign keys are enforced, so a
sighting cannot outlive the response it observed.

Every table here is append-oriented. The two columns that are ever updated are
an operation's lease and its terminal state, and both are guarded by the
transitions in `newz.control.scheduler`.
"""

from __future__ import annotations

MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (
        1,
        "catalog",
        """
        CREATE TABLE publishers (
            id                 TEXT PRIMARY KEY,
            name               TEXT NOT NULL,
            independence_group TEXT,
            recorded_at        TEXT NOT NULL
        ) STRICT;

        CREATE TABLE sources (
            id           TEXT PRIMARY KEY,
            publisher_id TEXT NOT NULL REFERENCES publishers(id),
            name         TEXT NOT NULL,
            topic        TEXT NOT NULL,
            recorded_at  TEXT NOT NULL
        ) STRICT;

        -- Immutable. A source that changes its role, scope, endpoint, risk floor
        -- or retention terms gets a new revision; the old one stays readable
        -- because edges admitted under it were admitted under those terms.
        CREATE TABLE source_revisions (
            id               TEXT PRIMARY KEY,
            source_id        TEXT NOT NULL REFERENCES sources(id),
            revision         INTEGER NOT NULL,
            endpoint_url     TEXT NOT NULL,
            delivery_kind    TEXT NOT NULL,
            role             TEXT NOT NULL,
            declared_scope   TEXT NOT NULL,
            risk_floor       TEXT NOT NULL,
            retention_policy TEXT NOT NULL,
            expected_mime    TEXT NOT NULL,
            recorded_at      TEXT NOT NULL,
            UNIQUE (source_id, revision)
        ) STRICT;

        CREATE TRIGGER source_revisions_are_immutable
        BEFORE UPDATE ON source_revisions
        BEGIN
            SELECT RAISE(ABORT, 'source revisions are immutable: record a new revision');
        END;

        CREATE TRIGGER source_revisions_are_not_deleted
        BEFORE DELETE ON source_revisions
        BEGIN
            SELECT RAISE(ABORT, 'source revisions are immutable: they are never deleted');
        END;
        """,
    ),
    (
        2,
        "control",
        """
        -- Immutable. An epoch is the exact set of enabled source revisions and
        -- the budget in force; changing either is a new epoch.
        CREATE TABLE diet_epochs (
            id           TEXT PRIMARY KEY,
            epoch        INTEGER NOT NULL UNIQUE,
            budget_json  TEXT NOT NULL,
            note         TEXT NOT NULL,
            activated_at TEXT NOT NULL
        ) STRICT;

        CREATE TABLE diet_epoch_sources (
            epoch_id           TEXT NOT NULL REFERENCES diet_epochs(id),
            source_revision_id TEXT NOT NULL REFERENCES source_revisions(id),
            PRIMARY KEY (epoch_id, source_revision_id)
        ) STRICT;

        CREATE TRIGGER diet_epochs_are_immutable
        BEFORE UPDATE ON diet_epochs
        BEGIN
            SELECT RAISE(ABORT, 'diet epochs are immutable: activate a new epoch');
        END;

        CREATE TRIGGER diet_epoch_sources_are_immutable
        BEFORE UPDATE ON diet_epoch_sources
        BEGIN
            SELECT RAISE(ABORT, 'diet epoch membership is immutable');
        END;

        CREATE TRIGGER diet_epoch_sources_are_not_deleted
        BEFORE DELETE ON diet_epoch_sources
        BEGIN
            SELECT RAISE(ABORT, 'diet epoch membership is immutable');
        END;

        CREATE TABLE operations (
            id                 TEXT PRIMARY KEY,
            kind               TEXT NOT NULL,
            lane               TEXT NOT NULL,
            source_revision_id TEXT NOT NULL REFERENCES source_revisions(id),
            epoch_id           TEXT NOT NULL REFERENCES diet_epochs(id),
            policy_version     TEXT NOT NULL,
            intent             TEXT NOT NULL,
            idempotency_key    TEXT NOT NULL UNIQUE,
            state              TEXT NOT NULL,
            local_day          TEXT NOT NULL,
            created_at         TEXT NOT NULL,
            lease_owner        TEXT,
            lease_expires_at   TEXT,
            terminal_at        TEXT,
            outcome            TEXT
        ) STRICT;

        CREATE INDEX operations_by_day ON operations (local_day, lane);
        CREATE INDEX operations_by_state ON operations (state);

        -- One reservation per operation, taken before any network act.
        CREATE TABLE reservations (
            id           TEXT PRIMARY KEY,
            operation_id TEXT NOT NULL UNIQUE REFERENCES operations(id),
            local_day    TEXT NOT NULL,
            lane         TEXT NOT NULL,
            borrowed_from TEXT,
            created_at   TEXT NOT NULL
        ) STRICT;

        CREATE INDEX reservations_by_day ON reservations (local_day, lane);

        CREATE TABLE audit_events (
            id        TEXT PRIMARY KEY,
            at        TEXT NOT NULL,
            actor     TEXT NOT NULL,
            channel   TEXT NOT NULL,
            action    TEXT NOT NULL,
            target    TEXT NOT NULL,
            reason    TEXT NOT NULL,
            preimage  TEXT NOT NULL,
            result    TEXT NOT NULL
        ) STRICT;

        -- An evidence change and its downstream invalidation commit in one
        -- transaction; the consumer reads from here.
        CREATE TABLE outbox (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            at          TEXT NOT NULL,
            kind        TEXT NOT NULL,
            subject     TEXT NOT NULL,
            payload     TEXT NOT NULL,
            consumed_at TEXT
        ) STRICT;

        CREATE INDEX outbox_unconsumed ON outbox (consumed_at) WHERE consumed_at IS NULL;
        """,
    ),
    (
        3,
        "acquisition",
        """
        CREATE TABLE attempts (
            id             TEXT PRIMARY KEY,
            operation_id   TEXT NOT NULL REFERENCES operations(id),
            url            TEXT NOT NULL,
            started_at     TEXT NOT NULL,
            outcome        TEXT NOT NULL,
            refusal_reason TEXT,
            http_status    INTEGER,
            bytes_read     INTEGER NOT NULL,
            redirects_json TEXT NOT NULL,
            detail         TEXT NOT NULL
        ) STRICT;

        CREATE INDEX attempts_by_operation ON attempts (operation_id);

        CREATE TABLE artifacts (
            id           TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL UNIQUE,
            byte_size    INTEGER NOT NULL,
            media_type   TEXT NOT NULL,
            stored_path  TEXT NOT NULL,
            stored_at    TEXT NOT NULL
        ) STRICT;

        CREATE TABLE responses (
            id              TEXT PRIMARY KEY,
            attempt_id      TEXT NOT NULL UNIQUE REFERENCES attempts(id),
            final_url       TEXT NOT NULL,
            http_status     INTEGER NOT NULL,
            declared_mime   TEXT NOT NULL,
            normalized_mime TEXT NOT NULL,
            content_hash    TEXT NOT NULL,
            byte_size       INTEGER NOT NULL,
            headers_json    TEXT NOT NULL,
            artifact_id     TEXT REFERENCES artifacts(id),
            recorded_at     TEXT NOT NULL
        ) STRICT;

        -- One recorded observation of a body at a source, revision, and time.
        -- Duplicate bodies share an artifact and never share a sighting.
        CREATE TABLE sightings (
            id                 TEXT PRIMARY KEY,
            response_id        TEXT NOT NULL REFERENCES responses(id),
            source_revision_id TEXT NOT NULL REFERENCES source_revisions(id),
            artifact_id        TEXT NOT NULL REFERENCES artifacts(id),
            observed_at        TEXT NOT NULL
        ) STRICT;

        CREATE INDEX sightings_by_artifact ON sightings (artifact_id);

        -- Operational standing only. Never an epistemic reliability score.
        CREATE TABLE instruction_observations (
            id                 TEXT PRIMARY KEY,
            source_revision_id TEXT NOT NULL REFERENCES source_revisions(id),
            artifact_id        TEXT NOT NULL REFERENCES artifacts(id),
            marker             TEXT NOT NULL,
            excerpt_hash       TEXT NOT NULL,
            offset_start       INTEGER NOT NULL,
            offset_end         INTEGER NOT NULL,
            observed_at        TEXT NOT NULL
        ) STRICT;

        CREATE INDEX instruction_observations_by_source
            ON instruction_observations (source_revision_id);

        CREATE TRIGGER artifacts_are_immutable
        BEFORE UPDATE ON artifacts
        BEGIN
            SELECT RAISE(ABORT, 'artifacts are immutable');
        END;

        CREATE TRIGGER responses_are_immutable
        BEFORE UPDATE ON responses
        BEGIN
            SELECT RAISE(ABORT, 'responses are immutable: corrections append');
        END;

        CREATE TRIGGER sightings_are_immutable
        BEFORE UPDATE ON sightings
        BEGIN
            SELECT RAISE(ABORT, 'sightings are immutable');
        END;
        """,
    ),
    (
        4,
        "preservation",
        """
        -- One run of one parser over one artifact. Immutable: a re-parse under a
        -- new parser version is a new execution, so a segmentation can always be
        -- attributed to the code that produced it.
        CREATE TABLE parse_executions (
            id              TEXT PRIMARY KEY,
            artifact_id     TEXT NOT NULL REFERENCES artifacts(id),
            parser_name     TEXT NOT NULL,
            parser_version  TEXT NOT NULL,
            normalized_mime TEXT NOT NULL,
            text_hash       TEXT NOT NULL,
            segment_count   INTEGER NOT NULL,
            failures_json   TEXT NOT NULL,
            executed_at     TEXT NOT NULL,
            UNIQUE (artifact_id, parser_name, parser_version)
        ) STRICT;

        -- Segment ids are derived from the artifact, the ordinal and the text,
        -- so the same bytes read the same way yield the same segment, and a
        -- segment whose text changed is a different segment rather than the
        -- same one saying something else.
        CREATE TABLE segments (
            id          TEXT PRIMARY KEY,
            artifact_id TEXT NOT NULL REFERENCES artifacts(id),
            ordinal     INTEGER NOT NULL,
            kind        TEXT NOT NULL,
            locator     TEXT NOT NULL,
            text        TEXT NOT NULL
        ) STRICT;

        CREATE INDEX segments_by_artifact ON segments (artifact_id, ordinal);

        CREATE TRIGGER parse_executions_are_immutable
        BEFORE UPDATE ON parse_executions
        BEGIN
            SELECT RAISE(ABORT, 'parse executions are immutable: record a new execution');
        END;

        CREATE TRIGGER segments_are_immutable
        BEFORE UPDATE ON segments
        BEGIN
            SELECT RAISE(ABORT, 'segments are immutable: a changed segment is a new segment');
        END;
        """,
    ),
)
