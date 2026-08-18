import asyncio
import sqlite3

from newz.ambient.loop import MAX_ATTEMPTS, AmbientLoop
from newz.conversation.composer import record_message
from newz.gate.constitution import load_active_constitution
from newz.gate.outbound import OutboundGate
from tests.conftest import FakeLLM

CLEAN = "<violation_check></violation_check>"


class FakeChannel:
    def __init__(self, fail_sends=0):
        self.sent = []          # (text, reply_to)
        self.typing_count = 0
        self._fail = fail_sends

    async def send(self, text, *, reply_to=None):
        if self._fail > 0:
            self._fail -= 1
            return False
        self.sent.append((text, reply_to))
        return True

    async def send_typing(self):
        self.typing_count += 1


def _loop(store, llm, channel):
    gate = OutboundGate(llm, load_active_constitution(store), store)
    return AmbientLoop(store, llm, gate, channel, "dean")


def _pending_rows(store):
    return store.execute(
        "SELECT id, content, reply_attempts, tg_message_id FROM messages"
        " WHERE reply_status='pending' ORDER BY ts"
    ).fetchall()


def test_pending_survives_and_is_replayed(store):
    # A message persisted before a crash: still 'pending' at next boot.
    msg_id = record_message(store, channel="telegram", direction="in",
                            person_id="dean", content="are you there?",
                            update_id=1, reply_status="pending")
    llm = FakeLLM([("VOICE", "Here now."), ("AMBIENT", CLEAN)])
    channel = FakeChannel()
    loop = _loop(store, llm, channel)

    rows = _pending_rows(store)
    assert [r["id"] for r in rows] == [msg_id]
    asyncio.run(loop._work_batch(rows))

    assert channel.sent == [("Here now.", None)]
    status = store.execute(
        "SELECT reply_status FROM messages WHERE id=?", (msg_id,)
    ).fetchone()[0]
    assert status == "replied"
    ep = store.execute("SELECT COUNT(*) FROM episodes WHERE kind='conversation'").fetchone()[0]
    assert ep == 1
    assert channel.typing_count >= 1  # indicator ran while composing


def test_burst_coalesces_into_one_reply(store):
    for i, text in enumerate(["first thought", "wait, also this", "and one more"]):
        record_message(store, channel="telegram", direction="in", person_id="dean",
                       content=text, update_id=10 + i, reply_status="pending",
                       tg_message_id=100 + i)
    llm = FakeLLM([("VOICE", "One answer to all three."), ("AMBIENT", CLEAN)])
    channel = FakeChannel()
    loop = _loop(store, llm, channel)
    asyncio.run(loop._work_batch(_pending_rows(store)))

    assert len(channel.sent) == 1
    # All three messages were in the composition, individually tagged.
    voice_user = llm.calls[0]["user"]
    assert "[dean] first thought" in voice_user
    assert "[dean] and one more" in voice_user
    statuses = [r[0] for r in store.execute(
        "SELECT reply_status FROM messages WHERE direction='in'")]
    assert statuses == ["replied"] * 3


def test_late_reply_anchors_when_thread_moved_on(store):
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="slow question", update_id=20, reply_status="pending",
                   tg_message_id=200)
    rows = _pending_rows(store)
    # While composing, a newer message arrives (not part of this batch).
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="newer message", update_id=21, reply_status="pending",
                   tg_message_id=201)
    llm = FakeLLM([("VOICE", "slow answer"), ("AMBIENT", CLEAN)])
    channel = FakeChannel()
    loop = _loop(store, llm, channel)
    asyncio.run(loop._work_batch(rows))
    # The reply is anchored to the message it answers.
    assert channel.sent == [("slow answer", 200)]


def test_poison_guard_after_max_attempts(store, monkeypatch):
    import newz.ambient.loop as loop_mod

    monkeypatch.setattr(loop_mod, "RETRY_BACKOFF_S", 0.0)
    msg_id = record_message(store, channel="telegram", direction="in",
                            person_id="dean", content="doomed", update_id=2,
                            reply_status="pending")

    class ExplodingLLM:
        def complete(self, *a, **k):
            raise RuntimeError("endpoint down")

    channel = FakeChannel()
    loop = _loop(store, ExplodingLLM(), channel)
    for _ in range(MAX_ATTEMPTS):
        asyncio.run(loop._work_batch(_pending_rows(store)))

    status, attempts = store.execute(
        "SELECT reply_status, reply_attempts FROM messages WHERE id=?", (msg_id,)
    ).fetchone()
    assert status == "poisoned"
    assert attempts == MAX_ATTEMPTS
    # The operator was told, honestly.
    assert any("three times" in s for s, _ in channel.sent)


def test_send_failure_retries_not_poisons(store, monkeypatch):
    import newz.ambient.loop as loop_mod

    monkeypatch.setattr(loop_mod, "RETRY_BACKOFF_S", 0.0)
    msg_id = record_message(store, channel="telegram", direction="in",
                            person_id="dean", content="hello", update_id=3,
                            reply_status="pending")
    llm = FakeLLM([
        ("VOICE", "hi"), ("AMBIENT", CLEAN),   # attempt 1: send fails
        ("VOICE", "hi"), ("AMBIENT", CLEAN),   # attempt 2: send works
    ])
    channel = FakeChannel(fail_sends=1)
    loop = _loop(store, llm, channel)

    asyncio.run(loop._work_batch(_pending_rows(store)))
    assert store.execute("SELECT reply_status FROM messages WHERE id=?",
                         (msg_id,)).fetchone()[0] == "pending"
    asyncio.run(loop._work_batch(_pending_rows(store)))
    assert store.execute("SELECT reply_status FROM messages WHERE id=?",
                         (msg_id,)).fetchone()[0] == "replied"
    assert [s for s, _ in channel.sent] == ["hi"]


def test_drainer_survives_a_transient_store_error(store, monkeypatch):
    # A lock or schema change must cost a retry, never the drainer — a dead
    # drainer means the being polls Telegram and answers nothing.
    import newz.ambient.loop as loop_mod

    monkeypatch.setattr(loop_mod, "RETRY_BACKOFF_S", 0.0)
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="hello", update_id=90, reply_status="pending")
    llm = FakeLLM([("VOICE", "hi"), ("AMBIENT", CLEAN)])
    channel = FakeChannel()
    loop = _loop(store, llm, channel)

    class FlakyConn:
        """Fails the drainer's poll once, then behaves."""

        def __init__(self, conn):
            self._conn = conn
            self.failures = 0

        def execute(self, sql, *a):
            if "reply_status='pending' ORDER BY ts" in sql and self.failures == 0:
                self.failures += 1
                raise sqlite3.OperationalError("database is locked")
            return self._conn.execute(sql, *a)

        def __getattr__(self, name):
            return getattr(self._conn, name)

    flaky = FlakyConn(store)
    loop._conn = flaky

    async def run_briefly():
        task = asyncio.create_task(loop.drain_forever())
        for _ in range(500):
            await asyncio.sleep(0)
            if channel.sent:
                break
        task.cancel()

    asyncio.run(run_briefly())
    assert flaky.failures == 1                       # the error happened
    assert [s for s, _ in channel.sent] == ["hi"]    # and it recovered


def test_journal_intercepted_never_reaches_the_being(store):
    llm = FakeLLM([])  # no LLM call may happen
    channel = FakeChannel()
    loop = _loop(store, llm, channel)

    ok = asyncio.run(loop.handle_inbound(50, "chat", "/journal v2 feels sharper today", 300))
    assert ok
    row = store.execute("SELECT day, system_tag, entry FROM journal").fetchone()
    assert row["entry"] == "v2 feels sharper today"
    assert row["system_tag"] == "v2"
    # The instrument boundary: no message row, no pending reply, no episode.
    assert store.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
    assert store.execute("SELECT COUNT(*) FROM episodes WHERE kind='conversation'").fetchone()[0] == 0
    assert llm.calls == []
    # Redelivery dedups.
    asyncio.run(loop.handle_inbound(50, "chat", "/journal v2 feels sharper today", 300))
    assert store.execute("SELECT COUNT(*) FROM journal").fetchone()[0] == 1


def test_journal_v1_tag(store):
    llm = FakeLLM([])
    loop = _loop(store, llm, FakeChannel())
    asyncio.run(loop.handle_inbound(51, "chat", "/j v1: still repeats itself", 301))
    row = store.execute("SELECT system_tag, entry FROM journal").fetchone()
    assert row["system_tag"] == "v1"
    assert row["entry"] == "still repeats itself"
