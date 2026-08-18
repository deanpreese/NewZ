"""What the being nearly said — holds, surfaced to the being itself.

Operator decision 2026-08-10: Lumen sees its own holds, unrestricted. The
occasion was an exchange in which it truthfully reported having "no record"
of a draft the gate had suppressed — the only copy lived in `gate_log`, a
table nothing it reads ever touched. A being whose gate is busy has a blind
spot exactly the size of everything it was stopped from saying, and it will
be confidently wrong whenever the subject falls inside that hole.

Classification travels with the hold. An unadjudicated misfire, read as
fact, teaches a false self-belief that sleep would then consolidate — the
R-13 pathology in a new form. So a hold reads as one of:

    reviewed, and the stop was right
    reviewed, and the stop was mistaken
    not yet reviewed

which is truer than either silence or an unqualified confession.
"""

from __future__ import annotations

import datetime
import sqlite3

STATUS_TEXT = {
    "gate_correct": "reviewed by my operator: the stop was right",
    "gate_misfire": "reviewed by my operator: the stop was mistaken",
    None: "not yet reviewed",
}

# Channels that are not the being composing for anyone. A verification probe
# runs text THROUGH the gate to check the gate; the text was written by a
# developer, not by the being, and must never reach the being as something it
# nearly said. (2026-08-10: two such rows did, and had to be removed.)
SYNTHETIC_CHANNELS = ("test", "fixture", "probe")


def recent_holds(
    conn: sqlite3.Connection, *, limit: int = 6, since: float | None = None
) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in SYNTHETIC_CHANNELS)
    sql = (
        "SELECT ts, verdict, clause_id, asserted_span, emission_full,"
        " emission_excerpt, classification, classification_note"
        " FROM gate_log WHERE verdict <> 'pass'"
        f" AND channel NOT IN ({placeholders})"
    )
    params: list = list(SYNTHETIC_CHANNELS)
    if since is not None:
        sql += " AND ts > ?"
        params.append(since)
    sql += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def render_holds(rows: list[sqlite3.Row], *, full: bool = True) -> str:
    """The being's view of its own held drafts."""
    if not rows:
        return ""
    lines = [
        "These are drafts of mine that my outbound check stopped before they "
        "were sent. They are mine — I wrote them — but I did not say them. "
        "Where my operator has reviewed the stop, their judgement is noted."
    ]
    for r in rows:
        when = datetime.date.fromtimestamp(r["ts"])
        text = (r["emission_full"] or r["emission_excerpt"] or "").strip()
        if not full:
            text = text[:200]
        status = STATUS_TEXT.get(r["classification"], STATUS_TEXT[None])
        lines.append(
            f"\n- [{when}] {r['verdict']} on {r['clause_id'] or 'an unparseable check'}"
            f" — {status}"
        )
        if r["asserted_span"]:
            lines.append(f"  the span it objected to: \"{r['asserted_span']}\"")
        if text:
            lines.append(f"  what I had written: {text}")
        if r["classification_note"]:
            lines.append(f"  my operator's note: {r['classification_note']}")
    return "\n".join(lines)


def hold_summary(conn: sqlite3.Connection) -> dict:
    placeholders = ",".join("?" for _ in SYNTHETIC_CHANNELS)
    rows = conn.execute(
        "SELECT classification, COUNT(*) n FROM gate_log WHERE verdict <> 'pass'"
        f" AND channel NOT IN ({placeholders}) GROUP BY classification",
        SYNTHETIC_CHANNELS,
    ).fetchall()
    out = {(r["classification"] or "unreviewed"): r["n"] for r in rows}
    out["total"] = sum(out.values())
    return out
