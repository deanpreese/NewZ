-- 0040_source_gap_cause — P4 W12a.
-- Writer: newz/world/research.py::record_gap, once per failed research pass.
-- Reader: newz/surface/generate.py::_questions renders repeat failures by
--   query and cause; tools/source_review.py groups them on demand.
--
-- **The record could not say which filter rejected.** `gap` was a composed
-- sentence and that was the whole of the diagnosis. Two stages reject a
-- candidate — an embedding floor at 0.35, then a triage call — and a floor
-- that cut everything at 0.34 produced the same row as a model that read six
-- summaries and refused all six. Different failures, different remedies, one
-- record.
--
-- 32 rows on 2026-08-21 said: 28 "nothing was relevant enough to read", 4
-- "nothing usable was extracted", and **zero** of the two cases that mean the
-- diet needs widening — "no source answered" and "I have already read
-- everything my sources return for this". The being is not short of sources.
-- Anyone reading only the count would have added some.
--
-- The counts are facts the research pass already held and threw away, so this
-- plumbs an existing measurement to the record rather than making a new one.
-- Nothing here is model-graded: which stage rejected, and how many, are
-- mechanical.
--
-- Expand-only. Rows written before this carry NULL, and NULL means "written
-- before the cause was recorded" rather than "no cause" — the readers say so
-- rather than counting them as a fifth category.

ALTER TABLE source_gaps ADD COLUMN cause TEXT;              -- no_source | all_already_read | floor | triage | capped | extraction
ALTER TABLE source_gaps ADD COLUMN candidates INTEGER;      -- results the adapters returned
ALTER TABLE source_gaps ADD COLUMN rejected_floor INTEGER;  -- cut by the 0.35 embedding floor
ALTER TABLE source_gaps ADD COLUMN rejected_triage INTEGER; -- refused by the triage call
ALTER TABLE source_gaps ADD COLUMN capped INTEGER;          -- deferred by an outlet share cap, never rejected
ALTER TABLE source_gaps ADD COLUMN already_read INTEGER;    -- found again, and read before
ALTER TABLE source_gaps ADD COLUMN best_score REAL;         -- highest relevance seen; says whether 0.35 is the problem

CREATE INDEX idx_source_gaps_cause ON source_gaps (cause, query);
