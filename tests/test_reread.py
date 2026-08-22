"""Re-reading, revision and retraction (P4 epic E2.2).

Done-when: a piece is revised or retracted from a re-read, with the prior
version and the reason both retrievable. The tests below hold that clause and
the two failure modes P4's Phase 2 decision rule names — never revising (the
re-read is decorative) and revising everything (churn, not judgment).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.works.reread import due_for_reread, reread_once, starts_today

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
DAY = 86400.0


@pytest.fixture
def store(tmp_path):
    conn = open_db(tmp_path / "rr.db")
    apply_pending(conn, MAIN_SQL)
    conn.execute(
        "INSERT INTO works (ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.time() - 10 * DAY, "concern", 1, "Does the index roll over?",
         "I keep returning to it", "On rolling over",
         "The index is rolling over and the reason is structural.", 9,
         "qwen", 200))
    conn.commit()
    yield conn
    conn.close()


class FakeLLM:
    def __init__(self, verdict: str, body: str = "", reason: str = "the data went the other way"):
        self._v, self._b, self._r = verdict, body, reason

    def complete(self, role, system, user, **kw):
        class R:
            model = "fake"
            completion_tokens = 40
            truncated = False
            text = (f"<review><verdict>{self._v}</verdict>"
                    f"<reason>{self._r}</reason>"
                    f"<title>On rolling over, corrected</title>"
                    f"<body>{self._b}</body></review>")
        return R


def _revisions(conn):
    return conn.execute("SELECT * FROM work_revisions ORDER BY id").fetchall()


def test_a_retraction_keeps_the_piece_and_what_it_used_to_say(store):
    """E2.2's Done-when. Consumer: tools/read_works.py. Behavior: the work is
    marked retracted, the prior text and reason are retrievable, and nothing is
    removed — E1.5's rule at the claim layer, applied to the work."""
    r = reread_once(store, FakeLLM("retract"))

    assert r.kind == "retracted"
    work = store.execute("SELECT status, body FROM works").fetchone()
    assert work["status"] == "retracted"
    assert work["body"], "a retracted piece still says what it said"

    rev = _revisions(store)[0]
    assert rev["kind"] == "retracted"
    assert rev["reason"] == "the data went the other way"
    assert rev["prior_body"].startswith("The index is rolling over")


def test_a_revision_keeps_the_prior_version_and_the_reason(store):
    """E2.2's Done-when for the other outcome. Behavior: the piece now says
    something else, and what it used to say is still readable beside it."""
    r = reread_once(store, FakeLLM("revise", body="It is not rolling over. I read the base effect wrong."))

    assert r.kind == "revised"
    work = store.execute("SELECT status, title, body FROM works").fetchone()
    assert work["status"] == "standing"
    assert work["title"] == "On rolling over, corrected"
    assert work["body"].startswith("It is not rolling over")

    rev = _revisions(store)[0]
    assert rev["kind"] == "revised"
    assert rev["prior_body"].startswith("The index is rolling over")
    assert rev["reason"]


def test_standing_is_the_ordinary_answer_and_writes_no_revision(store):
    """Consumer: P4 Phase 2's decision rule. Behavior: a piece that still holds
    is marked reviewed and nothing is rewritten — a re-read that revised
    everything would be churn, not judgment."""
    r = reread_once(store, FakeLLM("stands"))

    assert r.kind == "stands"
    assert _revisions(store) == []
    assert store.execute("SELECT last_reviewed_at FROM works").fetchone()[0]


def test_revise_with_no_new_text_is_recorded_as_standing(store):
    """Behavior: a verdict the being could not act on does not become a
    revision. Otherwise the decision rule reads "it revises" from a piece that
    was never rewritten."""
    r = reread_once(store, FakeLLM("revise", body=""))

    assert r.kind == "stands"
    assert _revisions(store) == []


def test_a_retracted_piece_and_its_history_cannot_be_deleted(store):
    """Consumer: 0031's triggers. Behavior: retraction is an outcome, never a
    deletion — the store refuses both, so a piece cannot be quietly unwritten."""
    reread_once(store, FakeLLM("retract"))

    with pytest.raises(sqlite3.IntegrityError, match="retracted, never deleted"):
        store.execute("DELETE FROM works")
    with pytest.raises(sqlite3.IntegrityError, match="not deletable"):
        store.execute("DELETE FROM work_revisions")


def test_a_piece_is_not_re_read_until_it_is_old_enough(store):
    """Behavior: re-reading yesterday's work is proofreading. The point is to
    meet it as something written by someone else."""
    store.execute("UPDATE works SET ts=?", (time.time() - 3600,))
    store.commit()

    assert due_for_reread(store) is None
    assert reread_once(store, FakeLLM("retract")).skipped


def test_the_reread_ceiling_counts_starts(store):
    """R-25 again, on its own cap: writing and re-reading share one attempt
    ledger and are budgeted separately.

    **Amended 2026-08-22, and the assertion it replaces was the defect.** This
    read `starts_today(store) >= 2` after two calls, of which only the first
    began anything — the second found the piece freshly reviewed and recorded
    `nothing_due`. So the old assertion passed on a ceiling that counted a turn
    which started nothing, and the being sat out three consecutive re-reads for
    it. R-25 caps "deliberations started per day, not completed"; a turn that
    found no work started nothing."""
    store.execute(
        "INSERT INTO works (ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.time() - 10 * DAY, "concern", 2, "And does it settle?",
         "it keeps returning", "On settling", "It settles, slowly.", 4,
         "qwen", 200))
    store.commit()

    for _ in range(2):                       # two due pieces, two real starts
        reread_once(store, FakeLLM("stands"))

    assert starts_today(store) == 2
    assert reread_once(store, FakeLLM("stands")).skipped
    assert store.execute(
        "SELECT COUNT(*) FROM work_attempts WHERE kind='write'").fetchone()[0] == 0


def test_a_reread_that_found_nothing_due_does_not_spend_the_day(store):
    """The turn that produced the amendment above. Behavior: `nothing_due` is
    recorded — so a rhythm with nothing to do is visible rather than looking
    like one that never ran — and it does not count against the ceiling."""
    store.execute("UPDATE works SET ts=?", (time.time() - 3600,))
    store.commit()

    assert reread_once(store, FakeLLM("stands")).skipped
    assert store.execute(
        "SELECT outcome FROM work_attempts ORDER BY id DESC LIMIT 1"
    ).fetchone()[0] == "nothing_due"
    assert starts_today(store) == 0
