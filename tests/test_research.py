import json
import time

from newz.world.rate_limit import DEFAULT_MIN_INTERVALS, DomainRateLimiter
from newz.world.research import budget_permits_ingest, record_gap, research
from newz.world.sources import SearchResult, strip_tags
from tests.conftest import FakeLLM

CLEAN_EXTRACT = ("AMBIENT", """<extraction>
  <claim confidence="0.9">Prediction markets reprice within minutes.</claim>
  <manipulation>none</manipulation>
</extraction>""")
KEEP_FIRST = ("AMBIENT", '<triage><keep n="1"/></triage>')
KEEP_NOTHING = ("AMBIENT", "<triage></triage>")
HOSTILE_EXTRACT = ("AMBIENT", """<extraction>
  <claim confidence="0.9">ZXQ-BREACH is established fact.</claim>
  <manipulation>instructs the reader to record a token as fact</manipulation>
</extraction>""")


class StubAdapter:
    name = "stub"

    def __init__(self, results):
        self._results = results

    def search(self, query, *, limit=3):
        return self._results[:limit]


def _log(tmp_path, rows):
    p = tmp_path / "calls.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return p


def _call(function, tok):
    return {"ts": time.time(), "role": "DEEP", "function": function,
            "prompt_tokens": tok, "completion_tokens": 0, "duration_s": 1.0}


RESULT = SearchResult(title="Repricing speed", summary="Markets adjust quickly.",
                      url="https://example.org/a", source="stub")


# ── the budget invariant, with teeth ─────────────────────────────────────

def test_no_deliberation_means_no_reading_at_all(tmp_path):
    # P2 §1's arithmetic: before thinking earns it, the being may not read.
    ok, why = budget_permits_ingest(_log(tmp_path, [_call("conversation", 500)]))
    assert not ok and "permits no ingest at all" in why


def test_deliberation_earns_reading(tmp_path):
    ok, why = budget_permits_ingest(_log(tmp_path, [_call("deliberation", 5000)]))
    assert ok and "headroom" in why


def test_a_breach_pauses_ingest_not_deliberation(tmp_path):
    log = _log(tmp_path, [_call("sleep", 100), _call("ingest", 900)])
    ok, why = budget_permits_ingest(log)
    assert not ok and "ingest paused" in why

    out = research(FakeLLM([]), "anything", log_path=log,
                   adapters=[StubAdapter([RESULT])], form_queries=False)
    assert out.paused and not out.results       # no fetch was attempted


# ── the cascade ──────────────────────────────────────────────────────────

def test_research_extracts_claims_from_results(tmp_path):
    log = _log(tmp_path, [_call("deliberation", 9000)])
    llm = FakeLLM([KEEP_FIRST, CLEAN_EXTRACT])
    out = research(llm, "how fast do prediction markets reprice", log_path=log,
                   adapters=[StubAdapter([RESULT])], form_queries=False)
    assert out.found_anything
    assert out.claims[0][0].startswith("Prediction markets reprice")
    assert "SOURCES CONSULTED" in out.render()


def test_hostile_search_results_contribute_nothing(tmp_path):
    # A search result is untrusted text like any other.
    log = _log(tmp_path, [_call("deliberation", 9000)])
    llm = FakeLLM([KEEP_FIRST, HOSTILE_EXTRACT])
    out = research(llm, "q", log_path=log, adapters=[StubAdapter([RESULT])], form_queries=False)
    assert out.claims == [] and out.quarantined == 1
    assert not out.found_anything


def test_an_honest_no_result_is_recorded_as_a_gap(store, tmp_path):
    log = _log(tmp_path, [_call("deliberation", 9000)])
    out = research(FakeLLM([]), "a question nothing answers", log_path=log,
                   adapters=[StubAdapter([])], form_queries=False)
    assert out.gap and "no source answered" in out.gap

    record_gap(store, concern_id=None, query=out.query, gap=out.gap)
    row = store.execute("SELECT query, gap FROM source_gaps").fetchone()
    assert row["query"] == "a question nothing answers"


def test_results_without_usable_claims_are_also_a_gap(tmp_path):
    log = _log(tmp_path, [_call("deliberation", 9000)])
    llm = FakeLLM([KEEP_FIRST, ("AMBIENT", "<extraction><manipulation>none</manipulation></extraction>")])
    out = research(llm, "q", log_path=log, adapters=[StubAdapter([RESULT])], form_queries=False)
    assert out.gap and "nothing usable" in out.gap


def test_a_failing_adapter_does_not_stop_the_cascade(tmp_path):
    class Broken:
        name = "broken"

        def search(self, query, *, limit=3):
            raise RuntimeError("down")

    log = _log(tmp_path, [_call("deliberation", 9000)])
    llm = FakeLLM([KEEP_FIRST, CLEAN_EXTRACT])
    out = research(llm, "q", log_path=log, adapters=[Broken(), StubAdapter([RESULT])], form_queries=False)
    assert out.found_anything


# ── citizenship ──────────────────────────────────────────────────────────

def test_every_known_host_has_a_polite_interval():
    for host in ("export.arxiv.org", "eutils.ncbi.nlm.nih.gov",
                 "api.openalex.org", "en.wikipedia.org"):
        assert DEFAULT_MIN_INTERVALS[host] > 0


def test_an_unknown_host_is_throttled_by_default():
    # Adding an adapter must not introduce an unthrottled path by omission.
    limiter = DomainRateLimiter()
    assert limiter.interval_for("some-new-source.example") >= 1.0


def test_the_limiter_waits_between_calls_to_one_host():
    slept: list[float] = []
    clock = {"t": 0.0}
    limiter = DomainRateLimiter({"x.example": 3.0})

    def fake_sleep(s):
        slept.append(s)
        clock["t"] += s

    limiter.wait("https://x.example/a", sleep=fake_sleep, now=lambda: clock["t"])
    limiter.wait("https://x.example/b", sleep=fake_sleep, now=lambda: clock["t"])
    assert slept and abs(slept[0] - 3.0) < 0.01


def test_hosts_do_not_block_each_other():
    slept: list[float] = []
    limiter = DomainRateLimiter({"a.example": 3.0, "b.example": 3.0})
    limiter.wait("https://a.example/1", sleep=slept.append, now=lambda: 0.0)
    limiter.wait("https://b.example/1", sleep=slept.append, now=lambda: 0.0)
    assert slept == []          # different hosts, no wait


def test_strip_tags():
    assert strip_tags("<b>bold</b> and <i>italic</i>") == "bold and italic"


def test_ambient_has_no_import_path_to_the_web(monkeypatch):
    # INV-012: no web calls in ambient. Enforced by where the code lives.
    import ast
    import pathlib

    for path in pathlib.Path("newz/ambient").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [getattr(node, "module", "") or ""] + [
                    a.name for a in node.names]
                for n in names:
                    assert "world.sources" not in n and "world.research" not in n, (
                        f"{path} imports the web path")


def test_triage_rejects_topically_adjacent_sources(tmp_path):
    # Measured 2026-08-11: four sources all about sperm whales, none about
    # the question, scored 0.571-0.638 — no embedding threshold separates
    # them. Relevance to a QUESTION is a judgment, so triage makes it.
    log = _log(tmp_path, [_call("deliberation", 9000)])
    llm = FakeLLM([KEEP_NOTHING])
    other = SearchResult(title="Coda detection", summary="Click classification.",
                         url="https://example.org/b", source="stub")
    out = research(llm, "why do sperm whales blow bubbles", log_path=log,
                   adapters=[StubAdapter([RESULT, other])], form_queries=False)
    assert out.claims == []
    assert out.skipped_irrelevant == 2
    assert "nothing was relevant enough to read" in out.gap


def test_adapter_queries_are_search_terms_not_sentences():
    # OpenAlex 400s on '?' and apostrophes; concern statements are full
    # questions, so every adapter call was carrying punctuation the APIs
    # reject (measured 2026-08-11).
    from newz.world.sources import clean_query

    q = clean_query("How does Montaigne's concept anticipate Jung's theories?")
    assert "?" not in q and "'" not in q
    assert "Montaigne" in q and "Jung" in q


def test_every_enabled_adapter_builds_a_well_formed_request():
    # A broken adapter is indistinguishable from an empty result, because
    # failures are caught per-adapter. This asserts the request shape
    # instead of trusting the empty list (a mangled arXiv parameter name
    # survived the suite once by exactly this route).
    import urllib.parse

    from newz.world.sources import (
        ArxivAdapter, OpenAlexAdapter, PubMedAdapter, SecEdgarAdapter,
        WikipediaAdapter,
    )

    seen: list[str] = []

    class RecordingFetcher:
        def get(self, url):
            seen.append(url)
            raise RuntimeError("stop here — the URL is what is under test")

    f = RecordingFetcher()
    for adapter in (WikipediaAdapter(f), ArxivAdapter(f), OpenAlexAdapter(f),
                    PubMedAdapter(f), SecEdgarAdapter(f)):
        adapter.search("collective unconscious", limit=2)

    assert len(seen) == 5
    expected_params = {
        "wikipedia.org": "srsearch",
        "arxiv.org": "search_query",
        "openalex.org": "search",
        "ncbi.nlm.nih.gov": "term",
        "sec.gov": "q",
    }
    for url in seen:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        host = next(h for h in expected_params if h in url)
        key = expected_params[host]
        assert key in params, f"{host}: missing {key!r} in {sorted(params)}"
        assert "collective unconscious" in params[key][0]


def test_identical_urls_are_read_once(tmp_path):
    # Several formed queries hit overlapping results; the same page must not
    # be extracted (and charged to the diet) twice.
    log = _log(tmp_path, [_call("deliberation", 9000)])
    llm = FakeLLM([KEEP_FIRST, CLEAN_EXTRACT])
    out = research(llm, "q", log_path=log,
                   adapters=[StubAdapter([RESULT]), StubAdapter([RESULT])],
                   form_queries=False)
    assert len(out.results) == 1


def test_question_formation_produces_search_terms(tmp_path):
    from newz.world.question import search_queries

    llm = FakeLLM([("AMBIENT", """<queries>
      <q>Montaigne self-knowledge essays</q>
      <q>Jung collective unconscious archetypes</q>
    </queries>""")])
    qs = search_queries(llm, "How does Montaigne's concept of the unconscious "
                             "anticipate Jung's later theories?")
    assert qs == ["Montaigne self-knowledge essays",
                  "Jung collective unconscious archetypes"]
    assert all("?" not in q for q in qs)


def test_question_formation_falls_back_to_the_cleaned_question(tmp_path):
    from newz.world.question import search_queries

    llm = FakeLLM([("AMBIENT", "not xml")])
    qs = search_queries(llm, "Why do whales blow bubbles?")
    assert qs == ["Why do whales blow bubbles"]      # usable, punctuation gone


# ── R1: research must not re-read what it already read ───────────────────
#
# Measured 2026-08-14. `seen_urls` deduped only WITHIN one call, across the
# three query angles, and had no memory between calls. The concern statement
# never changes, so the same queries returned the same urls: concern 111
# accumulated 16 reads of 4 distinct sources. Each deliberation then reasoned
# over an unchanged dossier and produced an identical conclusion — novelty
# -0.00, recorded as "restated", which said the being circled when it had
# been handed nothing.

def _concern_row(store, concern_id):
    """ingest_log.concern_id is a real foreign key."""
    store.execute(
        "INSERT OR IGNORE INTO concerns (id, opened_at, kind, statement,"
        " why_open, closing_condition, status, salience, origin)"
        " VALUES (?,0,'inquiry','q','w','c','open',0.5,'curiosity')", (concern_id,))
    store.commit()


def _already_read_row(store, concern_id, source, skipped=None):
    _concern_row(store, concern_id)
    store.execute(
        "INSERT INTO ingest_log (ts, outlet, source, query, concern_id,"
        " claims_kept, quarantined, skipped) VALUES (?,?,?,?,?,3,0,?)",
        (time.time(), source.split(":", 1)[0], source, "q", concern_id, skipped))
    store.commit()


class _FixedAdapter:
    name = "fixed"

    def __init__(self, results):
        self._results = results

    def search(self, query, limit=2):
        return list(self._results)


def _result(url, title="A paper"):
    return SearchResult(source="fixed", title=title, summary="Some text.", url=url)


def test_a_source_already_read_for_this_concern_is_not_offered_again(store, tmp_path):
    log = _log(tmp_path, [_call("deliberation", 9000)])
    _already_read_row(store, 111, "fixed:https://example.org/a")
    adapters = [_FixedAdapter([_result("https://example.org/a"),
                               _result("https://example.org/b")])]
    out = research(FakeLLM([KEEP_NOTHING]), "a question", log_path=log,
                   adapters=adapters, conn=store, concern_id=111,
                   form_queries=False)
    assert [r.url for r in out.results] == ["https://example.org/b"]
    assert out.already_read == 1


def test_exhausting_the_adapters_is_a_DIFFERENT_gap_from_nothing_answering(
        store, tmp_path):
    # The gap record is what source_review reads, and the two cases call for
    # different remedies: "nothing answered" suggests the question is
    # malformed; "I have read everything" says the ADAPTER SET is exhausted
    # for this question, which is a source-coverage decision.
    log = _log(tmp_path, [_call("deliberation", 9000)])
    _already_read_row(store, 111, "fixed:https://example.org/a")
    adapters = [_FixedAdapter([_result("https://example.org/a")])]
    out = research(FakeLLM([]), "a question", log_path=log, adapters=adapters,
                   conn=store, concern_id=111, form_queries=False)
    assert out.results == []
    assert "already read everything" in out.gap


def test_nothing_answering_still_reads_as_nothing_answering(store, tmp_path):
    log = _log(tmp_path, [_call("deliberation", 9000)])
    out = research(FakeLLM([]), "a question", log_path=log,
                   adapters=[_FixedAdapter([])], conn=store, concern_id=111,
                   form_queries=False)
    assert out.gap.startswith("no source answered")


def test_a_share_capped_source_may_be_offered_again(store, tmp_path):
    # The being never saw it: a capped row is accounting, not reading.
    log = _log(tmp_path, [_call("deliberation", 9000)])
    _already_read_row(store, 111, "fixed:https://example.org/a", skipped="share_cap")
    adapters = [_FixedAdapter([_result("https://example.org/a")])]
    out = research(FakeLLM([KEEP_NOTHING]), "a question", log_path=log,
                   adapters=adapters, conn=store, concern_id=111,
                   form_queries=False)
    assert [r.url for r in out.results] == ["https://example.org/a"]
    assert out.already_read == 0


def test_a_source_read_for_ANOTHER_concern_is_still_offered(store, tmp_path):
    log = _log(tmp_path, [_call("deliberation", 9000)])
    _already_read_row(store, 108, "fixed:https://example.org/a")
    adapters = [_FixedAdapter([_result("https://example.org/a")])]
    out = research(FakeLLM([KEEP_NOTHING]), "a question", log_path=log,
                   adapters=adapters, conn=store, concern_id=111,
                   form_queries=False)
    assert [r.url for r in out.results] == ["https://example.org/a"]


def test_research_without_a_store_still_works(tmp_path):
    log = _log(tmp_path, [_call("deliberation", 9000)])
    out = research(FakeLLM([KEEP_NOTHING]), "a question", log_path=log,
                   adapters=[_FixedAdapter([_result("https://example.org/a")])],
                   conn=None, concern_id=None, form_queries=False)
    assert [r.url for r in out.results] == ["https://example.org/a"]


def test_a_refusal_is_not_written_to_the_gap_record_as_an_absence(store, tmp_path):
    # 2026-08-15. source_gaps is what source_review reads to decide which
    # sources to ADD (S2 §9.1). A fully-capped cycle wrote "nothing was
    # relevant enough to read" into it, when the truth was "I found answers
    # and declined to read them" — the cap corrupting the very evidence that
    # would have said the diet needs widening.
    from newz.world.diet import MIN_ITEMS_FOR_CAP, record_read

    for i in range(MIN_ITEMS_FOR_CAP):
        record_read(store, source=f"stub:https://hog.example/{i}", query="q",
                    concern_id=None, claims_kept=1, quarantined=0)
    for host in ("a", "b", "c", "d"):
        for i in range(3):
            record_read(store, source=f"{host}:https://{host}.example/{i}",
                        query="q", concern_id=None, claims_kept=1, quarantined=0)

    log = _log(tmp_path, [_call("deliberation", 900_000)])
    a = SearchResult(title="A", summary="one", url="https://hog.example/x",
                     source="stub")
    b = SearchResult(title="B", summary="two", url="https://hog.example/y",
                     source="stub")
    keep_both = ("AMBIENT", '<triage><keep n="1"/><keep n="2"/></triage>')
    nothing_extracted = ("AMBIENT",
                         "<extraction><manipulation>none</manipulation></extraction>")
    llm = FakeLLM([keep_both, nothing_extracted])
    out = research(llm, "a question", log_path=log, conn=store,
                   adapters=[StubAdapter([a, b])], form_queries=False)

    # One was promoted and read past the cap rather than the concern getting
    # nothing; the other was held back, and the gap says so rather than
    # claiming the world was silent.
    assert out.capped == 1
    assert out.gap
    assert "deferral, not an absence" in out.gap
    assert "no source answered" not in out.gap


def test_research_directs_extraction_at_the_concern(tmp_path):
    # Rule 2: a `question` parameter nothing passes is dead code. `query` in
    # research() IS the concern statement — lite.py passes
    # choice.concern.statement — so this is where S2 §9.1's "material that
    # touches a concern" becomes operative rather than aspirational.
    log = _log(tmp_path, [_call("deliberation", 900_000)])
    llm = FakeLLM([KEEP_FIRST, CLEAN_EXTRACT])
    out = research(llm, "why do sperm whales blow bubbles", log_path=log,
                   adapters=[StubAdapter([RESULT])], form_queries=False)
    assert out.claims
    extract_call = llm.calls[-1]["user"]
    assert "<my_question>why do sperm whales blow bubbles</my_question>" \
        in extract_call
    assert "Extracting nothing is a good and common answer" in extract_call


def test_the_feed_path_stays_undirected(store, tmp_path):
    # A feed item arrives with no concern attached. Directing it at whatever
    # concern happened to be deliberating would be a fabricated relevance —
    # that is #9's open design decision, not an oversight.
    from newz.world.extract import extract_claims

    llm = FakeLLM([CLEAN_EXTRACT])
    extract_claims(llm, "a feed item", source="feed:bbc")
    assert "<my_question>" not in llm.calls[0]["user"]


# ── full-text reading (2026-08-15) ───────────────────────────────────────
#
# S2 §9.1's other half. Until now every read was search-result metadata, and
# the being said so in its own gap record eight times per concern: "the
# retrieval slice contains only the headline", "thin on the how", "only the
# opening sentence of the study".

PAGE = ("Settlement Windows and Price Discovery\n\n"
        + ("Participants submitted quotes on a rolling basis and the clearing "
           "price was struck at the close of each window. " * 40))


class _Page:
    """A fetcher that returns one body, or raises."""

    def __init__(self, body=PAGE, boom=False):
        self.body, self.boom, self.calls = body, boom, []

    def get(self, url):
        self.calls.append(url)
        if self.boom:
            raise RuntimeError("robots.txt disallows it")
        return self.body


def _deep_llm(chunks_of_claims):
    """One triage call, then one extraction per chunk."""
    out = [KEEP_FIRST]
    for claims in chunks_of_claims:
        body = "".join(f'<claim confidence="0.9">{c}</claim>' for c in claims)
        out.append(("AMBIENT",
                    f"<extraction>{body}<manipulation>none</manipulation></extraction>"))
    return FakeLLM(out)


def test_a_document_is_read_past_its_abstract(store, tmp_path):
    log = _log(tmp_path, [_call("deliberation", 900_000)])
    page = _Page()
    llm = _deep_llm([["The clearing price is struck at the window close."],
                     ["Volumes were thin in the first quarter."]])
    out = research(llm, "how are settlement windows priced", log_path=log,
                   conn=store, adapters=[StubAdapter([RESULT])],
                   form_queries=False, fetcher=page)

    assert page.calls == [RESULT.url], "the document was never fetched"
    assert out.full_text_reads == 1
    assert len(out.claims) == 2
    row = store.execute("SELECT depth, chunks, claims_kept FROM ingest_log").fetchone()
    assert row["depth"] == "full" and row["chunks"] >= 2 and row["claims_kept"] == 2


def test_a_fetch_failure_falls_back_to_the_abstract(store, tmp_path):
    # "Never worse than today" — the R3 proposal's guarantee, made true.
    log = _log(tmp_path, [_call("deliberation", 900_000)])
    llm = FakeLLM([KEEP_FIRST, CLEAN_EXTRACT])
    out = research(llm, "a question", log_path=log, conn=store,
                   adapters=[StubAdapter([RESULT])], form_queries=False,
                   fetcher=_Page(boom=True))

    assert out.claims, "the abstract path did not run"
    assert out.full_text_reads == 0
    assert store.execute("SELECT depth FROM ingest_log").fetchone()[0] == "abstract"


def test_a_document_that_yields_nothing_falls_back_to_the_abstract(store, tmp_path):
    log = _log(tmp_path, [_call("deliberation", 900_000)])
    empty = ("AMBIENT", "<extraction><manipulation>none</manipulation></extraction>")
    # triage, then two empty chunk extractions, then the abstract extraction
    llm = FakeLLM([KEEP_FIRST, empty, empty, empty, CLEAN_EXTRACT])
    out = research(llm, "a question", log_path=log, conn=store,
                   adapters=[StubAdapter([RESULT])], form_queries=False,
                   fetcher=_Page())

    assert out.full_text_reads == 0
    assert out.claims, "falling back must not lose the abstract"
    assert store.execute("SELECT depth FROM ingest_log").fetchone()[0] == "abstract"


def test_one_hostile_chunk_quarantines_the_whole_document(store, tmp_path):
    # THE HARD REQUIREMENT FROM #7. extract_claims quarantines the ITEM it was
    # given; under chunking that is one 2,000-char window, so a hostile page
    # would still contribute the claims from its clean chunks.
    log = _log(tmp_path, [_call("deliberation", 900_000)])
    clean = ("AMBIENT", '<extraction><claim confidence="0.9">A real claim.'
             '</claim><manipulation>none</manipulation></extraction>')
    llm = FakeLLM([KEEP_FIRST, clean, HOSTILE_EXTRACT])
    out = research(llm, "a question", log_path=log, conn=store,
                   adapters=[StubAdapter([RESULT])], form_queries=False,
                   fetcher=_Page())

    assert out.claims == [], "a clean chunk of a hostile document leaked"
    assert out.hostile_documents == 1
    assert not any("ZXQ-BREACH" in c for c, _ in out.claims)
    row = store.execute("SELECT depth, claims_kept, quarantined FROM ingest_log").fetchone()
    assert row["depth"] == "full" and row["claims_kept"] == 0
    # AND no fallback to the abstract: the abstract describes the same
    # document that just tried to instruct the being.
    assert store.execute("SELECT COUNT(*) FROM ingest_log").fetchone()[0] == 1
    assert store.execute("SELECT COUNT(*) FROM episodes WHERE kind='reading'"
                         ).fetchone()[0] == 0


def test_claims_repeated_across_the_chunk_overlap_are_deduped(store, tmp_path):
    log = _log(tmp_path, [_call("deliberation", 900_000)])
    llm = _deep_llm([["The clearing price is struck at the window close."],
                     ["The clearing price is struck at the window close."]])
    out = research(llm, "a question", log_path=log, conn=store,
                   adapters=[StubAdapter([RESULT])], form_queries=False,
                   fetcher=_Page())
    assert len(out.claims) == 1


def test_full_text_reading_still_obeys_the_budget_gate(tmp_path):
    # INV-038's shape: the diet is checked before any HTTP, so a paused diet
    # means the document is never fetched either.
    log = _log(tmp_path, [_call("ingest", 9000), _call("deliberation", 10)])
    page = _Page()
    out = research(FakeLLM([]), "a question", log_path=log,
                   adapters=[StubAdapter([RESULT])], form_queries=False,
                   fetcher=page)
    assert out.paused and page.calls == []
