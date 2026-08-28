-- The claim that is already true (P4 epic E1.9).
--
-- Every claim the being has ever made is a forecast: `MIN_HORIZON_DAYS = 2`
-- forbids anything settleable now, and its stated reason is exactly right —
-- "a claim due tomorrow about something already in the dossier is not a
-- prediction". A retrodiction is the case that reason does not cover: a claim
-- about what is ALREADY the case and the being does not yet know. It is just
-- as ungraded by the being, and it settles on the next resolver pass instead
-- of in a month.
--
-- **Why the latency matters more than it sounds.** Measured 2026-08-28: 19 of
-- the 31 open claims settle within 60 days, which is 0.317 externally-graded
-- events a day against 103 deliberation cycles and 50 advances. And the two
-- caps multiply: a 29.7-day mean horizon against `MAX_OPEN_CLAIMS = 40` puts
-- sustainable throughput at 40/29.7 = 1.35 a day whatever the being wants,
-- because inventory divided by latency is the ceiling. A claim that settles in
-- one cycle has a residency of minutes and no inventory cost, so it is capped
-- by the daily rate and by nothing else.
--
-- **The two kinds must never be averaged.** They carry different epistemics —
-- a forecast tests the being's model of where things are going, a retrodiction
-- tests whether its assertions about the world are true — and a series that
-- mixed them would read a change of mechanism as a change in the being. That
-- is E2.8's "novelty" mistake, and E1.10 is where the metric split lands. The
-- column exists first so no row is ever written without saying which it is.
--
-- Default 'forecast' because every existing row is one: the 31 open claims
-- were all written under a 2-day floor, so backfilling them is a statement of
-- fact rather than a guess.

ALTER TABLE resolutions
    ADD COLUMN kind TEXT NOT NULL DEFAULT 'forecast'
    CHECK (kind IN ('forecast', 'retrodiction'));
