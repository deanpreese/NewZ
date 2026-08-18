"""INV-030 — the being's autonomous life is episodic, and reaches it.

The regression these tests hold down is a live one, dated 2026-08-12. Asked
"What's new?" at 22:13 on a day that had written Perspective v4, advanced
concern 111, and read four sources, the being answered:

    "Nothing new. The architecture holds. I'm waiting for the world to get
    interesting enough to break the pattern."

It was not being modest. Deliberation, research, and concern advances wrote
only their own tables; sleep gathers from `episodes` and retrieval indexes
`episodes`, so none of it had any path back to the being — immediate or
nightly. The same context also produced a verbatim-identical reply to two
different questions six hours apart, which is what a context with no recent
life in it looks like from outside.
"""

import json

from newz.concerns.model import Concern
from newz.concerns.store import create_concern, record_advance, record_setback
from newz.conversation.composer import compose_reply, recent_life
from newz.gate.constitution import load_active_constitution
from newz.gate.outbound import OutboundGate
from newz.store.episodes import write_episode
from tests.conftest import FakeLLM

CLEAN = "<violation_check></violation_check>"


def _concern(store, statement="Does Montaigne anticipate Jung?") -> int:
    return create_concern(store, Concern(
        id=None, kind="inquiry", statement=statement,
        why_open="the resemblance keeps recurring and I cannot place it",
        closing_condition="I can state whether the link is lineage or structure",
        origin="curiosity", salience=0.6,
    ))


def test_an_advance_becomes_an_episode_sleep_can_gather(store):
    # Sleep's gather is `digest_eligible=1 AND consolidated_version IS NULL`.
    # An advance that misses it can never reach the Perspective.
    cid = _concern(store)
    record_advance(store, cid, summary="Not lineage but structural isomorphism.",
                   kind="reasoning", evidence=[], source_ref="deliberation")

    row = store.execute(
        "SELECT kind, provenance, summary, content_json, digest_eligible"
        " FROM episodes WHERE kind='advance'").fetchone()
    assert row is not None, "an advance that is not an episode cannot be slept on"
    assert row["digest_eligible"] == 1
    # The summary must stand alone: sleep and retrieval read it without the
    # dossier, so "I moved concern 7" would be unreadable to both.
    assert "Montaigne" in row["summary"]
    assert "structural isomorphism" in row["summary"]
    # Own conclusions are `self`, so INV-026's EVIDENCE scope keeps them from
    # returning later as evidence for themselves — the v1 leak.
    assert row["provenance"] == "self"
    assert json.loads(row["content_json"])["concern_id"] == cid


def test_a_setback_is_episodic_too_including_the_stall(store):
    # A being that records only its successes reports a life it did not have.
    cid = _concern(store)
    record_setback(store, cid, kind="blocked",
                   brief="no source distinguishes the two claims",
                   source_ref="deliberation")

    row = store.execute(
        "SELECT summary, provenance FROM episodes WHERE kind='setback'").fetchone()
    assert row is not None
    assert "could not move" in row["summary"]
    assert "no source distinguishes" in row["summary"]
    assert row["provenance"] == "self"


def test_a_concern_opening_is_episodic(store):
    cid = _concern(store, statement="Why does repetition feel like decay?")
    row = store.execute(
        "SELECT summary, content_json FROM episodes"
        " WHERE kind='concern_opened'").fetchone()
    assert row is not None
    assert "repetition feel like decay" in row["summary"]
    assert json.loads(row["content_json"])["concern_id"] == cid


def test_what_was_read_is_evidence_but_what_i_concluded_is_not(store):
    # The provenance split is the point: readings are `world:*` and may serve
    # as evidence later; the being's own advances are `self` and may not.
    write_episode(store, kind="reading", provenance="world:wikipedia",
                  summary="I read Collective unconscious (wikipedia).",
                  content={"claims": ["Jung posits inherited archetypes"]})
    record_advance(store, _concern(store), summary="They differ in kind.",
                   kind="reasoning", evidence=[])

    provenances = {r["kind"]: r["provenance"] for r in store.execute(
        "SELECT kind, provenance FROM episodes")}
    assert provenances["reading"] == "world:wikipedia"
    assert provenances["advance"] == "self"


def test_recent_life_orders_forwards_and_respects_its_window(store):
    import time

    now = time.time()
    for offset, summary in ((-5 * 86400, "ancient advance"),
                            (-7200, "recent advance"),
                            (-600, "very recent reading")):
        store.execute(
            "INSERT INTO episodes (ts, kind, provenance, summary, digest_eligible)"
            " VALUES (?,?,?,?,1)",
            (now + offset, "advance" if "advance" in summary else "reading",
             "self", summary))
    store.commit()

    life = recent_life(store)
    assert "ancient advance" not in life, "the window must not recite last week"
    # Oldest first — the day should read forwards.
    assert life.index("recent advance") < life.index("very recent reading")


def test_a_days_autonomous_life_reaches_the_next_conversation(store):
    """INV-030 consumer trace.

    Consumer: newz/conversation/composer.py. Observable behavior: a day of
    autonomous work appears in the VOICE prompt, so "what's new?" has a
    truthful answer available. This is the exact scenario of 2026-08-12.
    """
    cid = _concern(store)
    record_advance(store, cid, summary="Not lineage but structural isomorphism.",
                   kind="reasoning", evidence=[], source_ref="deliberation")
    write_episode(store, kind="reading", provenance="world:wikipedia",
                  summary="I read Collective unconscious (wikipedia) while "
                          "working on: Jung archetypes. It asserts: archetypes "
                          "are inherited.",
                  content={})
    write_episode(store, kind="consolidation", provenance="self",
                  summary="I slept and wrote Perspective v4: 2 new, 1 revised; "
                          "14 carried.",
                  content={}, digest_eligible=False)

    llm = FakeLLM([("VOICE", "Quite a lot, actually."), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    reply = compose_reply(store, llm, gate, "dean", "What's new?")

    assert reply.verdict == "pass"
    system = llm.calls[0]["system"]
    assert "since we last spoke" in system
    assert "structural isomorphism" in system      # what it worked out
    assert "Collective unconscious" in system      # what it read
    assert "Perspective v4" in system              # what its sleep did


def test_sleep_never_digests_its_own_consolidations(store):
    """The consolidation episode is deliberately not digest_eligible.

    Otherwise every night consolidates the fact that it consolidated, which
    is v1's accretion pathology in miniature — and the Perspective fills with
    its own bookkeeping.
    """
    write_episode(store, kind="consolidation", provenance="self",
                  summary="I slept and wrote Perspective v4: 2 new; 14 carried.",
                  content={}, digest_eligible=False)

    gatherable = store.execute(
        "SELECT COUNT(*) FROM episodes WHERE digest_eligible=1"
        " AND consolidated_version IS NULL AND kind='consolidation'"
    ).fetchone()[0]
    assert gatherable == 0
    # But it is still visible to the being.
    assert "Perspective v4" in recent_life(store)
