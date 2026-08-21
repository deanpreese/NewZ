#!/usr/bin/env python3
"""The gate, in one command (P4 W5).

    python tools/gate.py              # suite, ledger, freeze — exit 0 or 2
    python tools/gate.py --soak 10    # the suite ten times
    python tools/gate.py --quick      # ledger and freeze only, no suite

**Why one command.** Three checks existed and each ran only when a person typed
it: `pytest`, `tools/check_invariants.py`, `tools/freeze_check.py`. On
2026-08-19 a commit went in red because nothing ran the first. One command is
one thing to remember instead of three.

**Nothing runs this.** A pre-commit hook and a CI workflow both existed for
part of 2026-08-20 and the operator removed both: automation on every commit
was not wanted, and nothing replaced it. Running the gate is an act somebody
takes, which means the sentence "the suite is green" is a claim about the last
time someone ran this — no more and no less.

**And it is not a boundary against an agent.** It never was: `--no-verify` is
one flag and an agent runs as the same user. Nor is the freeze it runs — this
invokes `freeze_check --operator`, the mode that lists and does not refuse, so
nothing here has ever refused a diff. `evolution/hard_core.yaml` records that
as a standing fact (P4 W5, RT5; E3A.4).

`rebuild_check` is deliberately absent: it restores a backup and generates the
surface twice, which is a minute of work, and a per-commit check that slow is a
check people route around. It belongs to the weekly job.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _run(label: str, argv: list[str]) -> tuple[bool, str]:
    started = time.time()
    p = subprocess.run(argv, cwd=REPO, capture_output=True, text=True)
    took = time.time() - started
    ok = p.returncode == 0
    tail = (p.stdout or p.stderr or "").strip().splitlines()
    print(f"  {'PASS' if ok else 'FAIL'}  {label:<22} {took:5.1f}s   "
          f"{tail[-1][:70] if tail else ''}")
    return ok, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    argv = sys.argv[1:]
    soak = 1
    if "--soak" in argv:
        soak = int(argv[argv.index("--soak") + 1])
    quick = "--quick" in argv

    print(f"gate: {REPO}")
    results: list[tuple[bool, str]] = []

    if not quick:
        for i in range(soak):
            label = "suite" if soak == 1 else f"suite {i + 1}/{soak}"
            ok, out = _run(label, [sys.executable, "-m", "pytest", "-q"])
            results.append((ok, out))
            if not ok:
                print(out[-4000:])
                # A soak stops at the first red: the question it answers is
                # whether the suite is stable, and one failure answers it.
                break

    results.append(_run("ledger", [sys.executable, "tools/check_invariants.py"]))
    results.append(_run("freeze", [sys.executable, "tools/freeze_check.py",
                                   "--operator"]))

    failed = [out for ok, out in results if not ok]
    if failed:
        print(f"\nREFUSED — {len(failed)} check(s) failed")
        for out in failed:
            print(out[-2000:])
        return 2
    print("\nclean" + (f" — {soak} consecutive suite runs" if soak > 1 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
