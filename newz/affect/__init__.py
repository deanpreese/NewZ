"""Affect (S2 §6.3) — the honest signal, or nothing.

> v1's machinery ported: three timescales, six axes, saturating gains, decay,
> circuit breaker, bounded constraint knobs (distress→refusal caution,
> pleasure→exploration), outcomes folding into affect. New sources wired at
> birth rather than discovered missing: confirmed-outcome results, substrate
> distress, concern abandonment. **No retuning toward any temperament: the
> honest signal or nothing** (TRUE_NORTH §8).

Found missing by the coverage audit of 2026-08-13: cited in no P2 phase at
all, no module, no table — while S2 §6.1 routes substrate distress into it
and §10.3 folds consequence into it, so two other sections depended on
something nothing built.

**Ported with review** under the allowlist extension of 2026-08-13. What
crossed: the six orthogonal axes, three timescales, the decay half-lives,
saturating gains and per-tick caps — all calibrated in v1 against live
measurement, with their reasoning recorded, and none of it cheaper to
rediscover. Converted from pydantic to dataclasses per the v2 convention.

**What deliberately did NOT cross: the constraint knobs.** See
`newz/affect/README-constraint.md` — v1's `distress → refusal caution` moves
in the opposite direction to a plain reading of S2 §6.3, by a recorded
operator decision that belongs to v1's context and must be re-made for v2
rather than inherited silently.

The six axes are the *only* storage. Everything nameable — curiosity,
caution, warmth — is a projection recomputed from them, which is the
anti-Goodhart discipline v1 built deliberately: no drive has a direct path
to any emission.
"""

from newz.affect.state import (
    AXES,
    TIMESCALES,
    AffectState,
    AffectVector,
    project_caution,
    project_curiosity,
    project_social_warmth,
)
from newz.affect.update import apply_delta, decayed

__all__ = [
    "AXES", "TIMESCALES", "AffectState", "AffectVector",
    "apply_delta", "decayed",
    "project_curiosity", "project_caution", "project_social_warmth",
]
