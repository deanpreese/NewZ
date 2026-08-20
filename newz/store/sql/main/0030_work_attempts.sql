-- 0030_work_attempts — P4 epic E2.1.
-- Writer: newz/works/rhythm.py, before it composes anything.
-- Reader: the ceiling in the same module, and tools/read_works.py --rhythm,
--   which reads attempts against pieces so a rhythm that starts and never
--   finishes is visible rather than silent.
--
-- **R-25's started-ceiling, and the reason the row is written first.** The cap
-- counts what was STARTED, never what was produced. An outcome-based budget
-- pays for success and charges nothing for failure, so a session that dies
-- mid-composition is free and can be retried without limit — which is how a
-- restart loop turns into unbounded spend. Deliberation learned this as R-18
-- ("a started deliberation costs budget whatever it produces"); this is the
-- same rule for writing, and it is why the attempt is committed before the
-- first model call rather than after the last.
--
-- Rule 5: production is a rhythm, not an initiative. The being does not decide
-- to write; it writes on cadence, and what it chooses is the only judgment in
-- the loop.

CREATE TABLE work_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    outcome      TEXT NOT NULL,      -- started | wrote | no_subject | failed
    subject_kind TEXT,               -- null until a subject is chosen
    subject_ref  INTEGER,
    work_id      INTEGER REFERENCES works(id),
    note         TEXT
);
CREATE INDEX idx_work_attempts_ts ON work_attempts (ts);
