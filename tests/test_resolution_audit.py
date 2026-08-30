"""A resolution pass audits the world; it does not eat it.

Found by the operator, 2026-08-30, reading a proposed numeric source as adding
content and weighting things. It was true, and it predated the source: ten
resolution attempts had written **52 reading episodes** into the corpus —
retrievable, consolidatable, eligible to become Perspective evidence — and not
one of them was something the being chose to read.

E1.3 says a resolution writes "the one episode this phase produces"; E1.4 says
the refuting material "is deliberately not added to the item's evidence".
Reusing `research()` for the resolution pass did neither.
"""

from __future__ import annotations


# ── a resolution pass audits; it does not consume ────────────────────────

def test_a_resolution_pass_writes_no_reading_episodes(store, monkeypatch):
    """Found by the operator, 2026-08-30: the numeric source would "add too
    much content and weight things".

    It was true, and it predated that source. E1.3 says a resolution writes "the one
    episode this phase produces"; E1.4 says the refuting material "is
    deliberately not added to the item's evidence". Reusing `research()` did
    neither — ten resolution attempts had written **52 reading episodes** into
    the corpus, retrievable and eligible to become Perspective evidence, none
    of which the being chose to read. A resolution read is an AUDIT, and the
    material fetched to check a claim becoming evidence for the position that
    produced it is R-24's self-echo in a new place.

    The numeric source that surfaced this was removed entirely by the operator
    on 2026-08-30. The defect it exposed was never that source's: any adapter
    leading the resolution order feeds the corpus under its own provenance and
    inflates the world share of the grounding mix §1 rests on, while the being
    reaches one narrow set of sources more rather than the world more.
    """
    import newz.world.research as research_mod

    seen = {}

    def fake_research(client, query, **kw):
        seen.update(kw)
        return research_mod.ResearchOutcome(query=query)

    monkeypatch.setattr(research_mod, "research", fake_research)
    monkeypatch.setattr("newz.resolutions.resolver.research", fake_research,
                        raising=False)

    from newz.resolutions.model import Claim
    from newz.resolutions.resolver import resolve_claim
    from newz.resolutions.store import get_claim, open_claim
    from tests.conftest import FakeLLM
    import time

    cid = open_claim(store, Claim(
        id=None, claim="a claim", resolution_condition="a source says so",
        resolver="a named report", due_at=time.time(), opened_at=time.time(),
        provenance="concern:1"), models=set())
    resolve_claim(store, FakeLLM([]), get_claim(store, cid),
                  log_path="/nonexistent.jsonl")

    assert seen.get("as_experience") is False


def test_reads_are_still_recorded_for_the_diet(store):
    """The correction removes the corpus entry and nothing else. `record_read`
    is untouched, so diet accounting, the outlet share caps and the
    already-read dedup all keep working — a resolution read is real traffic
    and is charged as such."""
    import inspect

    import newz.world.research as research_mod

    src = inspect.getsource(research_mod.research)
    guarded = src.split("if claims and as_experience:")[0]

    assert "record_read(" in guarded, (
        "record_read must sit OUTSIDE the as_experience guard")
