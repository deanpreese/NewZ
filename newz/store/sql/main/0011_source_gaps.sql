-- 0011_source_gaps — P2 Phase 2.4.
-- Writer: newz/world/research.py when the adapters answer nothing usable.
-- Reader: tools/source_review.py, which is how the operator decides what to
--   add to the diet and what to drop.
--
-- S2 §9.1: reading is "chosen by the being's failed questions". This table
-- is that record — the questions the world did not answer, kept so the diet
-- is shaped by what the being actually needed rather than by what seemed
-- interesting when the feed list was written.

CREATE TABLE source_gaps (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    concern_id INTEGER REFERENCES concerns(id),
    query      TEXT NOT NULL,
    gap        TEXT NOT NULL
);
CREATE INDEX idx_source_gaps_ts ON source_gaps (ts);
