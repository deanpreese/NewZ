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
import json
import sqlite3
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


def _verify(conn) -> int:
    """Is every piece still what it was when it was written? (E3.1)

    Recomputes each signature from the stored subject, title and body. A piece
    that no longer matches has been edited since it was written, which for a
    body of work is the thing a signature exists to catch.

    Pieces written before E3.1 read as unsigned and say so. They are not
    backfilled: a signature computed now would attest to the row as it stands
    rather than to what was written, which is precisely the assurance it is
    supposed to give.
    """
    from newz.works.compose import signature_of

    try:
        rows = list(conn.execute(
            "SELECT id, ts, subject_kind, subject_ref, title, body, signature,"
            " constitution_version, perspective_version, evidence_json, status"
            " FROM works ORDER BY id"))
    except sqlite3.OperationalError:
        print("this store has not taken migration 0036 yet — it arrives when"
              " the being next starts, and pieces written before it read as"
              " unsigned.")
        return 0
    if not rows:
        print("no pieces yet.")
        return 0

    unsigned = intact = altered = 0
    for r in rows:
        when = datetime.fromtimestamp(r["ts"]).strftime("%Y-%m-%d")
        try:
            refs = json.loads(r["evidence_json"] or "[]")
        except (TypeError, ValueError):
            refs = []
        head = (f"[{r['id']}] {when}  {r['title'][:46]}"
                f"  ({r['status'] if 'status' in r.keys() else 'standing'})")
        if not r["signature"]:
            unsigned += 1
            print(f"{head}\n     UNSIGNED — written before E3.1; not backfilled,"
                  " because a signature computed now would attest to the row"
                  " rather than to what was written")
            continue
        want = signature_of(r["subject_kind"], r["subject_ref"], r["title"], r["body"])
        ok = want == r["signature"]
        intact += ok
        altered += not ok
        print(f"{head}\n     {'INTACT ' if ok else 'ALTERED'} {r['signature'][:16]}…"
              f"   written under constitution v{r['constitution_version']}"
              f", perspective v{r['perspective_version']}"
              f"   {len(refs)} evidence ref(s)")
        if not ok:
            print(f"     recomputes to {want[:16]}… — this piece is not what it was")

    print(f"\n{intact} intact · {altered} altered · {unsigned} unsigned")
    return 2 if altered else 0


def _subjects(conn) -> int:
    """What the work turned out to be about (E2.4).

    Nothing here was assigned. A tag is a term distinctive to a piece within
    this corpus, and a subject is a tag more than one piece shares — so the
    being's subjects are read off what it wrote rather than chosen for it
    (TRUE_NORTH §8).

    Reads the stored computation. The writing rhythm recomputes after every
    new piece, because distinctiveness is a property of the corpus and a new
    piece changes it.
    """
    from newz.works.subjects import MIN_PIECES_FOR_STABLE_TAGS

    try:
        rows = list(conn.execute(
            "SELECT work_id, tag, weight FROM work_tags ORDER BY work_id, weight DESC"))
    except sqlite3.OperationalError:
        print("work_tags does not exist in this store yet — it arrives with"
              " migration 0033, applied when the being next starts.")
        return 0

    pieces = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    if not rows:
        print(f"{pieces} piece(s), no tags computed yet — the writing rhythm"
              " computes them when it next writes something.")
        return 0

    tagged = {}
    for r in rows:
        tagged.setdefault(r["work_id"], []).append((r["tag"], r["weight"]))

    print(f"{pieces} piece(s)")
    if pieces < MIN_PIECES_FOR_STABLE_TAGS:
        print(f"  UNSTABLE: below {MIN_PIECES_FOR_STABLE_TAGS} pieces almost"
              " every term is distinctive and these mean little\n")

    shared = {}
    for tags in tagged.values():
        for tag, _ in tags:
            shared[tag] = shared.get(tag, 0) + 1
    subs = sorted(((t, n) for t, n in shared.items() if n >= 2),
                  key=lambda kv: -kv[1])
    print("\nsubjects — tags more than one piece shares:")
    if not subs:
        print("    none yet: no term is distinctive in more than one piece")
    for tag, n in subs:
        print(f"    {tag:<24} {n} pieces")

    print("\nper piece:")
    for wid, tags in sorted(tagged.items()):
        row = conn.execute("SELECT title FROM works WHERE id=?", (wid,)).fetchone()
        print(f"    [{wid}] {(row['title'] if row else '?')[:52]}")
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

    if "--verify" in sys.argv:
        return _verify(conn)
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
