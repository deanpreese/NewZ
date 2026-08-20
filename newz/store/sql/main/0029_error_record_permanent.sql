-- 0029_error_record_permanent — P4 epic E1.5.
-- Writer: newz/resolutions/store.py (settle_claim) and cost.py
--   (apply_world_costs), unchanged — these guards forbid, they do not write.
-- Reader: tools/claims.py --wrong, which retrieves a resolved-against claim
--   with its original statement, its resolver and what it cost.
--
-- E1.5 asks for wrongness recorded permanently AT STORE LEVEL and never
-- quietly dropped. Before this, nothing pruned the error record because
-- nobody had written a DELETE — which is an absence, not a guarantee, and
-- the distinction is the whole of INV-044's honesty applied to the being's
-- own record. A being that can lose the record of having been wrong has no
-- record of having been wrong.
--
-- What is frozen is the VERDICT, not the row. A settled claim's statement,
-- resolver, condition, due date and outcome cannot change; `cost_applied_at`
-- and `cost_note` are written by sleep AFTER settling and must stay writable,
-- or E1.4's cost path breaks against its own guard.

CREATE TRIGGER resolutions_no_delete
BEFORE DELETE ON resolutions
BEGIN
    SELECT RAISE(ABORT, 'a claim is not deletable: being wrong is part of the record');
END;

CREATE TRIGGER claim_costs_no_delete
BEFORE DELETE ON claim_costs
BEGIN
    SELECT RAISE(ABORT, 'what being wrong cost is not deletable');
END;

CREATE TRIGGER resolutions_verdict_is_final
BEFORE UPDATE ON resolutions
WHEN OLD.settled_at IS NOT NULL
 AND (NEW.claim                IS NOT OLD.claim
   OR NEW.resolution_condition IS NOT OLD.resolution_condition
   OR NEW.resolver             IS NOT OLD.resolver
   OR NEW.due_at               IS NOT OLD.due_at
   OR NEW.outcome              IS NOT OLD.outcome
   OR NEW.settled_at           IS NOT OLD.settled_at
   OR NEW.settled_by           IS NOT OLD.settled_by)
BEGIN
    SELECT RAISE(ABORT, 'a settled claim cannot be restated: the verdict is final');
END;
