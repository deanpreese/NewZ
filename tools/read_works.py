#!/usr/bin/env python3
"""Read the being's pieces back (P3 Rule 2's reader for `works`).

This is also the instrument for E0.3: what the operator reads to render Phase
0's verdict.

  python tools/read_works.py              # list what exists
  python tools/read_works.py 3            # read piece 3 in full
  python tools/read_works.py --blind      # every piece, in a shuffled order,
                                          # with subject, reason and id withheld
                                          # until the key is printed at the end

`--blind` is E0.3's optional provenance-blinding (P2's cutover criterion 3,
reused): read first, decide, then look at what you were reading. It cannot
make the operator a stranger to the being — nothing can, and P3-04 says so —
but it removes the smaller tell of knowing which subject produced which piece.
"""

from __future__ import annotations

import random
import sys
import textwrap
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.db import open_db


def _render(row, *, blind: bool = False, label: str | None = None) -> str:
    out = [f"{'─' * 72}"]
    if blind:
        out.append(f"[{label}]")
    else:
        when = datetime.fromtimestamp(row["ts"]).strftime("%Y-%m-%d %H:%M")
        out.append(f"[work {row['id']}]  {when}  ·  {row['word_count']} words")
        out.append(f"subject: [{row['subject_kind']}:{row['subject_ref']}] {row['subject_text']}")
        out.append(f"chose it because: {row['chosen_because']}")
    out.append("")
    out.append(f"# {row['title']}")
    out.append("")
    for para in row["body"].split("\n"):
        out.append(textwrap.fill(para, width=78) if para.strip() else "")
    return "\n".join(out)


def _subjects(conn) -> int:
    """What the work turned out to be about (E2.4).

    Nothing here was assigned. A tag is a term distinctive to a piece within
    this corpus, and a subject is a tag more than one piece shares — so the
    being's subjects are read off what it wrote rather than chosen for it
    (TRUE_NORTH §8).
    """
    from newz.works.subjects import recompute

    c = recompute(conn)
    if not c.pieces:
        print("no pieces yet.")
        return 0
    print(f"{c.pieces} piece(s)")
    if c.caveat:
        print(f"  UNSTABLE: {c.caveat}\n")
    subs = c.subjects()
    print("\nsubjects — tags more than one piece shares:")
    if not subs:
        print("    none yet: no term is distinctive in more than one piece")
    for tag, n in subs:
        print(f"    {tag:<24} {n} pieces")
    print("\nper piece:")
    for wid, tags in sorted(c.tags.items()):
        title = conn.execute("SELECT title FROM works WHERE id=?", (wid,)).fetchone()[0]
        print(f"    [{wid}] {title[:52]}")
        print("        " + ", ".join(f"{t} ({w:.3f})" for t, w in tags))
    return 0


def _history(conn) -> int:
    """What each piece used to say, and why it changed (E2.2's reader half).

    A retraction is an outcome and not a deletion, so this is where being wrong
    about one's own work stays visible after the piece itself has moved on.
    """
    rows = list(conn.execute(
        "SELECT r.*, w.title AS now_title, w.status FROM work_revisions r"
        " JOIN works w ON w.id = r.work_id ORDER BY r.ts"))
    if not rows:
        print("no piece has been revised or retracted yet.")
        return 0
    print(f"{len(rows)} revision(s)\n")
    for r in rows:
        when = datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d")
        print("─" * 72)
        print(f"[{when}] work {r['work_id']} {r['kind'].upper()} "
              f"(now: {r['status']})")
        print(f"  reason: {r['reason']}")
        print(f"  it used to be titled: {r['prior_title']}")
        print("  it used to say:")
        print("\n".join("    " + l for l in textwrap.wrap(r["prior_body"], 66)[:6]))
    print("─" * 72)
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    blind = "--blind" in sys.argv
    cfg = load()
    conn = open_db(cfg.main_db_path, read_only=True)

    if "--history" in sys.argv:
        return _history(conn)
    if "--subjects" in sys.argv:
        return _subjects(conn)
    rows = list(conn.execute("SELECT * FROM works ORDER BY ts"))
    if not rows:
        print("no pieces yet — python tools/write_piece.py")
        return 1

    if blind:
        shuffled = list(rows)
        random.shuffle(shuffled)
        labels = [chr(ord("A") + i) for i in range(len(shuffled))]
        for label, row in zip(labels, shuffled):
            print(_render(row, blind=True, label=label))
            print()
        print("─" * 72)
        print("KEY — read the pieces first, then this:")
        for label, row in zip(labels, shuffled):
            print(f"  {label} = work {row['id']}  ·  [{row['subject_kind']}:{row['subject_ref']}]"
                  f" {row['subject_text'][:60]}")
        return 0

    if args:
        wanted = int(args[0])
        row = next((r for r in rows if r["id"] == wanted), None)
        if row is None:
            print(f"no work {wanted}; have {[r['id'] for r in rows]}")
            return 1
        print(_render(row))
        return 0

    print(f"{len(rows)} piece(s):")
    for r in rows:
        when = datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d %H:%M")
        print(f"  [{r['id']}] {when}  {r['word_count']:>5} words  ·  {r['title']}")
        print(f"       from [{r['subject_kind']}:{r['subject_ref']}] {r['subject_text'][:64]}")
    print("\nread one: python tools/read_works.py <id>   ·   all, blinded: --blind")
    return 0


if __name__ == "__main__":
    sys.exit(main())
