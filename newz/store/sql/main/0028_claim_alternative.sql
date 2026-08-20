-- 0028_claim_alternative — R-35.
-- Writer: newz/resolutions/door.py — the being states what the other outcome
--   would look like, and the door refuses a claim whose alternative it cannot
--   state.
-- Reader: tools/claims.py, which renders it beside the claim.
--
-- The door's own prompt has always said "I could be wrong. If nothing would
-- surprise me, there is no claim here" — and then asked for no such judgment
-- and applied no check, so nothing in the system could tell a prediction from
-- a formality. Asking for the alternative is the cheapest thing that forces
-- the judgment the prompt already claims to want.

ALTER TABLE resolutions ADD COLUMN could_be_wrong TEXT;
