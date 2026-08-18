-- Noticing (S2 §6.1). Things the being might raise unprompted, carried until
-- they mature, surfaced under gates, and decayed when the moment passes.
--
-- v1's queue grew unbounded before its decay rule existed (31 pending, oldest
-- ~9 days). `decayed` is a real terminus here, not a tidy-up: a noticing
-- carried through a full wake cycle is the wrong moment to raise.
--
-- Writer: newz/ambient/noticing.py notice().  Readers: the same module's
-- surface selection and tools/health.py (P2 Rule 2).
CREATE TABLE IF NOT EXISTS noticings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    kind        TEXT NOT NULL,          -- what sort of thing was noticed
    episode_id  INTEGER REFERENCES episodes(id),
    text        TEXT NOT NULL,          -- what it is, in the being's own words
    score       REAL NOT NULL DEFAULT 0.5,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending|surfaced|decayed
    surfaced_at REAL,
    message_id  INTEGER REFERENCES messages(id)
);
CREATE INDEX IF NOT EXISTS idx_noticings_pending
    ON noticings (status, ts) WHERE status='pending';
CREATE UNIQUE INDEX IF NOT EXISTS idx_noticings_episode
    ON noticings (episode_id) WHERE episode_id IS NOT NULL;
