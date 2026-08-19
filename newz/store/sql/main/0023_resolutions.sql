-- The claim that the world can settle (P3 Phase 1, epic E1.1).
--
-- The being's grounding mix is 50% itself and 33% the operator; ≤17% is the
-- world (measured 2026-08-18, 119 refs). With one operator and no readers,
-- the only thing available to contradict it that is neither itself nor the
-- operator is **the world's own facts** — and a fact can only contradict a
-- claim that was specific enough to be wrong, stated before the fact was
-- known, and pointed at a source that settles it.
--
-- That is what this table is: claim, condition, date, resolver, outcome,
-- provenance. Nothing here judges the claim; it makes the claim judgeable.
--
-- Three things the schema itself refuses, because a claim that lacks them
-- cannot be settled and would sit open forever looking like work:
--
--   * a claim with no resolution condition — INV-034's discipline, which
--     concerns already carry as `closing_condition`, applied to claims;
--   * a claim with no named resolver;
--   * a claim with no date, which is how "I was right eventually" survives.
--
-- Rule 4 is the fourth refusal and cannot be a CHECK: the resolver may not be
-- the being's own model. A judge that is the being is not evidence, and a
-- claim resolved by asking the substrate what it thinks would launder the
-- being's opinion into the world's verdict — the exact failure Phase 1 exists
-- to correct. That check lives in the writer (newz/resolutions/store.py),
-- where the configured role models are known.
--
-- `outcome` stays NULL while the claim is open. It is written once, by the
-- resolver pass (E1.3), and E1.5 makes it permanent: nothing prunes a
-- resolved-against claim, because a record of error that can be tidied away
-- is not a record of error. Hygiene does not touch this table.
--
-- `provenance` is deliberately TEXT and not a foreign key, for 0020's reason:
-- a claim outlives the concern that prompted it, and a closed concern must
-- not cascade away the being's own wrongness.
--
-- Writer: newz/resolutions/store.py open_claim(). Readers: the same module's
-- get_claim/due_claims/claims_by_status, and tools/claims.py.
CREATE TABLE IF NOT EXISTS resolutions (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    opened_at            REAL NOT NULL,
    claim                TEXT NOT NULL,
    resolution_condition TEXT NOT NULL,
    resolver             TEXT NOT NULL,
    due_at               REAL NOT NULL,
    provenance           TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'open',
    outcome              TEXT,
    settled_at           REAL,
    settled_by           TEXT,
    settled_note         TEXT,

    CHECK (TRIM(claim) <> ''),
    CHECK (TRIM(resolution_condition) <> ''),
    CHECK (TRIM(resolver) <> ''),
    CHECK (due_at > 0),
    CHECK (TRIM(provenance) <> ''),
    CHECK (status IN ('open', 'resolved')),
    -- held: the world agreed. contradicted: the world did not. An open claim
    -- has no outcome, and a resolved one must have one — a claim cannot be
    -- quietly marked done without saying which way it went.
    CHECK (outcome IS NULL OR outcome IN ('held', 'contradicted')),
    CHECK ((status = 'open'     AND outcome IS NULL AND settled_at IS NULL)
        OR (status = 'resolved' AND outcome IS NOT NULL AND settled_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_resolutions_due ON resolutions (status, due_at);
CREATE INDEX IF NOT EXISTS idx_resolutions_opened ON resolutions (opened_at);
