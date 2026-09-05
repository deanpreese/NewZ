"""Where the model lives, read rather than transcribed.

`.env` is the authority for both the endpoint and the model name. ADR-0002 pins
the *tier* and the boundary — small, local, outside the trust boundary — and
deliberately pins neither value, because both are operator configuration that
moves: the endpoint has already moved once, and the model behind an LM Studio
name changes whenever the operator loads a different one.

This module reads no secret it does not need. `.env` also holds a bot token and
a mail password, and a loader that parsed the whole file into a dictionary
somebody later logs is how those leave the machine.
"""

from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

#: Preferred keys, then the role-keyed names from the superseded system. This
#: system has one model role, and `AMBIENT` was the tier that did classification,
#: extraction and noticing — the proposer's job under `SPEC.md` section 2.3.
ENDPOINT_KEYS = ("NEWZ_MODEL_ENDPOINT", "LLM_ENDPOINT_AMBIENT")
MODEL_KEYS = ("NEWZ_MODEL_NAME", "LLM_MODEL_AMBIENT")
EMBEDDING_KEYS = ("NEWZ_EMBEDDING_MODEL", "LLM_MODEL_EMBED")
USER_AGENT_KEYS = ("NEWZ_USER_AGENT",)

READ_KEYS = frozenset(ENDPOINT_KEYS + MODEL_KEYS + EMBEDDING_KEYS + USER_AGENT_KEYS)


class ModelConfigError(RuntimeError):
    """No usable configuration. Raised rather than defaulted.

    A default endpoint that happens to work is a system that reaches somewhere
    nobody chose; a default that does not work is a confusing failure later
    instead of a clear one now.
    """


@dataclass(frozen=True, slots=True)
class ModelConfig:
    endpoint: str
    model: str
    embedding_model: str = ""

    @property
    def host(self) -> str:
        return (urlsplit(self.endpoint).hostname or "").lower()

    @property
    def is_local(self) -> bool:
        """Whether inference stays on the operator's own network.

        The inverse of the acquisition rule, and deliberately so. The fetcher
        refuses an address inside the house because it is reaching outward on
        someone else's instruction. This refuses an address outside it, because
        `TRUE_NORTH.md` forbids an external model becoming the authority for the
        system's judgment, and an endpoint on the public internet is that
        happening whatever the model is called.
        """
        host = self.host
        if not host:
            return False
        if host in ("localhost", "localhost.localdomain"):
            return True
        try:
            address = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            # A name that is not an address cannot be shown to be local without
            # resolving it, and this module resolves nothing.
            return False
        return address.is_private or address.is_loopback or address.is_link_local


def read_env_file(path: Path, keys: frozenset[str] = READ_KEYS) -> dict[str, str]:
    """Parse only the keys asked for, ignoring everything else in the file."""
    if not path.exists():
        return {}
    found: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key in keys:
            found[key] = value.strip().strip('"').strip("'")
    return found


def user_agent(env_file: Path | str = ".env") -> str:
    """The contactable agent string, from `.env` or the environment.

    Kept here rather than in the transport because it is operator configuration
    like the model endpoint, and read the same narrow way: only the key that is
    needed, never the whole file.
    """
    import os

    source = dict(read_env_file(Path(env_file)))
    source.update({k: v for k, v in os.environ.items() if k in READ_KEYS})
    return _first(source, USER_AGENT_KEYS)


def _first(source: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = source.get(key, "").strip()
        if value:
            return value
    return ""


def load(
    environ: dict[str, str] | None = None,
    env_file: Path | str = ".env",
    require_local: bool = True,
) -> ModelConfig:
    """Read the model configuration. The process environment wins over the file."""
    source = dict(read_env_file(Path(env_file)))
    source.update({k: v for k, v in (environ or os.environ).items() if k in READ_KEYS})

    endpoint = _first(source, ENDPOINT_KEYS)
    model = _first(source, MODEL_KEYS)
    missing = [
        name
        for name, value, keys in (
            ("endpoint", endpoint, ENDPOINT_KEYS),
            ("model", model, MODEL_KEYS),
        )
        if not value
    ]
    if missing:
        raise ModelConfigError(
            "no model "
            + " or ".join(missing)
            + f" configured; set one of {', '.join(ENDPOINT_KEYS + MODEL_KEYS)}"
        )

    config = ModelConfig(
        endpoint=endpoint, model=model, embedding_model=_first(source, EMBEDDING_KEYS)
    )
    if require_local and not config.is_local:
        raise ModelConfigError(
            f"the model endpoint {config.endpoint!r} is not on the local network; "
            "ADR-0002 keeps inference local, and this refusal is that decision "
            "rather than a network check"
        )
    return config
