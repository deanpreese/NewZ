-- How deeply a source was actually read.
--
-- S2 §9.1: "Extraction depth is adaptive: headline-level by default,
-- full-extraction only for material that touches a concern." Only the default
-- half was built, and until 2026-08-15 nothing recorded which half had run —
-- so "the retrieval slice contains only the headline", which the being wrote
-- into its own source-gap record eight times per concern, could not be
-- confirmed from the store.
--
-- `depth` is 'abstract' or 'full'. `chunks` is how many extraction calls the
-- document cost, which is the honest per-read price for the diet: an abstract
-- is one call, a full document is up to six.
ALTER TABLE ingest_log ADD COLUMN depth TEXT NOT NULL DEFAULT 'abstract';
ALTER TABLE ingest_log ADD COLUMN chunks INTEGER NOT NULL DEFAULT 1;
