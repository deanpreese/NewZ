"""Write the policy out as machine-readable files.

`python -m newz.policy.emit` writes two artifacts under `policy/`:

- `capability_matrix.jsonl` — one line per cell, in a fixed order, so that a
  change to 3 cells of 2,016 reads as three lines in a diff rather than as a
  hash that moved;
- `bundle.json` — everything else the policy version covers, plus the digest
  over the whole bundle including the cells.

The snapshot test regenerates both and compares, so the committed files and the
code cannot drift apart silently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from newz.canonical import canonical, dumps
from newz.policy.bundle import BUNDLE

MATRIX_PATH = Path("policy/capability_matrix.jsonl")
BUNDLE_PATH = Path("policy/bundle.json")


def render_matrix() -> str:
    return "".join(dumps(entry.as_record()) + "\n" for entry in BUNDLE.matrix.entries())


def render_bundle() -> str:
    record = BUNDLE.as_record()
    matrix = record.pop("capability_matrix")
    record["capability_matrix"] = {
        "cells": f"{len(BUNDLE.matrix)} cells in {MATRIX_PATH.name}",
        "rules": matrix["rules"],
        "decisions": matrix["decisions"],
    }
    payload = {"digest": BUNDLE.digest, "bundle": record}
    return json.dumps(canonical(payload), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    matrix_path = root / MATRIX_PATH
    bundle_path = root / BUNDLE_PATH
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.write_text(render_matrix(), encoding="utf-8")
    bundle_path.write_text(render_bundle(), encoding="utf-8")
    print(f"{matrix_path}: {len(BUNDLE.matrix)} cells")
    print(f"{bundle_path}: policy {BUNDLE.version}, digest {BUNDLE.digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
