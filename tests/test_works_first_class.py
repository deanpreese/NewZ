"""`works` first-class (P4 epic E3.1).

E0.1's minimal row grows up. Done-when: every field has a writer and a reader
(Rule 2), and the generator consumes them — that last clause is discharged by
E3.2, which depends on this.

What was missing is everything that makes a piece a piece of WORK rather than a
stored string: a signature that makes it tamper-evident, the identity that wrote
it, and the evidence its subject rested on at the time.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.works.compose import Piece, Subject, evidence_for, signature_of, write_work

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "w.db")
    apply_pending(conn, MAIN_SQL)
    conn.execute("INSERT INTO constitution (version, ts, clauses_yaml,"
                 " change_summary, approval_status) VALUES (6, ?, 'x', 'y', 'active')",
                 (time.time(),))
    conn.execute("INSERT INTO perspective (version, ts, content, token_count,"
                 " writer) VALUES (12, ?, '...', 3, 'sleep')", (time.time(),))
    for cid in (1, 7):
        conn.execute(
            "INSERT INTO concerns (id, opened_at, kind, statement, why_open,"
            " closing_condition, status, salience, origin)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, time.time(), "inquiry", "Does the index roll over?",
             "it bears on what I hold",
             "the statistical office publishes its March release",
             "open", 0.5, "reading"))
    conn.commit()
    yield conn
    conn.close()


def _piece(kind="concern", ref=1, title="On rolling over", body="It is rolling over.") -> Piece:
    return Piece(Subject(kind, ref, "Does the index roll over?", "open"),
                 "I keep returning to it", title, body, "qwen", 200)


def test_a_piece_lands_signed(store):
    """Consumer: tools/read_works.py --verify. Behavior: the stored piece is
    tamper-evident, which is what gives E3.5's byte-comparable regeneration
    something to compare against."""
    wid = write_work(store, _piece())

    row = store.execute("SELECT * FROM works WHERE id=?", (wid,)).fetchone()
    assert row["signature"]
    assert row["signature"] == signature_of("concern", 1, "On rolling over",
                                            "It is rolling over.")


def test_an_edited_piece_no_longer_matches_its_signature(store):
    """The thing a signature is for. Behavior: a body of work whose pieces can
    be quietly edited is a current opinion with a date on it."""
    wid = write_work(store, _piece())

    store.execute("UPDATE works SET body='quietly edited' WHERE id=?", (wid,))
    store.commit()

    row = store.execute("SELECT * FROM works WHERE id=?", (wid,)).fetchone()
    assert signature_of(row["subject_kind"], row["subject_ref"],
                        row["title"], row["body"]) != row["signature"]


def test_the_signature_is_over_the_work_and_not_over_when_it_was_written(store):
    """Behavior: the same piece about the same subject is the same piece. A
    signature over the timestamp would make regeneration uncomparable, which is
    the opposite of what E3.5 needs."""
    a = signature_of("concern", 1, "T", "B")
    time.sleep(0.01)
    b = signature_of("concern", 1, "T", "B")

    assert a == b
    assert signature_of("position", 1, "T", "B") != a


def test_a_piece_records_the_being_that_wrote_it(store):
    """Behavior: a piece read a year later is read against the self that wrote
    it, not the self reading it — which is what makes E2.2's re-reading a
    meeting rather than a proofread."""
    wid = write_work(store, _piece())

    row = store.execute("SELECT * FROM works WHERE id=?", (wid,)).fetchone()
    assert row["constitution_version"] == 6
    assert row["perspective_version"] == 12


def test_the_evidence_its_subject_rested_on_is_copied_not_pointed_at(store):
    """Behavior: a concern's advances move and a position's evidence decays.
    What grounded THIS piece does not, so it is captured at write time."""
    store.execute(
        "INSERT INTO concern_advances (concern_id, ts, kind, summary,"
        " evidence_json) VALUES (?,?,?,?,?)",
        (7, time.time(), "reasoning", "s", json.dumps(["src-1", "src-2"])))
    store.commit()

    wid = write_work(store, _piece(ref=7))

    stored = json.loads(store.execute(
        "SELECT evidence_json FROM works WHERE id=?", (wid,)).fetchone()[0])
    assert stored == ["src-1", "src-2"]

    store.execute("UPDATE concern_advances SET evidence_json=? WHERE concern_id=?",
                  (json.dumps(["src-9"]), 7))
    store.commit()
    still = json.loads(store.execute(
        "SELECT evidence_json FROM works WHERE id=?", (wid,)).fetchone()[0])
    assert still == ["src-1", "src-2"], "what grounded the piece does not move"


def test_a_superseded_advance_is_not_evidence_for_a_piece(store):
    """Behavior: evidence is what the being currently holds on the subject —
    a retired advance is part of the record and not part of the grounding."""
    now = time.time()
    # The retiring advance must exist before anything can point at it —
    # superseded_by is itself a foreign key, which is how the store keeps a
    # retirement pointing at something real.
    cur = store.execute(
        "INSERT INTO concern_advances (concern_id, ts, kind, summary,"
        " evidence_json) VALUES (?,?,?,?,?)",
        (7, now, "reasoning", "new", json.dumps(["src-new"])))
    store.execute("INSERT INTO concern_advances (concern_id, ts, kind, summary,"
                  " evidence_json, superseded_by) VALUES (?,?,?,?,?,?)",
                  (7, now, "reasoning", "old", json.dumps(["src-old"]),
                   cur.lastrowid))
    store.commit()

    assert evidence_for(store, Subject("concern", 7, "q", "")) == ["src-new"]


def test_pieces_written_before_this_are_not_backfilled(store):
    """Behavior: a signature computed now would attest to the row as it stands
    rather than to what was written — which is exactly the assurance a
    signature is supposed to give. Unsigned is the honest state."""
    store.execute(
        "INSERT INTO works (ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.time(), "concern", 3, "q", "because", "old piece", "b", 1, "m", 1))
    store.commit()

    row = store.execute("SELECT signature FROM works WHERE title='old piece'").fetchone()
    assert row["signature"] is None
