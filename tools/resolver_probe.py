#!/usr/bin/env python3
"""Does the resolver work at all, and where does it fail? (P4 epic E1.3 / S1-E)

The method of `claim_door_probe.py`: real material, **hypotheses and an
expectation written down BEFORE the calls**, run against the live model.

**Why now.** `resolver.py::workable_claims` selects `due_at <= now`. Nothing
has ever been due, so `resolve_claim` has never executed once in life — not the
search, not the extraction, not the DEEP verdict, not the VERBATIM check
(INV-047), not the cost through INV-031, not the one `world`-provenance episode
sleep would ever see. Thirty-one claims are open, `attempts` is 0 on all of
them, and the first real execution is **2026-09-02**.

S1-E is the read PLAN calls the single most important one in the plan, and
Phase 1 carries the entire outer loop alone. Finding out on 2026-09-02 that the
path does not work is finding out four days late, and the failure is quiet:
`resolve_claim` records a failure, leaves the claim OPEN, and after four honest
attempts stops retrying. Nothing raises. Nothing alarms.

**Five hypotheses this separates.**

  H0  the path works end to end — a claim reaches a verdict whose quote is
      verbatim in the fetched material, and settles.
  H1  RETRIEVAL. `research()` returns nothing usable and the claim fails at
      "nothing came back from the source". The resolver's query is
      `f"{claim.resolver}: {claim.claim}"` and it goes through the same
      adapters, the same 0.35 relevance floor and the same triage call that
      produced 68 `cause='triage'` source gaps in seven days.
  H2  UNSUPPORTED. Material comes back, the model returns a verdict, and the
      quote is not verbatim in the material — so INV-047 refuses it. The
      material is a list of *extracted claim texts*, not page prose, and a
      model asked to quote from a list it has just been shown may paraphrase.
  H3  NOT SETTLED. Material comes back and the model says honestly that it
      does not settle the claim. This is the resolver working correctly and
      the *claim* being unanswerable by what the adapters can reach.
  H4  MALFORMED. The verdict is unreadable or names no outcome — a prompt or
      parser fault, and the cheapest of the five to fix.

**The expectation, fixed before any call was made: H1.** The claims due first
name `Federal Reserve H.4.1 Statistical Release`, `New York Fed Daily H.15`
and `ICE BofA US Dollar Index`. The adapter set is wikipedia, arxiv, openalex,
pubmed, sec_edgar and gdelt — an academic-paper and news set. **A statistical
release is not a paper**, and only gdelt could reach coverage of one. If H1
holds, the finding is not that the resolver is broken: it is that the being
names resolvers its own world cannot reach, and the fix is upstream at the
claim door, not here.

H2 is the second expectation and would be the more serious one, because it
would mean the path fails at its last step after paying for every earlier one.

**Writes nothing to the being.** `resolve_claim` books an attempt, records
failures, writes `source_gaps` and `ingest_log` rows and can settle a claim, so
this runs against a **throwaway copy** of the store — same code, same caps,
same failure paths. The live store is opened nowhere in write mode.

**The two log paths are deliberately different, and the first run got it
wrong.** `research()` reads §9.1's budget from the log path it is *given*, and
that ceiling is a ratio: reading is earned by thinking. A probe pointed at a
fresh log therefore sees zero deliberation in the window and is refused all
ingest — *"the invariant permits no ingest at all"* — which is what happened on
2026-08-28 09:04 and tested nothing. So the **budget is read from the live
call log**, which is the condition the resolver actually runs under, while the
probe's own calls are **recorded to `logs/probe_calls.jsonl`** so the being's
telemetry, diet accounting and health numbers stay clean.

The trade-off is stated rather than hidden: a handful of probe reads consume
real ingest capacity and are not charged for it. For a one-shot diagnostic that
is the right side to err on; for anything repeated it would not be.

  python tools/resolver_probe.py              # the 3 claims due soonest
  python tools/resolver_probe.py --claims 5
  python tools/resolver_probe.py --id 21      # one named claim
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.llm.recorder import CallRecorder
from newz.memory.embeddings import Embedder
from newz.resolutions.model import Claim
from newz.resolutions.resolver import resolve_claim
from newz.store.db import open_db

W = 74


def stage_of(out) -> str:
    """Which of the five hypotheses this outcome is evidence for.

    Keyed on the failure strings `resolve_claim` itself writes, so the
    taxonomy cannot drift from the code it describes without the fallback
    firing and saying so.
    """
    if out.settled:
        return "SETTLED"
    f = (out.failure or "").lower()
    if f.startswith("ingest paused"):
        return "DIET"
    if "nothing came back from the source" in f:
        return "RETRIEVAL"
    if "quote is not in the material" in f:
        return "UNSUPPORTED"
    if "verdict unreadable" in f:
        return "MALFORMED"
    if "named no outcome" in f:
        return "MALFORMED"
    return "NOT SETTLED"


HYPOTHESIS = {
    "SETTLED": "H0 — the path works end to end.",
    "RETRIEVAL": "H1 — the adapters cannot reach the source the claim named.",
    "UNSUPPORTED": "H2 — the verbatim check refused the verdict (INV-047).",
    "NOT SETTLED": "H3 — the material came back and honestly did not settle it.",
    "MALFORMED": "H4 — the verdict was unreadable or named no outcome.",
    "DIET": "the diet paused ingest; nothing about the resolver was tested.",
}


def claims_to_probe(conn: sqlite3.Connection, *, limit: int,
                    only: int | None) -> list[Claim]:
    """Real open claims, due soonest first — the ones that fire on 2026-09-02."""
    sql = ("SELECT id, opened_at, claim, resolution_condition, resolver, due_at,"
           " provenance, status, outcome, settled_at, settled_by, settled_note"
           " FROM resolutions WHERE status='open'")
    args: tuple = ()
    if only is not None:
        sql += " AND id=?"
        args = (only,)
    sql += " ORDER BY due_at LIMIT ?"
    rows = conn.execute(sql, (*args, limit)).fetchall()
    return [Claim(
        id=r["id"], claim=r["claim"],
        resolution_condition=r["resolution_condition"], resolver=r["resolver"],
        due_at=r["due_at"], provenance=r["provenance"], opened_at=r["opened_at"],
        status=r["status"], outcome=r["outcome"], settled_at=r["settled_at"],
        settled_by=r["settled_by"], settled_note=r["settled_note"]) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claims", type=int, default=3,
                    help="how many open claims to probe, due soonest first")
    ap.add_argument("--id", type=int, default=None, help="probe one claim by id")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO if a.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)-5s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    cfg = load()
    probe_log = cfg.repo_root / "logs" / "probe_calls.jsonl"
    # Read the budget from the being's own log — §9.1's ceiling is a ratio and
    # an empty log means no deliberation, therefore no ingest. Record to the
    # probe's log, so a diagnostic never enters the being's telemetry.
    budget_log = cfg.repo_root / "logs" / "llm_calls.jsonl"
    client = LLMClient(cfg, timeout=600, recorder=CallRecorder(probe_log))
    try:
        embedder = Embedder(cfg)
    except Exception:  # noqa: BLE001
        embedder = None
        print("  (no embedder — the 0.35 relevance floor is skipped this run)")

    tmp = Path(tempfile.mkdtemp(prefix="resolver-probe-"))
    copy = tmp / "probe.db"
    shutil.copy2(cfg.main_db_path, copy)
    conn = open_db(copy)
    conn.row_factory = sqlite3.Row

    claims = claims_to_probe(conn, limit=a.claims, only=a.id)
    if not claims:
        print("no open claims to probe")
        return 1

    print(f"resolver probe — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"  store copy   {copy}   (the live store is not opened for writing)")
    print(f"  call log     {probe_log.relative_to(cfg.repo_root)}"
          f"   (the being's telemetry is untouched)")
    print(f"  budget read  {budget_log.relative_to(cfg.repo_root)}"
          f"   (§9.1 earns reading from thinking; a fresh log permits none)")
    print(f"  expectation recorded before running: H1 (RETRIEVAL)")
    print(f"\n{len(claims)} claim(s), due soonest first\n" + "=" * W)

    stages: list[tuple[int, str, str]] = []
    for c in claims:
        reads_before = conn.execute("SELECT COUNT(*) FROM ingest_log").fetchone()[0]
        gaps_before = conn.execute("SELECT COUNT(*) FROM source_gaps").fetchone()[0]

        print(f"\nclaim {c.id}  ·  due {datetime.fromtimestamp(c.due_at):%Y-%m-%d}"
              f"  ·  opened {datetime.fromtimestamp(c.opened_at):%m-%d}")
        print(f"  claim     {c.claim[:200]}")
        print(f"  settles   {c.resolution_condition[:200]}")
        print(f"  resolver  {c.resolver[:200]}")
        print(f"  query     {c.resolver}: {c.claim}"[:W + 12])

        out = resolve_claim(conn, client, c, log_path=budget_log,
                            embedder=embedder)

        reads = conn.execute("SELECT COUNT(*) FROM ingest_log").fetchone()[0] - reads_before
        kept = conn.execute(
            "SELECT COUNT(*) FROM ingest_log WHERE claims_kept > 0"
            " AND id > (SELECT COALESCE(MAX(id),0) - ? FROM ingest_log)",
            (reads,)).fetchone()[0] if reads else 0
        gap = conn.execute(
            "SELECT cause, candidates, rejected_triage, rejected_floor, best_score"
            " FROM source_gaps ORDER BY id DESC LIMIT 1").fetchone() \
            if conn.execute("SELECT COUNT(*) FROM source_gaps").fetchone()[0] > gaps_before \
            else None

        print(f"  ── read    {reads} source(s) logged, {kept} yielded claims")
        if gap is not None:
            print(f"     gap     cause={gap['cause']} candidates={gap['candidates']}"
                  f" triage_rejected={gap['rejected_triage']}"
                  f" floor_rejected={gap['rejected_floor']}"
                  f" best={gap['best_score']}")

        stage = stage_of(out)
        if out.settled:
            note = conn.execute(
                "SELECT settled_note FROM resolutions WHERE id=?",
                (c.id,)).fetchone()["settled_note"]
            print(f"  ── STAGE   SETTLED  {out.outcome}  by {str(out.source)[:60]}")
            print(f"     quote   {str(note)[:200]}")
        else:
            print(f"  ── STAGE   {stage}")
            print(f"     why     {out.failure}")
        stages.append((c.id, stage, out.failure or ""))

    print("\n" + "=" * W)
    counts: dict[str, int] = {}
    for _, s, _ in stages:
        counts[s] = counts.get(s, 0) + 1
    for s, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {s:<12} {n}/{len(stages)}   {HYPOTHESIS.get(s, '')}")

    print()
    if counts.get("DIET"):
        print("  NOTHING WAS TESTED on at least one claim. The diet refused the")
        print("  ingest before the resolver reached the world, so no hypothesis")
        print("  above is supported or refuted by that claim. Re-run when §9.1")
        print("  permits reading; `python tools/budget.py` says whether it does.")
    elif counts.get("SETTLED"):
        print("  The path executes end to end. Whatever else is true, the")
        print("  mechanism S1-E depends on is not dead on arrival.")
    elif counts.get("RETRIEVAL") == len(stages):
        print("  H1 confirmed on this sample. The resolver is not broken — it was")
        print("  never reached. The claims name statistical releases and the")
        print("  adapters index papers and news, so the fix is at the claim door:")
        print("  a resolver the being's own world cannot reach should be refused")
        print("  the way an unreadable date already is (INV-046's shape).")
    elif counts.get("UNSUPPORTED"):
        print("  H2 on at least one claim. The path pays for search, extraction")
        print("  and a DEEP call and then refuses its own verdict at the last")
        print("  step. INV-047 is doing exactly what it was written to do; what")
        print("  needs looking at is whether `material` is quotable at all,")
        print("  since it is a list of extracted claim texts and not page prose.")
    elif counts.get("MALFORMED"):
        print("  H4. A prompt or parser fault, and the cheapest of the five to")
        print("  fix. Repair it and re-run before reading anything else here.")
    else:
        print("  H3. The resolver reached the world, the world answered, and the")
        print("  material did not settle the claim. That is the mechanism working")
        print("  and the claim being unanswerable by what the adapters reach.")

    print(f"\n  copy left at {tmp} — delete it when you are done reading.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
