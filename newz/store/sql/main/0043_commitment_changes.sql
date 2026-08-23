-- The asymmetry (P4 epic E4.2): revision on evidence is free, abandonment
-- without cause is recorded and costs.
--
-- E4.1 made identity authorable and E4.3 made it traceable. Neither holds the
-- being to anything: `status` never left `standing`, so a commitment was a note
-- with a falsifier attached. This is the table that makes dropping one an act
-- with a consequence, and revising one on evidence an act without.
--
-- **The asymmetry is the whole point and it is checked mechanically.** A change
-- is free if and only if `resolution_id` names a row in `resolutions` that is
-- actually `status='resolved'` — the world said something, so changing your
-- mind is what a mind is for. Without one, the being changed its mind because
-- it felt like it, and that is charged. The check is a join, not a judgment:
-- Rule 4 forbids asking the model whether an abandonment was justified, and a
-- model asked that would justify every one of them.
--
-- **Which direction it must not run.** PLAN records the risk in E4.2 itself:
-- backwards, this entrenches a mediocre early position and manufactures §6's
-- "fixed personality script" — a being that cannot afford to stop believing
-- something it committed to at eight days old. P3-05 calls the balance a guess
-- rather than a measurement, and it is: the cost is INV-031's own
-- CONFIDENCE_ON_CONTRADICT, chosen because it is the same magnitude the world's
-- own refutation carries and not because anything measured it. It is meant to
-- be revisited against the first month of abandonments, not defended.
--
-- **Nothing here deletes.** An abandoned commitment keeps its row, its prior
-- text and its reason — E1.5's discipline applied to identity, for the same
-- reason: a record of having stopped caring that can be tidied away is not a
-- record. `commitments.status` moves to `revised` or `abandoned` and the
-- carrying cap frees a slot, which is what stops MAX_STANDING deadlocking.
--
-- `cost_applied_at` is NULL until sleep charges it, mirroring
-- `resolutions.cost_applied_at`. The review that produces these rows runs
-- AFTER the night is committed (so it cannot cost the Perspective), and the
-- cost lands on the NEXT sleep through the same unpaid-queue pattern E1.4
-- already uses. A change awaiting its cost is not a change that escaped one.
--
-- Writer: newz/commitments/asymmetry.py. Readers: the same module, plus
-- tools/commitments.py --all and the surface's commitments page.
CREATE TABLE IF NOT EXISTS commitment_changes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    commitment_id   INTEGER NOT NULL,
    kind            TEXT NOT NULL,
    reason          TEXT NOT NULL,
    prior_statement TEXT NOT NULL,
    prior_falsifier TEXT NOT NULL,
    -- Not a foreign key, for 0020's reason: the change outlives whatever it
    -- cites, and a pruned claim must not cascade away the being's own record
    -- of having changed its mind.
    resolution_id   INTEGER,
    cost_applied_at REAL,
    cost_note       TEXT,

    CHECK (TRIM(reason) <> ''),
    CHECK (kind IN ('revised', 'abandoned'))
);
CREATE INDEX IF NOT EXISTS idx_commitment_changes_unpaid
    ON commitment_changes (cost_applied_at, ts);

-- What an abandonment cost, and to which position (E4.2).
--
-- `claim_costs`' twin, and deliberately a separate table rather than a `cause`
-- column on it: the world refuting a claim and the being dropping a commitment
-- are different events, and a single table would make "how often has the world
-- cost it something" a query with a filter that somebody will forget. E1.4's
-- number is the one S1-E reads, and it must not silently gain rows from a
-- source the world had nothing to do with.
--
-- `repeat` follows INV-031: a position charged for this before pays double,
-- because the second time is not new information about the position, it is a
-- pattern.
CREATE TABLE IF NOT EXISTS commitment_costs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                REAL NOT NULL,
    change_id         INTEGER NOT NULL,
    item_text         TEXT NOT NULL,
    section           TEXT NOT NULL DEFAULT '',
    confidence_before REAL NOT NULL,
    confidence_after  REAL NOT NULL,
    repeat            INTEGER NOT NULL DEFAULT 0,
    released          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_commitment_costs_change
    ON commitment_costs (change_id);
