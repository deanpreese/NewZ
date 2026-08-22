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
    )
    f.update(kw)
    return (f"<commitment>"
            f"<worth_committing>{f['worth_committing']}</worth_committing>"
            f"<kind>{f['kind']}</kind>"
            f"<statement>{f['statement']}</statement>"
            f"<falsifier>{f['falsifier']}</falsifier></commitment>")


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
