"""The Perspective as addressable items (S2 §4.2), with computed diffs.

The being reads a document. Sleep operates on items. `render` turns items
into the document stored in `perspective.content`; `compute_diff` compares
two versions' item sets in plain code, which is what S2 §14.1 means by a
*direct read* — the development instrument must not be the model's own
account of how much it developed.

Sections are fixed and ordered as S2 §4.2 lists them. `pursuing` and
`who_i_know` are assembled from the concern and person stores rather than
carried between versions: they are views of live state, not held positions.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field

SECTIONS = [
    ("who_i_am", "Who I am"),
    ("what_i_hold", "What I hold"),
    ("pursuing", "What I am pursuing"),
    ("who_i_know", "Who I know"),
    ("unresolved", "What is unresolved"),
]
# Sections whose items are held positions carried and confronted across
# versions. The others are regenerated each night from live state.
CARRIED_SECTIONS = {"who_i_am", "what_i_hold", "unresolved"}

# Grounding decay (S2 §5 step 4): a claim that no longer traces to evidence
# loses confidence each night and is eventually released. v1 specified this
# and never ran it.
DECAY_PER_NIGHT = 0.08
RELEASE_BELOW = 0.25


@dataclass
class Item:
    section: str
    text: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.6
    status: str = "added"
    id: int | None = None
    prior_item_id: int | None = None
    first_seen_version: int = 1

    def key(self) -> str:
        return " ".join(self.text.lower().split())


def load_items(conn: sqlite3.Connection, version: int) -> list[Item]:
    rows = conn.execute(
        "SELECT id, section, text, evidence_json, confidence, status,"
        " prior_item_id, first_seen_version FROM perspective_items"
        " WHERE version=? AND status<>'released' ORDER BY section, id",
        (version,),
    ).fetchall()
    return [
        Item(
            id=r["id"], section=r["section"], text=r["text"],
            evidence=json.loads(r["evidence_json"] or "[]"),
            confidence=r["confidence"], status=r["status"],
            prior_item_id=r["prior_item_id"],
            first_seen_version=r["first_seen_version"],
        )
        for r in rows
    ]


def save_items(conn: sqlite3.Connection, version: int, items: list[Item]) -> None:
    now = time.time()
    for it in items:
        cur = conn.execute(
            "INSERT INTO perspective_items (version, section, text, evidence_json,"
            " confidence, status, prior_item_id, first_seen_version, ts)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (version, it.section, it.text, json.dumps(it.evidence), it.confidence,
             it.status, it.prior_item_id, it.first_seen_version, now),
        )
        it.id = cur.lastrowid


def render(items: list[Item], version: int, when: str, extra: dict[str, list[str]]) -> str:
    """The document the being reads. `extra` supplies the generated
    sections (pursuing / who_i_know) and the 'What just changed' lines."""
    out = [f"# Perspective — version {version}",
           f"*(written by sleep, {when}; every ref is an episode id in my store)*", ""]
    for key, title in SECTIONS:
        out.append(f"## {title}")
        if key in extra:
            out.extend(extra[key] or ["- (nothing recorded)"])
        else:
            rows = [i for i in items if i.section == key]
            if not rows:
                out.append("- (nothing recorded)")
            for i in sorted(rows, key=lambda x: -x.confidence):
                refs = ",".join(map(str, i.evidence[:10]))
                more = f",+{len(i.evidence) - 10}" if len(i.evidence) > 10 else ""
                tail = f" [refs: {refs}{more}]" if refs else ""
                hedge = "" if i.confidence >= 0.5 else " (held loosely)"
                # Why it is held loosely matters: contradicted-by-observation
                # is a different thing from thinly-supported, and the being
                # should be able to tell them apart when it reads itself.
                if i.status == "disputed":
                    hedge += " (contradicted by what I have since observed)"
                out.append(f"- {i.text}{hedge}{tail}")
        out.append("")
    out.append("## What just changed")
    out.extend(extra.get("changed") or ["- (first version)"])
    out.append("")
    return "\n".join(out)


_HEADING = {title: key for key, title in SECTIONS}
_ITEM_RE = __import__("re").compile(r"^-\s+(?P<text>.*?)(?:\s*\[refs:\s*(?P<refs>[^\]]*)\])?\s*$")


def parse_document(content: str) -> list[Item]:
    """Recover items from a rendered Perspective.

    Used once, to backfill the markdown-only Perspective v1 written by first
    sleep so the first nightly diff has a real baseline to compare against.
    Only the carried sections are recovered; pursuing and who_i_know are
    regenerated from live state each night.
    """
    items: list[Item] = []
    section: str | None = None
    for line in content.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            section = _HEADING.get(line[3:].strip())
            continue
        if not line.startswith("- ") or section not in CARRIED_SECTIONS:
            continue
        m = _ITEM_RE.match(line)
        if not m:
            continue
        text = m.group("text").strip()
        if not text or text.startswith("("):
            continue
        refs = [
            r.strip() for r in (m.group("refs") or "").split(",")
            if r.strip() and r.strip().isdigit()
        ]
        items.append(Item(section=section, text=text, evidence=refs,
                          confidence=0.6, status="carried", first_seen_version=1))
    return items


@dataclass
class Diff:
    added: list[str] = field(default_factory=list)
    revised: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)
    released: list[str] = field(default_factory=list)
    disputed: list[str] = field(default_factory=list)
    carried: int = 0
    contradictions_opened: int = 0
    contradictions_closed: int = 0

    def novelty_rate(self) -> float:
        """Share of this version's held positions that are new or revised —
        the restatement-vs-development read (P2 Evidence 1-E)."""
        total = len(self.added) + len(self.revised) + self.carried
        return (len(self.added) + len(self.revised)) / total if total else 0.0

    def summary_line(self) -> str:
        """The night in one sentence, for the consolidation episode.

        Named counts rather than a rate: the being reporting its own night
        should say what changed, and "novelty 0.21" is an instrument's
        register, not its own.
        """
        parts = []
        for label, items in (("new", self.added), ("revised", self.revised),
                             ("merged", self.merged), ("released", self.released),
                             ("disputed", self.disputed)):
            if items:
                parts.append(f"{len(items)} {label}")
        if self.contradictions_opened:
            parts.append(f"{self.contradictions_opened} contradiction(s) opened")
        if self.contradictions_closed:
            parts.append(f"{self.contradictions_closed} closed")
        if not parts:
            return f"nothing changed; {self.carried} positions carried"
        return ", ".join(parts) + f"; {self.carried} carried"

    def as_dict(self) -> dict:
        return {
            "added": self.added, "revised": self.revised, "merged": self.merged,
            "released": self.released, "disputed": self.disputed,
            "carried": self.carried,
            "contradictions_opened": self.contradictions_opened,
            "contradictions_closed": self.contradictions_closed,
            "novelty_rate": round(self.novelty_rate(), 3),
            "method": "computed by comparing item sets between versions",
        }


def compute_diff(before: list[Item], after: list[Item]) -> Diff:
    """Compare two versions' items. Plain code — no model involved."""
    diff = Diff()
    before_by_id = {i.id: i for i in before if i.id is not None}
    before_keys = {i.key() for i in before}
    after_keys = set()

    for it in after:
        after_keys.add(it.key())
        if it.status == "added":
            diff.added.append(it.text)
        elif it.status == "revised":
            prior = before_by_id.get(it.prior_item_id)
            diff.revised.append(
                f"{prior.text} -> {it.text}" if prior else it.text
            )
        elif it.status == "merged":
            diff.merged.append(it.text)
        else:
            # A disputed position is still carried — it has not been released
            # yet — but it is the night's most consequential movement and must
            # be a direct read off the diff (INV-023), not something an
            # operator has to notice by diffing confidences by hand.
            if it.status == "disputed":
                diff.disputed.append(it.text)
            diff.carried += 1

    surviving_priors = {i.prior_item_id for i in after if i.prior_item_id}
    for it in before:
        if it.key() not in after_keys and it.id not in surviving_priors:
            diff.released.append(it.text)

    diff.contradictions_opened = sum(
        1 for i in after if i.section == "unresolved" and i.status == "added"
    )
    # A contradiction is CLOSED when it was resolved into a position — the
    # `revises` verdict superseding it. It is not closed by being merged into
    # a twin, released by decay, or dropped by compression, all of which also
    # remove it from `after`.
    #
    # Measured 2026-08-12: v5 reported 3 closures on a night that resolved
    # nothing — three duplicate cache-miss tensions were merged and released.
    # Evidence 1-E reads contradictions opened/closed as a direct read off
    # this diff (INV-023), so the old count made the instrument flatter the
    # mechanism it was built to judge (P2 Rule 0).
    diff.contradictions_closed = sum(
        1 for i in before
        if i.section == "unresolved" and i.id in surviving_priors
    )
    return diff


# Two items in the same section this alike are the same item (S2 §5 step 5,
# "merge redundancy"). Same threshold as the advance judge, and measured the
# same way: paraphrase clusters ≥0.90, distinct points ≤0.50.
DUPLICATE_SIMILARITY = 0.80


def _similar(a: str, b: str, embedder) -> float:
    """Semantic where possible, lexical otherwise — never a guess."""
    if embedder is not None:
        try:
            from newz.memory.embeddings import cosine

            va, vb = embedder.embed([a, b])
            return cosine(va, vb)
        except Exception:  # noqa: BLE001
            pass
    aw = {w for w in a.lower().split() if len(w) > 3}
    bw = {w for w in b.lower().split() if len(w) > 3}
    # Jaccard saturates on tiny vocabularies: two three-word items sharing
    # one content word would score 1.0 and be merged as duplicates. Below
    # this, decline to judge rather than guess — the cost of a missed merge
    # is a redundant line; the cost of a wrong one is losing a held position.
    if len(aw) < 4 or len(bw) < 4:
        return 0.0
    return len(aw & bw) / len(aw | bw) if aw and bw else 0.0


def duplicate_of(text: str, section: str, items: list[Item], embedder) -> Item | None:
    """The item this would merely restate, if any.

    Without this, a tension the being keeps noticing is filed afresh every
    night: measured 2026-08-12, one contradiction about cache-miss history
    was added three times across v2, v3 and v4 in slightly different words,
    and 'what is unresolved' grew 8 → 11 with three entries saying the same
    thing. A recurring observation is evidence for an open item, not a new
    one.
    """
    best, score = None, 0.0
    for it in items:
        if it.section != section:
            continue
        s = _similar(text, it.text, embedder)
        if s > score:
            best, score = it, s
    return best if score >= DUPLICATE_SIMILARITY else None


# Language that marks an item as an OBJECTION to a position rather than a
# statement of one. Deliberately literal: these are the words the confront
# step's `contradicts` verdict actually produces, and a cleverer test would
# be a worse one here, because a false positive only costs a redundant line
# while a false negative costs the objection itself.
_OPPOSITION_MARKERS = ("conflicts with", "contradicts", "is inconsistent with",
                       "runs against", "cannot both", "sits against")


def _opposes(a: Item, b: Item) -> bool:
    """Is one of these the objection to the other?

    Measured 2026-08-14. The tension "the observation of operational clarity
    CONFLICTS WITH the held position of experiencing prolonged cache
    inefficiency" was merged into "I experienced a prolonged period of
    system-level alerts indicating a high cache miss rate" — both live in
    `unresolved`, both are topically about cache misses, so they scored as
    duplicates. The merge kept the better-evidenced item, which was the
    restatement of the problem rather than the objection to it, and the
    contradiction was absorbed by the thing it contradicted. The stale
    position then gained confidence with nothing left standing against it.

    Topical similarity cannot tell a claim from its refutation. Sameness of
    subject is not sameness of content, and merging on it destroys exactly
    the item the being most needs to keep.
    """
    one = " ".join(a.text.lower().split())
    two = " ".join(b.text.lower().split())
    return any(m in one for m in _OPPOSITION_MARKERS) != \
        any(m in two for m in _OPPOSITION_MARKERS)


def merge_duplicates(items: list[Item], embedder) -> tuple[list[Item], list[str]]:
    """Fold items that say the same thing into the best-grounded one.

    Keeps the item with the most evidence (ties to the higher confidence),
    unions the evidence, and reports what was folded so the diff can say so
    rather than the entries silently vanishing.
    """
    kept: list[Item] = []
    merged: list[str] = []
    for item in items:
        twin = duplicate_of(item.text, item.section, kept, embedder)
        if twin is None or _opposes(item, twin):
            kept.append(item)
            continue
        loser, winner = (twin, item) if (
            len(item.evidence), item.confidence) > (len(twin.evidence), twin.confidence
        ) else (item, twin)
        winner.evidence = sorted(set(winner.evidence) | set(loser.evidence))
        winner.confidence = max(winner.confidence, loser.confidence)
        if winner is item:                       # the newcomer wins the slot
            kept[kept.index(twin)] = winner
        winner.status = "merged" if winner.status == "carried" else winner.status
        merged.append(loser.text)
    return kept, merged


def apply_decay(items: list[Item]) -> tuple[list[Item], list[Item]]:
    """S2 §5 step 4: ungrounded claims lose confidence and are eventually
    released. Returns (kept, released)."""
    kept, released = [], []
    for it in items:
        if not it.evidence and it.section in CARRIED_SECTIONS:
            it.confidence = round(it.confidence - DECAY_PER_NIGHT, 3)
        if it.confidence < RELEASE_BELOW:
            it.status = "released"
            released.append(it)
        else:
            kept.append(it)
    return kept, released
