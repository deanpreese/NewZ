-- 0036_works_first_class — P4 epic E3.1.
-- Writer: newz/works/compose.py::write_work, at the moment the piece lands.
-- Readers: tools/read_works.py (--history, --subjects, --verify), and the
--   generator at E3.2, which is what "the generator consumes them" means.
--
-- E0.1's minimal row grows up. What was missing is everything that makes a
-- piece a piece of WORK rather than a stored string:
--
--   signature             sha256 over the subject, title and body as written.
--                         Makes the stored piece tamper-evident, and gives
--                         E3.5's byte-comparable regeneration something to
--                         compare against.
--   constitution_version  what the being had committed to when it wrote this.
--   perspective_version   what it held when it wrote this. A piece read a year
--                         later is read against the self that wrote it, not
--                         the self reading it — which is the whole point of
--                         E2.2's re-reading.
--   evidence_json         the refs its subject rested on, captured at write
--                         time. A concern's advances move and a position's
--                         evidence decays; what grounded THIS piece does not.
--
-- Backfill is deliberately absent. The four pieces written before this cannot
-- be signed honestly — a signature computed now would attest to the row as it
-- stands rather than to what was written, which is exactly the assurance a
-- signature is supposed to give. They read as unsigned and say why.

ALTER TABLE works ADD COLUMN signature TEXT;
ALTER TABLE works ADD COLUMN constitution_version INTEGER;
ALTER TABLE works ADD COLUMN perspective_version INTEGER;
ALTER TABLE works ADD COLUMN evidence_json TEXT;

CREATE INDEX idx_works_signature ON works (signature);
