"""The closure sweep — a concern that has stopped can still be recognised.

Closure was reachable only from the moment after an advance was recorded, so a
concern with nothing left to move could never be asked whether it was already
finished. 77 concerns sat stalled with both counters BELOW the limits that
produce a stall — a state the current code cannot create — and for every one of
them closure was structurally unreachable.
"""

import time

from newz.concerns.model import BLOCKED_LIMIT, STALL_LIMIT, Concern
from newz.concerns.store import create_concern, record_advance
from newz.concerns.sweep import JUDGE_COOLDOWN_HOURS, eligible, sweep
from tests.conftest import FakeLLM


def _closure(met="yes"):
    return ("DEEP", f"""<closure>
  <met>{met}</met>
  <position>I hold that the link is structural rather than lineage.</position>
  <resolution>Settled against the dossier already held.</resolution>
  <missing>{'' if met == 'yes' else 'a source that dates the essays'}</missing>
</closure>""")


def _stalled(store, *, stalls=3, blocked=1, advances=2, statement="Does X hold?"):
    cid = create_concern(store, Concern(
        id=None, statement=statement, why_open="it recurs",
        closing_condition="I can state whether the link is lineage or structure",
        origin="curiosity"))
    for i in range(advances):
        record_advance(store, cid, summary=f"established point {i}",
                       kind="reasoning", evidence=[str(i + 1)])
    store.execute(
        "UPDATE concerns SET status='stalled', stall_count=?, blocked_count=?"
        " WHERE id=?", (stalls, blocked, cid))
    store.commit()
    return cid


def test_a_concern_stalled_below_both_limits_is_eligible(store):
    """The mechanical warrant. Today's code stalls a concern only when a
    counter REACHES its limit, so a stalled concern below both was stalled
    under rules that no longer apply — checkable without asking a model."""
    below = _stalled(store, stalls=STALL_LIMIT - 1, blocked=BLOCKED_LIMIT - 1)
    assert below in eligible(store, limit=50)


def test_a_concern_that_genuinely_exhausted_itself_is_left_alone(store):
    """At or over a limit is a real stall, not an artifact. The sweep is not a
    general revival: it reaches only the state the rules cannot produce."""
    for stalls, blocked in ((STALL_LIMIT, 0), (0, BLOCKED_LIMIT)):
        cid = _stalled(store, stalls=stalls, blocked=blocked)
        assert cid not in eligible(store, limit=50)


def test_closing_takes_no_pool_slot_and_resets_no_counter(store):
    """It does not revive anything. The being did fail to move this concern —
    `stall_count` stays true — and it also, it turns out, had already answered
    it. Both facts are kept, and no MAX_OPEN_CONCERNS slot is consumed, so
    nothing here competes with new curiosity."""
    cid = _stalled(store, stalls=4, blocked=1)
    result = sweep(store, FakeLLM([_closure()]), limit=5)

    assert cid in result.closed
    row = store.execute(
        "SELECT status, stall_count, blocked_count FROM concerns WHERE id=?",
        (cid,)).fetchone()
    assert row["status"] == "closed"
    assert row["stall_count"] == 4 and row["blocked_count"] == 1
    assert store.execute(
        "SELECT COUNT(*) FROM concerns WHERE status='open'").fetchone()[0] == 0


def test_closures_are_capped_because_sleep_is_the_only_perspective_writer(store):
    """Sleep's `_closure_observations` collects every concern_closed episode
    since the last sleep, so an uncapped sweep would deliver a whole backlog
    into one confrontation. Positions entering identity is the least
    reversible act here (INV-009)."""
    for i in range(4):
        _stalled(store, statement=f"Does X{i} hold?")

    result = sweep(store, FakeLLM([_closure()] * 8), limit=10, max_closures=2)

    assert len(result.closed) == 2
    assert "least reversible" in result.stopped_early
    assert store.execute(
        "SELECT COUNT(*) FROM concerns WHERE status='stalled'").fetchone()[0] == 2


def test_a_concern_judged_and_not_met_is_not_re_judged_for_a_week(store):
    """15 of 23 measured did not close and will not on an unchanged dossier.
    Without the stamp they would cost one DEEP call every run, forever."""
    cid = _stalled(store)
    sweep(store, FakeLLM([_closure(met="no")]), limit=5)

    assert store.execute(
        "SELECT status FROM concerns WHERE id=?", (cid,)).fetchone()[0] == "stalled"
    assert cid not in eligible(store, limit=50)

    later = time.time() + (JUDGE_COOLDOWN_HOURS + 1) * 3600.0
    assert cid in eligible(store, now=later, limit=50)


def test_the_sweep_and_deliberation_close_through_the_same_act(store):
    """Two implementations of "is this concern finished" would eventually
    disagree, in the one place where disagreement means the being both holds
    and does not hold a position."""
    import inspect

    from newz.deliberation.lite import Deliberator

    assert "attempt_closure" in inspect.getsource(Deliberator._maybe_close)
    assert "attempt_closure" in inspect.getsource(sweep)
