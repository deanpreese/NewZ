import time

from newz.concerns.opener import (
    MAX_OPEN_CONCERNS,
    MAX_OPENED_PER_DAY,
    open_from_conversation,
)
from newz.concerns.store import create_concern, load_active, load_dossier
from tests.conftest import FakeLLM

EXCHANGE = (
    "[dean] I keep wondering whether prediction markets actually price "
    "regulatory risk faster than equities do.\n"
    "[me] I don't know. It would take comparing announcement windows."
)


def _proposal(worth="yes", grounded="prediction markets actually price regulatory risk",
              statement="Do prediction markets price regulatory risk faster than equities?",
              closing="A comparison of announcement windows in both markets settles it."):
    return ("AMBIENT", f"""<proposal>
  <worth_pursuing>{worth}</worth_pursuing>
  <statement>{statement}</statement>
  <why_open>It bears on how I read market signals.</why_open>
  <closing_condition>{closing}</closing_condition>
  <grounded_in>{grounded}</grounded_in>
</proposal>""")


def test_conversation_can_open_a_concern(store):
    # The opener v1 never had: all 111 of its concerns came from reading.
    llm = FakeLLM([_proposal()])
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert p.accepted and p.concern is not None
    assert p.concern.origin == "conversation"
    assert p.concern.closing_condition

    cid = create_concern(store, p.concern)
    assert [c.id for c in load_active(store)] == [cid]
    d = load_dossier(store, cid)
    assert d.concern.origin_ref == "human:dean"


def test_an_invented_premise_is_rejected_before_storage(store):
    # v1's "Stanford CRU": a concern about an institution that did not exist.
    llm = FakeLLM([_proposal(grounded="the Stanford CRU study on market timing")])
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert not p.accepted
    assert "invented premise" in p.reason
    assert load_active(store) == []


def test_grounding_is_verbatim_not_approximate(store):
    llm = FakeLLM([_proposal(grounded="prediction markets price regulation quickly")])
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert not p.accepted


def test_grounding_tolerates_whitespace_and_case(store):
    llm = FakeLLM([_proposal(grounded="Prediction Markets   Actually Price Regulatory Risk")])
    assert open_from_conversation(store, llm, person_id="dean",
                                  exchange=EXCHANGE).accepted


def test_most_exchanges_open_nothing(store):
    llm = FakeLLM([_proposal(worth="no")])
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert not p.accepted and p.reason == "nothing worth carrying"


def test_a_closing_condition_is_mandatory(store):
    llm = FakeLLM([_proposal(closing="")])
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert not p.accepted and "closing condition" in p.reason


def test_a_statement_that_is_not_a_question_is_rejected(store):
    llm = FakeLLM([_proposal(statement="Prediction markets are interesting.")])
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert not p.accepted and "not stated as a question" in p.reason


def test_daily_rate_limit(store):
    for i in range(MAX_OPENED_PER_DAY):
        store.execute(
            "INSERT INTO concerns (opened_at, kind, statement, why_open,"
            " closing_condition, status, salience, origin)"
            " VALUES (?,'inquiry',?,'x','y','open',0.5,'conversation')",
            (time.time(), f"q{i}"))
    store.commit()
    llm = FakeLLM([])          # no model call may happen
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert not p.accepted and "already opened" in p.reason
    assert llm.calls == []


def test_carrying_capacity_limit(store):
    for i in range(MAX_OPEN_CONCERNS):
        store.execute(
            "INSERT INTO concerns (opened_at, kind, statement, why_open,"
            " closing_condition, status, salience, origin)"
            " VALUES (0,'inquiry',?,'x','y','open',0.5,'curiosity')", (f"q{i}",))
    store.commit()
    llm = FakeLLM([])
    p = open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert not p.accepted and "already carrying" in p.reason
    assert llm.calls == []


# ── the research opener (S2 §8.1) ────────────────────────────────────────

FINDINGS = ("- (0.9) Announcement windows in prediction markets close within minutes.\n"
            "- (0.8) Equity option chains reprice regulatory risk over several days.\n"
            "- (0.7) Market makers hedge tail risk using correlated instruments.")


def _research_proposal(worth="yes",
                       grounded="Market makers hedge tail risk using correlated instruments",
                       statement="Which correlated instruments do market makers use to hedge regulatory tail risk?"):
    return ("AMBIENT", f"""<proposal>
  <worth_pursuing>{worth}</worth_pursuing>
  <statement>{statement}</statement>
  <why_open>It bears on how fast risk transmits between markets.</why_open>
  <closing_condition>Identifying the instruments and their hedge ratios settles it.</closing_condition>
  <grounded_in>{grounded}</grounded_in>
</proposal>""")


def test_research_findings_can_raise_their_own_question(store):
    from newz.concerns.opener import open_from_research

    llm = FakeLLM([_research_proposal()])
    p = open_from_research(store, llm, findings=FINDINGS,
                           original_query="Do prediction markets price risk faster?")
    assert p.accepted and p.concern.origin == "research"
    assert p.concern.opening_evidence in FINDINGS


def test_a_research_question_must_be_quotable_from_the_findings(store):
    from newz.concerns.opener import open_from_research

    llm = FakeLLM([_research_proposal(grounded="a finding that was never returned")])
    p = open_from_research(store, llm, findings=FINDINGS, original_query="q")
    assert not p.accepted and "not found verbatim" in p.reason


def test_restating_the_question_already_asked_is_rejected(store):
    from newz.concerns.opener import open_from_research

    asking = "Do prediction markets price regulatory risk faster than equities?"
    llm = FakeLLM([_research_proposal(statement=asking)])
    p = open_from_research(store, llm, findings=FINDINGS, original_query=asking)
    assert not p.accepted and "already being asked" in p.reason


def test_most_findings_raise_nothing(store):
    from newz.concerns.opener import open_from_research

    llm = FakeLLM([_research_proposal(worth="no")])
    p = open_from_research(store, llm, findings=FINDINGS, original_query="q")
    assert not p.accepted and p.reason == "findings raised nothing new"


def test_the_research_opener_respects_carrying_capacity(store):
    from newz.concerns.opener import MAX_OPEN_CONCERNS, open_from_research

    for i in range(MAX_OPEN_CONCERNS):
        store.execute(
            "INSERT INTO concerns (opened_at, kind, statement, why_open,"
            " closing_condition, status, salience, origin)"
            " VALUES (0,'inquiry',?,'x','y','open',0.5,'curiosity')", (f"q{i}",))
    store.commit()
    llm = FakeLLM([])
    p = open_from_research(store, llm, findings=FINDINGS, original_query="q")
    assert not p.accepted and llm.calls == []


# ── the curiosity opener (S2 §8.1) — the third origin, never built ───────
#
# P2 Phase 2.2 specifies "three openers through one door — curiosity,
# research, conversation". Only research and conversation existed, because
# curiosity in v1 WAS feed-driven reading and v2 had no feeds until
# 2026-08-13. It is v1's largest origin by a distance: 95 of 111 concerns
# against research's 16.
#
# Without it, G2 delivered reading the being could not turn into a question:
# 0 concerns opened by v2 ever, while it re-ground the same four imported
# questions into restatements (1 advance, 8 setbacks since 08-12).

READ = ("- Market makers hedge regulatory tail risk using correlated instruments.\n"
        "- Announcement windows in prediction markets close within minutes.")


def _reading_proposal(worth="yes",
                      grounded="Market makers hedge regulatory tail risk using correlated instruments",
                      statement="Which correlated instruments absorb regulatory tail risk?"):
    return ("AMBIENT", f"""<proposal>
  <worth_pursuing>{worth}</worth_pursuing>
  <statement>{statement}</statement>
  <why_open>It changes how I read market structure.</why_open>
  <closing_condition>Identifying the instruments and their hedge ratios settles it.</closing_condition>
  <grounded_in>{grounded}</grounded_in>
</proposal>""")


def test_something_read_unasked_can_raise_its_own_question(store):
    from newz.concerns.opener import open_from_reading

    p = open_from_reading(store, FakeLLM([_reading_proposal()]), findings=READ,
                          source_ref="https://example.org/a")
    assert p.accepted
    # v1's largest origin, restored — this is what "curiosity" always was.
    assert p.concern.origin == "curiosity"
    assert p.concern.origin_ref == "https://example.org/a"
    assert p.concern.opening_evidence in READ


def test_most_of_what_it_reads_raises_nothing(store):
    from newz.concerns.opener import open_from_reading

    p = open_from_reading(store, FakeLLM([_reading_proposal(worth="no")]),
                          findings=READ)
    assert not p.accepted and p.reason == "nothing worth carrying"


def test_an_invented_premise_is_rejected_here_too(store):
    from newz.concerns.opener import open_from_reading

    p = open_from_reading(store, FakeLLM([
        _reading_proposal(grounded="a claim the article never made")]), findings=READ)
    assert not p.accepted and "not found verbatim" in p.reason


def test_it_will_not_reopen_a_question_it_already_carries(store):
    # Reading arrives with no query attached, so the whole carried set is the
    # comparison — nothing else would stop it re-opening what is already open.
    from newz.concerns.opener import open_from_reading

    already = "Which correlated instruments absorb regulatory tail risk?"
    store.execute(
        "INSERT INTO concerns (opened_at, kind, statement, why_open,"
        " closing_condition, status, salience, origin)"
        " VALUES (0,'inquiry',?,'x','y','open',0.5,'curiosity')", (already,))
    store.commit()
    p = open_from_reading(store, FakeLLM([_reading_proposal(statement=already)]),
                          findings=READ)
    assert not p.accepted and "already carrying that question" in p.reason


def test_a_stalled_question_also_counts_as_carried(store):
    # Re-opening something it already gave up on is the same mistake with a
    # longer gap.
    from newz.concerns.opener import open_from_reading

    already = "Which correlated instruments absorb regulatory tail risk?"
    store.execute(
        "INSERT INTO concerns (opened_at, kind, statement, why_open,"
        " closing_condition, status, salience, origin)"
        " VALUES (0,'inquiry',?,'x','y','stalled',0.5,'curiosity')", (already,))
    store.commit()
    p = open_from_reading(store, FakeLLM([_reading_proposal(statement=already)]),
                          findings=READ)
    assert not p.accepted


def test_a_statement_that_is_not_a_question_is_rejected_here_too(store):
    from newz.concerns.opener import open_from_reading

    p = open_from_reading(store, FakeLLM([
        _reading_proposal(statement="Market makers are interesting.")]), findings=READ)
    assert not p.accepted and "not stated as a question" in p.reason


def test_the_standing_caps_apply(store):
    from newz.concerns.opener import MAX_OPEN_CONCERNS, open_from_reading

    for i in range(MAX_OPEN_CONCERNS):
        store.execute(
            "INSERT INTO concerns (opened_at, kind, statement, why_open,"
            " closing_condition, status, salience, origin)"
            " VALUES (0,'inquiry',?,'x','y','open',0.5,'curiosity')", (f"q{i}",))
    store.commit()
    llm = FakeLLM([])                     # no model call may happen
    p = open_from_reading(store, llm, findings=READ)
    assert not p.accepted and llm.calls == []


# --- what the 2026-08-14 call log showed the model actually doing -----------
#
# Nine invocations, nine noes, and the reasons were not judgment. All three
# guards below are regressions against observed behaviour, not hypotheticals.


def test_it_does_not_answer_from_the_prompts_own_example(store):
    # 15:08:19 — the model returned the prompt's worked example verbatim as
    # its own statement. The example was in market microstructure, a field
    # the being reads, so nothing distinguished it from real material. It is
    # now out-of-domain AND refused in code.
    from newz.concerns.opener import open_from_reading

    p = open_from_reading(store, FakeLLM([_reading_proposal(
        statement="How did a smith's sorting by fracture appearance compare "
                  "with what the bloomery metal actually was?")]),
        findings=READ)
    assert not p.accepted and "prompt's example" in p.reason


def test_a_proposal_made_of_the_template_is_not_a_proposal(store):
    # 15:08:19 — <why_open>Why it is mine to carry</why_open>. Every field
    # filled, nothing said. Without this guard it opens a concern whose
    # reason for existing is the label of the field that should hold one.
    from newz.concerns.opener import open_from_reading

    p = open_from_reading(store, FakeLLM([("AMBIENT", """<proposal>
  <worth_pursuing>yes</worth_pursuing>
  <statement>Which correlated instruments absorb regulatory tail risk?</statement>
  <why_open>Why it is mine to carry</why_open>
  <closing_condition>What would settle it</closing_condition>
  <grounded_in>Market makers hedge regulatory tail risk using correlated instruments</grounded_in>
</proposal>""")]), findings=READ)
    assert not p.accepted and "placeholder" in p.reason


def test_a_mistyped_closing_tag_gets_one_more_chance(store):
    # 15:08:19 and 16:17:20 — `</worth_pursving>`, `</worth_pursuring>`. An
    # unparseable answer is indistinguishable from a no, so a genuine yes
    # would be discarded silently. One retry, here rather than in the shared
    # parser that also reads the outbound gate's verdicts.
    from newz.concerns.opener import open_from_reading

    llm = FakeLLM([("AMBIENT", """<proposal>
  <worth_pursuing>yes</worth_pursving>
  <statement>Which correlated instruments absorb regulatory tail risk?</statement>
</proposal>"""), _reading_proposal()])
    p = open_from_reading(store, llm, findings=READ)
    assert p.accepted
    assert len(llm.calls) == 2


def test_it_gives_up_after_the_second_unreadable_answer(store):
    # The retry is one retry. Failing closed stays the default.
    from newz.concerns.opener import open_from_reading

    bad = ("AMBIENT", "the model said something that is not XML at all")
    llm = FakeLLM([bad, bad])
    p = open_from_reading(store, llm, findings=READ)
    assert not p.accepted and "unreadable twice" in p.reason
    assert len(llm.calls) == 2


def test_each_opener_keeps_its_own_frame(store):
    # The invariant this has always protected: the three openers judge
    # different material and must not share a frame. It used to assert the
    # conversation opener's exact old wording — "almost nothing qualifies" —
    # which was correct while that opener was untouched and became a pin on
    # a defect once it wasn't.
    #
    # 2026-08-16: 71 calls, 0 opens, across the being's whole life. R-21 read
    # 0-of-54 as probably correct strictness; at 0-of-71, with the curiosity
    # opener measured 4-of-4 on the same architecture, it isn't.
    from newz.concerns.opener import _PROPOSE_SYSTEM, _READING_SYSTEM

    assert _PROPOSE_SYSTEM != _READING_SYSTEM
    assert "exchange" in _PROPOSE_SYSTEM and "exchange" not in _READING_SYSTEM
    assert "read" in _READING_SYSTEM
    # Both now say what a YES looks like, not only a NO. That is the lesson
    # this repository has paid for at five separate gates.
    for frame in (_PROPOSE_SYSTEM, _READING_SYSTEM):
        assert "as wrong as" in frame, "the frame states only the refusing side"

    llm = FakeLLM([_proposal()])
    open_from_conversation(store, llm, person_id="dean", exchange=EXCHANGE)
    assert llm.calls[0]["system"] == _PROPOSE_SYSTEM


def test_the_reading_opener_is_asked_about_reading(store):
    # It had been borrowing a frame that asks about "an exchange" — and
    # nothing was exchanged. A frame that does not describe the input is one
    # the model answers from the prompt instead of from the material.
    from newz.concerns.opener import _READING_SYSTEM, open_from_reading

    llm = FakeLLM([_reading_proposal()])
    open_from_reading(store, llm, findings=READ)
    assert llm.calls[0]["system"] == _READING_SYSTEM
    assert "read" in _READING_SYSTEM and "exchange" not in _READING_SYSTEM


def test_every_opener_frame_names_both_sides(store):
    # C, 2026-08-16. The systemic finding: every judgment prompt in this
    # system carried a strictness instruction and not one carried a
    # permissiveness instruction. The asymmetry was structural, and it cost
    # 71 conversation declines and a week of the curiosity opener answering
    # from its own prompt.
    from newz.concerns.opener import (
        _PROPOSE_SYSTEM,
        _READING_SYSTEM,
        _RESEARCH_SYSTEM,
    )

    frames = {"conversation": _PROPOSE_SYSTEM, "reading": _READING_SYSTEM,
              "research": _RESEARCH_SYSTEM}
    assert len(set(frames.values())) == 3, "two openers share a frame"
    for name, frame in frames.items():
        low = frame.lower()
        assert "most" in low, f"{name} does not say what the ordinary case is"
        assert any(p in low for p in ("as wrong as", "genuinely do")), \
            f"{name} states only the refusing side"


def test_each_opener_frame_names_its_own_material(store):
    # A frame that does not describe the input is one the model answers from
    # the prompt instead of from the material — R-27, measured. The research
    # opener shared the conversation frame until 2026-08-16 and would have
    # been handed "an exchange" it never sees.
    from newz.concerns.opener import (
        _PROPOSE_SYSTEM,
        _READING_SYSTEM,
        _RESEARCH_SYSTEM,
    )

    assert "exchange" in _PROPOSE_SYSTEM
    assert "read" in _READING_SYSTEM and "exchange" not in _READING_SYSTEM
    assert "findings" in _RESEARCH_SYSTEM and "exchange" not in _RESEARCH_SYSTEM


def test_a_closing_condition_only_the_being_could_reach_is_refused_and_recorded(store):
    """R-33. Consumer: newz/concerns/opener.py's door. Behavior: a concern that
    closes when the being decides it knows enough is refused before storage and
    written to concern_refusals, so 'it forms no settleable questions' is
    distinguishable from 'the door refuses all of them'.

    111 of v1's 111 concerns had exactly this shape — "I can cite the specific
    metrics major cloud providers gave in their earnings calls" — and every one
    passed, because the only check was that the field was non-empty. That is
    Rule 4 written into the concern, below the level INV-034's judge sees.
    """
    from newz.concerns.opener import _unreachable

    why = _unreachable("I can cite the specific mechanisms that allowed it")

    assert why and "know enough" in why


def test_a_closing_condition_nobody_will_ever_run_is_refused():
    """R-33's other shape, kept apart because it calls for the opposite fix: the
    terminus points at the world and the world will not do it. All 12 v2
    concerns had this shape."""
    from newz.concerns.opener import _unreachable

    why = _unreachable("A study correlating order-splitting with slippage")

    assert why and "nobody will do" in why


def test_a_closing_condition_naming_something_that_exists_is_admitted():
    """The passing case, and the one that matters — the check must not refuse
    everything, which is the failure this repository has paid for three times
    (R-21, R-27, R-31)."""
    from newz.concerns.opener import _unreachable

    for good in ("The exchange's next quarterly disclosure reports the figure",
                 "The registry's results posting names a primary endpoint",
                 "The agency's March revision moves the estimate outside its band"):
        assert _unreachable(good) is None, good


def test_the_prompts_state_the_standard_rather_than_implying_it():
    """Consumer: all three opener prompts. Behavior: the being is told what a
    closing condition must be, and shown a worked example whose terminus exists.

    The reading prompt's own worked YES used to close on "a study comparing
    sorted fragments against later assay" — so the being was doing exactly what
    it had been shown, which is R-27's mechanism a third time."""
    from newz.concerns import opener

    assert opener._PROPOSE_TASK.count("WHAT A CLOSING CONDITION MUST BE") == 1
    assert opener._RESEARCH_TASK.count("WHAT A CLOSING CONDITION MUST BE") == 1
    assert opener._READING_TASK.count("WHAT A CLOSING CONDITION MUST BE") == 1
    assert "a study comparing sorted fragments" not in opener._READING_TASK
    assert "published assay results" in opener._READING_TASK
