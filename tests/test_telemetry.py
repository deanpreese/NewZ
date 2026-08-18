import json
import time

from newz.telemetry import read_budget


def _log(tmp_path, rows):
    p = tmp_path / "llm_calls.jsonl"
    with open(p, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return p


def _call(function, tok, age_h=0.0):
    return {"ts": time.time() - age_h * 3600, "role": "DEEP", "function": function,
            "prompt_tokens": tok, "completion_tokens": 0, "duration_s": 1.0}


def test_shares_by_function(tmp_path):
    p = _log(tmp_path, [_call("sleep", 100), _call("gate", 50), _call("conversation", 50)])
    r = read_budget(p)
    assert r.calls == 3 and r.tokens == 200
    assert r.share("sleep") == 0.5
    assert r.by_function["gate"]["calls"] == 1


def test_window_excludes_old_calls(tmp_path):
    p = _log(tmp_path, [_call("sleep", 100, age_h=1), _call("sleep", 999, age_h=200)])
    assert read_budget(p, window_hours=24).tokens == 100


def test_diet_invariant_holds_and_breaches(tmp_path):
    holds = read_budget(_log(tmp_path, [_call("sleep", 500), _call("ingest", 200)]))
    assert holds.invariant_holds()
    assert holds.ingest_headroom() == 300

    breach = read_budget(_log(tmp_path, [_call("sleep", 100), _call("ingest", 900)]))
    assert not breach.invariant_holds()
    assert breach.ingest_headroom() == 0


def test_no_consolidation_means_no_ingest_allowed(tmp_path):
    # P2 §1's arithmetic: before sleep exists the denominator is zero, so any
    # ingest breaches — which is why feeds cannot precede Phase 1.
    r = read_budget(_log(tmp_path, [_call("conversation", 500), _call("gate", 200)]))
    assert r.earning_tokens == 0
    assert r.ingest_headroom() == 0
    assert r.invariant_holds()          # vacuously: no ingest has happened
    breach = read_budget(_log(tmp_path, [_call("conversation", 500), _call("ingest", 1)]))
    assert not breach.invariant_holds()


def test_untagged_calls_are_visible_not_hidden(tmp_path):
    p = _log(tmp_path, [{"ts": time.time(), "role": "DEEP",
                         "prompt_tokens": 10, "completion_tokens": 5}])
    r = read_budget(p)
    assert r.by_function["unspecified"]["tokens"] == 15


def test_missing_log_is_empty_not_an_error(tmp_path):
    assert read_budget(tmp_path / "nope.jsonl").calls == 0


# ── the sizing (P2 Phase 2.4, done 2026-08-16) ───────────────────────────
#
# S2 §9.1 states the invariant and its target in one sentence: "ingest may not
# exceed deliberation + consolidation (target: ≤50% of tokens)". Those are the
# same number only if deliberation+consolidation is about half of cognition.
# Measured, it is nine percent — conversation is 42% and the gate 15% — so the
# ratio alone capped ingest at about a fifth of the share the sentence names.

from newz.telemetry import INGEST_SHARE_CEILING


def test_the_share_ceiling_applies_when_thinking_is_a_small_share(tmp_path):
    # The live shape: a lot of conversation, a little deliberation.
    b = read_budget(_log(tmp_path, [
        _call("conversation", 8_000), _call("gate", 1_000),
        _call("deliberation", 500), _call("ingest", 900)]))
    assert b.earning_tokens == 500
    assert b.share_ceiling_tokens == int(10_400 * INGEST_SHARE_CEILING)
    assert b.binding_ceiling() == "share"
    # Under the ratio alone this would have breached at 900 > 500.
    assert b.invariant_holds()
    assert b.ingest_headroom() == b.share_ceiling_tokens - 900


def test_the_ratio_still_binds_when_it_is_the_looser_of_the_two(tmp_path):
    # A being that thinks far more than it talks keeps the original ceiling,
    # which is higher for it than the share would be.
    b = read_budget(_log(tmp_path, [
        _call("deliberation", 9_000), _call("ingest", 1_000)]))
    assert b.earning_tokens == 9_000
    assert b.binding_ceiling() == "ratio"
    assert b.ingest_ceiling() == 9_000


def test_zero_earning_is_still_zero_ceiling(tmp_path):
    # P2 §1's arithmetic, and the first draft of the sizing broke it: "before
    # sleep and deliberation exist that denominator is zero, so any ingest
    # whatsoever breaches". Without this a being that had only held
    # conversations could read half of them back, having never thought.
    b = read_budget(_log(tmp_path, [
        _call("conversation", 50_000), _call("gate", 10_000)]))
    assert b.share_ceiling_tokens > 0        # the share alone would allow it
    assert b.ingest_ceiling() == 0
    assert b.ingest_headroom() == 0
    assert not b.invariant_holds() or b.ingest_tokens == 0


def test_a_breach_is_still_a_breach_above_the_looser_ceiling(tmp_path):
    b = read_budget(_log(tmp_path, [
        _call("conversation", 1_000), _call("deliberation", 100),
        _call("ingest", 5_000)]))
    assert not b.invariant_holds()
    assert b.ingest_headroom() == 0
