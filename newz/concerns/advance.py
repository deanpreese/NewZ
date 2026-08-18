"""Advances are earned — the corrected judge (S2 §8.3).

v1 credited reworded aphorisms: three of one concern's four advances were a
single sentence re-worded, and it closed on that count. The correction
requires **all three** of the following, and the first two are decided in
code:

1. **Movement** — bears on the question and does not merely restate what is
   already held. The model gives a stance; code maps the verdict.
2. **Novelty against the WHOLE advance history** — v1 checked only against
   the current tick, which is how the same sentence passed four times.
   Similarity is computed here, over every advance the concern has ever
   recorded.
3. **Evidence-class honesty** — `kind='evidence'` requires non-empty refs
   that actually reached the dossier. Reasoning without sources is recorded
   as `kind='reasoning'`, which is legitimate and labelled. The check gates
   *evidence claims*, not *thought*: parametric knowledge is not invention
   (S2 §8.3), so unsourced reasoning is downgraded, never rejected.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Above these, a candidate says nothing the concern has not already recorded.
#
# Semantic is the operative check and is used whenever an embedder is
# available. Measured 2026-08-11 on nomic-embed-text-v1.5 with the three
# rewordings of v1's aphorism that closed a concern:
#
#     restatements of one claim   cos 0.912 – 0.940
#     genuinely new points        cos 0.422 – 0.495
#     unrelated statements        cos 0.455
#
# 0.80 sits in a very wide gap. The lexical fallback exists so the judge
# still functions with no embedder, but it CANNOT catch paraphrase — the
# same three rewordings score only 0.43 Jaccard, which is precisely how v1
# credited the same sentence four times. Never rely on the fallback where
# an embedder can be had.
SEMANTIC_RESTATEMENT_LIMIT = 0.80
NOVELTY_SIMILARITY_LIMIT = 0.72          # lexical fallback only
_WORD = re.compile(r"[a-z0-9']+")
_STOP = frozenset("""
a an and are as at be but by for from had has have i if in into is it its of on
or that the their there they this to was were what when which who will with my
""".split())


@dataclass
class AdvanceVerdict:
    accepted: bool
    kind: str                      # evidence | reasoning | rejected
    reason: str
    novelty: float = 1.0
    evidence: list[str] = field(default_factory=list)

    @property
    def is_setback(self) -> bool:
        return not self.accepted


def _bag(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP and len(w) > 2}


def similarity(a: str, b: str) -> float:
    """Jaccard over content words. Cheap, explainable, and good enough to
    catch the failure it exists for: the same claim in different words."""
    x, y = _bag(a), _bag(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def novelty_against_history(
    candidate: str, history: list[str], embedder=None
) -> tuple[float, str | None, float]:
    """Lowest novelty against ANY prior advance (v1 checked only the latest).

    Returns (novelty, the advance it echoes, the limit that applied). With an
    embedder this is semantic and catches paraphrase; without one it is
    lexical and catches only near-identical wording.

    **The caller decides what counts as history.** Since 2026-08-15 an advance
    the candidate explicitly SUPERSEDES is excluded, because superseding
    something necessarily resembles it and this function cannot tell the two
    apart — see judge_advance and S2 §8.3's recorded deviation.
    """
    if not history:
        return 1.0, None, SEMANTIC_RESTATEMENT_LIMIT if embedder else NOVELTY_SIMILARITY_LIMIT

    if embedder is not None:
        try:
            vectors = embedder.embed([candidate, *history])
            from newz.memory.embeddings import cosine

            sims = [cosine(vectors[0], v) for v in vectors[1:]]
            best = max(range(len(sims)), key=lambda i: sims[i])
            return 1.0 - sims[best], history[best], SEMANTIC_RESTATEMENT_LIMIT
        except Exception:  # noqa: BLE001
            logger.warning("advance: embedder unavailable, falling back to lexical "
                           "novelty — paraphrase will not be caught", exc_info=True)

    worst, echo = 1.0, None
    for prior in history:
        sim = similarity(candidate, prior)
        if 1.0 - sim < worst:
            worst, echo = 1.0 - sim, prior
    return worst, echo, NOVELTY_SIMILARITY_LIMIT


def judge_advance(
    *,
    summary: str,
    moves: bool,
    claimed_kind: str,
    evidence_refs: list[str],
    dossier_refs: set[str],
    history: list[str],
    embedder=None,
) -> AdvanceVerdict:
    """Code decides; the caller supplies the model's stance as `moves`.

    `dossier_refs` is what actually reached the concern's dossier. An
    evidence claim citing something absent from it is not evidence.
    """
    if not (summary or "").strip():
        return AdvanceVerdict(False, "rejected", "empty summary", 0.0)

    if not moves:
        return AdvanceVerdict(False, "rejected", "does not bear on the question", 1.0)

    novelty, echo, limit = novelty_against_history(summary, history, embedder)
    if novelty < (1.0 - limit):
        return AdvanceVerdict(
            False, "rejected",
            f"restates an earlier advance (novelty {novelty:.2f}): {(echo or '')[:80]}",
            novelty,
        )

    grounded = [r for r in evidence_refs if r in dossier_refs]
    if claimed_kind == "evidence":
        if not grounded:
            # Legitimate thought, honestly relabelled — not a rejection.
            logger.info("advance: evidence claim without dossier refs — recording as reasoning")
            return AdvanceVerdict(
                True, "reasoning",
                "claimed evidence but cited nothing in the dossier; "
                "recorded as reasoning",
                novelty, [],
            )
        return AdvanceVerdict(True, "evidence", "grounded in the dossier",
                              novelty, grounded)

    return AdvanceVerdict(True, "reasoning", "reasoning without sources, labelled",
                          novelty, grounded)
