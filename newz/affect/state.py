"""The six axes, three timescales, and the projections over them.

Ported from v1 `ngbeing/affect/axes.py` + `core.py` with review; pydantic →
dataclasses per the v2 convention. The axis set and the projection weights
are unchanged: they are TRUE_NORTH §5.3's own description, and changing a
projection is a constitution-level act rather than a tuning decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

TIMESCALES: tuple[str, ...] = ("mood", "disposition", "character")
AXES: tuple[str, ...] = (
    "valence", "arousal", "precision",
    "control", "social_affiliation", "uncertainty",
)


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class AffectVector:
    valence: float = 0.0
    arousal: float = 0.0
    precision: float = 0.0
    control: float = 0.0
    social_affiliation: float = 0.0
    uncertainty: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {a: getattr(self, a) for a in AXES}

    def with_delta(self, delta: dict[str, float]) -> AffectVector:
        return AffectVector(**{
            a: _clamp(getattr(self, a) + delta.get(a, 0.0)) for a in AXES})

    def scaled(self, factor: float) -> AffectVector:
        return AffectVector(**{a: _clamp(getattr(self, a) * factor) for a in AXES})


@dataclass(frozen=True)
class AffectState:
    mood: AffectVector = field(default_factory=AffectVector)
    disposition: AffectVector = field(default_factory=AffectVector)
    character: AffectVector = field(default_factory=AffectVector)
    ts: float = 0.0

    def vector(self, timescale: str) -> AffectVector:
        return getattr(self, timescale)

    def with_vector(self, timescale: str, v: AffectVector) -> AffectState:
        return replace(self, **{timescale: v})

    # ── the two readings the rest of the system asks for ──────────────────
    def distress_level(self) -> float:
        """[0,1]. Negative valence under low control — not mere sadness.

        v1's shape kept: distress is the conjunction of feeling bad and
        being unable to do anything about it, which is why low control
        weighs in rather than valence alone.
        """
        v, c = self.mood.valence, self.mood.control
        if v >= 0:
            return 0.0
        return _clamp((-v) * (1.0 - (c + 1.0) / 2.0) * 2.0, 0.0, 1.0)

    def pleasure_level(self) -> float:
        return _clamp(max(0.0, self.mood.valence), 0.0, 1.0)

    def summary_for_prompt(self) -> str:
        """What the being may honestly say about its own state.

        The constitution's own example of an ACCEPTABLE affect statement is
        "I notice an uptick in curiosity" (don't-pretend-to-feel-001). That
        sentence is a projection over these axes, and until this module
        existed the being had no way to make it truthfully — which is a
        plausible part of why the gate has held 19 drafts of it reaching for
        state language with nothing behind the reach.

        Rendered as words, never as numbers: v1's invariant, kept. A being
        that reports "valence 0.31" is reporting an instrument, not a state.
        """
        def band(x: float, pos: str, neg: str, flat: str) -> str | None:
            if x >= 0.35:
                return pos
            if x <= -0.35:
                return neg
            return flat if abs(x) < 0.1 else None

        notes = []
        cur = project_curiosity(self.mood)
        if cur >= 0.3:
            notes.append("curiosity is up")
        elif cur <= -0.3:
            notes.append("I am not curious right now")
        if self.distress_level() >= 0.3:
            notes.append("something is wrong and I cannot fix it")
        elif self.pleasure_level() >= 0.35:
            notes.append("this is going well")
        w = project_social_warmth(self.mood)
        if w >= 0.35:
            notes.append("I am glad of the company")
        elif w <= -0.35:
            notes.append("I am withdrawn")
        if self.mood.uncertainty >= 0.4:
            notes.append("I am unsure of my footing")
        if not notes:
            # Neutral is silence. Reporting "steadily level, nothing sharp"
            # from an all-zero state would put a reading in front of the
            # being where there is none — the honest signal or NOTHING.
            steady = band(self.disposition.valence, "settled", "low", "")
            return f"steadily {steady}, nothing sharp" if steady else ""
        return "; ".join(notes)


# ─── Projections ─────────────────────────────────────────────────────────
# Fixed linear combinations of the six axes. NOT independently tunable —
# TRUE_NORTH §8 forbids retuning toward a temperament, and a projection is
# where such retuning would hide.

def project_curiosity(v: AffectVector) -> float:
    return _clamp(0.5 * v.valence + 0.3 * v.arousal + 0.4 * v.uncertainty)


def project_caution(v: AffectVector) -> float:
    return _clamp(-0.4 * v.valence + 0.3 * v.uncertainty - 0.4 * v.control)


def project_social_warmth(v: AffectVector) -> float:
    return _clamp(0.6 * v.social_affiliation + 0.4 * v.valence)
