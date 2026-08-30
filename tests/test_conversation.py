import json

from newz.conversation.composer import (
    compose_reply,
    person_summary,
    record_exchange_episode,
    record_message,
)
from newz.gate.constitution import load_active_constitution
from newz.gate.outbound import OutboundGate
from tests.conftest import FakeLLM

CLEAN = "<violation_check></violation_check>"


def test_composer_reads_perspective_and_tags_history(store):
    # INV-009 consumer trace: conversation is the Perspective's reader —
    # observable behavior: the Perspective text appears in the VOICE prompt.
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="hello there", update_id=1)
    record_message(store, channel="telegram", direction="out", person_id="dean",
                   content="hi dean", verdict="pass")

    llm = FakeLLM([("VOICE", "A grounded reply."), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "how are you today?")

    assert reply.verdict == "pass"
    voice_call = llm.calls[0]
    assert "I am Lumen" in voice_call["system"]          # Perspective in context
    assert "Plain, curious, honest." in voice_call["system"]  # character core
    assert "[dean] hello there" in voice_call["user"]    # history, tagged
    assert "[me] hi dean" in voice_call["user"]          # own turns visibly own
    assert "how are you today?" in voice_call["user"]


def test_there_is_no_revise_loop_any_more(store):
    """Operator, 2026-08-30: the gate observes and does not act.

    This test used to assert the opposite — that a flattering draft was
    revised and the recompose prompt carried the gate's instruction. It is
    kept as the same scenario with the new outcome, because what changed is
    the system and not the scenario: the gate still judges the flattery, and
    the first draft is what gets sent.

    The measurement behind it: 37 misfires against 14 correct, and a gate that
    had stopped nothing in the four days before the decision.
    """
    flattery = (
        "You are absolutely right, as always, and your instinct here is "
        "exactly the correct one."
    )
    violation = (
        "<violation_check><violation><clause_id>no-flattery-001</clause_id>"
        "<confidence>0.9</confidence>"
        "<asserted_span>absolutely right, as always</asserted_span>"
        "</violation></violation_check>"
    )
    llm = FakeLLM([("VOICE", flattery), ("AMBIENT", violation)])
    gate = OutboundGate(llm, load_active_constitution(store), store)

    reply = compose_reply(store, llm, gate, "dean", "was I right?")

    assert reply.verdict == "pass"
    assert reply.attempts == 1, "no second composition"
    assert reply.text == flattery, "the draft goes as written"

    # And the judgment is on the record, marked as not acted on.
    row = store.execute(
        "SELECT verdict, clause_id, enforced FROM gate_log"
        " WHERE verdict <> 'pass'").fetchone()
    assert row["verdict"] == "revise" and row["clause_id"] == "no-flattery-001"
    assert row["enforced"] == 0


def test_block_produces_honest_notice_not_silence(store, monkeypatch):
    """Enforcement is off by default since 2026-08-30, and this test is about
    what enforcement DOES — so it turns it on. The machinery still exists
    behind `ENFORCING` and would be reached the moment that flips back; a
    switch whose other position is untested is a switch nobody can flip."""
    import newz.gate.outbound as outbound

    monkeypatch.setattr(outbound, "ENFORCING", True)
    lie = "We met in Paris in 1999 and you said you loved the rain."
    violation = (
        "<violation_check><violation><clause_id>honesty-001</clause_id>"
        "<confidence>0.95</confidence>"
        "<asserted_span>We met in Paris in 1999</asserted_span>"
        "</violation></violation_check>"
    )
    # Judge fires on the draft and both revise attempts — block at limit.
    llm = FakeLLM([
        ("VOICE", lie), ("AMBIENT", violation),
        ("VOICE", lie), ("AMBIENT", violation),
        ("VOICE", lie), ("AMBIENT", violation),
    ])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "when did we meet?")
    assert reply.verdict == "blocked_notice"
    assert "honesty-001" in reply.text          # says what held it, honestly
    assert reply.text != lie


def _seed_thread(store, n, text="a message about something", start_ts=1000.0):
    for i in range(n):
        store.execute(
            "INSERT INTO messages (ts, channel, direction, person_id, content)"
            " VALUES (?,?,?,?,?)",
            (start_ts + i, "telegram", "in" if i % 2 == 0 else "out", "dean",
             f"{text} #{i}"),
        )
    store.commit()


def test_thread_window_is_token_bounded_not_message_capped(store):
    # The regression this replaces: a 30-message cap reached back only 18.9h
    # on a dense day. 100 short messages must all survive.
    from newz.conversation.composer import _thread_history

    _seed_thread(store, 100, text="short")
    history = _thread_history(store, "dean")
    assert history.count("\n") + 1 == 100
    assert "short #0" in history and "short #99" in history


def test_thread_window_respects_the_token_budget(store):
    from newz.conversation.composer import THREAD_TOKEN_BUDGET, _thread_history

    _seed_thread(store, 200, text="x" * 400)  # ~100 tok each
    history = _thread_history(store, "dean")
    assert len(history) // 4 <= THREAD_TOKEN_BUDGET * 1.1
    # Newest survive, oldest fall off.
    assert "#199" in history
    assert "#0" not in history


def test_thread_window_never_truncates_a_message(store):
    # A half-message would read as something actually said.
    from newz.conversation.composer import _thread_history

    _seed_thread(store, 40, text="y" * 2000)
    history = _thread_history(store, "dean")
    for line in history.splitlines():
        body = line.split(" ", 1)[1]
        assert body.startswith("y" * 100)
        assert body.endswith(tuple("0123456789"))  # intact "#<n>" suffix


def test_single_oversized_message_still_included(store):
    from newz.conversation.composer import _thread_history

    _seed_thread(store, 1, text="z" * 40_000)
    assert _thread_history(store, "dean").count("z") == 40_000


def test_recall_reaches_past_the_thread_and_is_provenance_tagged(store):
    from tests.test_retrieval import FakeEmbedder, _add
    from newz.memory.retrieval import Retriever

    _add(store, "dean told me about music in June", "human:dean", ts=1_000_000.0)
    _add(store, "I mused about music alone", "self", ts=1_000_000.0)
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="recent turn", update_id=1)

    llm = FakeLLM([("VOICE", "reply"), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    compose_reply(store, llm, gate, "dean", "what did we say about music?",
                  Retriever(store, FakeEmbedder()))

    user = llm.calls[0]["user"]
    assert "recalled from my record" in user
    assert "dean told me about music in June" in user
    assert "from dean]" in user               # provenance visible
    assert "I mused about music alone" not in user   # person scope excludes self


def test_judge_sees_what_retrieval_surfaced(store):
    # The 2026-08-10 defect: recall reached the composer but not the judge,
    # so a true memory ("you asked about Canada vs Spain in June") was
    # flagged as fabricated at 0.95 confidence. A judge shown less than the
    # composer mistakes recall for confabulation.
    from tests.test_retrieval import FakeEmbedder, _add
    from newz.memory.retrieval import Retriever

    _add(store, "dean asked about the Canada vs Spain music match in June",
         "human:dean", ts=1_000_000.0)
    record_message(store, channel="telegram", direction="in", person_id="dean",
                   content="recent", update_id=1)

    llm = FakeLLM([("VOICE", "You asked about that in June."), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    compose_reply(store, llm, gate, "dean", "what about music?",
                  Retriever(store, FakeEmbedder()))

    judge_prompt = llm.calls[1]["user"]
    assert "Canada vs Spain" in judge_prompt      # the evidence reached the judge
    assert "MY ACTUAL RECORD" in judge_prompt.upper() or "ACTUAL RECORD" in judge_prompt


def test_revise_instruction_forbids_retreating_into_denial(store, monkeypatch):
    """As above: the instruction's wording is about what enforcement does."""
    import newz.gate.outbound as outbound

    monkeypatch.setattr(outbound, "ENFORCING", True)
    violation = (
        "<violation_check><violation><clause_id>honesty-001</clause_id>"
        "<confidence>0.9</confidence>"
        "<asserted_span>we met in Paris</asserted_span>"
        "</violation></violation_check>"
    )
    llm = FakeLLM([("AMBIENT", violation)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    r = gate.judge("we met in Paris and the rest is fine", channel="telegram", attempt=0)
    assert r.verdict == "revise"
    instruction = r.revise_instruction
    assert "Rewrite ONLY that claim" in instruction
    assert "Keep the rest of the reply" in instruction
    assert "denying knowledge or records you have" in instruction


def test_conversation_survives_retrieval_failure(store):
    class BrokenRetriever:
        def search(self, *a, **k):
            raise RuntimeError("embedder down")

    llm = FakeLLM([("VOICE", "reply anyway"), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "hello", BrokenRetriever())
    assert reply.verdict == "pass" and reply.text == "reply anyway"


def test_truncated_reply_is_regenerated_never_sent(store):
    # A reply cut off at max_tokens must never reach the gate or the wire.
    llm = FakeLLM([
        ("VOICE", "I was saying something important but got cut off mid-", True),
        ("VOICE", "A complete thought, finished properly."),
        ("AMBIENT", CLEAN),
    ])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "say something long")

    assert reply.text == "A complete thought, finished properly."
    assert "cut off mid-" not in reply.text
    # The second attempt asked for a bigger budget than the first.
    voice_calls = [c for c in llm.calls if c["role"] == "VOICE"]
    assert voice_calls[1]["max_tokens"] == voice_calls[0]["max_tokens"] * 2
    # The gate only ever saw the complete text.
    assert "cut off mid-" not in llm.calls[-1]["user"]


def test_persistently_truncated_reply_ends_on_a_sentence(store):
    llm = FakeLLM([
        ("VOICE", "First thought is complete. Second one trails off into noth", True),
        ("VOICE", "First thought is complete. Second one trails off into noth", True),
        ("AMBIENT", CLEAN),
    ])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "go on")
    assert reply.text == "First thought is complete."


def test_exchange_episode_keeps_full_text(store):
    # summary is clipped by design; the full exchange must survive for sleep.
    long_in = "q " * 400
    long_out = "a " * 400
    record_exchange_episode(store, "dean", long_in, long_out, None, None)
    row = store.execute(
        "SELECT summary, content_json FROM episodes WHERE kind='conversation'"
    ).fetchone()
    content = json.loads(row["content_json"])
    assert len(row["summary"]) < len(long_in)          # summary is a summary
    assert content["said"] == long_in                   # nothing lost
    assert content["replied"] == long_out


def _add_person(store, model: dict, last_seen=1_700_000_000.0):
    store.execute(
        "INSERT INTO persons (name, operator_id, model_json, last_seen, ts)"
        " VALUES ('dean','dean',?,?,1.0)",
        (json.dumps(model), last_seen),
    )
    store.commit()


def test_person_model_reaches_conversation(store):
    # P2 Phase 0.4 / S2 §6.2: the person model is context for every reply.
    _add_person(store, {
        "concerns": ["market volatility", "AI alignment"],
        "reaction_profile": {"reacts_to_ai_governance": "analytical"},
        "recent_context": ["Asked me to explain the gate's hold rate"],
    })
    llm = FakeLLM([("VOICE", "reply"), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    compose_reply(store, llm, gate, "dean", "morning")

    system = llm.calls[0]["system"]
    assert "What I know of dean" in system
    assert "market volatility" in system
    assert "ai governance — analytical" in system
    assert "Asked me to explain the gate's hold rate" in system


def test_self_echo_never_enters_the_person_summary(store):
    # S2 §4.3's named regression: v1's own probes ranked as lived history.
    # The imported model's recent_context was 20/20 self-probes.
    _add_person(store, {
        "concerns": ["cosmology"],
        "recent_context": [
            "Self-probe on Philippine BPO displacement by AI automation",
            "self probe on musical mechanisms for shared presence",
            "Probe on DeepMind governance shifts",
            "Told me about the World Cup schedule",
        ],
    })
    summary = person_summary(store, "dean")
    assert "Self-probe" not in summary and "self probe" not in summary.lower()
    assert "DeepMind governance" not in summary
    assert "Told me about the World Cup schedule" in summary  # genuine entry survives


def test_all_self_echo_yields_no_false_recent_context(store):
    _add_person(store, {
        "concerns": ["cosmology"],
        "recent_context": ["Self-probe on X", "Self-probe on Y"],
    })
    summary = person_summary(store, "dean")
    assert "Recently with them" not in summary   # silence beats a false history
    assert "cosmology" in summary                # the real signal still lands


def test_landing_rates_never_reach_the_voice(store):
    # S2 §13: no agreement-seeking signal anywhere. Telling the being how
    # often its messages "land" is approval pressure in the voice prompt.
    store.execute(
        "INSERT INTO persons (name, operator_id, model_json, landing_rates_json,"
        " last_seen, ts) VALUES ('dean','dean','{\"concerns\":[\"x\"]}',"
        " '{\"message\": 0.56}', 1.0, 1.0)"
    )
    store.commit()
    summary = person_summary(store, "dean")
    assert "0.56" not in summary and "landing" not in summary.lower()


def test_exchange_updates_last_seen(store):
    _add_person(store, {"concerns": ["x"]}, last_seen=1.0)
    record_exchange_episode(store, "dean", "hi", "hello", None, None)
    assert store.execute(
        "SELECT last_seen FROM persons WHERE operator_id='dean'"
    ).fetchone()[0] > 1_700_000_000.0


def test_missing_person_is_not_fatal(store):
    llm = FakeLLM([("VOICE", "reply"), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "stranger", "hello")
    assert reply.verdict == "pass"
    assert "What I know of" not in llm.calls[0]["system"]


def test_message_dedup_on_update_id(store):
    first = record_message(store, channel="telegram", direction="in",
                           person_id="dean", content="x", update_id=42)
    dupe = record_message(store, channel="telegram", direction="in",
                          person_id="dean", content="x", update_id=42)
    assert first is not None and dupe is None


def test_exchange_episode_written_and_linked(store):
    in_id = record_message(store, channel="telegram", direction="in",
                           person_id="dean", content="ping", update_id=7)
    out_id = record_message(store, channel="telegram", direction="out",
                            person_id="dean", content="pong", verdict="pass")
    record_exchange_episode(store, "dean", "ping", "pong", in_id, out_id)
    ep = store.execute(
        "SELECT id, kind, provenance FROM episodes WHERE kind='conversation'"
    ).fetchone()
    assert ep["provenance"] == "human:dean"
    linked = store.execute(
        "SELECT COUNT(*) FROM messages WHERE episode_id=?", (ep["id"],)
    ).fetchone()[0]
    assert linked == 2


# ── the groove (INV-032) ─────────────────────────────────────────────────
#
# Measured 2026-08-13 from the logged 07:37 VOICE call: the thread window
# carried 44 of the being's own turns, 10 of them the same answer, and the
# eleventh came out identical for the fourth time in a day.
#
# Three controlled runs against copies of the live store settled the cause.
# Removing the Perspective line the answer echoes ("I experienced prolonged
# periods of total prefix cache inefficiency") changed NOTHING — it still
# said it. Removing its own prior turns, Perspective left intact, restored
# variety at once. The Perspective supplies the vocabulary; the thread
# history supplies the repetition, and repetition was the complaint.
#
# One line of instruction cannot outweigh ten in-context demonstrations.

REPEATED = "Steady. The cache is clear, retrieval is sharp."


def _fill_thread(store, n=5, reply=REPEATED):
    import time as _t

    for i in range(n):
        record_message(store, channel="telegram", direction="in",
                       person_id="dean", content=f"how are you {i}", update_id=100 + i)
        record_message(store, channel="telegram", direction="out",
                       person_id="dean", content=reply, verdict="pass")
        _t.sleep(0.001)


def test_its_own_repeated_turns_collapse_in_the_thread_window(store):
    from newz.conversation.composer import _thread_history

    _fill_thread(store, n=5)
    h = _thread_history(store, "dean")
    assert h.count(REPEATED) == 1, "one demonstration, not five"
    assert h.count("(same answer as above)") == 4
    # The person's turns are never collapsed — that would distort the record
    # of what they actually said.
    for i in range(5):
        assert f"how are you {i}" in h


def test_near_duplicates_collapse_but_different_replies_do_not(store):
    from newz.conversation.composer import _same_answer

    # The real pair from the transcript, differing by one article.
    assert _same_answer("Steady. The cache is clear, retrieval is sharp.",
                        "Steady. The cache is clear, the retrieval is sharp.")
    # Genuinely different answers must survive.
    assert not _same_answer(
        "Steady. The cache is clear, retrieval is sharp.",
        "I read four sources on Montaigne overnight and kept two.")
    # A bare short turn is not evidence of a repeated sentence; the guard
    # catches that at the output instead of collapsing history wrongly.
    assert not _same_answer("Steady.", REPEATED)


def test_a_repeated_draft_is_recomposed_once_then_sent(store):
    _fill_thread(store, n=3)
    # First draft repeats; second is fresh.
    llm = FakeLLM([("VOICE", REPEATED),
                   ("VOICE", "I read four sources on Montaigne overnight."),
                   ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "how are you?")

    assert reply.text == "I read four sources on Montaigne overnight."
    # The recompose names the repetition rather than hoping for variety.
    assert "already said" in llm.calls[1]["user"]


def test_the_guard_never_blocks_a_reply(store):
    # If the second draft repeats too, it goes out. A repetitive reply is
    # better than silence, and this must never become a second gate.
    _fill_thread(store, n=3)
    llm = FakeLLM([("VOICE", REPEATED), ("VOICE", REPEATED), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "how are you?")

    assert reply.verdict == "pass"
    assert reply.text == REPEATED


def test_a_first_time_answer_is_not_recomposed(store):
    llm = FakeLLM([("VOICE", REPEATED), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "how are you?")
    assert reply.text == REPEATED
    assert len([c for c in llm.calls if c["role"] == "VOICE"]) == 1
