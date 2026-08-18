"""LLM-call recording with size-based rotation (S2 §16).

Every call — role, model, full prompts, full response, tokens, duration —
appends one JSON line to logs/llm_calls.jsonl. When the file exceeds the
size cap it rotates to .1 (one generation kept). This is what made v1's
gate diagnosable; v2 records from day one.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

DEFAULT_MAX_BYTES = 50 * 1024 * 1024


class CallRecorder:
    def __init__(self, path: Path, max_bytes: int = DEFAULT_MAX_BYTES):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        role: str,
        model: str,
        system: str,
        user: str,
        response: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_s: float,
        think: bool,
        error: str | None = None,
        function: str = "unspecified",
    ) -> None:
        self._rotate_if_needed()
        line = json.dumps(
            {
                "ts": time.time(),
                "role": role,
                "function": function,
                "model": model,
                "think": think,
                "system": system,
                "user": user,
                "response": response,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "duration_s": round(duration_s, 3),
                "error": error,
            },
            ensure_ascii=False,
        )
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _rotate_if_needed(self) -> None:
        try:
            if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
                rotated = self.path.with_suffix(self.path.suffix + ".1")
                if rotated.exists():
                    rotated.unlink()
                self.path.rename(rotated)
        except OSError:
            pass  # recording must never take the being down
