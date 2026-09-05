"""The model endpoint and name come from `.env`, and inference stays local."""

from __future__ import annotations

import pytest

from newz.model.config import READ_KEYS, ModelConfig, ModelConfigError, load, read_env_file

ENV = """\
# LLM endpoints (role-keyed)
#LLM_ENDPOINT_AMBIENT=http://10.0.0.50:1234/v1
LLM_ENDPOINT_AMBIENT=http://10.0.0.214:1234/v1
LLM_MODEL_AMBIENT=qwen/qwen3.6-35b-a3b

TELEGRAM_BOT_TOKEN=a-secret-nobody-asked-for
GMAIL_PASS=another-one

LLM_MODEL_EMBED=text-embedding-nomic-embed-text-v1.5@q8_0
"""


@pytest.fixture
def env_file(tmp_path):
    path = tmp_path / ".env"
    path.write_text(ENV, encoding="utf-8")
    return path


def test_both_values_are_read_from_the_file(env_file):
    config = load({}, env_file)
    assert config.endpoint == "http://10.0.0.214:1234/v1"
    assert config.model == "qwen/qwen3.6-35b-a3b"
    assert config.embedding_model == "text-embedding-nomic-embed-text-v1.5@q8_0"


def test_a_commented_out_endpoint_is_not_read(env_file):
    """The address moved once already; the old line is still in the file."""
    assert "10.0.0.50" not in load({}, env_file).endpoint


def test_only_the_keys_it_needs_are_parsed(env_file):
    """`.env` holds a bot token and a mail password. Neither is this module's."""
    parsed = read_env_file(env_file)
    assert set(parsed) <= READ_KEYS
    assert "TELEGRAM_BOT_TOKEN" not in parsed
    assert "GMAIL_PASS" not in parsed
    assert not any("secret" in value for value in parsed.values())


def test_the_process_environment_wins_over_the_file(env_file):
    config = load({"NEWZ_MODEL_NAME": "qwen/other-model"}, env_file)
    assert config.model == "qwen/other-model"
    assert config.endpoint == "http://10.0.0.214:1234/v1"


def test_the_preferred_keys_win_over_the_superseded_role_keys(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "LLM_ENDPOINT_AMBIENT=http://10.0.0.1:1234/v1\n"
        "NEWZ_MODEL_ENDPOINT=http://10.0.0.2:1234/v1\n"
        "LLM_MODEL_AMBIENT=old\nNEWZ_MODEL_NAME=new\n",
        encoding="utf-8",
    )
    config = load({}, path)
    assert config.endpoint == "http://10.0.0.2:1234/v1"
    assert config.model == "new"


@pytest.mark.parametrize("missing", ["endpoint", "model"])
def test_missing_configuration_raises_rather_than_defaulting(tmp_path, missing):
    lines = {
        "endpoint": "LLM_ENDPOINT_AMBIENT=http://10.0.0.214:1234/v1",
        "model": "LLM_MODEL_AMBIENT=qwen/qwen3.6-35b-a3b",
    }
    del lines[missing]
    path = tmp_path / ".env"
    path.write_text("\n".join(lines.values()), encoding="utf-8")
    with pytest.raises(ModelConfigError, match=missing):
        load({}, path)


def test_an_absent_file_is_not_silently_a_working_default(tmp_path):
    with pytest.raises(ModelConfigError):
        load({}, tmp_path / "nothing-here")


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://10.0.0.214:1234/v1",
        "http://127.0.0.1:1234/v1",
        "http://localhost:1234/v1",
        "http://192.168.1.40:1234/v1",
        "http://[::1]:1234/v1",
    ],
)
def test_a_local_endpoint_is_accepted(endpoint):
    assert ModelConfig(endpoint=endpoint, model="m").is_local


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://api.some-vendor.example/v1",
        "http://93.184.216.34:1234/v1",
        "https://inference.example.org/v1",
    ],
)
def test_an_endpoint_off_the_local_network_is_refused(endpoint):
    """The inverse of the acquisition rule, and the reason is TRUE_NORTH's."""
    assert not ModelConfig(endpoint=endpoint, model="m").is_local
    with pytest.raises(ModelConfigError, match="not on the local network"):
        load({"NEWZ_MODEL_ENDPOINT": endpoint, "NEWZ_MODEL_NAME": "m"}, "/nonexistent")


def test_the_locality_refusal_can_be_lifted_deliberately_and_never_by_accident():
    """It is an argument a caller has to pass, not a value that drifts."""
    config = load(
        {"NEWZ_MODEL_ENDPOINT": "https://api.some-vendor.example/v1", "NEWZ_MODEL_NAME": "m"},
        "/nonexistent",
        require_local=False,
    )
    assert not config.is_local


def test_the_operators_own_env_loads(tmp_path):
    """The repository's `.env`, if it is there, is the configuration in force."""
    from pathlib import Path

    env = Path(".env")
    if not env.exists():
        pytest.skip("no .env in the working tree")
    config = load({}, env)
    assert config.endpoint.startswith("http")
    assert config.model
    assert config.is_local
