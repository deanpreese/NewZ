import time

from newz.concerns.model import Concern
from newz.concerns.store import create_concern, load_dossier, record_advance
from newz.deliberation.lite import Deliberator
from newz.store.db import open_db
from newz.store.migrations import apply_pending
from tests.conftest import FakeLLM, LexicalEmbedder

from tests.test_migrations import MAIN_SQL
from tests.test_research import _call, _log


def _store(tmp_path, concerns=1):
    path = tmp_path / "newz.db"
    conn = open_db(path)
    apply_pending(conn, MAIN_SQL)
    ids = []
    for i in range(concerns):
        ids.append(create_concern(conn, Concern(
            id=None, statement=f"Do prediction markets price risk faster? #{i}",
            why_open="it bears on how I read signals",
            closing_condition="a comparison of announcement windows settles it",
            origin="conversation", opened_at=time.time() - 100 * 3600)))
    conn.commit()
    conn.close()
    return path, ids


def _reply(moved="yes", summary="Announcement windows differ because market makers "
           "hedge regulatory tail risk directly.", kind="reasoning", evidence="",
           blocked_on=""):
    return ("DEEP", f"""<deliberation>
  <moved>{moved}</moved>
  <summary>{summary}</summary>
  <kind>{kind}</kind>
  <evidence>{evidence}</evidence>
  <blocked_on>{blocked_on}</blocked_on>
</deliberation>""")


def test_a_concern_can_actually_move(tmp_path):
    path, (cid,) = _store(tmp_path)
    r = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder()).run_once()
    assert r.moved and r.kind == "reasoning" and r.concern_id == cid

    conn = open_db(path, read_only=True)
    d = load_dossier(conn, cid)
    assert d.concern.advance_count == 1
    assert d.concern.last_advanced_at is not None
    assert len(d.advances) == 1
    conn.close()


def test_honest_failure_is_recorded_as_blocked_and_costs_score(tmp_path):
    # S2 §7.4: "the world has not answered this" is a first-class outcome.
    path, (cid,) = _store(tmp_path)
    llm = FakeLLM([_reply(moved="no", summary="",
                          blocked_on="I need announcement-window data I do not have.")])
    r = Deliberator(path, llm, embedder=LexicalEmbedder()).run_once()
    assert not r.moved
    assert r.blocked_on.startswith("I need announcement-window")

    conn = open_db(path, read_only=True)
    d = load_dossier(conn, cid)
    assert d.concern.blocked_count == 1
    assert d.concern.stall_count == 0          # blocked is NOT stalled
    assert d.setbacks[0]["kind"] == "blocked"
    conn.close()


def test_a_restatement_is_a_setback_not_an_advance(tmp_path):
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Attention is the scarce resource, not information.",
                   kind="reasoning", evidence=[])
    # Seeded history, not an attempt in this test's timeline — otherwise the
    # §7.1 state trigger correctly reads "nothing new since the last attempt".
    conn.execute("UPDATE concerns SET last_attempted_at=NULL")
    conn.commit()
    conn.close()

    llm = FakeLLM([_reply(summary="It is attention that is scarce, not information.")])
    r = Deliberator(path, llm, embedder=LexicalEmbedder()).run_once()
    assert not r.moved
    assert "restates an earlier advance" in r.reason

    conn = open_db(path, read_only=True)
    d = load_dossier(conn, cid)
    assert d.concern.advance_count == 1        # unchanged
    assert d.concern.stall_count == 1          # circling costs
    conn.close()


def test_evidence_claims_are_checked_against_the_dossier(tmp_path):
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="An earlier grounded point about hedging costs.",
                   kind="evidence", evidence=["ep-7"])
    conn.execute("UPDATE concerns SET last_attempted_at=NULL")
    conn.commit()
    conn.close()

    # Cites something that never reached the dossier -> relabelled, not rejected.
    llm = FakeLLM([_reply(summary="A further distinct point about liquidity depth.",
                          kind="evidence", evidence="ep-999")])
    r = Deliberator(path, llm, embedder=LexicalEmbedder()).run_once()
    assert r.moved and r.kind == "reasoning"

    conn = open_db(path, read_only=True)
    assert load_dossier(conn, cid).advances[-1]["kind"] == "reasoning"
    conn.close()


def test_the_daily_budget_is_respected(tmp_path):
    path, (cid,) = _store(tmp_path)
    d = Deliberator(path, FakeLLM([]), daily_budget=0)
    r = d.run_once()
    assert r.skipped == "daily deliberation budget spent"


def test_no_active_concerns_is_not_an_invented_pursuit(tmp_path):
    # The original assertion still holds where it matters: nothing is
    # deliberated on and no pursuit is manufactured. What changed on
    # 2026-08-15 is that the cycle now goes LOOKING instead of returning —
    # with no feeds configured (the default here) that is a no-op.
    path, _ = _store(tmp_path, concerns=0)
    r = Deliberator(path, FakeLLM([]), embedder=LexicalEmbedder()).run_once()
    assert r.skipped and r.skipped.startswith("no active concerns")
    assert r.concern_id is None and not r.moved and r.opened == []


def test_unreadable_output_costs_nothing(tmp_path):
    path, (cid,) = _store(tmp_path)
    r = Deliberator(path, FakeLLM([("DEEP", "not xml")]),
                    embedder=LexicalEmbedder()).run_once()
    assert r.skipped and "unreadable" in r.skipped
    conn = open_db(path, read_only=True)
    d = load_dossier(conn, cid)
    assert d.concern.advance_count == 0 and d.concern.stall_count == 0
    conn.close()


def test_deliberation_is_budget_tagged(tmp_path):
    path, _ = _store(tmp_path)
    llm = FakeLLM([_reply()])
    Deliberator(path, llm, embedder=LexicalEmbedder()).run_once()
    # It must count on the EARNING side of the S2 §9.1 diet invariant.
    assert llm.calls[0]["function"] == "deliberation"


def test_repeated_blocking_eventually_lets_a_concern_go(tmp_path):
    from newz.concerns.model import BLOCKED_LIMIT

    path, (cid,) = _store(tmp_path)
    for _ in range(BLOCKED_LIMIT):
        llm = FakeLLM([_reply(moved="no", summary="", blocked_on="still missing the data")])
        Deliberator(path, llm, embedder=LexicalEmbedder(), daily_budget=999).run_once()
        # Each iteration stands for a separate occasion on which the world was
        # asked again; without clearing the stamp the §7.1 trigger correctly
        # skips the second and every one after it.
        c = open_db(path)
        c.execute("UPDATE concerns SET last_attempted_at=NULL")
        c.commit()
        c.close()
    conn = open_db(path, read_only=True)
    assert load_dossier(conn, cid).concern.status == "stalled"
    conn.close()


# ── RISKS R-18/R-19/R-20 ─────────────────────────────────────────────────

def test_a_failed_deliberation_still_costs_budget(tmp_path):
    # R-18: counting outcomes meant an unparseable run was free, so a
    # concern that reliably failed could be retried without limit.
    path, (cid,) = _store(tmp_path)
    d = Deliberator(path, FakeLLM([("DEEP", "not xml")]), embedder=LexicalEmbedder(),
                    daily_budget=1)
    first = d.run_once()
    assert first.skipped and "unreadable" in first.skipped

    second = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder(),
                         daily_budget=1).run_once()
    assert second.skipped == "daily deliberation budget spent"

    conn = open_db(path, read_only=True)
    outcomes = [r[0] for r in conn.execute("SELECT outcome FROM deliberation_log")]
    assert outcomes == ["started", "unreadable"]
    conn.close()


def test_the_attempt_is_booked_before_any_spending(tmp_path):
    # R-19: research must not be able to spend the diet on a run that never
    # produced a viable frame without that run being counted.
    path, (cid,) = _store(tmp_path)
    Deliberator(path, FakeLLM([("DEEP", "not xml")]), embedder=LexicalEmbedder(),
                daily_budget=5).run_once()
    conn = open_db(path, read_only=True)
    assert conn.execute(
        "SELECT COUNT(*) FROM deliberation_log WHERE outcome='started'"
    ).fetchone()[0] == 1
    conn.close()


def test_deliberation_stands_off_during_sleeps_window(tmp_path):
    # R-20: sleep yields the whole night when the store is busy.
    import datetime as dt

    from newz.deliberation.lite import DeliberationScheduler

    sched = DeliberationScheduler(
        Deliberator(tmp_path / "x.db", FakeLLM([])), quiet_hour=3, quiet_span_h=1.5)
    assert sched._in_quiet_window(dt.datetime(2026, 8, 12, 3, 0))
    assert sched._in_quiet_window(dt.datetime(2026, 8, 12, 4, 20))
    assert not sched._in_quiet_window(dt.datetime(2026, 8, 12, 4, 40))
    assert not sched._in_quiet_window(dt.datetime(2026, 8, 12, 20, 0))


# ── the claims path (RISKS R-22) ─────────────────────────────────────────
#
# Reproduced 2026-08-13. `618db9f` shipped the research opener as a call to
# `self._maybe_open_from_research(...)` that was never defined, so EVERY
# deliberation reaching claims died with AttributeError. It stayed invisible
# because the line only executes when research returns claims, and research
# was returning nothing until `43a4718` fixed question formation — which
# activated the crash. The 02:30 run of 2026-08-13 read four sources, threw
# there, and recorded no advance, no setback, and no `unreadable` row.
#
# The suite passed throughout: no test drove a real Deliberator down the
# claims path. This one does.

def _outcome_with_claims():
    from newz.world.research import ResearchOutcome

    return ResearchOutcome(
        query="prediction markets regulatory risk",
        claims=[("Announcement windows close within minutes.", 0.9),
                ("Equity chains reprice over days.", 0.8)],
    )


def test_a_deliberation_that_reaches_claims_still_finishes(tmp_path, monkeypatch):
    path, (cid,) = _store(tmp_path)
    monkeypatch.setattr("newz.world.research.research",
                        lambda *a, **k: _outcome_with_claims())
    # The opener declines; what matters is that the run completes and records.
    llm = FakeLLM([("AMBIENT", """<proposal>
  <worth_pursuing>no</worth_pursuing><statement></statement><why_open></why_open>
  <closing_condition></closing_condition><grounded_in></grounded_in>
</proposal>"""), _reply()])
    r = Deliberator(path, llm, embedder=LexicalEmbedder(), research=True,
                    log_path=tmp_path / "calls.jsonl").run_once()

    assert r.moved, "a deliberation that read something must still record an outcome"
    conn = open_db(path, read_only=True)
    outcomes = [x[0] for x in conn.execute("SELECT outcome FROM deliberation_log")]
    assert "failed" not in outcomes
    assert load_dossier(conn, cid).concern.advance_count == 1
    conn.close()


def test_a_finding_can_open_its_own_concern(tmp_path, monkeypatch):
    from newz.concerns.store import load_active

    path, (cid,) = _store(tmp_path)
    monkeypatch.setattr("newz.world.research.research",
                        lambda *a, **k: _outcome_with_claims())
    llm = FakeLLM([("AMBIENT", """<proposal>
  <worth_pursuing>yes</worth_pursuing>
  <statement>Why do equity chains reprice more slowly than prediction markets?</statement>
  <why_open>It bears on how fast risk transmits.</why_open>
  <closing_condition>Comparing the two repricing mechanisms settles it.</closing_condition>
  <grounded_in>Equity chains reprice over days.</grounded_in>
</proposal>"""), _reply()])
    Deliberator(path, llm, embedder=LexicalEmbedder(), research=True,
                log_path=tmp_path / "calls.jsonl").run_once()

    conn = open_db(path, read_only=True)
    origins = {c.origin for c in load_active(conn)}
    assert "research" in origins, "the research opener must be able to fire"
    conn.close()


def test_an_opener_failure_never_costs_the_deliberation(tmp_path, monkeypatch):
    path, (cid,) = _store(tmp_path)
    monkeypatch.setattr("newz.world.research.research",
                        lambda *a, **k: _outcome_with_claims())
    monkeypatch.setattr("newz.concerns.opener.open_from_research",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder(),
                    research=True, log_path=tmp_path / "calls.jsonl").run_once()
    assert r.moved


def test_a_restart_does_not_cost_four_hours_of_thinking(tmp_path):
    """RISKS R-23. The scheduler slept its whole interval before the first
    run, so every restart pushed the next deliberation a full interval out.
    Measured 2026-08-13: three restarts in a morning left the being eight
    hours without deliberating — and since feeds harvest inside deliberation
    and closure fires after an advance, the entire autonomous side was
    dormant while looking merely quiet.
    """
    import inspect

    from newz.deliberation.lite import BOOT_DELAY_S, DeliberationScheduler

    src = inspect.getsource(DeliberationScheduler.run)
    assert "BOOT_DELAY_S" in src, "the first run must not wait a full interval"
    assert BOOT_DELAY_S < 300, "a restart should cost seconds, not an hour"


def test_restart_spam_cannot_buy_extra_deliberations(tmp_path):
    # The boot run is safe only because the daily budget counts ATTEMPTS over
    # a rolling 24h, so N restarts cannot exceed the day's allowance.
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    for _ in range(4):
        conn.execute("INSERT INTO deliberation_log (ts, concern_id, outcome,"
                     " detail) VALUES (?,?,'started','')", (time.time(), cid))
    conn.commit()
    conn.close()
    r = Deliberator(path, FakeLLM([]), daily_budget=4).run_once()
    assert r.skipped == "daily deliberation budget spent"


def test_the_cooldown_not_the_interval_is_what_bounds_regrinding(tmp_path):
    """RISKS R-24. Frequency is safe only because of REATTEMPT_COOLDOWN_HOURS.

    Measured 2026-08-14, when the interval went to 20 minutes: with 9 open
    concerns and a 6h cooldown a concern can be attempted 4 times a day, and
    STALL_LIMIT is 5. Since 6 of 8 recent setbacks were restatements, a
    faster loop with a small pool stalls the pool rather than moving it. The
    cooldown is the only thing standing between those two, so it is pinned
    here rather than left to be "simplified" later.
    """
    from newz.concerns.scoring import REATTEMPT_COOLDOWN_HOURS, choose_concern
    from newz.concerns.model import STALL_LIMIT

    assert REATTEMPT_COOLDOWN_HOURS >= 6.0
    # 24h / cooldown must stay under the stall limit, or a day of pure
    # restatement stalls every concern the being carries.
    assert 24 / REATTEMPT_COOLDOWN_HOURS < STALL_LIMIT

    now = time.time()
    just_tried = Concern(id=1, statement="q1", why_open="w",
                         closing_condition="c", salience=0.9,
                         last_attempted_at=now - 60)
    rested = Concern(id=2, statement="q2", why_open="w",
                     closing_condition="c", salience=0.1,
                     last_attempted_at=now - 8 * 3600)
    # Salience 0.9 vs 0.1 and it still picks the rested one: the cooldown is
    # a floor, not a preference.
    assert choose_concern([just_tried, rested], now=now).concern.id == 2


def test_a_being_with_everything_cooling_is_never_left_with_nothing(tmp_path):
    from newz.concerns.scoring import choose_concern

    now = time.time()
    cooling = [Concern(id=i, statement=f"q{i}", why_open="w",
                       closing_condition="c", last_attempted_at=now - 60)
               for i in (1, 2)]
    choice = choose_concern(cooling, now=now)
    assert choice.concern is not None      # bypass, rather than idling


# ── S2 §7.1's state-driven trigger (P2 Phase 3.1, pulled forward) ────────
#
# "A deliberation begins when the being's state warrants one: ... ENOUGH NEW
# MATERIAL HAS ACCUMULATED ON A DOSSIER ... or the daily budget would
# otherwise go unspent. The budget is finite (target: 3-6/day)."
#
# The budget is a ceiling spent when state warrants. A timer spends it
# regardless — and at 20-minute intervals against a paused diet, DEEP re-runs
# on an unchanged dossier, returns the same conclusion (measured at novelty
# -0.00), and books a `restated` setback. Four attempts a day against
# STALL_LIMIT 5 stalls the pool for reasons unrelated to the concern.

def _busy_loop(conn, cid):
    """The loop is otherwise active, so §7.1's unspent-budget floor is quiet.

    An empty deliberation_log means the being has NEVER deliberated, and the
    floor correctly says to do one — the skip is only meaningful against a
    loop that is already running.
    """
    conn.execute("INSERT INTO deliberation_log (ts, concern_id, outcome, detail)"
                 " VALUES (?,?,'started','')", (time.time() - 300, cid))
    conn.commit()


def _paused_log(tmp_path):
    """A call log where ingest already exceeds earning: reading is paused."""
    return _log(tmp_path, [_call("ingest", 9000), _call("deliberation", 100)])


def _busy_log(tmp_path):
    return _log(tmp_path, [_call("deliberation", 9000)])


def test_a_paused_diet_no_longer_stops_the_being_thinking(tmp_path):
    # REVERSED 2026-08-15, operator approved. This asserted the opposite
    # until today: an unchanged dossier with reading paused was skipped.
    #
    # S2 §9.1 forbids that in terms — "breach pauses ingest, NEVER
    # deliberation" — and deliberation is the earning term, so pausing it on
    # breach makes the breach permanent. Measured: 2h10m of total inactivity,
    # 277 tokens short of being allowed to read, with the only cognition that
    # could earn those tokens switched off because reading was switched off.
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Established once.", kind="reasoning",
                   evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() + 60, cid))          # attempted AFTER the advance
    _busy_loop(conn, cid)
    conn.close()

    llm = FakeLLM([_reply(moved="no", blocked_on="I need the study itself.")])
    r = Deliberator(path, llm, research=True,
                    log_path=_paused_log(tmp_path)).run_once()
    assert not r.skipped, "a paused diet must not stop deliberation"
    assert llm.calls, "the being must still think"


def test_a_setback_from_a_paused_cycle_is_recorded_but_not_charged(tmp_path):
    # §4.2, and it is what makes §4.1 safe. The cycle now RUNS on a paused
    # diet, so it will fail — and that failure belongs to the diet, not the
    # question. Measured setbacks 2026-08-14 21:00 onward: blocked 11,
    # restated 2, so exempting only restatements would have protected 2 of 13
    # and spent the last three concerns by morning.
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Established once.", kind="reasoning",
                   evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() + 60, cid))
    _busy_loop(conn, cid)
    conn.close()

    Deliberator(path, FakeLLM([_reply(moved="no", blocked_on="I need the study.")]),
                research=True, log_path=_paused_log(tmp_path)).run_once()

    conn = open_db(path, read_only=True)
    row = conn.execute("SELECT blocked_count, stall_count, status, "
                       "last_attempted_at FROM concerns WHERE id=?",
                       (cid,)).fetchone()
    assert row["blocked_count"] == 0 and row["stall_count"] == 0
    assert row["status"] == "open"
    # The being can still SAY it failed, and staleness still advances so the
    # pool keeps rotating.
    assert conn.execute("SELECT COUNT(*) FROM concern_setbacks").fetchone()[0] == 1
    assert row["last_attempted_at"]
    conn.close()


def test_a_skip_books_no_setback_so_the_pool_does_not_stall(tmp_path):
    # This is the failure being prevented: a manufactured `restated` setback
    # from a run that had nothing to work with.
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Established once.", kind="reasoning",
                   evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() + 60, cid))
    conn.commit()
    conn.close()

    Deliberator(path, FakeLLM([]), research=True,
                log_path=_paused_log(tmp_path)).run_once()
    conn = open_db(path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM concern_setbacks").fetchone()[0] == 0
    assert load_dossier(conn, cid).concern.stall_count == 0
    conn.close()


def test_an_unchanged_dossier_still_runs_when_reading_might_bring_something(
        tmp_path):
    # The second condition matters. A concern with an unchanged dossier is
    # still worth a run if the world might answer — that is the ordinary case,
    # and skipping it would make the being stop trying.
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Established once.", kind="reasoning",
                   evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() + 60, cid))
    _busy_loop(conn, cid)
    conn.close()

    r = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder(),
                    research=False, log_path=_busy_log(tmp_path)).run_once()
    # research=False means no reading prospect, so it skips...
    assert r.skipped and "research is off" in r.skipped


def test_new_material_since_the_last_attempt_always_warrants_a_run(tmp_path):
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Something new arrived.", kind="reasoning",
                   evidence=[])
    # record_advance stamps last_attempted_at itself, so the backdating has to
    # come after it: the advance is newer than the last attempt.
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() - 3600, cid))
    conn.commit()
    conn.close()

    r = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder(),
                    research=True, log_path=_paused_log(tmp_path)).run_once()
    assert not r.skipped


def test_a_concern_never_attempted_is_always_worth_one(tmp_path):
    path, (cid,) = _store(tmp_path)
    r = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder(),
                    research=True, log_path=_paused_log(tmp_path)).run_once()
    assert not r.skipped


def test_a_quiet_state_must_not_become_silence(tmp_path):
    """S2 §7.1's last trigger: "or the daily budget would otherwise go
    unspent."

    The state trigger alone deadlocks. With reading paused every concern
    skips, no deliberation tokens accrue, earning never grows, and the diet
    never recovers — the being idles until sleep breaks it overnight.
    Thinking is the only thing that earns reading back, so quiet must have a
    floor.
    """
    from newz.deliberation.lite import UNSPENT_BUDGET_AFTER_S

    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Established once.", kind="reasoning",
                   evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() + 60, cid))
    # The last attempt was long enough ago that the allowance is going unused.
    conn.execute("INSERT INTO deliberation_log (ts, concern_id, outcome, detail)"
                 " VALUES (?,?,'started','')",
                 (time.time() - UNSPENT_BUDGET_AFTER_S - 60, cid))
    conn.commit()
    conn.close()

    r = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder(),
                    research=True, log_path=_paused_log(tmp_path)).run_once()
    assert not r.skipped, "the floor did not fire; the loop would deadlock"


def test_a_cycle_that_DID_read_is_charged_exactly_as_before(tmp_path):
    # The other side of §4.2, and the reason it is narrow. On 2026-08-15 at
    # 13:34 concern 54 read three claims from Wikipedia, failed to move, and
    # stalled — correctly, because the world answered and the answer did not
    # help. Only a PAUSED diet clears the charge.
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Established once.", kind="reasoning",
                   evidence=[])
    # Attempted BEFORE the advance, so the dossier counts as changed and the
    # state trigger lets the cycle run.
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() - 3600, cid))
    _busy_loop(conn, cid)
    conn.commit()
    conn.close()

    # research OFF: no diet pause is possible, so could_read stays true.
    Deliberator(path, FakeLLM([_reply(moved="no", blocked_on="I need the study.")]),
                embedder=LexicalEmbedder()).run_once()

    conn = open_db(path, read_only=True)
    assert conn.execute("SELECT blocked_count FROM concerns WHERE id=?",
                        (cid,)).fetchone()[0] == 1
    conn.close()


# ── exploration: the world must keep arriving (2026-08-15) ───────────────
#
# Both openers that can START a pursuit lived downstream of already having
# one: the curiosity opener fires inside harvest(), harvest() fired inside a
# deliberation, and a deliberation returned at "no active concerns" before
# reaching it. At zero concerns the being had no autonomous route back — the
# world stopped arriving exactly when it had nothing to pursue. With 82 of
# 111 concerns stalled and three left, that was days away.


def _fake_harvest(calls, *, opened=()):
    from newz.world.feeds import FeedHarvest

    def _h(client, conn, path, **kw):
        calls.append({"path": path, **kw})
        return FeedHarvest(polled=1, offered=3, shortlisted=2,
                           opened=list(opened))
    return _h


def test_nothing_to_pursue_is_a_reason_to_go_looking(tmp_path, monkeypatch):
    from newz.world import feeds as feeds_mod

    calls = []
    monkeypatch.setattr(feeds_mod, "harvest",
                        _fake_harvest(calls, opened=["Why do X and Y diverge?"]))
    path, _ = _store(tmp_path, concerns=0)
    feeds = tmp_path / "feeds.yaml"
    feeds.write_text("rss:\n- {name: A, url: 'https://a.org/f'}\n")

    r = Deliberator(path, FakeLLM([]), embedder=LexicalEmbedder(),
                    research=True, feeds_path=feeds).run_once()

    assert len(calls) == 1, "the world did not arrive"
    assert r.opened == ["Why do X and Y diverge?"]
    assert "explored instead" in r.skipped
    assert "opened 1" in r.skipped


def test_a_skipped_cycle_still_lets_the_world_arrive(tmp_path, monkeypatch):
    # The other half of the same trap: a skipped cycle returned before
    # harvest, which guaranteed the dossier stayed unchanged, which
    # guaranteed the next cycle skipped for the same reason.
    from newz.world import feeds as feeds_mod

    calls = []
    monkeypatch.setattr(feeds_mod, "harvest", _fake_harvest(calls))
    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time(), cid))
    # A recent attempt, so the unspent-budget floor does not fire and the
    # dossier-unchanged branch is the one under test.
    conn.execute("INSERT INTO deliberation_log (ts, concern_id, outcome)"
                 " VALUES (?,?,'started')", (time.time(), cid))
    conn.commit()
    conn.close()

    # An empty call log means zero earning, so budget_permits_ingest is False
    # and _nothing_to_work_with skips — the exact live condition on 2026-08-15.
    log = tmp_path / "calls.jsonl"
    log.write_text("")

    d = Deliberator(path, FakeLLM([]), embedder=LexicalEmbedder(),
                    research=True, feeds_path=tmp_path / "feeds.yaml",
                    log_path=log)
    r = d.run_once()
    assert r.skipped, "expected the state trigger to skip this cycle"
    assert len(calls) == 1, "a skipped cycle must still let the world arrive"


def test_exploring_is_still_gated_by_the_diet_and_the_feed_list(tmp_path):
    # The brakes that matter are untouched. No feeds configured means nothing
    # to poll; harvest() itself checks the §9.1 budget before any HTTP
    # (INV-038), which this must not bypass.
    path, _ = _store(tmp_path, concerns=0)
    r = Deliberator(path, FakeLLM([]), embedder=LexicalEmbedder(),
                    research=True, feeds_path=None).run_once()
    assert r.opened == []
    r2 = Deliberator(path, FakeLLM([]), embedder=LexicalEmbedder(),
                     research=False, feeds_path=tmp_path / "f.yaml").run_once()
    assert r2.opened == []


def test_a_failing_harvest_never_breaks_the_cycle(tmp_path, monkeypatch):
    from newz.world import feeds as feeds_mod

    def _boom(*a, **k):
        raise RuntimeError("feed server on fire")

    monkeypatch.setattr(feeds_mod, "harvest", _boom)
    path, _ = _store(tmp_path, concerns=0)
    r = Deliberator(path, FakeLLM([]), embedder=LexicalEmbedder(),
                    research=True, feeds_path=tmp_path / "f.yaml").run_once()
    assert r.opened == [] and r.skipped


def _reply_superseding(adv_label, summary="The earlier version was too coarse: "
                       "the link is structural, not transmitted."):
    return ("DEEP", f"""<deliberation>
  <moved>yes</moved>
  <summary>{summary}</summary>
  <kind>reasoning</kind>
  <evidence></evidence>
  <supersedes>{adv_label}</supersedes>
  <blocked_on></blocked_on>
</deliberation>""")


def test_an_advance_that_supersedes_is_not_judged_against_what_it_replaces(tmp_path):
    # The 2026-08-15 09:03:44 case, as a regression. Without the exclusion the
    # refinement scores 0.18 against the thing it refines and is recorded as
    # circling.
    from newz.concerns.store import record_advance

    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="The bridge is a structural isomorphism "
                   "between Montaigne and Jung.", kind="reasoning", evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() - 3600, cid))
    _busy_loop(conn, cid)
    conn.commit()
    old = load_dossier(conn, cid).advances[0]["id"]
    conn.close()

    r = Deliberator(path, FakeLLM([_reply_superseding(
        f"adv-{old}",
        summary="The structural isomorphism was a static comparison that "
                "failed to address the historical mechanism.")]),
        embedder=LexicalEmbedder()).run_once()

    assert r.moved, f"the refinement was rejected: {r.reason}"
    conn = open_db(path, read_only=True)
    d = load_dossier(conn, cid)
    assert len(d.advances) == 1, "the superseded advance should have retired"
    assert "static comparison" in d.advances[0]["summary"]
    conn.close()


def test_a_hallucinated_supersedes_label_retires_nothing(tmp_path):
    # The failure mode must be "no exclusion", never "wrong exclusion". A
    # label that names no live advance of THIS concern is ignored and the
    # full history applies.
    from newz.concerns.store import record_advance

    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Established once.", kind="reasoning",
                   evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() - 3600, cid))
    _busy_loop(conn, cid)
    conn.commit()
    conn.close()

    r = Deliberator(path, FakeLLM([_reply_superseding("adv-99999")]),
                    embedder=LexicalEmbedder()).run_once()

    conn = open_db(path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM concern_advances WHERE"
                        " superseded_by IS NOT NULL").fetchone()[0] == 0
    conn.close()
    assert r.moved or r.status_after   # it is judged normally, either way


def test_a_genuine_duplicate_is_still_caught_when_nothing_is_superseded(tmp_path):
    # The -0.00 case from 2026-08-14 against the same echo. The gate must
    # still catch a real repeat.
    from newz.concerns.store import record_advance

    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="Announcement windows differ because "
                   "market makers hedge regulatory tail risk directly.",
                   kind="reasoning", evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                 (time.time() - 3600, cid))
    _busy_loop(conn, cid)
    conn.commit()
    conn.close()

    r = Deliberator(path, FakeLLM([_reply()]), embedder=LexicalEmbedder()).run_once()
    assert not r.moved and "restates" in r.reason
