#!/usr/bin/env python3
"""The gate. Run it before every commit.

    python tools/gate.py

Standalone by convention: this file imports nothing from `newz` and reads no
store. It shells out to the checks and reports what they said. Where it needs
something the package knows — whether the committed policy artifacts are
current — it regenerates them in a subprocess and compares the bytes, rather
than importing the policy engine and asking it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ("policy/capability_matrix.jsonl", "policy/bundle.json")


def run(name: str, *command: str) -> bool:
    print(f"\n=== {name} " + "=" * max(0, 60 - len(name)))
    result = subprocess.run(command, cwd=ROOT)
    return result.returncode == 0


def policy_artifacts_are_current() -> bool:
    print("\n=== policy artifacts " + "=" * 45)
    before = {path: (ROOT / path).read_bytes() for path in ARTIFACTS}
    result = subprocess.run(
        [sys.executable, "-m", "newz.policy.emit"], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr.strip())
        return False
    stale = [path for path in ARTIFACTS if (ROOT / path).read_bytes() != before[path]]
    for path in stale:
        print(f"stale: {path} was regenerated and differs; commit the regenerated file")
    if not stale:
        print("current")
    return not stale


def main() -> int:
    checks = [
        ("ruff", run("ruff", sys.executable, "-m", "ruff", "check", ".")),
        ("policy artifacts", policy_artifacts_are_current()),
        ("pytest", run("pytest", sys.executable, "-m", "pytest")),
    ]
    print("\n" + "=" * 66)
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'pass' if ok else 'FAIL'}  {name}")
    if failed:
        print(f"\ngate: FAILED ({', '.join(failed)})")
        return 1
    print("\ngate: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
