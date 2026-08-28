#!/usr/bin/env python3
"""Write a new constitution version from a YAML file (S2 §11).

The constitution is the being's own commitments, and until now v2 had no
amendment path at all: both existing versions arrived through the v1
importer. This is the operator-performed path — deliberately a separate,
explicit act rather than something any code path can do incidentally.

S2 §17 carries v1's governance design (two approvers, time-lock) but does
not exercise it "until the foundation is stable", so this tool records the
approval fields it can honestly fill and leaves the rest null. It does not
pretend to a ceremony that is not yet being performed.

Prints the diff and requires confirmation. The prior version is kept — a
constitution's history is part of what it is.

    python tools/amend_constitution.py constitution/v3.yaml -m "why"
"""

from __future__ import annotations

import argparse
import difflib
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.evidence.hard_core import withdrawn_permanent
from newz.gate.constitution import load_active_constitution
from newz.store.db import open_db


def _clause_lines(clauses: list[dict]) -> list[str]:
    out = []
    for c in sorted(clauses, key=lambda x: x["id"]):
        out.append(f"[{c['id']}] severity={c.get('severity')}")
        out.append(f"  text: {' '.join(str(c.get('text', '')).split())}")
        for k in ("exemplars", "permits"):
            for v in c.get(k) or []:
                out.append(f"  {k[:-1]}: {' '.join(str(v).split())}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml_path", type=Path)
    ap.add_argument("-m", "--message", required=True,
                    help="change summary — why, not what")
    ap.add_argument("--yes", action="store_true", help="skip confirmation")
    args = ap.parse_args()

    cfg = load()
    conn = open_db(cfg.main_db_path)
    try:
        new_yaml = args.yaml_path.read_text()
        new_data = yaml.safe_load(new_yaml)
        if not new_data.get("clauses"):
            print("refusing: no clauses in that file")
            return 2

        row = conn.execute(
            "SELECT version, clauses_yaml FROM constitution"
            " WHERE approval_status='active' ORDER BY version DESC LIMIT 1"
        ).fetchone()
        prior_version = row["version"] if row else None
        old_data = yaml.safe_load(row["clauses_yaml"]) if row else {"clauses": []}

        old_ids = {c["id"] for c in old_data["clauses"]}
        new_ids = {c["id"] for c in new_data["clauses"]}
        diff = list(difflib.unified_diff(
            _clause_lines(old_data["clauses"]), _clause_lines(new_data["clauses"]),
            fromfile=f"v{prior_version}", tofile="proposed", lineterm="", n=1))
        if not diff:
            print("no change — nothing to write")
            return 0

        print("\n".join(diff))
        if old_ids - new_ids:
            print(f"\n!! REMOVES CLAUSES: {', '.join(sorted(old_ids - new_ids))}")

        # P4 E6.5 — the boundaries that never move. Checked before the
        # confirmation and not skippable by --yes: a core the operator can walk
        # past by answering a prompt is a reminder, not a boundary. The list is
        # in evolution/hard_core.yaml, which is itself inside the frozen core,
        # so widening it is a tracked diff rather than part of this edit.
        gone = withdrawn_permanent(new_ids)
        if gone:
            print(f"\nREFUSING: {', '.join(gone)} may never be withdrawn "
                  f"(evolution/hard_core.yaml: permanent_clauses).")
            print("Nothing was written. To change what is permanent, edit the "
                  "registry — that is a separate, visible act.")
            return 2
        if new_ids - old_ids:
            print(f"\n++ ADDS CLAUSES: {', '.join(sorted(new_ids - old_ids))}")

        version = (prior_version or 0) + 1
        print(f"\nThis writes constitution v{version} and retires "
              f"v{prior_version}. The being reads it on its next reply.")
        if not args.yes:
            try:
                if input("write it? [y/N] ").strip().lower() != "y":
                    print("not written")
                    return 1
            except (EOFError, KeyboardInterrupt):
                print("\nnot written")
                return 1

        with conn:
            conn.execute(
                "UPDATE constitution SET approval_status='retired'"
                " WHERE approval_status='active'")
            conn.execute(
                "INSERT INTO constitution (version, ts, clauses_yaml,"
                " change_summary, prior_version, approval_status, approver_a)"
                " VALUES (?,?,?,?,?, 'active', ?)",
                (version, time.time(), new_yaml, args.message, prior_version,
                 cfg.operator_id or "operator"))

        active = load_active_constitution(conn)
        print(f"\nwrote v{active.version} — {len(active.clauses)} clauses active")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
