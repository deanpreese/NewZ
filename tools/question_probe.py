#!/usr/bin/env python3
"""Does telling the query former what already failed change what it finds?

The method of `claim_door_probe.py` and `retrodiction_probe.py`: real material,
**expectations fixed BEFORE the calls**, run against the live model and the
live adapters.

**Why.** Measured 2026-08-30: 146 source gaps across only 29 distinct
questions, concentrated hard — one question asked **17 times**, the next 14, 11,
10. In those passes 753 of 761 candidates were refused by triage and only 8 by
the 0.35 floor, at an average best relevance of 0.578. The material was topical
and triage still declined it.

The mechanism is not strictness. `search_queries` turns the concern statement
into terms at temperature 0.2 and **has no memory of any previous attempt** —
there is no reference to gaps, attempts or prior searches anywhere in
`question.py`. Same statement, same terms, same ranked candidates. R1's dedup
(2026-08-14) then excludes what was already read for that concern, so the good
material was consumed on pass one and every repeat sees a worse tail. Triage
refuses the tail, correctly. `research.py` says it in its own comment: *"the
concern statement never changes, so question.py forms the same queries every
cycle and the adapters return the same urls."*

R1 fixed READING the same source sixteen times. It left ASKING the same
question seventeen times and reading nothing.

**The proposed fix is to tell the query former what has already failed.** This
probe asks whether that would do anything, before any of it is built.

  BASELINE   `search_queries` exactly as it runs today.
  TREATMENT  the same call with the baseline's own terms marked as tried and
             fruitless — which is precisely the being's situation on pass two
             and every pass after.

Both term sets are then run through the real adapters and the real relevance
floor, and the urls compared.

**Four outcomes, and only one of them is worth building.**

  H0  the terms DO NOT MOVE. Told its terms failed, the model returns them
      anyway. The fix is dead and the constraint is somewhere else entirely.
  H1  the terms move, the CANDIDATES do not. Different words, same index
      results. The fix is decoration — it would spend a call per pass to
      rediscover the same urls.
  H2  the terms move and NEW candidates appear, at comparable relevance. The
      fix is worth building: the being has been re-asking a question whose
      other angles were reachable all along.
  H3  the terms move and the new candidates are WORSE. The fix would find junk
      faster, into a corpus where 7.2% of sources are ever cited. This is the
      outcome hardest to act on and it must be looked for rather than hoped
      against.

**The expectation, fixed before any call was made: H2**, and held loosely. The
adapters are keyword search over academic indexes, so different terms plausibly
return different rows. Whether the new rows are any *better* is the part I do
not know, and H1 is the serious risk — a model told "not those" may only
paraphrase.

**Writes nothing.** The store is opened read-only and only `source_gaps` is
read. Adapter traffic goes through the ordinary `Fetcher`, so robots and the
per-domain rate limits apply.

  python tools/question_probe.py             # the 4 most-repeated questions
  python tools/question_probe.py --top 6
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.llm.xml_parser import extract_xml
from newz.world.question import MAX_QUERIES, _SYSTEM, _TASK, search_queries
from newz.world.sources import clean_query, default_adapters

W = 74
RELEVANCE_FLOOR = 0.35


def stuck_questions(conn, top: int) -> list[tuple[str, int]]:
    """The questions the being keeps asking and keeps getting nothing for."""
    return conn.execute(
        "SELECT query, COUNT(*) n FROM source_gaps WHERE cause='triage'"
        " GROUP BY query ORDER BY n DESC LIMIT ?", (top,)).fetchall()


def informed_queries(client, question: str, tried: list[str]) -> list[str]:
    """`search_queries` with the failed terms named.

    Built inline rather than by changing `question.py`, so nothing ships on the
    strength of a probe that has not run. The task text is the shipped one plus
    one block — the smallest difference that can answer the question.
    """
    block = (
        "\n\n<already_tried>\n"
        "These searches were already run for this question and returned nothing\n"
        "worth reading. Do not repeat them or reword them; the indexes have\n"
        "been asked and answered. Find angles these did not cover — a\n"
        "different discipline, a different entity, the mechanism rather than\n"
        "the phenomenon, the phenomenon rather than the mechanism.\n"
        + "\n".join(f"  - {t}" for t in tried)
        + "\n</already_tried>")
    try:
        result = client.complete(
            "AMBIENT", _SYSTEM,
            f"{_TASK}{block}\n\n<question>{question}</question>",
            max_tokens=250, temperature=0.2, function="ingest")
        root = extract_xml(result.text, "queries")
    except Exception as e:  # noqa: BLE001
        print(f"    (treatment call unusable: {e})")
        return []
    out: list[str] = []
    for el in root.findall("q"):
        q = clean_query((el.text or "").strip(), max_words=8)
        if q and q.lower() not in {o.lower() for o in out}:
            out.append(q)
    return out[:MAX_QUERIES]


def candidates_for(terms: list[str], adapters, embedder, question: str):
    """Every url the adapters return for these terms, with its relevance."""
    from newz.memory.embeddings import cosine

    found: dict[str, tuple[str, str]] = {}
    for adapter in adapters:
        for term in terms:
            try:
                for r in adapter.search(term, limit=3):
                    if r.url and r.url not in found:
                        found[r.url] = (r.title, f"{r.title} {r.summary}")
            except Exception:  # noqa: BLE001
                continue
    if not found or embedder is None:
        return {u: (t, None) for u, (t, _) in found.items()}
    try:
        vecs = embedder.embed([question] + [b for _, b in found.values()])
        scores = [cosine(vecs[0], v) for v in vecs[1:]]
    except Exception:  # noqa: BLE001
        return {u: (t, None) for u, (t, _) in found.items()}
    return {u: (t, s) for (u, (t, _)), s in zip(found.items(), scores)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=4,
                    help="how many of the most-repeated questions to probe")
    a = ap.parse_args()

    cfg = load()
    client = LLMClient(cfg, timeout=300)
    conn = sqlite3.connect(f"file:{cfg.main_db_path}?mode=ro", uri=True)
    try:
        from newz.memory.embeddings import Embedder
        embedder = Embedder(cfg)
    except Exception:  # noqa: BLE001
        embedder = None
        print("  (no embedder — relevance is not scored this run)")

    adapters = default_adapters()
    rows = stuck_questions(conn, a.top)

    print(f"\nquestion probe — {len(rows)} of the most-repeated questions")
    print(f"  expectation recorded before running: H2 (terms move, new "
          f"candidates appear)")
    print(f"  store read-only · live adapters · live model\n")

    moved = new_urls = worse = 0
    for question, times in rows:
        print("=" * W)
        print(f"asked {times}×  ·  {question[:110]}")

        base = search_queries(client, question)
        treat = informed_queries(client, question, base)
        print(f"  baseline   {' | '.join(base)}")
        print(f"  treatment  {' | '.join(treat) if treat else '(none)'}")

        same = {t.lower() for t in base} == {t.lower() for t in treat}
        if treat and not same:
            moved += 1
        print(f"  terms      {'UNCHANGED' if same or not treat else 'moved'}")

        b = candidates_for(base, adapters, embedder, question)
        t = candidates_for(treat, adapters, embedder, question) if treat else {}
        fresh = set(t) - set(b)
        if fresh:
            new_urls += 1

        def best(d):
            s = [v[1] for v in d.values() if v[1] is not None]
            return max(s) if s else None

        bb, tb = best(b), best(t)
        print(f"  candidates baseline {len(b)}, treatment {len(t)}, "
              f"NEW {len(fresh)}")
        if bb is not None and tb is not None:
            print(f"  best score baseline {bb:.3f}, treatment {tb:.3f}")
            if tb < bb - 0.05:
                worse += 1
        for u in list(fresh)[:3]:
            sc = t[u][1]
            print(f"     + [{sc:.2f}] {t[u][0][:64]}" if sc is not None
                  else f"     + {t[u][0][:64]}")

    print("\n" + "=" * W)
    n = len(rows)
    print(f"  terms moved            {moved}/{n}")
    print(f"  new candidates found   {new_urls}/{n}")
    print(f"  treatment scored worse {worse}/{n}")
    print()
    if moved == 0:
        print("  H0 — THE TERMS DO NOT MOVE. Told its own searches returned")
        print("  nothing, the model offers them again. Telling the query former")
        print("  what failed cannot help, and the constraint is elsewhere.")
    elif new_urls == 0:
        print("  H1 — DECORATION. The words change and the indexes return the")
        print("  same rows, so a repeat pass would spend a call to rediscover")
        print("  what it already had. Do not build this.")
    elif worse >= max(1, new_urls // 2):
        print("  H3 — NEW BUT WORSE. Fresh candidates arrive at materially lower")
        print("  relevance, so this would find junk faster into a corpus where")
        print("  7.2% of sources are ever cited. The floor and triage would")
        print("  still refuse them — more gaps, not more reading.")
    else:
        print(f"  H2 — WORTH BUILDING. Terms moved on {moved} of {n} and brought")
        print("  candidates the being had never been offered, at comparable")
        print("  relevance. It has been re-asking questions whose other angles")
        print("  were reachable the whole time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
