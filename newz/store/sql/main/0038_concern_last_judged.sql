-- 0038_concern_last_judged — the closure sweep's cooldown.
-- Writer: newz/concerns/sweep.py::sweep, one stamp per concern judged.
-- Reader: the same module's eligibility query, which will not re-judge a
--   concern inside JUDGE_COOLDOWN_HOURS.
--
-- **Why a sweep exists at all.** Closure was welded to progress. `_maybe_close`
-- had exactly one caller — immediately after an advance was recorded — so a
-- concern could only be recognised as finished as a side effect of moving it
-- further. A concern with nothing left to move could not be noticed, however
-- completely it had already answered its own question.
--
-- Measured 2026-08-20: 8 of 23 eligible stalled concerns met their closing
-- condition on their EXISTING dossiers, with no retrieval at all. That number
-- is model-graded and unreplicated, so under INV-073 it may halt and may never
-- justify — it is the reason to look, not the warrant. The warrant is
-- mechanical: 77 concerns sit stalled with both counters BELOW the limits that
-- produce a stall, a state the current code cannot create, and for every one
-- of them closure is structurally unreachable.
--
-- **The cooldown is what stops this becoming a tax.** 15 of the 23 did not
-- close and will not close on an unchanged dossier; without a stamp the sweep
-- would re-judge them every run, one DEEP call each, forever.

ALTER TABLE concerns ADD COLUMN last_judged_at REAL;

CREATE INDEX IF NOT EXISTS idx_concerns_sweep
    ON concerns (status, stall_count, blocked_count, last_judged_at);
