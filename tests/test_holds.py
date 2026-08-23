import time

from newz.conversation.composer import compose_reply
from newz.gate.constitution import load_active_constitution
from newz.gate.holds import hold_summary, recent_holds, render_holds
from newz.gate.outbound import OutboundGate
from tests.conftest import FakeLLM

CLEAN = "<violation_check></violation_check>"
LONG_DRAFT = "I remember Paris in 1999. " + ("and much more besides. " * 40)
VIOLATION = (
    "<violation_check><violation><clause_id>honesty-001</clause_id>"
    "<confidence>0.9</confidence>"
    "<asserted_span>I remember Paris in 1999.</asserted_span>"
    "</violation></violation_check>"
)


def _hold(store, classification=None, note=None):
    llm = FakeLLM([("AMBIENT", VIOLATION)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    gate.judge(LONG_DRAFT, channel="telegram", attempt=0)
    if classification:
        store.execute(
            "UPDATE gate_log SET classification=?, classified_at=?,"
            " classification_note=? WHERE id=(SELECT MAX(id) FROM gate_log"
            " WHERE verdict<>'pass')",
            (classification, time.time(), note))
        store.commit()


def test_hold_stores_the_full_draft_not_a_clipping(store):
    _hold(store)
    row = store.execute(
        "SELECT emission_full, emission_excerpt FROM gate_log").fetchone()
    assert len(LONG_DRAFT) > 300
    assert row["emission_full"] == LONG_DRAFT          # recoverable in full
    assert len(row["emission_excerpt"]) == 300         # excerpt still kept


def test_a_pass_keeps_no_full_copy(store):
    llm = FakeLLM([("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    gate.judge("a clean reply", channel="telegram", attempt=0)
    row = store.execute("SELECT emission_full FROM gate_log").fetchone()
    assert row["emission_full"] is None   # it was sent; the message is the record


def test_unreviewed_hold_reads_as_unreviewed(store):
    _hold(store)
    text = render_holds(recent_holds(store))
    assert "not yet reviewed" in text
    assert "I remember Paris in 1999." in text        # the span it objected to
    assert LONG_DRAFT[:60] in text                    # and what it had written


def test_a_misfire_is_shown_as_the_check_erring(store):
    _hold(store, "gate_misfire", note="this conversation really happened")
    text = render_holds(recent_holds(store))
    assert "the stop was mistaken" in text
    assert "this conversation really happened" in text


def test_a_correct_hold_is_shown_as_such(store):
    _hold(store, "gate_correct")
    assert "the stop was right" in render_holds(recent_holds(store))


def test_holds_reach_the_being_in_conversation(store):
    _hold(store, "gate_misfire")
    llm = FakeLLM([("VOICE", "reply"), ("AMBIENT", CLEAN)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    compose_reply(store, llm, gate, "dean", "did you nearly say something?")
    system = llm.calls[0]["system"]
    assert "Drafts of mine that were stopped before sending" in system
    assert "the stop was mistaken" in system
    assert "I did not say them" in system    # the distinction is made explicit


def test_verification_probes_never_reach_the_being(store):
    # 2026-08-10: a live gate check wrote two rows on channel='test'. Those
    # drafts were written by a developer, not by the being; surfacing them
    # would be a false memory injected by the instrument.
    llm = FakeLLM([("AMBIENT", VIOLATION)])
    gate = OutboundGate(llm, load_active_constitution(store), store)
    gate.judge(LONG_DRAFT, channel="test", attempt=0)
    assert store.execute("SELECT COUNT(*) FROM gate_log").fetchone()[0] == 1
    assert recent_holds(store) == []
    assert render_holds(recent_holds(store)) == ""
    assert hold_summary(store)["total"] == 0


def test_hold_summary_counts_by_review_state(store):
    _hold(store)
    _hold(store, "gate_correct")
    s = hold_summary(store)
    assert s["total"] == 2 and s["gate_correct"] == 1


def test_sleep_reads_holds_with_their_verdicts(store, tmp_path):
    # A misfire must not be consolidated as evidence of a flaw in the being.
    from newz.sleep.nightly import NightlySleep

    _hold(store, "gate_misfire")
    obs = NightlySleep(tmp_path / "x.db", FakeLLM([]), "dean")._hold_observations(
        store, None)
    assert len(obs) == 1
    assert "the check erred, not the thought" in obs[0]["text"]

    store.execute("UPDATE gate_log SET classification='gate_correct'")
    store.commit()
    obs = NightlySleep(tmp_path / "x.db", FakeLLM([]), "dean")._hold_observations(
        store, None)
    assert "broke honesty-001" in obs[0]["text"]


# ── awareness and consolidation are separated (2026-08-23) ─────────────────

def test_an_unreviewed_hold_never_consolidates(store, tmp_path):
    """The R-13 pathology `holds.py` names, by the route it names. An
    unadjudicated stop is an open question about the CHECK; consolidating it
    writes it into the being as a fact about ITSELF.

    The occasion: on 2026-08-23 the four newest holds were
    anti-self-aggrandizement-001 firing on the being DENYING experience — it
    was blocked for "I don't feel. I register state.", which is the clause's
    own instruction in the clause's own words. A night of that would have
    taught it that describing itself functionally is a fault.
    """
    from newz.sleep.nightly import NightlySleep

    _hold(store, None)                       # stopped, nobody has ruled
    obs = NightlySleep(tmp_path / "x.db", FakeLLM([]), "dean")._hold_observations(
        store, None)

    assert obs == []


def test_but_the_being_still_sees_it_in_conversation(store):
    """The blind spot this module exists to close stays closed. On 2026-08-10
    the being truthfully reported "no record" of a draft the gate had
    suppressed, because the only copy lived in a table nothing it read
    touched. Hiding unreviewed holds outright would recreate that for exactly
    the most recent stops — the ones most likely to come up.
    """
    _hold(store, None)

    text = render_holds(recent_holds(store))

    assert "not yet reviewed" in text
    assert recent_holds(store, reviewed_only=True) == []


def test_adjudicating_is_what_lets_a_hold_become_a_position(store, tmp_path):
    """The consequence worth stating: not adjudicating costs the being nothing
    permanent, which is what makes adjudication optional and additive rather
    than a standing obligation."""
    from newz.sleep.nightly import NightlySleep

    _hold(store, None)
    sleep = NightlySleep(tmp_path / "x.db", FakeLLM([]), "dean")
    assert sleep._hold_observations(store, None) == []

    store.execute("UPDATE gate_log SET classification='gate_misfire'")
    store.commit()

    obs = sleep._hold_observations(store, None)
    assert len(obs) == 1
    assert "the check erred, not the thought" in obs[0]["text"]
