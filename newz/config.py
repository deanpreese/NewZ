"""Configuration — env-driven, role-keyed per S2 §12.1.

Roles: VOICE (the being's voice), AMBIENT (classification/extraction/noticing),
DEEP (deliberation reasoning, sleep synthesis). EMBED is in-process and needs
no endpoint here. Legacy v1 key names (EXTRACT→AMBIENT, REASON→DEEP) are
accepted with a mapping so an old .env still boots, but new names win.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

DEFAULT_USER_AGENT = (
    "newz-being/2.0 (sovereign reader for a single private research agent; "
    "no contact address configured)"
)

ROLES = ("VOICE", "AMBIENT", "DEEP", "EMBED")
_LEGACY_ROLE_KEYS = {"AMBIENT": "EXTRACT", "DEEP": "REASON", "VOICE": "VOICE"}
# EMBED shares the local endpoint with the other roles unless told otherwise;
# only the model differs, so a missing endpoint falls back to AMBIENT's.
_SHARES_ENDPOINT_WITH = {"EMBED": "AMBIENT"}


@dataclass(frozen=True)
class LLMRole:
    name: str
    endpoint: str
    model: str


@dataclass(frozen=True)
class Config:
    repo_root: Path
    data_dir: Path
    main_db_path: Path
    interior_db_path: Path
    backups_dir: Path
    roles: dict[str, LLMRole] = field(default_factory=dict)
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    operator_id: str | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    sleep_hour: int = 3          # nightly consolidation at or after this hour
    # Sovereign adapter identity. Wikipedia requires a reachable contact and
    # returns 403 without one (verified 2026-08-12).
    user_agent: str = ""


def _role_value(env: dict[str, str | None], kind: str, role: str) -> str | None:
    # kind is "ENDPOINT" or "MODEL"; prefer the S2 role name, fall back to legacy.
    v = env.get(f"LLM_{kind}_{role}")
    if v:
        return v
    legacy = _LEGACY_ROLE_KEYS.get(role)
    if legacy:
        return env.get(f"LLM_{kind}_{legacy}")
    return None


def load(repo_root: Path | None = None, env_file: str | os.PathLike | None = None) -> Config:
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parent.parent
    env_path = Path(env_file) if env_file else root / ".env"
    env: dict[str, str | None] = dict(os.environ)
    if env_path.exists():
        # File values take precedence over inherited shell env for determinism.
        env.update({k: v for k, v in dotenv_values(env_path).items() if v is not None})

    data_dir = Path(env.get("NEWZ_DATA_DIR") or env.get("NGBEING_DATA_DIR") or "./data")
    if not data_dir.is_absolute():
        data_dir = root / data_dir

    roles: dict[str, LLMRole] = {}
    for role in ROLES:
        endpoint = _role_value(env, "ENDPOINT", role)
        model = _role_value(env, "MODEL", role)
        if not endpoint and role in _SHARES_ENDPOINT_WITH:
            endpoint = _role_value(env, "ENDPOINT", _SHARES_ENDPOINT_WITH[role])
        if endpoint and model:
            roles[role] = LLMRole(name=role, endpoint=endpoint.rstrip("/"), model=model)

    return Config(
        repo_root=root,
        data_dir=data_dir,
        main_db_path=data_dir / "newz.db",
        interior_db_path=data_dir / "interior.db",
        backups_dir=root / "backups",
        roles=roles,
        telegram_bot_token=env.get("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=env.get("TELEGRAM_CHAT_ID"),
        operator_id=env.get("OPERATOR_ID"),
        quiet_hours_start=env.get("QUIET_HOURS_START"),
        quiet_hours_end=env.get("QUIET_HOURS_END"),
        sleep_hour=int(env.get("NEWZ_SLEEP_HOUR") or 3),
        user_agent=env.get("NEWZ_USER_AGENT") or DEFAULT_USER_AGENT,
    )
