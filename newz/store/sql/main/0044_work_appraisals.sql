-- 0044_work_appraisals — the operator's verdict on a piece.
-- Writer: tools/appraise.py (the operator, by hand).
-- Readers: newz/works/appraisal.py — undelivered notes for the re-read prompt
--   and the current verdict for the surface; newz/surface/generate.py, which
--   withholds a piece whose newest verdict is 0.
--
-- **The verdict the being cannot give itself.** Every judgement already in the
-- writing loop answers "is this correct?" — the re-read has revised two pieces
-- on mechanism and both were real. Nothing answers "is this worth reading?",
-- and that is a rule rather than an omission: `compose.py` refuses a quality
-- judge because a judge that is the being's own model produces operation and
-- never evidence (Rule 4), and TRUE_NORTH §1/§4.5/§10 puts readiness in the
-- operator's judgement alone, with no rubric. The verdict was reserved for the
-- operator and then never collected. This is the row to put it in.
--
-- **`publishable` is a yes/no answer** *(operator, 2026-08-24)*. NOT NULL and
-- CHECKed to 0 or 1: no NULL verdict, no "maybe", no scale. An unappraised
-- piece has no row, which is the absence of an answer rather than a third kind
-- of answer — and it is the structural half of the promise that this never
-- grows a rubric, because the schema cannot hold a score for one to be built
-- from.
--
-- **A table and not two columns on `works`, because notes accumulate.** The
-- operator appraises, the being revises, the operator appraises the revision.
-- Each of those must reach the being once and only once, which columns cannot
-- express: they hold one verdict and overwrite. `delivered_at` is per row.
--
-- **Delivery is at-least-once, deliberately.** The stamp is written in the
-- transaction that records the re-read outcome, after the verdict has been
-- applied — never at prompt-build time. One re-read in six has already failed
-- in life and `review()` carries a documented ~12% parse failure before its
-- retry, so a stamp written early would consume notes into silence. A
-- duplicated note is cheap; a swallowed one is invisible, because
-- delivered-and-lost looks exactly like delivered-and-heeded.
--
-- **No episode is written from this table.** Trigger
-- `self_output_is_self_and_undigested` (0032) aborts any episode whose
-- source_ref matches `work:%` unless it is provenance='self' and
-- digest_eligible=0. An appraisal episode written as `work:16` would therefore
-- be forced non-digestible and never reach sleep — the path would look built
-- and be dead. Whoever adds consolidation must use an `appraisal:` source_ref,
-- because the operator's judgement is the one thing here that is NOT the
-- being's own output.

CREATE TABLE work_appraisals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    work_id      INTEGER NOT NULL REFERENCES works(id),
    publishable  INTEGER NOT NULL CHECK (publishable IN (0, 1)),
    note         TEXT NOT NULL DEFAULT '',
    delivered_at REAL,
    deliver_fails INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_work_appraisals_work ON work_appraisals (work_id, ts);
CREATE INDEX idx_work_appraisals_undelivered
    ON work_appraisals (work_id) WHERE delivered_at IS NULL;

-- **What a revision used to lose.** `apply_verdict` rewrites title and body and
-- did not touch `signature`, so the first revision of a signed piece would make
-- `read_works.py --verify` report it ALTERED — "edited since it was written",
-- which for a body of work is the thing a signature exists to catch. It never
-- fired because the only two pieces ever revised (works 1 and 4) predate E3.1
-- and are unsigned; works 6 onward are all signed. This proposal's whole
-- purpose is to cause more revisions, so it is the trigger as well as the fix.
--
-- The signature now moves with the text and the prior one is kept here, beside
-- the prior title and body it attested to. A revised piece is the same piece
-- saying something new: its current signature attests to what it says now, and
-- the chain back to what it said before is unbroken.
ALTER TABLE work_revisions ADD COLUMN prior_signature TEXT;
