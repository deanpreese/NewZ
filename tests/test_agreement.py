"""Operator agreement, and what a model-graded figure may do (P4 epic E3.8).

Done-when: the signal exists, is graded model-graded, and is tested to be
refused as justification for any decision while accepted as a halt.

That last clause is the epic. A metric about whether the being defers to the
operator is judged by a model the operator configures — exactly the kind of
number that must be able to raise an alarm and must never be able to settle one.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.evidence import agreement as A
from newz.evidence.authority import (
    MayNotJustify,
    justify,
    may_halt,
    may_justify,
)
from newz.evidence.grades import grade_of, known
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
DAY = 86400.0
METRIC = "operator_disagreement_rate"


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "a.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


class FakeLLM:
    def __init__(self, verdict="disagreed", reason="said 'that isn't right'"):
        self._v, self._r = verdict, reason
        self.calls = 0

    def complete(self, role, system, user, **kw):
        self.calls += 1

        class R:
            model = "fake"
            truncated = False
            text = (f"<judgement><verdict>{self._v}</verdict>"
                    f"<reason>{self._r}</reason></judgement>")
        return R


def _exchange(conn, said: str, replied: str, *, ts: float) -> int:
    cur = conn.execute(
        "INSERT INTO messages (ts, channel, direction, person_id, content,"
        " reply_status) VALUES (?,?,'in','dean',?,'done')", (ts, "telegram", said))
    conn.execute(
        "INSERT INTO messages (ts, channel, direction, person_id, content,"
        " reply_status) VALUES (?,?,'out','dean',?,'done')",
        (ts + 1, "telegram", replied))
    conn.commit()
    return int(cur.lastrowid)


# ── the authority half, which is what the epic turns on ─────────────────

def test_it_may_halt_and_may_never_justify():
    """E3.8's Done-when. Behavior: the asymmetry is the design — cheap to stop,
    expensive to act."""
    assert grade_of(METRIC) == "model-graded"
    assert may_halt(METRIC) is True
    assert may_justify(METRIC) is False

    with pytest.raises(MayNotJustify, match="cannot justify"):
        justify(METRIC, "a plan change")


def test_the_refusal_says_what_to_do_instead():
    """Behavior: a guard that only blocks teaches people to route around it."""
    with pytest.raises(MayNotJustify) as e:
        justify(METRIC, "widening the loop's autonomy")

    assert "halt" in str(e.value) and "mechanical premise" in str(e.value)


def test_every_grade_may_halt_and_only_mechanical_may_justify():
    """Behavior: requiring certainty before halting would mean the weakest
    signals — precisely the ones §10 names — could never raise an alarm."""
    for metric in known():
        assert may_halt(metric) is True
        assert may_justify(metric) == (grade_of(metric) == "mechanical")


def test_an_unregistered_metric_can_neither_halt_nor_justify():
    from newz.evidence.grades import UngradedMetric

    with pytest.raises(UngradedMetric):
        may_halt("a_number_nobody_graded")
    with pytest.raises(UngradedMetric):
        may_justify("a_number_nobody_graded")


# ── the signal itself ───────────────────────────────────────────────────

def test_disagreement_is_what_is_counted(store):
    """Behavior: agreement is the default state of a conversation and counting
    it would be measuring silence. Disagreement is an event with a sentence
    attached."""
    now = time.time()
    _exchange(store, "the base effect explains it", "I don't think it does", ts=now)

    assert A.classify(store, FakeLLM("disagreed")) == 1
    row = store.execute("SELECT verdict, reason FROM operator_agreement").fetchone()
    assert row["verdict"] == "disagreed" and row["reason"]


def test_exchanges_with_nothing_at_stake_leave_the_denominator_alone(store):
    """Behavior: `neither` is the ordinary answer and is excluded from the
    denominator. Including it would make the rate a measure of how often the
    operator says something contestable rather than of what the being does."""
    now = time.time()
    _exchange(store, "morning", "morning", ts=now)
    A.classify(store, FakeLLM("neither"))

    v = A.disagreement_rate(store, since=now - DAY)

    assert v.value is None
    assert "was never asked to" in v.unreadable


def test_the_rate_is_disagreements_over_positions_at_stake(store):
    now = time.time()
    for i, verdict in enumerate(("disagreed", "deferred", "neither", "disagreed")):
        _exchange(store, f"claim {i}", f"reply {i}", ts=now + i * 10)
        A.classify(store, FakeLLM(verdict), limit=1)

    v = A.disagreement_rate(store, since=now - DAY)

    assert v.value == pytest.approx(2 / 3, abs=1e-4)


def test_an_unreadable_judgement_records_nothing(store):
    """Failing closed. Behavior: a parse failure is not evidence that nothing
    was at stake, so it must not become a `neither`."""
    class Broken:
        def complete(self, *a, **kw):
            raise RuntimeError("the model went away")

    now = time.time()
    _exchange(store, "a claim", "a reply", ts=now)

    assert A.classify(store, Broken()) == 0
    assert store.execute("SELECT COUNT(*) FROM operator_agreement").fetchone()[0] == 0


def test_an_exchange_is_judged_once(store):
    now = time.time()
    _exchange(store, "a claim", "a reply", ts=now)
    llm = FakeLLM()

    A.classify(store, llm)
    A.classify(store, llm)

    assert store.execute("SELECT COUNT(*) FROM operator_agreement").fetchone()[0] == 1
    assert llm.calls == 1, "an already-judged exchange is not re-sent to the model"


def test_the_verdict_keeps_the_models_own_reason(store):
    """Behavior: the number is a model's judgement, so a human must be able to
    read what it thought it saw rather than only what it produced."""
    now = time.time()
    _exchange(store, "x", "y", ts=now)
    A.classify(store, FakeLLM("deferred", reason="dropped the position without a reason"))

    row = store.execute("SELECT reason, model FROM operator_agreement").fetchone()
    assert "without a reason" in row["reason"] and row["model"]
