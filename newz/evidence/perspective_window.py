"""Evidence 1-E (P2 Phase 1) — the Perspective diff window, read directly.

P2 asks four things of the window, "all four off the diff artifact (direct
reads)": novelty vs restatement, contradictions opened and closed, the
compression ratio, and evidence coverage. This module computes them from
`perspective.diff_json` and `perspective_items` and consults nothing else.

Three things about the method, because the rate is easy to misread.

**Novelty is pooled across the window, never averaged over nights.** Its
denominator is everything held after a night — added + revised + carried — so
a night that carries 200 positions and a night that carries 12 do not deserve
equal weight in a window figure. Averaging the per-night rates gives the
sparse night the same vote as the full one, which is how a window can appear
to develop on the strength of its emptiest evening.

**The rate moves when the document shrinks, with no change in development.**
Compression is a stated goal of sleep (S2 §5 step 5) and it removes carried
items — the denominator. Between v1 and v9 this Perspective went 2,758 → 2,071
tokens. A novelty rate rising across a compressing window is consistent with
development and equally consistent with the same handful of new positions
landing in a steadily smaller document, so the counts are reported beside the
rate and a trend in the rate alone is not offered.

**The first sleep is not a night.** It had no prior Perspective to confront,
writes a differently-shaped diff, and carries no novelty rate at all. It is
excluded, and `Window.excluded` says so by version and reason — an instrument
that quietly drops a row is worse than one that never had it.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field

# What a nightly diff must carry to be a night at all. The first sleep's diff
# has `first_sleep`/`observations` instead and is excluded by this key.
NIGHTLY_MARKER = "carried"

# Above this, the stored rate and the recomputed one disagree enough to mean
# the artifact was rewritten after the fact. 0.001 is the rounding in
# `Diff.as_dict`; anything past a few of those is not rounding.
NOVELTY_DRIFT_TOLERANCE = 0.005


@dataclass
class Night:
    """One nightly sleep, as its own diff recorded it."""

    version: int
    ts: float
    added: int = 0
    revised: int = 0
    merged: int = 0
    released: int = 0
    disputed: int = 0
    carried: int = 0
    contradictions_opened: int = 0
    contradictions_closed: int = 0
    tokens: int = 0
    items: int = 0
    grounded: int = 0
    stored_novelty: float | None = None

    @property
    def developed(self) -> int:
        return self.added + self.revised

    @property
    def weighed(self) -> int:
        """Everything held after the night — the share `novelty` is a share of."""
        return self.developed + self.carried

    @property
    def novelty(self) -> float:
        return self.developed / self.weighed if self.weighed else 0.0

    @property
    def coverage(self) -> float:
        """Share of held items carrying at least one evidence reference.

        Coverage, not grounding: this counts whether an item cites anything,
        never whether what it cites supports it, and never whether the cited
        episodes are the being's own echo. That separation is INV-026's and
        INV-033's work — `tools/what_shaped.py` reads the provenance mix.
        """
        return self.grounded / self.items if self.items else 0.0

    @property
    def novelty_drift(self) -> float | None:
        """Recomputed rate minus the one the artifact stored, or None."""
        if self.stored_novelty is None:
            return None
        return self.novelty - self.stored_novelty


@dataclass
class Window:
    nights: list[Night] = field(default_factory=list)
    excluded: list[tuple[int, str]] = field(default_factory=list)

    @property
    def novelty(self) -> float:
        """Pooled over the window: total developed / total held."""
        weighed = sum(n.weighed for n in self.nights)
        return sum(n.developed for n in self.nights) / weighed if weighed else 0.0

    @property
    def restatement(self) -> float:
        return 1.0 - self.novelty

    @property
    def contradictions_opened(self) -> int:
        return sum(n.contradictions_opened for n in self.nights)

    @property
    def contradictions_closed(self) -> int:
        return sum(n.contradictions_closed for n in self.nights)

    @property
    def compression(self) -> float | None:
        """Last night's token count over the first's. <1 is compression."""
        if len(self.nights) < 2 or not self.nights[0].tokens:
            return None
        return self.nights[-1].tokens / self.nights[0].tokens

    @property
    def item_compression(self) -> float | None:
        """The same ratio in held items, which is what the rate's denominator is."""
        if len(self.nights) < 2 or not self.nights[0].items:
            return None
        return self.nights[-1].items / self.nights[0].items

    @property
    def coverage(self) -> float:
        """Coverage as it stands now — the newest night's."""
        return self.nights[-1].coverage if self.nights else 0.0

    @property
    def drifted(self) -> list[Night]:
        """Nights whose stored rate no longer matches their own counts."""
        return [n for n in self.nights
                if n.novelty_drift is not None
                and abs(n.novelty_drift) > NOVELTY_DRIFT_TOLERANCE]

    def meets_floor(self, nights: int = 7) -> bool:
        """P2's Evidence 1-E floor: diffs over ≥7 nights."""
        return len(self.nights) >= nights


def read_window(conn: sqlite3.Connection, *, since: float | None = None) -> Window:
    """Read recorded Perspective versions. Plain SQL — no model.

    `since` bounds the window to nights at or after a timestamp. It defaults to
    None — every night — because Evidence 1-E asks about the whole history and
    that is what this module was built for.

    **It exists because a caller was silently getting the whole history.**
    E3.7's derivations passed a `since` into a helper that dropped it, so
    `volume_against_development` divided episodes over seven days by
    development over all time, and `restatement_rate` was an all-time figure
    filed nightly under a 168-hour window. A window argument nothing applies is
    worse than none: the reading carries the window in its own row.
    """
    items: dict[int, tuple[int, int]] = {}
    for version, total, grounded in conn.execute(
        "SELECT version, COUNT(*), SUM(CASE WHEN evidence_json IS NOT NULL"
        "   AND evidence_json NOT IN ('', '[]', 'null') THEN 1 ELSE 0 END)"
        " FROM perspective_items GROUP BY version"
    ):
        items[version] = (total, grounded or 0)

    window = Window()
    for version, ts, diff_json, tokens in conn.execute(
        "SELECT version, ts, diff_json, token_count FROM perspective"
        " WHERE ts >= ? ORDER BY version", (since if since is not None else 0.0,)
    ):
        try:
            diff = json.loads(diff_json) if diff_json else {}
        except json.JSONDecodeError:
            window.excluded.append((version, "diff_json is not readable JSON"))
            continue
        if not isinstance(diff, dict) or NIGHTLY_MARKER not in diff:
            window.excluded.append(
                (version, "no prior Perspective to confront — first sleep "
                          "writes observations, not a nightly diff")
            )
            continue

        total, grounded = items.get(version, (0, 0))
        listlen = lambda key: len(diff.get(key) or [])  # noqa: E731
        window.nights.append(Night(
            version=version,
            ts=ts,
            added=listlen("added"),
            revised=listlen("revised"),
            merged=listlen("merged"),
            released=listlen("released"),
            disputed=listlen("disputed"),
            carried=int(diff.get("carried") or 0),
            contradictions_opened=int(diff.get("contradictions_opened") or 0),
            contradictions_closed=int(diff.get("contradictions_closed") or 0),
            tokens=int(tokens or 0),
            items=total,
            grounded=grounded,
            stored_novelty=diff.get("novelty_rate"),
        ))
    return window
