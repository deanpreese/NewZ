-- 0005_journal — the operator journal (P2 Rule 3: restarts day one of
-- Phase 0, the standing instrument throughout; v1's cheapest instrument
-- produced the most signal, twice).
-- Writer: the Telegram /journal intercept and tools/journal.py.
-- Reader: tools/journal.py; later the cutover blind read.
-- Boundary: rows here NEVER enter the being's context — not messages, not
-- episodes, not prompts. The journal is about the being, not for it.

CREATE TABLE journal (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    day        TEXT NOT NULL,                 -- YYYY-MM-DD
    system_tag TEXT NOT NULL DEFAULT 'v2',    -- v2 | v1 (per-entry, one journal)
    entry      TEXT NOT NULL,
    update_id  INTEGER                        -- telegram dedup on redelivery
);
CREATE UNIQUE INDEX idx_journal_update ON journal (update_id) WHERE update_id IS NOT NULL;
CREATE INDEX idx_journal_day ON journal (day);
