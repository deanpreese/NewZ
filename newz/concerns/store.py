"""Concern persistence and the dossier (S2 §8.2).

The dossier is the concern's memory: everything it has accumulated —
advances with their evidence, setbacks with their reasons, the sources
consulted. A concern is a research programme in miniature, and the dossier
is what deliberation opens.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field

from newz.concerns.model import BLOCKED_LIMIT, STALL_LIMIT, Concern
from newz.store.episodes import write_episode

logger = logging.getLogger(__name__)

# What the dossier may show of what it read. Measured 2026-08-15 across the
# eight then-open concerns: the largest was 22 claims (~695 tokens) against a
# 33k window, about 2%. So these are cheap insurance against one pathological
# concern, not a design constraint — set generously and revisit only if a
# dossier is ever observed crowding out the being's own thinking.
MAX_CLAIMS_PER_SOURCE = 6
MAX_DOSSIER_CLAIMS = 40


@dataclass
class Dossier:
    concern: Concern
    advances: list[dict] = field(default_factory=list)
    setbacks: list[dict] = field(default_factory=list)
    # What the being actually READ while working on this concern. Loaded
    # from ingest_log, which has recorded concern_id since Phase 2.4 and was
    # never read back — see evidence_refs().
    sources: list[dict] = field(default_factory=list)

    def advance_summaries(self, *, exclude: int | None = None) -> list[str]:
        """What the novelty check compares against.

        S2 §8.3 says "the whole advance history", and that is what this was.
        `exclude` is the recorded deviation (2026-08-15): an advance the
        candidate explicitly supersedes is left out, because superseding
        something necessarily resembles it. ONE may be excluded, so the rest
        of the history still applies and a genuine repeat is still caught.
        """
        return [a["summary"] for a in self.advances if a["id"] != exclude]

    def live_advance_ids(self) -> set[int]:
        """Advances that may be superseded — this concern's, not yet retired."""
        return {a["id"] for a in self.advances}

    def evidence_refs(self) -> set[str]:
        """Everything that actually reached this dossier. An evidence claim
        citing something absent from here is not evidence (S2 §8.3).

        C1, 2026-08-14. This set previously held only refs from PRIOR
        advances plus the opening citations — so it structurally could not
        contain anything the being had just read, and every citation of a
        freshly-read source was relabelled from `evidence` to `reasoning`.
        Measured: ingest_log had 99 claims recorded against named concerns
        (111: 12 reads/69 claims, 108: 3/22, 72: 2/8), all invisible here.
        v1 recorded 104 evidence-class advances of 164; v2 recorded 1.

        Much of what this being reads is factual — SEC filings, Fed
        releases, wire copy — and for that material the content IS the
        evidence; there is no separate corroboration to go and find. S2
        §8.3's intent is anti-fabrication ("do not dress reasoning as
        evidence"), not "produce a second source". A ref must still
        correspond to something actually read; what changed is that
        "actually read" now includes reading.

        Both forms are accepted because a model will cite either: the
        dossier's own `src-N` label, or the url it was shown.
        """
        refs: set[str] = set()
        for a in self.advances:
            refs.update(a.get("evidence") or [])
        refs.update(self.concern.opening_citations)
        for s in self.sources:
            refs.add(f"src-{s['id']}")
            if s.get("url"):
                refs.add(s["url"])
        return refs

    def render(self, *, max_items: int = 12) -> str:
        c = self.concern
        lines = [
            f"CONCERN: {c.statement}",
            f"  why I opened it: {c.why_open}",
            f"  it closes when: {c.closing_condition}",
            f"  opened from: {c.origin}"
            + (f" ({c.origin_ref})" if c.origin_ref else ""),
            f"  history: {c.advance_count} advances, {c.stall_count} stalls, "
            f"{c.blocked_count} blocked",
        ]
        if self.advances:
            lines.append("  what I have established:")
            for a in self.advances[-max_items:]:
                refs = ",".join(a.get("evidence") or [])
                # Labelled so the being can name which one a new advance
                # REPLACES — see <supersedes> in the deliberation prompt.
                # Without a label it could only gesture at one by quoting it.
                lines.append(f"    - [adv-{a['id']}] [{a['kind']}] {a['summary']}"
                             + (f" [refs: {refs}]" if refs else ""))
        if self.sources:
            # Rendered so the being can CITE them: the evidence check reads
            # the same labels back out of <evidence>.
            #
            # WITH THEIR CLAIMS, since 2026-08-15. This printed a label, an
            # outlet and a COUNT — "9 claims kept" — and none of the claims.
            # The comment above says "so the being can CITE them" and there
            # was nothing to cite ABOUT. Concern 111 was shown twelve entries
            # for four unique sources and none of its 23 stored claims, then
            # asked for `<evidence>` refs "that appear in the dossier above".
            #
            # The claims are untrusted web text and this is the first thing in
            # the dossier that is. They are fenced (INV-011) as one block: a
            # stored claim replays into every deliberation from here,
            # indefinitely, so a claim that survives once survives forever.
            body = ["  what I have read on this:"]
            budget = MAX_DOSSIER_CLAIMS
            for s in self.sources[-max_items:]:
                kept = (f", {s['claims_kept']} claims kept"
                        if s.get("claims_kept") else ", nothing usable kept")
                body.append(f"    - [src-{s['id']}] {s['outlet']}{kept}"
                            + (f" — {s['url']}" if s.get("url") else ""))
                for claim in (s.get("claims") or [])[:MAX_CLAIMS_PER_SOURCE]:
                    if budget <= 0:
                        break
                    body.append(f"        · {claim}")
                    budget -= 1
            from newz.untrusted import wrap

            lines.append(wrap("\n".join(body[1:]), source=f"dossier:concern-{c.id}",
                              trust="world").render())
            lines.insert(len(lines) - 1, body[0])
        if self.setbacks:
            lines.append("  where it has failed to move:")
            for s in self.setbacks[-max_items:]:
                lines.append(f"    - [{s['kind']}] {s['brief']}")
        return "\n".join(lines)


def load_active(conn: sqlite3.Connection) -> list[Concern]:
    return [Concern.from_row(r) for r in conn.execute(
        "SELECT * FROM concerns WHERE status='open' ORDER BY id")]


def load_dossier(conn: sqlite3.Connection, concern_id: int) -> Dossier | None:
    row = conn.execute("SELECT * FROM concerns WHERE id=?", (concern_id,)).fetchone()
    if row is None:
        return None
    # Superseded advances are excluded: they are still in the table as the
    # record of what the being once held, but they are no longer what it
    # holds, so they are neither shown as established nor compared against
    # for novelty. See 0018_advance_superseded.sql.
    advances = [
        {"id": r["id"], "summary": r["summary"], "kind": r["kind"],
         "ts": r["ts"], "evidence": json.loads(r["evidence_json"] or "[]")}
        for r in conn.execute(
            "SELECT id, summary, kind, ts, evidence_json FROM concern_advances"
            " WHERE concern_id=? AND superseded_by IS NULL ORDER BY ts",
            (concern_id,))
    ]
    setbacks = [
        {"kind": r["kind"], "brief": r["brief"], "ts": r["ts"]}
        for r in conn.execute(
            "SELECT kind, brief, ts FROM concern_setbacks"
            " WHERE concern_id=? ORDER BY ts", (concern_id,))
    ]
    # What was actually read, and what it said. Claims live on the reading
    # episode's content_json and were read by nothing until 2026-08-15.
    claims_by_url: dict[str, list[str]] = {}
    for r in conn.execute(
        "SELECT source_ref, content_json FROM episodes WHERE kind='reading'"
        " AND json_extract(content_json,'$.concern_id')=?", (concern_id,)
    ):
        try:
            d = json.loads(r["content_json"] or "{}")
        except ValueError:
            continue
        url = d.get("url") or r["source_ref"]
        if not url:
            continue
        seen = claims_by_url.setdefault(url, [])
        for claim in d.get("claims") or []:
            if claim not in seen:          # the chunk overlap repeats claims
                seen.append(claim)

    # Deduplicated by url, EARLIEST label kept. Concern 111 showed twelve
    # entries for four unique sources — src-1/5/15 the same DOI, src-2/6/16
    # the same Wikipedia page. That is not a token problem, it is the dossier
    # misreporting the being's own reading to itself: it said "I have read
    # twelve things" when it had read four.
    sources: list[dict] = []
    by_url: dict[str, dict] = {}
    for r in conn.execute(
        "SELECT id, outlet, source, claims_kept FROM ingest_log"
        " WHERE concern_id=? AND skipped IS NULL ORDER BY ts", (concern_id,)
    ):
        raw = r["source"] or ""
        url = raw.split(":", 1)[-1] if ":" in raw else raw
        if url in by_url:
            # A re-read is not a second thing read. Keep the highest yield so
            # the count does not understate what the source gave.
            by_url[url]["claims_kept"] = max(by_url[url]["claims_kept"],
                                             r["claims_kept"])
            continue
        entry = {"id": r["id"], "outlet": r["outlet"], "url": url,
                 "claims_kept": r["claims_kept"],
                 "claims": claims_by_url.get(url, [])}
        by_url[url] = entry
        sources.append(entry)
    return Dossier(Concern.from_row(row), advances, setbacks, sources)


def create_concern(conn: sqlite3.Connection, concern: Concern) -> int:
    now = time.time()
    cur = conn.execute(
        "INSERT INTO concerns (opened_at, kind, statement, why_open,"
        " closing_condition, status, salience, origin, origin_ref, meta_json,"
        " opening_evidence, opening_citations_json)"
        " VALUES (?,?,?,?,?,'open',?,?,?,'{}',?,?)",
        (concern.opened_at or now, concern.kind, concern.statement,
         concern.why_open, concern.closing_condition, concern.salience,
         concern.origin, concern.origin_ref, concern.opening_evidence,
         json.dumps(concern.opening_citations)),
    )
    concern_id = cur.lastrowid
    write_episode(
        conn, kind="concern_opened", provenance="self",
        summary=f"I opened a concern ({concern.origin}): {concern.statement}"
                f" — I opened it because {concern.why_open}",
        content={"concern_id": concern_id, "statement": concern.statement,
                 "why_open": concern.why_open, "origin": concern.origin,
                 "closing_condition": concern.closing_condition},
        source_ref=f"concern:{concern_id}", commit=False,
    )
    conn.commit()
    return concern_id


def record_advance(
    conn: sqlite3.Connection, concern_id: int, *, summary: str, kind: str,
    evidence: list[str], source_ref: str | None = None,
    supersedes: int | None = None,
) -> None:
    """Record an advance. `supersedes` retires the advance it replaces.

    Retiring is not deleting: the row stays as the record of what the being
    once held, and sleep, retrieval and the episode log all still see it. It
    simply stops being compared against for novelty and stops being listed as
    established, because it is no longer what the being holds.
    """
    now = time.time()
    cur = conn.execute(
        "INSERT INTO concern_advances (concern_id, ts, kind, summary,"
        " evidence_json, source_ref) VALUES (?,?,?,?,?,?)",
        (concern_id, now, kind, summary, json.dumps(evidence), source_ref))
    if supersedes is not None:
        # Scoped to this concern so a mis-stated label cannot retire another
        # concern's thinking, and only ever retires a LIVE advance.
        conn.execute(
            "UPDATE concern_advances SET superseded_by=? WHERE id=? AND"
            " concern_id=? AND superseded_by IS NULL",
            (cur.lastrowid, supersedes, concern_id))
    conn.execute(
        "UPDATE concerns SET advance_count=advance_count+1, last_advanced_at=?,"
        " last_attempted_at=? WHERE id=?", (now, now, concern_id))
    statement = _statement_of(conn, concern_id)
    write_episode(
        conn, kind="advance", provenance="self",
        summary=f"I moved a concern — {statement}: {summary}",
        content={"concern_id": concern_id, "statement": statement,
                 "summary": summary, "kind": kind, "evidence": evidence},
        source_ref=f"concern:{concern_id}", commit=False,
    )
    conn.commit()


def record_setback(
    conn: sqlite3.Connection, concern_id: int, *, kind: str, brief: str,
    source_ref: str | None = None, charged: bool = True,
) -> str:
    """Record a failure to move. Returns the concern's status afterwards.

    `blocked` is distinct from `restated` (v1's lesson): being blocked is a
    correct report about a gap in the world, not the being circling, so it
    carries its own counter and its own gentler limit.

    **`charged=False`: the failure belongs to the diet, not the question.**
    (2026-08-15, operator approved.) A cycle whose ingest budget was paused
    will fail whatever the concern is, and charging it spends the concern on a
    condition it did not cause. The setback is still WRITTEN: the being should
    be able to say it failed, and the source-gap record still learns from it.
    What it does not do is count toward `STALL_LIMIT` or `BLOCKED_LIMIT`.

    Scoped to a paused diet ONLY. Research being switched off entirely is a
    different case, already handled upstream by the state trigger, and an
    earlier draft that cleared the charge for it too made every setback free.

    Deliberately not scoped to `restated`, which was the first draft of this.
    Measured setbacks from 2026-08-14 21:00: **blocked 11, restated 2**.
    `blocked` is the ordinary outcome — the model says "I could not move this,
    I need X" far more often than it circles — so exempting only restatements
    would have protected 2 of 13, and with three concerns left the pool would
    have been gone by morning.

    A cycle that DID read and still failed is charged exactly as before. On
    2026-08-15 at 13:34 concern 54 read three claims from Wikipedia, failed to
    move, and stalled — correctly, because the world answered and the answer
    did not help.
    """
    now = time.time()
    conn.execute(
        "INSERT INTO concern_setbacks (concern_id, ts, kind, brief, source_ref)"
        " VALUES (?,?,?,?,?)", (concern_id, now, kind, brief, source_ref))
    column = "blocked_count" if kind == "blocked" else "stall_count"
    if charged:
        conn.execute(
            f"UPDATE concerns SET {column}={column}+1, last_attempted_at=? WHERE id=?",
            (now, concern_id))
    else:
        # The attempt still happened, so staleness still advances — otherwise
        # `choose_concern` would pick the same concern every cycle and the
        # pool would stop rotating.
        conn.execute("UPDATE concerns SET last_attempted_at=? WHERE id=?",
                     (now, concern_id))
        logger.info("setback on concern %d not charged: the cycle could not read",
                    concern_id)

    row = conn.execute(
        "SELECT stall_count, blocked_count FROM concerns WHERE id=?",
        (concern_id,)).fetchone()
    status = "open"
    if row["stall_count"] >= STALL_LIMIT or row["blocked_count"] >= BLOCKED_LIMIT:
        # Letting go is a real loss, recorded as such rather than tidied away.
        status = "stalled"
        conn.execute("UPDATE concerns SET status='stalled' WHERE id=?", (concern_id,))

    # Failing to move something is as much a part of the life as moving it,
    # and the being should be able to say so rather than reporting only its
    # successes. A concern going stalled is the loss above, made sayable.
    statement = _statement_of(conn, concern_id)
    said = ("I could not move a concern"
            if kind == "blocked" else "I circled a concern without moving it")
    if status == "stalled":
        said += ", and it has now stalled"
    _affect(conn, "CONCERN_ABANDONED" if status == "stalled" else "CONCERN_BLOCKED",
            f"{kind}: {statement[:90]}")
    write_episode(
        conn, kind="setback", provenance="self",
        summary=f"{said} — {statement}: {brief}",
        content={"concern_id": concern_id, "statement": statement,
                 "kind": kind, "brief": brief, "status_after": status},
        source_ref=f"concern:{concern_id}", commit=False,
    )
    conn.commit()
    return status


def close_concern(conn: sqlite3.Connection, concern_id: int, *,
                  position: str, resolution: str) -> None:
    """Close a concern against its own condition (S2 §8.4).

    The position is NOT written to the Perspective here — INV-009 makes
    sleep its only writer. It rides on the episode, and sleep's
    `_closure_observations` offers it as a candidate with this concern's
    accumulated evidence. Closure records; sleep admits.
    """
    now = time.time()
    statement = _statement_of(conn, concern_id)
    conn.execute(
        "UPDATE concerns SET status='closed', closed_at=?, resolution=?"
        " WHERE id=?", (now, resolution, concern_id))
    refs = sorted({
        r for (ev,) in conn.execute(
            "SELECT evidence_json FROM concern_advances WHERE concern_id=?",
            (concern_id,))
        for r in json.loads(ev or "[]")
    })
    _affect(conn, "CONCERN_CLOSED", f"closed: {statement[:90]}")
    write_episode(
        conn, kind="concern_closed", provenance="self",
        summary=f"I closed a concern — {statement}: {resolution}",
        content={"concern_id": concern_id, "statement": statement,
                 "position": position, "resolution": resolution,
                 "evidence": refs},
        source_ref=f"concern:{concern_id}", commit=False,
    )
    conn.commit()


def _affect(conn: sqlite3.Connection, which: str, note: str) -> None:
    """Fold a concern outcome into affect (S2 §6.3's named sources).

    Never lets an affect failure cost the concern record it accompanies:
    how the being feels about an event is worth less than the event.
    """
    try:
        from newz.affect import store as affect_store

        affect_store.record(conn, getattr(affect_store, which),
                            source="concern", note=note)
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).warning("affect not updated (%s)", which,
                                            exc_info=True)


def _statement_of(conn: sqlite3.Connection, concern_id: int) -> str:
    """The concern's own words, so an episode summary stands alone.

    Sleep and retrieval read summaries without the dossier in hand; "I moved
    concern 111" would be unreadable to both.
    """
    row = conn.execute(
        "SELECT statement FROM concerns WHERE id=?", (concern_id,)).fetchone()
    return row["statement"] if row else f"concern {concern_id}"


# A concern that circled this fast was not hard, it was impossible. Measured
# 2026-08-31 across all 102 stalled concerns: 69 accumulated a setback a day
# or faster, 27 did not. The threshold separates them and is not tuned finer
# than the measurement supports.
REVIVE_RATE_PER_DAY = 1.0
# Long enough that a concern which stalled this morning is not revived this
# afternoon; short enough that a day's quiet is a real chance to come back.
REVIVE_QUIET_HOURS = 24.0
# Below this many open concerns the pool is starving: at
# REATTEMPT_COOLDOWN_HOURS = 6 five concerns supply under one eligible attempt
# an hour against three cycles, so the being is already exploring most cycles.
# Revival is a rescue, not a top-up — the opener maintains the pool, and
# `opener.py` puts its target at ten.
MIN_OPEN_CONCERNS = 5


def revivable(conn: sqlite3.Connection, *, now: float | None = None):
    """Stalled concerns that circled SLOWLY, best candidate first.

    Rate, not count. `stall_count` treats five circles over 330 hours and five
    over 8.3 as the same object; the first is a hard concern and the second is
    one the pool was too small to leave alone. See 0049.
    """
    now = now or time.time()
    rows = conn.execute(
        "SELECT c.id, c.stall_count,"
        "       COUNT(s.id) AS n,"
        "       MIN(s.ts) AS first_ts,"
        "       MAX(s.ts) AS last_ts"
        "  FROM concerns c JOIN concern_setbacks s ON s.concern_id = c.id"
        " WHERE c.status = 'stalled'"
        " GROUP BY c.id HAVING COUNT(s.id) >= 2").fetchall()
    out = []
    for r in rows:
        if (now - r["last_ts"]) / 3600.0 < REVIVE_QUIET_HOURS:
            continue
        span_days = (r["last_ts"] - r["first_ts"]) / 86400.0
        if span_days <= 0:
            continue
        rate = r["n"] / span_days
        if rate >= REVIVE_RATE_PER_DAY:
            continue
        out.append({"id": r["id"], "rate": rate, "setbacks": r["n"],
                    "over_days": span_days, "stall_count": r["stall_count"],
                    "quiet_h": (now - r["last_ts"]) / 3600.0})
    # Slowest circler first; a longer silence breaks the tie.
    out.sort(key=lambda d: (d["rate"], -d["quiet_h"]))
    return out


def revive(conn: sqlite3.Connection, cand: dict, *,
           now: float | None = None) -> None:
    """Put one stalled concern back, one attempt at a time.

    `stall_count` is decremented rather than reset: the revival buys a single
    attempt, and a concern that circles again lands straight back where it
    was. `last_attempted_at` is deliberately untouched — the candidate has
    been quiet for a day, so it is already past its cooldown and can be
    worked on the cycle after this one.
    """
    now = now or time.time()
    # Decrement whichever counter actually stalled it. Concerns 54 and 59 sit
    # at stall_count 0 and blocked_count 8: they went out on BLOCKED_LIMIT,
    # and taking a stall off them would buy nothing at all.
    row = conn.execute(
        "SELECT stall_count, blocked_count FROM concerns WHERE id=?",
        (cand["id"],)).fetchone()
    stalls, blocked = int(row["stall_count"]), int(row["blocked_count"])
    if stalls >= STALL_LIMIT:
        stalls -= 1
    elif blocked >= BLOCKED_LIMIT:
        blocked -= 1
    left = stalls
    conn.execute(
        "UPDATE concerns SET status='open', stall_count=?, blocked_count=?"
        " WHERE id=?", (stalls, blocked, cand["id"]))
    conn.execute(
        "INSERT INTO concern_revivals (ts, concern_id, setbacks, over_days,"
        " stall_count) VALUES (?,?,?,?,?)",
        (now, cand["id"], cand["setbacks"], round(cand["over_days"], 2), left))
    conn.commit()
    logger.info("revived concern %d: %d setbacks over %.1f days (%.2f/day),"
                " stall_count now %d", cand["id"], cand["setbacks"],
                cand["over_days"], cand["rate"], left)
