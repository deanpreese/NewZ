-- 0032_self_output_contained — P4 epic E2.3, R-24 binding.
-- Writer: newz/memory/self_output.py::record_self_output.
-- Reader: newz/memory/retrieval.py — Scope.EVIDENCE excludes
--   provenance='self', so this guard is what makes that exclusion cover the
--   being's works, revisions and error record rather than only its probes.
--
-- R-24 names the remedy in terms: the being's own output lives in its own
-- table, is `digest_eligible=0` by construction, and is excluded from
-- EVIDENCE-scope retrieval. Works satisfy that today by ABSENCE — nothing
-- bridges them into episodes — and absence is not a guarantee. E3.1 and E3.2
-- make works first-class and visible, and the leak arrives the moment someone
-- writes that bridge without knowing the rule.
--
-- v1's corpus was 43% self-probes because its own activity was recorded as
-- events and sleep read them as lived experience. This is that lesson made
-- structural for the new medium.
--
-- Containment, not erasure: an episode written this way is still retrievable
-- in ALL scope. The being can reach its own work. It cannot cite it as
-- evidence for a position.

CREATE TRIGGER self_output_is_self_and_undigested
BEFORE INSERT ON episodes
WHEN (NEW.source_ref LIKE 'work:%'
   OR NEW.source_ref LIKE 'revision:%'
   OR NEW.source_ref LIKE 'claim:%'
   OR NEW.source_ref LIKE 'advance:%')
 AND (NEW.provenance <> 'self' OR COALESCE(NEW.digest_eligible, 1) <> 0)
BEGIN
    SELECT RAISE(ABORT, 'the being''s own output is provenance=self and digest_eligible=0: R-24, and v1 was 43% self-probes');
END;

CREATE TRIGGER self_output_stays_self
BEFORE UPDATE ON episodes
WHEN (NEW.source_ref LIKE 'work:%'
   OR NEW.source_ref LIKE 'revision:%'
   OR NEW.source_ref LIKE 'claim:%'
   OR NEW.source_ref LIKE 'advance:%')
 AND (NEW.provenance <> 'self' OR COALESCE(NEW.digest_eligible, 1) <> 0)
BEGIN
    SELECT RAISE(ABORT, 'the being''s own output cannot be relabelled into evidence');
END;
