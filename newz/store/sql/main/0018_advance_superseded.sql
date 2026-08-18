-- An advance may replace an earlier one rather than sit beside it.
--
-- S2 §8.3 requires "novelty against the whole advance history", and the whole
-- history is what was compared — so an advance that SUPERSEDED an earlier one
-- was judged a restatement of the thing it replaced. Measured 2026-08-15:
-- concern 111 at 09:03:44, rejected at novelty 0.18, where the summary began
-- "I recognize that my previous 'structural isomorphism' was a static
-- comparison that failed to address the historical mechanism". It resembled
-- the prior advance because it superseded it; refinement is what advancing a
-- concern looks like, and cosine distance cannot tell it from repetition.
--
-- The row is never deleted. It is the record of what the being once held, and
-- sleep, retrieval and the episode log all still see it. What `superseded_by`
-- changes is only which advances the NOVELTY CHECK compares against — which
-- also stops that history growing monotonically, so a concern's later
-- advances stop facing a harder test than its early ones.
ALTER TABLE concern_advances ADD COLUMN superseded_by INTEGER
    REFERENCES concern_advances (id);

CREATE INDEX idx_concern_advances_live
    ON concern_advances (concern_id, ts) WHERE superseded_by IS NULL;
