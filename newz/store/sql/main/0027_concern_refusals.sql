-- 0027_concern_refusals — P4 epic C (R-33).
-- Writer: newz/concerns/opener.py, when the door refuses a proposed concern
--   whose closing condition nothing could ever reach.
-- Reader: tools/claims.py --read, which prints the refusal counts beside the
--   closing-condition shapes so "the being forms no settleable concerns" is
--   distinguishable from "the door refuses all of them".
--
-- This is INV-046's move, one layer up. The claim door records a refusal
-- because P4's Phase 1 decision rule turns on telling "it commits to nothing
-- checkable" apart from "the door rejects everything" — and the concern
-- opener had the same blind spot with no table to see it through. Declining
-- to open is ordinary and is NOT recorded, exactly as declining to claim is
-- not; what is recorded is a concern the being proposed and the door would
-- not admit.
--
-- R-33 is why the table exists at all: 123 of 123 concerns carry a closing
-- condition nothing can reach — 111 that only the being could satisfy
-- ("I can cite..."), 12 that only an uncommissioned study could. Both shapes
-- pass a non-empty check, which was the only check there was.

CREATE TABLE concern_refusals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    origin     TEXT NOT NULL,          -- reading | research | conversation
    reason     TEXT NOT NULL,
    statement  TEXT NOT NULL,
    closing    TEXT NOT NULL
);
CREATE INDEX idx_concern_refusals_ts ON concern_refusals (ts);
