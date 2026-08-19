-- What the claim door turned away (P3 Phase 1, epic E1.2).
--
-- P3's decision rule for Phase 1 says to diagnose in order: *are its claims
-- resolvable at all* — if not, its concerns are unfalsifiable by construction
-- and the openers are the fix — then does the resolver run, then does the cost
-- reach the position. The first question is unanswerable unless refusals are
-- written down. An empty `resolutions` table otherwise has two readings that
-- look identical from outside: the being never commits to anything checkable,
-- or it tries constantly and the door rejects every attempt. Those call for
-- opposite fixes.
--
-- This is the same shape as `source_gaps` — the record of a reach that found
-- nothing — and it exists for the same reason: a refusal that leaves no trace
-- is indistinguishable from an attempt never made.
--
-- Deliberately NOT deliberation_log: `spent_today` counts every row there as
-- an attempt against the daily deliberation budget (R-18), so logging refusals
-- into it would charge the being for the door's strictness and slow the very
-- loop that produces claims.
--
-- `declined` is not recorded here. The being answering "nothing here is worth
-- claiming" is the ordinary outcome, like triage keeping nothing; only a claim
-- the being DID make and the door would not admit is a refusal.
--
-- Writer: newz/resolutions/door.py. Reader: tools/claims.py --refused.
CREATE TABLE IF NOT EXISTS claim_refusals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL NOT NULL,
    concern_id INTEGER,              -- not a FK, for 0020's reason
    reason     TEXT NOT NULL,        -- which of the door's checks refused it
    claim      TEXT NOT NULL DEFAULT '',
    condition  TEXT NOT NULL DEFAULT '',
    resolver   TEXT NOT NULL DEFAULT '',
    due_text   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_claim_refusals_ts ON claim_refusals (ts);
