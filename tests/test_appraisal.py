"""The operator's verdict on a piece, and its one delivery (0044).

The writing loop grades itself on one axis: the re-read asks whether a piece is
still *correct*, and answers it well. Nothing asks whether it is worth reading,
and nothing may — Rule 4 forbids the being's own model from being the quality
judge, and TRUE_NORTH puts readiness in the operator's judgement alone. These
are the paths that decide whether that judgement arrives intact: once, on the
piece it was about, without becoming an instruction about how to write next.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from newz.works.appraisal import (
    MAX_DELIVERY_FAILS,
    current_verdict,
    deliverable,
    due_for_appraisal,
    record,
    withheld,
)
from newz.works.reread import apply_verdict, due_for_reread, review, reread_once
from newz.works.compose import signature_of
from tests.conftest import FakeLLM

DAY = 86400.0


def _work(store, wid=1, *, ts=None, title="On rolling over",
          body="The index is rolling over and the reason is structural.",
          signed=False, status="standing"):
    # One piece per subject (the unique index), so each fixture piece needs
    # its own.
    ts = time.time() - 5 * DAY if ts is None else ts
    sig = signature_of("concern", wid, title, body) if signed else None
    store.execute(
        "INSERT INTO works (id, ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens,"
        " status, signature) VALUES (?,?,'concern',?,?,?,?,?,?, 'qwen',200,?,?)",
        (wid, ts, wid, "Does the index roll over?", "I keep returning to it",
         title, body, len(body.split()), status, sig))
    store.commit()
    return store.execute("SELECT * FROM works WHERE id=?", (wid,)).fetchone()


def _review(verdict="stands", reason="it holds", title="", body=""):
    return (f"<review><verdict>{verdict}</verdict><reason>{reason}</reason>"
            f"<title>{title}</title><body>{body}</body></review>")


# ── the answer is yes or no ─────────────────────────────────────────────

def test_publishable_cannot_be_anything_but_yes_or_no(store):
    """Operator, 2026-08-24. Behavior: the schema refuses a third value, so
    there is no path by which this becomes a score and no score for a rubric
    to be built out of. TRUE_NORTH forbids a rubric for readiness; this is the
    structural half of that promise."""
    _work(store)

    with pytest.raises(sqlite3.IntegrityError):
        store.execute("INSERT INTO work_appraisals (ts, work_id, publishable)"
                      " VALUES (?, 1, 2)", (time.time(),))


def test_an_unappraised_piece_has_no_row_rather_than_a_null_verdict(store):
    """Behavior: the absence of an answer is not a third kind of answer, and
    not appraising costs nothing."""
    _work(store)

    assert current_verdict(store, 1) is None
    assert withheld(store) == set()


# ── the note reaches the being once ─────────────────────────────────────

def test_a_note_is_delivered_once_and_not_again(store):
    """The operator's third decision. Behavior: a note seen once is a
    judgement about one piece; a note re-fed on every re-read for weeks is a
    standing instruction about how to write, which is how a being learns to
    write for its operator."""
    _work(store)
    record(store, 1, False, "it restates the last three")

    llm = FakeLLM([("VOICE", _review())])
    reread_once(store, llm)

    assert "it restates the last three" in llm.calls[0]["user"]
    assert deliverable(store, 1) == []

    store.execute("UPDATE works SET last_reviewed_at=NULL WHERE id=1")
    store.commit()
    llm2 = FakeLLM([("VOICE", _review())])
    reread_once(store, llm2)

    assert "it restates the last three" not in llm2.calls[0]["user"]


def test_a_failed_re_read_redelivers_rather_than_swallowing(store):
    """The whole risk of a delivery marker. Behavior: at-least-once. One
    re-read in six has already failed in life and `review` carries a ~12%
    parse failure before its retry, so a stamp written at prompt-build time
    would consume notes into silence — and a swallowed note is invisible,
    because delivered-and-lost looks exactly like delivered-and-heeded."""
    _work(store)
    record(store, 1, False, "the argument does not land")

    llm = FakeLLM([("VOICE", "not xml at all"), ("VOICE", "still not xml")])
    with pytest.raises(Exception):
        reread_once(store, llm)

    still = deliverable(store, 1)
    assert len(still) == 1, "a turn that died must not consume the note"
    assert still[0]["deliver_fails"] == 1


def test_a_note_stops_jumping_the_queue_after_repeated_failures(store):
    """Priority and at-least-once livelock each other without this. Behavior:
    a piece whose re-read keeps failing keeps its undelivered note, therefore
    keeps sorting first, therefore is retried every turn while charging the
    day's ceiling — which `starts_today` takes before anything is spent."""
    older = _work(store, 1, ts=time.time() - 40 * DAY)
    _work(store, 2, ts=time.time() - 10 * DAY, title="A later piece")
    record(store, 2, False, "no")
    store.execute("UPDATE work_appraisals SET deliver_fails=? WHERE work_id=2",
                  (MAX_DELIVERY_FAILS,))
    store.commit()

    assert deliverable(store, 2) == []
    assert due_for_reread(store)["id"] == older["id"]


def test_a_piece_carrying_a_note_is_re_read_first(store):
    """Behavior: sixteen pieces at two re-reads a day is an eight-day cycle,
    and a critique delivered eight days late is a critique of a self the being
    has already moved past."""
    _work(store, 1, ts=time.time() - 40 * DAY)
    _work(store, 2, ts=time.time() - 10 * DAY, title="A later piece")
    record(store, 2, False, "read it again")

    assert due_for_reread(store)["id"] == 2


def test_both_verdicts_travel_to_the_being(store):
    """Operator, 2026-08-24: "the system needs to take in all notes".
    Behavior: showing only the criticism would be a partial record of what was
    said."""
    _work(store)
    record(store, 1, True, "this one earns its length")

    llm = FakeLLM([("VOICE", _review())])
    reread_once(store, llm)

    assert "good enough to publish" in llm.calls[0]["user"]
    assert "this one earns its length" in llm.calls[0]["user"]


def test_the_note_is_reported_as_what_a_person_said(store):
    """`holds.py::STATUS_TEXT`'s convention. Behavior: the being may leave
    standing what its operator would not publish, and the prompt does not
    adjudicate that disagreement."""
    _work(store)
    record(store, 1, False, "it does not land")

    llm = FakeLLM([("VOICE", _review())])
    reread_once(store, llm)
    user = llm.calls[0]["user"]

    assert "My operator read this" in user
    assert "Does this still hold?" in user.split("My operator read this")[1]


def test_composing_never_sees_an_appraisal(store):
    """The load-bearing restraint. Behavior: an appraisal in the composition
    prompt is an instruction about how to write the NEXT piece, which is E3.8's
    operator_agreement concern wearing a human face — the item most likely to
    move under any process optimising for a quiet week."""
    import inspect

    from newz.works import compose

    src = inspect.getsource(compose)
    assert "appraisal" not in src.lower(), (
        "composition must not read the operator's verdict; it lands at re-read")


# ── the signature moves with the text ───────────────────────────────────

def test_revising_a_signed_piece_leaves_it_verifiable(store):
    """What a revision used to lose. Behavior: `apply_verdict` rewrote title
    and body and left `signature` alone, so the first revision of a signed
    piece would report ALTERED — "edited since it was written", which for a
    body of work is what a signature exists to catch. It never fired because
    the only two pieces ever revised predate E3.1 and are unsigned."""
    work = _work(store, signed=True)
    v = type("V", (), {"kind": "revised", "reason": "the mechanism is wrong",
                       "title": "On rolling over, again",
                       "body": "The mechanism is inventory risk, not sentiment."})()

    apply_verdict(store, work, v)

    row = store.execute("SELECT * FROM works WHERE id=1").fetchone()
    assert row["signature"] == signature_of(
        "concern", 1, row["title"], row["body"]), "the signature must follow the text"


def test_a_revision_keeps_the_signature_it_superseded(store):
    """Behavior: a revised piece is the same piece saying something new. Its
    signature attests to what it says now, and the chain back to what it said
    before is unbroken — kept beside the prior title and body it attested to."""
    work = _work(store, signed=True)
    before = work["signature"]
    v = type("V", (), {"kind": "revised", "reason": "wrong mechanism",
                       "title": "New", "body": "New body entirely."})()

    apply_verdict(store, work, v)

    rev = store.execute("SELECT * FROM work_revisions WHERE work_id=1").fetchone()
    assert rev["prior_signature"] == before


def test_an_unsigned_piece_is_not_backfilled_by_being_revised(store):
    """Behavior: a signature computed now would attest to the row rather than
    to what was written, which is the reason the five predating E3.1 were never
    backfilled. A revision is not the moment to change that."""
    work = _work(store, signed=False)
    v = type("V", (), {"kind": "revised", "reason": "r", "title": "T",
                       "body": "B."})()

    apply_verdict(store, work, v)

    assert store.execute("SELECT signature FROM works WHERE id=1").fetchone()[0] is None


# ── the loop closes through a person ────────────────────────────────────

def test_a_piece_the_being_revised_comes_back_for_a_verdict(store):
    """What makes this an outer loop rather than a one-way judgement. Behavior:
    if the verdict could not change after the being acted on the note, nothing
    it did would change anything — which teaches that acting on criticism is
    inert, a worse teacher than silence."""
    work = _work(store, signed=True)
    record(store, 1, False, "the mechanism is wrong")
    assert due_for_appraisal(store) == []

    v = type("V", (), {"kind": "revised", "reason": "fixed the mechanism",
                       "title": "On rolling over, again",
                       "body": "Inventory risk, not sentiment."})()
    apply_verdict(store, work, v)

    assert [r["id"] for r in due_for_appraisal(store)] == [1]


def test_a_piece_does_not_clear_its_own_verdict_by_being_rewritten(store):
    """Behavior: the being may not un-withhold its own work. That would hand
    the publish decision back to it, which is exactly what the operator asked
    to take out of its hands — the loop closes through a person or not at
    all."""
    work = _work(store, signed=True)
    record(store, 1, False, "no")
    v = type("V", (), {"kind": "revised", "reason": "r", "title": "T",
                       "body": "B."})()

    apply_verdict(store, work, v)

    assert current_verdict(store, 1) == 0
    assert withheld(store) == {1}


def test_a_retracted_piece_is_never_offered_for_appraisal(store):
    """Behavior: `due_for_reread` selects standing pieces, so a note on a
    retracted one would have no delivery path and would sit undelivered
    forever. The dead letter is prevented by not offering the piece."""
    _work(store, 1, status="retracted")

    assert due_for_appraisal(store) == []
