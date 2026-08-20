"""The retrieval index was never maintained (S2 §4.3).

`write_episode` does not embed and `tools/embed_episodes.py` is an operator
tool that was run once. Measured 2026-08-20: 2,066 of 3,662 episodes carried no
vector, including 0 of 653 `reading` episodes. `Retriever.search` requires
`embedding IS NOT NULL`, so nothing the being had read was recallable — in
concern work OR in conversation, which queries retrieval today.
"""

import time

from newz.memory.index import EmbeddingScheduler, coverage, embed_pending
from newz.store.episodes import write_episode
from tests.conftest import LexicalEmbedder


class _Embedder(LexicalEmbedder):
    model = "test-embed-v1"


def _read(store, summary, ts):
    """write_episode stamps its own ts, so order is set afterwards — these
    tests care about newest-first, which needs deterministic timestamps."""
    eid = write_episode(store, kind="reading", provenance="world:CoinDesk",
                        summary=summary, content={"claims": []},
                        source_ref="feed:test")
    store.execute("UPDATE episodes SET ts=? WHERE id=?", (ts, eid))
    store.commit()
    return eid


def test_reading_episodes_become_retrievable(store):
    """The gap itself: a read the being cannot recall is a read it did not
    keep. Retrieval requires a vector and nothing was producing one."""
    _read(store, "I read about bitcoin futures open interest", 1000.0)
    _read(store, "I read about market liquidity mismatch", 1001.0)
    e = _Embedder()

    assert coverage(store, e.model)[0] == 0
    assert embed_pending(store, e, limit=10) == 2

    done, eligible = coverage(store, e.model)
    assert done == eligible == 2
    assert store.execute(
        "SELECT COUNT(*) FROM episodes WHERE kind='reading'"
        " AND embedding IS NOT NULL").fetchone()[0] == 2


def test_it_is_bounded_and_takes_the_newest_first(store):
    """A 2,000-episode blast competes with the being and lands the whole
    behaviour change between one message and the next. Recent material is also
    what conversation reaches for, so currency beats completeness."""
    for i in range(6):
        _read(store, f"I read piece {i}", 1000.0 + i)

    assert embed_pending(store, _Embedder(), limit=2) == 2

    embedded = [r[0] for r in store.execute(
        "SELECT summary FROM episodes WHERE embedding IS NOT NULL")]
    assert sorted(embedded) == ["I read piece 4", "I read piece 5"]


def test_it_is_idempotent_and_safe_beside_the_operator_tool(store):
    """The filter excludes anything already carrying a vector from this model,
    so the rhythm and tools/embed_episodes.py can overlap without redoing each
    other's work."""
    _read(store, "I read about liquidity", 1000.0)
    e = _Embedder()

    assert embed_pending(store, e, limit=10) == 1
    assert embed_pending(store, e, limit=10) == 0


def test_a_vector_from_another_model_is_replaced_not_reused(store):
    """A mixed vector space corrupts retrieval silently, and retrieval feeds
    evidence contexts — where v1's self-echo leak lived."""
    _read(store, "I read about liquidity", 1000.0)
    store.execute("UPDATE episodes SET embedding=X'00', embedding_model='v1-old'")
    store.commit()

    assert embed_pending(store, _Embedder(), limit=10) == 1
    assert store.execute(
        "SELECT embedding_model FROM episodes").fetchone()[0] == "test-embed-v1"


def test_coverage_is_reported_so_a_dead_endpoint_is_not_silence(store):
    """A rhythm reporting "0 embedded" because the endpoint is down looks
    exactly like one reporting "0 embedded" because there is nothing to do."""
    for i in range(4):
        _read(store, f"I read piece {i}", 1000.0 + i)
    e = _Embedder()

    embed_pending(store, e, limit=2)
    assert coverage(store, e.model) == (2, 4)


def test_a_missing_embed_role_turns_the_rhythm_off_rather_than_crashing(tmp_path):
    """No EMBED role is a configuration state, not a crash. Restarting a
    rhythm that cannot work would be a crash loop wearing a retry."""
    import asyncio

    class _NoRole:
        roles: dict = {}

    sched = EmbeddingScheduler(tmp_path / "newz.db", _NoRole())
    asyncio.run(asyncio.wait_for(sched.run(), timeout=5))


def test_embeddings_do_not_touch_the_ingest_budget():
    """`Embedder` posts directly to the EMBED endpoint rather than through
    LLMClient, so nothing here reaches llm_calls.jsonl and S2 §9.1's reading
    budget is unaffected. A rhythm that quietly paused the being's reading
    would be a poor way to repair its memory."""
    import inspect

    from newz.memory import embeddings

    src = inspect.getsource(embeddings)
    assert "CallRecorder" not in src and "recorder" not in src
    assert "httpx" in src
