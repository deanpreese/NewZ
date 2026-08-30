"""A question that failed does not get asked in the same words (0046).

Measured 2026-08-30: 146 source gaps across 29 distinct questions, one asked
**17 times**, the next 14, 11, 10. In those passes 753 of 761 candidates were
refused by triage and 8 by the 0.35 floor, at an average best relevance of
0.578 — the material was topical and triage still declined it.

The mechanism was not strictness. `search_queries` derived terms from the
concern statement with no memory of a previous attempt, so the same statement
produced the same terms, the adapters returned the same ranked rows, R1's dedup
(2026-08-14) removed whatever had been read on pass one, and triage correctly
refused the tail. R1 fixed READING the same source sixteen times; this is
ASKING the same question seventeen times and reading nothing.

`tools/question_probe.py` established before any of this shipped that naming
the spent terms moves the search — 4 of 4 questions, with candidates the being
had never been offered — and found the one refinement that matters: told "not
those", the model drops the entity.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from newz.world.question import search_queries
from newz.world.research import (GAP_MEMORY_DAYS, MAX_TRIED_TERMS,
                                 _searches_that_failed)

DAY = 86400.0
Q = "How much of the decoupling between US yields and EM currency divergence?"


class _LLM:
    """Records the prompt it was given; returns two fixed queries."""

    def __init__(self):
        self.prompts: list[str] = []

    def complete(self, role, system, prompt, **kw):
        self.prompts.append(prompt)

        class R:
            text = "<queries><q>alpha beta</q><q>gamma delta</q></queries>"

        return R()


def _gap(store, query, searches, *, age_days=0.0, cause="triage"):
    store.execute(
        "INSERT INTO source_gaps (ts, concern_id, query, gap, cause, searches)"
        " VALUES (?,?,?,?,?,?)",
        (time.time() - age_days * DAY, None, query, "nothing relevant",
         cause, searches))
    store.commit()


# ── what was asked is now written down ───────────────────────────────────

def test_the_terms_that_failed_are_remembered(store):
    _gap(store, Q, "US yields EM decoupling\nglobal risk capital flows")

    assert _searches_that_failed(store, Q) == [
        "US yields EM decoupling", "global risk capital flows"]


def test_newest_first_and_deduplicated(store):
    _gap(store, Q, "old angle\nshared angle", age_days=3)
    _gap(store, Q, "new angle\nshared angle", age_days=0)

    got = _searches_that_failed(store, Q)

    assert got[0] == "new angle"
    assert got.count("shared angle") == 1


def test_another_question_is_not_borrowed_from(store):
    _gap(store, "a different question entirely", "someone else's terms")

    assert _searches_that_failed(store, Q) == []


def test_stale_gaps_are_forgotten(store):
    """Long enough for a question the being returns to for weeks; short enough
    that a genuinely new pass at an old subject is not told its angles are
    used up."""
    _gap(store, Q, "ancient angle", age_days=GAP_MEMORY_DAYS + 1)

    assert _searches_that_failed(store, Q) == []


def test_the_block_is_bounded(store):
    """More than this and the hint becomes most of the prompt."""
    for i in range(30):
        _gap(store, Q, f"angle {i}", age_days=i * 0.01)

    assert len(_searches_that_failed(store, Q)) == MAX_TRIED_TERMS


# ── and none of it may cost a research pass ──────────────────────────────

def test_a_store_without_the_column_is_silent(store):
    """A pre-0046 store returns nothing rather than raising: the memory is an
    improvement to a pass, never a precondition for one."""
    store.execute("DROP TABLE source_gaps")
    store.commit()

    assert _searches_that_failed(store, Q) == []


def test_no_store_and_no_query_are_both_empty():
    assert _searches_that_failed(None, Q) == []


# ── the prompt says the thing the probe had to find ─────────────────────

def test_the_failed_terms_reach_the_prompt(store):
    llm = _LLM()

    search_queries(llm, Q, tried=["US yields EM decoupling"])

    assert "already_tried" in llm.prompts[0]
    assert "US yields EM decoupling" in llm.prompts[0]


def test_without_failed_terms_the_prompt_is_unchanged(store):
    """A first pass must be exactly what it was before 0046."""
    llm = _LLM()

    search_queries(llm, Q)

    assert "already_tried" not in llm.prompts[0]


def test_the_prompt_insists_on_keeping_the_entity():
    """The probe's finding, and the reason it is worth a test rather than a
    comment. Asked for angles its terms had not covered, the model turned "EU
    Digital Services Act amplification definition" into "algorithmic
    transparency technical metrics" and best relevance fell 0.683 -> 0.590. It
    obeyed "different" by abandoning the subject."""
    import re

    from newz.world.question import _TASK, _TRIED

    # Whitespace-normalised: the prompt is prose and gets rewrapped, and a
    # test that fails on a line break trains its own bypass.
    flat = lambda t: re.sub(r"\s+", " ", t)

    assert "Keep the subject" in flat(_TRIED)
    assert "not a new angle, it is a new question" in flat(_TRIED)
    assert "Keep them even when asked for a new angle" in flat(_TASK), (
        "the base task must carry it too, or a first pass loses the rule")


def test_the_terms_are_a_hint_and_not_a_constraint(store):
    """The model may return a term it was told had failed. The floor and triage
    still decide what is read, and a query former that REFUSED to repeat could
    be walked away from the subject one pass at a time."""
    llm = _LLM()

    got = search_queries(llm, Q, tried=["alpha beta"])

    assert "alpha beta" in got
