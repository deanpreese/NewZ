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
    (
        5,
        "semantics",
        """
        -- One model call over one parse. The raw proposal is retained as an
        -- artifact like any other body: SPEC 6 keeps the operation's own
        -- material inspectable, and a proposal nobody can read back is a
        -- decision nobody can replay.
        CREATE TABLE extraction_runs (
            id                 TEXT PRIMARY KEY,
            artifact_id        TEXT NOT NULL REFERENCES artifacts(id),
            parse_execution_id TEXT NOT NULL REFERENCES parse_executions(id),
            model              TEXT NOT NULL,
            prompt_hash        TEXT NOT NULL,
            raw_artifact_id    TEXT NOT NULL REFERENCES artifacts(id),
            proposed           INTEGER NOT NULL,
            accepted           INTEGER NOT NULL,
            refusals_json      TEXT NOT NULL,
            executed_at        TEXT NOT NULL
        ) STRICT;

        -- An assertion always points at a verified span. There is no column
        -- here for a role or a risk: those live on the source revision and the
        -- edge, where a model cannot reach them.
        CREATE TABLE assertions (
            id                 TEXT PRIMARY KEY,
            extraction_run_id  TEXT NOT NULL REFERENCES extraction_runs(id),
            artifact_id        TEXT NOT NULL REFERENCES artifacts(id),
            segment_id         TEXT NOT NULL REFERENCES segments(id),
            source_revision_id TEXT NOT NULL REFERENCES source_revisions(id),
            kind               TEXT NOT NULL,
            quote              TEXT NOT NULL,
            offset_start       INTEGER NOT NULL,
            offset_end         INTEGER NOT NULL,
            locator            TEXT NOT NULL,
            summary            TEXT NOT NULL,
            live               INTEGER NOT NULL DEFAULT 1,
            recorded_at        TEXT NOT NULL
        ) STRICT;

        CREATE INDEX assertions_by_artifact ON assertions (artifact_id);

        -- Disambiguation data only. SPEC 10.1: a person is an address in the
        -- graph, never a dossier in it, so there is deliberately no column here
        -- for a claim, an allegation, an assessment, or a count of anything.
        CREATE TABLE entities (
            id             TEXT PRIMARY KEY,
            name           TEXT NOT NULL UNIQUE,
            kind           TEXT NOT NULL,
            disambiguation TEXT NOT NULL,
            recorded_at    TEXT NOT NULL
        ) STRICT;

        CREATE TABLE assertion_entities (
            assertion_id TEXT NOT NULL REFERENCES assertions(id),
            entity_id    TEXT NOT NULL REFERENCES entities(id),
            PRIMARY KEY (assertion_id, entity_id)
        ) STRICT;

        CREATE TABLE claims (
            id                 TEXT PRIMARY KEY,
            kind               TEXT NOT NULL,
            wording            TEXT NOT NULL,
            risk               TEXT,
            resolution_horizon TEXT,
            resolver           TEXT,
            withdrawn          INTEGER NOT NULL DEFAULT 0,
            recorded_at        TEXT NOT NULL
        ) STRICT;

        CREATE TABLE claim_aliases (
            claim_id TEXT NOT NULL REFERENCES claims(id),
            alias    TEXT NOT NULL,
            PRIMARY KEY (claim_id, alias)
        ) STRICT;

        -- Where a claim came from. Not evidence for it: a claim's origin says
        -- who raised the question, and the edges say what answers it.
        CREATE TABLE claim_origins (
            claim_id          TEXT NOT NULL REFERENCES claims(id),
            extraction_run_id TEXT NOT NULL REFERENCES extraction_runs(id),
            artifact_id       TEXT NOT NULL REFERENCES artifacts(id),
            segment_id        TEXT REFERENCES segments(id),
            quote             TEXT NOT NULL,
            PRIMARY KEY (claim_id, extraction_run_id)
        ) STRICT;

        CREATE TRIGGER assertions_are_immutable_except_liveness
        BEFORE UPDATE OF id, artifact_id, segment_id, kind, quote, offset_start,
                         offset_end, source_revision_id ON assertions
        BEGIN
            SELECT RAISE(ABORT, 'assertions are immutable: withdraw by setting live = 0');
        END;

        CREATE TRIGGER extraction_runs_are_immutable
        BEFORE UPDATE ON extraction_runs
        BEGIN
            SELECT RAISE(ABORT, 'extraction runs are immutable: record a new run');
        END;
        """,
    ),
    (
        6,
        "evidence",
        """
        -- A basis is the upstream origin an edge rests on. `resolved` is basis
        -- IDENTITY: the origin is nameable and stable, even when it is a single
        -- unnamed witness reached through one publication. Independence is a
        -- separate, pairwise property and is deliberately not a column here.
        CREATE TABLE bases (
            id                 TEXT PRIMARY KEY,
            origin_kind        TEXT NOT NULL,
            origin_identifier  TEXT NOT NULL,
            resolved           INTEGER NOT NULL,
            independence_group TEXT,
            recorded_at        TEXT NOT NULL
        ) STRICT;

        -- Publication lineage. If this basis is downstream of that one they are
        -- the same underlying origin, and no justification makes them two.
        CREATE TABLE basis_derivations (
            basis_id              TEXT NOT NULL REFERENCES bases(id),
            derived_from_basis_id TEXT NOT NULL REFERENCES bases(id),
            reason                TEXT NOT NULL,
            recorded_at           TEXT NOT NULL,
            PRIMARY KEY (basis_id, derived_from_basis_id)
        ) STRICT;

        -- The operator correcting basis identity, append-only and reasoned.
        CREATE TABLE basis_corrections (
            id          TEXT PRIMARY KEY,
            basis_id    TEXT NOT NULL REFERENCES bases(id),
            actor       TEXT NOT NULL,
            reason      TEXT NOT NULL,
            preimage    TEXT NOT NULL,
            result      TEXT NOT NULL,
            corrected_at TEXT NOT NULL
        ) STRICT;

        CREATE TABLE independence_claims (
            id              TEXT PRIMARY KEY,
            basis_a         TEXT NOT NULL REFERENCES bases(id),
            basis_b         TEXT NOT NULL REFERENCES bases(id),
            justification   TEXT NOT NULL,
            evidence        TEXT NOT NULL,
            operator_actor  TEXT,
            operator_reason TEXT,
            recorded_at     TEXT NOT NULL,
            UNIQUE (basis_a, basis_b)
        ) STRICT;

        -- Append-only. A withdrawal is a later event with live = 0, never an
        -- edit, so an admitted edge and its later withdrawal both stay readable.
        CREATE TABLE edge_events (
            id              TEXT PRIMARY KEY,
            assertion_id    TEXT NOT NULL REFERENCES assertions(id),
            claim_id        TEXT NOT NULL REFERENCES claims(id),
            relation        TEXT NOT NULL,
            basis_id        TEXT NOT NULL REFERENCES bases(id),
            role            TEXT NOT NULL,
            assertion_kind  TEXT NOT NULL,
            risk            TEXT,
            policy_version  TEXT,
            admitted        INTEGER NOT NULL,
            live            INTEGER NOT NULL DEFAULT 1,
            refusal_reason  TEXT,
            declared_scope  TEXT NOT NULL,
            topic           TEXT NOT NULL,
            adjudicative_scope_covers_claim INTEGER,
            recorded_at     TEXT NOT NULL
        ) STRICT;

        CREATE INDEX edge_events_by_claim ON edge_events (claim_id);

        -- One row per named predicate, with its inputs, so an admission replays.
        CREATE TABLE predicate_attestations (
            edge_event_id TEXT NOT NULL REFERENCES edge_events(id),
            predicate     TEXT NOT NULL,
            held          INTEGER NOT NULL,
            inputs_json   TEXT NOT NULL,
            PRIMARY KEY (edge_event_id, predicate)
        ) STRICT;

        CREATE TABLE tasks (
            id              TEXT PRIMARY KEY,
            claim_id        TEXT NOT NULL REFERENCES claims(id),
            lane            TEXT NOT NULL,
            state           TEXT NOT NULL,
            owner           TEXT NOT NULL,
            reason          TEXT NOT NULL,
            due             TEXT NOT NULL,
            retry_budget    INTEGER NOT NULL DEFAULT 0,
            state_reason    TEXT NOT NULL DEFAULT '',
            expected_record TEXT NOT NULL DEFAULT '',
            repository      TEXT NOT NULL DEFAULT '',
            query           TEXT NOT NULL DEFAULT '',
            time_window     TEXT NOT NULL DEFAULT '',
            searched_scope  TEXT NOT NULL DEFAULT '',
            recorded_at     TEXT NOT NULL
        ) STRICT;

        CREATE INDEX tasks_by_claim ON tasks (claim_id, lane);

        -- Append-only history. The current assessment is the newest row, and an
        -- assessment never outlives the policy version that produced it.
        CREATE TABLE assessments (
            id                     TEXT PRIMARY KEY,
            claim_id               TEXT NOT NULL REFERENCES claims(id),
            state                  TEXT NOT NULL,
            supporting_bases       INTEGER NOT NULL,
            contradicting_bases    INTEGER NOT NULL,
            policy_version         TEXT NOT NULL,
            code_version           TEXT NOT NULL,
            explanation            TEXT NOT NULL,
            blocked_lanes_json     TEXT NOT NULL,
            countable_edge_ids_json TEXT NOT NULL,
            derived_at             TEXT NOT NULL
        ) STRICT;

        CREATE INDEX assessments_by_claim ON assessments (claim_id, derived_at);

        CREATE TRIGGER edge_events_are_immutable_except_liveness
        BEFORE UPDATE OF id, assertion_id, claim_id, relation, basis_id, role,
                         assertion_kind, admitted, policy_version ON edge_events
        BEGIN
            SELECT RAISE(ABORT, 'edge events are immutable: withdraw by setting live = 0');
        END;

        CREATE TRIGGER assessments_are_immutable
        BEFORE UPDATE ON assessments
        BEGIN
            SELECT RAISE(ABORT, 'assessments are append-only: derive a new one');
        END;

        CREATE TRIGGER bases_keep_their_identity
        BEFORE UPDATE OF id, origin_kind, origin_identifier ON bases
        BEGIN
            SELECT RAISE(ABORT, 'basis identity changes through a recorded correction');
        END;
        """,
    ),
)
