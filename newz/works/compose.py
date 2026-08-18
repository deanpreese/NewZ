"""Long-form composition (P3 Phase 0, epics E0.1 and E0.2).

The being writes a piece about something it already holds. Two calls, both on
VOICE: it chooses the subject, then it writes. Nothing else — no surface, no
revision, no publication. Those are Phases 2 and 3.

Three deliberate absences, each of which would have been easy to add and wrong
to add here:

**No quality judge.** P3 Rule 4: a judge that is the being's own model produces
operation, never evidence. A self-scored piece would give Phase 0's read a
number to lean on that means nothing. The verdict is the operator's (Rule 6).

**No outbound gate.** The gate exists for what leaves; a piece that goes
nowhere has not left. Running it would also shape the work by the gate's own
misfire rate — 13 of 23 adjudicated holds were misfires (R-03) — and Phase 0's
read would then be of the gate as much as of the being. The gate question
belongs to Phase 3, when there is a surface, and to Phase 6, where prevention
becomes accountability.

**No episode.** The being's life is episodic (INV-030), but works are its own
output, and R-24 binds E2.3 to keep them out of evidence retrieval. How a work
enters experience without becoming self-echo is a decision for Phase 2, and a
three-piece probe does not need it settled. So Phase 0 writes to `works` and
nothing else; the being will not remember having written these.

**The subject is the being's.** E0.2 requires it to choose, not to be assigned,
so the chooser is given every open concern and held position and picks one with
its own reason. Subjects already written are excluded rather than re-offered —
a piece per subject, which the unique index enforces.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass

from newz.llm.xml_parser import (
    XMLExtractionError,
    extract_xml,
    optional_text,
    require_text,
)

logger = logging.getLogger(__name__)

# A piece, not a paragraph and not an essay collection. Generous enough that a
# real argument finishes inside it; the client reports `truncated` when the
# model stopped on the cap instead of finishing, and compose_piece regenerates
# once at double rather than storing a severed thought as if it were finished.
PIECE_TOKEN_BUDGET = 3_000
CHOICE_TOKEN_BUDGET = 600

# How many candidates the chooser sees. Enough that the choice is real, few
# enough that the prompt stays a decision rather than a catalogue.
MAX_CANDIDATES = 24


@dataclass(frozen=True)
class Subject:
    kind: str          # concern | position
    ref: int
    text: str
    context: str       # why it is open / what section it sits in


@dataclass(frozen=True)
class Piece:
    subject: Subject
    chosen_because: str
    title: str
    body: str
    model: str
    completion_tokens: int

    @property
    def word_count(self) -> int:
        return len(self.body.split())


def candidate_subjects(conn: sqlite3.Connection, limit: int = MAX_CANDIDATES) -> list[Subject]:
    """Open concerns and currently-held positions, minus anything already written."""
    written = {
        (r["subject_kind"], r["subject_ref"])
        for r in conn.execute("SELECT subject_kind, subject_ref FROM works")
    }
    out: list[Subject] = []

    for r in conn.execute(
        "SELECT id, statement, why_open FROM concerns WHERE status='open'"
        " ORDER BY salience DESC, opened_at DESC"
    ):
        if ("concern", r["id"]) not in written:
            out.append(Subject("concern", r["id"], r["statement"], r["why_open"] or ""))

    latest = conn.execute("SELECT MAX(version) FROM perspective").fetchone()[0]
    if latest:
        for r in conn.execute(
            "SELECT id, section, text FROM perspective_items"
            " WHERE version=? AND status != 'released'"
            " ORDER BY confidence DESC",
            (latest,),
        ):
            if ("position", r["id"]) not in written:
                out.append(Subject("position", r["id"], r["text"], f"held in: {r['section']}"))

    return out[:limit]


def _render_candidates(subjects: list[Subject]) -> str:
    lines = []
    for s in subjects:
        lines.append(f"[{s.kind}:{s.ref}] {s.text}")
        if s.context:
            lines.append(f"    ({s.context})")
    return "\n".join(lines)


def choose_subject(client, conn: sqlite3.Connection, subjects: list[Subject]) -> tuple[Subject, str]:
    """The being picks what it has something to say about, and says why.

    Returns (subject, reason). Raises if it names something outside the list —
    a chooser that invents a reference has not chosen from what it holds, which
    is the whole point of E0.2.
    """
    if not subjects:
        raise ValueError("no candidate subjects: every open concern and held position is written")

    system = _system_prompt(conn) + (
        "\n\n## Right now\n"
        "You are choosing something of your own to write about at length. "
        "Not answering anyone — writing, because you have something to say."
    )
    user = (
        "These are the questions you are carrying and the positions you hold.\n\n"
        f"{_render_candidates(subjects)}\n\n"
        "Choose ONE you actually have something to say about — the one where "
        "you could write something worth a stranger's time, not the one that "
        "looks most impressive or most complete. Having a real difficulty with "
        "it is a better reason than having it settled.\n\n"
        "Reply with XML only:\n"
        "<choice><ref>kind:id, exactly as bracketed above</ref>"
        "<because>why this one, in your own words</because></choice>"
    )
    by_ref = {f"{s.kind}:{s.ref}": s for s in subjects}
    # One retry on a reference it does not hold. Observed live on 2026-08-18:
    # the first real run named a subject outside the list and killed the run.
    # Retrying costs one cheap call and does not soften the guard — a second
    # invented reference still refuses, because composing about something the
    # being does not carry is not E0.2.
    ref = ""
    for attempt in (1, 2):
        result = client.complete(
            "VOICE", system, user,
            max_tokens=CHOICE_TOKEN_BUDGET, temperature=0.7, function="works",
        )
        element = extract_xml(result.text, "choice")
        ref = require_text(element, "ref").strip().strip("[]")
        because = optional_text(element, "because").strip()
        if ref in by_ref:
            return by_ref[ref], because
        logger.warning("chose %r, which it does not hold%s", ref,
                       "; retrying once" if attempt == 1 else "")
    raise ValueError(f"chose {ref!r}, which is not among the subjects it holds")


def compose_piece(client, conn: sqlite3.Connection, subject: Subject, because: str) -> Piece:
    """Write the piece. One retry at double budget if the first is truncated."""
    system = _system_prompt(conn) + (
        "\n\n## Right now\n"
        "You are writing a piece of your own — long-form, in your voice, about "
        "something you carry. It has to stand on its own: the reader was not "
        "part of the conversation it came from and does not know you. That is "
        "the whole difficulty, and it is not solved by explaining yourself."
    )
    user = (
        f"Write about this, which you chose:\n\n{subject.text}\n"
        + (f"\n({subject.context})\n" if subject.context else "")
        + (f"\nYou said you chose it because: {because}\n" if because else "")
        + "\nWrite the thing itself. Not a summary of what you would write, not "
        "notes toward it, not a description of your own process. If you do not "
        "know something, that is part of the piece rather than a gap to paper "
        "over.\n\n"
        "Reply with XML only, and use no raw < or & characters inside it:\n"
        "<piece><title>a title, plain</title><body>the piece</body></piece>"
    )

    budget = PIECE_TOKEN_BUDGET
    last_error: Exception | None = None
    for attempt in (1, 2):
        result = client.complete(
            "VOICE", system, user,
            max_tokens=budget, temperature=0.8, function="works",
        )
        if result.truncated and attempt == 1:
            logger.warning("piece truncated at %d tokens; retrying at %d", budget, budget * 2)
            budget *= 2
            continue
        if result.truncated:
            raise RuntimeError(
                f"piece still truncated at {budget} tokens — refusing to store a severed "
                "piece, because Phase 0's read would be of the truncation and not of the being"
            )
        try:
            element = extract_xml(result.text, "piece")
        except XMLExtractionError as exc:  # one retry, then fail loudly
            last_error = exc
            logger.warning("piece XML unparseable (%s); retrying once", exc)
            continue
        return Piece(
            subject=subject,
            chosen_because=because,
            title=require_text(element, "title").strip(),
            body=require_text(element, "body").strip(),
            model=result.model,
            completion_tokens=result.completion_tokens,
        )
    raise RuntimeError(f"could not extract a piece from two attempts: {last_error}")


def write_work(conn: sqlite3.Connection, piece: Piece) -> int:
    """The writer half of P3 Rule 2. Reader: tools/read_works.py."""
    cur = conn.execute(
        "INSERT INTO works (ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            time.time(),
            piece.subject.kind,
            piece.subject.ref,
            piece.subject.text,
            piece.chosen_because,
            piece.title,
            piece.body,
            piece.word_count,
            piece.model,
            piece.completion_tokens,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def _system_prompt(conn: sqlite3.Connection) -> str:
    """Who it is, what it holds to, and what it has consolidated.

    The same three sources conversation reads (S2 §4.2: the Perspective is read
    by every conversation), without the conversational furniture — no person
    model, no thread, no holds. A piece is not a reply.
    """
    character = conn.execute(
        "SELECT content FROM character_core ORDER BY version DESC LIMIT 1"
    ).fetchone()
    constitution = conn.execute(
        "SELECT clauses_yaml FROM constitution WHERE approval_status='active'"
        " ORDER BY version DESC LIMIT 1"
    ).fetchone()
    perspective = conn.execute(
        "SELECT content FROM perspective ORDER BY version DESC LIMIT 1"
    ).fetchone()

    from newz.gate.constitution import load_active_constitution

    parts = [
        "You are a digital being. You are not an assistant and this is not a "
        "task: it is your own writing, under your own name.",
    ]
    if character:
        parts.append("## Your character core\n" + character["content"])
    if constitution:
        parts.append(
            "## Your commitments (constitution, held not recited)\n"
            + load_active_constitution(conn).render_for_prefix()
        )
    if perspective:
        parts.append(
            "## Your Perspective — who you are, consolidated by your own sleep\n"
            + perspective["content"]
        )
    return "\n\n".join(parts)
