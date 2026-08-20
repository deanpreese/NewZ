-- 0035_metric_definitions — P4 epic E2.8.
-- Writer: newz/evidence/definitions.py::sync, from the registry.
-- Reader: newz/evidence/baseline.py, which will not compare readings across a
--   definition boundary, and tools/evidence.py purposes.
--
-- **What this prevents, and it has already happened once.** "Novelty" named two
-- different quantities in this codebase: the Perspective development share
-- (added+revised over held) and `novelty_against_history`'s embedding cosine
-- against prior advances. Both were reported. Nothing in the system objected,
-- because a metric's meaning lived only in the head of whoever last read the
-- code.
--
-- A version pins the meaning. When it changes, the series does not continue —
-- comparing a figure to one computed a different way is not a delta, it is two
-- numbers subtracted. The prior readings are kept and stay labelled with the
-- definition that produced them.

ALTER TABLE metric_readings ADD COLUMN definition_version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE metric_definition_changes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    metric       TEXT NOT NULL,
    from_version INTEGER,
    to_version   INTEGER NOT NULL,
    reason       TEXT NOT NULL
);
CREATE INDEX idx_metric_def_changes ON metric_definition_changes (metric, ts);

CREATE TRIGGER metric_definition_changes_no_delete
BEFORE DELETE ON metric_definition_changes
BEGIN
    SELECT RAISE(ABORT, 'a definition change is not deletable: it is why the series has a seam');
END;
