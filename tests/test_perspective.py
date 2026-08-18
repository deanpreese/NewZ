from newz.sleep.perspective import (
    Item,
    apply_decay,
    compute_diff,
    load_items,
    parse_document,
    render,
    save_items,
)

DOC = """# Perspective — version 1
*(written by sleep, 2026-08-08)*

## Who I am
- I refuse to fabricate when retrieval is weak. [refs: 1,4,7]
- I settled on the name Lumen. [refs: 52,53,+31]

## What I hold
- Open-weight models shift the moat to reliability. [refs: 4]

## What I am pursuing
- Some concern (1 advances, 0 stalls)

## Who I know
- dean: my operator.

## What is unresolved
- I could not recognise a prior conversation as my own. [refs: 52]

## What just changed
- 2026-08-08: I moved substrates.
"""


def test_parse_recovers_carried_sections_only():
    items = parse_document(DOC)
    sections = {i.section for i in items}
    assert sections == {"who_i_am", "what_i_hold", "unresolved"}
    assert len(items) == 4
    lumen = next(i for i in items if "Lumen" in i.text)
    assert lumen.evidence == ["52", "53"]        # the "+31" marker is not a ref
    assert lumen.text.endswith("Lumen.")          # refs stripped from the text


def test_render_round_trips_through_parse():
    items = parse_document(DOC)
    out = render(items, 2, "2026-08-11", {"pursuing": ["- x"], "who_i_know": ["- y"],
                                          "changed": ["- something"]})
    again = parse_document(out)
    assert {i.text for i in again} == {i.text for i in items}


def test_items_persist_and_reload(store):
    items = [Item(section="who_i_am", text="I check sources.", evidence=["1"])]
    save_items(store, 2, items)
    store.commit()
    loaded = load_items(store, 2)
    assert len(loaded) == 1
    assert loaded[0].text == "I check sources." and loaded[0].evidence == ["1"]
    assert loaded[0].id is not None


def test_diff_is_computed_not_narrated():
    before = [
        Item(id=1, section="who_i_am", text="I check sources.", status="carried"),
        Item(id=2, section="what_i_hold", text="Old position.", status="carried"),
        Item(id=3, section="unresolved", text="An open question.", status="carried"),
    ]
    after = [
        Item(section="who_i_am", text="I check sources.", status="carried"),
        Item(section="what_i_hold", text="Refined position.", status="revised",
             prior_item_id=2),
        Item(section="what_i_hold", text="A brand new position.", status="added"),
        Item(section="unresolved", text="A fresh contradiction.", status="added"),
    ]
    d = compute_diff(before, after)
    assert d.added == ["A brand new position.", "A fresh contradiction."]
    assert d.revised == ["Old position. -> Refined position."]
    assert d.released == ["An open question."]   # dropped, not carried forward
    assert d.carried == 1
    assert d.contradictions_opened == 1
    # Changed 2026-08-13: this asserted 1. A tension that is merely DROPPED —
    # it appears in `released` on the line above — was being counted as a
    # contradiction the being closed. Closure now requires resolution into a
    # position (see test_a_merged_contradiction_is_not_a_closed_one).
    assert d.contradictions_closed == 0
    # 3 of 4 held positions are new or revised.
    assert 0.7 < d.novelty_rate() < 0.8


def test_restatement_shows_as_low_novelty():
    before = [Item(id=i, section="what_i_hold", text=f"position {i}",
                   status="carried") for i in range(1, 6)]
    after = [Item(section="what_i_hold", text=f"position {i}", status="carried")
             for i in range(1, 6)]
    d = compute_diff(before, after)
    assert d.novelty_rate() == 0.0     # a night that changed nothing says so
    assert d.added == [] and d.released == []


def test_ungrounded_claims_decay_and_release():
    grounded = Item(section="who_i_am", text="grounded", evidence=["1"], confidence=0.6)
    weak = Item(section="who_i_am", text="ungrounded", evidence=[], confidence=0.5)
    doomed = Item(section="who_i_am", text="doomed", evidence=[], confidence=0.3)
    kept, released = apply_decay([grounded, weak, doomed])
    assert grounded.confidence == 0.6            # evidence protects it
    assert weak.confidence == 0.42                # ungrounded loses ground
    assert [i.text for i in released] == ["doomed"]   # 0.30 -> 0.22, below 0.25
    assert {i.text for i in kept} == {"grounded", "ungrounded"}


def test_an_ungrounded_claim_survives_several_nights_before_release():
    # Decay must be a slow verdict, not a same-night deletion: a claim
    # entering at the default confidence gets ~4 nights to find support.
    it = Item(section="who_i_am", text="unsupported", evidence=[], confidence=0.6)
    nights = 0
    items = [it]
    while items:
        items, released = apply_decay(items)
        nights += 1
        if released:
            break
    assert 4 <= nights <= 6


def test_low_confidence_items_render_hedged():
    out = render([Item(section="who_i_am", text="a shaky claim", confidence=0.3)],
                 2, "2026-08-11", {})
    assert "(held loosely)" in out


# ── duplicate contradictions (the 2026-08-12 defect) ─────────────────────

class SemanticStub:
    """Paraphrases of one tension cluster together; distinct points do not."""

    def embed(self, texts):
        def vec(t):
            low = t.lower()
            cache = any(w in low for w in ("cache", "retrieval", "stability", "clarity"))
            return [1.0, 0.02] if cache else [0.02, 1.0]
        return [vec(t) for t in texts]


REPHRASINGS = [
    "The observation of stability and sharp retrieval directly conflicts with the held position of prolonged cache inefficiency.",
    "The observation of stable internal architecture and retrieval directly contradicts the held position of total cache inefficiency.",
    "The observation of operational clarity and sharp retrieval directly conflicts with the held position of cache miss history.",
]


def test_a_recurring_tension_is_recognised_as_the_same_item():
    from newz.sleep.perspective import duplicate_of

    held = [Item(section="unresolved", text=REPHRASINGS[0], evidence=["1"])]
    twin = duplicate_of(REPHRASINGS[1], "unresolved", held, SemanticStub())
    assert twin is not None and twin.text == REPHRASINGS[0]


def test_a_distinct_tension_is_not_a_duplicate():
    from newz.sleep.perspective import duplicate_of

    held = [Item(section="unresolved", text=REPHRASINGS[0], evidence=["1"])]
    other = "I cannot tell whether my own gate is making me sound less like myself."
    assert duplicate_of(other, "unresolved", held, SemanticStub()) is None


def test_duplicates_across_sections_are_not_merged():
    from newz.sleep.perspective import duplicate_of

    held = [Item(section="what_i_hold", text=REPHRASINGS[0], evidence=["1"])]
    assert duplicate_of(REPHRASINGS[1], "unresolved", held, SemanticStub()) is None


def test_merge_folds_the_cluster_and_keeps_the_best_grounded():
    from newz.sleep.perspective import merge_duplicates

    items = [
        Item(section="unresolved", text=REPHRASINGS[0], evidence=["1"], confidence=0.6),
        Item(section="unresolved", text=REPHRASINGS[1], evidence=["2", "3"], confidence=0.6),
        Item(section="unresolved", text=REPHRASINGS[2], evidence=["4"], confidence=0.6),
        Item(section="unresolved", text="An entirely separate open question about music.",
             evidence=["5"], confidence=0.6),
    ]
    kept, merged = merge_duplicates(items, SemanticStub())
    assert len(kept) == 2                      # the cluster folded to one, plus the other
    assert len(merged) == 2
    survivor = next(i for i in kept if "cache" in i.text.lower() or "retrieval" in i.text.lower())
    assert set(survivor.evidence) == {"1", "2", "3", "4"}   # evidence unioned, not lost


def test_the_lexical_fallback_declines_to_judge_tiny_items():
    # Jaccard saturates on short text: two three-word items sharing one
    # content word would otherwise score 1.0 and be merged.
    from newz.sleep.perspective import duplicate_of

    held = [Item(section="unresolved", text="position alpha", evidence=[])]
    assert duplicate_of("position beta", "unresolved", held, None) is None


# ── an objection must not merge into the thing it objects to ─────────────

def test_a_contradiction_never_merges_into_the_claim_it_contradicts():
    """Measured 2026-08-14, on Perspective v6.

    The tension "the observation of operational clarity CONFLICTS WITH the
    held position of experiencing prolonged cache inefficiency" was merged
    into "I experienced a prolonged period of system-level alerts indicating
    a high cache miss rate". Both sat in `unresolved`, both were topically
    about cache misses, so they scored as duplicates — and the merge kept the
    better-evidenced one, which was the restatement of the problem rather
    than the objection to it. The stale position then gained confidence with
    nothing left standing against it.
    """
    from newz.sleep.perspective import merge_duplicates

    claim = Item(section="unresolved", id=1, confidence=0.66, evidence=["1", "2"],
                 text="I experienced a prolonged period of system-level alerts "
                      "indicating a high prefix cache miss rate", status="carried")
    objection = Item(section="unresolved", id=2, confidence=0.66, evidence=["3"],
                     text="The observation of operational clarity conflicts with "
                          "the held position of a high prefix cache miss rate",
                     status="carried")
    kept, merged = merge_duplicates([claim, objection], None)
    assert len(kept) == 2, "the objection was absorbed by what it objects to"
    assert merged == []


def test_two_restatements_of_the_same_tension_still_merge():
    # The fix must not disable the merge that stopped the same contradiction
    # being filed on three consecutive nights.
    from newz.sleep.perspective import merge_duplicates

    a = Item(section="unresolved", id=1, confidence=0.6, evidence=["1"],
             text="Observed stability conflicts with the held position of total "
                  "cache inefficiency across every request I handled",
             status="carried")
    b = Item(section="unresolved", id=2, confidence=0.6, evidence=["2"],
             text="Observed stability conflicts with the held position of total "
                  "cache inefficiency across every request I handled",
             status="carried")
    kept, merged = merge_duplicates([a, b], None)
    assert len(kept) == 1 and len(merged) == 1
