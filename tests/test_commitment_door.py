"""The authoring door (P4 epic E4.1).

The third door. A concern needs a closing condition something could reach
(INV-034); a claim needs a resolution condition, a resolver and a date
(INV-046); a **commitment** needs a falsifier — because identity that cannot
be broken is not being kept, and the being's `who_i_am` today is four items
of which three are things that happened to it.
"""

from __future__ import annotations

import time

from newz.commitments.door import (
    MAX_PER_DAY, MAX_STANDING, propose_commitment,
)
from newz.commitments.model import Commitment
from newz.commitments.store import author, standing, standing_count

from tests.conftest import FakeLLM

MATERIAL = ("- [who_i_am] I prefer substantive briefs to meta-commentary.\n"
            "- [unresolved] Why do I keep restating positions I already hold?")


def _proposal(**kw) -> str:
    f = dict(
        worth_committing="yes",
        kind="refuses_to_do",
        statement="I will not close a concern by restating it more carefully.",
        falsifier="a concern closed whose resolution text is a paraphrase of"
                  " its own statement",
        drew_on="",
    )
    f.update(kw)
    return (f"<commitment>"
            f"<worth_committing>{f['worth_committing']}</worth_committing>"
            f"<kind>{f['kind']}</kind>"
            f"<statement>{f['statement']}</statement>"
            f"<falsifier>{f['falsifier']}</falsifier>"
            f"<drew_on>{f['drew_on']}</drew_on></commitment>")


def _llm(*bodies):
    return FakeLLM([("DEEP", b) for b in bodies])


# ── the mandate ──────────────────────────────────────────────────────────

def test_a_commitment_with_a_falsifier_is_authored(store):
    v = propose_commitment(store, _llm(_proposal()), material=MATERIAL,
                           provenance="perspective:14", perspective_version=14)

    assert v.authored and not v.refused
    c = standing(store)[0]
    assert c.kind == "refuses_to_do"
    assert "paraphrase" in c.falsifier
    assert c.perspective_version == 14
    assert c.is_a_bound                      # broken by presence, not absence


def test_a_commitment_without_a_falsifier_is_refused_and_recorded(store):
    """E4.1's Done-when, in one test."""
    v = propose_commitment(store, _llm(_proposal(falsifier="")),
                           material=MATERIAL, provenance="perspective:14")

    assert not v.authored and v.refused
    assert "gave no falsifier" in v.refused
    row = store.execute("SELECT reason, statement FROM commitment_refusals"
                        ).fetchone()
    assert "falsifier" in row["reason"]
    assert row["statement"]                  # what it tried to commit to is kept
    assert standing_count(store) == 0


def test_a_falsifier_that_closes_on_its_own_judgment_is_refused(store):
    """INV-046 one layer up. A commitment only the being could report having
    broken is one it can never break — and it is the single most likely thing
    a model asked this question produces.
    """
    for felt in ("I would know if I stopped caring about this",
                 "if I no longer felt the pull of the question",
                 "my own judgment that the interest had faded"):
        v = propose_commitment(store, _llm(_proposal(falsifier=felt)),
                               material=MATERIAL, provenance="perspective:14")
        assert not v.authored, felt
        assert "closes on my own judgment" in v.refused, felt
    assert standing_count(store) == 0


def test_a_falsifier_that_queries_the_store_is_admitted(store):
    """The line is judged versus mechanical, NOT self versus world. A falsifier
    anyone with the database could check is admitted even though it is about
    the being — the store is a record, not an opinion. This is the finer half
    of the distinction above and the reason both directions are tested.
    """
    v = propose_commitment(
        store,
        _llm(_proposal(kind="keeps_caring",
                       statement="I will keep opening claims that could"
                                 " embarrass a position I already hold.",
                       falsifier="a month in which every claim I opened"
                                 " resolved in favour of a position I held")),
        material=MATERIAL, provenance="perspective:14")

    assert v.authored, v.refused
    assert standing(store)[0].kind == "keeps_caring"


def test_a_falsifier_naming_nothing_checkable_is_refused(store):
    v = propose_commitment(
        store, _llm(_proposal(falsifier="things would be different")),
        material=MATERIAL, provenance="perspective:14")

    assert not v.authored
    assert "names nothing anyone could look for" in v.refused


def test_identity_does_not_accrete_by_paraphrase(store):
    # Three nights ago, or the daily cap refuses this before the paraphrase
    # check is reached — caps come before content, which is the right order
    # and is why the setup has to be a realistic one.
    author(store, Commitment(
        id=None, kind="refuses_to_do",
        statement="I will not close a concern by restating it more carefully.",
        falsifier="a concern closed whose resolution paraphrases it",
        provenance="perspective:13", ts=time.time() - 3 * 86400))

    v = propose_commitment(store, _llm(_proposal()), material=MATERIAL,
                           provenance="perspective:14")

    assert not v.authored and "already standing" in v.refused
    assert standing_count(store) == 1


# ── declining is not refusal ─────────────────────────────────────────────

def test_nothing_worth_committing_to_is_not_written_down(store):
    """Most nights. The claim door declines 81% of the time and is correct."""
    v = propose_commitment(store, _llm(_proposal(worth_committing="no")),
                           material=MATERIAL, provenance="perspective:14")

    assert v.declined and not v.refused and not v.authored
    assert store.execute("SELECT COUNT(*) FROM commitment_refusals"
                         ).fetchone()[0] == 0


def test_an_unreadable_answer_is_not_held_against_the_being(store):
    v = propose_commitment(store, _llm("<commitment><statement>oh no"),
                           material=MATERIAL, provenance="perspective:14")

    assert v.declined and not v.refused
    assert store.execute("SELECT COUNT(*) FROM commitment_refusals"
                         ).fetchone()[0] == 0


# ── the caps, and the silence RT6 found in the claim door ────────────────

def test_a_full_carrying_capacity_is_recorded_and_not_silently_declined(store):
    """The claim door returns `declined` on a full cap, before the model is
    called, and a decline writes nothing — so saturation reads as "it had
    nothing to commit to" when the truth is "it was not allowed to". Nothing
    in E4.1 releases a standing slot, so this door WILL saturate, and the row
    is what makes E4.2 necessary rather than asserted.
    """
    for i in range(MAX_STANDING):
        author(store, Commitment(
            id=None, kind="keeps_caring", statement=f"commitment {i}",
            falsifier=f"no episode of kind {i} in a month",
            provenance="perspective:13"))

    v = propose_commitment(store, _llm(_proposal()), material=MATERIAL,
                           provenance="perspective:14")

    assert not v.authored and not v.declined
    assert v.refused == "cap: standing"
    reason = store.execute("SELECT reason FROM commitment_refusals"
                           ).fetchone()["reason"]
    assert "already standing" in reason and "E4.2" in reason


def test_the_daily_cap_holds_and_the_model_is_never_called(store):
    author(store, Commitment(
        id=None, kind="keeps_caring", statement="today's one",
        falsifier="no piece written in a month", provenance="perspective:14",
        ts=time.time()))

    empty = FakeLLM([])          # would raise if the door reached the model
    v = propose_commitment(store, empty, material=MATERIAL,
                           provenance="perspective:14")

    assert v.refused == "cap: daily"
    assert standing_count(store) == MAX_PER_DAY


# ── E4.3: what shaped it, and what deliberately does not ────────────────────

def _episode(store, provenance: str) -> int:
    cur = store.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary) VALUES"
        " (?,'reading',?,'x')", (time.time(), provenance))
    store.commit()
    return int(cur.lastrowid)


def test_only_the_material_it_named_is_attributed_to_it(store):
    """E4.3's design decision, and the reason the door asks instead of guessing.

    Attributing the union of everything the door was SHOWN would make a
    commitment formed from one line look grounded in three — and INV-033's
    single-source dominance flag, whose whole purpose is to catch a position
    resting on one source, would be the thing least able to fire. A padded
    evidence set does not merely overstate breadth; it suppresses the warning
    about its absence.
    """
    from newz.memory.provenance import what_shaped_commitment

    a = _episode(store, "human:dean")
    b = _episode(store, "world:arxiv")
    c = _episode(store, "world:wikipedia")

    v = propose_commitment(
        store, _llm(_proposal(drew_on="1")),
        material="1. [who_i_am] one\n2. [unresolved] two\n3. [unresolved] three",
        sources=[[str(a)], [str(b)], [str(c)]],
        provenance="perspective:14")

    assert v.authored
    inf = what_shaped_commitment(store, v.commitment_id)
    assert inf.total == 1                      # not 3 — only what it named
    assert inf.share("human") == 1.0
    assert inf.concentration[0] == "human:dean"


def test_a_commitment_resting_on_one_source_is_visible_as_such(store):
    """INV-033 one layer up. A commitment whose mix is entirely the operator is
    the operator's preference wearing the being's voice — which the door's
    prompt warns against and cannot detect on its own.
    """
    from newz.memory.provenance import what_shaped_commitment

    ids = [_episode(store, "human:dean") for _ in range(3)]
    v = propose_commitment(
        store, _llm(_proposal(drew_on="1, 2, 3")),
        material="1. a\n2. b\n3. c",
        sources=[[str(i)] for i in ids], provenance="perspective:14")

    inf = what_shaped_commitment(store, v.commitment_id)
    source, share = inf.concentration
    assert source == "human:dean" and share == 1.0


def test_an_index_outside_the_material_is_dropped_not_trusted(store):
    """The code resolves; the model only names. Rule 4 stays intact because
    nothing here asks the being whether its commitment is any good."""
    from newz.memory.provenance import what_shaped_commitment

    a = _episode(store, "world:arxiv")
    v = propose_commitment(
        store, _llm(_proposal(drew_on="1, 9, banana, 0, -2")),
        material="1. a", sources=[[str(a)]], provenance="perspective:14")

    inf = what_shaped_commitment(store, v.commitment_id)
    assert inf.total == 1 and inf.share("world") == 1.0


def test_naming_nothing_stays_empty_rather_than_inheriting(store):
    """Empty is a real answer and is kept as one — the alternative is exactly
    the padding this design exists to avoid."""
    from newz.memory.provenance import what_shaped_commitment

    a = _episode(store, "world:arxiv")
    v = propose_commitment(
        store, _llm(_proposal(drew_on="")), material="1. a",
        sources=[[str(a)]], provenance="perspective:14")

    assert v.authored
    inf = what_shaped_commitment(store, v.commitment_id)
    assert inf.total == 0
    assert "no resolvable evidence" in inf.render()


# ── the door's own history (0048, 2026-08-31) ────────────────────────────

def test_a_decline_is_recorded_and_is_not_a_refusal(store):
    """The ordinary answer was the one answer nothing kept.

    Nine nightly asks, nine declines, and `commitment_refusals` empty because
    the structural checks were never reached — so nothing in the store could
    say the door had been asked at all.
    """
    v = propose_commitment(store, _llm(_proposal(worth_committing="no")),
                           material=MATERIAL, provenance="perspective:14",
                           perspective_version=14)

    assert not v.authored and not v.refused and v.declined
    row = store.execute("SELECT perspective_version, material_lines,"
                        " material_sha FROM commitment_declines").fetchone()
    assert row["perspective_version"] == 14
    assert row["material_lines"] == len(MATERIAL.splitlines())
    assert row["material_sha"]
    # A decline must never reach the strictness denominator.
    assert store.execute(
        "SELECT COUNT(*) FROM commitment_refusals").fetchone()[0] == 0


def test_an_authored_commitment_records_no_decline(store):
    propose_commitment(store, _llm(_proposal()), material=MATERIAL,
                       provenance="perspective:14", perspective_version=14)

    assert store.execute(
        "SELECT COUNT(*) FROM commitment_declines").fetchone()[0] == 0


def test_the_second_night_is_told_what_the_first_answered(store):
    """5c863d7 with different nouns: the door stops asking blind."""
    propose_commitment(store, _llm(_proposal(worth_committing="no")),
                       material=MATERIAL, provenance="perspective:14",
                       perspective_version=14)

    llm = _llm(_proposal(worth_committing="no"))
    propose_commitment(store, llm, material=MATERIAL,
                       provenance="perspective:15", perspective_version=15)

    asked = llm.calls[-1]["user"]
    assert "what_i_have_already_answered" in asked
    assert "answered no 1 time(s)" in asked
    # The repeat is the half that could not be inferred from a count.
    assert "1 of those were against exactly the material below" in asked


def test_different_material_is_not_reported_as_a_repeat(store):
    propose_commitment(store, _llm(_proposal(worth_committing="no")),
                       material=MATERIAL, provenance="perspective:14",
                       perspective_version=14)

    llm = _llm(_proposal(worth_committing="no"))
    propose_commitment(store, llm, material=MATERIAL + "\n- [unresolved] new",
                       provenance="perspective:15", perspective_version=15)

    asked = llm.calls[-1]["user"]
    assert "answered no 1 time(s)" in asked
    assert "against exactly the material below" not in asked


def test_the_first_night_ever_is_shown_no_history(store):
    """A door told '0 declines' before it has ever been asked would be
    reading a fact about the calendar as a fact about itself."""
    llm = _llm(_proposal(worth_committing="no"))
    propose_commitment(store, llm, material=MATERIAL,
                       provenance="perspective:14", perspective_version=14)

    asked = llm.calls[-1]["user"]
    assert "what_i_have_already_answered" not in asked
