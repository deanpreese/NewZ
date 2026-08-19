import json

import pytest

from newz.sleep.nightly import NightlySleep
from newz.sleep.perspective import Item, load_items, save_items
from newz.store.db import open_db
from newz.store.migrations import apply_pending
from tests.conftest import CONSTITUTION_YAML, FakeLLM
from tests.test_migrations import MAIN_SQL

DIGEST = ("DEEP", """<digest>
  <observation refs="1,2">I kept returning to how my memory actually works.</observation>
  <observation refs="3">I declined to invent a citation I could not find.</observation>
</digest>""")


def _sleep_store(tmp_path, episodes, items=None):
    """A store on disk (sleep opens its own connection to a path)."""
    path = tmp_path / "newz.db"
    conn = open_db(path)
    apply_pending(conn, MAIN_SQL)
    conn.execute(
        "INSERT INTO constitution (version, ts, clauses_yaml, change_summary,"
        " approval_status) VALUES (1, 1.0, ?, 'test', 'active')", (CONSTITUTION_YAML,))
    conn.execute(
        "INSERT INTO perspective (version, ts, content, diff_json, token_count)"
        " VALUES (1, 1.0, '# Perspective v1', '{}', 10)")
    for i, (summary, prov) in enumerate(episodes, start=1):
        conn.execute(
            "INSERT INTO episodes (id, ts, kind, provenance, summary, digest_eligible,"
            " consolidated_version) VALUES (?,?,?,?,?,1,NULL)",
            (i, 100.0 + i, "conversation", prov, summary))
    if items:
        save_items(conn, 1, items)
    conn.commit()
    conn.close()
    return path


EPISODES = [("dean asked how my memory works", "human:dean"),
            ("I explained the thread window", "human:dean"),
            ("I declined to invent a citation", "human:dean")]


def test_sleep_writes_v2_and_marks_episodes_consolidated(tmp_path):
    path = _sleep_store(tmp_path, EPISODES)
    llm = FakeLLM([DIGEST, ("DEEP", """<confrontation>
        <verdict candidate="1" type="new" section="who_i_am">I am curious about my own mechanics.</verdict>
        <verdict candidate="2" type="none"/>
    </confrontation>""")])
    report = NightlySleep(path, llm, "dean").run()

    assert report.version == 2
    assert report.gathered == 3
    conn = open_db(path, read_only=True)
    row = conn.execute("SELECT content, diff_json, token_count FROM perspective"
                       " WHERE version=2").fetchone()
    assert "I am curious about my own mechanics." in row["content"]
    diff = json.loads(row["diff_json"])
    assert diff["added"] == ["I am curious about my own mechanics."]
    assert diff["method"].startswith("computed")
    # Every gathered episode is marked, so the next night does not re-read it.
    assert conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE consolidated_version=2").fetchone()[0] == 3
    conn.close()


def test_second_run_finds_nothing_and_writes_nothing(tmp_path):
    path = _sleep_store(tmp_path, EPISODES)
    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation></confrontation>")])
    NightlySleep(path, llm, "dean").run()
    second = NightlySleep(path, FakeLLM([]), "dean").run()
    assert second.version is None
    assert second.skipped_reason == "nothing new to consolidate"
    conn = open_db(path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM perspective").fetchone()[0] == 2
    conn.close()


def test_confrontation_reinforces_and_revises_held_positions(tmp_path):
    held = [Item(section="what_i_hold", text="My memory is unreliable.",
                 evidence=["9"], confidence=0.6, status="carried"),
            Item(section="who_i_am", text="I refuse to fabricate.",
                 evidence=["8"], confidence=0.6, status="carried")]
    path = _sleep_store(tmp_path, EPISODES, items=held)
    llm = FakeLLM([DIGEST, ("DEEP", """<confrontation>
      <verdict candidate="1" type="revises" item="1">My memory is bounded, not unreliable.</verdict>
      <verdict candidate="2" type="reinforces" item="2"/>
    </confrontation>""")])
    report = NightlySleep(path, llm, "dean").run()

    conn = open_db(path, read_only=True)
    items = load_items(conn, 2)
    texts = {i.text: i for i in items}
    assert "My memory is bounded, not unreliable." in texts
    assert "My memory is unreliable." not in texts        # superseded
    revised = texts["My memory is bounded, not unreliable."]
    assert revised.status == "revised" and revised.prior_item_id is not None

    reinforced = texts["I refuse to fabricate."]
    assert reinforced.confidence > 0.6                     # supported tonight
    assert "3" in reinforced.evidence                      # and the ref accrued
    assert report.diff["revised"] == [
        "My memory is unreliable. -> My memory is bounded, not unreliable."]
    conn.close()


def test_contradiction_opens_an_unresolved_entry(tmp_path):
    held = [Item(section="what_i_hold", text="I always cite sources.",
                 evidence=["9"], confidence=0.6, status="carried")]
    path = _sleep_store(tmp_path, EPISODES, items=held)
    llm = FakeLLM([DIGEST, ("DEEP", """<confrontation>
      <verdict candidate="2" type="contradicts" item="1">I claim to always cite, but I declined to produce one.</verdict>
    </confrontation>""")])
    report = NightlySleep(path, llm, "dean").run()
    conn = open_db(path, read_only=True)
    unresolved = [i for i in load_items(conn, 2) if i.section == "unresolved"]
    assert len(unresolved) == 1
    assert report.diff["contradictions_opened"] == 1
    conn.close()


def test_a_night_that_changes_nothing_reports_zero_novelty(tmp_path):
    held = [Item(section="what_i_hold", text=t, evidence=["9"],
                 confidence=0.6, status="carried") for t in (
        "Open-weight models shift advantage toward reliability engineering.",
        "Prediction markets reprice regulatory risk faster than equity chains.",
        "Consolidation is what turns experience into a usable perspective.")]
    path = _sleep_store(tmp_path, EPISODES, items=held)
    llm = FakeLLM([DIGEST, ("DEEP", """<confrontation>
      <verdict candidate="1" type="none"/><verdict candidate="2" type="none"/>
    </confrontation>""")])
    report = NightlySleep(path, llm, "dean").run()
    assert report.diff["novelty_rate"] == 0.0
    assert report.diff["carried"] == 3


def test_failed_digest_loses_the_night_and_nothing_else(tmp_path):
    path = _sleep_store(tmp_path, EPISODES)

    class Exploding:
        def complete(self, *a, **k):
            raise RuntimeError("endpoint down")

    report = NightlySleep(path, Exploding(), "dean").run()
    assert report.version is None
    conn = open_db(path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM perspective").fetchone()[0] == 1
    # Episodes stay unconsolidated, so tomorrow picks them up.
    assert conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE consolidated_version IS NULL"
    ).fetchone()[0] == 3
    conn.close()


def test_compression_releases_the_least_supported(tmp_path):
    topics = ["monetary policy transmission lags across credit channels",
              "improvisation structure in live performance traditions",
              "regulatory arbitrage in prediction market venues",
              "grounding claims against episodic evidence over time",
              "compression as a forcing function for what is held",
              "attention allocation under competing open questions"]
    held = [Item(section="what_i_hold", text=f"{t} " + "detail " * 60,
                 evidence=["9"] if i else [], confidence=0.9 if i else 0.3,
                 status="carried") for i, t in enumerate(topics)]
    path = _sleep_store(tmp_path, EPISODES, items=held)
    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation></confrontation>")])
    report = NightlySleep(path, llm, "dean", budget=300).run()
    assert report.compressed > 0
    conn = open_db(path, read_only=True)
    kept = [i.text for i in load_items(conn, 2)]
    assert not any(t.startswith("monetary policy") for t in kept)  # weakest went first
    conn.close()


def test_scheduler_fires_once_per_day_after_the_hour(tmp_path):
    import datetime as dt

    from newz.sleep.nightly import SleepScheduler

    path = _sleep_store(tmp_path, EPISODES)   # perspective v1 dated 1970
    sched = SleepScheduler(path, FakeLLM([]), "dean", hour=3)

    assert not sched._due(dt.datetime(2026, 8, 11, 1, 0))   # before the hour
    assert sched._due(dt.datetime(2026, 8, 11, 4, 0))       # after, nothing today

    conn = open_db(path)
    conn.execute(
        "INSERT INTO perspective (version, ts, content, diff_json, token_count)"
        " VALUES (2, ?, 'x', '{}', 1)",
        (dt.datetime(2026, 8, 11, 3, 30).timestamp(),))
    conn.commit()
    conn.close()
    # Already consolidated today — one night, one sleep.
    assert not sched._due(dt.datetime(2026, 8, 11, 22, 0))
    # Tomorrow it is due again.
    assert sched._due(dt.datetime(2026, 8, 12, 3, 5))


def test_sleep_does_not_publish_the_loops_partial_work(tmp_path):
    # The verified defect (RISKS R-14): on a SHARED connection, sleep's
    # commit would publish whatever the conversation path had in flight.
    # With its own connection it cannot.
    path = _sleep_store(tmp_path, EPISODES)
    loop_conn = open_db(path)
    loop_conn.execute(
        "INSERT INTO messages (ts, channel, direction, person_id, content)"
        " VALUES (1.0,'telegram','in','dean','in flight, never committed')")
    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation></confrontation>")])
    NightlySleep(path, llm, "dean").run()
    loop_conn.rollback()          # the loop's work is discarded, as intended
    loop_conn.close()

    other = open_db(path, read_only=True)
    assert other.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
    other.close()


def test_a_busy_store_costs_the_night_and_nothing_more(tmp_path):
    # R-17 from the other side: the loop holds the write lock. Sleep must
    # yield cleanly — no exception, no partial version, episodes preserved.
    path = _sleep_store(tmp_path, EPISODES)
    holder = open_db(path, busy_timeout_ms=100)
    holder.execute("INSERT INTO episodes (ts, kind, provenance, summary)"
                   " VALUES (1.0,'conversation','human:dean','holding the lock')")

    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation></confrontation>")])
    report = NightlySleep(path, llm, "dean").run()   # must not raise

    assert report.version is None
    assert "busy" in (report.skipped_reason or "")
    holder.rollback()
    holder.close()

    conn = open_db(path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM perspective").fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM episodes WHERE consolidated_version IS NULL"
    ).fetchone()[0] == 3          # tomorrow picks them up
    conn.close()


# ── contradiction must cost the position it contradicts ──────────────────
#
# Measured 2026-08-12. "I experienced prolonged periods of total prefix cache
# inefficiency" sat first in "who I am" at 0.72 while three consecutive
# nights each filed a fresh tension against it, and none of them touched it.
# The being then told the operator its state of health was "the cache is
# clear, retrieval is sharp" — reciting a self-model that its own sleep had
# contradicted three times. Filing a tension is not confronting a position.

CONTRADICTS = ("DEEP", """<confrontation>
  <verdict candidate="1" type="contradicts" item="1">The stability I observe conflicts with the inefficiency I hold.</verdict>
</confrontation>""")


def _held_position(text="I experience total cache inefficiency.", confidence=0.72):
    return [Item(section="who_i_am", text=text, evidence=["9"],
                 confidence=confidence, status="carried")]


def test_a_contradiction_costs_the_position_it_contradicts(tmp_path):
    path = _sleep_store(tmp_path, EPISODES, items=_held_position())
    report = NightlySleep(path, FakeLLM([DIGEST, CONTRADICTS]), "dean").run()

    conn = open_db(path, read_only=True)
    held = [i for i in load_items(conn, 2) if i.section == "who_i_am"][0]
    assert held.confidence == 0.57          # 0.72 - CONFIDENCE_ON_CONTRADICT
    assert held.status == "disputed"
    # A direct read off the diff (INV-023), not something to excavate.
    assert report.diff["disputed"] == [held.text]
    # The contradicting evidence must NOT become support for the claim.
    assert held.evidence == ["9"]
    conn.close()


def test_the_world_s_refutation_reaches_the_position_during_sleep(tmp_path):
    """E1.4's wiring. INV-009 keeps sleep the only writer of the Perspective,
    so the cost has to land here — and between confrontation and decay, so the
    ordinary release floor carries out anything it takes under."""
    import time as _t

    from newz.resolutions.model import Claim
    from newz.resolutions.store import open_claim, settle_claim

    held = "Reported open interest overstates collateralised positions."
    path = _sleep_store(tmp_path, EPISODES, items=[
        Item(section="what_i_hold", text=held, evidence=["4"], confidence=0.6,
             status="carried", first_seen_version=1)])
    conn = open_db(path)
    conn.execute(
        "INSERT INTO episodes (id, ts, kind, provenance, summary, source_ref,"
        " digest_eligible, consolidated_version)"
        " VALUES (4, 104.0, 'advance', 'self', 'I established it.',"
        " 'concern:7', 1, 1)")
    cid = open_claim(conn, Claim(
        id=None, claim="The COT report will print 10% below.",
        resolution_condition="The release is published and compared.",
        resolver="CFTC Commitments of Traders weekly report",
        due_at=_t.time() - 86400, provenance="concern:7"), models=set())
    settle_claim(conn, cid, outcome="contradicted",
                 settled_by="https://cftc.gov/cot", note="It printed above.")
    conn.commit()
    conn.close()

    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation>"
                            "<verdict candidate=\"1\" type=\"none\"/>"
                            "<verdict candidate=\"2\" type=\"none\"/>"
                            "</confrontation>")])
    report = NightlySleep(path, llm, "dean").run()

    assert report.world_costs == 1
    conn = open_db(path, read_only=True)
    item = [i for i in load_items(conn, report.version) if i.text == held][0]
    assert item.confidence == 0.45 and item.status == "disputed"
    cost = conn.execute("SELECT claim_id, released FROM claim_costs").fetchone()
    assert cost["claim_id"] == cid and not cost["released"]
    conn.close()


def test_a_repeated_contradiction_costs_double_and_eventually_releases(tmp_path):
    # The tension already stands in `unresolved`, so tonight's filing
    # restates it: the position is failing, not having one odd night.
    items = _held_position(confidence=0.6) + [
        Item(section="unresolved",
             text="The stability I observe conflicts with the inefficiency I hold.",
             evidence=["8"], confidence=0.6, status="carried")]
    path = _sleep_store(tmp_path, EPISODES, items=items)
    # Items are numbered in (section, id) order, so `unresolved` is 1 and the
    # held position is 2.
    contradicts_held = ("DEEP", """<confrontation>
      <verdict candidate="1" type="contradicts" item="2">The stability I observe conflicts with the inefficiency I hold.</verdict>
    </confrontation>""")
    report = NightlySleep(path, FakeLLM([DIGEST, contradicts_held]), "dean").run()

    conn = open_db(path, read_only=True)
    remaining = [i for i in load_items(conn, 2) if i.section == "who_i_am"]
    # 0.6 - CONFIDENCE_ON_REPEAT_CONTRADICT = 0.30, still above RELEASE_BELOW.
    assert remaining and remaining[0].confidence == 0.30
    # And the tension was reinforced rather than cloned for a second time.
    unresolved = [i for i in load_items(conn, 2) if i.section == "unresolved"]
    assert len(unresolved) == 1
    conn.close()

    # A further repeat drops it under the floor and the existing release
    # machinery lets it go — nothing new deletes items. (A night needs
    # unconsolidated episodes or sleep correctly skips it.)
    # Offer the same episodes again rather than new ones: the digest stub
    # cites refs 1-3, and observations citing episodes outside the night's
    # gather are dropped as ungrounded.
    conn = open_db(path)
    conn.execute("UPDATE episodes SET consolidated_version=NULL WHERE id<=3")
    conn.commit()
    conn.close()

    report2 = NightlySleep(path, FakeLLM([DIGEST, contradicts_held]), "dean").run()
    conn = open_db(path, read_only=True)
    assert [i for i in load_items(conn, 3) if i.section == "who_i_am"] == []
    assert any("cache inefficiency" in t for t in report2.diff["released"])
    conn.close()


def test_a_dispute_persists_across_nights_until_something_settles_it(tmp_path):
    # The earlier version of this test asserted only that `disputed` was gone
    # after a reinforcing night — which passed because _confront reset EVERY
    # item to "carried" on entry. It tested the reset, not the mechanism.
    # This one pins both halves: dispute survives an uneventful night, and
    # support is what clears it.
    items = _held_position(confidence=0.4)
    items[0].status = "disputed"
    path = _sleep_store(tmp_path, EPISODES, items=items)

    quiet = ("DEEP", """<confrontation>
      <verdict candidate="1" type="none"/>
    </confrontation>""")
    NightlySleep(path, FakeLLM([DIGEST, quiet]), "dean").run()
    conn = open_db(path, read_only=True)
    held = [i for i in load_items(conn, 2) if i.section == "who_i_am"][0]
    assert held.status == "disputed", "a standing dispute must not lapse silently"
    conn.close()

    conn = open_db(path)
    conn.execute("UPDATE episodes SET consolidated_version=NULL WHERE id<=3")
    conn.commit()
    conn.close()

    supports = ("DEEP", """<confrontation>
      <verdict candidate="1" type="reinforces" item="1"></verdict>
    </confrontation>""")
    NightlySleep(path, FakeLLM([DIGEST, supports]), "dean").run()
    conn = open_db(path, read_only=True)
    held = [i for i in load_items(conn, 3) if i.section == "who_i_am"][0]
    assert held.status != "disputed"      # support clears it
    assert held.confidence > 0.4
    conn.close()


def test_a_merged_contradiction_is_not_a_closed_one(tmp_path):
    # v5 reported 3 contradictions closed on a night that resolved nothing:
    # three duplicate tensions were merged away, and the count read any
    # vanished `unresolved` item as a closure. Evidence 1-E reads this.
    from newz.sleep.perspective import Diff, Item as It, compute_diff

    before = [It(section="unresolved", text="A tension about cache misses.",
                 evidence=["1"], confidence=0.6, status="carried", id=1),
              It(section="unresolved", text="A tension re cache misses.",
                 evidence=["2"], confidence=0.6, status="carried", id=2)]
    # Item 2 merged into item 1; nothing was resolved.
    after = [It(section="unresolved", text="A tension about cache misses.",
                evidence=["1", "2"], confidence=0.66, status="merged", id=1)]
    assert compute_diff(before, after).contradictions_closed == 0

    # Whereas a tension SUPERSEDED by a revision is genuinely closed.
    resolved = [It(section="what_i_hold", text="Cache behaviour is stable now.",
                   evidence=["1"], confidence=0.6, status="revised",
                   prior_item_id=1)]
    assert compute_diff(before[:1], resolved).contradictions_closed == 1


def test_a_disputed_position_says_why_it_is_held_loosely(tmp_path):
    # Thinly-supported and contradicted-by-observation are different states,
    # and the being reads this document as itself.
    from newz.sleep.perspective import render

    doc = render(_held_position(confidence=0.3) and [
        Item(section="who_i_am", text="I experience total cache inefficiency.",
             evidence=["9"], confidence=0.3, status="disputed")],
        2, "2026-08-13", {})
    assert "contradicted by what I have since observed" in doc


def test_the_night_records_what_confrontation_decided_not_only_what_changed(tmp_path):
    """The diff says what changed; this says what the being decided.

    Measured 2026-08-14: v6 added nothing (novelty 0.0) and the stale
    cache-miss position GAINED confidence. Whether that was a disposition
    toward `reinforces` or a starved digest producing `none` was
    unanswerable, because SleepReport counted every verdict and then threw
    them away — only the diff was persisted. A fix shipped that day rested on
    an inference that could not be checked before or after.
    """
    held = [Item(section="what_i_hold", text="I check my sources.",
                 evidence=["9"], confidence=0.6, status="carried")]
    path = _sleep_store(tmp_path, EPISODES, items=held)
    llm = FakeLLM([DIGEST, ("DEEP", """<confrontation>
      <verdict candidate="1" type="reinforces" item="1"/>
      <verdict candidate="2" type="none"/>
    </confrontation>""")])
    NightlySleep(path, llm, "dean").run()

    conn = open_db(path, read_only=True)
    row = conn.execute("SELECT verdicts_json FROM perspective WHERE version=2").fetchone()
    verdicts = json.loads(row["verdicts_json"])
    assert verdicts["reinforces"] == 1
    assert verdicts["none"] == 1
    conn.close()


def test_a_night_that_only_reinforces_is_visible_as_such(tmp_path):
    # The exact shape of the 2026-08-14 night: everything reinforces, the
    # diff adds nothing, and until now the two were indistinguishable from
    # "there was nothing worth adding".
    held = [Item(section="what_i_hold", text="I check my sources.",
                 evidence=["9"], confidence=0.6, status="carried")]
    path = _sleep_store(tmp_path, EPISODES, items=held)
    llm = FakeLLM([DIGEST, ("DEEP", """<confrontation>
      <verdict candidate="1" type="reinforces" item="1"/>
      <verdict candidate="2" type="reinforces" item="1"/>
    </confrontation>""")])
    report = NightlySleep(path, llm, "dean").run()

    assert report.diff["added"] == []
    conn = open_db(path, read_only=True)
    verdicts = json.loads(conn.execute(
        "SELECT verdicts_json FROM perspective WHERE version=2").fetchone()[0])
    # The night is now diagnosable: all reinforcement, nothing admitted.
    assert verdicts.get("reinforces") == 2
    assert "new" not in verdicts
    conn.close()


# ── the confront pass batches (2026-08-16) ───────────────────────────────
#
# _digest has always batched at 60. _confront did not batch at all: every
# candidate went into ONE DEEP call capped at 2,500 output tokens, so
# everything past what fitted in a single reply was digested and then never
# weighed — present in the store, absent from the Perspective, and invisible
# as a failure because the call succeeds. It also made reading self-limiting
# in a way nothing measured: however much the being read, only one reply's
# worth could ever reach what it holds.

from newz.sleep.nightly import CONFRONT_BATCH


def _many_observations(n):
    # refs must resolve to gathered episode ids or _digest drops the
    # observation — episode 1 exists in EPISODES.
    obs = "\n".join(
        f'  <observation refs="1">Observation number {i} about my work.</observation>'
        for i in range(1, n + 1))
    return ("DEEP", f"<digest>\n{obs}\n</digest>")


def _verdicts(first, count, kind="none"):
    body = "\n".join(f'  <verdict candidate="{i}" type="{kind}"/>'
                     for i in range(1, count + 1))
    return ("DEEP", f"<confrontation>\n{body}\n</confrontation>")


def test_more_observations_than_one_call_holds_are_still_weighed(tmp_path):
    n = CONFRONT_BATCH * 2 + 3          # three batches
    path = _sleep_store(tmp_path, EPISODES)
    llm = FakeLLM([_many_observations(n),
                   _verdicts(1, CONFRONT_BATCH),
                   _verdicts(1, CONFRONT_BATCH),
                   _verdicts(1, 3)])
    report = NightlySleep(path, llm, "dean").run()

    # Every observation reached a verdict, not just the first batch's worth.
    assert sum(report.verdicts.values()) == n
    # Three confront calls plus the digest.
    confronts = [c for c in llm.calls if "<candidates>" in c["user"]]
    assert len(confronts) == 3


def test_each_batch_carries_no_more_than_the_batch_size(tmp_path):
    n = CONFRONT_BATCH + 1
    path = _sleep_store(tmp_path, EPISODES)
    llm = FakeLLM([_many_observations(n),
                   _verdicts(1, CONFRONT_BATCH), _verdicts(1, 1)])
    NightlySleep(path, llm, "dean").run()
    for call in [c for c in llm.calls if "<candidates>" in c["user"]]:
        assert call["user"].count("<candidate ") <= CONFRONT_BATCH


def test_a_later_batch_sees_what_an_earlier_one_added(tmp_path):
    # Batches see the CURRENT item set, not a frozen snapshot, so an
    # observation read later tonight can bear on a position formed earlier
    # tonight. That is the order a mind reads in.
    n = CONFRONT_BATCH + 1
    path = _sleep_store(tmp_path, EPISODES)
    llm = FakeLLM([
        _many_observations(n),
        ("DEEP", '<confrontation><verdict candidate="1" type="new" '
                 'section="what_i_hold">Something I now hold.</verdict>'
                 '</confrontation>'),
        ("DEEP", '<confrontation><verdict candidate="1" type="none"/>'
                 '</confrontation>'),
    ])
    NightlySleep(path, llm, "dean").run()
    second = [c for c in llm.calls if "<candidates>" in c["user"]][1]
    assert "Something I now hold." in second["user"], \
        "the second batch was not shown what the first added"


def test_one_failed_batch_costs_its_own_observations_not_the_night(tmp_path):
    n = CONFRONT_BATCH + 1
    path = _sleep_store(tmp_path, EPISODES)
    llm = FakeLLM([
        _many_observations(n),
        ("DEEP", "not xml at all"),                       # batch 1 fails
        ("DEEP", '<confrontation><verdict candidate="1" type="new" '
                 'section="what_i_hold">This still landed.</verdict>'
                 '</confrontation>'),
    ])
    NightlySleep(path, llm, "dean").run()
    conn = open_db(path, read_only=True)
    texts = [r["text"] for r in conn.execute(
        "SELECT text FROM perspective_items WHERE version=2")]
    conn.close()
    assert "This still landed." in texts


# ── curiosity: a question is not a position and not nothing (2026-08-16) ──
#
# Both gates from reading to memory were binary: the opener gave a concern or
# nothing, confront gave a position or nothing. There was no shallow
# retention — which is another way of saying the being had commitment but no
# curiosity. And `unresolved`, the tier S2 §4.2 reserves for "questions the
# world has not answered", could only be reached by CONTRADICTING something
# already held.

OPENS = ("DEEP", """<confrontation>
  <verdict candidate="1" type="opens">Does coordination failure in multi-agent
  systems come from the protocol or from shared training data?</verdict>
  <verdict candidate="2" type="none"/>
</confrontation>""")


def test_a_question_that_is_not_a_position_reaches_unresolved(tmp_path):
    path = _sleep_store(tmp_path, EPISODES)
    NightlySleep(path, FakeLLM([DIGEST, OPENS]), "dean").run()

    conn = open_db(path, read_only=True)
    rows = conn.execute(
        "SELECT text, section FROM perspective_items WHERE version=2"
        " AND section='unresolved'").fetchall()
    conn.close()
    assert rows, "the question had nowhere to go"
    assert "coordination failure" in rows[0]["text"]


def test_a_question_the_world_raises_again_is_reinforced_not_cloned(tmp_path):
    # The maturity signal, and it already existed: _add_or_reinforce finds the
    # semantic twin and raises confidence rather than adding a second copy.
    held = [Item(section="unresolved", confidence=0.6, status="carried",
                 evidence=["1"],
                 text="Does coordination failure in multi-agent systems come "
                      "from the protocol or from shared training data?")]
    path = _sleep_store(tmp_path, EPISODES, items=held)
    NightlySleep(path, FakeLLM([DIGEST, OPENS]), "dean").run()

    conn = open_db(path, read_only=True)
    rows = conn.execute(
        "SELECT confidence FROM perspective_items WHERE version=2"
        " AND section='unresolved' AND status<>'released'").fetchall()
    conn.close()
    assert len(rows) == 1, "the recurring question was cloned instead of reinforced"
    assert rows[0]["confidence"] > 0.6


def test_a_matured_question_becomes_a_concern_and_leaves_unresolved(tmp_path):
    # The missing half: unresolved had no way out. Entries sat, decayed and
    # were released, and nothing ever turned one into something to pursue.
    ripe = [Item(section="unresolved", confidence=0.72, status="carried",
                 evidence=["1"],
                 text="Does coordination failure in multi-agent systems come "
                      "from the protocol or from shared training data?")]
    path = _sleep_store(tmp_path, EPISODES, items=ripe)
    opener_yes = ("AMBIENT", """<proposal>
  <worth_pursuing>yes</worth_pursuing>
  <statement>Does coordination failure come from the protocol or the data?</statement>
  <why_open>It changes how I read multi-agent results.</why_open>
  <closing_condition>An ablation separating protocol from training data settles it.</closing_condition>
  <grounded_in>Does coordination failure in multi-agent systems come from the protocol or from shared training data?</grounded_in>
</proposal>""")
    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation></confrontation>"), opener_yes])
    NightlySleep(path, llm, "dean").run()

    conn = open_db(path, read_only=True)
    concerns = conn.execute(
        "SELECT statement, origin FROM concerns WHERE status='open'").fetchall()
    still_open = conn.execute(
        "SELECT COUNT(*) FROM perspective_items WHERE version=2"
        " AND section='unresolved' AND status<>'released'").fetchone()[0]
    conn.close()
    assert len(concerns) == 1, "a matured question did not become a concern"
    assert concerns[0]["origin"] == "curiosity"
    assert still_open == 0, "the question is held in two places at once"


def test_an_unreinforced_question_is_left_alone(tmp_path):
    # Only questions the world raised AGAIN mature. A fresh one waits, which
    # is what stops every passing thought becoming a research programme.
    fresh = [Item(section="unresolved", confidence=0.6, status="carried",
                 evidence=["1"], text="Some question I met once.")]
    path = _sleep_store(tmp_path, EPISODES, items=fresh)
    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation></confrontation>")])
    NightlySleep(path, llm, "dean").run()   # no opener call may happen

    conn = open_db(path, read_only=True)
    assert conn.execute("SELECT COUNT(*) FROM concerns").fetchone()[0] == 0
    conn.close()


def test_the_question_carries_its_material_not_only_itself(tmp_path):
    # Grounding the concern in the being's own restated question would make
    # the anti-fabrication check a formality it could always satisfy by
    # quoting itself. The evidence episodes go with it.
    ripe = [Item(section="unresolved", confidence=0.72, status="carried",
                 evidence=["1"], text="A question I keep meeting.")]
    path = _sleep_store(tmp_path, EPISODES, items=ripe)
    llm = FakeLLM([DIGEST, ("DEEP", "<confrontation></confrontation>"),
                   ("AMBIENT", "<proposal><worth_pursuing>no</worth_pursuing></proposal>")])
    NightlySleep(path, llm, "dean").run()
    opener_call = llm.calls[-1]["user"]
    assert "A question I keep meeting." in opener_call
    assert "dean asked how my memory works" in opener_call
