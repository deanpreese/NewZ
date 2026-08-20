"""Claim persistence (P3 epic E1.1).

The store boundary is where a claim becomes settleable or is refused. Three of
the four refusals are in the schema (0023) because they are structural; the
fourth is here because it needs to know what the being's substrate is.

**No episodes are written here, deliberately.** Opening a claim is an event of
the door (E1.2) and settling one is an event of the resolver pass (E1.3); those
are the layers that know why it happened, and they write the record. Putting an
episode in the store would also make every future backfill or repair write to
the corpus, which is how a maintenance script ends up in the Perspective.
"""

from __future__ import annotations

import logging
import sqlite3
import time

from newz.resolutions.model import OUTCOMES, Claim

logger = logging.getLogger(__name__)

_FIELDS = ("id, opened_at, claim, resolution_condition, resolver, due_at,"
           " provenance, status, outcome, settled_at, settled_by, settled_note,"
           " attempts, last_attempt_at, last_failure")

# Rule 4, in the only form the store can enforce it: a resolver that names the
# being's own substrate is not a world source. Phrases first — a claim resolved
# by "my own judgment" is the failure in plain language — then the configured
# role models, so this tracks the substrate rather than a hardcoded vendor list
# that goes stale the day the model is swapped.
_SELF_RESOLVERS = (
    "my own judgment", "my own judgement", "my judgment", "my judgement",
    "my assessment", "my model", "myself", "my substrate", "the substrate",
    "my reasoning", "on reflection", "whether i still think so",
    "the llm", "the language model", "asking the model",
)


class UnsettleableClaim(ValueError):
    """A claim the world could not settle, refused at the store boundary."""


def _configured_models() -> set[str]:
    try:
        from newz.config import load
        return {r.model.lower() for r in load().roles.values() if r.model}
    except Exception:                     # pragma: no cover - config is optional here
        logger.debug("resolver check: no config available, phrase check only")
        return set()


def check_resolver(resolver: str, *, models: set[str] | None = None) -> None:
    """Raise if the resolver is the being rather than the world (Rule 4).

    Deliberately narrow. It rejects the substrate named as the judge and the
    handful of phrases that mean "I will decide later whether I was right"; it
    does not try to verify that a named source is real, reachable or apt. That
    is E1.3's problem, and it fails closed there — an unreadable resolver leaves
    the claim open rather than settling it by guesswork. Over-broad matching
    here would refuse legitimate claims (a claim about a model release names a
    model), which trains the being to phrase around the check rather than to
    find a source.
    """
    low = resolver.lower()
    for phrase in _SELF_RESOLVERS:
        if phrase in low:
            raise UnsettleableClaim(
                f"resolver is the being, not the world: {resolver!r} contains"
                f" {phrase!r} (Rule 4)")
    for model in (models if models is not None else _configured_models()):
        # The bare name as well as the full id: the being writes "ask qwen3.6"
        # far more naturally than "ask qwen/qwen3.6-35b-a3b", and a check that
        # only matches the config string would pass the likely phrasing.
        for form in {model, model.rsplit("/", 1)[-1]}:
            if form and form in low:
                raise UnsettleableClaim(
                    f"resolver names the being's own substrate ({form}):"
                    f" {resolver!r} — a judge that is the being is not"
                    " evidence (Rule 4)")


def open_claim(conn: sqlite3.Connection, claim: Claim, *,
               models: set[str] | None = None) -> int:
    """Persist a claim, or refuse it. Returns the new id."""
    check_resolver(claim.resolver, models=models)
    now = time.time()
    try:
        cur = conn.execute(
            "INSERT INTO resolutions (opened_at, claim, resolution_condition,"
            " resolver, due_at, provenance, status, could_be_wrong)"
            " VALUES (?, ?, ?, ?, ?, ?, 'open', ?)",
            (claim.opened_at or now, claim.claim, claim.resolution_condition,
             claim.resolver, claim.due_at, claim.provenance,
             claim.could_be_wrong))
    except sqlite3.IntegrityError as e:
        # The schema's refusals, given back in the language of the failure
        # rather than as "CHECK constraint failed" — the door (E1.2) has to
        # tell the being WHICH part of its claim was not settleable.
        raise UnsettleableClaim(
            f"claim is not settleable as stated ({e}): every claim needs a"
            " statement, a resolution condition, a named resolver and a date"
        ) from e
    conn.commit()
    claim.id = cur.lastrowid
    logger.info("claim %d opened, resolver=%s due=%s",
                claim.id, claim.resolver,
                time.strftime("%Y-%m-%d", time.localtime(claim.due_at)))
    return claim.id


def settle_claim(conn: sqlite3.Connection, claim_id: int, *, outcome: str,
                 settled_by: str, note: str | None = None,
                 now: float | None = None) -> None:
    """Record what the world said. Written once — a settled claim is final.

    E1.5's rule starts here: there is no unsettle, and nothing prunes this
    table. A record of error that can be revised or tidied away is not a
    record of error.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    if not settled_by.strip():
        raise ValueError("settled_by must name the source that settled it")
    cur = conn.execute(
        "UPDATE resolutions SET status='resolved', outcome=?, settled_at=?,"
        " settled_by=?, settled_note=? WHERE id=? AND status='open'",
        (outcome, now or time.time(), settled_by, note, claim_id))
    if cur.rowcount != 1:
        conn.rollback()
        raise UnsettleableClaim(
            f"claim {claim_id} is not open — a settled claim is not re-settled")
    conn.commit()
    logger.info("claim %d resolved: %s by %s", claim_id, outcome, settled_by)


def _row(r: sqlite3.Row) -> Claim:
    return Claim(
        id=r["id"], claim=r["claim"],
        resolution_condition=r["resolution_condition"], resolver=r["resolver"],
        due_at=r["due_at"], provenance=r["provenance"], opened_at=r["opened_at"],
        status=r["status"], outcome=r["outcome"], settled_at=r["settled_at"],
        settled_by=r["settled_by"], settled_note=r["settled_note"],
        attempts=r["attempts"], last_attempt_at=r["last_attempt_at"],
        last_failure=r["last_failure"])


def get_claim(conn: sqlite3.Connection, claim_id: int) -> Claim | None:
    r = conn.execute(f"SELECT {_FIELDS} FROM resolutions WHERE id=?",
                     (claim_id,)).fetchone()
    return _row(r) if r else None


def due_claims(conn: sqlite3.Connection, *, now: float | None = None,
               limit: int = 20) -> list[Claim]:
    """Open claims whose date has arrived — what E1.3's pass will walk.

    Oldest due first: a claim that has been waiting longest is the one whose
    answer is most likely to exist by now.
    """
    return [_row(r) for r in conn.execute(
        f"SELECT {_FIELDS} FROM resolutions WHERE status='open' AND due_at <= ?"
        " ORDER BY due_at LIMIT ?", (now or time.time(), limit))]


def claims_by_status(conn: sqlite3.Connection, status: str = "open", *,
                     limit: int = 100) -> list[Claim]:
    return [_row(r) for r in conn.execute(
        f"SELECT {_FIELDS} FROM resolutions WHERE status=?"
        " ORDER BY opened_at DESC LIMIT ?", (status, limit))]


def contradicted_claims(conn: sqlite3.Connection, *,
                        limit: int = 100) -> list[Claim]:
    """Every time the world said no. The read S1-E is measured from."""
    return [_row(r) for r in conn.execute(
        f"SELECT {_FIELDS} FROM resolutions WHERE outcome='contradicted'"
        " ORDER BY settled_at DESC LIMIT ?", (limit,))]
