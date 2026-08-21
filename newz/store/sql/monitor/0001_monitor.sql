-- 0001_monitor — the monitor's own database (P4 E3A.1).
--
-- **Why a second file.** The monitor runs beside the being, not inside it, and
-- what it records is an observation *about* the being rather than part of the
-- being's own record. Two consequences, and both are the reason:
--
--   - `newz.db` keeps exactly one writer. The being writes its life; nothing
--     else writes into it.
--   - the being's store stops accreting ~245k rows a year of telemetry about
--     itself, which is what the backups and E3.5's clean-room rebuild exist to
--     describe.
--
-- This is `interior.db`'s discipline for the same reason it was applied there:
-- separation is structural — different file, different connection — not a
-- table prefix.
--
-- Attached as `mon` by newz/store/db.py::attach_monitor, so every existing
-- reader reaches these tables without a signature change.
--
-- Writer: newz/evidence/baseline.py::take, once per metric per hourly run, via
--   tools/monitor.py. definitions.py::sync writes the second table.
-- Readers: baseline.py::_baseline and series, definitions.py, pre_loop.py,
--   newz/surface/generate.py::_read, newz/monitor/report.py, tools/claims.py.

-- The runner's own record, per database. The monitor's chain is its own; it
-- shares nothing with the being's, which is the point of the separate file.
CREATE TABLE schema_versions (
    version     INTEGER PRIMARY KEY,
    applied_at  REAL    NOT NULL,
    description TEXT    NOT NULL
);

CREATE TABLE metric_readings (
    id                 INTEGER PRIMARY KEY,   -- carried over from newz.db
    ts                 REAL NOT NULL,
    metric             TEXT NOT NULL,
    status             TEXT NOT NULL,         -- ok | incomplete | unreadable
    value              REAL,                  -- null unless status='ok'
    window_hours       REAL NOT NULL,
    note               TEXT NOT NULL DEFAULT '',
    definition_version INTEGER NOT NULL DEFAULT 1
);

-- The two access patterns: series (metric, newest first) and the baseline
-- lookup (metric, newest at or before a moment).
CREATE INDEX idx_metric_readings ON metric_readings (metric, ts DESC);

-- E2.8. A definition change resets the series and records why; no delta is
-- ever computed across the boundary.
CREATE TABLE metric_definition_changes (
    id           INTEGER PRIMARY KEY,
    ts           REAL NOT NULL,
    metric       TEXT NOT NULL,
    from_version INTEGER NOT NULL,
    to_version   INTEGER NOT NULL,
    reason       TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_metric_definition_changes ON metric_definition_changes (metric, ts);

-- Carried with the table (main 0035). A definition change is the reason a
-- series has a seam in it; deleting one leaves the seam and removes the
-- explanation, which is the one edit that makes the record lie.
CREATE TRIGGER metric_definition_changes_no_delete
BEFORE DELETE ON metric_definition_changes
BEGIN
    SELECT RAISE(ABORT, 'a definition change is not deletable: it is why the series has a seam');
END;

-- Every run and every send, with its outcome. Rule 2: the reader is the daily
-- email, which reports the hours it missed and any send that failed, and it is
-- what stops a day being sent twice.
CREATE TABLE monitor_log (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     REAL NOT NULL,
    kind   TEXT NOT NULL,              -- reading | send | move
    ok     INTEGER NOT NULL,           -- 1 | 0
    note   TEXT NOT NULL DEFAULT ''
);

CREATE INDEX idx_monitor_log ON monitor_log (kind, ts DESC);
