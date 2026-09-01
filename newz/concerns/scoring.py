"""Which concern gets attention — code decides (S2 §1.1, ported from v1).

Ported with review from `ngbeing/concerns/select.py`. Every constant below
was paid for in production and the reasons are kept, because a later reader
tempted to "simplify" one of them needs to know what it cost:

  staleness   keyed on when the concern last MOVED, not when it was last
              thought about — otherwise circling something without progress
              keeps it looking fresh.
  stall drag  multiplicative, never subtractive: a discount is monotone and
              always positive, so two badly-stalled concerns are ordered by
              merit rather than by how far they overshot zero.
  blocked drag  because blocking used to cost NOTHING. A blocked verdict
              touches neither last_advanced_at nor stall_count, so staleness
              grew while everything else stayed put: being unable to answer
              made a concern MORE attractive next time, and blocked was 79%
              of all v1 setbacks. Gentler than stall drag, because being
              blocked is a correct report about a gap, not the being circling.
  cooldown    a floor, not a preference: no amount of salience makes it right
              to re-ask a question answered twenty minutes ago. **It used to be
              bypassed when everything was cooling, "so the being is never left
              with nothing", and that bypass emptied the concern pool on
              2026-08-31.** It can only fire when every open concern is inside
              its six hours, which is only ever true when the pool is small —
              so it did nothing while the pool was healthy and fired every
              cycle once it was not. Measured: concern 116 took 330 hours to
              accumulate its five stalls and concern 144, opened the morning
              the pool ran dry, took 8.3. One setback per 65 hours became one
              per 1.5, the pool went to zero, and deliberation stopped.

              The reasoning was right when idleness was the only alternative.
              It is not any more: `_explore` was built 2026-08-15 for exactly
              this state and its own docstring says nothing to work with "is
              the strongest reason to go and find some". Returning None here
              routes there, books no attempt and charges no setback. This
              function's own docstring already said it — "a being with nothing
              to pursue should say so rather than manufacture a pursuit".

Review change from v1: affect fit is accepted as an optional scalar rather
than an AffectState object — affect machinery lands later (S2 §6.3), and the
scorer should not wait for it.
"""

from __future__ import annotations

from dataclasses import dataclass

from newz.concerns.model import Concern

W_STALENESS = 0.40
W_SALIENCE = 0.35
W_AFFECT_FIT = 0.25
STALL_DRAG = 0.30
BLOCKED_DRAG = 0.20
STALENESS_SATURATION_HOURS = 48.0
REATTEMPT_COOLDOWN_HOURS = 6.0


@dataclass(frozen=True)
class ConcernChoice:
    concern: Concern | None
    score: float
    reason: str
    considered: int


def _staleness(concern: Concern, now: float) -> float:
    return min(1.0, max(0.0, concern.hours_since_touched(now) / STALENESS_SATURATION_HOURS))


def _affect_fit(concern: Concern, valence: float | None) -> float:
    """Prefer tractable concerns under strain, stuck ones at ease.

    Neutral (0.5) when affect is unavailable, so a missing signal does not
    silently suppress every concern.
    """
    if valence is None:
        return 0.5
    has_traction = concern.advance_count > 0
    if valence < -0.05:
        return 0.8 if has_traction else 0.3
    if valence > 0.05:
        return 0.4 if has_traction else 0.8
    return 0.5


def score_concern(concern: Concern, *, now: float, valence: float | None = None) -> float:
    score = (
        W_STALENESS * _staleness(concern, now)
        + W_SALIENCE * concern.salience
        + W_AFFECT_FIT * _affect_fit(concern, valence)
    )
    drag = 1.0 + STALL_DRAG * concern.stall_count + BLOCKED_DRAG * concern.blocked_count
    return score / drag


def choose_concern(
    concerns: list[Concern], *, now: float, valence: float | None = None,
    allow_cooling: bool = False,
) -> ConcernChoice:
    """Pick what to pursue. Deterministic; ties broken by id.

    Returns concern=None when nothing is active — a being with nothing to
    pursue should say so rather than manufacture a pursuit.
    """
    active = [c for c in concerns if c.is_active]
    if not active:
        return ConcernChoice(None, 0.0, "no active concerns", len(concerns))

    eligible = [c for c in active
                if c.hours_since_attempted(now) >= REATTEMPT_COOLDOWN_HOURS]
    cooling = len(active) - len(eligible)
    if not eligible and not allow_cooling:
        # Everything is inside its cooldown. That is not a reason to re-ask
        # the question answered twenty minutes ago; it is a reason to go and
        # read. `run_once` sends a None choice to `_explore`, which books no
        # attempt and charges no setback.
        return ConcernChoice(None, 0.0,
                             f"all {cooling} cooling — nothing is eligible",
                             len(concerns))
    if not eligible:
        # S2 §7.1's floor, and the ONLY thing that may cross the cooldown:
        # nothing has been attempted for `UNSPENT_BUDGET_AFTER_S`, so the
        # being really is idling and thinking is what earns reading back.
        # The caller owns that judgment; this function is only told the
        # answer. The old unconditional bypass differed by firing every
        # cycle rather than once every four hours, which is the whole of the
        # damage it did.
        eligible, cooling = active, 0

    scored = sorted(
        ((score_concern(c, now=now, valence=valence), c) for c in eligible),
        key=lambda sc: (sc[0], -(sc[1].id or 0)),
        reverse=True,
    )
    best_score, best = scored[0]
    bits = [f"stale {best.hours_since_touched(now):.0f}h",
            f"salience {best.salience:.2f}"]
    if best.stall_count:
        bits.append(f"stalled {best.stall_count}x")
    if best.blocked_count:
        bits.append(f"blocked {best.blocked_count}x")
    if cooling:
        bits.append(f"{cooling} cooling")
    return ConcernChoice(best, best_score, " · ".join(bits), len(active))
