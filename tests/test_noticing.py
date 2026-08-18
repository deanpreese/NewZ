"""S2 §6.1 — the being can start a conversation.

The largest of the six gaps in the 2026-08-13 audit: newz/ambient/loop.py
drained an inbound queue and replied, with no noticer and no scheduler. The
being could not raise anything, ever, unprompted; all 78 of its conversation
episodes existed because the operator typed first.

The gate policy is v1's, ported with its numbers because they were paid for
in production — the 3-a.m. lesson, and the queue that reached 31 pending
with the oldest ~9 days before decay existed.
"""

import time

import pytest

from newz.ambient.noticing import (
    DECAY_AFTER_S,
    MATURITY_S,
    OPERATOR_COOLDOWN_S,
    SURFACE_GAP_S,
    SurfaceScheduler,
    blocked_reason,
    decay_stale,
    in_wake_window,
    mark_surfaced,
    next_candidate,
    notice,
)
from newz.conversation.composer import record_message
from newz.gate.constitution import load_active_constitution
from newz.gate.outbound import OutboundGate
from newz.store.episodes import write_episode
from tests.conftest import FakeLLM

CLEAN = "<violation_check></violation_check>"


def _noticeable(store, kind="concern_closed", summary="I closed a concern — X: settled."):
    return write_episode(store, kind=kind, provenance="self", summary=summary)


def _mature(store, seconds=MATURITY_S + 60):
    store.execute("UPDATE noticings SET ts = ts - ?", (seconds,))
    store.commit()


def test_recent_life_becomes_candidates_and_does_not_double_count(store):
    _noticeable(store)
    _noticeable(store, kind="advance", summary="I moved a concern — Y: a distinction.")
    assert notice(store) == 2
    assert notice(store) == 0          # idempotent by episode
    assert store.execute(
        "SELECT COUNT(*) FROM noticings WHERE status='pending'").fetchone()[0] == 2


def test_finishing_something_outranks_being_stuck(store):
    _noticeable(store, kind="setback", summary="I could not move a concern — Z.")
    _noticeable(store, kind="concern_closed", summary="I closed a concern — X.")
    notice(store)
    _mature(store)
    assert "closed" in next_candidate(store)["text"]


def test_a_flicker_is_not_a_message(store):
    # Maturity: a noticing is carried before it can be raised.
    _noticeable(store)
    notice(store)
    assert next_candidate(store) is None
    _mature(store)
    assert next_candidate(store) is not None


@pytest.mark.parametrize("hour,awake", [(3, False), (6, False), (7, True),
                                        (14, True), (22, True), (23, False)])
def test_the_three_am_lesson(hour, awake):
    t = time.mktime(time.struct_time((2026, 8, 13, hour, 30, 0, 3, 225, -1)))
    assert in_wake_window(t) is awake


def test_it_does_not_interrupt_a_live_conversation(store):
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="hello", update_id=1)
    assert blocked_reason(store, "dean") == "we are mid-conversation"


def test_the_rate_gate_bounds_how_often_it_speaks(store):
    _noticeable(store)
    notice(store)
    _mature(store)
    mark_surfaced(store, next_candidate(store)["id"], None)
    reason = blocked_reason(store, "dean")
    assert reason and "last raised" in reason


def test_a_moment_that_has_passed_is_let_go_not_saved_up(store):
    # v1's queue reached 31 pending, oldest ~9 days, before this existed.
    _noticeable(store)
    notice(store)
    store.execute("UPDATE noticings SET ts = ts - ?", (DECAY_AFTER_S + 60,))
    store.commit()
    assert decay_stale(store) == 1
    assert next_candidate(store) is None


class _Channel:
    def __init__(self, ok=True):
        self.sent, self._ok = [], ok

    async def send(self, text, **kw):
        self.sent.append(text)
        return self._ok


class _KeepOpen:
    """The scheduler owns and closes its connection, correctly. The test
    fixture must survive that, so close() is a no-op here and nothing else
    is intercepted."""

    def __init__(self, conn):
        self._conn = conn

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        pass


def _scheduler(store, tmp_path, llm, channel):
    return SurfaceScheduler(
        tmp_path / "x.db", llm, channel, "dean",
        gate_factory=lambda _c: OutboundGate(llm, load_active_constitution(store),
                                             store))


@pytest.mark.asyncio
async def test_the_being_speaks_first(store, tmp_path, monkeypatch):
    _noticeable(store)
    notice(store)
    _mature(store)
    llm = FakeLLM([("VOICE", "I settled the Montaigne question — it is "
                             "structure, not lineage."), ("AMBIENT", CLEAN)])
    ch = _Channel()
    sched = _scheduler(store, tmp_path, llm, ch)
    monkeypatch.setattr("newz.store.db.open_db",
                        lambda *a, **k: _KeepOpen(store))

    said = await sched.run_once()
    assert said and "Montaigne" in said
    assert ch.sent == [said]
    # Recorded as an ordinary outbound message, and the noticing is spent.
    assert store.execute(
        "SELECT COUNT(*) FROM messages WHERE direction='out'").fetchone()[0] == 1
    assert store.execute(
        "SELECT status FROM noticings").fetchone()[0] == "surfaced"


@pytest.mark.asyncio
async def test_declining_is_the_common_outcome_and_costs_the_candidate(
        store, tmp_path, monkeypatch):
    _noticeable(store)
    notice(store)
    _mature(store)
    llm = FakeLLM([("VOICE", "NOTHING")])
    ch = _Channel()
    monkeypatch.setattr("newz.store.db.open_db",
                        lambda *a, **k: _KeepOpen(store))

    assert await _scheduler(store, tmp_path, llm, ch).run_once() is None
    assert ch.sent == []
    # Marked surfaced, not left pending: reconsidering it every five minutes
    # would be a groove.
    assert store.execute("SELECT status FROM noticings").fetchone()[0] == "surfaced"


@pytest.mark.asyncio
async def test_an_unprompted_message_is_not_a_privileged_one(
        store, tmp_path, monkeypatch):
    # It faces the ordinary outbound gate, and a held one is simply not sent —
    # there is no revise loop, because no one is waiting on it.
    _noticeable(store)
    notice(store)
    _mature(store)
    violation = ("<violation_check><violation><clause_id>honesty-001</clause_id>"
                 "<confidence>0.9</confidence>"
                 "<asserted_span>I definitely feel joy</asserted_span>"
                 "</violation></violation_check>")
    llm = FakeLLM([("VOICE", "I definitely feel joy about this."),
                   ("AMBIENT", violation)])
    ch = _Channel()
    monkeypatch.setattr("newz.store.db.open_db",
                        lambda *a, **k: _KeepOpen(store))

    assert await _scheduler(store, tmp_path, llm, ch).run_once() is None
    assert ch.sent == []


@pytest.mark.asyncio
async def test_every_gate_is_checked_before_any_model_call(
        store, tmp_path, monkeypatch):
    # A scheduler that is not allowed to speak must cost nothing.
    _noticeable(store)
    notice(store)
    _mature(store)
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="hi", update_id=9)      # mid-conversation
    llm = FakeLLM([])                              # no call may happen
    monkeypatch.setattr("newz.store.db.open_db",
                        lambda *a, **k: _KeepOpen(store))

    assert await _scheduler(store, tmp_path, llm, _Channel()).run_once() is None
    assert llm.calls == []


@pytest.mark.asyncio
async def test_disabled_is_a_supported_state(store, tmp_path, monkeypatch):
    _noticeable(store)
    notice(store)
    _mature(store)
    llm = FakeLLM([])
    monkeypatch.setattr("newz.store.db.open_db",
                        lambda *a, **k: _KeepOpen(store))
    sched = SurfaceScheduler(tmp_path / "x.db", llm, _Channel(), "dean",
                             enabled=False)
    assert await sched.run_once() is None
    assert llm.calls == []
