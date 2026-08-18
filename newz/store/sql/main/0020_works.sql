-- The being's own durable output (P3 Phase 0, epic E0.1).
--
-- Everything the being has produced so far is ephemeral: replies that scroll
-- away, Perspective items that sleep rewrites, dossiers nobody reads twice.
-- A work is the first thing it makes that persists as its own — which is what
-- lets it encounter its past self as an external object later (E2.2), and
-- what gives wrongness somewhere to be recorded.
--
-- Deliberately minimal. E3.1 grows this into the first-class object with
-- revisions, retraction, signature, subject tags and evidence refs; P3 Rule 2
-- forbids shipping those columns before their writer and reader exist. What
-- is here is written by newz/works/compose.py and read by tools/read_works.py
-- and the composer's own subject exclusion.
--
-- `subject_ref` is deliberately not a foreign key: a piece outlives the
-- concern that prompted it, and a closed or abandoned concern must not cascade
-- away the work it produced.
CREATE TABLE IF NOT EXISTS works (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                REAL NOT NULL,
    subject_kind      TEXT NOT NULL,     -- concern | position
    subject_ref       INTEGER NOT NULL,  -- concerns.id | perspective_items.id
    subject_text      TEXT NOT NULL,     -- the subject as it stood when chosen
    chosen_because    TEXT NOT NULL,     -- the being's own reason for picking it
    title             TEXT NOT NULL,
    body              TEXT NOT NULL,
    word_count        INTEGER NOT NULL,
    model             TEXT NOT NULL,
    completion_tokens INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_works_ts ON works (ts);
CREATE UNIQUE INDEX IF NOT EXISTS idx_works_subject
    ON works (subject_kind, subject_ref);
