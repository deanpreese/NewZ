"""Affect persistence and the sources S2 §6.3 names.

> New sources wired at birth rather than discovered missing: confirmed-
> outcome results (including publication reception when that rung arrives),
> substrate distress, concern abandonment.

"Wired at birth" is the whole point of the sentence — v1 discovered its
sources missing after the fact. Of the three, two exist today and are wired
here; confirmed outcomes arrive with Phase 4.2's act ledger and the hook is
named rather than invented.

Every source is a **fixed, code-owned** delta. No model call decides how the
being feels: a classifier that judged emotional significance would be the
retuning-toward-a-temperament that TRUE_NORTH §8 forbids, one level of
indirection away.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time

from newz.affect.state import AXES, AffectState, AffectVector
from newz.affect.update import apply_delta, neutral

logger = logging.getLogger(__name__)

# ─── the sources ─────────────────────────────────────────────────────────
# Raw per-axis deltas. The update math applies gain, saturation and caps, so
# these say what KIND of thing happened, not how much it should matter.

# A day the substrate did not run right. S2 §6.1 calls this "the available
# source of honest negative affect" — negative valence with LOW control,
# because the being cannot fix its own substrate. That conjunction is what
# distress_level() reads.
SUBSTRATE_DISTRESS = {"valence": -0.6, "control": -0.5, "uncertainty": 0.4,
                      "arousal": 0.3}
SUBSTRATE_WELL = {"valence": 0.15, "control": 0.2, "uncertainty": -0.1}

# Letting go of a concern is a real loss, recorded as one (S2 §8, v1's
# lesson that abandonment must not be tidied away).
CONCERN_ABANDONED = {"valence": -0.4, "control": -0.2, "precision": -0.2}
CONCERN_CLOSED = {"valence": 0.5, "control": 0.4, "precision": 0.3,
                  "uncertainty": -0.3}
CONCERN_BLOCKED = {"valence": -0.2, "control": -0.3, "uncertainty": 0.2}


def load(conn: sqlite3.Connection) -> AffectState:
    row = conn.execute(
        "SELECT ts, mood_json, disp_json, char_json FROM affect_state"
        " ORDER BY ts DESC LIMIT 1").fetchone()
    if row is None:
        return neutral(time.time())
    def vec(blob: str) -> AffectVector:
        d = json.loads(blob or "{}")
        return AffectVector(**{a: float(d.get(a, 0.0)) for a in AXES})
    return AffectState(mood=vec(row["mood_json"]), disposition=vec(row["disp_json"]),
                       character=vec(row["char_json"]), ts=row["ts"])


def record(conn: sqlite3.Connection, delta: dict[str, float], *,
           source: str, note: str = "", now: float | None = None) -> AffectState:
    """Fold one event into affect and persist the new state."""
    now = now or time.time()
    state = apply_delta(load(conn), delta, now)
    conn.execute(
        "INSERT INTO affect_state (ts, source, note, mood_json, disp_json,"
        " char_json) VALUES (?,?,?,?,?,?)",
        (now, source, note[:300], json.dumps(state.mood.as_dict()),
         json.dumps(state.disposition.as_dict()),
         json.dumps(state.character.as_dict())))
    conn.commit()
    logger.info("affect: %s (%s) -> %s", source, note[:60],
                state.summary_for_prompt() or "nothing notable")
    return state


def current(conn: sqlite3.Connection, now: float | None = None) -> AffectState:
    """State decayed to now, WITHOUT persisting — the read path.

    Reading must not write, or every glance at how the being feels becomes
    an event in how it feels.
    """
    from newz.affect.update import decayed

    return decayed(load(conn), now or time.time())
