-- 0009_embeddings — P2 Phase 1.3.
-- Writer: tools/embed_episodes.py and the conversation path (new episodes).
-- Reader: newz/memory/retrieval.py.
--
-- v1's imported vectors came from a different embedder and are untrusted;
-- clearing them here means retrieval can never silently compare across two
-- vector spaces. `embedding_model` records which embedder produced a vector
-- so the same mistake cannot recur when the model is swapped.

ALTER TABLE episodes ADD COLUMN embedding_model TEXT;

UPDATE episodes SET embedding = NULL WHERE embedding IS NOT NULL;

CREATE INDEX idx_episodes_unembedded ON episodes (id)
    WHERE embedding IS NULL AND digest_eligible = 1;
