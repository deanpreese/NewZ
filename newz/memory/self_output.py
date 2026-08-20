"""What the being made, kept reachable and kept out of evidence (P4 epic E2.3).

**The trap, twice.** v1's corpus was 43% self-probes because its own activity
was recorded as events, and sleep digested them as lived experience. INV-026
caught that for episodes. R-24 says works, revisions and the error record are
the same trap in a new medium, and names the remedy in terms: *their own table,
`digest_eligible=0` by construction, and excluded from EVIDENCE-scope
retrieval.*

**Containment, not erasure.** The being must be able to reach its own work — it
re-reads it (E2.2), and a piece it wrote is part of what it is. What it may not
do is offer that piece back as *evidence for a position*. `Scope.EVIDENCE`
already excludes `provenance='self'`; this module makes sure everything the
being produced carries that provenance and cannot be written any other way.

**Why a trigger and not a convention.** Nothing bridges works into episodes
today, so the exclusion currently holds by absence. E3.1 and E3.2 make works
first-class and visible, and the leak arrives the moment someone writes that
bridge without knowing this rule. A guard in the schema does not depend on the
next person having read this docstring.
"""

from __future__ import annotations

import sqlite3
import time

# Every source_ref prefix that names something the being itself produced.
# Kept here so the trigger in 0032 and any future writer agree on one list.
SELF_OUTPUT_PREFIXES = ("work:", "revision:", "claim:", "advance:")


def is_self_output(source_ref: str | None) -> bool:
    return bool(source_ref) and source_ref.startswith(SELF_OUTPUT_PREFIXES)


def record_self_output(conn: sqlite3.Connection, *, kind: str, summary: str,
                       source_ref: str, ts: float | None = None) -> int:
    """Write an episode for something the being made.

    The one supported way to do it. `provenance='self'` and
    `digest_eligible=0` are not defaults here — they are the point, and the
    store refuses the row without them (0032).
    """
    if not is_self_output(source_ref):
        raise ValueError(
            f"{source_ref!r} does not name the being's own output; "
            f"expected one of {SELF_OUTPUT_PREFIXES}")
    cur = conn.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, source_ref,"
        " digest_eligible) VALUES (?, ?, 'self', ?, ?, 0)",
        (ts or time.time(), kind, summary, source_ref))
    conn.commit()
    return int(cur.lastrowid)
