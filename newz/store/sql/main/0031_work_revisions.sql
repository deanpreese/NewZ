-- 0031_work_revisions — P4 epic E2.2.
-- Writer: newz/works/reread.py, when a re-read revises or retracts a piece.
-- Reader: tools/read_works.py --history, which prints a piece with what it
--   used to say and why it changed.
--
-- **A retraction is an outcome, not a deletion.** P4's E2.2 says so in terms,
-- and E1.5 already established why at the claim layer: a being that can lose
-- the record of having been wrong has no record of having been wrong. The
-- same guards apply here — the prior text is kept, and neither the revision
-- record nor a retracted piece can be removed.
--
-- `works` gains a status rather than rows being rewritten in place, because
-- the unique index on (subject_kind, subject_ref) means a revision cannot be
-- a second row: one subject, one piece, and its history beside it.

ALTER TABLE works ADD COLUMN status TEXT NOT NULL DEFAULT 'standing';
ALTER TABLE works ADD COLUMN last_reviewed_at REAL;

CREATE TABLE work_revisions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ts               REAL NOT NULL,
    work_id          INTEGER NOT NULL REFERENCES works(id),
    kind             TEXT NOT NULL,      -- revised | retracted
    reason           TEXT NOT NULL,      -- the being's own reason, at the time
    prior_title      TEXT NOT NULL,
    prior_body       TEXT NOT NULL,
    prior_word_count INTEGER NOT NULL
);
CREATE INDEX idx_work_revisions_work ON work_revisions (work_id, ts);

CREATE TRIGGER work_revisions_no_delete
BEFORE DELETE ON work_revisions
BEGIN
    SELECT RAISE(ABORT, 'a revision is not deletable: what it used to say is part of the record');
END;

CREATE TRIGGER works_retraction_is_not_deletion
BEFORE DELETE ON works
BEGIN
    SELECT RAISE(ABORT, 'a piece is retracted, never deleted');
END;

-- Re-reading is its own rhythm with its own ceiling; one attempt ledger,
-- two caps (R-25 applies to both).
ALTER TABLE work_attempts ADD COLUMN kind TEXT NOT NULL DEFAULT 'write';
