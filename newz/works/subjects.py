"""Subjects emerge, they are not assigned (P4 epic E2.4).

**The constraint is the design.** E2.4's Done-when: *tags are computed from the
corpus and no tag vocabulary is hand-authored.* That rules out a topic list, and
it rules out asking the model — a model assigning topics is a judge, and
TRUE_NORTH §8 asks for viewpoint non-prescription, which begins with not
deciding in advance what the being is allowed to be about.

So the vocabulary **is** the corpus. A term is a tag for a piece when it occurs
in that piece and is rare across the rest — ordinary inverse document
frequency. Nothing is authored, not even a stop-list: a word common to every
piece has an IDF of zero and drops out by arithmetic rather than by someone's
judgment about which words are interesting.

**A subject is a tag more than one piece shares.** One piece about liquidity is
a piece; three are a subject, and the being was never told that liquidity was
available to care about.

**Honest at small n.** With few pieces almost everything is distinctive and the
tags mean very little. `Corpus.stable` says so rather than letting a number
stand where a measurement should be (INV-044), and callers are expected to
print the caveat rather than the tags.
"""

from __future__ import annotations

import math
import re
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass, field

# Below this the corpus cannot say what is distinctive: with three pieces a
# term in one of them is "rare" trivially. Not a threshold on quality — a
# statement about when the arithmetic starts to mean anything.
MIN_PIECES_FOR_STABLE_TAGS = 8
TAGS_PER_PIECE = 6
MIN_WORD_LEN = 4
# A term in almost every piece describes the writer, not the piece.
MAX_DOCUMENT_SHARE = 0.6

_WORD = re.compile(r"[a-z][a-z\-']{%d,}" % (MIN_WORD_LEN - 2))


@dataclass
class Corpus:
    pieces: int = 0
    tags: dict[int, list[tuple[str, float]]] = field(default_factory=dict)

    @property
    def stable(self) -> bool:
        return self.pieces >= MIN_PIECES_FOR_STABLE_TAGS

    @property
    def caveat(self) -> str:
        if self.stable:
            return ""
        return (f"{self.pieces} pieces — below {MIN_PIECES_FOR_STABLE_TAGS}, "
                "almost every term is distinctive and these tags mean little")

    def subjects(self, *, min_pieces: int = 2) -> list[tuple[str, int]]:
        """Tags more than one piece shares — what the work turned out to be about."""
        shared: Counter = Counter()
        for tags in self.tags.values():
            for tag, _ in tags:
                shared[tag] += 1
        return [(t, n) for t, n in shared.most_common() if n >= min_pieces]


def _terms(text: str) -> Counter:
    return Counter(_WORD.findall((text or "").lower()))


def compute(conn: sqlite3.Connection, *, per_piece: int = TAGS_PER_PIECE) -> Corpus:
    """Distinctive terms per piece, over the works corpus as it stands."""
    rows = conn.execute(
        "SELECT id, title, body FROM works ORDER BY id").fetchall()
    if not rows:
        return Corpus()

    counts = {r["id"]: _terms(f"{r['title']} {r['body']}") for r in rows}
    n = len(rows)
    doc_freq: Counter = Counter()
    for c in counts.values():
        doc_freq.update(c.keys())

    out: dict[int, list[tuple[str, float]]] = {}
    for wid, c in counts.items():
        total = sum(c.values()) or 1
        scored = []
        for term, k in c.items():
            df = doc_freq[term]
            if df / n > MAX_DOCUMENT_SHARE:
                continue                      # describes the writer, not the piece
            idf = math.log(n / df) if df else 0.0
            if idf <= 0:
                continue                      # in every piece: zero by arithmetic
            scored.append((term, (k / total) * idf))
        scored.sort(key=lambda kv: (-kv[1], kv[0]))
        out[wid] = scored[:per_piece]
    return Corpus(pieces=n, tags=out)


def recompute(conn: sqlite3.Connection, *, per_piece: int = TAGS_PER_PIECE) -> Corpus:
    """Replace every tag. Tags are a property of the corpus, not of the piece."""
    corpus = compute(conn, per_piece=per_piece)
    now = time.time()
    conn.execute("DELETE FROM work_tags")
    for wid, tags in corpus.tags.items():
        for tag, weight in tags:
            conn.execute(
                "INSERT INTO work_tags (computed_at, work_id, tag, weight)"
                " VALUES (?,?,?,?)", (now, wid, tag, round(weight, 6)))
    conn.commit()
    return corpus
