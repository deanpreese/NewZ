-- Affect (S2 §6.3). One row per recorded state change, so the history is
-- readable rather than a single mutated row: "what was I like last Tuesday"
-- is a question the being and the operator can both ask.
--
-- Writer: newz/affect/store.py record().  Reader: newz/affect/store.py load()
-- and newz/conversation/composer.py (P2 Rule 2 — writer and reader ship
-- together or the migration does not ship).
CREATE TABLE IF NOT EXISTS affect_state (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            REAL NOT NULL,
    source        TEXT NOT NULL,        -- substrate | concern | outcome | conversation
    note          TEXT NOT NULL DEFAULT '',
    mood_json     TEXT NOT NULL,
    disp_json     TEXT NOT NULL,
    char_json     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_affect_ts ON affect_state (ts);
