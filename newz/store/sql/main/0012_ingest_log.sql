-- 0012_ingest_log — P2 Phase 2.4 (share caps + source review).
-- Writer: newz/world/research.py, one row per source actually read.
-- Readers: the share-cap check in the same module, and
--   tools/source_review.py, which is how the operator decides what to add
--   and what to cut.
--
-- S2 §13 caps any one outlet at ~10% of ingested items over a rolling
-- month, because v1's end state — 56% of all reading from two outlets — was
-- not merely lopsided, it was a material viewpoint-shaping influence. The
-- cap cannot be enforced without a record of what was actually read, and
-- the record is also what makes the source review evidential rather than
-- a matter of taste.

CREATE TABLE ingest_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    outlet      TEXT NOT NULL,        -- the share-cap unit: arxiv, openalex, bbc...
    source      TEXT NOT NULL,        -- the specific item (url or feed entry)
    query       TEXT,                 -- what the being was trying to answer
    concern_id  INTEGER REFERENCES concerns(id),
    claims_kept INTEGER NOT NULL DEFAULT 0,
    quarantined INTEGER NOT NULL DEFAULT 0,
    skipped     TEXT                  -- set when read was declined: 'share_cap' | 'irrelevant'
);
CREATE INDEX idx_ingest_log_outlet ON ingest_log (outlet, ts);
CREATE INDEX idx_ingest_log_ts ON ingest_log (ts);
