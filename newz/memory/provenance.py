"""What shaped this view (S2 §13) — the traceability instrument.

TRUE_NORTH §8 made structural: every held position carries its evidence
refs, so a query can answer *"what shaped this view"* — sources, episodes,
people — on demand. S2 names this as the instrument v1's own invariant
deferred for lack of; it is built here because the data has been sitting
ready since Phase 1.3 and only the query was missing.

Two things it must be able to say, because §13 asks for both:

- **Diversity.** Which outlets, which people, and how concentrated. v1's end
  state was 56% of all reading from two outlets, and that is a material
  viewpoint-shaping influence rather than a logistics detail.
- **Operator influence, traceable like everything else.** Canon sources and
  operator conversation are provenance-tagged the same way, so the being can
  see — and say — where its operator shaped a view rather than the world.

This reads; it never writes. An instrument that can alter what it measures
is not an instrument.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Influence:
    """What shaped one held position."""

    item_id: int | None
    text: str
    section: str
    confidence: float
    # provenance string -> how many supporting episodes carry it
    by_provenance: Counter = field(default_factory=Counter)
    episodes: list[dict] = field(default_factory=list)
    unresolved_refs: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.by_provenance.values())

    def share(self, prefix: str) -> float:
        """Fraction of supporting episodes whose provenance starts with
        `prefix` — 'world:', 'human:', or 'self'."""
        if not self.total:
            return 0.0
        n = sum(v for k, v in self.by_provenance.items() if k.startswith(prefix))
        return n / self.total

    @property
    def concentration(self) -> tuple[str, float] | None:
        """The single largest source and its share — v1's 56%-from-two-outlets
        anti-pattern, made visible per position rather than per corpus."""
        if not self.total:
            return None
        source, n = self.by_provenance.most_common(1)[0]
        return source, n / self.total

    def render(self) -> str:
        lines = [f"{self.text}",
                 f"  section: {self.section}   confidence: {self.confidence:.2f}"]
        if not self.total:
            lines.append("  shaped by: nothing traceable — this position "
                         "carries no resolvable evidence")
            if self.unresolved_refs:
                lines.append(f"  refs that resolve to no episode: "
                             f"{', '.join(self.unresolved_refs[:8])}")
            return "\n".join(lines)

        lines.append(f"  shaped by {self.total} episode(s):")
        for prov, n in self.by_provenance.most_common():
            lines.append(f"    {n:>3}  {prov}")
        world, human, own = (self.share("world:"), self.share("human:"),
                             self.share("self"))
        lines.append(f"  the world {world:.0%} · people {human:.0%} · myself {own:.0%}")
        top, top_share = self.concentration
        if top_share >= 0.5:
            lines.append(f"  ** {top_share:.0%} of this view comes from one "
                         f"source: {top}")
        if self.unresolved_refs:
            lines.append(f"  {len(self.unresolved_refs)} ref(s) resolve to no "
                         f"episode: {', '.join(self.unresolved_refs[:8])}")
        return "\n".join(lines)


def what_shaped(conn: sqlite3.Connection, item_id: int) -> Influence | None:
    """Trace one Perspective item back to the episodes that support it."""
    row = conn.execute(
        "SELECT id, text, section, confidence, evidence_json"
        " FROM perspective_items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        return None
    return _trace(conn, row)


def what_shaped_version(conn: sqlite3.Connection,
                        version: int | None = None) -> list[Influence]:
    """Every held position in a Perspective version, newest by default."""
    if version is None:
        got = conn.execute("SELECT MAX(version) FROM perspective_items").fetchone()
        version = got[0] if got else None
    if version is None:
        return []
    rows = conn.execute(
        "SELECT id, text, section, confidence, evidence_json"
        " FROM perspective_items WHERE version=? AND status<>'released'"
        " ORDER BY section, confidence DESC", (version,)).fetchall()
    return [_trace(conn, r) for r in rows]


def _trace(conn: sqlite3.Connection, row: sqlite3.Row) -> Influence:
    inf = Influence(item_id=row["id"], text=row["text"], section=row["section"],
                    confidence=row["confidence"])
    refs = json.loads(row["evidence_json"] or "[]")
    ids = [int(r) for r in refs if str(r).lstrip("-").isdigit()]
    inf.unresolved_refs = [str(r) for r in refs if not str(r).lstrip("-").isdigit()]
    if not ids:
        return inf

    placeholders = ",".join("?" * len(ids))
    found = conn.execute(
        f"SELECT id, ts, kind, provenance, summary FROM episodes"
        f" WHERE id IN ({placeholders})", ids).fetchall()
    seen = set()
    for e in found:
        seen.add(e["id"])
        inf.by_provenance[e["provenance"]] += 1
        inf.episodes.append({"id": e["id"], "ts": e["ts"], "kind": e["kind"],
                             "provenance": e["provenance"],
                             "summary": e["summary"]})
    # A ref naming an episode that is not there is a real finding, not a
    # rounding error: it means the position cites something the store cannot
    # produce. Reported rather than silently dropped.
    inf.unresolved_refs += [str(i) for i in ids if i not in seen]
    return inf


def corpus_concentration(conn: sqlite3.Connection) -> Counter:
    """Provenance mix across everything currently held — the §13 diversity
    read at the level v1 measured it (56% from two outlets)."""
    total: Counter = Counter()
    for inf in what_shaped_version(conn):
        total.update(inf.by_provenance)
    return total
