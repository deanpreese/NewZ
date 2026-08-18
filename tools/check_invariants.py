#!/usr/bin/env python3
"""Invariant-ledger CI parser (S2 §15.1, fresh build — not a v1 port).

Parses INVARIANTS.md's ledger table and enforces:
  - every row has a unique INV-### id;
  - status is one of: structural | enforced | consumer_traced | deferred;
  - `enforced` and `consumer_traced` rows name a test that exists
    (tests/<file>.py::<test_name>, verified by scanning for `def <test_name>`);
  - `consumer_traced` rows also name a consumer code site (an existing file,
    optionally file:line) and a behavior;
  - `deferred` rows name the phase that delivers them.

Exit 0 on a clean ledger; exit 1 with per-row errors otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VALID_STATUSES = {"structural", "enforced", "consumer_traced", "deferred"}
ROW_RE = re.compile(r"^\|\s*(INV-\d+)\s*\|(.+?)\|\s*(\w+)\s*\|(.*?)\|(.*?)\|(.*?)\|\s*$")


def parse_ledger(md_path: Path) -> list[dict]:
    rows = []
    for line in md_path.read_text().splitlines():
        m = ROW_RE.match(line)
        if m:
            rows.append(
                {
                    "id": m.group(1),
                    "invariant": m.group(2).strip(),
                    "status": m.group(3).strip(),
                    "test": m.group(4).strip(),
                    "consumer": m.group(5).strip(),
                    "behavior": m.group(6).strip(),
                }
            )
    return rows


def test_exists(repo: Path, ref: str) -> bool:
    if "::" not in ref:
        return False
    file_part, test_name = ref.split("::", 1)
    test_file = repo / file_part
    if not test_file.exists():
        return False
    return bool(re.search(rf"^(async )?def {re.escape(test_name)}\b", test_file.read_text(), re.M))


def consumer_exists(repo: Path, ref: str) -> bool:
    file_part = ref.split(":", 1)[0]
    return (repo / file_part).exists()


def check(repo: Path) -> list[str]:
    md = repo / "INVARIANTS.md"
    if not md.exists():
        return ["INVARIANTS.md not found"]
    rows = parse_ledger(md)
    errors: list[str] = []
    if not rows:
        errors.append("no ledger rows parsed from INVARIANTS.md")
    seen: set[str] = set()
    for r in rows:
        rid = r["id"]
        if rid in seen:
            errors.append(f"{rid}: duplicate id")
        seen.add(rid)
        if r["status"] not in VALID_STATUSES:
            errors.append(f"{rid}: invalid status {r['status']!r}")
            continue
        if r["status"] in ("enforced", "consumer_traced"):
            if not test_exists(repo, r["test"]):
                errors.append(f"{rid}: test {r['test']!r} not found")
        if r["status"] == "consumer_traced":
            if not r["consumer"] or not consumer_exists(repo, r["consumer"]):
                errors.append(f"{rid}: consumer site {r['consumer']!r} not found")
            if not r["behavior"]:
                errors.append(f"{rid}: consumer_traced requires a behavior")
        if r["status"] == "deferred" and "Phase" not in r["behavior"] and "Phase" not in r["consumer"]:
            errors.append(f"{rid}: deferred rows must name the delivering Phase")
    return errors


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    errors = check(repo)
    for e in errors:
        print(f"INVARIANTS: {e}", file=sys.stderr)
    if errors:
        return 1
    print(f"INVARIANTS: {len(parse_ledger(repo / 'INVARIANTS.md'))} rows clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
