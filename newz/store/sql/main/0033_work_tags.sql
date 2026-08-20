-- 0033_work_tags — P4 epic E2.4.
-- Writer: newz/works/subjects.py::recompute, wholesale.
-- Reader: tools/read_works.py --subjects, and E2.4's evidence — whether a
--   subject emerged rather than being assigned.
--
-- **Recomputed, never accumulated.** A term is a tag because it is
-- distinctive *within this corpus*, and that is a property of the corpus and
-- not of the piece. What is distinctive across three pieces is often noise
-- across thirty, so tags are replaced on every run rather than added to. A
-- table that accumulated them would record the history of a measurement as
-- though it were the history of a subject.
--
-- TRUE_NORTH §8: no vocabulary is authored here, not even a stop-list. Terms
-- common to everything score zero by construction, which is what inverse
-- document frequency is for — so "the" is excluded by the arithmetic rather
-- than by someone's judgment about which words are interesting.

CREATE TABLE work_tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    computed_at REAL NOT NULL,
    work_id     INTEGER NOT NULL REFERENCES works(id),
    tag         TEXT NOT NULL,
    weight      REAL NOT NULL
);
CREATE INDEX idx_work_tags_work ON work_tags (work_id, weight DESC);
CREATE INDEX idx_work_tags_tag ON work_tags (tag);
