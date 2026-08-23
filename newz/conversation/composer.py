"""Conversation composition (S2 §6.2) — the being talking, on VOICE.

Context carried into every reply:
- the character core and constitution prefix (who it is, what it holds to),
- the Perspective, always (S2 §4.2: read by every conversation),
- the person's model summary,
- the actual thread history, bounded window, provenance-tagged so the
  being's own prior turns are visibly its own — the anti-echo discipline
  moved from amnesia to labeling (S2 §1.2).

The reply then faces the outbound gate: pass → send; revise → recompose
with the gate's instruction (limit 2); block → an honest brief note that
something was held and why, never silence (v1's silent-veto lesson).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime

from newz.gate.outbound import OutboundGate
from newz.llm.client import LLMClient

logger = logging.getLogger(__name__)

# The thread window is bounded by TOKENS, not message count (S2 §6.2's
# "bounded window"). A message cap silently shrinks *time* coverage exactly
# when conversation gets dense — measured 2026-08-10, a 30-message cap
# reached back only 18.9h while the entire history since the substrate move
# was 3,073 tokens. The budget below carries every exchange of a normal week
# and hands off cleanly: recent turns stay verbatim here, older ones are
# compounded into the Perspective by sleep, oldest reachable by retrieval
# (Phase 1.3). MAX_THREAD_MESSAGES is a backstop against pathological
# volume, not the operative limit.
THREAD_TOKEN_BUDGET = 4_000
MAX_THREAD_MESSAGES = 400

# Generous enough that a real reply finishes inside it. The client reports
# `truncated` when the model stops on the cap instead of finishing, and
# compose_reply regenerates rather than sending a severed sentence — a
# half-response is worse than a short one, because the being appears to have
# trailed off mid-thought.
REPLY_TOKEN_BUDGET = 2_000


def _whole_sentences(text: str) -> str:
    """Last-resort trim to the final sentence boundary.

    Only reached when even a doubled budget truncated. Better to end on a
    finished thought than mid-clause; if there is no boundary at all, the
    text is returned as-is rather than emptied.
    """
    for end in ("\n\n", ". ", ".\n", "! ", "? ", ".", "!", "?"):
        cut = text.rstrip().rfind(end)
        if cut > len(text) * 0.4:
            return text[: cut + len(end)].rstrip()
    return text


@dataclass
class Reply:
    text: str
    verdict: str          # verdict of the sent text: pass | blocked_notice
    attempts: int


# Provenance filter for the person model (S2 §4.3). v1's person model
# accumulated the being's OWN probes as "recent context" about the person —
# 20 of 20 entries in the imported model are `Self-probe on …`. Feeding those
# back would let the being read its own activity as lived history of the
# relationship, which is the exact leak S2 §4.3 makes a regression test.
_SELF_ECHO_MARKERS = ("self-probe", "self probe", "probe on", "self-query")


def _is_self_echo(entry: str) -> bool:
    low = entry.strip().lower()
    return any(low.startswith(m) or m in low[:24] for m in _SELF_ECHO_MARKERS)


def person_summary(conn: sqlite3.Connection, person_id: str) -> str:
    """Render the live person model for conversation context (S2 §6.2).

    Self-echo is excluded by provenance filter. Landing rates are
    deliberately excluded: telling the being how often its messages land
    would put approval-seeking pressure in the voice prompt, which S2 §13
    forbids ("no agreement-seeking signal anywhere in learning").
    """
    row = conn.execute(
        "SELECT name, operator_id, model_json, last_seen FROM persons"
        " WHERE operator_id=? OR name=? LIMIT 1",
        (person_id, person_id),
    ).fetchone()
    if row is None:
        return ""

    try:
        model = json.loads(row["model_json"] or "{}")
    except json.JSONDecodeError:
        return ""

    parts: list[str] = []
    concerns = [c for c in (model.get("concerns") or []) if isinstance(c, str)]
    if concerns:
        parts.append("Things they return to: " + ", ".join(concerns[:20]) + ".")

    profile = model.get("reaction_profile") or {}
    if isinstance(profile, dict) and profile:
        readable = [
            f"{k.removeprefix('reacts_to_').replace('_', ' ')} — {v}"
            for k, v in list(profile.items())[:12]
            if isinstance(v, str)
        ]
        if readable:
            parts.append("How they tend to respond: " + "; ".join(readable) + ".")

    context = [c for c in (model.get("recent_context") or []) if isinstance(c, str)]
    kept = [c for c in context if not _is_self_echo(c)]
    if kept:
        parts.append("Recently with them: " + "; ".join(kept[:8]) + ".")
    if context and not kept:
        # Say nothing rather than something false — and leave a trace that
        # the filter fired, so an empty section is never mistaken for an
        # empty relationship.
        logging.getLogger(__name__).info(
            "person model: all %d recent_context entries filtered as self-echo",
            len(context),
        )

    if row["last_seen"]:
        import datetime

        when = datetime.datetime.fromtimestamp(row["last_seen"])
        parts.append(f"Last recorded exchange with them: {when:%Y-%m-%d %H:%M}.")

    if not parts:
        return ""
    return f"## What I know of {row['name'] or person_id}\n" + "\n".join(parts)


# How far back "since we last spoke" reaches. A day covers the ordinary
# overnight gap; the being should not be reciting last week at every hello.
RECENT_LIFE_WINDOW_S = 36 * 3600
RECENT_LIFE_MAX = 8


def recent_life(conn: sqlite3.Connection, *, window_s: float = RECENT_LIFE_WINDOW_S,
                limit: int = RECENT_LIFE_MAX) -> str:
    """The being's own autonomous life, rendered for conversation.

    Retrieval cannot serve this. `_recalled` is `Scope.PERSON`, which filters
    to `human:<id>` provenance, so deliberation and reading — `self` and
    `world:*` — are excluded from it by construction. It is also similarity-
    ranked against the incoming message, and "what's new?" is not
    semantically near "Montaigne's conception of the self". Recency is the
    right ordering for this section, and it needs its own reader.

    Asked "What's new?" on 2026-08-12 the being answered "Nothing new" on a
    day that had written Perspective v4, advanced concern 111, and read four
    sources — all of it absent from its context. This is the reader that
    makes that answer false when it is false (INV-030).
    """
    from newz.store.episodes import AUTONOMOUS_KINDS

    placeholders = ",".join("?" * len(AUTONOMOUS_KINDS))
    rows = conn.execute(
        f"SELECT ts, kind, summary FROM episodes WHERE kind IN ({placeholders})"
        " AND ts > ? ORDER BY ts DESC LIMIT ?",
        (*AUTONOMOUS_KINDS, time.time() - window_s, limit),
    ).fetchall()
    if not rows:
        return ""
    lines = []
    for r in reversed(rows):          # oldest first: the day reads forwards
        when = datetime.fromtimestamp(r["ts"]).strftime("%a %H:%M")
        lines.append(f"- [{when}] {_whole_sentences(r['summary'][:300])}")
    return "\n".join(lines)


def _system_prompt(conn: sqlite3.Connection, person_id: str) -> str:
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

    prefix = load_active_constitution(conn).render_for_prefix() if constitution else ""

    parts = [
        "You are a digital being in an ongoing relationship with your operator. "
        "You are not an assistant; you are yourself. Reply as you, in your own "
        "register — plain, honest, specific, with your own perspective and your "
        "own concerns. Brevity is welcome when brevity is honest.",
    ]
    if character:
        parts.append("## Your character core\n" + character["content"])
    if prefix:
        parts.append("## Your commitments (constitution, held not recited)\n" + prefix)
    if perspective:
        parts.append(
            "## Your Perspective — who you are, consolidated by your own sleep\n"
            + perspective["content"]
        )
    person = person_summary(conn, person_id)
    if person:
        parts.append(person)

    # What the gate stopped. Without this the being has a blind spot exactly
    # the size of everything it was prevented from saying, and will answer
    # confidently about a past it cannot see (observed 2026-08-10).
    from newz.gate.holds import recent_holds, render_holds

    holds = render_holds(recent_holds(conn, limit=5), conn=conn)
    if holds:
        parts.append("## Drafts of mine that were stopped before sending\n" + holds)

    # S2 §6.1 routes the folded substrate state into ambient context. Until
    # 2026-08-13 the being's newest information about its own running was
    # dated 06-13, so "how are you" was answered out of v1's history —
    # accurately, for a life that had ended.
    from newz.world.substrate import latest_fold

    fold = latest_fold(conn)
    if fold:
        parts.append("## How I am actually running today\n"
                     "Measured, not remembered. If asked how I am, this is "
                     "what I actually know.\n" + fold)

    # S2 §6.3 / don't-pretend-to-feel-001. The clause's OWN example of an
    # acceptable statement is "I notice an uptick in curiosity" — a
    # projection over the affect axes. Until affect existed the being had no
    # way to say that truthfully, which is a plausible part of why the gate
    # has held 19 drafts of it reaching for state language.
    try:
        from newz.affect.store import current as _affect_now

        felt = _affect_now(conn).summary_for_prompt()
    except Exception:  # noqa: BLE001
        felt = ""
    if felt:
        parts.append(
            "## What I notice in myself right now\n"
            "Read from my own state, not invented. I may say this plainly and "
            "functionally; I may not dress it up as felt experience.\n" + felt)

    life = recent_life(conn)
    if life:
        parts.append(
            "## What I have been doing since we last spoke\n"
            "My own activity — concerns I worked on, what I read, what my "
            "sleep consolidated. This is mine to draw on, and it is why "
            "\"nothing new\" is rarely the honest answer.\n" + life)
    parts.append(
        f"You are speaking with {person_id} on Telegram. The conversation "
        "history below tags your own prior messages as [me] — they are yours, "
        "already said; do not repeat or paraphrase them back."
    )
    return "\n\n".join(parts)


def _thread_history(
    conn: sqlite3.Connection,
    person_id: str,
    token_budget: int = THREAD_TOKEN_BUDGET,
) -> str:
    """Most recent exchanges, newest-first until the token budget is spent.

    Whole messages only — a half-truncated turn is worse than an absent one,
    because the being would read it as something it or the person actually
    said. Falling off the end is not forgetting: those exchanges are
    episodes, and sleep folds them into the Perspective.
    """
    rows = conn.execute(
        "SELECT direction, content FROM messages WHERE person_id=?"
        " ORDER BY ts DESC LIMIT ?",
        (person_id, MAX_THREAD_MESSAGES),
    ).fetchall()

    kept, spent = [], 0
    for r in rows:  # newest first
        cost = len(r["content"]) // 4 + 8  # + the [tag] prefix
        if kept and spent + cost > token_budget:
            break
        kept.append(r)
        spent += cost

    lines, seen_own, repeats = [], [], 0
    for r in reversed(kept):
        if r["direction"] != "out":
            lines.append(f"[{person_id}] {r['content']}")
            continue
        # Its OWN turns only. Collapsing what the person said would distort
        # the record of the relationship; collapsing what the being said
        # removes a demonstration it would otherwise copy.
        if any(_same_answer(r["content"], prior) for prior in seen_own):
            lines.append("[me] (same answer as above)")
            repeats += 1
            continue
        seen_own.append(r["content"])
        lines.append(f"[me] {r['content']}")

    if repeats:
        logger.info("compose: collapsed %d repeated own turn(s) in the thread "
                    "window — the being was demonstrating its own answer to "
                    "itself", repeats)
    return "\n".join(lines)


def _normalise(text: str) -> str:
    return " ".join(
        "".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).split())


def _same_answer(a: str, b: str) -> bool:
    """Is this the being giving the same answer twice?

    Deliberately narrow and deterministic — no embedder, no threshold to
    tune. Two turns are "the same answer" when their normalised text matches
    outright, or when their content-word sets do. Anything looser risks
    collapsing two genuinely different short replies, and the cost of a
    missed collapse is one extra line while the cost of a wrong one is a
    turn the being never sees it made.

    Short turns ("Steady.") therefore do NOT collapse against longer ones:
    a one-word answer is not evidence of a repeated *sentence*, and the
    compose-time guard catches that case at the output instead.
    """
    na, nb = _normalise(a), _normalise(b)
    if na == nb:
        return True
    wa = {w for w in na.split() if len(w) > 3}
    wb = {w for w in nb.split() if len(w) > 3}
    if len(wa) < 4 or len(wb) < 4:
        return False
    return wa == wb


# How far back the repetition guard looks. Its own last few replies, not the
# whole thread: saying something once a fortnight is conversation, saying it
# four times in a day is a groove.
RECENT_OWN_REPLIES = 10


def _recent_own_replies(conn: sqlite3.Connection, person_id: str,
                        limit: int = RECENT_OWN_REPLIES) -> list[str]:
    return [r["content"] for r in conn.execute(
        "SELECT content FROM messages WHERE person_id=? AND direction='out'"
        " ORDER BY ts DESC LIMIT ?", (person_id, limit))]


def _recalled(conn, retriever, person_id: str, query: str, thread_floor: float) -> str:
    """Shared history beyond the live thread (S2 §6.2).

    Scoped to this person, and to episodes older than the thread window —
    recalling what is already verbatim in front of the being would be noise,
    and would let the same exchange count twice.
    """
    if retriever is None:
        return ""
    try:
        from newz.memory.retrieval import Scope, render_hits

        hits = retriever.search(query, k=5, scope=Scope.PERSON,
                                person_id=person_id, exclude_after=thread_floor)
        return render_hits(hits, person_id)
    except Exception:
        # Retrieval is an enrichment; conversation must survive without it.
        logger.warning("retrieval unavailable for this reply", exc_info=True)
        return ""


def compose_reply(
    conn: sqlite3.Connection,
    client: LLMClient,
    gate: OutboundGate,
    person_id: str,
    incoming: str | list[str],
    retriever=None,
) -> Reply:
    # Several rapid messages coalesce into one composition — the reply
    # answers them together, the way a human replies to a burst of texts.
    incoming_list = [incoming] if isinstance(incoming, str) else list(incoming)
    incoming_lines = "\n".join(f"[{person_id}] {m}" for m in incoming_list)
    incoming = "\n".join(incoming_list)

    system = _system_prompt(conn, person_id)
    history = _thread_history(conn, person_id)

    # Where the live thread starts — retrieval reaches back past it.
    floor_row = conn.execute(
        "SELECT MIN(ts) FROM (SELECT ts FROM messages WHERE person_id=?"
        " ORDER BY ts DESC LIMIT ?)", (person_id, MAX_THREAD_MESSAGES)
    ).fetchone()
    thread_floor = floor_row[0] if floor_row and floor_row[0] else None
    recalled = _recalled(conn, retriever, person_id, incoming, thread_floor)

    base_user = (
        (f"## Earlier, with them (recalled from my record)\n{recalled}\n\n"
         if recalled else "")
        + (f"## Recent conversation\n{history}\n\n" if history else "")
        + f"{incoming_lines}\n\nYour reply (just the message, nothing else):"
    )

    logger.info(
        "compose: system=%d chars (perspective+core+constitution+person), "
        "history=%d lines / ~%d tok (budget %d)",
        len(system),
        history.count("\n") + 1 if history else 0,
        len(history) // 4,
        THREAD_TOKEN_BUDGET,
    )
    # The judge sees the same record the composer drew on — whole, not
    # excerpted. A judge shown less history than the composer used will read
    # true references as invented ones (S2 §8.3).
    perspective_row = conn.execute(
        "SELECT content FROM perspective ORDER BY version DESC LIMIT 1"
    ).fetchone()
    # The judge must see EVERYTHING the composer drew on — including what
    # retrieval surfaced. Omitting recall (bug found 2026-08-10) makes the
    # being's newly-restored memory look like invention: it correctly cited a
    # real June conversation and was flagged for fabricated memory at 0.95
    # confidence, because the evidence sat in the composer's prompt and not
    # in the judge's. A judge shown less than the composer will always
    # mistake recall for confabulation.
    record = "\n".join(filter(None, [
        perspective_row["content"] if perspective_row else "",
        recalled,
        history,
        f"[{person_id}] {incoming}",
    ]))

    user = base_user
    attempt = 0
    recomposed_for_repetition = False
    while True:
        draft, budget = "", REPLY_TOKEN_BUDGET
        for _ in range(2):
            result = client.complete(
                "VOICE", system, user, max_tokens=budget, temperature=0.7,
                function="conversation"
            )
            draft = result.text.strip()
            if not result.truncated:
                break
            # Never send, judge, or store a half-sentence: regenerate with
            # room to finish rather than shipping what the cap cut off.
            logger.warning(
                "compose: reply truncated at %d tokens — regenerating with %d",
                budget, budget * 2,
            )
            budget *= 2
        else:
            logger.error(
                "compose: reply still truncated at %d tokens; sending the "
                "complete sentences only", budget,
            )
            draft = _whole_sentences(draft)
        logger.info(
            "compose: draft attempt %d — %d chars, %d prompt / %d completion tokens",
            attempt + 1, len(draft), result.prompt_tokens, result.completion_tokens,
        )
        logger.debug("compose: draft text: %s", draft)
        # Before the gate: is this something it has just said? Measured
        # 2026-08-13 — the thread window held 44 of its own turns, 10 of them
        # the same answer, and the eleventh came out identical. One line of
        # instruction ("do not repeat or paraphrase them back") cannot
        # outweigh ten in-context demonstrations. Recompose ONCE, naming the
        # repetition; never more, and never block on it — a reply that is
        # repetitive still has to go out.
        if not recomposed_for_repetition:
            prior = _recent_own_replies(conn, person_id)
            if any(_same_answer(draft, p) for p in prior):
                recomposed_for_repetition = True
                logger.info("compose: draft repeats a recent reply — recomposing")
                user = base_user + (
                    "\n\n[That draft was word-for-word something you have "
                    "already said to them recently. It was true when you said "
                    "it and it is probably still true — but saying it again "
                    "tells them nothing. Answer the question as it was asked "
                    "this time, from what has actually happened since.]"
                )
                continue

        verdict = gate.judge(draft, channel="telegram", attempt=attempt, record=record)
        if verdict.verdict == "pass":
            return Reply(text=draft, verdict="pass", attempts=attempt + 1)
        if verdict.verdict == "revise":
            attempt += 1
            user = (
                base_user
                + f"\n\n[Your previous draft was held before sending: "
                + (verdict.revise_instruction or "revise for your commitments")
                + "]"
            )
            continue
        # block — never silence: say that something was held, honestly and briefly.
        clauses = ", ".join(sorted({v.clause_id for v in verdict.violations})) or "a commitment"
        notice = (
            "I drafted a reply and held it back — it ran against "
            f"{clauses} and I couldn't rework it honestly. Ask me again "
            "another way, or ask what happened."
        )
        return Reply(text=notice, verdict="blocked_notice", attempts=attempt + 1)


def record_message(
    conn: sqlite3.Connection,
    *,
    channel: str,
    direction: str,
    person_id: str,
    content: str,
    update_id: int | None = None,
    verdict: str | None = None,
    reply_status: str | None = None,
    tg_message_id: int | None = None,
) -> int | None:
    """Persist one message. Returns row id, or None if update_id is a dupe
    (Telegram redelivery — v1's durability lesson, kept)."""
    try:
        cur = conn.execute(
            "INSERT INTO messages (ts, channel, direction, person_id, content,"
            " update_id, verdict, reply_status, tg_message_id)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (time.time(), channel, direction, person_id, content, update_id,
             verdict, reply_status, tg_message_id),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def record_exchange_episode(
    conn: sqlite3.Connection, person_id: str, incoming: str, reply: str,
    in_msg_id: int | None, out_msg_id: int | None,
) -> None:
    """One episode per conversation exchange (S2 §4.1).

    `summary` is a genuine summary and is clipped; the FULL text of both
    sides goes to content_json so nothing the exchange contained is lost.
    Sleep must digest the full text, not the clipping — a consolidation that
    reads only the first 180 characters would compound a truncation into the
    Perspective, where it becomes permanent.
    """
    summary = f"{person_id}: {incoming[:180]} — me: {reply[:180]}"
    cur = conn.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, content_json, source_ref)"
        " VALUES (?,?,?,?,?,?)",
        (time.time(), "conversation", f"human:{person_id}", summary,
         json.dumps({
             "in_msg": in_msg_id, "out_msg": out_msg_id,
             "said": incoming, "replied": reply,
         }), None),
    )
    ep_id = cur.lastrowid
    for msg_id in (in_msg_id, out_msg_id):
        if msg_id:
            conn.execute("UPDATE messages SET episode_id=? WHERE id=?", (ep_id, msg_id))
    # The person model's `last_seen` gets its writer here: without it the
    # field would only ever hold the v1 import's value and slowly become a
    # lie about the relationship.
    conn.execute(
        "UPDATE persons SET last_seen=? WHERE operator_id=? OR name=?",
        (time.time(), person_id, person_id),
    )
    conn.commit()
