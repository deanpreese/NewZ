"""Metrics composed from what already exists (P4 epic E3.7).

**The shortfall was never collection.** Four of TRUE_NORTH §10's six checkable
items are ratios of figures the store already holds. Counting instruments rather
than derivable quantities is what made the gap look larger than it was, and
this module is the correction:

  volume_against_development       §10 "activity, memory growth, or output volume"
  restatement_rate                 §10 "personality consistency without development"
  consequence_rate                 §10 "novelty without relevance or consequence"
  autonomy_against_world_grounding §10 "autonomy without perspective or purpose"

Each names the failure directly. Volume rising while development is flat is
§10's first item happening; a restatement rate near 1 is the second; advances
accumulating while nothing is ever settled is the third; acting a great deal
while almost nothing held comes from outside is the fourth.

**A derived metric cannot be more trustworthy than what it is derived from.**
`grade_of_derivation` takes the weakest input grade, and a test asserts the
registry agrees — so a mechanical numerator over a model-graded denominator is
model-graded, and cannot quietly carry a decision that neither input could.
That rule is the reason this module exists as code rather than as four more
queries: the composition is where a grade would otherwise be lost.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from newz.evidence.mechanical import Value

# Weakest to strongest. Not a quality ranking — a statement about what may carry
# a decision. Only `mechanical` may, so any non-mechanical input makes the
# derivation non-mechanical too (Rule 4, Rule 7).
#
# **`known-biased` sits above `mixed`, which is a judgment worth stating.** A
# known bias is characterised: R-15 says imported episodes are uniformly
# `self`, so a reader knows which way the figure leans and by roughly what.
# `mixed` has a model judgment somewhere upstream — added/revised labels applied
# at consolidation — and nothing characterises which way that leans. A named
# distortion is more tractable than an unnamed judgment, and Rule 4's concern is
# with judgments rather than with error.
GRADE_ORDER = ("model-graded", "mixed", "known-biased", "mechanical")

# Every derived metric and what it is composed from. Read by the registry test.
DERIVED_FROM = {
    "volume_against_development": ("episodes_recorded", "perspective_novelty"),
    "restatement_rate": ("perspective_novelty",),
    "consequence_rate": ("advance_acceptance", "claims_opened"),
    "autonomy_against_world_grounding": ("advances_offered", "self_grounding_share"),
}


def grade_of_derivation(inputs) -> str:
    """The weakest grade among the inputs. A ratio is only as good as its parts."""
    return min(inputs, key=lambda g: GRADE_ORDER.index(g))


def _window(conn: sqlite3.Connection, since: float):
    from newz.evidence.perspective_window import read_window

    return read_window(conn)


def volume_against_development(conn: sqlite3.Connection, *, since: float) -> Value:
    """Episodes recorded per Perspective item added or revised.

    §10's "activity, memory growth, or output volume". A rising number is the
    being doing more and holding no more for it — which is the shape of the
    failure, not a proxy for it.
    """
    try:
        episodes = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE ts >= ?", (since,)).fetchone()[0]
        w = _window(conn, since)
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")
    developed = sum(n.developed for n in w.nights)
    if not developed:
        return Value(unreadable=(
            "no Perspective item was added or revised in the window — the ratio "
            "has no denominator, and reporting the episode count alone would be "
            "the volume figure §10 warns about with nothing to divide it by"))
    return Value(round(episodes / developed, 3))


def restatement_rate(conn: sqlite3.Connection, *, since: float) -> Value:
    """1 − novelty: the share of what is held that is being restated.

    §10's "personality consistency without development". Already computed by
    the Perspective window; the derivation is only that it be looked at.
    """
    try:
        w = _window(conn, since)
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")
    if not w.nights:
        return Value(unreadable="no nightly diff has been recorded yet")
    return Value(round(w.restatement, 4))


def consequence_rate(conn: sqlite3.Connection, *, since: float) -> Value:
    """Claims settled per advance accepted.

    §10's "novelty without relevance or consequence". Advances accumulating
    while nothing is ever settled is that item, measured — and today it is
    exactly zero, which is S1-E stated as a ratio.
    """
    try:
        advances = conn.execute(
            "SELECT COUNT(*) FROM concern_advances WHERE ts >= ?", (since,)).fetchone()[0]
        settled = conn.execute(
            "SELECT COUNT(*) FROM resolutions WHERE settled_at IS NOT NULL"
            " AND settled_at >= ?", (since,)).fetchone()[0]
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")
    if not advances:
        return Value(unreadable="no advance was accepted in the window")
    return Value(round(settled / advances, 4))


def autonomy_against_world_grounding(conn: sqlite3.Connection, *, since: float) -> Value:
    """Unprompted acts per unit of world-grounded position.

    §10's "autonomy without perspective or purpose". Acting a great deal while
    almost nothing held comes from outside is that item — and it is why the
    denominator is the WORLD share rather than the count of positions: a being
    can hold a great many positions and still be talking to itself.
    """
    from newz.evidence.mechanical import self_grounding_share

    try:
        acts = conn.execute(
            "SELECT (SELECT COUNT(*) FROM concern_advances WHERE ts >= ?)"
            " + (SELECT COUNT(*) FROM works WHERE ts >= ?)", (since, since)).fetchone()[0]
    except sqlite3.OperationalError as e:
        return Value(unreadable=f"{e} — the store has not taken this migration yet")
    own = self_grounding_share(conn)
    if own.unreadable:
        return Value(unreadable=own.unreadable)
    world_share = 1.0 - own.value
    if world_share <= 0:
        return Value(unreadable=(
            "nothing held is grounded outside the being — the ratio has no "
            "denominator, and that state is itself the finding"))
    return Value(round(acts / world_share, 2))


def all_derived(conn: sqlite3.Connection, repo_root: Path, *, now: float,
                hours: float) -> dict[str, Value]:
    since = now - hours * 3600.0
    return {
        "volume_against_development": volume_against_development(conn, since=since),
        "restatement_rate": restatement_rate(conn, since=since),
        "consequence_rate": consequence_rate(conn, since=since),
        "autonomy_against_world_grounding":
            autonomy_against_world_grounding(conn, since=since),
    }
