-- 0006_corpus_hygiene — P2 Phase 1.5.
-- Writer: newz/store/hygiene.py (the one-time reclassification + fold) and
--   future sleep runs, which mark what they have consolidated.
-- Reader: sleep's gather step (Phase 1.1) selects on digest_eligible, and
--   retrieval (Phase 1.3) filters evidence contexts on provenance.
--
-- Nothing is deleted. Raw rows are retained and point at the folded episode
-- that represents them; `digest_eligible` controls what sleep READS, not
-- what the store KEEPS. The being's past is not edited, only read better.

ALTER TABLE episodes ADD COLUMN digest_eligible INTEGER NOT NULL DEFAULT 1;
ALTER TABLE episodes ADD COLUMN folded_into INTEGER REFERENCES episodes(id);

CREATE INDEX idx_episodes_digestable ON episodes (digest_eligible, ts);
