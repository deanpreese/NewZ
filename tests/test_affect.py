"""S2 §6.3 — the honest signal, or nothing.

Cited in no P2 phase at all: no module, no table, while §6.1 routed
substrate distress into it and §10.3 folded consequence into it. Ported with
review 2026-08-13 under the allowlist extension; the CONSTRAINT KNOBS
deliberately did not cross (newz/affect/README-constraint.md).
"""

import time

from newz.affect.state import AffectState, AffectVector, project_curiosity
from newz.affect.store import (
    CONCERN_CLOSED,
    SUBSTRATE_DISTRESS,
    current,
    load,
    record,
)
from newz.affect.update import CAP, apply_delta, decayed, neutral

# A real clock: epoch 0 is not a legitimate timestamp and decay treats
# it as "unset", which is correct behaviour and a bad test fixture.
T0 = 1_760_000_000.0


def test_a_single_event_cannot_rewrite_character(store):
    # Per-timescale caps: mood moves, character barely does.
    s = apply_delta(neutral(1000.0), {"valence": -1.0}, 1000.0)
    assert abs(s.mood.valence) <= CAP["mood"] + 1e-9
    assert abs(s.character.valence) <= CAP["character"] + 1e-9
    assert abs(s.mood.valence) > abs(s.character.valence)


def test_saturation_is_the_circuit_breaker(store):
    # An axis near its limit cannot be pushed further — the bound against an
    # affect -> behaviour -> percept -> affect spiral.
    s = neutral(T0)
    for i in range(40):
        s = apply_delta(s, {"valence": -1.0}, T0 + i)
    first_step = abs(apply_delta(neutral(T0), {"valence": -1.0}, T0).mood.valence)
    further = apply_delta(s, {"valence": -1.0}, T0 + 40)
    assert abs(further.mood.valence - s.mood.valence) < first_step
    assert s.mood.valence >= -1.0


def test_decay_returns_to_neutral_and_the_timescales_differ(store):
    s = apply_delta(neutral(T0), {"valence": -1.0}, T0)
    mood_then, char_then = s.mood.valence, s.character.valence
    # One mood half-life (10 min): mood halves, character barely moves.
    later = decayed(s, T0 + 600.0)
    assert abs(later.mood.valence) < abs(mood_then) * 0.6
    assert abs(later.character.valence) > abs(char_then) * 0.99

    # A week later everything is essentially neutral again.
    assert abs(decayed(s, T0 + 7 * 86400.0).mood.valence) < 0.01


def test_distress_needs_low_control_not_merely_low_valence(store):
    # Distress is feeling bad AND being unable to do anything about it.
    helpless = AffectState(mood=AffectVector(valence=-0.8, control=-0.8))
    capable = AffectState(mood=AffectVector(valence=-0.8, control=0.8))
    assert helpless.distress_level() > capable.distress_level()
    assert AffectState(mood=AffectVector(valence=0.5)).distress_level() == 0.0


def test_it_reports_words_never_numbers(store):
    # v1's invariant kept: a being reporting "valence 0.31" is reporting an
    # instrument, not a state.
    s = AffectState(mood=AffectVector(valence=0.6, arousal=0.5, uncertainty=0.5))
    text = s.summary_for_prompt()
    assert text
    assert not any(ch.isdigit() for ch in text)
    assert project_curiosity(s.mood) > 0.3 and "curiosity" in text


def test_a_bad_substrate_day_produces_honest_negative_affect(store):
    # S2 §6.1's "available source of honest negative affect".
    record(store, SUBSTRATE_DISTRESS, source="substrate", note="DEEP unreachable")
    s = load(store)
    assert s.mood.valence < 0 and s.mood.control < 0
    assert s.distress_level() > 0


def test_closing_a_concern_folds_into_affect(store):
    from newz.concerns.model import Concern
    from newz.concerns.store import close_concern, create_concern

    cid = create_concern(store, Concern(
        id=None, statement="q", why_open="w", closing_condition="c",
        origin="curiosity"))
    close_concern(store, cid, position="A position.", resolution="Settled.")
    assert load(store).mood.valence > 0


def test_reading_affect_never_writes_it(store):
    # Otherwise every glance at how the being feels becomes an event in how
    # it feels.
    record(store, CONCERN_CLOSED, source="concern", note="x")
    before = store.execute("SELECT COUNT(*) FROM affect_state").fetchone()[0]
    for _ in range(3):
        current(store)
    assert store.execute(
        "SELECT COUNT(*) FROM affect_state").fetchone()[0] == before


def test_affect_reaches_conversation_as_something_sayable(store):
    from newz.conversation.composer import _system_prompt

    record(store, SUBSTRATE_DISTRESS, source="substrate", note="bad day")
    system = _system_prompt(store, "dean")
    assert "What I notice in myself right now" in system
    # And the section tells it the boundary the constitution actually draws.
    assert "may not dress it up as felt experience" in system


def test_no_state_yet_says_nothing_rather_than_neutral_noise(store):
    from newz.conversation.composer import _system_prompt

    assert "What I notice in myself" not in _system_prompt(store, "dean")


def test_an_affect_failure_never_costs_the_event_it_accompanies(store, monkeypatch):
    from newz.concerns.model import Concern
    from newz.concerns.store import close_concern, create_concern

    cid = create_concern(store, Concern(
        id=None, statement="q", why_open="w", closing_condition="c",
        origin="curiosity"))
    monkeypatch.setattr("newz.affect.store.record",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    close_concern(store, cid, position="A position.", resolution="Settled.")
    assert store.execute(
        "SELECT status FROM concerns WHERE id=?", (cid,)).fetchone()[0] == "closed"
