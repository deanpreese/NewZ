"""Admitting a class of source to carry R2 evidence, adversarially.

`PLAN.md` Phase 6 item 3: R2 source classes are added after direct adversarial
review. `SPEC.md` section 8 puts active institutions, current secrecy and named
organisations at R2, needing strong provenance, two independent countable bases
and explicit allegation labels.

The evidence bar was already enforced — the promotion thresholds carry it. What
this adds is the admission: whether a class of source may supply that evidence
at all, and on whose judgment.

**A review with no case against is not adversarial.** That is the whole design.
It would be easy to record a review as a reviewer, a date and a verdict, and
such a record would be indistinguishable from a rubber stamp — the same shape
whether somebody argued about it or nobody did. So a review must state the
strongest case *against* admitting the class and then answer it, and both fields
are required. What a reviewer could not think of an argument against, they have
not reviewed adversarially; they have approved.

**And it must say what would disqualify the class later.** A review that cannot
be falsified by anything is a preference. `disqualifiers` is what a future
operator reads to know whether the review still holds, and it is the difference
between a judgment and a permanent grant.

**Membership is declared, never inferred.** A class the system could widen by
itself would be a class whose review covers whatever it later decides to
include, which is the review's authority being borrowed by things nobody looked
at.

Reviews expire. Institutions change, and a source class is a claim about how a
kind of publisher behaves now.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from newz.clock import as_utc, from_ledger, stamp
from newz.domain.enums import RiskTier
from newz.store.db import Store

#: How long a review holds before somebody has to look again. A year, because a
#: source class is a claim about how a kind of publisher behaves now, and the
#: institutions at R2 are exactly the ones that reorganise.
REVIEW_MONTHS = 12


class ReviewRefused(Exception):
    """A review that would not be a review, or a class that has not had one."""


@dataclass(frozen=True, slots=True)
class ClassReview:
    id: str
    source_class: str
    reviewer: str
    trusted_for: str
    case_against: str
    answer: str
    disqualifiers: str
    expires_at: str
    withdrawn_at: str = ""
    withdrawn_reason: str = ""

    def live(self, now: datetime) -> bool:
        return not self.withdrawn_at and as_utc(now) <= from_ledger(self.expires_at)

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_class": self.source_class,
            "reviewer": self.reviewer,
            "trusted_for": self.trusted_for,
            "case_against": self.case_against,
            "answer": self.answer,
            "disqualifiers": self.disqualifiers,
            "expires_at": self.expires_at,
            "withdrawn_reason": self.withdrawn_reason,
        }


def review_class(
    store: Store,
    *,
    review_id: str,
    source_class: str,
    reviewer: str,
    trusted_for: str,
    case_against: str,
    answer: str,
    disqualifiers: str,
    expires_at: datetime,
) -> ClassReview:
    """Record a direct adversarial review admitting a source class to R2."""
    if not reviewer.startswith("operator:"):
        raise ReviewRefused(
            f"a direct adversarial review is a person's, not {reviewer or 'nobody'}'s"
        )
    missing = [
        name
        for name, value in (
            ("trusted_for", trusted_for),
            ("case_against", case_against),
            ("answer", answer),
            ("disqualifiers", disqualifiers),
        )
        if not value.strip()
    ]
    if missing:
        raise ReviewRefused(
            f"a review missing {', '.join(missing)} is not adversarial: a record with a "
            "reviewer, a date and a verdict is the same shape whether somebody argued "
            "about it or nobody did"
        )
    if case_against.strip() == answer.strip():
        raise ReviewRefused("the answer restates the case against rather than meeting it")

    with store.write() as connection:
        connection.execute(
            "INSERT INTO r2_class_reviews (id, source_class, reviewer, trusted_for, "
            "case_against, answer, disqualifiers, expires_at, withdrawn_at, "
            "withdrawn_reason, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, '', datetime('now'))",
            (
                review_id,
                source_class,
                reviewer,
                trusted_for,
                case_against,
                answer,
                disqualifiers,
                stamp(expires_at),
            ),
        )
    return ClassReview(
        review_id,
        source_class,
        reviewer,
        trusted_for,
        case_against,
        answer,
        disqualifiers,
        stamp(expires_at),
    )


def withdraw_review(store: Store, review_id: str, reason: str, now: datetime) -> None:
    """Take an admission back. A disqualifier fired, or the class changed."""
    if not reason.strip():
        raise ValueError("withdrawing a review records why")
    with store.write() as connection:
        connection.execute(
            "UPDATE r2_class_reviews SET withdrawn_at = ?, withdrawn_reason = ? WHERE id = ?",
            (stamp(now), reason, review_id),
        )


def add_member(store: Store, source_class: str, source_revision_id: str, added_by: str) -> None:
    """Put a source in a class. Declared, never inferred."""
    if not added_by.startswith("operator:"):
        raise ReviewRefused(
            "class membership is declared by an operator: a class the system could "
            "widen by itself is a class whose review covers whatever it later includes"
        )
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO r2_class_members (source_class, source_revision_id, "
            "added_by, added_at) VALUES (?, ?, ?, datetime('now'))",
            (source_class, source_revision_id, added_by),
        )


def class_of_source(store: Store, source_revision_id: str) -> str:
    row = store.one(
        "SELECT source_class FROM r2_class_members WHERE source_revision_id = ? "
        "ORDER BY source_class LIMIT 1",
        source_revision_id,
    )
    return row["source_class"] if row else ""


def live_review(store: Store, source_class: str, now: datetime) -> ClassReview | None:
    for row in store.query(
        "SELECT * FROM r2_class_reviews WHERE source_class = ? ORDER BY rowid DESC",
        source_class,
    ):
        review = _as_review(row)
        if review.live(now):
            return review
    return None


def _as_review(row) -> ClassReview:
    return ClassReview(
        id=row["id"],
        source_class=row["source_class"],
        reviewer=row["reviewer"],
        trusted_for=row["trusted_for"],
        case_against=row["case_against"],
        answer=row["answer"],
        disqualifiers=row["disqualifiers"],
        expires_at=row["expires_at"],
        withdrawn_at=row["withdrawn_at"] or "",
        withdrawn_reason=row["withdrawn_reason"],
    )


def unreviewed_r2_sources(store: Store, claim_id: str, now: datetime) -> tuple[str, ...]:
    """Sources carrying countable evidence on an R2 claim with no live admission.

    Read from the live edges rather than the catalogue, because what matters is
    which sources are actually holding the claim up.
    """
    rows = store.query(
        "SELECT DISTINCT a.source_revision_id AS revision FROM edge_events e "
        "JOIN assertions a ON a.id = e.assertion_id "
        "WHERE e.claim_id = ? AND e.live = 1 AND e.admitted = 1 ORDER BY revision",
        claim_id,
    )
    unreviewed = []
    for row in rows:
        source_class = class_of_source(store, row["revision"])
        if not source_class:
            unreviewed.append(f"{row['revision']} (in no reviewed class)")
        elif live_review(store, source_class, now) is None:
            unreviewed.append(f"{row['revision']} (class {source_class} has no live review)")
    return tuple(unreviewed)


def r2_admission_refusal(store: Store, claim_id: str, risk: str, now: datetime) -> str:
    """Why an R2 claim may not publish on the sources currently holding it up."""
    if risk != RiskTier.R2.value:
        return ""
    unreviewed = unreviewed_r2_sources(store, claim_id, now)
    if not unreviewed:
        return ""
    return (
        "R2 evidence may come only from a source class admitted by direct adversarial "
        f"review: {'; '.join(unreviewed)}"
    )


def report(store: Store, now: datetime) -> dict[str, Any]:
    reviews = tuple(
        _as_review(row) for row in store.query("SELECT * FROM r2_class_reviews ORDER BY id")
    )
    members = store.query(
        "SELECT source_class, COUNT(*) AS n FROM r2_class_members GROUP BY source_class "
        "ORDER BY source_class"
    )
    return {
        "reviews": [review.as_record() for review in reviews],
        "live_classes": sorted(
            {review.source_class for review in reviews if review.live(now)}
        ),
        "expired_or_withdrawn": sorted(
            {review.source_class for review in reviews if not review.live(now)}
        ),
        "members": {row["source_class"]: row["n"] for row in members},
        "review_months": REVIEW_MONTHS,
    }
