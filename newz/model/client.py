"""The model client: the second, and last, module that opens a socket.

It differs from the acquisition transport in every way that matters. That one
fetches URLs it did not choose and treats everything it receives as hostile.
This one talks to exactly one endpoint, configured by the operator and checked
to be local, and never to an address that came from retained content. The two
are separate doors because they are separate risks, and a single "http helper"
serving both would let one of them inherit the other's assumptions.

What comes back is a proposal. `SPEC.md` section 2.3: a model may propose
extraction, classification, summaries, search queries, notices and research
tasks, and may not grant evidence capability, establish independence, lower
risk, delete history, or publish. None of that is enforced here — it is enforced
by the proposal having nowhere to say it.
"""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

from newz.model.config import ModelConfig


@dataclass(frozen=True, slots=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    elapsed_ms: int = 0


class ModelUnavailable(Exception):
    """The model did not answer. Never a reason to proceed without it."""


class ModelClient(Protocol):
    def complete(self, system: str, user: str, max_tokens: int = 2048) -> Completion: ...


class LocalModelClient:
    """An OpenAI-compatible chat completion against the configured endpoint."""

    def __init__(self, config: ModelConfig, timeout: float = 120.0) -> None:
        self.config = config
        self.timeout = timeout

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> Completion:
        parts = urlsplit(self.config.endpoint)
        host = parts.hostname or ""
        port = parts.port or (443 if parts.scheme == "https" else 80)
        path = (parts.path.rstrip("/") or "/v1") + "/chat/completions"

        payload = json.dumps(
            {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                # Determinism where the endpoint offers it. A proposer that
                # answers differently to the same prompt makes an extraction
                # unreproducible, and SPEC 13 asks for replay.
                "temperature": 0,
                "max_tokens": max_tokens,
                # Thinking off: the rigor lives in policy and the evidence
                # graph, and chain-of-thought is not something an assessment may
                # rest on (Gate 2).
                "reasoning_effort": "none",
                "stream": False,
            }
        ).encode("utf-8")

        connection = (
            http.client.HTTPSConnection(host, port, timeout=self.timeout)
            if parts.scheme == "https"
            else http.client.HTTPConnection(host, port, timeout=self.timeout)
        )
        try:
            connection.request(
                "POST",
                path,
                body=payload,
                headers={"Content-Type": "application/json", "Connection": "close"},
            )
            response = connection.getresponse()
            body = response.read()
            if response.status != 200:
                raise ModelUnavailable(f"HTTP {response.status} from {host}:{port}")
        except OSError as error:
            raise ModelUnavailable(f"{type(error).__name__}: {error}") from error
        finally:
            connection.close()

        try:
            document = json.loads(body)
            choice = document["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise ModelUnavailable(f"unreadable completion: {error}") from error

        usage = document.get("usage") or {}
        return Completion(
            text=choice or "",
            model=document.get("model", self.config.model),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )
