"""The publisher concentration cap, enforced where the specification puts it.

`SPEC.md` section 5.1: over a rolling 30 days no publisher may exceed 20% of
retained full reads during Pilot or 10% during Production, unless the operator
records a scoped exception. The cap is enforced **at reservation**, not after the
fact, and the refusal is recorded with the publisher, the window and the figure
so it is visible rather than merely absent.

The distinction the section spends its length on is worth keeping in view here:
the cap governs acquisition and nothing else. It never invalidates a retained
artifact, never touches an admitted edge, and never changes an assessment. A
system that reconsidered evidence because its reading had become unbalanced
would be letting a property of the diet reach a conclusion, which is the failure
`TRUE_NORTH.md` names as permanent.

**The cap does not bind until it can be satisfied.** At a cold start the first
retained read is 100% of the window, the second 50%, and a cap applied there
would refuse exactly the reads that would make it satisfiable — a ceiling that
locks the door on the way in. So it binds only once the window holds enough
reads for the share to be reachable at all, which is `ceil(1 / cap)`: five reads
at 20%, ten at 10%. Below that the figure is still computed and still reported;
it just does not refuse. The specification did not settle this, and the choice is
recorded here rather than buried in a comparison.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from newz.pilot.modes import DeploymentMode, current_mode
from newz.store.db import Store

WINDOW_DAYS = 30

#: Pilot and Production are the tiers section 5.1 names. Shadow reads live
#: sources and so is held to the pilot cap; Fixture reads nothing over a network
#: and Lockdown reads nothing at all, so neither has a share to exceed.
CAPS: dict[DeploymentMode, float] = {
    DeploymentMode.SHADOW: 0.20,
    DeploymentMode.PILOT: 0.20,
    DeploymentMode.PRODUCTION: 0.10,
}


@dataclass(frozen=True, slots=True)
class Share:
    """One publisher's prospective share of the window, and what it means."""

    publisher_id: str
    publisher_name: str
    retained: int
    total: int
    cap: float | None
    exception_id: str = ""

    @property
    def prospective(self) -> float:
        """The share this publisher would hold if this read were retained."""
        return (self.retained + 1) / (self.total + 1)

    @property
    def binds(self) -> bool:
        """Whether the cap is reachable at this window volume at all."""
        if self.cap is None:
            return False
        return self.total + 1 >= math.ceil(1 / self.cap)

    @property
    def exceeded(self) -> bool:
        return self.binds and self.prospective > self.cap

    def detail(self) -> str:
        return (
            f"{self.publisher_name} would hold {self.prospective:.1%} of retained full reads "
            f"over {WINDOW_DAYS} days ({self.retained + 1} of {self.total + 1}), "
            f"past the {self.cap:.0%} cap"
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "publisher_id": self.publisher_id,
            "publisher_name": self.publisher_name,
            "retained": self.retained,
            "total": self.total,
            "cap": self.cap,
            "prospective": round(self.prospective, 4),
            "binds": self.binds,
            "exceeded": self.exceeded,
            "exception_id": self.exception_id,
        }


def cap_for(mode: DeploymentMode) -> float | None:
    return CAPS.get(mode)


def grant_exception(
    store: Store,
    *,
    exception_id: str,
    publisher_id: str,
    cap: float,
    granted_by: str,
    reason: str,
    expires_at: str,
) -> None:
    """Raise one publisher's cap, for a stated reason, until a stated date.

    Every argument is required, including the expiry. An exception without an
    end is not an exception to the cap; it is the cap being different for that
    publisher from now on, which is a diet decision wearing an exception's name.
    """
    if not (granted_by and reason and expires_at):
        raise ValueError("an exception needs an operator, a reason and an expiry")
    if not 0 < cap <= 1:
        raise ValueError(f"a cap is a share: {cap}")
    with store.write() as connection:
        connection.execute(
            "INSERT INTO concentration_exceptions "
            "(id, publisher_id, cap, granted_by, reason, expires_at, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (exception_id, publisher_id, cap, granted_by, reason, expires_at),
        )


def _live_exception(store: Store, publisher_id: str, local_day: str) -> tuple[str, float] | None:
    row = store.one(
        "SELECT id, cap FROM concentration_exceptions WHERE publisher_id = ? "
        "AND expires_at >= ? ORDER BY cap DESC LIMIT 1",
        publisher_id,
        local_day,
    )
    return (row["id"], row["cap"]) if row is not None else None


def share_if_retained(store: Store, source_revision_id: str, local_day: str) -> Share | None:
    """What this source's publisher would hold if this read were retained."""
    publisher = store.one(
        "SELECT p.id AS id, p.name AS name FROM source_revisions sr "
        "JOIN sources s ON s.id = sr.source_id "
        "JOIN publishers p ON p.id = s.publisher_id WHERE sr.id = ?",
        source_revision_id,
    )
    if publisher is None:
        return None

    window = (
        "SELECT COUNT(*) AS n FROM sightings sg "
        "JOIN source_revisions sr ON sr.id = sg.source_revision_id "
        "JOIN sources s ON s.id = sr.source_id "
        f"WHERE sg.observed_at > datetime(?, '-{WINDOW_DAYS} days')"
    )
    total = store.one(window, local_day)["n"]
    retained = store.one(window + " AND s.publisher_id = ?", local_day, publisher["id"])["n"]

    cap = cap_for(current_mode(store))
    exception_id = ""
    granted = _live_exception(store, publisher["id"], local_day)
    if granted is not None and cap is not None:
        exception_id, cap = granted[0], max(cap, granted[1])
    return Share(
        publisher_id=publisher["id"],
        publisher_name=publisher["name"],
        retained=retained,
        total=total,
        cap=cap,
        exception_id=exception_id,
    )


def would_exceed(store: Store, source_revision_id: str, local_day: str) -> str:
    """The refusal detail if this read would carry its publisher past the cap."""
    share = share_if_retained(store, source_revision_id, local_day)
    if share is None or not share.exceeded:
        return ""
    return share.detail()


def record_refusal(
    store: Store,
    *,
    idempotency_key: str,
    source_revision_id: str,
    lane: str,
    refusal: str,
    detail: str,
    local_day: str,
) -> None:
    """Write down a reservation that did not happen.

    `FetchRefusal`'s own docstring says refusals are recorded and never merely
    returned, and for fetches that was true. Reservations only ever raised, so a
    diet repeatedly hitting a ceiling read exactly like a diet nobody asked
    about.
    """
    with store.write() as connection:
        connection.execute(
            "INSERT INTO reservation_refusals (idempotency_key, source_revision_id, lane, "
            "refusal, detail, local_day, refused_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (idempotency_key, source_revision_id, lane, refusal, detail, local_day),
        )


def refusals(store: Store, local_day: str = "") -> tuple[dict[str, Any], ...]:
    """Recorded reservation refusals, newest last."""
    sql = "SELECT * FROM reservation_refusals"
    params: tuple[Any, ...] = ()
    if local_day:
        sql += " WHERE local_day = ?"
        params = (local_day,)
    return tuple(
        {
            "idempotency_key": row["idempotency_key"],
            "source_revision_id": row["source_revision_id"],
            "lane": row["lane"],
            "refusal": row["refusal"],
            "detail": row["detail"],
            "local_day": row["local_day"],
        }
        for row in store.query(sql + " ORDER BY id", *params)
    )


def report(store: Store, local_day: str) -> dict[str, Any]:
    """Every enabled publisher's standing against the cap. An operator figure."""
    mode = current_mode(store)
    cap = cap_for(mode)
    rows = store.query(
        "SELECT DISTINCT sr.id AS revision FROM diet_epoch_sources d "
        "JOIN source_revisions sr ON sr.id = d.source_revision_id "
        "WHERE d.epoch_id = (SELECT id FROM diet_epochs ORDER BY epoch DESC LIMIT 1) "
        "ORDER BY sr.id"
    )
    shares: dict[str, dict[str, Any]] = {}
    for row in rows:
        share = share_if_retained(store, row["revision"], local_day)
        if share is not None:
            shares[share.publisher_name] = share.as_record()
    return {
        "mode": mode.value,
        "cap": cap,
        "window_days": WINDOW_DAYS,
        "binding": any(entry["binds"] for entry in shares.values()),
        "publishers": shares,
        "refusals_today": [r for r in refusals(store, local_day)],
    }
