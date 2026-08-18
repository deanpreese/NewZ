"""Decay, saturating gains, per-tick caps — the update math.

Ported from v1 `ngbeing/affect/update.py` with review. The constants below
were calibrated in v1 against live measurement and carry their reasoning;
none of it is cheaper to rediscover, and re-deriving it would mean
re-tuning, which TRUE_NORTH §8 forbids doing toward any temperament.

Three properties matter and each has a test:

- **Decay** gives the timescale names temporal meaning rather than being
  distinguished only by gain. Mood is minutes; character is a week.
- **Saturation** means an axis already at its limit cannot be pushed
  further. A bad day cannot drive valence below the floor no matter how many
  bad things happen, which is the circuit breaker against an
  affect → behaviour → percept → affect spiral.
- **Per-tick caps** bound how far any single event can move each timescale,
  so one event cannot rewrite character.
"""

from __future__ import annotations

import math

from newz.affect.state import AXES, TIMESCALES, AffectState, AffectVector

# How much of a raw delta each timescale absorbs.
GAIN: dict[str, float] = {"mood": 1.00, "disposition": 0.30, "character": 0.05}

# Per-axis movement cap per event, per timescale. One event cannot rewrite
# who the being is.
CAP: dict[str, float] = {"mood": 0.40, "disposition": 0.15, "character": 0.05}

# Exponential decay half-lives. At dt = half-life each axis is multiplied by
# 0.5 before new deltas land.
HALF_LIFE_S: dict[str, float] = {
    "mood": 600.0,             # 10 minutes
    "disposition": 14_400.0,   # 4 hours
    "character": 604_800.0,    # 7 days
}

# One-shot decay is capped: after a long restart the being should return to
# neutral, not compute exp() of a fortnight. Mood at a 10-minute half-life is
# already ~1e-43 at 24h, so the cap costs nothing real.
MAX_DECAY_GAP_S: float = 86_400.0


def decayed(state: AffectState, now: float) -> AffectState:
    """Apply time decay from `state.ts` to `now`. Neutral is the attractor."""
    # Explicit rather than `state.ts or now`: 0.0 is falsy, so that form
    # silently skipped decay for any state stamped at epoch 0. Harmless
    # in production (ts is always a real clock) and wrong everywhere else.
    base = state.ts if state.ts > 0 else now
    gap = min(max(0.0, now - base), MAX_DECAY_GAP_S)
    if gap <= 0:
        return state
    out = state
    for ts in TIMESCALES:
        factor = math.pow(0.5, gap / HALF_LIFE_S[ts])
        if factor < 1.0 - 1e-9:
            out = out.with_vector(ts, out.vector(ts).scaled(factor))
    return AffectState(mood=out.mood, disposition=out.disposition,
                       character=out.character, ts=now)


def apply_delta(state: AffectState, delta: dict[str, float],
                now: float) -> AffectState:
    """Decay to `now`, then land a saturated, gained, capped delta.

    `delta` is per-axis and raw — the caller says what happened, not how
    much it should move anything. Scaling is this module's job so no caller
    can turn its own event into a temperament.
    """
    out = decayed(state, now)
    clean = {a: float(d) for a, d in delta.items() if a in AXES and d}
    if not clean:
        return out

    for ts in TIMESCALES:
        v = out.vector(ts)
        current = v.as_dict()
        scaled: dict[str, float] = {}
        for axis, raw in clean.items():
            # Saturation against THIS timescale's own position: the closer an
            # axis is to its limit, the less any event moves it.
            sat = max(0.0, 1.0 - abs(current[axis]))
            d = raw * sat * GAIN[ts]
            cap = CAP[ts]
            scaled[axis] = max(-cap, min(cap, d))
        out = out.with_vector(ts, v.with_delta(scaled))
    return AffectState(mood=out.mood, disposition=out.disposition,
                       character=out.character, ts=now)


def neutral(now: float = 0.0) -> AffectState:
    return AffectState(mood=AffectVector(), disposition=AffectVector(),
                       character=AffectVector(), ts=now)
