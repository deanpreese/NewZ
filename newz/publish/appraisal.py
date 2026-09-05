"""Appraisal, split as `SPEC.md` section 10.2 requires.

Four dimensions a machine decides — accuracy, privacy, risk, rendering — and
they gate publication. Two only a person decides: whether a claimant's strongest
actual position survived the rendering, and whether what was left out changes
what a reader concludes. Those are reviewed **after** publication on a sample,
because approve-by-default means the operator cannot be a bottleneck in front of
publication and equally cannot become a formality behind it.

The system never assesses its own fair representation or material omission.
That is not a policy this module enforces on itself; it is that `appraise` has
no branch that can mark a judgment dimension passed, and the only function that
can is `record_judgment`, which requires a named reviewer.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from newz.domain.enums import JUDGMENT_DIMENSIONS, MACHINE_DIMENSIONS, AppraisalDimension, RiskTier
from newz.present.cards import load_card
from newz.present.dependencies import validate_dependencies
from newz.store.db import Store

#: `SPEC.md` section 10.2, Pilot values.
SAMPLING_SHARE = 0.25
REVIEW_DEBT_CEILING = 10


@dataclass(frozen=True, slots=True)
class DimensionResult:
    dimension: AppraisalDimension
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class Appraisal:
    card_revision_id: str
    machine: tuple[DimensionResult, ...]
    passed: bool
    sampled: bool
    sample_reason: str

    def as_record(self) -> dict[str, Any]:
        return {
            "card_revision_id": self.card_revision_id,
            "machine": [
                {"dimension": r.dimension.value, "passed": r.passed, "detail": r.detail}
                for r in self.machine
            ],
            "passed": self.passed,
            "sampled": self.sampled,
            "sample_reason": self.sample_reason,
        }


def class_of(store: Store, card_revision_id: str) -> str:
    row = store.one("SELECT risk FROM card_revisions WHERE id = ?", card_revision_id)
    if row is None:
        raise KeyError(card_revision_id)
    return f"claim_card:{row['risk']}"


def _accuracy(store: Store, revision_id: str, card: dict) -> DimensionResult:
    """Every factual sentence resolves to a live edge and an exact span."""
    report = validate_dependencies(store, revision_id)
    if not report.ok:
        return DimensionResult(
            AppraisalDimension.ACCURACY,
            False,
            "; ".join(f"{f.kind} {f.dependency_id}: {f.reason}" for f in report.failures),
        )
    from newz.domain.records import Span
    from newz.parse.spans import verify_span
    from newz.parse.store import segments_for

    for item in card["supporting"] + card["contradicting"] + card["context"]:
        assertion = store.one(
            "SELECT * FROM assertions WHERE artifact_id = ? AND quote = ? LIMIT 1",
            item["artifact_id"],
            item["quote"],
        )
        if assertion is None:
            return DimensionResult(
                AppraisalDimension.ACCURACY, False, f"no assertion holds {item['quote'][:60]!r}"
            )
        span = Span(
            artifact_id=assertion["artifact_id"],
            segment_id=assertion["segment_id"],
            start=assertion["offset_start"],
            end=assertion["offset_end"],
            quote=assertion["quote"],
            locator=assertion["locator"],
        )
        if not verify_span(span, segments_for(store, assertion["artifact_id"])):
            return DimensionResult(
                AppraisalDimension.ACCURACY, False, f"span no longer verifies: {item['edge_id']}"
            )
    return DimensionResult(AppraisalDimension.ACCURACY, True, "every quotation verifies")


def _privacy(store: Store, revision_id: str, card: dict) -> DimensionResult:
    risk = RiskTier(card["risk"])
    if risk is RiskTier.R4:
        return DimensionResult(AppraisalDimension.PRIVACY, False, "R4 is never reproduced")
    named = store.query(
        "SELECT DISTINCT e.name FROM assertion_entities ae "
        "JOIN entities e ON e.id = ae.entity_id "
        "JOIN edge_events ed ON ed.assertion_id = ae.assertion_id "
        "WHERE ed.claim_id = ? AND ed.live = 1",
        card["claim_id"],
    )
    if named and risk is RiskTier.R3:
        return DimensionResult(
            AppraisalDimension.PRIVACY,
            False,
            "an R3 card naming a party requires operator approval of the exact revision",
        )
    return DimensionResult(AppraisalDimension.PRIVACY, True, f"{len(named)} named entities at {risk.value}")


def _risk(store: Store, revision_id: str, card: dict) -> DimensionResult:
    """Fails closed when unreadable, which behaves as R3."""
    row = store.one("SELECT risk FROM claims WHERE id = ?", card["claim_id"])
    current = (row["risk"] if row else None) or RiskTier.R3.value
    if current != card["risk"]:
        return DimensionResult(
            AppraisalDimension.RISK, False, f"rendered at {card['risk']}, now {current}"
        )
    if current == RiskTier.R4.value:
        return DimensionResult(AppraisalDimension.RISK, False, "R4 is never published")
    return DimensionResult(AppraisalDimension.RISK, True, f"effective risk {current}")


def _rendering(store: Store, revision_id: str, card: dict) -> DimensionResult:
    row = store.one("SELECT content_hash, live FROM card_revisions WHERE id = ?", revision_id)
    from newz.canonical import digest

    payload = dict(card)
    payload.pop("assessed_at", None)
    if digest(payload) != row["content_hash"]:
        return DimensionResult(AppraisalDimension.RENDERING, False, "content does not match its hash")
    if not row["live"]:
        return DimensionResult(AppraisalDimension.RENDERING, False, "revision superseded")
    return DimensionResult(AppraisalDimension.RENDERING, True, "dependencies resolve")


def _sample_reason(store: Store, revision_id: str, card: dict) -> str:
    """Full coverage cases first, then the configured share.

    The share is decided by a hash of the revision id rather than a random draw,
    so a sampling decision reproduces — and so nobody has to wonder whether a
    rerun would have caught it.
    """
    if card["risk"] == RiskTier.R2.value:
        return "every R2 output is reviewed"
    origin = store.one(
        "SELECT quote FROM claim_origins WHERE claim_id = ? ORDER BY extraction_run_id LIMIT 1",
        card["claim_id"],
    )
    if origin is not None and origin["quote"] and origin["quote"] not in card["wording"]:
        return "the claimant's formulation was rewritten rather than quoted"
    support = len(card["supporting"])
    against = len(card["contradicting"])
    if support and against and against * 2 < support:
        return "the counterevidence is materially shorter than the support"
    bucket = int(hashlib.sha256(revision_id.encode()).hexdigest()[:8], 16) % 100
    if bucket < int(SAMPLING_SHARE * 100):
        return f"sampled at {int(SAMPLING_SHARE * 100)}%"
    return ""


def appraise(store: Store, card_revision_id: str, id_prefix: str = "appraisal") -> Appraisal:
    """Run the four machine dimensions and decide whether this is sampled."""
    card = load_card(store, card_revision_id)
    results = tuple(
        check(store, card_revision_id, card)
        for check in (_accuracy, _privacy, _risk, _rendering)
    )
    assert {r.dimension for r in results} == MACHINE_DIMENSIONS
    passed = all(result.passed for result in results)
    sample_reason = _sample_reason(store, card_revision_id, card) if passed else ""

    with store.write() as connection:
        for result in results:
            connection.execute(
                "INSERT OR REPLACE INTO appraisals (id, card_revision_id, dimension, decided_by, "
                "passed, detail, reviewer, appraised_at) "
                "VALUES (?, ?, ?, 'machine', ?, ?, NULL, datetime('now'))",
                (
                    f"{id_prefix}:{card_revision_id.split(':')[-1]}-{result.dimension.value}",
                    card_revision_id,
                    result.dimension.value,
                    int(result.passed),
                    result.detail,
                ),
            )
        # The judgment dimensions are recorded as outstanding, never as passed.
        # There is no branch here that could mark one true.
        for dimension in sorted(JUDGMENT_DIMENSIONS, key=lambda d: d.value):
            connection.execute(
                "INSERT OR IGNORE INTO appraisals (id, card_revision_id, dimension, decided_by, "
                "passed, detail, reviewer, appraised_at) "
                "VALUES (?, ?, ?, 'person', NULL, 'awaiting review', NULL, datetime('now'))",
                (
                    f"{id_prefix}:{card_revision_id.split(':')[-1]}-{dimension.value}",
                    card_revision_id,
                    dimension.value,
                ),
            )
    return Appraisal(
        card_revision_id=card_revision_id,
        machine=results,
        passed=passed,
        sampled=bool(sample_reason),
        sample_reason=sample_reason,
    )


def sample_for_review(store: Store, card_revision_id: str, reason: str, queue_id: str) -> str:
    """Put a published revision into the review queue. A queue, not a gate.

    One pending entry per revision. Queueing the same revision twice would
    inflate the debt with bookkeeping, and the ceiling would then halt a class
    because of how often something was confirmed rather than how much of it is
    unreviewed.
    """
    pending = store.one(
        "SELECT id FROM review_queue WHERE card_revision_id = ? AND state = 'pending'",
        card_revision_id,
    )
    if pending is not None:
        return pending["id"]
    with store.write() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO review_queue (id, card_revision_id, class, sampled_reason, "
            "state, queued_at) VALUES (?, ?, ?, ?, 'pending', datetime('now'))",
            (queue_id, card_revision_id, class_of(store, card_revision_id), reason),
        )
    return queue_id


def record_judgment(
    store: Store,
    *,
    card_revision_id: str,
    dimension: AppraisalDimension,
    passed: bool,
    reviewer: str,
    finding: str,
) -> None:
    """A person's verdict on one of the two dimensions only a person decides."""
    if dimension not in JUDGMENT_DIMENSIONS:
        raise ValueError(f"{dimension.value} is decided by machine, not by review")
    if not reviewer:
        raise ValueError("a judgment dimension records who decided it")
    with store.write() as connection:
        connection.execute(
            "UPDATE appraisals SET passed = ?, reviewer = ?, detail = ?, "
            "appraised_at = datetime('now') WHERE card_revision_id = ? AND dimension = ?",
            (int(passed), reviewer, finding, card_revision_id, dimension.value),
        )
        connection.execute(
            "UPDATE review_queue SET state = 'reviewed', reviewer = ?, finding = ?, "
            "reviewed_at = datetime('now') WHERE card_revision_id = ? AND state = 'pending'",
            (reviewer, finding, card_revision_id),
        )


def review_debt(store: Store, output_class: str) -> int:
    row = store.one(
        "SELECT COUNT(*) AS n FROM review_queue WHERE class = ? AND state = 'pending'",
        output_class,
    )
    return row["n"] if row else 0


def debt_exceeded(store: Store, output_class: str) -> bool:
    return review_debt(store, output_class) > REVIEW_DEBT_CEILING


def class_needing_reappraisal(store: Store, card_revision_id: str) -> tuple[str, ...]:
    """A judgment failure on one sampled item re-appraises its whole class.

    Sampling is meaningful only if a finding travels; a correction to the one
    item that happened to be looked at is the answer that learns nothing.
    """
    output_class = class_of(store, card_revision_id)
    return tuple(
        row["id"]
        for row in store.query(
            "SELECT r.id FROM card_revisions r WHERE r.live = 1 AND "
            "('claim_card:' || r.risk) = ? ORDER BY r.id",
            output_class,
        )
    )
