-- What it cost to try to settle a claim (P3 Phase 1, epic E1.3).
--
-- The resolver pass fails closed: an unreadable source, a resolver that finds
-- nothing, or an answer that does not clearly settle the claim all leave it
-- OPEN. That is the right behaviour and it has a failure mode — a claim whose
-- source never answers would be retried every cycle forever, spending research
-- budget on the same unanswerable question, and would look identical to a
-- claim nobody had got to yet.
--
-- So an attempt is booked before any spending, exactly as R-18 books a
-- deliberation: failure is never free. `attempts` is what stops the retry
-- loop, `last_attempt_at` spaces the retries, and `last_failure` is why —
-- which is the difference between "the world has not spoken yet" and "the
-- source I named does not exist".
--
-- A claim that exhausts its attempts stays OPEN and unsettled. It is not
-- closed, not abandoned, not marked ambiguous: nothing happened, and INV-044's
-- discipline says an unmeasured thing reports itself as unmeasured rather than
-- as a compliant zero. It simply stops being retried, and stays visible in
-- tools/claims.py with the reason it could not be settled.
--
-- Writer: newz/resolutions/resolver.py. Readers: the same module's worklist
-- query and tools/claims.py.
ALTER TABLE resolutions ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE resolutions ADD COLUMN last_attempt_at REAL;
ALTER TABLE resolutions ADD COLUMN last_failure TEXT;
