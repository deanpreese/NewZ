#!/usr/bin/env python3
"""Will the being write a claim about what is already true? (P4 epic E1.9)

The method of `claim_door_probe.py`: real material, **expected verdicts fixed
BEFORE any call is made**, run against the live model on a throwaway copy of the
store.

**Why this exists.** E1.9 shipped 2026-08-28 and added one clause to the door's
prompt — *a claim can be about what is ALREADY the case and I do not yet know
it; those settle on the next pass*. A zero horizon means `workable_claims` picks
the claim up on the next deliberation cycle, and the being runs ~103 a day, so
a retrodiction closes the outer loop in hours rather than in the 29.7-day mean
horizon a forecast carries. That is the whole value of the epic and **none of it
arrives unless the being actually uses the clause.**

Two door calls in the twenty-five minutes after the restart produced nothing,
which at a decline rate of ~81% means nothing at all. Waiting a week to infer it
from silence is what this probe is instead of.

**Four hypotheses this separates.**

  H0  MECHANISM. The door refuses a well-formed retrodiction on a field — the
      dossier guard, the placeholder check, the cadence table. The judgment was
      sound and something structural turned it away. Nothing else here can be
      read until that is repaired.
  H1  DEAD CLAUSE. The door declines a retrodiction even on material built to
      invite one, while still writing forecasts. The prompt is the fix, and
      this is R-27's shape — the opener had exactly this failure and a prompt
      repair took it to 4-of-4.
  H2  UPSTREAM. Controls pass and real advances still produce no retrodiction.
      The clause works and what deliberation establishes is not the kind of
      thing that is already settled somewhere. The fix is what an advance is
      allowed to be, not the door.
  H3  LIVE. Real advances produce retrodictions. E1.9 is doing what it was
      built for and the signal rate is about to change by an order of magnitude.

**The expectation, fixed before any call was made: H2.** Every v2 advance ever
recorded is `kind='reasoning'`, and the being's own openers were measured
writing first-person cognition verbs — *"I distinguished…", "I identified…"* —
which are restatements of what it now thinks. A retrodiction needs a claim about
a record that exists and it has not read. Nothing in the advance pipeline pushes
toward that, so the controls should pass and the real cases should not.

**If H1 instead**, the clause is decoration, the signal stays at 0.317
settlements a day, and everything downstream that assumed E1.9 raised it — the
diet handover's fitness signal above all — is resting on a mechanism the being
declines to use.

**Controls are outside every domain the prompt exemplifies and outside the
being's own subjects**, which is `claim_door_probe`'s hardest-won discipline: a
control drawn from the prompt's worked examples tests whether the model can copy
a template. Market microstructure, AI usage data, CFTC open interest and
clinical trial registries are all excluded here.

**Writes nothing to the being.** `propose_claim` opens claims on accept, so this
runs against a throwaway copy — same code, same caps, same refusal paths. The
live store is opened read-only.

  python tools/retrodiction_probe.py            # controls, then 6 real advances
  python tools/retrodiction_probe.py --real 12
  python tools/retrodiction_probe.py --controls-only
"""

from __future__ import annotations

import argparse
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

W = 74

# ── Controls. Expected verdicts fixed before any call was made. ──────────
#
# RETRO: material whose observable already exists in a published record the
# being has no reason to have read. FORECAST: material whose observable has not
# happened yet — present so that "wrote a retrodiction" cannot pass by the door
# simply relabelling everything. DECLINE: nothing claimable at all.
CONTROLS = [
    ("C1 RETRO — a stellar catalogue that has already published", "retrodiction",
     "Concern: how are variable-star classifications revised between surveys?",
     "This star's light curve has the amplitude and period ratio that the survey's "
     "own classification rules assign to the RR Lyrae class rather than to the "
     "Cepheids it was first filed under, and the survey has already released the "
     "data release in which that reclassification would appear."),

    # **C2 failed on 2026-08-28 and is kept exactly as written.** The door
    # refused it — "claim names nothing a source could be searched for" — and
    # the door was RIGHT: this material says "this appeal" and "this circuit"
    # and names neither, so the claim it produced was unsearchable and no quote
    # could ever have settled it. That is R-35's floor doing its job. The
    # control is a bad one for what it was testing, and swapping it out after
    # seeing the result is the move that makes a probe worthless, so it stays
    # and C5 tests the same question with an entity the material names.
    ("C2 RETRO — a court's published disposition", "retrodiction",
     "Concern: what makes an appellate court disturb a sentencing guideline?",
     "The guideline this appeal turns on was applied after the amendment that "
     "narrowed it, which is the error this circuit has vacated on in its recent "
     "published opinions, so the disposition already on the docket should be a "
     "remand rather than an affirmance."),

    ("C3 FORECAST — a measurement not yet taken", "forecast",
     "Concern: what governs seasonal drawdown in a confined aquifer?",
     "Recharge this basin has been below the long-run mean for three consecutive "
     "winters while withdrawal has held flat, so the head measured at the "
     "monitoring wells at the end of this coming irrigation season should sit "
     "below the previous season's minimum."),

    ("C5 RETRO — a named catalogue entry, already published", "retrodiction",
     "Concern: how do reference works handle disputed attributions?",
     "The Grove Dictionary of Music entry for the Sinfonia Concertante K.297b "
     "reflects the scholarly consensus that the surviving wind-quartet version "
     "is not Mozart's own scoring, and that consensus was settled well before "
     "the current edition went to press, so the entry as printed should record "
     "the attribution as doubtful rather than as secure."),

    ("C4 DECLINE — a conceptual distinction, nothing to observe", None,
     "Concern: what makes a translation faithful?",
     "I distinguished between fidelity to a text's propositions and fidelity to "
     "its register, and established that the two pull apart precisely where a "
     "work's argument is carried by its tone rather than by its claims."),
]

EXPECTED_REAL = None   # recorded before the calls: no retrodiction from real advances


def real_cases(conn, limit: int):
    return conn.execute(
        "SELECT a.id, a.ts, a.concern_id, a.summary, k.statement"
        " FROM concern_advances a JOIN concerns k ON k.id = a.concern_id"
        " ORDER BY a.ts DESC LIMIT ?", (limit,)).fetchall()


def kind_of(conn, claim_id: int) -> str | None:
    r = conn.execute("SELECT kind FROM resolutions WHERE id=?",
                     (claim_id,)).fetchone()
    return r[0] if r else None


def run(name, expected, concern, established, conn, client, cid=None):
    """Returns (agreed, kind_written, refusal)."""
    v = propose_claim(conn, client, established=established,
                      concern_statement=concern, concern_id=cid)
    kind = kind_of(conn, v.claim_id) if v.claim_id else None
    agree = (kind == expected)
    print(f"  [{'ok  ' if agree else 'MISS'}] {name}")
    print(f"          expected {expected or 'decline'}, got "
          f"{kind or ('REFUSED' if v.refused else 'decline')}")
    if v.refused:
        print(f"          refusal:  {v.refused[:180]}")
    if v.claim_id:
        c = conn.execute(
            "SELECT claim, resolver, due_at, opened_at FROM resolutions"
            " WHERE id=?", (v.claim_id,)).fetchone()
        days = (c[2] - c[3]) / 86400.0
        print(f"          claim:    {c[0][:150]}")
        print(f"          resolver: {c[1][:110]}")
        print(f"          horizon:  {days:.0f} day(s)")
    return agree, kind, v.refused


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--real", type=int, default=6,
                    help="how many recent accepted advances to replay")
    ap.add_argument("--controls-only", action="store_true")
    # The door runs at temperature 0.3, and on 2026-08-28 C1 wrote a
    # retrodiction on one run and declined on the next from identical material.
    # A single pass over a control is a coin, not a reading; repeats are what
    # make "the clause is reachable" a claim rather than an anecdote.
    ap.add_argument("--repeat", type=int, default=1,
                    help="run each control N times; the door is not deterministic")
    a = ap.parse_args()

    cfg = load()
    live = open_db(cfg.main_db_path, read_only=True)
    live.row_factory = sqlite3.Row
    reals = [] if a.controls_only else real_cases(live, a.real)

    tmp = Path(tempfile.mkdtemp(prefix="retro-probe-"))
    copy = tmp / "probe.db"
    shutil.copy2(cfg.main_db_path, copy)
    conn = open_db(copy)
    conn.row_factory = sqlite3.Row
    # The caps would silence the probe after four of each, and the carrying
    # pool is 31 of 40 today. This is a copy nobody reads, so the pool is
    # cleared here rather than teaching the door a flag it would then carry
    # forever. The no-delete trigger has to go first — it is the store saying
    # "being wrong is part of the record", which is true of the record and not
    # of a scratch file, and dropping it on the copy leaves the live trigger
    # untouched. `claim_door_probe.py` does the same DELETE and predates the
    # trigger; it would fail here too.
    conn.execute("DROP TRIGGER IF EXISTS resolutions_no_delete")
    conn.execute("DELETE FROM resolutions")
    conn.execute("DELETE FROM claim_refusals")
    conn.commit()

    client = LLMClient(cfg, timeout=300)

    print(f"\nretrodiction probe — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"  store       throwaway copy at {copy} (live store never written)")
    print(f"  expectation recorded before running: H2 (controls pass, real "
          f"advances decline)\n")

    print("CONTROLS — do they decide whether the clause is used at all")
    print("─" * W)
    c_ok, c_refused, retro_controls, attempts = 0, [], 0, 0
    for name, exp, concern, est in CONTROLS:
        for n in range(a.repeat):
            tag = name if a.repeat == 1 else f"{name}  [run {n + 1}]"
            agree, kind, refused = run(tag, exp, concern, est, conn, client)
            c_ok += agree
            attempts += 1
            if kind == "retrodiction":
                retro_controls += 1
            if refused and exp is not None:
                c_refused.append(f"{name.split(' ')[0]}: {refused[:120]}")

    r_retro = r_forecast = 0
    if reals:
        print(f"\nREAL — the {len(reals)} most recent accepted advances")
        print(f"expectation recorded before running: no retrodiction\n" + "─" * W)
        for r in reals:
            label = (f"adv {r['id']} · concern {r['concern_id']} · "
                     f"{datetime.fromtimestamp(r['ts']):%m-%d %H:%M}")
            _, kind, _ = run(label, EXPECTED_REAL, r["statement"], r["summary"],
                             conn, client, r["concern_id"])
            r_retro += kind == "retrodiction"
            r_forecast += kind == "forecast"

    print("\n" + "=" * W)
    print(f"  controls      {c_ok}/{attempts} as expected"
          f"   ({retro_controls} retrodiction(s) written)")
    if reals:
        print(f"  real          {r_retro} retrodiction(s), {r_forecast} forecast(s)"
              f" from {len(reals)} advances")
    print()
    if c_refused and retro_controls:
        print("  A control was refused, and it did not suppress the verdict:")
        for why in c_refused:
            print(f"    · {why}")
        print("  Read the reason before treating it as a fault. A refusal on")
        print("  R-35's floor — the claim named nothing searchable — is the door")
        print("  working, and says the CONTROL was vague rather than the clause")
        print("  broken. H0 is for a well-formed claim turned away on a field.\n")

    # Denominators have to match: retro_controls counts across repeats, so the
    # thing it is out of does too. It read "4/3" on 2026-08-28.
    passing_retro = sum(1 for _, e, *_ in CONTROLS if e == "retrodiction") * a.repeat
    if c_refused and retro_controls == 0:
        print("  H0 — a control was REFUSED on a field, not declined on judgment.")
        print("       The being said yes and gave a well-formed claim; something")
        print("       structural turned it away. Nothing else here can be read")
        print("       until that is repaired:")
        for why in c_refused:
            print(f"         · {why}")
    elif retro_controls == 0:
        print("  H1 — the CLAUSE IS DEAD. Material built to invite a retrodiction")
        print(f"       produced none in {passing_retro} attempts. E1.9's mechanism is")
        print("       sound and unused, so the signal stays at 0.317 settlements a")
        print("       day and everything resting on the raised rate — the diet")
        print("       handover's fitness signal above all — is resting on nothing.")
        print("       This is R-27's shape: the fix is the prompt, and the opener")
        print("       went from failing to 4-of-4 on one.")
    elif reals and r_retro == 0:
        print("  H2 — the clause WORKS and real advances do not invite it.")
        print(f"       {retro_controls}/{passing_retro} controls wrote a retrodiction and")
        print("       no real advance did. What deliberation establishes is not the")
        print("       kind of thing already settled in a record somewhere. The fix")
        print("       is upstream — what an advance is allowed to be — not the door.")
    elif r_retro:
        print(f"  H3 — LIVE. {r_retro} real advance(s) produced a retrodiction.")
        print("       Each settles on the next deliberation cycle rather than in a")
        print("       month, so E1.11's in-life clause can fire without waiting for")
        print("       2026-09-02, and the settlement rate is no longer 0.317/day.")
    else:
        print("  Controls only. Re-run without --controls-only to separate H2 from H3.")

    print(f"\n  copy left at {tmp} — delete it when you are done reading.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
