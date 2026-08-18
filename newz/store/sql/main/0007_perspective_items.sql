-- 0007_perspective_items — P2 Phase 1.1.
-- Writer: sleep (the only Perspective writer, INV-009).
-- Reader: perspective rendering (what conversation sees) and diff
--   computation (S2 §14.1's primary development instrument).
--
-- The Perspective remains "a single versioned document" to the being
-- (S2 §4.2) — the document in `perspective.content` is RENDERED from these
-- rows. Items exist so confrontation can operate per held position
-- (S2 §5 step 3) and so the diff between versions is COMPUTED by comparing
-- item sets, not narrated by the model that wrote them. A narrated diff
-- would be the development instrument grading its own work.

CREATE TABLE perspective_items (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    version            INTEGER NOT NULL,     -- the Perspective version this row belongs to
    section            TEXT    NOT NULL,     -- who_i_am|what_i_hold|pursuing|who_i_know|unresolved
    text               TEXT    NOT NULL,
    evidence_json      TEXT    NOT NULL DEFAULT '[]',
    confidence         REAL    NOT NULL DEFAULT 0.6,
    -- How this item came to be in THIS version. 'carried' means it survived
    -- unchanged; the others are what the diff reports.
    status             TEXT    NOT NULL,     -- added|carried|revised|merged|released
    prior_item_id      INTEGER REFERENCES perspective_items(id),
    first_seen_version INTEGER NOT NULL,     -- when this position first appeared
    ts                 REAL    NOT NULL
);
CREATE INDEX idx_perspective_items_version ON perspective_items (version, section);
CREATE INDEX idx_perspective_items_lineage ON perspective_items (prior_item_id);
