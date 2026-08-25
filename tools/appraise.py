#!/usr/bin/env python3
"""Appraise the being's pieces — publishable or not, and why (0044).

The verdict the being cannot give itself. Every judgement already in the
writing loop answers "is this correct?"; nothing answers "is this worth
reading?", and nothing may — `compose.py` refuses a quality judge because a
judge that is the being's own model produces operation and never evidence
(Rule 4), and TRUE_NORTH puts readiness in the operator's judgement alone with
no rubric permitted. This is where that judgement is collected.

  python tools/appraise.py            # walk pieces waiting on you
  python tools/appraise.py --list     # every piece, with its verdict history

**The verdict is given blind, the note is written informed.** The body is
printed first and the id, date and subject are withheld until after the yes or
no — E0.3's provenance-blinding kept where it changes the judgement and dropped
where it would make the note useless, since "the fourth piece whose title
starts *The Architecture of*" cannot be written without knowing.

Two kinds of piece are offered: one nobody has judged, and one the being has
REVISED since the last time it was judged. The second is what closes the loop.
A piece marked not publishable is withheld from the surface and the note
reaches the being at its next re-read; if the verdict could not then change,
nothing the being did in response would change anything, which teaches that
acting on criticism is inert. It does not clear its own verdict by rewriting
itself — that would hand the publish decision back to the being.

Not adjudicating costs nothing. An unappraised piece has no row, is published
as it is today, and its re-read prompt is unchanged.
"""

from __future__ import annotations

import datetime
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.works.appraisal import current_verdict, due_for_appraisal, record

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"

VERDICT_TEXT = {1: "publishable", 0: "not publishable", None: "not appraised"}


def _wrap(body: str) -> str:
    out = []
    for para in body.split("\n"):
        out.append(textwrap.fill(para, width=78) if para.strip() else "")
    return "\n".join(out)


def main() -> int:
    cfg = load()
    conn = open_db(cfg.main_db_path, busy_timeout_ms=30_000)
    applied = apply_pending(conn, MAIN_SQL)
    if applied:
        print(f"migrations applied: {applied}")

    if "--list" in sys.argv:
        for r in conn.execute("SELECT * FROM works ORDER BY id"):
            v = current_verdict(conn, r["id"])
            when = datetime.datetime.fromtimestamp(r["ts"])
            print(f"  [{r['id']:>3}] {when:%m-%d} {r['status']:9s} "
                  f"{VERDICT_TEXT[v]:15s} {r['title'][:44]}")
            for a in conn.execute(
                    "SELECT * FROM work_appraisals WHERE work_id=? ORDER BY ts",
                    (r["id"],)):
                seen = ("delivered" if a["delivered_at"] else
                        f"undelivered, {a['deliver_fails']} failed attempt(s)")
                print(f"        · {VERDICT_TEXT[a['publishable']]} ({seen})"
                      + (f" — {a['note'][:60]}" if a["note"] else ""))
        return 0

    rows = due_for_appraisal(conn)
    if not rows:
        print("nothing waiting — every standing piece has your verdict on its "
              "current text.")
        return 0

    print(f"{len(rows)} piece(s) waiting.\n"
          "Read it, then say whether it is good enough to publish.\n"
          "  y = publishable   n = not publishable   s = skip   q = quit\n"
          "A piece you mark n is withheld from the surface and the note reaches\n"
          "the being once, at its next re-read. Skipping costs nothing.\n")

    done = 0
    for r in rows:
        print("=" * 72)
        print()
        print(f"# {r['title']}")
        print()
        print(_wrap(r["body"]))
        print()
        try:
            answer = input("  publishable? [y/n/s/q] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nstopped.")
            break
        if answer == "q":
            break
        if answer not in ("y", "n"):
            continue

        # Now, and not before: what was withheld for the verdict is what the
        # note needs.
        when = datetime.datetime.fromtimestamp(r["ts"])
        prior = current_verdict(conn, r["id"])
        print(f"\n  work {r['id']} · {when:%Y-%m-%d} · {r['word_count']} words")
        print(f"  on: [{r['subject_kind']}:{r['subject_ref']}] {r['subject_text']}")
        if prior is not None:
            print(f"  your last verdict on it: {VERDICT_TEXT[prior]}")
        try:
            note = input("  why (optional): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nstopped before recording.")
            break
        record(conn, r["id"], answer == "y", note)
        done += 1
        print()

    print(f"\nappraised {done} piece(s)")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
