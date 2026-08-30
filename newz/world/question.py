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
  - Name the entities: people, works, concepts, institutions. **Keep them even
    when asked for a new angle** — an angle is a different way into the same
    subject, not a different subject.
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

# **Told "not those", a model drops the entity.** Measured by
# `tools/question_probe.py`, 2026-08-30: asked for angles its previous terms
# had not covered, the model turned "EU Digital Services Act amplification
# definition" into "algorithmic transparency technical metrics" and the new
# candidates came back as Explainable AI and Technical Debt Prioritization —
# best relevance 0.683 -> 0.590. It obeyed "different" by abandoning the
# subject. The other three questions kept their entities and gained material
# the being had never been offered, so the instruction is not "be different",
# it is "same subject, different way in".
_TRIED = """

<already_tried>
These searches have already been run for this question and returned nothing
worth reading. The indexes have been asked in these words and answered.

Give angles these did not cover — a different discipline, a different named
entity in the same subject, the mechanism rather than the phenomenon, or the
phenomenon rather than the mechanism.

**Keep the subject.** Dropping the entity that identifies the question is not
a new angle, it is a new question, and it returns material about something
else.

{terms}
</already_tried>"""


def search_queries(client: LLMClient, question: str, *,
                   limit: int = MAX_QUERIES,
                   tried: list[str] | None = None) -> list[str]:
    """Search terms for one concern. Falls back to the cleaned question.

    `tried` is what this question has already been asked in and got nothing
    for (0046). Without it the same statement produced the same terms every
    cycle, so the adapters returned the same rows, R1's dedup removed what had
    been read on the first pass, and triage refused the tail — seventeen times
    for one question. The terms are a hint and never a constraint: the model
    may return one of them, and the floor and triage still decide what is read.
    """
    fallback = [clean_query(question)]
    block = _TRIED.format(
        terms="\n".join(f"  - {t}" for t in tried)) if tried else ""
    try:
        result = client.complete(
            "AMBIENT", _SYSTEM, f"{_TASK}{block}\n\n<question>{question}</question>",
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
