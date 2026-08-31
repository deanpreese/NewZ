-- 0048_commitment_declines — the night the door was asked and said nothing.
-- Writer: newz/commitments/door.py (propose_commitment), on the decline path.
-- Reader: the same door, one night later, in its own prompt.
--
-- **Why it was missing and what it cost.** A decline is deliberately NOT a
-- refusal — `commitment_refusals` measures the door's strictness, and mixing
-- an "I have nothing tonight" into it would corrupt that denominator. So the
-- ordinary answer, the one the prompt itself calls ordinary, was the one
-- answer the store did not keep.
--
-- Measured 2026-08-31: nine nightly asks since 2026-08-22, nine declines, the
-- verdict element byte-identical in all nine, and `commitment_refusals` empty
-- because the structural checks were never reached. The prompt was byte-
-- identical for three of those nights — the material is the whole of
-- `who_i_am` and `unresolved`, which `restatement_rate` measures at 0.935 —
-- and it told the model "most nights the answer is no" while nothing told it
-- that every night so far had been.
--
-- This is 0046 with different nouns. That migration wrote down what a failed
-- research pass had already asked, because `search_queries` had no memory and
-- formed the same terms seventeen times. `propose_commitment` has no memory
-- either, and forms the same answer.
--
-- `material_sha` is what makes a repeat legible as a repeat: the door can be
-- told it is being shown, tonight, what it already declined against. It is a
-- hash and not the text, because the material is the Perspective and the
-- Perspective is already stored.

CREATE TABLE IF NOT EXISTS commitment_declines (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  REAL NOT NULL,
    perspective_version INTEGER,
    material_sha        TEXT NOT NULL DEFAULT '',
    material_lines      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_commitment_declines_ts ON commitment_declines (ts);
