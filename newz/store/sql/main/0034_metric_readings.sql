-- 0034_metric_readings — P4 epic E2.7.
-- Writer: newz/evidence/baseline.py::take, on every read.
-- Reader: the same module, for the baseline a later reading is compared to,
--   and tools/claims.py --read, which prints the delta beside the value.
--
-- **Why a delta needs a table.** The project's deltas exist today only as
-- prose: "advance acceptance rose 28.3% -> 41.1% where P2 expected a fall" was
-- computed by hand, once, inside an argument. Nothing can steer on a figure
-- that lives in a document, and nothing can notice when it moves again.
--
-- Every reading is kept, including the ones that measured nothing. A reading
-- that was INCOMPLETE or UNREADABLE is exactly what a later reader needs in
-- order to know the series has a hole in it — dropping those rows would make
-- the record of a measurement look continuous when the measurement was not
-- (INV-044, generalised).

CREATE TABLE metric_readings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    metric       TEXT NOT NULL,
    status       TEXT NOT NULL,      -- ok | incomplete | unreadable
    value        REAL,               -- null unless status='ok'
    window_hours REAL NOT NULL,
    note         TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_metric_readings ON metric_readings (metric, ts DESC);
