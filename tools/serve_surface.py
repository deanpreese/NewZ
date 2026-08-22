#!/usr/bin/env python3
"""Serve the surface (P4 epic E3.4).

    python tools/serve_surface.py          # reach from config; local by default

Reach is one config value — `NEWZ_SURFACE_REACH` — and flipping it to `open`
exposes the surface with no code change, which is E3.4's whole Done-when.
Anything that is not the literal `open` binds the loopback, because the failure
mode of a typo here is not a broken page but an unintended reader.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.evidence.reach import ReachUnattested, attest
from newz.surface.serve import host_for, is_open, serve


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load()
    out = cfg.repo_root / "published"
    if not out.exists() or not (out / "index.md").exists():
        print("nothing generated yet — run tools/generate_surface.py first")
        return 1

    # `.env` is gitignored, so setting NEWZ_SURFACE_REACH produces no diff and
    # no freeze check can see it (R-37b). Exposure takes a second act, in a
    # tracked file, which is what makes it the operator's.
    try:
        attest(cfg.surface_reach)
    except ReachUnattested as e:
        print(f"REFUSING TO SERVE\n\n{e}")
        return 2

    if is_open(cfg.surface_reach):
        print("REACH IS OPEN. This binds every interface; anyone who can route")
        print("to this machine can read the surface. P4 Decision 1 — who the")
        print("first reader is and what they see first — is the decision this")
        print("setting encodes.\n")
    httpd = serve(out, reach=cfg.surface_reach, port=cfg.surface_port)
    print(f"http://{host_for(cfg.surface_reach)}:{cfg.surface_port}/   ctrl-c to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
