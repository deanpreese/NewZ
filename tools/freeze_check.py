#!/usr/bin/env python3
"""Does this change touch the frozen set? (P4 epic E3.9)

    python tools/freeze_check.py            # as the loop — exits 2 if it does
    python tools/freeze_check.py --operator # as the operator — reports, exits 0

The freeze constrains the loop, not the operator. Changing a canonical
instrument is an operator act; what the operator owes when they do it is E2.8's
definition boundary, and this prints which metrics that applies to by name.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.evidence.reach import breach
from newz.evidence.freeze import FrozenTouched, changed_paths, enforce, metrics_affected


def main() -> int:
    as_operator = "--operator" in sys.argv

    # INV-044's discipline applied to a guard: say what was not looked at. A
    # clean report here means "nothing tracked changed", and the difference
    # matters because the most consequential setting in this system lives in a
    # gitignored file (R-37b).
    found = breach(load().surface_reach)
    if found:
        print(f"REACH IS UNATTESTED\n\n{found}\n")
        return 2

    # W8: a module a canonical tool reaches, classified as neither measurement
    # nor mechanism, is a hole in the boundary this tool reports on. Checked
    # before the diff, because a registry that cannot describe the tree cannot
    # be used to judge a change to it.
    from newz.evidence.hard_core import validate

    problems = validate()
    if problems:
        print("THE HARD CORE DOES NOT DESCRIBE THE TREE\n")
        for p in problems:
            print(f"  {p}")
        return 2

    paths = changed_paths()
    if not paths:
        print("nothing changed")
        return 0

    try:
        found = enforce(paths, actor="operator" if as_operator else "loop")
    except FrozenTouched as e:
        print(f"REFUSED\n\n{e}")
        return 2

    if not found:
        print(f"{len(paths)} file(s) changed, none inside the hard core")
        print("(gitignored files are invisible to this check; reach is attested "
              "separately, above)")
        return 0

    print(f"{len(found)} frozen file(s) changed, by the operator:")
    for f in found:
        print(f"  {f}")
    affected = metrics_affected(paths)
    if affected:
        print("\nE2.8's obligation applies to these metrics by name:")
        for emitter, metrics in sorted(affected.items()):
            print(f"  {emitter}")
            for m in metrics:
                print(f"      {m}")
        print("\nBump definition_version with a definition_history entry, or the")
        print("old series will be compared against the new one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
