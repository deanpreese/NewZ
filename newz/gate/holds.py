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

import yaml

from newz.gate.constitution import load_active_constitution

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
    reviewed_only: bool = False, instructive_only: bool = False,
) -> list[sqlite3.Row]:
    """Holds the being may see. `reviewed_only` is for consolidation.

    `reviewed_only` defaults False because conversation is where this module's
    original purpose lives: a being blind to what it was stopped from saying is
    confidently wrong wherever the subject falls (2026-08-10). Sleep passes
    True, because an unadjudicated stop must not become a position.

    **`instructive_only` drops what the being cannot learn from** *(operator,
    2026-08-30)*. Two kinds, and the module already holds this position one
    function over: `_clause_text_floor` gives a retired clause no prior at all,
    "which is correct: nothing is subject to it."

      - a hold the operator adjudicated `gate_misfire`. Of 53 adjudicated
        holds, 37 were misfires — a being shown a stream of mostly-mistaken
        judgements learns to avoid what was never a problem, which is PLAN's
        own objection to E6.2 and was live in every reply.
      - a hold on a clause no longer in the active constitution. Nothing is
        subject to it, so there is nothing to learn.

    Measured the day it was fixed: the five holds rendered into every reply
    were four `anti-self-aggrandizement-001` stops, ALL FOUR adjudicated
    misfires, on a clause withdrawn in v7 four days earlier — and one
    unreviewed. The being had been reading, on every turn, four drafts it was
    stopped from sending by a rule that no longer exists for reasons already
    judged mistaken.

    An UNREVIEWED hold still shows. The default is that a stop is real until
    someone says otherwise; suppressing what has not been looked at would let
    an unadjudicated backlog quietly become an absence.
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
    if instructive_only:
        sql += " AND (classification IS NULL OR classification <> 'gate_misfire')"
    if since is not None:
        sql += " AND ts > ?"
        params.append(since)
    sql += " ORDER BY ts DESC LIMIT ?"
    # Over-fetch when a clause filter has to run in Python: the retired-clause
    # test needs the active constitution, and a SQL LIMIT applied first would
    # return four rows and then drop them all.
    params.append(limit * 8 if instructive_only else limit)
    rows = conn.execute(sql, params).fetchall()
    if not instructive_only:
        return rows

    live = load_active_constitution(conn)
    return [r for r in rows if live.by_id(r["clause_id"]) is not None][:limit]


# Below this many reviewed holds a rate is noise wearing a denominator, and
# the being is better served by the plain absence than by "1 of 1".
MIN_FOR_PRIOR = 5


def _clause_text_floor(conn: sqlite3.Connection, clause_id: str) -> float | None:
    """When the clause last CHANGED — the earliest ts its current wording held.

    Without this the prior is a number about a rule that no longer exists.
    `don't-pretend-to-feel-001` was patched in v4 and retired in v5, and 22 of
    the project's 32 lifetime misfires belong to it; a rate that pools across a
    rewrite tells the being about a check it is not subject to. `gate_log` does
    not record a constitution version, so the floor is recovered by walking the
    versions and finding where this clause's current text was introduced.

    Returns None if the clause is not in the active constitution — a retired
    clause gets no prior at all, which is correct: nothing is subject to it.
    """
    rows = conn.execute(
        "SELECT version, ts, clauses_yaml FROM constitution ORDER BY version"
    ).fetchall()
    if not rows:
        return None
    texts: list[tuple[float, str | None]] = []
    for r in rows:
        try:
            clauses = yaml.safe_load(r["clauses_yaml"])["clauses"]
        except Exception:  # noqa: BLE001 — an unparseable version is not a floor
            texts.append((r["ts"], None))
            continue
        found = next((c["text"] for c in clauses if c.get("id") == clause_id), None)
        texts.append((r["ts"], found))
    current = texts[-1][1]
    if current is None:
        return None
    floor = texts[-1][0]
    for ts, text in reversed(texts[:-1]):
        if text != current:
            break
        floor = ts
    return floor


def clause_prior(conn: sqlite3.Connection, clause_id: str) -> tuple[int, int] | None:
    """(judged mistaken, reviewed) for this clause AS IT CURRENTLY READS.

    **It reports the mistaken count and never the count judged right**, and
    that asymmetry is deliberate. A line saying "judged RIGHT in 6 of 12" makes
    a constraint more binding, which is this mechanism running backwards; the
    operator's condition on the whole design was that it become less
    restrictive, not more. The number is the same fact either way — what
    changes is whether the sentence can be read as backing the stop.

    `None` when there is no floor, or fewer than `MIN_FOR_PRIOR` reviewed.
    """
    floor = _clause_text_floor(conn, clause_id)
    if floor is None:
        return None
    row = conn.execute(
        "SELECT COUNT(*) n, SUM(classification = 'gate_misfire') m FROM gate_log"
        " WHERE clause_id = ? AND verdict <> 'pass' AND ts >= ?"
        "   AND classification IS NOT NULL",
        (clause_id, floor)).fetchone()
    if not row or (row["n"] or 0) < MIN_FOR_PRIOR:
        return None
    return int(row["m"] or 0), int(row["n"])


def render_holds(rows: list[sqlite3.Row], *, full: bool = True,
                 conn: sqlite3.Connection | None = None) -> str:
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
        if r["classification"] is None and conn is not None:
            prior = clause_prior(conn, r["clause_id"] or "")
            if prior:
                mistaken, seen = prior
                status += (f" — where anyone has looked at a stop on this "
                           f"check, {mistaken} of {seen} were judged mistaken")
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
