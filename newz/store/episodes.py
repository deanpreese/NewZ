"""The episode writer — one door into lived experience (S2 §4.1).

Everything the being does becomes an episode here, or it does not happen as
far as the being is concerned. Both paths that let it know its own life read
this table and nothing else:

- **sleep** gathers `digest_eligible=1 AND consolidated_version IS NULL`
  (newz/sleep/nightly.py `_gather`), so an event that is not an episode can
  never reach the Perspective;
- **retrieval** indexes episodes (newz/memory/retrieval.py), so an event that
  is not an episode can never be recalled.

Observed 2026-08-12, and the reason this module exists: deliberation,
research, and concern advances wrote only their own tables. Asked "what's
new?" after a night that wrote Perspective v4, an advance on concern 111,
and a research run that kept 4 sources and extracted 23 claims, the being
answered "Nothing new" — correctly, for a context in which none of it was
present. It had no path to its own autonomous life, immediate or nightly.
That is the severed-loop pattern P2 Rule 1 exists to catch: a write whose
consumer was never traced.

**Provenance follows the established vocabulary** — `self`, `human:<id>`,
`world:<outlet>` — and the choice carries weight, because EVIDENCE-scope
retrieval excludes `provenance='self'` (INV-026). The being's own advances
and setbacks are `self`: they are things it concluded, and letting a
conclusion return later as evidence for itself is precisely the v1 leak that
filter was built for. What it read is `world:<outlet>` and is legitimately
evidence.
"""

from __future__ import annotations

import json
import sqlite3
import time


def write_episode(
    conn: sqlite3.Connection,
    *,
    kind: str,
    provenance: str,
    summary: str,
    content: dict | None = None,
    source_ref: str | None = None,
    digest_eligible: bool = True,
    commit: bool = True,
) -> int:
    """Write one episode and return its id.

    `summary` is what sleep digests and what retrieval renders, so it must
    stand alone — a reader with no other context should learn what happened.
    `content` holds the full record; nothing is lost to the clipping.

    `commit=False` leaves the write inside the caller's transaction, for the
    one caller (sleep) that must publish the episode with the version it
    belongs to or not at all.
    """
    cur = conn.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, content_json,"
        " source_ref, digest_eligible) VALUES (?,?,?,?,?,?,?)",
        (time.time(), kind, provenance, summary,
         json.dumps(content or {}), source_ref, 1 if digest_eligible else 0),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


# The kinds that are the being's own autonomous life, as opposed to
# conversation or imported v1 history. `recent_life` in the composer reads
# exactly this set, so a new autonomous kind reaches conversation by being
# added here.
AUTONOMOUS_KINDS = ("advance", "setback", "concern_opened", "reading",
                    "consolidation")
