"""Turning a concern into something a search index can answer.

The missing link in the cascade (found 2026-08-12). Concern statements are
full questions — *"How does Montaigne's concept of the unconscious anticipate
Jung's later theories?"* — and search APIs want terms. Measured: that
sentence returns nothing from Wikipedia, while "Carl Jung collective
unconscious" returns the right article. The adapters were working and the
query was wrong.

Several queries rather than one, because a concern usually has more than one
searchable angle and the adapters index different things: a term that finds
the philosophy paper is not the term that finds the encyclopaedia entry.
v1 carried the same idea in `research/question.py`; this is the same
mechanism rebuilt against the concern store.
"""

from __future__ import annotations

import logging

from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml
from newz.world.sources import clean_query

logger = logging.getLogger(__name__)

MAX_QUERIES = 3

_SYSTEM = (
    "You turn a research question into search terms for academic and "
    "reference indexes. You respond with XML only."
)

_TASK = """<task>
Turn this question into search queries an index can actually answer.

  - Terms, not a sentence. Drop "how does", "what specific", "why".
  - Name the entities: people, works, concepts, institutions.
  - Give up to three DIFFERENT angles, not three rewordings — a query that
    finds a philosophy paper is not the one that finds an encyclopaedia
    entry.
  - Two to six words each.

Example:
  question: "How does Montaigne's concept of the unconscious anticipate
             Jung's later theories?"
  queries:  "Montaigne self-knowledge essays" /
            "Jung collective unconscious archetypes" /
            "history of the unconscious before Freud"

Output ONLY:
<queries>
  <q>first search</q>
  <q>second search</q>
</queries>
</task>"""


def search_queries(client: LLMClient, question: str, *,
                   limit: int = MAX_QUERIES) -> list[str]:
    """Search terms for one concern. Falls back to the cleaned question."""
    fallback = [clean_query(question)]
    try:
        result = client.complete(
            "AMBIENT", _SYSTEM, f"{_TASK}\n\n<question>{question}</question>",
            max_tokens=250, temperature=0.2, function="ingest",
        )
        root = extract_xml(result.text, "queries")
    except (XMLExtractionError, Exception) as e:  # noqa: BLE001
        logger.info("question formation unusable (%s) — searching the question", e)
        return fallback

    out: list[str] = []
    for el in root.findall("q"):
        q = clean_query((el.text or "").strip(), max_words=8)
        if q and q.lower() not in {o.lower() for o in out}:
            out.append(q)
    if not out:
        return fallback
    logger.info("search terms: %s", " | ".join(out[:limit]))
    return out[:limit]
