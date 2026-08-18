import json

from newz.store.hygiene import classify, run_hygiene, survey


def _seed(store, summaries):
    for i, s in enumerate(summaries):
        store.execute(
            "INSERT INTO episodes (ts, kind, provenance, summary, content_json)"
            " VALUES (?,?,?,?,?)",
            (1000.0 + i * 3600, "v1_tick", "self", s, "{}"),
        )
    store.commit()


CORPUS = [
    "prefix_cache_miss_rate_high: 1.00",
    "prefix_cache_miss_rate_high: 1.00",
    "endpoint_down: reason=timeout",
    "SELF PROBE (concern) — you are carrying this: how does X work",
    "INITIATIVE PROBE — a recent operator-conversation thread connects",
    "What is your favorite sport",
    "FIFA World Cup is going on right now",
    "",
]


def test_classification_is_total_and_correct():
    assert classify("prefix_cache_miss_rate_high: 1.00") == "substrate"
    assert classify("endpoint_down: reason=timeout") == "substrate"
    assert classify("SELF PROBE (concern) — carrying this") == "self_probe"
    assert classify("INITIATIVE PROBE — a thread connects") == "self_probe"
    assert classify("What is your favorite sport") == "conversation"
    assert classify("FIFA World Cup is going on right now") == "conversation"
    assert classify("") == "empty"
    assert classify(None) == "empty"
    # A conversational line that merely contains a colon is not telemetry.
    assert classify("Here is my view: the thing is complicated") == "conversation"


def test_survey_does_not_write(store):
    _seed(store, CORPUS)
    report = survey(store)
    assert report.counts == {"substrate": 3, "self_probe": 2, "conversation": 2, "empty": 1}
    assert not report.applied
    assert store.execute(
        "SELECT COUNT(*) FROM episodes WHERE kind='v1_tick'"
    ).fetchone()[0] == len(CORPUS)


def test_hygiene_retags_and_folds_without_deleting(store):
    _seed(store, CORPUS)
    report = run_hygiene(store, "dean", apply=True)
    assert report.applied and report.folded_rows == 3

    # Nothing deleted: 8 originals + 1 fold.
    assert store.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == len(CORPUS) + 1

    kinds = dict(store.execute("SELECT kind, COUNT(*) FROM episodes GROUP BY kind"))
    assert kinds == {"v1_substrate": 3, "v1_self_probe": 2, "v1_conversation": 2,
                     "v1_empty": 1, "substrate_fold": 1}

    # Provenance is now accurate — the filter Phase 1.3 needs.
    prov = dict(store.execute(
        "SELECT provenance, COUNT(*) FROM episodes GROUP BY provenance"))
    assert prov["human:dean"] == 2
    assert prov["self"] == 3           # 2 probes + 1 empty
    assert prov["world:substrate"] == 4  # 3 raw + the fold

    # Raw telemetry is retained but no longer read by sleep; the fold is.
    assert store.execute(
        "SELECT COUNT(*) FROM episodes WHERE kind='v1_substrate' AND digest_eligible=1"
    ).fetchone()[0] == 0
    fold = store.execute(
        "SELECT id, summary, content_json, digest_eligible FROM episodes"
        " WHERE kind='substrate_fold'").fetchone()
    assert fold["digest_eligible"] == 1
    assert "3 recorded moments" in fold["summary"]
    assert json.loads(fold["content_json"])["folded_rows"] == 3

    # Every folded row points at the episode that now stands for it.
    linked = store.execute(
        "SELECT COUNT(*) FROM episodes WHERE folded_into=?", (fold["id"],)
    ).fetchone()[0]
    assert linked == 3


def test_hygiene_is_idempotent(store):
    _seed(store, CORPUS)
    run_hygiene(store, "dean", apply=True)
    before = store.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    second = run_hygiene(store, "dean", apply=True)
    assert second.total() == 0
    assert store.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == before


def test_new_conversation_episodes_are_untouched(store):
    _seed(store, CORPUS)
    store.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary) VALUES"
        " (9999.0,'conversation','human:dean','a live exchange')"
    )
    store.commit()
    run_hygiene(store, "dean", apply=True)
    row = store.execute(
        "SELECT kind, provenance, digest_eligible FROM episodes WHERE ts=9999.0"
    ).fetchone()
    assert (row["kind"], row["provenance"], row["digest_eligible"]) == (
        "conversation", "human:dean", 1)
