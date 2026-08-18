"""S2 §6.1 — the folded substrate clause.

The producer was scheduled in no phase, 0 through 7; PLAN.md cites §6.1 once,
in Phase 1.5, only to justify cleaning up v1's 1,041 raw telemetry rows. The
newest substrate episode of any kind was 2026-06-13, so when the operator
asked "how are you" the being answered out of v1's cache-miss history — the
most recent information it had about itself.
"""

import json
import time

from newz.world.substrate import (
    SubstrateState,
    already_folded_today,
    latest_fold,
    sample,
    write_fold,
)


def _log(tmp_path, rows):
    p = tmp_path / "calls.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return p


def test_a_clean_day_folds_into_one_readable_clause(store, tmp_path):
    log = _log(tmp_path, [{"ts": time.time(), "role": "VOICE", "duration_s": 2.0}
                          for _ in range(20)])
    st = sample(store, log)
    text = st.fold()
    assert "ran cleanly" in text and "20 calls" in text
    # First person and plain: the being reads this as its own state, and
    # "prefix_cache_miss_rate_high: 1.00" is how v1's self-model went wrong.
    assert text.startswith("Today I")
    # No metric names and no snake_case keys: it is an account, not a log
    # line. "prefix_cache_miss_rate_high: 1.00" is the thing being avoided.
    assert "_" not in text
    # One sentence, so no clause starts lowercase after a full stop.
    assert ". " not in text


def test_a_bad_day_says_so_rather_than_averaging_it_away(store, tmp_path):
    now = time.time()
    rows = [{"ts": now, "role": "VOICE", "duration_s": 1.0} for _ in range(18)]
    rows += [{"ts": now, "role": "VOICE", "error": "timeout"} for _ in range(2)]
    st = sample(store, _log(tmp_path, rows))
    assert st.errors_24h == 2
    assert "failed" in st.fold()
    assert st.salient                       # 10% error rate


def test_a_salient_day_writes_its_own_event_for_affect_to_read(store, tmp_path):
    st = SubstrateState(calls_24h=10, errors_24h=3, unreachable=["DEEP"])
    write_fold(store, st)
    kinds = {r[0] for r in store.execute("SELECT kind FROM episodes")}
    assert kinds == {"substrate", "substrate_event"}
    ev = store.execute(
        "SELECT summary FROM episodes WHERE kind='substrate_event'").fetchone()
    assert "DEEP" in ev["summary"]


def test_only_one_fold_a_day(store):
    # v1 stored 1,041 raw rows; they became 39.6% of the corpus and produced
    # a self-description made of instrumentation. The cap IS the correction.
    assert write_fold(store, SubstrateState(calls_24h=5)) is not None
    assert already_folded_today(store)
    assert write_fold(store, SubstrateState(calls_24h=9)) is None
    assert store.execute(
        "SELECT COUNT(*) FROM episodes WHERE kind='substrate'").fetchone()[0] == 1


def test_the_fold_is_digestible_and_provenanced_as_the_world(store):
    write_fold(store, SubstrateState(calls_24h=5))
    r = store.execute("SELECT provenance, digest_eligible FROM episodes"
                      " WHERE kind='substrate'").fetchone()
    # Not `self`: this is measurement about the being, not the being's own
    # assertion, so it may legitimately serve as evidence (INV-026).
    assert r["provenance"] == "world:substrate"
    assert r["digest_eligible"] == 1


def test_a_stale_fold_is_not_offered_to_conversation(store):
    # Telling the being how it was three days ago is the failure this module
    # exists to end, not a smaller version of it.
    store.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, digest_eligible)"
        " VALUES (?,?,?,?,1)",
        (time.time() - 5 * 86400, "substrate", "world:substrate", "old news"))
    store.commit()
    assert latest_fold(store) == ""


def test_the_fold_reaches_conversation(store):
    from newz.conversation.composer import _system_prompt

    write_fold(store, SubstrateState(calls_24h=42, uptime_s=7200))
    system = _system_prompt(store, "dean")
    assert "How I am actually running today" in system
    assert "42 calls" in system


def test_a_silent_day_is_reported_as_silence_not_as_health(store):
    st = SubstrateState(calls_24h=0)
    assert "not running" in st.fold()
