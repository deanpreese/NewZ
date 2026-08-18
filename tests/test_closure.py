"""S2 §8.4 — a concern can reach its own terminus.

Found missing by the coverage audit of 2026-08-13: no close path existed in
v2. All 17 `closed` concerns were import artifacts stamped 2026-08-08 by the
importer, and the only end v2 code could reach was `stalled` — 77 of 111.
P2 Phase 4.4 reads "closed concern -> position -> artifact -> gate ->
surface", so Phase 4 began from an event that could not occur.
"""

import json
import time

from newz.concerns.closure import judge_closure
from newz.concerns.model import Concern
from newz.concerns.store import (
    close_concern,
    create_concern,
    load_dossier,
    record_advance,
)
from newz.deliberation.lite import Deliberator
from newz.store.db import open_db
from tests.conftest import FakeLLM, LexicalEmbedder


def _closure(met="yes", position="Montaigne and Jung converge structurally, "
             "not by transmission.", resolution="Settled by dating the essays.",
             missing=""):
    return ("DEEP", f"""<closure>
  <met>{met}</met>
  <position>{position}</position>
  <resolution>{resolution}</resolution>
  <missing>{missing}</missing>
</closure>""")


def _concern(store, statement="Does Montaigne anticipate Jung?"):
    """A concern with no advances yet."""
    return create_concern(store, Concern(
        id=None, statement=statement, why_open="the resemblance recurs",
        closing_condition="I can state whether the link is lineage or structure",
        origin="curiosity"))


def _concern_with_advances(store, n=2):
    cid = create_concern(store, Concern(
        id=None, statement="Does Montaigne anticipate Jung?",
        why_open="the resemblance recurs",
        closing_condition="I can state whether the link is lineage or structure",
        origin="curiosity"))
    for i in range(n):
        record_advance(store, cid, summary=f"established point {i}",
                       kind="reasoning", evidence=[str(i + 1)])
    return cid


def test_a_met_condition_closes_the_concern_and_yields_a_position(store):
    cid = _concern_with_advances(store)
    v = judge_closure(FakeLLM([_closure()]), load_dossier(store, cid))
    assert v.closed and v.position and v.resolution

    close_concern(store, cid, position=v.position, resolution=v.resolution)
    c = load_dossier(store, cid).concern
    assert c.status == "closed" and c.closed_at and c.resolution


def test_closure_fails_closed_on_every_failure_mode(store):
    cid = _concern_with_advances(store)
    d = load_dossier(store, cid)

    # unparseable judge
    assert not judge_closure(FakeLLM([("DEEP", "not xml")]), d).closed
    # condition not met
    assert not judge_closure(FakeLLM([_closure(met="no", position="")]), d).closed
    # claims closure but yields no position — closes nothing S2 asks for
    assert not judge_closure(FakeLLM([_closure(position="")]), d).closed


def test_a_concern_with_nothing_established_is_not_even_asked(store):
    cid = _concern_with_advances(store, n=0)
    llm = FakeLLM([])                       # no model call may happen
    v = judge_closure(llm, load_dossier(store, cid))
    assert not v.closed and llm.calls == []


def test_a_concern_with_no_closing_condition_cannot_close(store):
    cid = create_concern(store, Concern(
        id=None, statement="An imported concern", why_open="x",
        closing_condition="", origin="curiosity"))
    for i in range(3):
        record_advance(store, cid, summary=f"point {i}", kind="reasoning", evidence=[])
    llm = FakeLLM([])
    assert not judge_closure(llm, load_dossier(store, cid)).closed
    assert llm.calls == []


def test_closing_writes_an_episode_carrying_the_position_and_evidence(store):
    # The position reaches the Perspective through sleep (INV-009), so it has
    # to survive on the episode with its grounding.
    cid = _concern_with_advances(store)
    close_concern(store, cid, position="A structural convergence.",
                  resolution="Settled by dating.")
    row = store.execute(
        "SELECT provenance, summary, content_json FROM episodes"
        " WHERE kind='concern_closed'").fetchone()
    assert row["provenance"] == "self"
    d = json.loads(row["content_json"])
    assert d["position"] == "A structural convergence."
    assert d["evidence"] == ["1", "2"]      # accumulated from its advances


def test_sleep_offers_a_closed_concerns_position_as_a_candidate(store):
    from newz.sleep.nightly import NightlySleep

    cid = _concern_with_advances(store)
    close_concern(store, cid, position="A structural convergence, not lineage.",
                  resolution="Settled by dating.")
    sleeper = NightlySleep.__new__(NightlySleep)
    obs = sleeper._closure_observations(store, None)
    assert len(obs) == 1
    assert obs[0]["text"] == "A structural convergence, not lineage."
    assert obs[0]["refs"] == ["1", "2"]     # arrives grounded


def test_deliberation_judges_closure_after_an_advance(tmp_path):
    from tests.test_deliberation import _reply, _store

    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="an earlier established point",
                   kind="reasoning", evidence=["1"])
    # Seeded history, not an attempt in this test's timeline (S2 §7.1 trigger).
    conn.execute("UPDATE concerns SET last_attempted_at=NULL")
    conn.commit()
    conn.close()

    llm = FakeLLM([_reply(), _closure()])
    r = Deliberator(path, llm, embedder=LexicalEmbedder()).run_once()
    assert r.moved and r.status_after == "closed"

    conn = open_db(path, read_only=True)
    assert load_dossier(conn, cid).concern.status == "closed"
    conn.close()


def test_a_failing_closure_judge_never_costs_the_advance(tmp_path):
    from tests.test_deliberation import _reply, _store

    path, (cid,) = _store(tmp_path)
    conn = open_db(path)
    record_advance(conn, cid, summary="an earlier point", kind="reasoning", evidence=[])
    conn.execute("UPDATE concerns SET last_attempted_at=NULL")
    conn.commit()
    conn.close()

    llm = FakeLLM([_reply(), ("DEEP", "not xml")])
    r = Deliberator(path, llm, embedder=LexicalEmbedder()).run_once()
    assert r.moved                            # the advance stands
    conn = open_db(path, read_only=True)
    assert load_dossier(conn, cid).concern.status == "open"
    conn.close()


# ── C1 / C2 (2026-08-14) ─────────────────────────────────────────────────

def test_what_was_read_counts_as_evidence(store):
    """C1. `evidence_refs()` could not contain anything the being had read.

    ingest_log has recorded concern_id since Phase 2.4 and was never read
    back, so a citation of a freshly-read source was relabelled from
    `evidence` to `reasoning` every time. Measured 2026-08-14: 99 claims
    read against named concerns, invisible to the check. v1 recorded 104
    evidence-class advances of 164; v2 recorded 1.
    """
    cid = _concern(store)
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined) VALUES (?,?,?,?,?,?,0)",
        (time.time(), "wikipedia",
         "wikipedia:https://en.wikipedia.org/wiki/Collective_unconscious",
         "jung archetypes", cid, 3))
    store.commit()

    d = load_dossier(store, cid)
    assert len(d.sources) == 1
    refs = d.evidence_refs()
    # Either label works, because a model will cite either.
    assert "src-1" in refs
    assert "https://en.wikipedia.org/wiki/Collective_unconscious" in refs


def test_the_being_can_see_what_it_read_in_order_to_cite_it(store):
    cid = _concern(store)
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined) VALUES (?,?,?,?,?,?,0)",
        (time.time(), "sec-edgar", "sec-edgar:https://sec.gov/x", "q", cid, 4))
    store.commit()
    rendered = load_dossier(store, cid).render()
    assert "what I have read on this" in rendered
    assert "[src-1] sec-edgar" in rendered
    assert "4 claims kept" in rendered


def test_a_read_that_kept_nothing_is_still_shown_honestly(store):
    cid = _concern(store)
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined) VALUES (?,?,?,?,?,0,0)",
        (time.time(), "arxiv", "arxiv:https://arxiv.org/abs/1", "q", cid))
    store.commit()
    assert "nothing usable kept" in load_dossier(store, cid).render()


def test_a_read_declined_by_the_share_cap_is_not_evidence(store):
    # skipped rows record accounting, not reading. The being never saw it.
    cid = _concern(store)
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined, skipped) VALUES (?,?,?,?,?,0,0,'share_cap')",
        (time.time(), "bbc", "bbc:https://bbc.co.uk/x", "q", cid))
    store.commit()
    assert load_dossier(store, cid).sources == []


def test_reads_for_another_concern_are_not_this_concern_s_evidence(store):
    mine = _concern(store, statement="Does Montaigne anticipate Jung?")
    other = _concern(store, statement="A different question entirely?")
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined) VALUES (?,?,?,?,?,2,0)",
        (time.time(), "openalex", "openalex:https://doi.org/x", "q", other))
    store.commit()
    assert load_dossier(store, mine).sources == []


def test_one_grounded_advance_is_enough_to_ask_whether_it_is_finished(store):
    """C2. A factual question answered by one good source can now close.

    Requiring two advances meant the judge was never consulted about the
    kind of question the being mostly carries — 8 of 9 open concerns are
    factual lookups, and there were 0 closures ever.
    """
    cid = _concern(store)
    record_advance(store, cid, summary="Established from the primary source.",
                   kind="evidence", evidence=["src-1"])
    llm = FakeLLM([_closure()])
    v = judge_closure(llm, load_dossier(store, cid))
    assert v.closed, "the judge was not even asked"
    assert llm.calls, "no DEEP call was made"


def test_a_concern_with_nothing_established_is_still_not_asked(store):
    # One advance is required; zero is still a floor, because a concern that
    # has established nothing cannot have met a closing condition.
    cid = _concern(store, statement="Nothing has moved here?")
    llm = FakeLLM([])
    assert not judge_closure(llm, load_dossier(store, cid)).closed
    assert llm.calls == []
