#!/usr/bin/env python3
"""Generate the surface from the store (P4 epic E3.2).

    python tools/generate_surface.py              # into published/
    python tools/generate_surface.py --out DIR    # anywhere
    python tools/generate_surface.py --check      # regenerate and diff, write nothing

Every page comes from a query and `manifest.json` records which rows. Nothing
is hand-authored, nothing is incremental, and nothing reaches the network.
"""

from __future__ import annotations

import filecmp
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.db import open_db
from newz.surface.generate import generate


def main() -> int:
    cfg = load()
    argv = sys.argv[1:]
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else cfg.repo_root / "published"
    conn = open_db(cfg.main_db_path, read_only=True)
    try:
        if "--check" in argv:
            with tempfile.TemporaryDirectory() as tmp:
                generate(conn, Path(tmp), now=time.time())
                if not out.exists():
                    print(f"{out} does not exist — nothing to compare")
                    return 1
                names = sorted(p.name for p in Path(tmp).iterdir())
                match, mismatch, errors = filecmp.cmpfiles(tmp, out, names, shallow=False)
                for n in mismatch + errors:
                    print(f"  DIFFERS  {n}")
                print(f"{len(match)} of {len(names)} identical")
                return 0 if not (mismatch or errors) else 2

        if out.exists():
            for p in out.iterdir():
                if p.name != ".gitkeep":
                    shutil.rmtree(p) if p.is_dir() else p.unlink()
        m = generate(conn, out, now=time.time())
        total = sum(len(ids) for t in m.pages.values() for ids in t.values())
        print(f"wrote {len(list(out.glob('*.html')))} pages to {out}")
        print(f"traced to {total} store row(s) across "
              f"{len({t for p in m.pages.values() for t in p})} table(s)")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
