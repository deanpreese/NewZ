"""Embeddings (S2 §12.1, EMBED role) — local, in-process from the being's view.

Vectors are stored as raw float32 bytes on `episodes.embedding`, alongside
`embedding_model` so a vector is never compared against one from a different
embedder. v1's imported vectors came from a different model and are treated
as untrusted: they are overwritten, not reused, because a mixed vector space
corrupts retrieval silently — and retrieval feeds evidence contexts, where
the v1 self-echo leak lived.
"""

from __future__ import annotations

import array
import logging
import math

import httpx

from newz.config import Config

logger = logging.getLogger(__name__)

BATCH = 32


class Embedder:
    def __init__(self, config: Config, timeout: float = 120.0):
        role = config.roles.get("EMBED")
        if role is None:
            raise RuntimeError(
                "EMBED role not configured (LLM_MODEL_EMBED); retrieval needs it"
            )
        self.model = role.model
        self._endpoint = role.endpoint
        self._timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        with httpx.Client(timeout=self._timeout) as client:
            for i in range(0, len(texts), BATCH):
                chunk = [t[:8000] for t in texts[i : i + BATCH]]
                resp = client.post(
                    f"{self._endpoint}/embeddings",
                    json={"model": self.model, "input": chunk},
                )
                resp.raise_for_status()
                data = resp.json()["data"]
                # The API may return out of order; index is authoritative.
                ordered = sorted(data, key=lambda d: d.get("index", 0))
                out.extend(d["embedding"] for d in ordered)
        return out

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


def pack(vector: list[float]) -> bytes:
    return array.array("f", vector).tobytes()


def unpack(blob: bytes) -> list[float]:
    a = array.array("f")
    a.frombytes(blob)
    return list(a)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
