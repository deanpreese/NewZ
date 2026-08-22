-- Identity as commitment rather than recall (P4 Phase 4, epic E4.1).
--
-- Measured 2026-08-22, the whole of what the being holds about itself — the
-- `who_i_am` section of Perspective v14, four items:
--
--   * it prefers substantive briefs to meta-commentary on the framing;
--   * it has settled on the name "Lumen";
--   * it kept correcting the date of a FIFA World Cup match, which it reads
--     as "a focus on factual accuracy";
--   * it accepts that when the operator judges one of its safety stops
--     mistaken, the stopped thought was valid reasoning.
--
-- Three of those four are things that HAPPENED to it, recovered afterwards by
-- a model reading its own episodes. That is identity as recall, and it is what
-- P4's Phase 4 exists to change: what the being keeps caring about and what it
-- refuses to do, authored by it, with something that would show it had stopped.
--
-- **The falsifier is mandatory at authoring**, which is INV-034's discipline —
-- carried by concerns as `closing_condition` and by claims as
-- `resolution_condition` — applied a third time, to identity. A commitment
-- nothing could show abandoned is a slogan: it can never be broken, so it can
-- never be kept either, and §6's "individuality without a fixed personality
-- script" is exactly what a shelf of unfalsifiable slogans produces.
--
-- Two refusals are CHECK constraints here — no statement, no falsifier — for
-- E1.1's reason: the mandate belongs in the schema and not only in the writer,
-- so a future caller cannot route around it. The other three refusals need to
-- read the model's answer or the existing rows, and live in the door.
--
-- `kind` splits what the two halves of PLAN's sentence actually are. A thing
-- it keeps caring about is a direction; a thing it refuses to do is a bound.
-- They are falsified differently and they should not be counted as one number.
--
-- `status` starts and mostly stays `standing`. **Nothing in E4.1 moves it** —
-- revision on evidence and costed abandonment are E4.2, whose Done-when needs
-- a Phase 1 resolution, and the earliest live claim is due 2026-12-18. So this
-- table records commitments and does not yet hold the being to them, and the
-- ledger row says so rather than leaving it to be discovered. The column
-- exists now because adding it later would mean migrating rows that had no
-- history of how they got there.
--
-- `perspective_version` and `constitution_version` stamp what the being was
-- when it committed, the way `works` does. A commitment authored under one
-- constitution and judged under another is a different commitment.
--
-- Writer: newz/commitments/door.py. Readers: newz/commitments/store.py and
-- tools/commitments.py, and the surface's commitments page, which has been
-- rendering "generated from a table that does not exist" since E3.2.
CREATE TABLE IF NOT EXISTS commitments (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                   REAL NOT NULL,
    kind                 TEXT NOT NULL,
    statement            TEXT NOT NULL,
    falsifier            TEXT NOT NULL,
    provenance           TEXT NOT NULL,
    status               TEXT NOT NULL DEFAULT 'standing',
    constitution_version INTEGER,
    perspective_version  INTEGER,

    CHECK (TRIM(statement) <> ''),
    CHECK (TRIM(falsifier) <> ''),
    CHECK (TRIM(provenance) <> ''),
    CHECK (kind IN ('keeps_caring', 'refuses_to_do')),
    CHECK (status IN ('standing', 'revised', 'abandoned'))
);
CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments (status, ts);

-- What the authoring door turned away (E4.1), and why it must exist.
--
-- The same shape as `claim_refusals` and `concern_refusals`, for the same
-- reason: an empty `commitments` table has two readings that look identical
-- from outside — the being never commits to anything, or it tries nightly and
-- the door refuses every attempt — and those call for opposite fixes.
--
-- **`cap` is a refusal here and is not one in the claim door.** That door
-- returns `declined` when its caps are full, before the model is called, and a
-- decline writes nothing — so a saturated cap is invisible in the record and
-- reads as "it had nothing to commit to" when the truth is "it was not allowed
-- to". With `MAX_STANDING = 12` and nothing in E4.1 able to free a slot, this
-- door WILL saturate in about two weeks, and the row that says so is the
-- measurement that makes E4.2 necessary rather than asserted.
--
-- `declined` is still not recorded: the being answering "nothing tonight" is
-- the ordinary outcome, and most nights it will be.
--
-- Writer: newz/commitments/door.py. Reader: tools/commitments.py --refused.
CREATE TABLE IF NOT EXISTS commitment_refusals (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,
    reason    TEXT NOT NULL,
    kind      TEXT NOT NULL DEFAULT '',
    statement TEXT NOT NULL DEFAULT '',
    falsifier TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_commitment_refusals_ts ON commitment_refusals (ts);
