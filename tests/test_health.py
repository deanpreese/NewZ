"""The first tests health.py has ever had (#40, 2026-08-16).

It is the instrument the operator reads most and nothing asserted its output,
which is precisely how the diet line kept describing the old ceiling for a day
after #33 changed which ceiling binds. The verdict was right the whole time;
only the words were wrong — the worse failure for an instrument, because the
words are what is read.
"""

import json
import time

from tools.health import diet_line
from newz.telemetry import read_budget


def _log(tmp_path, rows):
    p = tmp_path / "calls.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return p


def _call(function, tok):
    return {"ts": time.time(), "role": "DEEP", "function": function,
            "prompt_tokens": tok, "completion_tokens": 0, "duration_s": 1.0}


def test_the_line_names_the_share_ceiling_when_that_is_what_binds(tmp_path):
    # The live shape since #33: a lot of conversation, a little deliberation,
    # so 50%-of-tokens is far looser than the earning sum.
    b = read_budget(_log(tmp_path, [
        _call("conversation", 8_000), _call("deliberation", 500),
        _call("ingest", 900)]))
    out = diet_line(b)
    assert "share ceiling" in out
    assert f"{b.ingest_ceiling():,}" in out
    assert "earning" not in out, "still describing the ratio it no longer used"


def test_the_line_names_the_ratio_ceiling_when_that_is_what_binds(tmp_path):
    b = read_budget(_log(tmp_path, [
        _call("deliberation", 9_000), _call("ingest", 1_000)]))
    out = diet_line(b)
    assert "ratio ceiling" in out


def test_the_arithmetic_on_the_line_is_actually_true(tmp_path):
    # THE REGRESSION. It printed "ingest 736,948 <= earning 422,402" beside a
    # positive headroom. Whatever comparison the line states must hold.
    for rows in (
        [_call("conversation", 8_000), _call("deliberation", 500), _call("ingest", 900)],
        [_call("deliberation", 9_000), _call("ingest", 1_000)],
        [_call("conversation", 1_000), _call("deliberation", 100), _call("ingest", 5_000)],
    ):
        b = read_budget(_log(tmp_path, rows))
        out = diet_line(b)
        if " <= " in out:
            assert b.ingest_tokens <= b.ingest_ceiling(), out
            assert b.invariant_holds(), out
        elif " > " in out:
            assert b.ingest_tokens > b.ingest_ceiling(), out
            assert not b.invariant_holds(), out


def test_zero_earning_says_so_rather_than_printing_a_ceiling_of_zero(tmp_path):
    # P2 §1's arithmetic: with nothing thought or consolidated, no ingest is
    # permitted however large the window. "ingest 5,000 <= share ceiling 0"
    # would be technically false and useless.
    b = read_budget(_log(tmp_path, [_call("conversation", 50_000)]))
    out = diet_line(b)
    assert "nothing earned yet" in out
    assert "ceiling 0" not in out
