"""Long-form composition (P3 Phase 0, E0.1/E0.2).

Phase 0 is exempt from Rule 1 — its epics are a probe and produce a verdict,
not a behaviour change — but the code is real and Phase 2 builds on it, so the
paths that could quietly corrupt the operator's read are tested here: a
truncated piece must not reach the store, a chooser must not invent a subject,
and a written subject must not be offered twice.
"""

from __future__ import annotations

import json

import pytest

from newz.works.compose import (
    Subject,
    candidate_subjects,
    choose_subject,
    compose_piece,
    write_work,
)

from tests.conftest import FakeLLM


def _open_concern(store, statement="Does the diet ceiling hold under load?", cid=1):
    store.execute(
        "INSERT INTO concerns (id, opened_at, kind, statement, why_open,"
        " closing_condition, status, salience, origin)"
        " VALUES (?, 1.0, 'question', ?, 'it keeps recurring', 'a measurement',"
        " 'open', 0.8, 'curiosity')",
        (cid, statement),
    )
    store.commit()


def _choice(ref, because="I keep coming back to it."):
    return f"<choice><ref>{ref}</ref><because>{because}</because></choice>"


def _piece(title="On the ceiling", body="A paragraph that stands on its own."):
    return f"<piece><title>{title}</title><body>{body}</body></piece>"


def test_candidates_are_the_beings_own_open_questions_and_held_positions(store):
    _open_concern(store)
    store.execute(
        "INSERT INTO perspective_items (id, version, section, text, evidence_json,"
        " confidence, status, first_seen_version, ts)"
        " VALUES (7, 1, 'who_i_am', 'I prefer plain language.', '[]', 0.7, 'carried', 1, 1.0)"
    )
    store.commit()

    subjects = candidate_subjects(store)

    assert {(s.kind, s.ref) for s in subjects} == {("concern", 1), ("position", 7)}


def test_a_written_subject_is_never_offered_again(store):
    _open_concern(store)
    subject = candidate_subjects(store)[0]
    llm = FakeLLM([("VOICE", _piece())])
    write_work(store, compose_piece(llm, store, subject, "because"))

    assert candidate_subjects(store) == []


def test_the_being_cannot_choose_a_subject_it_does_not_hold(store):
    """A chooser that invents a reference has not chosen from what it carries,
    which is the whole of E0.2. Refuse rather than compose about nothing."""
    _open_concern(store)
    subjects = candidate_subjects(store)
    llm = FakeLLM([("VOICE", _choice("concern:999")), ("VOICE", _choice("concern:998"))])

    with pytest.raises(ValueError, match="not among the subjects it holds"):
        choose_subject(llm, store, subjects)


def test_an_invented_reference_is_retried_once(store):
    """Observed live 2026-08-18: the first real run named a subject outside the
    list. One retry, because the slip is a reference error and not a refusal."""
    _open_concern(store)
    subjects = candidate_subjects(store)
    llm = FakeLLM([("VOICE", _choice("concern:999")), ("VOICE", _choice("concern:1"))])

    subject, _ = choose_subject(llm, store, subjects)

    assert (subject.kind, subject.ref) == ("concern", 1)
    assert len(llm.calls) == 2


def test_the_choice_carries_the_beings_own_reason(store):
    _open_concern(store)
    subjects = candidate_subjects(store)
    llm = FakeLLM([("VOICE", _choice("concern:1", "I have been wrong about this twice."))])

    subject, because = choose_subject(llm, store, subjects)

    assert (subject.kind, subject.ref) == ("concern", 1)
    assert because == "I have been wrong about this twice."


def test_a_truncated_piece_is_retried_and_then_refused(store):
    """A severed piece would make Phase 0's read a read of the truncation."""
    subject = Subject("concern", 1, "Does it hold?", "")
    llm = FakeLLM([
        ("VOICE", "<piece><title>Cut</title><body>half a th", True),
        ("VOICE", "<piece><title>Cut</title><body>still half a th", True),
    ])

    with pytest.raises(RuntimeError, match="still truncated"):
        compose_piece(llm, store, subject, "because")

    assert store.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 0


def test_a_piece_that_finishes_on_the_second_attempt_is_kept(store):
    subject = Subject("concern", 1, "Does it hold?", "")
    llm = FakeLLM([
        ("VOICE", "<piece><title>Cut</title><body>half a th", True),
        ("VOICE", _piece(body="Two words here.")),
    ])

    piece = compose_piece(llm, store, subject, "because")

    assert piece.word_count == 3
    assert llm.calls[1]["max_tokens"] == 2 * llm.calls[0]["max_tokens"]


def test_the_written_piece_reads_back_whole(store):
    """P3 Rule 2: the migration ships with a writer and a reader."""
    _open_concern(store)
    subject = candidate_subjects(store)[0]
    llm = FakeLLM([("VOICE", _piece("A title", "The body, entire."))])

    work_id = write_work(store, compose_piece(llm, store, subject, "it nags"))

    row = store.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
    assert row["title"] == "A title"
    assert row["body"] == "The body, entire."
    assert row["chosen_because"] == "it nags"
    assert row["subject_text"] == "Does the diet ceiling hold under load?"


def test_no_second_model_grades_the_piece(store):
    """P3 Rule 4: a judge that is the being's own model is operation, not
    evidence. Composition must cost exactly one call — choosing is separate."""
    subject = Subject("concern", 1, "Does it hold?", "")
    llm = FakeLLM([("VOICE", _piece())])

    compose_piece(llm, store, subject, "because")

    assert len(llm.calls) == 1


def test_the_piece_is_written_with_perspective_and_constitution_in_context(store):
    subject = Subject("concern", 1, "Does it hold?", "")
    llm = FakeLLM([("VOICE", _piece())])

    compose_piece(llm, store, subject, "because")

    system = llm.calls[0]["system"]
    assert "I am Lumen" in system                    # the Perspective
    assert "honesty-001" in system or "false" in system  # the constitution prefix
    assert "Plain, curious, honest." in system       # the character core


# ── writing ends the concern (operator, 2026-08-21) ─────────────────────

def _composed(kind, ref):
    """A Piece as `compose_piece` returns it, ready for `write_work`."""
    from newz.works.compose import Piece, Subject

    return Piece(subject=Subject(kind, ref, "the subject", "why"),
                 chosen_because="because", title="A title",
                 body="Some prose that stands on its own.", model="m",
                 completion_tokens=10)


def test_writing_about_a_concern_closes_it(store):
    """*(operator, 2026-08-21)* — the loop this breaks: `score_concern` keys
    staleness on `last_advanced_at` and takes drag only from stalls, so a
    concern that keeps advancing resets its own clock and is never dragged.
    Concern 112 reached 44 advances, stall_count 1, and never closed. Behavior:
    an essay is a terminus that asks no model anything."""
    from newz.works.compose import write_work
    from newz.works.rhythm import close_subject

    _open_concern(store, cid=1)
    piece = _composed("concern", 1)
    work_id = write_work(store, piece)

    assert close_subject(store, piece, work_id) == "closed"
    row = store.execute(
        "SELECT status, resolution FROM concerns WHERE id=?", (1,)).fetchone()
    assert row["status"] == "closed"
    assert f"work {work_id}" in row["resolution"]


def test_the_closure_carries_no_position(store):
    """E2.3 and R-24: a work may never be evidence for a position. `close_concern`
    puts the position on an episode that sleep may admit into the Perspective,
    so taking one from the essay would be the self-echo trap in a new medium.
    Behavior: the position is empty — the piece IS the position, and it stays
    outside the Perspective."""
    from newz.works.compose import write_work
    from newz.works.rhythm import close_subject

    _open_concern(store, cid=1)
    piece = _composed("concern", 1)
    close_subject(store, piece, write_work(store, piece))

    ep = store.execute(
        "SELECT content_json FROM episodes WHERE kind='concern_closed'"
        " AND source_ref=?", ("concern:1",)).fetchone()
    assert ep is not None, "closing must still record the episode"
    assert json.loads(ep["content_json"])["position"] == ""


def test_writing_about_a_position_closes_nothing(store):
    """Works are written about held positions too, and a position is not a
    concern. Behavior: the closure applies to concerns alone."""
    from newz.works.compose import write_work
    from newz.works.rhythm import close_subject

    piece = _composed("position", 1)
    assert close_subject(store, piece, write_work(store, piece)) == ""


def test_a_subject_that_is_gone_is_not_reported_as_closed(store):
    """`close_concern` is an UPDATE with no rowcount check, so a missing concern
    would report success AND write a `concern_closed` episode about a row that
    does not exist — a record saying something happened to nothing. Behavior:
    the status is read first, the work stands, and no episode is written."""
    from newz.works.compose import write_work
    from newz.works.rhythm import close_subject

    piece = _composed("concern", 9999)            # no such concern
    work_id = write_work(store, piece)

    assert close_subject(store, piece, work_id) == "open"
    assert store.execute(
        "SELECT COUNT(*) FROM works WHERE id=?", (work_id,)).fetchone()[0] == 1
    assert store.execute(
        "SELECT COUNT(*) FROM episodes WHERE kind='concern_closed'"
    ).fetchone()[0] == 0


def test_a_concern_already_closed_is_not_closed_twice(store):
    """The judge may close a concern between the subject being chosen and the
    piece landing. Behavior: the second closure is a no-op, so there is one
    `concern_closed` episode and not two."""
    from newz.works.compose import write_work
    from newz.works.rhythm import close_subject

    _open_concern(store, cid=1)
    piece = _composed("concern", 1)
    work_id = write_work(store, piece)      # UNIQUE(subject_kind, subject_ref)

    assert close_subject(store, piece, work_id) == "closed"
    assert close_subject(store, piece, work_id) == "closed"
    assert store.execute(
        "SELECT COUNT(*) FROM episodes WHERE kind='concern_closed'"
    ).fetchone()[0] == 1


def test_a_written_concern_leaves_the_deliberation_pool(store):
    """The desired outcome, stated as the being's own scorer sees it.
    `ACTIVE_STATUSES` is ("open",), so a closed concern is not chosen, not
    scored and not advanced again. Behavior: the loop cannot resume."""
    from newz.concerns.store import load_active
    from newz.works.compose import write_work
    from newz.works.rhythm import close_subject

    _open_concern(store, cid=1)
    assert 1 in [c.id for c in load_active(store)]

    piece = _composed("concern", 1)
    close_subject(store, piece, write_work(store, piece))

    assert 1 not in [c.id for c in load_active(store)]
