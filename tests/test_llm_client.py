import pytest

from newz.config import Config, LLMRole
from newz.llm.client import LLMClient, strip_thinking


def _config(tmp_path):
    return Config(
        repo_root=tmp_path,
        data_dir=tmp_path,
        main_db_path=tmp_path / "newz.db",
        interior_db_path=tmp_path / "interior.db",
        monitor_db_path=tmp_path / "monitor.db",
        backups_dir=tmp_path / "backups",
        roles={
            "DEEP": LLMRole("DEEP", "http://localhost:9", "m"),
            "AMBIENT": LLMRole("AMBIENT", "http://localhost:9", "m"),
        },
    )


def test_thinking_off_by_default_and_deep_only(tmp_path):
    body = LLMClient.build_request("m", "sys", "usr", max_tokens=10, temperature=0.1, think=False)
    # reasoning_effort="none" is the switch the live stack honors (benched
    # 2026-08-08: 0 reasoning tokens); enable_thinking=false is the belt.
    assert body["reasoning_effort"] == "none"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}

    body_think = LLMClient.build_request("m", "sys", "usr", max_tokens=10, temperature=0.1, think=True)
    assert "reasoning_effort" not in body_think
    assert body_think["chat_template_kwargs"] == {"enable_thinking": True}

    client = LLMClient(_config(tmp_path))
    with pytest.raises(ValueError):
        client.complete("AMBIENT", "sys", "usr", think=True)


def test_think_block_stripped():
    raw = "<think>secret scratch\nacross lines</think>  the actual answer"
    assert strip_thinking(raw) == "the actual answer"
    assert strip_thinking("no block") == "no block"


def test_no_json_mode_exposed():
    import inspect

    sig = inspect.signature(LLMClient.build_request)
    assert "response_format" not in sig.parameters
    assert "json" not in [p.lower() for p in sig.parameters]
