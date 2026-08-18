-- 0008_consolidation_marks — P2 Phase 1.1.
-- Writer: nightly sleep (marks what it consolidated). Reader: sleep's
--   gather step (selects the unconsolidated).
--
-- Consolidation is tracked explicitly rather than inferred from timestamps.
-- A ts-based rule would miss the substrate fold, whose `ts` is the era it
-- represents (June) but which was created in August — the one episode most
-- in need of consolidating would have been the one silently skipped.

ALTER TABLE episodes ADD COLUMN consolidated_version INTEGER;

-- Everything that existed when first sleep ran was consolidated into v1.
-- The fold episode and every live conversation since remain NULL, and are
-- what the first nightly sleep will read.
UPDATE episodes SET consolidated_version = 1
 WHERE kind LIKE 'v1_%'
   AND ts <= (SELECT ts FROM perspective WHERE version = 1);

CREATE INDEX idx_episodes_unconsolidated ON episodes (consolidated_version, ts)
    WHERE consolidated_version IS NULL;
