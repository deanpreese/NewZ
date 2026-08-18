"""Retrieval (S2 §4.3) — indexed, provenance-tagged, self-echo excluded.

Two rules carried from the review of v1:

- **Provenance flows into every result**, so the being always knows whether
  it is looking at the world, another person, or itself.
- **Self-echo is excluded from evidence contexts by provenance filter, and
  the v1 leak is the regression test.** v1's own probes ranked as lived
  history; here `EVIDENCE` scope excludes `provenance='self'` outright, and
  a test asserts a self-probe cannot surface as evidence.

Scoring is similarity with a mild recency lean — old material stays
reachable (that is the point of having a past), but two comparably relevant
memories resolve toward the more recent one.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from newz.memory.embeddings import Embedder, cosine, unpack

# How much a year of age costs a memory, multiplicatively. Small on purpose.
RECENCY_HALFLIFE_DAYS = 365.0
MIN_SIMILARITY = 0.25


@dataclass
class Hit:
    episode_id: int
    ts: float
    kind: str
    provenance: str
    summary: str
    similarity: float
    score: float


class Scope:
    """Which memories a query is allowed to see."""

    ALL = "all"
    # Evidence must not be the being's own voice coming back to it.
    EVIDENCE = "evidence"
    # Shared history with one person (S2 §6.2's conversation retrieval).
    PERSON = "person"


def _where(scope: str, person_id: str | None) -> tuple[str, list]:
    if scope == Scope.EVIDENCE:
        return "AND provenance <> 'self'", []
    if scope == Scope.PERSON:
        return "AND provenance = ?", [f"human:{person_id}"]
    return "", []


class Retriever:
    def __init__(self, conn: sqlite3.Connection, embedder: Embedder):
        self._conn = conn
        self._embedder = embedder

    def search(
        self,
        query: str,
        *,
        k: int = 6,
        scope: str = Scope.ALL,
        person_id: str | None = None,
        exclude_after: float | None = None,
    ) -> list[Hit]:
        clause, params = _where(scope, person_id)
        rows = self._conn.execute(
            "SELECT id, ts, kind, provenance, summary, embedding FROM episodes"
            " WHERE embedding IS NOT NULL AND embedding_model = ?"
            f" {clause}"
            + (" AND ts < ?" if exclude_after else ""),
            [self._embedder.model, *params]
            + ([exclude_after] if exclude_after else []),
        ).fetchall()
        if not rows:
            return []

        qv = self._embedder.embed_one(query)
        newest = max(r["ts"] for r in rows)
        hits: list[Hit] = []
        for r in rows:
            sim = cosine(qv, unpack(r["embedding"]))
            if sim < MIN_SIMILARITY:
                continue
            age_days = max(0.0, (newest - r["ts"]) / 86400)
            score = sim * (0.5 ** (age_days / RECENCY_HALFLIFE_DAYS))
            hits.append(Hit(
                episode_id=r["id"], ts=r["ts"], kind=r["kind"],
                provenance=r["provenance"], summary=r["summary"],
                similarity=round(sim, 4), score=round(score, 4),
            ))
        hits.sort(key=lambda h: -h.score)
        return hits[:k]


def render_hits(hits: list[Hit], person_id: str) -> str:
    """Retrieved memories, provenance visible to the being (S2 §4.3)."""
    if not hits:
        return ""
    import datetime

    lines = []
    for h in hits:
        who = ("me" if h.provenance == "self"
               else person_id if h.provenance == f"human:{person_id}"
               else h.provenance)
        when = datetime.date.fromtimestamp(h.ts)
        lines.append(f"- [{when}, from {who}] {h.summary[:300]}")
    return "\n".join(lines)
