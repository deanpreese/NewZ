"""LLM client — role-keyed, OpenAI-compatible, thinking off by construction.

S2 §16 model-call discipline: every call asserts thinking off per-call,
never assumed from server config. Empirically benched 2026-08-08 against
LM Studio + qwen/qwen3.6-35b-a3b: `reasoning_effort: "none"` is the switch
this stack honors (0 reasoning tokens); the Qwen3 soft switches (`/no_think`,
`/nothink`) and `chat_template_kwargs.enable_thinking` are all ignored by it.
We send `reasoning_effort` plus `enable_thinking=false` as a belt for other
OpenAI-compatible stacks, and never pollute prompts with soft switches.
Thinking may be enabled only for DEEP (S2 §16 reconsideration path), and any
thinking stream that comes back is substrate scratch: stripped here, never
returned to a caller, never stored.

Structured output is XML, never JSON (S2 §16): this client exposes no JSON
mode and no response_format parameter.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from newz.config import Config

logger = logging.getLogger(__name__)

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>\s*", re.S)


@dataclass
class LLMResult:
    text: str
    role: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    # True when the model stopped because it hit max_tokens rather than
    # finishing. A truncated generation must never be sent, judged, or
    # stored as if it were what the being meant to say.
    truncated: bool = False


class LLMClient:
    def __init__(self, config: Config, timeout: float = 300.0, recorder=None):
        self._roles = config.roles
        self._timeout = timeout
        self._recorder = recorder  # CallRecorder | None (S2 §16 recording)

    def complete(
        self,
        role: str,
        system: str,
        user: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        think: bool = False,
        function: str = "unspecified",
    ) -> LLMResult:
        """`function` is what this call is FOR (S2 §14.4 budget telemetry).

        Role is not function: today AMBIENT happens to mean the gate, but in
        Phase 2 ingest joins it on the same role and the proxy breaks. The
        S2 §9.1 diet invariant — ingest ≤ deliberation + consolidation — is
        computed from this tag, so it must be explicit at every call site.
        """
        if role not in self._roles:
            raise KeyError(f"no endpoint configured for role {role!r}")
        if think and role != "DEEP":
            raise ValueError("thinking may be enabled only for DEEP (S2 §16)")
        r = self._roles[role]
        body = self.build_request(r.model, system, user, max_tokens=max_tokens,
                                  temperature=temperature, think=think)
        import time as _time

        started = _time.monotonic()
        error: str | None = None
        text, p_tok, c_tok, truncated = "", 0, 0, False
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(f"{r.endpoint}/chat/completions", json=body)
                resp.raise_for_status()
                data = resp.json()
            choice = data["choices"][0]
            text = strip_thinking(choice["message"].get("content") or "")
            truncated = choice.get("finish_reason") == "length"
            if truncated:
                logger.warning(
                    "%s hit the %d-token cap — response is incomplete", role, max_tokens
                )
            usage = data.get("usage", {})
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            raise
        finally:
            if self._recorder is not None:
                self._recorder.record(
                    role=role, model=r.model, system=system, user=user,
                    response=text, prompt_tokens=p_tok, completion_tokens=c_tok,
                    duration_s=_time.monotonic() - started, think=think,
                    error=error, function=function,
                )
        return LLMResult(
            text=text, role=role, model=r.model,
            prompt_tokens=p_tok, completion_tokens=c_tok, truncated=truncated,
        )

    @staticmethod
    def build_request(
        model: str,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperature: float,
        think: bool,
    ) -> dict:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "chat_template_kwargs": {"enable_thinking": think},
        }
        if not think:
            body["reasoning_effort"] = "none"
        return body


def strip_thinking(text: str) -> str:
    # Substrate scratch: a <think> block is discarded before anything else
    # sees the text — it must never reach memory, evidence, or a human.
    return _THINK_BLOCK_RE.sub("", text).strip()
