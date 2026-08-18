-- 0013_deliberation_log — RISKS R-18.
-- Writer: newz/deliberation/lite.py, one row per deliberation STARTED.
-- Reader: the same module's budget check, and tools/health.py.
--
-- The budget previously counted advances and setbacks, so a deliberation
-- whose output would not parse cost nothing and could repeat without limit.
-- An attempt is booked before any model call or fetch, so failure is never
-- free — which is what makes state-driven scheduling (3.1) safe to build.

CREATE TABLE deliberation_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    concern_id INTEGER REFERENCES concerns(id),
    outcome    TEXT NOT NULL,          -- started | unreadable
    detail     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_deliberation_log_ts ON deliberation_log (ts);
