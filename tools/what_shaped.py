#!/usr/bin/env python3
"""What shaped this view (S2 §13) — trace a held position to its sources.

    python tools/what_shaped.py                    # every held position
    python tools/what_shaped.py --item 41          # one, with its episodes
    python tools/what_shaped.py --search montaigne # positions matching text
    python tools/what_shaped.py --concentration    # the diversity read

Read-only. TRUE_NORTH §8's non-prescription is only checkable if the
influence on a view can be named, and this is the naming.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.memory.provenance import (
    corpus_concentration,
    what_shaped,
    what_shaped_version,
)
from newz.store.db import open_db


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", type=int, help="a perspective_items id")
    ap.add_argument("--search", help="substring of a position's text")
    ap.add_argument("--version", type=int, help="default: newest")
    ap.add_argument("--concentration", action="store_true",
                    help="provenance mix across everything held")
    ap.add_argument("--episodes", action="store_true",
                    help="list the supporting episodes, not just the counts")
    args = ap.parse_args()

    conn = open_db(load().main_db_path, read_only=True)
    try:
        if args.concentration:
            mix = corpus_concentration(conn)
            total = sum(mix.values())
            if not total:
                print("nothing held carries resolvable evidence")
                return 0
            print(f"provenance of everything currently held "
                  f"({total} episode references)\n")
            for prov, n in mix.most_common():
                bar = "#" * max(1, round(40 * n / total))
                print(f"  {n / total:>6.1%}  {bar:<41}{prov}  ({n})")
            top = mix.most_common(2)
            two = sum(n for _, n in top) / total
            print(f"\n  top two sources are {two:.0%} of all influence")
            if two > 0.5:
                print("  ** v1's end state was 56% from two outlets (S2 §13)")
            return 0

        if args.item is not None:
            inf = what_shaped(conn, args.item)
            if inf is None:
                print(f"no perspective item with id {args.item}")
                return 1
            infs = [inf]
        else:
            infs = what_shaped_version(conn, args.version)
            if args.search:
                needle = args.search.lower()
                infs = [i for i in infs if needle in i.text.lower()]

        if not infs:
            print("nothing matched")
            return 1
        for inf in infs:
            print(f"\n[{inf.item_id}] {inf.render()}")
            if args.episodes:
                for e in sorted(inf.episodes, key=lambda x: x["ts"]):
                    print(f"      ep {e['id']:<6} {e['provenance']:<18} "
                          f"{(e['summary'] or '')[:74]}")
        print()
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
