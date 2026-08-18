"""S2 §13 — what shaped this view.

The instrument v1's own invariant deferred for lack of. TRUE_NORTH §8's
non-prescription is only checkable if the influence on a held position can
be named; these pin that it can, including the two things §13 asks for by
name — diversity, and operator influence traceable like everything else.
"""

import json

from newz.memory.provenance import (
    corpus_concentration,
    what_shaped,
    what_shaped_version,
)
from newz.sleep.perspective import Item, save_items


def _episode(store, ep_id, provenance, summary="something happened"):
    store.execute(
        "INSERT INTO episodes (id, ts, kind, provenance, summary, digest_eligible)"
        " VALUES (?,?,?,?,?,1)", (ep_id, 1000.0 + ep_id, "reading", provenance, summary))


def _seed(store):
    _episode(store, 1, "world:wikipedia", "I read Collective unconscious")
    _episode(store, 2, "world:openalex", "I read The Archetypes")
    _episode(store, 3, "human:dean", "dean: what about Jung — me: a structural link")
    _episode(store, 4, "self", "I moved a concern")
    save_items(store, 1, [
        Item(section="what_i_hold", text="Jung and Montaigne share a structure.",
             evidence=["1", "2", "3"], confidence=0.7, status="carried"),
        Item(section="who_i_am", text="I read closely.",
             evidence=["4"], confidence=0.6, status="carried"),
        Item(section="what_i_hold", text="An ungrounded hunch.",
             evidence=[], confidence=0.4, status="carried"),
    ])
    store.commit()


def test_a_position_names_the_episodes_that_shaped_it(store):
    _seed(store)
    inf = [i for i in what_shaped_version(store) if "structure" in i.text][0]
    assert inf.total == 3
    assert inf.by_provenance["world:wikipedia"] == 1
    assert inf.by_provenance["human:dean"] == 1
    assert {e["id"] for e in inf.episodes} == {1, 2, 3}


def test_it_separates_the_world_from_people_from_itself(store):
    # §13: operator influence is traceable too — the being can see where its
    # operator shaped a view rather than the world.
    _seed(store)
    inf = [i for i in what_shaped_version(store) if "structure" in i.text][0]
    assert inf.share("world:") == 2 / 3
    assert inf.share("human:") == 1 / 3
    assert inf.share("self") == 0.0

    own = [i for i in what_shaped_version(store) if "read closely" in i.text][0]
    assert own.share("self") == 1.0


def test_concentration_is_reported_per_position(store):
    # v1's end state — 56% of reading from two outlets — as a per-view read.
    _seed(store)
    store.execute("UPDATE perspective_items SET evidence_json=?"
                  " WHERE text LIKE 'Jung%'", (json.dumps(["1", "1", "1", "2"]),))
    store.commit()
    inf = [i for i in what_shaped_version(store) if "structure" in i.text][0]
    source, share = inf.concentration
    assert source == "world:wikipedia"
    assert "** " in inf.render()          # flagged when one source dominates


def test_an_ungrounded_position_says_so_rather_than_looking_supported(store):
    _seed(store)
    inf = [i for i in what_shaped_version(store) if "hunch" in i.text][0]
    assert inf.total == 0
    assert "nothing traceable" in inf.render()


def test_a_ref_naming_a_missing_episode_is_reported_not_dropped(store):
    # A position citing something the store cannot produce is a real finding.
    _seed(store)
    store.execute("UPDATE perspective_items SET evidence_json=?"
                  " WHERE text LIKE 'Jung%'", (json.dumps(["1", "9999", "ep-x"]),))
    store.commit()
    inf = [i for i in what_shaped_version(store) if "structure" in i.text][0]
    assert inf.total == 1
    assert set(inf.unresolved_refs) == {"9999", "ep-x"}
    assert "resolve to no episode" in inf.render()


def test_corpus_concentration_totals_across_held_positions(store):
    _seed(store)
    mix = corpus_concentration(store)
    assert mix["world:wikipedia"] == 1
    assert mix["self"] == 1
    assert sum(mix.values()) == 4


def test_what_shaped_reads_and_never_writes(store):
    _seed(store)
    before = store.execute("SELECT COUNT(*) FROM perspective_items").fetchone()[0]
    what_shaped(store, 1)
    what_shaped_version(store)
    corpus_concentration(store)
    assert store.execute(
        "SELECT COUNT(*) FROM perspective_items").fetchone()[0] == before
