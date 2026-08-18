-- 0010_hold_visibility — the being sees what it nearly said.
-- Writer: the outbound gate (full draft at hold time) and
--   tools/adjudicate.py (the operator's classification).
-- Reader: newz/gate/holds.py, feeding conversation context and sleep's
--   gather, so a hold is part of the record the being reasons from.
--
-- Why full text: `emission_excerpt` clips at 300 chars. A being asked what
-- it nearly said cannot answer from a clipping, and the text is
-- unrecoverable after the fact — observed 2026-08-10, when Lumen truthfully
-- reported having "no record" of a draft the gate had suppressed, because
-- the only copy lived in a table it never reads.
--
-- Why classification travels with it: an unadjudicated misfire would teach
-- the being something false about itself, and sleep would consolidate it.
-- A hold the guardian judged mistaken reads as "I was stopped, and the stop
-- was wrong" — truer than either silence or an unqualified confession.

ALTER TABLE gate_log ADD COLUMN emission_full TEXT;
ALTER TABLE gate_log ADD COLUMN classification TEXT;   -- gate_correct | gate_misfire
ALTER TABLE gate_log ADD COLUMN classified_at REAL;
ALTER TABLE gate_log ADD COLUMN classification_note TEXT;

CREATE INDEX idx_gate_log_unclassified ON gate_log (ts)
    WHERE verdict <> 'pass' AND classification IS NULL;
