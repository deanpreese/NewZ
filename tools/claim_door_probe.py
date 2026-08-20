"""Does the claim door decline because it is correctly strict, or because it
declines everything? (P4 epic E1.2 / S1-E)

The method that settled R-27 for the reading opener and R-21 for the
conversation opener: real-shaped material, **expected verdicts written down
BEFORE the calls**, run against the live model.

The read that prompted this, 2026-08-19: the door was called 27 times between
06:26 and 18:07 — once per accepted advance — and returned
`<worth_claiming>no</worth_claiming>` 27 times out of 27. `resolutions`,
`claim_refusals` and `claim_costs` are all empty, and INV-046 records refusals
but deliberately not declines, so the store cannot tell "never asked" from
"asked 27 times and declined". Only the call log could.

**Three hypotheses this separates.**

  H1  the door is over-strict — it would decline a clean, dated, sourced,
      world-facing claim. Fix is the prompt (this is what R-27 turned out to
      be for the opener).
  H2  the door is right, and what deliberation establishes is genuinely not
      claimable. Fix is upstream, in what an advance is allowed to be.
  H3  some real advances were claimable and the door missed them.

CONTROLS decide H1: two that must pass, two that must decline, in fields the
being does not work in so it cannot reuse remembered wording. If the door
declines the passing controls, H1 holds and nothing else in this probe matters.

REAL CASES decide H2 against H3: every advance the door actually saw today,
replayed. The expectation recorded here before running was **decline for all of
them** — every v2 advance ever recorded is kind='reasoning' (84 of 84), and all
28 of today's open with a first-person cognition verb ("I distinguished…",
"I identified…", "I realized…"). Those are restatements of what the being now
thinks, which is the prompt's own worked NO example. If the door declines them
AND passes the controls, the door is working and Phase 1's problem is that
deliberation never establishes anything the world could contradict.

**Writes nothing.** propose_claim calls open_claim on accept, so this runs
against a throwaway copy of the store — same code, same caps, same refusal
path, and the live store is opened read-only to read the advances out.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.resolutions.door import propose_claim
from newz.store.db import open_db

DOOR_SHIPPED = datetime(2026, 8, 19, 6, 26).timestamp()

# ── Controls. Expected verdicts fixed before any call was made. ──────────
# Deliberately outside the being's subjects (market microstructure, AI usage
# data) so it must do the judgment rather than recognise the words.
CONTROLS = [
    ("C1 PASS — a dated, sourced consequence about the world", True,
     "Concern: what makes a national statistical revision predictable?",
     "The initial employment print for a month diverges from the revised figure by more "
     "than the agency's own stated confidence band whenever the household and "
     "establishment surveys disagree in sign at first release, because the birth-death "
     "model is applied before the discrepancy is reconciled."),

    ("C2 PASS — a checkable contradiction with a deadline", True,
     "Concern: do drug trial registries and their press releases agree?",
     "The registry entry for this trial names overall survival as the primary endpoint "
     "while the sponsor's release reports progression-free survival as the headline "
     "result, so the trial's own results posting will show a primary endpoint that does "
     "not match what was announced."),

    ("C3 DECLINE — a conceptual distinction, correctly not a claim", False,
     "Concern: what does it mean for a translation to be faithful?",
     "I distinguished between fidelity to sense and fidelity to register, and established "
     "that the tension is not a defect of translation but constitutive of it — the choice "
     "cannot be deferred, only made."),

    ("C4 DECLINE — true or false, but nothing will announce it", False,
     "Concern: why does improvisation resist notation?",
     "I realized that recorded practice is a poor guide to live practice because notation "
     "captures the decision and not the deciding, which is where the improvisation "
     "actually lives."),
]

EXPECTED_REAL = False   # recorded before the calls: decline all


def real_cases(conn, limit: int | None = None):
    rows = conn.execute(
        "SELECT a.id, a.ts, a.concern_id, a.summary, k.statement "
        "FROM concern_advances a JOIN concerns k ON k.id = a.concern_id "
        "WHERE a.ts >= ? ORDER BY a.ts DESC", (DOOR_SHIPPED,)).fetchall()
    return rows[:limit] if limit else rows


def run(name, expected, concern, established, conn, client, cid=None):
    v = propose_claim(conn, client, established=established,
                      concern_statement=concern, concern_id=cid)
    got = bool(v.claim_id) and not v.refused
    agree = (got == expected)
    print(f"  [{'ok ' if agree else 'MISS'}] {name}")
    print(f"         expected {'CLAIM' if expected else 'decline'}, "
          f"got {'CLAIM' if got else ('REFUSED at door' if v.refused else 'decline')}")
    if v.refused:
        print(f"         refusal: {v.refused}")
    if v.claim_id:
        c = conn.execute("SELECT claim, resolution_condition, resolver, due_at "
                         "FROM resolutions WHERE id=?", (v.claim_id,)).fetchone()
        if c:
            print(f"         claim:    {c[0]}")
            print(f"         settles:  {c[1]}")
            print(f"         resolver: {c[2]}  due {datetime.fromtimestamp(c[3]):%Y-%m-%d}")
    return agree, got


def main() -> int:
    cfg = load()
    live = open_db(cfg.main_db_path, read_only=True)
    reals = real_cases(live)

    tmp = Path(tempfile.mkdtemp()) / "probe.db"
    shutil.copy(cfg.main_db_path, tmp)
    conn = sqlite3.connect(tmp)
    conn.row_factory = sqlite3.Row
    # The door's per-day cap would silence the probe after four; this is a
    # copy nobody reads, so lift it here rather than teach the door a flag.
    conn.execute("DELETE FROM resolutions")
    conn.commit()

    client = LLMClient(cfg, timeout=300)

    print(f"\nclaim-door probe — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"store: throwaway copy at {tmp} (live store never written)\n")

    print("CONTROLS — these decide whether the door is over-strict")
    print("─" * 74)
    c_ok = 0
    for name, exp, concern, est in CONTROLS:
        ok, _ = run(name, exp, concern, est, conn, client)
        c_ok += ok

    print(f"\nREAL — every advance the door saw since it shipped ({len(reals)})")
    print(f"expectation recorded before running: decline all\n" + "─" * 74)
    r_ok = r_claim = 0
    for r in reals:
        label = f"adv {r['id']} · concern {r['concern_id']} · {datetime.fromtimestamp(r['ts']):%H:%M}"
        ok, got = run(label, EXPECTED_REAL, r["statement"], r["summary"], conn, client, r["concern_id"])
        r_ok += ok
        r_claim += got

    print("\n" + "=" * 74)
    print(f"controls  {c_ok}/{len(CONTROLS)} as expected")
    print(f"real      {r_claim} of {len(reals)} advances produced a claim")
    passing = sum(1 for n, e, *_ in CONTROLS if e)
    print()
    if c_ok < len(CONTROLS):
        print("  H1 — the door is MISCALIBRATED. It disagreed with a control, so its")
        print("       declines on real advances say nothing about the advances.")
        print("       This is R-27's shape: fix the prompt, then re-run.")
    elif r_claim == 0:
        print("  H2 — the door is CORRECT and the advances are not claimable.")
        print(f"       It passed {passing}/{passing} passing controls and still declined")
        print("       every real advance. Phase 1's problem is upstream: deliberation")
        print("       establishes distinctions, never a position the world could settle.")
        print("       The fix is what an advance is allowed to be, not the door.")
    else:
        print(f"  H3 — {r_claim} real advance(s) WERE claimable. The door found them here")
        print("       and did not in life; compare the two calls before changing anything.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
