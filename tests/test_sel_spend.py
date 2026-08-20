"""The loop's spend is recorded in its own log and never enters the being's
diet denominator (operator decision, 2026-08-20 — option 1b).

**The hazard this exists for.** S2 §9.1's ingest ceiling is a share of ALL
cognition, read from `logs/llm_calls.jsonl`. If the loop's calls were tagged
into that same file, the denominator would grow with the loop's own thinking
and the being's reading limit would rise with it — a self-serving path through
the one invariant that constrains ingest, available to the process that writes
the log. Two files, and the diet reads one of them.

The loop does not exist yet (E8.2 builds the runner that would write the second
file). These tests fix the rule before there is code to break it, which is the
only order in which that is cheap.
"""

import json
import time
from pathlib import Path

from newz.telemetry import read_budget

BEING_LOG = "llm_calls.jsonl"
SEL_LOG = "sel_calls.jsonl"


def _line(function: str, tokens: int) -> str:
    return json.dumps({
        "ts": time.time(), "role": "DEEP", "function": function,
        "model": "m", "think": False, "system": "", "user": "", "response": "",
        "prompt_tokens": tokens, "completion_tokens": 0, "duration_s": 0.1,
    })


def _logs(tmp_path: Path) -> tuple[Path, Path]:
    being = tmp_path / BEING_LOG
    being.write_text("\n".join([
        _line("ingest", 400), _line("deliberation", 300), _line("sleep", 300)]) + "\n")
    sel = tmp_path / SEL_LOG
    sel.write_text("\n".join([_line("sel.read", 5_000), _line("sel.decide", 5_000)]) + "\n")
    return being, sel


def test_the_diet_denominator_is_the_beings_log_alone(tmp_path):
    being, sel = _logs(tmp_path)
    b = read_budget(being, window_hours=24)
    assert b.tokens == 1_000
    assert "sel.read" not in b.by_function
    assert b.share_ceiling_tokens == 500


def test_merging_the_logs_would_have_raised_the_beings_ingest_ceiling(tmp_path):
    """The hazard, quantified, so the reason for two files is not just asserted.

    10,000 tokens of the loop thinking would lift the ceiling on the being's
    reading from 500 to 5,500 — an eleven-fold relaxation of §9.1 bought by
    spending on something that is not the being at all."""
    being, sel = _logs(tmp_path)
    merged = tmp_path / "merged.jsonl"
    merged.write_text(being.read_text() + sel.read_text())

    honest = read_budget(being, window_hours=24).share_ceiling_tokens
    corrupted = read_budget(merged, window_hours=24).share_ceiling_tokens
    assert honest == 500
    assert corrupted == 5_500
    assert corrupted > honest * 10


def test_the_sel_log_reads_with_the_same_instrument(tmp_path):
    """Option 1b costs no new reader: the second file is the same format and
    read_budget already takes a path."""
    _, sel = _logs(tmp_path)
    s = read_budget(sel, window_hours=24)
    assert s.calls == 2
    assert s.tokens == 10_000
    assert set(s.by_function) == {"sel.read", "sel.decide"}


def test_a_missing_sel_log_is_zero_and_not_an_error(tmp_path):
    """Before E8.2 the file does not exist, and the weekly read must still
    run rather than failing on an absent loop."""
    s = read_budget(tmp_path / SEL_LOG, window_hours=24)
    assert s.calls == 0 and s.tokens == 0
