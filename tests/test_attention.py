"""Noticing, the interest register, the diet self-report, and decay."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from newz.attention import decay, interest, notices
from newz.attention.diet import diet_self_report
from newz.attention.notices import NoticeRefused, notice_over_span, record_notice
from newz.clock import stamp
from newz.domain.enums import NoticeProvenanceKind
from tests import world as world_module

NOW = datetime(2026, 9, 5, 12, 0, 0)
QUOTE = "It held station off the right wing"
TARGETS = {
    "uap_and_aerospace_anomalies": "18%",
    "metascience_methods_and_replication": "10%",
}


@pytest.fixture
def world(store):
    return world_module.build(store)


def _notice(store, world, notice_id="notice:n1", key="harbour", quote=QUOTE, reason="the vector claim is unusually specific"):
    return notice_over_span(store, notice_id, world.artifact(key), quote, reason)


# ---------------------------------------------------------------------------
# Noticing
# ---------------------------------------------------------------------------


def test_a_notice_points_at_a_span_that_verifies(store, world):
    notice = _notice(store, world)
    assert notice.quote == QUOTE
    assert notice.locator.endswith("p 3")
    assert notice.provenance_kind is NoticeProvenanceKind.OBSERVED


def test_a_notice_cannot_arise_from_the_systems_own_output(store, world):
    """Attention drawn from a projection is attention feeding on itself."""
    raw = store.one("SELECT raw_artifact_id FROM extraction_runs LIMIT 1")["raw_artifact_id"]
    with pytest.raises(NoticeRefused, match="own output"):
        record_notice(
            store,
            notice_id="notice:bad",
            artifact_id=raw,
            segment_id="segment:whatever",
            quote="anything",
            start=0,
            end=3,
            locator="",
            reason="a reason",
            provenance_kind=NoticeProvenanceKind.INFERRED,
        )


def test_a_notice_needs_material_that_was_actually_retrieved(store, world):
    with store.write() as connection:
        connection.execute(
            "INSERT INTO artifacts (id, content_hash, byte_size, media_type, stored_path, "
            "stored_at) VALUES ('artifact:unsighted', 'deadbeef', 1, 'text/plain', 'x', "
            "datetime('now'))"
        )
    with pytest.raises(NoticeRefused, match="retrieved and retained"):
        record_notice(
            store,
            notice_id="notice:bad",
            artifact_id="artifact:unsighted",
            segment_id="segment:x",
            quote="q",
            start=0,
            end=1,
            locator="",
            reason="a reason",
            provenance_kind=NoticeProvenanceKind.OBSERVED,
        )


def test_a_notice_that_does_not_verify_is_refused(store, world):
    with pytest.raises(NoticeRefused, match="exactly once"):
        notice_over_span(store, "notice:bad", world.artifact("harbour"), "words never written", "r")


def test_a_notice_says_why(store, world):
    with pytest.raises(NoticeRefused, match="says why"):
        record_notice(
            store,
            notice_id="notice:bad",
            artifact_id=world.artifact("harbour"),
            segment_id="segment:x",
            quote="q",
            start=0,
            end=1,
            locator="",
            reason="  ",
            provenance_kind=NoticeProvenanceKind.OBSERVED,
        )


def test_the_three_provenance_kinds_stay_apart(store, world):
    """What it saw, what it concluded, what it was handed."""
    for index, kind in enumerate(NoticeProvenanceKind):
        notice_over_span(
            store,
            f"notice:p{index}",
            world.artifact("harbour"),
            ("It held station off the right wing", "no radar", "vector we could not match")[index]
            if index != 1
            else "No radar correlation has been released",
            f"reason {index}",
            provenance_kind=kind,
        )
    kinds = {row["provenance_kind"] for row in notices.notices(store)}
    assert kinds == {"observed", "inferred", "told"}


# ---------------------------------------------------------------------------
# The register
# ---------------------------------------------------------------------------


def test_an_interest_records_its_influences(store, world):
    notice = _notice(store, world)
    entry = interest.form_interest(
        store,
        interest_id="interest:i1",
        subject="the Coral Ridge vector",
        rationale="the account describes a manoeuvre the aircraft could not match",
        notice_ids=(notice.id,),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    assert entry.diet_epoch_id == "epoch:1"
    assert dict(entry.topic_targets) == TARGETS
    assert entry.notice_ids == (notice.id,)
    events = interest.events_for(store, "interest:i1")
    assert events[0]["kind"] == "formed"


def test_an_interest_that_traces_only_to_a_topic_target_is_labelled_diet_derived(store, world):
    """A catalog weighted 18% toward one subject produces a system interested in
    that subject. That is a property of the diet, not self-discovery."""
    notice = _notice(store, world)
    derived = interest.form_interest(
        store,
        interest_id="interest:derived",
        subject="uap and aerospace anomalies",
        rationale="the diet is full of it",
        notice_ids=(notice.id,),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    assert derived.diet_derived

    formed = interest.form_interest(
        store,
        interest_id="interest:formed",
        subject="the Coral Ridge vector",
        rationale="one specific manoeuvre, picked out of the reading",
        notice_ids=(notice.id,),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    assert not formed.diet_derived


def test_an_interest_records_what_it_caused_and_nothing_else(store, world):
    notice = _notice(store, world)
    interest.form_interest(
        store,
        interest_id="interest:i1",
        subject="the Coral Ridge vector",
        rationale="a reason",
        notice_ids=(notice.id,),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    interest.record_outcome(store, "interest:i1", "investigation", "investigation:x")
    interest.record_outcome(store, "interest:i1", "essay", "essay:y")
    entry = interest.load_interest(store, "interest:i1")
    assert entry.outcomes == (("essay", "essay:y"), ("investigation", "investigation:x"))
    assert entry.productive


def test_an_interest_that_produced_nothing_is_retired_or_renewed_with_a_reason(store, world):
    notice = _notice(store, world)
    interest.form_interest(
        store,
        interest_id="interest:i1",
        subject="something that went nowhere",
        rationale="a reason",
        notice_ids=(notice.id,),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
        window_days=30,
        # Pinned, so this measures the window rather than racing the wall clock.
        # With the opening stamped by the ledger it passed or failed depending on
        # which side of UTC midnight the suite ran.
        opened_at=stamp(NOW),
    )
    assert interest.unproductive(store, NOW) == ()
    later = NOW + timedelta(days=31)
    assert interest.unproductive(store, later) == ("interest:i1",)

    with pytest.raises(ValueError, match="records why"):
        interest.retire_interest(store, "interest:i1", "")
    interest.retire_interest(store, "interest:i1", "thirty days and no investigation")
    assert interest.load_interest(store, "interest:i1").retired
    assert interest.unproductive(store, later) == ()


def test_a_productive_interest_is_never_swept_up_as_unproductive(store, world):
    notice = _notice(store, world)
    interest.form_interest(
        store,
        interest_id="interest:i1",
        subject="a productive one",
        rationale="a reason",
        notice_ids=(notice.id,),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    interest.record_outcome(store, "interest:i1", "investigation", "investigation:x")
    assert interest.unproductive(store, NOW + timedelta(days=90)) == ()


def test_the_register_is_append_only(store, world):
    import sqlite3

    notice = _notice(store, world)
    interest.form_interest(
        store,
        interest_id="interest:i1",
        subject="s",
        rationale="a reason",
        notice_ids=(notice.id,),
        diet_epoch_id="epoch:1",
        topic_targets=TARGETS,
    )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"), store.write() as connection:
        connection.execute("UPDATE interest_events SET reason = 'rewritten'")


def test_the_provenance_mix_is_dominated_by_external_material(store, world):
    for index, key in enumerate(("harbour", "registry", "ardenne")):
        quote = {
            "harbour": QUOTE,
            "registry": "Radar correlation: none found in the recorded window.",
            "ardenne": "we observe an effect of -0.01",
        }[key]
        notice_over_span(store, f"notice:n{index}", world.artifact(key), quote, f"reason {index}")
        interest.form_interest(
            store,
            interest_id=f"interest:i{index}",
            subject=f"subject {index}",
            rationale="a reason",
            notice_ids=(f"notice:n{index}",),
            diet_epoch_id="epoch:1",
            topic_targets=TARGETS,
        )
    mix = interest.provenance_mix(store)
    assert mix["notices_behind_interests"] == 3
    assert mix["external_share"] == 1.0
    assert mix["externally_dominated"]


def test_the_origination_share_counts_what_interest_actually_caused(store, world):
    from newz.research import investigations

    for origin in ("operator", "assessment", "interest"):
        investigations.open_investigation(
            store,
            investigation_id=f"investigation:{origin}",
            question="a question",
            rationale="a reason",
            exit_conditions=("something",),
            closing_observation="an observation",
            origin=origin,
        )
    share = interest.origination_share(store)
    assert share["investigations"] == 3
    assert share["interest_originated"] == 1
    assert share["share"] == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# The diet self-report
# ---------------------------------------------------------------------------


def test_the_system_can_state_the_shape_of_its_own_reading(store, world):
    report = diet_self_report(store)
    assert report["retained_reads"] == 9
    assert set(report["roles"]) >= {"firsthand_witness", "primary_record", "empirical_study"}
    assert sum(report["topic_share"].values()) == pytest.approx(1.0, abs=0.01)
    assert "not the shape of the world" in report["note"]


def test_the_self_report_names_an_under_represented_perspective(store, world):
    """Enabled and unread is the honest form of the question."""
    with store.write() as connection:
        connection.execute(
            "INSERT INTO sources (id, publisher_id, name, topic, recorded_at) "
            "VALUES ('source:unread', 'publisher:harbour', 'unread', 'psi_and_consciousness', "
            "datetime('now'))"
        )
        connection.execute(
            "INSERT INTO source_revisions (id, source_id, revision, endpoint_url, delivery_kind, "
            "role, declared_scope, risk_floor, retention_policy, expected_mime, recorded_at) "
            "VALUES ('srcrev:unread-1', 'source:unread', 1, 'https://unread.example/x', 'page', "
            "'skeptical_investigation', 'scope', 'R1', 'full_text', 'text/html', datetime('now'))"
        )
        connection.execute(
            "INSERT INTO diet_epoch_sources (epoch_id, source_revision_id) "
            "VALUES ('epoch:1', 'srcrev:unread-1')"
        )
    report = diet_self_report(store)
    assert "psi_and_consciousness" in report["under_represented"]


def test_the_self_report_separates_interests_that_track_the_diet(store, world):
    notice = _notice(store, world)
    interest.form_interest(
        store, interest_id="interest:tracks", subject="uap and aerospace anomalies",
        rationale="r", notice_ids=(notice.id,), diet_epoch_id="epoch:1", topic_targets=TARGETS,
    )
    interest.form_interest(
        store, interest_id="interest:diverges", subject="the Coral Ridge vector",
        rationale="r", notice_ids=(notice.id,), diet_epoch_id="epoch:1", topic_targets=TARGETS,
    )
    report = diet_self_report(store)
    assert [e["interest_id"] for e in report["interests_tracking_the_diet"]] == ["interest:tracks"]
    assert [e["interest_id"] for e in report["interests_diverging_from_the_diet"]] == [
        "interest:diverges"
    ]


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------


def test_attention_decays_and_leaves_a_record_of_decaying(store, world):
    notice_over_span(
        store, "notice:n1", world.artifact("harbour"), QUOTE, "a reason",
        noticed_at="2026-01-01T00:00:00",
    )
    stale = decay.decayable_notices(store, NOW)
    assert stale == ("notice:n1",)
    decay.decay_notices(store, stale, "decay:d1", "past the 90-day window")

    row = store.one("SELECT * FROM notices WHERE id = 'notice:n1'")
    assert row["quote"] == ""          # the payload is gone
    assert row["superseded_by"] == "decay:d1"  # the record of it is not
    held = decay.what_is_no_longer_held(store)
    assert held[0]["covers"] == ["notice:n1"]
    assert "reduced to this summary" in held[0]["summary"]


def test_evidence_never_decays(store, world):
    notice_over_span(
        store, "notice:n1", world.artifact("harbour"), QUOTE, "a reason",
        noticed_at="2026-01-01T00:00:00",
    )
    decay.decay_notices(store, decay.decayable_notices(store, NOW), "decay:d1", "window")
    assert decay.evidence_is_untouched(store)
    assert store.one("SELECT COUNT(*) AS n FROM assertions WHERE quote != ''")["n"] > 0


def test_a_retired_interest_decays_ninety_days_later_and_not_before(store, world):
    notice = _notice(store, world)
    interest.form_interest(
        store, interest_id="interest:i1", subject="s", rationale="a reason",
        notice_ids=(notice.id,), diet_epoch_id="epoch:1", topic_targets=TARGETS,
    )
    assert decay.decayable_interests(store, NOW) == ()
    interest.retire_interest(store, "interest:i1", "produced nothing")
    assert decay.decayable_interests(store, NOW) == ()

    interest.form_interest(
        store, interest_id="interest:old", subject="s", rationale="a reason",
        notice_ids=(notice.id,), diet_epoch_id="epoch:1", topic_targets=TARGETS,
    )
    interest.retire_interest(
        store, "interest:old", "produced nothing", at="2026-01-01T00:00:00"
    )
    assert decay.decayable_interests(store, NOW) == ("interest:old",)
    decay.decay_interests(store, ("interest:old",), "decay:d2", "ninety days after retirement")
    assert (
        store.one("SELECT rationale FROM interest_entries WHERE id = 'interest:old'")["rationale"]
        == "[decayed]"
    )


def test_decay_must_cite_what_it_covers(store):
    with pytest.raises(ValueError, match="cites what it covers"):
        decay.decay_notices(store, (), "decay:d1", "nothing")
