import math

from newz.memory.embeddings import cosine, pack, unpack
from newz.memory.retrieval import Retriever, Scope, render_hits

MODEL = "fake-embed-v1"


class FakeEmbedder:
    """Deterministic 3-d vectors keyed by a word in the text, so tests can
    reason about similarity without a network."""

    model = MODEL
    AXES = {"memory": [1.0, 0.0, 0.0], "sport": [0.0, 1.0, 0.0],
            "music": [0.0, 0.0, 1.0]}

    def _vec(self, text: str):
        v = [0.0, 0.0, 0.0]
        for word, axis in self.AXES.items():
            if word in text.lower():
                v = [a + b for a, b in zip(v, axis)]
        return v if any(v) else [0.577, 0.577, 0.577]

    def embed(self, texts):
        return [self._vec(t) for t in texts]

    def embed_one(self, text):
        return self._vec(text)


def _add(store, summary, provenance, ts=1000.0, kind="conversation"):
    emb = pack(FakeEmbedder()._vec(summary))
    store.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, embedding,"
        " embedding_model, digest_eligible) VALUES (?,?,?,?,?,?,1)",
        (ts, kind, provenance, summary, emb, MODEL))
    store.commit()


def test_self_echo_never_surfaces_as_evidence(store):
    # THE v1 REGRESSION (S2 §4.3): its own probes ranked as lived history.
    _add(store, "SELF PROBE — what is memory to me", "self", kind="v1_self_probe")
    _add(store, "dean asked how my memory works", "human:dean")

    r = Retriever(store, FakeEmbedder())
    evidence = r.search("memory", scope=Scope.EVIDENCE)
    assert [h.provenance for h in evidence] == ["human:dean"]
    assert all("SELF PROBE" not in h.summary for h in evidence)

    # Unscoped search still sees it — the filter is about evidence, not
    # about hiding the being's own past from itself.
    everything = r.search("memory", scope=Scope.ALL)
    assert any(h.provenance == "self" for h in everything)


def test_person_scope_is_shared_history_only(store):
    _add(store, "dean talked about sport", "human:dean")
    _add(store, "someone else talked about sport", "human:other")
    _add(store, "I thought about sport alone", "self")
    hits = Retriever(store, FakeEmbedder()).search(
        "sport", scope=Scope.PERSON, person_id="dean")
    assert len(hits) == 1 and hits[0].summary.startswith("dean")


def test_vectors_from_another_embedder_are_never_compared(store):
    _add(store, "memory from the current model", "human:dean")
    store.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, embedding,"
        " embedding_model, digest_eligible) VALUES (1.0,'conversation',"
        "'human:dean','memory from an old model',?,'v1-legacy-embedder',1)",
        (pack([1.0, 0.0, 0.0]),))
    store.commit()
    hits = Retriever(store, FakeEmbedder()).search("memory", scope=Scope.ALL)
    assert len(hits) == 1
    assert "old model" not in hits[0].summary


def test_relevance_beats_noise_and_recency_breaks_ties(store):
    _add(store, "we discussed music", "human:dean", ts=1000.0)
    _add(store, "we discussed music", "human:dean", ts=90_000_000.0)
    _add(store, "we discussed sport", "human:dean", ts=90_000_000.0)
    hits = Retriever(store, FakeEmbedder()).search("music", scope=Scope.ALL, k=3)
    assert hits[0].ts == 90_000_000.0          # newer of the two matches first
    assert hits[0].summary.endswith("music")
    assert all(h.similarity >= hits[-1].similarity for h in hits[:1])


def test_rendered_hits_carry_provenance(store):
    _add(store, "dean asked about music", "human:dean", ts=1_700_000_000.0)
    _add(store, "I wondered about music myself", "self", ts=1_700_000_000.0)
    hits = Retriever(store, FakeEmbedder()).search("music", scope=Scope.ALL, k=2)
    text = render_hits(hits, "dean")
    assert "from dean]" in text and "from me]" in text


def test_pack_unpack_round_trip():
    v = [0.1, -0.25, 3.5]
    back = unpack(pack(v))
    assert all(math.isclose(a, b, rel_tol=1e-6) for a, b in zip(v, back))


def test_cosine_edges():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0
    assert cosine([], [1]) == 0.0
    assert cosine([0, 0], [1, 1]) == 0.0
