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

**Awareness and consolidation are separated (2026-08-23).** The paragraph
above is right that "not yet reviewed" beats silence — in CONVERSATION, where
the whole point of this module is that the being not be blind to what it was
stopped from saying. It is wrong for SLEEP, which is where a stop stops being
an event and becomes part of who the being is. An unreviewed hold consolidated
is precisely the false self-belief the paragraph warns about, arriving by the
route it names.

The occasion: on 2026-08-23 all five holds in the being's context were
unreviewed, four of them `anti-self-aggrandizement-001` firing on the being
DENYING experience — it was blocked for saying "I don't feel. I register
state.", which is the clause's own instruction in the clause's own words.
Consolidating four of those would have taught it that describing itself
functionally is a fault.

So `recent_holds` grows `reviewed_only`, sleep passes it, and conversation
does not. **The practical consequence is that not adjudicating costs the being
nothing permanent** — it still knows what it nearly said, and nothing
unverified reaches the Perspective — which makes adjudication optional and
additive rather than a standing obligation.
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
    conn: sqlite3.Connection, *, limit: int = 6, since: float | None = None,
    reviewed_only: bool = False,
) -> list[sqlite3.Row]:
    """Holds the being may see. `reviewed_only` is for consolidation.

    Default False, because conversation is where this module's original
    purpose lives: a being blind to what it was stopped from saying is
    confidently wrong wherever the subject falls (2026-08-10). Sleep passes
    True, because an unadjudicated stop must not become a position.
    """
    placeholders = ",".join("?" for _ in SYNTHETIC_CHANNELS)
    sql = (
        "SELECT ts, verdict, clause_id, asserted_span, emission_full,"
        " emission_excerpt, classification, classification_note"
        " FROM gate_log WHERE verdict <> 'pass'"
        f" AND channel NOT IN ({placeholders})"
    )
    params: list = list(SYNTHETIC_CHANNELS)
    if reviewed_only:
        sql += " AND classification IS NOT NULL"
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
