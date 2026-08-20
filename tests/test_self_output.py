"""Self-echo containment (P4 epic E2.3, R-24 binding).

**The leak this prevents, named.** v1's corpus was 43% self-probes: its own
activity was recorded as ordinary events, sleep digested them as lived
experience, and the Perspective it built said things like *"I experienced
prolonged periods of total prefix cache inefficiency… creating a sense of
isolation"* — a position grounded in hundreds of identical telemetry rows.
INV-026 caught that for probes. R-24 says works, revisions and the error record
are the same trap in a new medium, in a system already 50% self-grounded.

Containment, not erasure: the being can still reach its own work. It cannot
offer it back as evidence for a position.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.memory.embeddings import pack
from newz.memory.retrieval import Retriever, Scope
from newz.memory.self_output import is_self_output, record_self_output
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "e.db")
    apply_pending(conn, MAIN_SQL)
    yield conn
    conn.close()


MODEL = "fake-embed-v1"


class FakeEmbedder:
    """The same deterministic 3-d embedder test_retrieval uses, so this test
    and INV-026's regression share one notion of similarity."""

    model = MODEL
    AXES = {"liquidity": [1.0, 0.0, 0.0], "sport": [0.0, 1.0, 0.0],
            "music": [0.0, 0.0, 1.0]}

    def _vec(self, text: str):
        v = [0.0, 0.0, 0.0]
        for word, axis in self.AXES.items():
            if word in text.lower():
                v = [a + b for a, b in zip(v, axis)]
        return v if any(v) else [0.577, 0.577, 0.577]

    def embed(self, texts):
        return [self._vec(t) for t in texts]

    def embed_one(self, text):
        return self._vec(text)


def _world(store, summary: str) -> int:
    """Something it read, which evidence scope must still admit."""
    cur = store.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, source_ref,"
        " digest_eligible) VALUES (?, 'reading', 'world:arxiv', ?, ?, 1)",
        (time.time(), summary, "https://arxiv.org/abs/1"))
    store.commit()
    return int(cur.lastrowid)


def _embed(store, episode_id: int, text: str) -> None:
    store.execute("UPDATE episodes SET embedding=?, embedding_model=? WHERE id=?",
                  (pack(FakeEmbedder()._vec(text)), MODEL, episode_id))
    store.commit()


def test_a_work_never_surfaces_as_evidence_for_a_position(store):
    """E2.3's Done-when, and the regression test names the leak: v1 ranked its
    own probes as lived history. Consumer: newz/memory/retrieval.py's
    Scope.EVIDENCE. Behavior: the piece the being wrote is not returned when it
    is looking for something to ground a position in."""
    world_text = "Order-splitting degrades liquidity quality under stress."
    own_text = "On order-splitting: liquidity quality degrades under stress."
    world_id = _world(store, world_text)
    wid = record_self_output(store, kind="work", source_ref="work:1",
                             summary=own_text)
    _embed(store, world_id, world_text)
    _embed(store, wid, own_text)

    r = Retriever(store, FakeEmbedder())
    ev = [h.episode_id for h in r.search("order-splitting liquidity", scope=Scope.EVIDENCE)]
    everything = [h.episode_id for h in r.search("order-splitting liquidity", scope=Scope.ALL)]

    assert wid not in ev, "the being's own piece came back as evidence — the v1 leak"
    assert wid in everything, "containment, not erasure: it can still reach its own work"


def test_the_store_refuses_to_write_a_work_as_anything_but_self(store):
    """Consumer: 0032's trigger. Behavior: the exclusion does not depend on the
    next person to write a works-to-episodes bridge having read R-24.

    Works satisfy the rule today by ABSENCE — nothing bridges them — and E3.1
    and E3.2 make them first-class and visible. Absence is not a guarantee."""
    with pytest.raises(sqlite3.IntegrityError, match="provenance=self"):
        store.execute(
            "INSERT INTO episodes (ts, kind, provenance, summary, source_ref,"
            " digest_eligible) VALUES (?, 'work', 'world:me', ?, 'work:1', 0)",
            (time.time(), "a piece, mislabelled as the world"))


def test_the_store_refuses_to_make_a_work_digest_eligible(store):
    """R-24's other clause. Behavior: sleep can never digest the being's own
    output as lived experience — the mechanism by which v1's corpus became 43%
    self-probes."""
    with pytest.raises(sqlite3.IntegrityError, match="digest_eligible=0"):
        store.execute(
            "INSERT INTO episodes (ts, kind, provenance, summary, source_ref,"
            " digest_eligible) VALUES (?, 'work', 'self', ?, 'work:1', 1)",
            (time.time(), "a piece sleep would read as something that happened"))


def test_own_output_cannot_be_relabelled_into_evidence_later(store):
    """Behavior: the guard holds on UPDATE too, so a correctly-written episode
    cannot be quietly promoted into the evidence pool afterwards."""
    eid = record_self_output(store, kind="work", source_ref="work:1",
                             summary="a piece")

    with pytest.raises(sqlite3.IntegrityError, match="relabelled"):
        store.execute("UPDATE episodes SET provenance='world:arxiv' WHERE id=?", (eid,))


def test_revisions_and_the_error_record_are_the_same_trap(store):
    """R-24 binds all three: works, revisions and the error record. Behavior:
    each carries a source_ref the guard recognises."""
    assert is_self_output("work:12") and is_self_output("revision:3")
    assert is_self_output("claim:7") and is_self_output("advance:99")
    assert not is_self_output("https://arxiv.org/abs/1")

    for ref in ("revision:3", "claim:7"):
        with pytest.raises(sqlite3.IntegrityError):
            store.execute(
                "INSERT INTO episodes (ts, kind, provenance, summary,"
                " source_ref, digest_eligible) VALUES (?, 'x', 'world:a', ?, ?, 0)",
                (time.time(), "mislabelled", ref))


def test_the_helper_refuses_a_ref_that_is_not_the_beings_own(store):
    """Behavior: record_self_output is for own output only — using it to write
    a world episode as 'self' would be the leak running the other way."""
    with pytest.raises(ValueError, match="does not name the being's own output"):
        record_self_output(store, kind="reading", source_ref="https://arxiv.org/abs/1",
                           summary="something it read")
