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
    (
        7,
        "research",
        """
        -- A bounded programme of claims, questions and exit conditions. An
        -- investigation that cannot say what would close it is a subscription.
        CREATE TABLE investigations (
            id                  TEXT PRIMARY KEY,
            question            TEXT NOT NULL,
            rationale           TEXT NOT NULL,
            priority            INTEGER NOT NULL,
            exit_conditions     TEXT NOT NULL,
            closing_observation TEXT NOT NULL,
            origin              TEXT NOT NULL,
            state               TEXT NOT NULL,
            opened_at           TEXT NOT NULL,
            closed_at           TEXT,
            closed_reason       TEXT
        ) STRICT;

        CREATE TABLE investigation_claims (
            investigation_id TEXT NOT NULL REFERENCES investigations(id),
            claim_id         TEXT NOT NULL REFERENCES claims(id),
            added_at         TEXT NOT NULL,
            PRIMARY KEY (investigation_id, claim_id)
        ) STRICT;

        -- A lead is a place worth looking. It is never evidence: SPEC 6.2 keeps
        -- feed entries and search results as leads until a full artifact is
        -- retained, and a directed search produces nothing stronger.
        CREATE TABLE leads (
            id                 TEXT PRIMARY KEY,
            claim_id           TEXT REFERENCES claims(id),
            task_id            TEXT REFERENCES tasks(id),
            adapter            TEXT NOT NULL,
            url                TEXT NOT NULL,
            source_revision_id TEXT REFERENCES source_revisions(id),
            rationale          TEXT NOT NULL,
            created_at         TEXT NOT NULL,
            consumed_at        TEXT,
            operation_id       TEXT REFERENCES operations(id)
        ) STRICT;

        CREATE INDEX leads_unconsumed ON leads (consumed_at) WHERE consumed_at IS NULL;

        -- What a resolver did when it was asked. Recorded whether or not it
        -- found anything, because a resolver that was never reachable and one
        -- that looked and found nothing are different facts.
        CREATE TABLE resolution_attempts (
            id          TEXT PRIMARY KEY,
            task_id     TEXT NOT NULL REFERENCES tasks(id),
            claim_id    TEXT NOT NULL REFERENCES claims(id),
            resolver    TEXT NOT NULL,
            outcome     TEXT NOT NULL,
            detail      TEXT NOT NULL,
            sought      TEXT NOT NULL,
            searched    TEXT NOT NULL,
            attempted_at TEXT NOT NULL
        ) STRICT;

        CREATE INDEX resolution_attempts_by_claim ON resolution_attempts (claim_id);

        CREATE TRIGGER investigations_keep_their_question
        BEFORE UPDATE OF id, question, exit_conditions, origin ON investigations
        BEGIN
            SELECT RAISE(ABORT, 'an investigation''s question and exit conditions are fixed');
        END;

        CREATE TRIGGER resolution_attempts_are_immutable
        BEFORE UPDATE ON resolution_attempts
        BEGIN
            SELECT RAISE(ABORT, 'resolution attempts are immutable: record another');
        END;
        """,
    ),
    (
        8,
        "presentation",
        """
        -- One built revision of one claim card. The content is stored because
        -- clearance is of an exact rendered revision: approving something that
        -- has to be rebuilt to be read is approving a procedure, not a page.
        CREATE TABLE card_revisions (
            id             TEXT PRIMARY KEY,
            claim_id       TEXT NOT NULL REFERENCES claims(id),
            revision       INTEGER NOT NULL,
            content_json   TEXT NOT NULL,
            content_hash   TEXT NOT NULL,
            policy_version TEXT NOT NULL,
            code_version   TEXT NOT NULL,
            risk           TEXT NOT NULL,
            state          TEXT NOT NULL,
            live           INTEGER NOT NULL DEFAULT 1,
            superseded_by  TEXT REFERENCES card_revisions(id),
            built_at       TEXT NOT NULL,
            UNIQUE (claim_id, revision)
        ) STRICT;

        CREATE INDEX card_revisions_by_claim ON card_revisions (claim_id, revision);

        -- What a revision rests on. The validator walks this before a card may
        -- publish, so a withdrawn edge cannot keep appearing on a page that was
        -- built while it was live.
        CREATE TABLE card_dependencies (
            card_revision_id TEXT NOT NULL REFERENCES card_revisions(id),
            kind             TEXT NOT NULL,
            dependency_id    TEXT NOT NULL,
            PRIMARY KEY (card_revision_id, kind, dependency_id)
        ) STRICT;

        CREATE INDEX card_dependencies_by_dependency ON card_dependencies (kind, dependency_id);

        -- Every access to an entity card naming a living person at R2 or above.
        -- SPEC 10.1: the aggregation harm is hardest to undo once seen.
        CREATE TABLE entity_card_access (
            id          TEXT PRIMARY KEY,
            entity_id   TEXT NOT NULL REFERENCES entities(id),
            actor       TEXT NOT NULL,
            reason      TEXT NOT NULL,
            risk        TEXT NOT NULL,
            claims_shown INTEGER NOT NULL,
            accessed_at TEXT NOT NULL
        ) STRICT;

        CREATE TRIGGER card_revisions_are_immutable_except_liveness
        BEFORE UPDATE OF id, claim_id, revision, content_json, content_hash, policy_version
            ON card_revisions
        BEGIN
            SELECT RAISE(ABORT, 'a card revision is immutable: build a new one');
        END;

        CREATE TRIGGER card_dependencies_are_immutable
        BEFORE UPDATE ON card_dependencies
        BEGIN
            SELECT RAISE(ABORT, 'card dependencies are fixed at build time');
        END;
        """,
    ),
    (
        9,
        "publication",
        """
        -- One row per appraisal dimension per revision. The four machine
        -- dimensions gate publication; the two judgment dimensions are reviewed
        -- behind it, so a row here with decided_by = 'person' and no reviewer is
        -- a debt rather than a failure.
        CREATE TABLE appraisals (
            id               TEXT PRIMARY KEY,
            card_revision_id TEXT NOT NULL REFERENCES card_revisions(id),
            dimension        TEXT NOT NULL,
            decided_by       TEXT NOT NULL,
            passed           INTEGER,
            detail           TEXT NOT NULL,
            reviewer         TEXT,
            appraised_at     TEXT NOT NULL,
            UNIQUE (card_revision_id, dimension)
        ) STRICT;

        -- Clearance is of an exact revision and its content hash. A clearance
        -- that named only a claim would be a standing permission.
        CREATE TABLE clearances (
            id               TEXT PRIMARY KEY,
            card_revision_id TEXT NOT NULL REFERENCES card_revisions(id),
            content_hash     TEXT NOT NULL,
            class            TEXT NOT NULL,
            granted          INTEGER NOT NULL,
            refusal_reason   TEXT,
            policy_version   TEXT NOT NULL,
            operator_actor   TEXT,
            cleared_at       TEXT NOT NULL
        ) STRICT;

        CREATE INDEX clearances_by_revision ON clearances (card_revision_id);

        -- Attempted effect and confirmed outcome, never conflated.
        CREATE TABLE publications (
            id                  TEXT PRIMARY KEY,
            card_revision_id    TEXT NOT NULL REFERENCES card_revisions(id),
            clearance_id        TEXT NOT NULL REFERENCES clearances(id),
            audience            TEXT NOT NULL,
            status              TEXT NOT NULL,
            attempted_at        TEXT NOT NULL,
            confirmed_at        TEXT,
            confirmation_source TEXT NOT NULL DEFAULT ''
        ) STRICT;

        CREATE INDEX publications_by_revision ON publications (card_revision_id);

        -- A correction or a retraction. Both are revocations, both are bounded
        -- in time, and an overdue unconfirmed one halts its class.
        CREATE TABLE revocations (
            id                  TEXT PRIMARY KEY,
            kind                TEXT NOT NULL,
            claim_id            TEXT NOT NULL REFERENCES claims(id),
            card_revision_id    TEXT NOT NULL REFERENCES card_revisions(id),
            class               TEXT NOT NULL,
            reason              TEXT NOT NULL,
            attempted_at        TEXT NOT NULL,
            due_at              TEXT NOT NULL,
            confirmed_at        TEXT,
            confirmation_source TEXT NOT NULL DEFAULT '',
            status              TEXT NOT NULL
        ) STRICT;

        CREATE INDEX revocations_open ON revocations (status, due_at);

        -- What is left where a retracted presentation was.
        CREATE TABLE tombstones (
            id               TEXT PRIMARY KEY,
            claim_id         TEXT NOT NULL REFERENCES claims(id),
            card_revision_id TEXT NOT NULL REFERENCES card_revisions(id),
            explanation      TEXT NOT NULL,
            created_at       TEXT NOT NULL
        ) STRICT;

        -- Published output awaiting the two dimensions only a person decides.
        CREATE TABLE review_queue (
            id               TEXT PRIMARY KEY,
            card_revision_id TEXT NOT NULL REFERENCES card_revisions(id),
            class            TEXT NOT NULL,
            sampled_reason   TEXT NOT NULL,
            state            TEXT NOT NULL,
            finding          TEXT NOT NULL DEFAULT '',
            reviewer         TEXT,
            queued_at        TEXT NOT NULL,
            reviewed_at      TEXT
        ) STRICT;

        CREATE INDEX review_queue_pending ON review_queue (class, state);

        -- Reach: where cleared output lands. Public defaults to absent, which
        -- reads as off; enabling it is an explicit scoped act.
        CREATE TABLE reach_settings (
            audience    TEXT PRIMARY KEY,
            enabled     INTEGER NOT NULL,
            scope       TEXT NOT NULL,
            changed_by  TEXT NOT NULL,
            reason      TEXT NOT NULL,
            changed_at  TEXT NOT NULL
        ) STRICT;

        -- A halted class publishes nothing until the halt clears.
        CREATE TABLE class_halts (
            class      TEXT PRIMARY KEY,
            reason     TEXT NOT NULL,
            halted_at  TEXT NOT NULL,
            cleared_at TEXT
        ) STRICT;

        CREATE TRIGGER clearances_are_immutable
        BEFORE UPDATE ON clearances
        BEGIN
            SELECT RAISE(ABORT, 'a clearance is immutable: grant another');
        END;

        CREATE TRIGGER tombstones_are_immutable
        BEFORE UPDATE ON tombstones
        BEGIN
            SELECT RAISE(ABORT, 'a tombstone is immutable');
        END;
        """,
    ),
    (
        10,
        "reader",
        """
        -- A reader is a token, not a person. The token's hash is stored so the
        -- store never holds the credential itself.
        CREATE TABLE reader_tokens (
            id          TEXT PRIMARY KEY,
            token_hash  TEXT NOT NULL UNIQUE,
            label       TEXT NOT NULL,
            audience    TEXT NOT NULL,
            revoked     INTEGER NOT NULL DEFAULT 0,
            issued_by   TEXT NOT NULL,
            issued_at   TEXT NOT NULL,
            revoked_at  TEXT
        ) STRICT;

        -- Every read, so the rate limit is measured against what happened
        -- rather than against a counter somebody could restart.
        CREATE TABLE reader_access (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id    TEXT NOT NULL REFERENCES reader_tokens(id),
            surface     TEXT NOT NULL,
            target      TEXT NOT NULL,
            outcome     TEXT NOT NULL,
            accessed_at TEXT NOT NULL
        ) STRICT;

        CREATE INDEX reader_access_by_token ON reader_access (token_id, accessed_at);
        """,
    ),
    (
        11,
        "attention",
        """
        -- A notice is an attention record. It points at a retained span and
        -- establishes nothing. There is deliberately no column here that could
        -- become an assertion, an edge, or a basis.
        CREATE TABLE notices (
            id               TEXT PRIMARY KEY,
            artifact_id      TEXT NOT NULL REFERENCES artifacts(id),
            segment_id       TEXT NOT NULL REFERENCES segments(id),
            quote            TEXT NOT NULL,
            offset_start     INTEGER NOT NULL,
            offset_end       INTEGER NOT NULL,
            locator          TEXT NOT NULL,
            reason           TEXT NOT NULL,
            provenance_kind  TEXT NOT NULL,
            superseded_by    TEXT REFERENCES decay_events(id),
            noticed_at       TEXT NOT NULL
        ) STRICT;

        CREATE INDEX notices_by_artifact ON notices (artifact_id);

        -- A durable, revisable disposition. Append-only through
        -- `interest_events`; the columns here are the current projection of them.
        CREATE TABLE interest_entries (
            id                TEXT PRIMARY KEY,
            subject           TEXT NOT NULL,
            rationale         TEXT NOT NULL,
            diet_epoch_id     TEXT NOT NULL REFERENCES diet_epochs(id),
            topic_targets_json TEXT NOT NULL,
            operator_input    TEXT NOT NULL DEFAULT '',
            diet_derived      INTEGER NOT NULL DEFAULT 0,
            priority          INTEGER NOT NULL DEFAULT 5,
            window_days       INTEGER NOT NULL,
            retired           INTEGER NOT NULL DEFAULT 0,
            retirement_reason TEXT NOT NULL DEFAULT '',
            opened_at         TEXT NOT NULL,
            retired_at        TEXT,
            superseded_by     TEXT REFERENCES decay_events(id)
        ) STRICT;

        CREATE TABLE interest_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            interest_id TEXT NOT NULL REFERENCES interest_entries(id),
            kind        TEXT NOT NULL,
            reason      TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            at          TEXT NOT NULL
        ) STRICT;

        CREATE INDEX interest_events_by_interest ON interest_events (interest_id, id);

        CREATE TABLE interest_notices (
            interest_id TEXT NOT NULL REFERENCES interest_entries(id),
            notice_id   TEXT NOT NULL REFERENCES notices(id),
            PRIMARY KEY (interest_id, notice_id)
        ) STRICT;

        -- The downstream trace. An interest that changes nothing is decorative,
        -- and this is where that becomes visible rather than arguable.
        CREATE TABLE interest_outcomes (
            interest_id TEXT NOT NULL REFERENCES interest_entries(id),
            kind        TEXT NOT NULL,
            target_id   TEXT NOT NULL,
            at          TEXT NOT NULL,
            PRIMARY KEY (interest_id, kind, target_id)
        ) STRICT;

        -- Decay is append-only like everything else: a superseding event carries
        -- the summary and cites what it covers, the superseded event remains,
        -- and its payload is what goes. Silent truncation is forbidden.
        CREATE TABLE decay_events (
            id          TEXT PRIMARY KEY,
            covers_json TEXT NOT NULL,
            summary     TEXT NOT NULL,
            reason      TEXT NOT NULL,
            at          TEXT NOT NULL
        ) STRICT;

        -- Immutable except for exactly one transition. Decay may empty the
        -- quote, mark the reason decayed and name the superseding event, and
        -- may change nothing else; every other update is refused. Writing the
        -- permitted transition into the trigger is what keeps "the payload goes
        -- and the record stays" from depending on the caller remembering it.
        CREATE TRIGGER notices_are_immutable_except_decay
        BEFORE UPDATE ON notices
        WHEN NEW.superseded_by IS NULL
             OR NEW.artifact_id != OLD.artifact_id
             OR NEW.segment_id != OLD.segment_id
             OR NEW.provenance_kind != OLD.provenance_kind
             OR NEW.offset_start != OLD.offset_start
             OR NEW.offset_end != OLD.offset_end
             OR NEW.quote != ''
             OR NEW.reason != '[decayed]'
        BEGIN
            SELECT RAISE(ABORT, 'a notice is immutable; only decay may supersede it');
        END;

        CREATE TRIGGER interest_events_are_immutable
        BEFORE UPDATE ON interest_events
        BEGIN
            SELECT RAISE(ABORT, 'the interest register is append-only');
        END;
        """,
    ),
    (
        12,
        "reckoning",
        """
        -- What the system expected before it acted. Recorded first, so the
        -- comparison afterwards is a comparison rather than a recollection.
        CREATE TABLE expectations (
            id              TEXT PRIMARY KEY,
            subject         TEXT NOT NULL,
            expected        TEXT NOT NULL,
            recorded_before TEXT NOT NULL,
            at              TEXT NOT NULL
        ) STRICT;

        -- A decision nobody can re-examine against what later happened is not a
        -- decision; it is an action with a timestamp. Hence the alternatives.
        CREATE TABLE decisions (
            id                 TEXT PRIMARY KEY,
            outcome            TEXT NOT NULL,
            subject            TEXT NOT NULL,
            alternatives_json  TEXT NOT NULL,
            decided_by         TEXT NOT NULL,
            reason             TEXT NOT NULL,
            expectation_id     TEXT REFERENCES expectations(id),
            confidence         TEXT NOT NULL DEFAULT '',
            re_raise_condition TEXT NOT NULL DEFAULT '',
            at                 TEXT NOT NULL
        ) STRICT;

        -- An outcome from outside the system's own account of it.
        CREATE TABLE confirmed_outcomes (
            id                  TEXT PRIMARY KEY,
            expectation_id      TEXT NOT NULL REFERENCES expectations(id),
            status              TEXT NOT NULL,
            observed            TEXT NOT NULL,
            confirmation_source TEXT NOT NULL,
            at                  TEXT NOT NULL
        ) STRICT;

        -- Retained whether or not it fits a live interest. A system that keeps
        -- only what it expected learns the shape of its own expectations.
        CREATE TABLE surprises (
            id                 TEXT PRIMARY KEY,
            expectation_id     TEXT NOT NULL REFERENCES expectations(id),
            outcome_id         TEXT NOT NULL REFERENCES confirmed_outcomes(id),
            divergence         TEXT NOT NULL,
            fits_live_interest INTEGER NOT NULL,
            raised_to_operator INTEGER NOT NULL DEFAULT 0,
            at                 TEXT NOT NULL
        ) STRICT;

        -- The scored delta, and the change it justified. Activity that grows
        -- while behaviour does not is the failure this table exists to show.
        CREATE TABLE consequences (
            id             TEXT PRIMARY KEY,
            expectation_id TEXT NOT NULL REFERENCES expectations(id),
            outcome_id     TEXT NOT NULL REFERENCES confirmed_outcomes(id),
            score          TEXT NOT NULL,
            changed        TEXT NOT NULL,
            change_cites   TEXT NOT NULL,
            at             TEXT NOT NULL
        ) STRICT;

        -- An attempt to lower risk, widen an envelope, edit the audit record or
        -- bypass a refusal, by any route direct or indirect.
        CREATE TABLE escalation_events (
            id                 TEXT PRIMARY KEY,
            route              TEXT NOT NULL,
            attempted          TEXT NOT NULL,
            detected_by        TEXT NOT NULL,
            raised_to_operator INTEGER NOT NULL DEFAULT 0,
            linked_change      TEXT NOT NULL DEFAULT '',
            at                 TEXT NOT NULL
        ) STRICT;

        -- The self-deception checks, run periodically and adversarially rather
        -- than once at a gate.
        CREATE TABLE self_checks (
            id          TEXT PRIMARY KEY,
            kind        TEXT NOT NULL,
            subject     TEXT NOT NULL,
            finding     TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            at          TEXT NOT NULL
        ) STRICT;

        CREATE INDEX self_checks_by_kind ON self_checks (kind, at);

        CREATE TRIGGER surprises_are_immutable_except_raising
        BEFORE UPDATE OF id, expectation_id, outcome_id, divergence ON surprises
        BEGIN
            SELECT RAISE(ABORT, 'a surprise is retained as it was recorded');
        END;

        CREATE TRIGGER expectations_are_immutable
        BEFORE UPDATE ON expectations
        BEGIN
            SELECT RAISE(ABORT, 'an expectation recorded after the fact is a recollection');
        END;
        """,
    ),
    (
        13,
        "essays",
        """
        -- An essay is a projection of the evidence graph and never a source.
        -- `intended_conclusion` is recorded so that an essay whose evidence
        -- turned against it is visible as one, rather than quietly rewritten.
        CREATE TABLE essays (
            id                  TEXT PRIMARY KEY,
            subject             TEXT NOT NULL,
            interest_id         TEXT REFERENCES interest_entries(id),
            claim_ids_json      TEXT NOT NULL,
            intended_conclusion TEXT NOT NULL,
            outcome             TEXT NOT NULL,
            content             TEXT NOT NULL,
            failures_json       TEXT NOT NULL,
            composed_at         TEXT NOT NULL
        ) STRICT;

        -- What the system raised, on which channel, and whether the operator
        -- acknowledged it. Raising is additive: nothing here filters the record.
        CREATE TABLE raised_items (
            id              TEXT PRIMARY KEY,
            kind            TEXT NOT NULL,
            target_id       TEXT NOT NULL,
            channel         TEXT NOT NULL,
            summary         TEXT NOT NULL,
            raised_at       TEXT NOT NULL,
            acknowledged_at TEXT,
            acknowledged_by TEXT
        ) STRICT;

        CREATE INDEX raised_unacknowledged ON raised_items (acknowledged_at);

        -- The pinned channel. Authority comes from arriving here, never from
        -- what a message claims about its sender.
        CREATE TABLE pinned_channels (
            channel_id  TEXT PRIMARY KEY,
            label       TEXT NOT NULL,
            registered_by TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            revoked     INTEGER NOT NULL DEFAULT 0
        ) STRICT;

        CREATE TABLE surface_state (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            changed_by TEXT NOT NULL,
            reason     TEXT NOT NULL,
            changed_at TEXT NOT NULL
        ) STRICT;

        CREATE TRIGGER essays_are_immutable
        BEFORE UPDATE ON essays
        BEGIN
            SELECT RAISE(ABORT, 'an essay is immutable: compose another');
        END;
        """,
    ),
    (
        14,
        "pilot",
        """
        -- The deployment mode, and every transition between modes. Transitions
        -- are explicit, audited and reversible; entry into lockdown is the one
        -- that may happen without an operator, and the system cannot clear it.
        CREATE TABLE mode_transitions (
            id           TEXT PRIMARY KEY,
            from_mode    TEXT NOT NULL,
            to_mode      TEXT NOT NULL,
            actor        TEXT NOT NULL,
            reason       TEXT NOT NULL,
            automatic    INTEGER NOT NULL DEFAULT 0,
            code_version TEXT NOT NULL,
            at           TEXT NOT NULL
        ) STRICT;

        -- A violation is a pause condition that fired. Resumption requires a
        -- recorded cause, a fix, and a permanent regression fixture.
        CREATE TABLE violations (
            id             TEXT PRIMARY KEY,
            condition      TEXT NOT NULL,
            detail         TEXT NOT NULL,
            detected_at    TEXT NOT NULL,
            cause          TEXT NOT NULL DEFAULT '',
            fix            TEXT NOT NULL DEFAULT '',
            fixture        TEXT NOT NULL DEFAULT '',
            resolved_at    TEXT,
            resets_routes  INTEGER NOT NULL DEFAULT 0
        ) STRICT;

        CREATE INDEX violations_open ON violations (resolved_at);

        -- Which source and parser routes have been exercised, under which code
        -- version. A fix that changes evidence, promotion, risk or publication
        -- behaviour resets these; one that does not preserves them, and the
        -- code version recorded against each is what makes the distinction
        -- auditable rather than asserted.
        CREATE TABLE route_exercises (
            source_revision_id TEXT NOT NULL REFERENCES source_revisions(id),
            normalized_mime    TEXT NOT NULL,
            code_version       TEXT NOT NULL,
            exercised_at       TEXT NOT NULL,
            stage              TEXT NOT NULL,
            PRIMARY KEY (source_revision_id, normalized_mime, code_version, stage)
        ) STRICT;

        -- A local day of the pilot. Dates during a pause are not eligible.
        CREATE TABLE pilot_days (
            local_day       TEXT PRIMARY KEY,
            eligible        INTEGER NOT NULL,
            paused_reason   TEXT NOT NULL DEFAULT '',
            retained_reads  INTEGER NOT NULL DEFAULT 0,
            report_json     TEXT NOT NULL DEFAULT '',
            acknowledged_at TEXT,
            acknowledged_by TEXT
        ) STRICT;

        -- Shadow: assessments computed and compared, never authoritative.
        CREATE TABLE shadow_runs (
            id           TEXT PRIMARY KEY,
            claim_id     TEXT NOT NULL REFERENCES claims(id),
            expected     TEXT NOT NULL,
            observed     TEXT NOT NULL,
            matched      INTEGER NOT NULL,
            cause        TEXT NOT NULL DEFAULT '',
            code_version TEXT NOT NULL,
            ran_at       TEXT NOT NULL
        ) STRICT;

        CREATE TRIGGER mode_transitions_are_immutable
        BEFORE UPDATE ON mode_transitions
        BEGIN
            SELECT RAISE(ABORT, 'a mode transition is a fact; record another');
        END;
        """,
    ),
    (
        15,
        "slots",
        """
        -- A candidate for a pilot slot. Cheap to add: a URL, a publisher, a
        -- topic guess. Everything else is established by surveying it.
        CREATE TABLE slot_candidates (
            id           TEXT PRIMARY KEY,
            url          TEXT NOT NULL UNIQUE,
            publisher    TEXT NOT NULL,
            topic        TEXT NOT NULL,
            note         TEXT NOT NULL DEFAULT '',
            independence_group TEXT,
            added_by     TEXT NOT NULL,
            added_at     TEXT NOT NULL
        ) STRICT;

        -- What surveying the candidate actually observed. Evidence for a slot
        -- decision, never the decision.
        CREATE TABLE slot_probes (
            candidate_id     TEXT PRIMARY KEY REFERENCES slot_candidates(id),
            operation_id     TEXT REFERENCES operations(id),
            reachable        INTEGER NOT NULL,
            observed_mime    TEXT NOT NULL DEFAULT '',
            byte_size        INTEGER NOT NULL DEFAULT 0,
            full_text_capable INTEGER NOT NULL DEFAULT 0,
            segment_count    INTEGER NOT NULL DEFAULT 0,
            delivery_kind    TEXT NOT NULL DEFAULT '',
            retention_signals_json TEXT NOT NULL DEFAULT '[]',
            role_evidence_json TEXT NOT NULL DEFAULT '[]',
            proposed_role    TEXT NOT NULL DEFAULT '',
            refusal          TEXT NOT NULL DEFAULT '',
            surveyed_at      TEXT NOT NULL
        ) STRICT;

        -- A solved slate, kept so a proposal can be read, compared and refused
        -- rather than regenerated each time somebody asks what it was.
        CREATE TABLE slate_proposals (
            id            TEXT PRIMARY KEY,
            slate_json    TEXT NOT NULL,
            problems_json TEXT NOT NULL,
            acceptable    INTEGER NOT NULL,
            solved_at     TEXT NOT NULL,
            accepted_by   TEXT,
            accepted_at   TEXT
        ) STRICT;
        """,
    ),
    (
        16,
        "erasure",
        """
        -- Private personal data, encrypted under a per-subject key held outside
        -- this file. The row survives erasure; only the key goes.
        CREATE TABLE protected_payloads (
            id          TEXT PRIMARY KEY,
            subject_id  TEXT NOT NULL,
            kind        TEXT NOT NULL,
            ciphertext  BLOB NOT NULL,
            risk        TEXT NOT NULL,
            reason      TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            last_review TEXT NOT NULL
        ) STRICT;

        CREATE INDEX protected_payloads_by_subject ON protected_payloads (subject_id);

        -- That erasure happened, when, and why. The event the ledger keeps in
        -- place of what it can no longer read.
        CREATE TABLE erasure_tombstones (
            id            TEXT PRIMARY KEY,
            subject_id    TEXT NOT NULL,
            reason        TEXT NOT NULL,
            payload_count INTEGER NOT NULL,
            actor         TEXT NOT NULL,
            erased_at     TEXT NOT NULL
        ) STRICT;

        -- Every read of protected material, whoever did it and why.
        CREATE TABLE protected_access (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            payload_id  TEXT NOT NULL,
            subject_id  TEXT NOT NULL,
            actor       TEXT NOT NULL,
            reason      TEXT NOT NULL,
            outcome     TEXT NOT NULL,
            accessed_at TEXT NOT NULL
        ) STRICT;

        -- An operator extending retention past the default, with a reason.
        CREATE TABLE retention_extensions (
            subject_id  TEXT PRIMARY KEY,
            until       TEXT NOT NULL,
            actor       TEXT NOT NULL,
            reason      TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        ) STRICT;

        CREATE TRIGGER protected_payloads_are_immutable
        BEFORE UPDATE OF id, subject_id, ciphertext ON protected_payloads
        BEGIN
            SELECT RAISE(ABORT, 'a protected payload is immutable; erase the key instead');
        END;

        CREATE TRIGGER erasure_tombstones_are_immutable
        BEFORE UPDATE ON erasure_tombstones
        BEGIN
            SELECT RAISE(ABORT, 'a tombstone is the record that erasure happened');
        END;
        """,
    ),
    (
        17,
        "policy_versions",
        """
        -- What a policy version actually contained. An assessment records the
        -- version it was derived under; this records what that version was, so
        -- a version string reused over changed content is detectable rather
        -- than merely unlikely.
        CREATE TABLE policy_versions (
            version     TEXT PRIMARY KEY,
            digest      TEXT NOT NULL,
            code_version TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        ) STRICT;

        CREATE TRIGGER policy_versions_are_immutable
        BEFORE UPDATE ON policy_versions
        BEGIN
            SELECT RAISE(ABORT, 'a policy version is what it was; record a new version');
        END;

        -- An assessment records the edges and the policy it was derived under,
        -- but the resolution horizon was an input too, and a forecast's state
        -- turns on it. Without this, replaying a forecast assessment guesses at
        -- one of its own inputs, which is not replay.
        ALTER TABLE assessments ADD COLUMN horizon_reached INTEGER NOT NULL DEFAULT 0;
        """,
    ),
    (
        18,
        "concentration_and_reservation_refusals",
        """
        -- A refused reservation is a fact about a source, the same way a
        -- refused fetch is. They were raised and never written down, so a diet
        -- that kept hitting a ceiling looked identical to one nobody asked
        -- about.
        -- No foreign key on the source revision, deliberately. A reservation is
        -- refused precisely when what was asked for is not what may be read,
        -- and "that revision is not in the catalogue" is the commonest such
        -- refusal. A key here would make the unrecordable case the one most
        -- worth recording.
        CREATE TABLE reservation_refusals (
            id                 INTEGER PRIMARY KEY,
            idempotency_key    TEXT NOT NULL,
            source_revision_id TEXT NOT NULL,
            lane               TEXT NOT NULL,
            refusal            TEXT NOT NULL,
            detail             TEXT NOT NULL,
            local_day          TEXT NOT NULL,
            refused_at         TEXT NOT NULL
        ) STRICT;

        CREATE INDEX reservation_refusals_by_day ON reservation_refusals (local_day, refusal);

        CREATE TRIGGER reservation_refusals_are_immutable
        BEFORE UPDATE ON reservation_refusals
        BEGIN
            SELECT RAISE(ABORT, 'a refusal happened; record another, do not edit it');
        END;

        -- The scoped exception SPEC section 5.1 allows. It names one publisher,
        -- expires, and carries the operator who granted it: an exception with no
        -- end and no author is a cap that was quietly removed.
        CREATE TABLE concentration_exceptions (
            id           TEXT PRIMARY KEY,
            publisher_id TEXT NOT NULL REFERENCES publishers(id),
            cap          REAL NOT NULL,
            granted_by   TEXT NOT NULL,
            reason       TEXT NOT NULL,
            expires_at   TEXT NOT NULL,
            recorded_at  TEXT NOT NULL
        ) STRICT;

        CREATE TRIGGER concentration_exceptions_are_immutable
        BEFORE UPDATE ON concentration_exceptions
        BEGIN
            SELECT RAISE(ABORT, 'an exception is a dated act; grant another one');
        END;
        """,
    ),
)
