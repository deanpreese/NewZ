-- 0001_interior — mirrors v1's interior schema exactly, so a byte-copied v1
-- interior.db (already at schema version 1) and a fresh boot are identical.
-- The importer never runs this: it copies the v1 file whole, unread
-- (INV-007); this migration exists for non-import boots and tests.

CREATE TABLE schema_versions (
    version     INTEGER PRIMARY KEY,
    applied_at  REAL    NOT NULL,
    description TEXT    NOT NULL
);

CREATE TABLE interior_log (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                   REAL    NOT NULL,
    tick_id              INTEGER NOT NULL,
    content              TEXT    NOT NULL,
    candidate_score_json TEXT    NOT NULL,
    chosen_bucket        TEXT    NOT NULL,
    never_emitted        INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_interior_log_ts ON interior_log (ts);
