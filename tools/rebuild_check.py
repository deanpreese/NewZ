#!/usr/bin/env python3
"""Rebuild the surface in a clean room, from a verified backup (P4 E3.5).

    python tools/rebuild_check.py

Proves the surface is a function of the store and nothing else: restores the
newest backup into a temporary directory, generates twice from different
working directories, and compares byte for byte.

Exit 0 if the rebuild is byte-comparable and carries no absolute path; 2 if not.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.surface.cleanroom import rebuild
from newz.surface.generate import generate


def main() -> int:
    cfg = load()
    r = rebuild(cfg.backups_dir, generate_fn=generate)
    if r.unreadable:
        print(f"UNREADABLE — {r.unreadable}")
        return 2

    print(f"restored   {r.source.name}")
    print(f"monitor    {r.monitor or 'NONE — the read page will say so'}")
    print(f"rebuilt    {r.pages} file(s), from a different working directory")
    print(f"identical  {len(r.identical)} of {r.pages}")
    for name in r.differing:
        print(f"  DIFFERS  {name}")
    for leak in r.leaked_paths:
        print(f"  ABSOLUTE PATH  {leak}")

    if r.ok:
        print("\nbyte-comparable, and nothing in the output names this machine.")
        print("What this does NOT prove: that the store survives a different")
        print("filesystem, architecture or locale, or that a backup restores")
        print("somewhere other than where it was made. Those need the second")
        print("machine R-11 defers, and the deferral carries its own trip-wire.")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
