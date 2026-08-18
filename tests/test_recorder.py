import json

from newz.llm.recorder import CallRecorder


def test_records_full_call_as_jsonl(tmp_path):
    rec = CallRecorder(tmp_path / "logs" / "llm_calls.jsonl")
    rec.record(role="VOICE", model="m", system="sys", user="usr", response="out",
               prompt_tokens=10, completion_tokens=5, duration_s=1.234, think=False)
    lines = (tmp_path / "logs" / "llm_calls.jsonl").read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["role"] == "VOICE" and row["system"] == "sys" and row["response"] == "out"
    assert row["error"] is None


def test_size_rotation(tmp_path):
    rec = CallRecorder(tmp_path / "llm_calls.jsonl", max_bytes=500)
    for _ in range(20):
        rec.record(role="AMBIENT", model="m", system="s" * 40, user="u" * 40,
                   response="r" * 40, prompt_tokens=1, completion_tokens=1,
                   duration_s=0.1, think=False)
    assert (tmp_path / "llm_calls.jsonl").exists()
    assert (tmp_path / "llm_calls.jsonl.1").exists()
