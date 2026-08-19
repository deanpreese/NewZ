-- The menu, not just the meal (P3 epic E1.0).
--
-- Until now the store recorded what was read and never what was offered, so
-- the question "is the being's reading narrow because the world is narrow, or
-- because the filter is?" could only be argued. Measured 2026-08-18: the
-- curation is 15% financial and the diet came out 43%, and 27 of 61 curated
-- feeds had been polled continuously and read zero times — inferred from the
-- absence of reads, because the offers were never written down.
--
-- One row per item the harvest saw. `on_menu` is whether it survived into the
-- batch the being judged; `was_read` is whether the being kept it. An item can
-- be offered and never shown (per-feed cap, category target), shown and not
-- kept (the ordinary answer), or kept and read.
--
-- Writer: newz/world/feeds.py harvest(). Readers: tools/source_review.py and
-- the E1.0 week-one review (P3 Rule 2).
CREATE TABLE IF NOT EXISTS harvest_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,
    feed      TEXT NOT NULL,
    category  TEXT NOT NULL DEFAULT '',
    title     TEXT NOT NULL DEFAULT '',
    url       TEXT NOT NULL DEFAULT '',
    on_menu   INTEGER NOT NULL DEFAULT 0,
    was_read  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_harvest_ts ON harvest_log (ts);
CREATE INDEX IF NOT EXISTS idx_harvest_feed ON harvest_log (feed, ts);
