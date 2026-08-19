-- Being wrong costs the position (P3 Phase 1, epic E1.4).
--
-- INV-031 already makes a contradiction cost the position it contradicts —
-- but only when the contradiction comes from the being's own observations
-- during sleep. Measured 2026-08-12, that mechanism exists because a stale
-- self-description sat at 0.72 through three nights that each filed a fresh
-- tension against it. This is the same mechanism pointed OUTWARD: the
-- contradiction arrives from the world, through a claim the being made and
-- the resolver settled against it.
--
-- The trace is exact rather than judged. A claim's provenance names the
-- concern it came from; every episode that concern produced carries
-- `source_ref = 'concern:N'`; a Perspective item's evidence is a list of
-- episode ids. So the position that pays is the one whose own grounding
-- includes episodes from the concern that produced the refuted claim. No
-- model decides who pays — Rule 4 would forbid it anyway, since the being's
-- model choosing which of the being's positions to punish is the being
-- grading the being.
--
-- `claim_costs` is the measurable half of E1.4's done-when and the beginning
-- of E1.5's permanent record: what the claim was, which position paid, how
-- much, and whether that payment released it. Nothing prunes it.
--
-- A refuted claim that traces to no position is recorded as such
-- (`cost_note`) rather than left looking unprocessed. INV-044's discipline:
-- an unmeasured thing reports itself as unmeasured, never as a compliant
-- zero. It is a real and expected outcome — the being can be wrong about
-- something it never wrote into its Perspective.
--
-- Writer: newz/resolutions/cost.py, called by sleep (INV-009 keeps sleep the
-- only writer of the Perspective). Reader: tools/claims.py --wrong.
ALTER TABLE resolutions ADD COLUMN cost_applied_at REAL;
ALTER TABLE resolutions ADD COLUMN cost_note TEXT;

CREATE TABLE IF NOT EXISTS claim_costs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                REAL NOT NULL,
    claim_id          INTEGER NOT NULL,
    item_text         TEXT NOT NULL,     -- item ids change every version; text carries
    section           TEXT NOT NULL,
    confidence_before REAL NOT NULL,
    confidence_after  REAL NOT NULL,
    repeat            INTEGER NOT NULL DEFAULT 0,   -- the world has refuted this position before
    released          INTEGER NOT NULL DEFAULT 0    -- the cost took it under the floor
);
CREATE INDEX IF NOT EXISTS idx_claim_costs_claim ON claim_costs (claim_id);
