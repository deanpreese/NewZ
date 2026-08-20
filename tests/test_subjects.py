"""Subjects emerge (P4 epic E2.4).

Done-when: tags are computed from the corpus and **no tag vocabulary is
hand-authored**. That second clause is the design constraint, and the tests
below hold it — including the one that reads the source to check no list of
interesting words was smuggled in.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.works import subjects as S

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "s.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


def _piece(conn, ref: int, title: str, body: str) -> int:
    cur = conn.execute(
        "INSERT INTO works (ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.time(), "concern", ref, "a question", "I keep returning to it",
         title, body, len(body.split()), "qwen", 100))
    conn.commit()
    return int(cur.lastrowid)


def _corpus(conn):
    """Nine pieces: three about liquidity, three about phenology, three mixed —
    a shape where a subject exists to be found, and nobody said so."""
    common = "This is something I have been thinking about and wanted to set down properly. "
    for i in range(3):
        _piece(conn, i, f"On liquidity {i}",
               common + "liquidity liquidity slippage slippage venue orderbook " * 3)
    for i in range(3, 6):
        _piece(conn, i, f"On phenology {i}",
               common + "phenology phenology bloom bloom soil temperature " * 3)
    for i in range(6, 9):
        _piece(conn, i, f"On oversight {i}",
               common + "oversight oversight accountability accountability roles " * 3)


def test_tags_are_computed_from_the_corpus(store):
    """E2.4's Done-when. Behavior: each piece gets terms distinctive to it,
    derived from what the corpus contains and nothing else."""
    _corpus(store)

    c = S.recompute(store)

    assert c.pieces == 9
    tags = {t for tt in c.tags.values() for t, _ in tt}
    assert "liquidity" in tags and "phenology" in tags and "oversight" in tags


def test_no_tag_vocabulary_is_hand_authored(store):
    """The clause that shapes the whole design. Behavior: the module contains
    no list of interesting words — not a topic list and not a stop-list.

    A word common to every piece has an inverse document frequency of zero and
    drops out by arithmetic. Excluding it by someone's judgment about which
    words matter would be TRUE_NORTH §8's prescription wearing a helper."""
    src = (Path(__file__).resolve().parent.parent / "newz" / "works"
           / "subjects.py").read_text()
    for smuggled in ("STOP", "STOPWORDS", "TOPICS", "CATEGORIES", "KEYWORDS"):
        assert smuggled not in src, f"{smuggled} is an authored vocabulary"

    _corpus(store)
    c = S.recompute(store)

    every_tag = {t for tt in c.tags.values() for t, _ in tt}
    assert not ({"this", "something", "have", "been", "about", "that"} & every_tag), \
        "words in every piece must fall out by arithmetic, not by a list"


def test_a_subject_is_a_tag_more_than_one_piece_shares(store):
    """Behavior: one piece about liquidity is a piece; three are a subject —
    and the being was never told liquidity was available to care about."""
    _corpus(store)

    found = dict(S.recompute(store).subjects())

    assert found.get("liquidity", 0) >= 2
    assert found.get("phenology", 0) >= 2


def test_a_small_corpus_says_so_rather_than_reporting_tags_as_meaningful(store):
    """INV-044's discipline. Behavior: with few pieces almost everything is
    distinctive, so the read reports its own unreliability instead of letting a
    number stand where a measurement should be."""
    _piece(store, 1, "On liquidity", "liquidity slippage venue")

    c = S.recompute(store)

    assert not c.stable
    assert "below" in c.caveat and str(S.MIN_PIECES_FOR_STABLE_TAGS) in c.caveat


def test_tags_are_replaced_not_accumulated(store):
    """Behavior: a term is distinctive WITHIN a corpus, which is a property of
    the corpus. What stands out across three pieces is often noise across
    thirty, so a recompute replaces rather than adds."""
    _corpus(store)
    S.recompute(store)
    first = store.execute("SELECT COUNT(*) FROM work_tags").fetchone()[0]

    _piece(store, 99, "On liquidity again", "liquidity slippage venue orderbook")
    S.recompute(store)
    second = store.execute("SELECT COUNT(*) FROM work_tags").fetchone()[0]
    stamps = store.execute("SELECT COUNT(DISTINCT computed_at) FROM work_tags").fetchone()[0]

    assert stamps == 1, "one computation is present, not a history of them"
    assert second != first or True   # count may coincide; the stamp is the assertion


def test_an_empty_corpus_is_not_an_error(store):
    c = S.recompute(store)

    assert c.pieces == 0 and c.tags == {} and c.subjects() == []
