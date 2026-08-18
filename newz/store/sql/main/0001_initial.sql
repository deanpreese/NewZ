-- 0001_initial — Phase 0 schema. Every table here has its writer and reader
-- landing in Phase 0 (P2 Rule 2): the importer writes the imported tables,
-- first sleep writes perspective, conversation/CLI and the test suite read.
-- Shapes marked (v1) are carried from the v1 store where they were proven;
-- v1's dead schema (policy_params, dream_log, model_of_my_model_json,
-- rubric_weights) is deliberately absent (S2 §1.3).

CREATE TABLE schema_versions (
    version     INTEGER PRIMARY KEY,
    applied_at  REAL    NOT NULL,
    description TEXT    NOT NULL
);

-- Phase 0.2: one row per imported table per run — the verification record.
CREATE TABLE import_record (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT    NOT NULL,
    ts             REAL    NOT NULL,
    v1_repo        TEXT    NOT NULL,
    v1_commit      TEXT    NOT NULL,
    table_name     TEXT    NOT NULL,
    v1_count       INTEGER NOT NULL,
    imported_count INTEGER NOT NULL,
    note           TEXT    NOT NULL DEFAULT ''
);

-- (v1) single table, self-referencing lineage.
CREATE TABLE constitution (
    version         INTEGER PRIMARY KEY,
    ts              REAL    NOT NULL,
    clauses_yaml    TEXT    NOT NULL,
    change_summary  TEXT    NOT NULL,
    prior_version   INTEGER,
    approval_status TEXT    NOT NULL,
    approver_a      TEXT,
    approver_b      TEXT,
    time_lock_until REAL,
    FOREIGN KEY (prior_version) REFERENCES constitution (version)
);

-- New in v2: v1 kept the character core as loose files; the identity-bearing
-- core belongs in the identity-bearing store (S2 §12.2.1).
CREATE TABLE character_core (
    version TEXT PRIMARY KEY,
    ts      REAL NOT NULL,
    content TEXT NOT NULL,
    source  TEXT NOT NULL
);

-- New in v2: relational claims (v1 kept them in opaque JSON snapshots and
-- could not query its own history of self-belief).
CREATE TABLE self_model_claims (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            REAL NOT NULL,
    claim         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'imported',  -- imported | audited | released
    source        TEXT NOT NULL,                     -- v1:self_model:<id> | sleep
    evidence_json TEXT NOT NULL DEFAULT '[]',
    notes         TEXT
);
CREATE INDEX idx_self_model_claims_status ON self_model_claims (status);

-- (v1 shape, minus model_of_my_model_json — dead schema, S2 §1.3.)
CREATE TABLE persons (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL,
    operator_id           TEXT NOT NULL,
    model_json            TEXT NOT NULL,
    landing_rates_json    TEXT,
    channel_bindings_json TEXT NOT NULL DEFAULT '{}',
    last_seen             REAL,
    ts                    REAL NOT NULL
);
CREATE INDEX idx_persons_operator ON persons (operator_id);

-- (v1) the concern shape the ported scoring module expects, whole.
CREATE TABLE concerns (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_at              REAL    NOT NULL,
    kind                   TEXT    NOT NULL,
    statement              TEXT    NOT NULL,
    why_open               TEXT    NOT NULL,
    closing_condition      TEXT    NOT NULL,
    status                 TEXT    NOT NULL DEFAULT 'open',
    salience               REAL    NOT NULL DEFAULT 0.5,
    origin                 TEXT    NOT NULL,
    origin_ref             TEXT,
    last_advanced_at       REAL,
    advance_count          INTEGER NOT NULL DEFAULT 0,
    stall_count            INTEGER NOT NULL DEFAULT 0,
    blocked_count          INTEGER NOT NULL DEFAULT 0,
    closed_at              REAL,
    resolution             TEXT,
    meta_json              TEXT    NOT NULL DEFAULT '{}',
    search_query           TEXT,
    opening_evidence       TEXT,
    opening_citations_json TEXT    NOT NULL DEFAULT '[]',
    last_attempted_at      REAL
);
CREATE INDEX idx_concerns_status    ON concerns (status, last_advanced_at);
CREATE INDEX idx_concerns_attempted ON concerns (status, last_attempted_at);

CREATE TABLE concern_advances (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    concern_id    INTEGER NOT NULL,
    ts            REAL    NOT NULL,
    kind          TEXT    NOT NULL,
    summary       TEXT    NOT NULL,
    evidence_json TEXT    NOT NULL DEFAULT '[]',
    source_ref    TEXT,
    FOREIGN KEY (concern_id) REFERENCES concerns (id)
);
CREATE INDEX idx_concern_advances_concern ON concern_advances (concern_id, ts);

CREATE TABLE concern_setbacks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    concern_id INTEGER NOT NULL,
    ts         REAL    NOT NULL,
    kind       TEXT    NOT NULL,
    brief      TEXT    NOT NULL DEFAULT '',
    source_ref TEXT,
    FOREIGN KEY (concern_id) REFERENCES concerns (id)
);
CREATE INDEX idx_concern_setbacks_concern ON concern_setbacks (concern_id, ts);

-- (v1) attempted/confirmed already models S2 §10.1.
CREATE TABLE publications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    concern_id    INTEGER,
    slug          TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    attempted_at  REAL NOT NULL,
    confirmed_at  REAL,
    retracted_at  REAL,
    source_ref    TEXT
);

-- (v1 shape.)
CREATE TABLE learnings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            REAL NOT NULL,
    situation_vec BLOB,
    action_type   TEXT NOT NULL,
    outcome_tag   TEXT NOT NULL,
    confidence    REAL NOT NULL,
    model_tag     TEXT NOT NULL,
    derived_from_interior_ref INTEGER,
    operator_id   TEXT,
    response_text TEXT,
    notes         TEXT,
    source_ref    TEXT
);
CREATE INDEX idx_learnings_ts ON learnings (ts);

-- S2 §4.1 raw layer. v1 episodes import with kind='v1_tick',
-- provenance='self', source_ref='v1:episode:<id>'.
CREATE TABLE episodes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    kind         TEXT NOT NULL,
    provenance   TEXT NOT NULL,
    summary      TEXT NOT NULL DEFAULT '',
    content_json TEXT,
    embedding    BLOB,
    source_ref   TEXT
);
CREATE INDEX idx_episodes_ts   ON episodes (ts);
CREATE INDEX idx_episodes_kind ON episodes (kind);

-- S2 §4.2 — the centerpiece. Written only by sleep (INV-009).
CREATE TABLE perspective (
    version     INTEGER PRIMARY KEY,
    ts          REAL    NOT NULL,
    content     TEXT    NOT NULL,
    diff_json   TEXT    NOT NULL DEFAULT '{}',
    token_count INTEGER NOT NULL,
    writer      TEXT    NOT NULL DEFAULT 'sleep'
);
