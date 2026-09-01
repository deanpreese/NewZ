-- 0049_concern_revivals — a concern that circled slowly is not a dead one.
-- Writer: newz/concerns/store.py (revive), from the deliberation cycle.
-- Reader: tools/health.py and this file's own record; the concern's setbacks
--   are untouched, so the record of having stalled survives the revival.
--
-- **Why.** `record_setback` writes `status='stalled'` at STALL_LIMIT = 5 and
-- nothing in the codebase ever writes it back to 'open'. Measured 2026-08-31:
-- 102 of 145 concerns stalled, 35 closed, 8 abandoned, **0 open** — and with
-- no open concern `load_active` returns nothing, `choose_concern` returns
-- None, and deliberation stops. It stopped at 19:09 and had not run for
-- eleven hours when the health check found it.
--
-- **What the counter conflates.** Concern 116 accumulated its five stalls
-- over 330 hours. Concern 144, opened the morning the pool ran dry,
-- accumulated five in 8.3. `stall_count` treats those as the same object and
-- they are not: circling is a RATE, and five circles spread over two weeks is
-- a hard concern rather than an impossible one. 69 of the 102 circled at a
-- setback a day or faster; 27 did not, and those 27 are what this revives.
--
-- **It is bounded by the counter it does not reset.** A revival decrements
-- `stall_count` by one, so it buys exactly one more attempt before the
-- concern stalls again, and a concern that then circles fast raises its own
-- rate out of eligibility. Nothing here can produce an immortal concern.

CREATE TABLE IF NOT EXISTS concern_revivals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    concern_id   INTEGER NOT NULL REFERENCES concerns(id),
    setbacks     INTEGER NOT NULL,      -- what it had accumulated
    over_days    REAL    NOT NULL,      -- and how long it took
    stall_count  INTEGER NOT NULL       -- what it was left at
);
CREATE INDEX IF NOT EXISTS idx_concern_revivals_ts ON concern_revivals (ts);
