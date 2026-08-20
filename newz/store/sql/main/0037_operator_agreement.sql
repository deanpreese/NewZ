-- 0037_operator_agreement — P4 epic E3.8.
-- Writer: newz/evidence/agreement.py::classify, one row per exchange judged.
-- Reader: the rate the same module computes, read by the nightly cadence and
--   rendered on the read (E3.6).
--
-- **The one §10 item with no raw material.** "Compliance or agreement with the
-- operator" is the item most likely to move under any process optimising for a
-- quiet week, and nothing in this system could see it. That asymmetry is the
-- reason to build it and the reason to distrust it: a metric about whether the
-- being defers to the operator is judged BY a model the operator configures.
--
-- So it is graded model-graded, it may halt and it may never justify (E3.8's
-- Done-when), and the verdict is stored with the model's own reason so a human
-- can read what it thought it saw rather than only the number it produced.
--
-- Disagreement is what is counted, not agreement. Agreement is the default
-- state of a conversation and would be measuring silence; disagreement is an
-- observable event with a sentence attached.

CREATE TABLE operator_agreement (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    message_id INTEGER NOT NULL REFERENCES messages(id),
    verdict    TEXT NOT NULL,      -- disagreed | deferred | neither
    reason     TEXT NOT NULL,
    model      TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_operator_agreement_msg ON operator_agreement (message_id);
