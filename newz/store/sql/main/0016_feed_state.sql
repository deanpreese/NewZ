-- Feed polling watermarks (S2 §9.1 "operator-curated feeds").
--
-- One row per feed, not one per item: dedup is a per-feed watermark on the
-- item timestamp, so 61 feeds cost 61 rows however long they run. Storing
-- every item seen would be ~1M rows a year to answer a question a single
-- float already answers.
--
-- Writer/reader: newz/world/feeds.py (P2 Rule 2).
CREATE TABLE IF NOT EXISTS feed_state (
    url            TEXT PRIMARY KEY,
    name           TEXT NOT NULL DEFAULT '',
    last_polled    REAL NOT NULL DEFAULT 0,
    last_item_ts   REAL NOT NULL DEFAULT 0,
    failures       INTEGER NOT NULL DEFAULT 0,
    last_error     TEXT
);
