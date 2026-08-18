-- 0002_conversation — Phase 0.4. Writers and readers land together (Rule 2):
-- messages: written by the ambient loop (both directions), read by the
--   composer as thread history (S2 §6.2).
-- gate_log: written by the outbound gate on every verdict (passes included,
--   for the denominator — S2 §11), read by tools/gate_report.py and tests.

CREATE TABLE messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL    NOT NULL,
    channel   TEXT    NOT NULL,             -- 'telegram'
    direction TEXT    NOT NULL,             -- 'in' | 'out'
    person_id TEXT    NOT NULL,             -- operator id for Phase 0
    content   TEXT    NOT NULL,
    update_id INTEGER,                      -- telegram update dedup (inbound)
    verdict   TEXT,                          -- gate verdict on outbound
    episode_id INTEGER REFERENCES episodes(id)
);
CREATE UNIQUE INDEX idx_messages_update ON messages (update_id) WHERE update_id IS NOT NULL;
CREATE INDEX idx_messages_ts ON messages (ts);

CREATE TABLE gate_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ts               REAL NOT NULL,
    channel          TEXT NOT NULL,
    verdict          TEXT NOT NULL,          -- pass | revise | block
    clause_id        TEXT,
    confidence       REAL,
    asserted_span    TEXT,
    emission_hash    TEXT,
    emission_excerpt TEXT,
    attempt          INTEGER NOT NULL DEFAULT 0,
    note             TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_gate_log_verdict ON gate_log (verdict, ts);
