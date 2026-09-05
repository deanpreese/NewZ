"""Noticing: marking something in retained material as worth attention.

A notice records the artifact, the span it arose from, and its reason, in the
system's own words. It is not evidence. It falls under the same rule as a lead —
it may direct attention and may establish nothing — and the way that holds here
is that the `notices` table has no column that could become an assertion, an
edge or a basis, and this module has no function that writes to those tables.

Two refusals matter more than the rest.

**A notice must arise from retained material**, so it points at a span that
verifies. A notice with no span is an opinion with a timestamp.

**A notice must not arise from NewZ's own output.** Essays, cards, reports and
raw model proposals are projections, and attention drawn from a projection is
attention feeding on itself: confidence rising while grounding falls. The check
is concrete rather than aspirational — the artifact must have been sighted at a
source, and must not be an artifact this system wrote.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.domain.enums import NoticeProvenanceKind
from newz.domain.records import Span
from newz.parse.spans import verify_span
from newz.parse.store import segments_for
from newz.store.db import Store


class NoticeRefused(Exception):
    """A notice that would have fed on the system's own output, or on nothing."""


@dataclass(frozen=True, slots=True)
class Notice:
    id: str
    artifact_id: str
    segment_id: str
    quote: str
    locator: str
    reason: str
    provenance_kind: NoticeProvenanceKind

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "segment_id": self.segment_id,
            "quote": self.quote,
            "locator": self.locator,
            "reason": self.reason,
            "provenance_kind": self.provenance_kind.value,
        }


def is_system_output(store: Store, artifact_id: str) -> bool:
    """Whether this artifact is something NewZ produced rather than retrieved."""
    proposal = store.one(
        "SELECT id FROM extraction_runs WHERE raw_artifact_id = ?", artifact_id
    )
    return proposal is not None


def externally_sighted(store: Store, artifact_id: str) -> bool:
    return (
        store.one("SELECT id FROM sightings WHERE artifact_id = ? LIMIT 1", artifact_id)
        is not None
    )


def record_notice(
    store: Store,
    *,
    notice_id: str,
    artifact_id: str,
    segment_id: str,
    quote: str,
    start: int,
    end: int,
    locator: str,
    reason: str,
    provenance_kind: NoticeProvenanceKind,
    noticed_at: str = "",
) -> Notice:
    """Record a notice, or refuse and say which rule it broke.

    `noticed_at` is an input rather than a clock reading, for the same reason
    every other derivation here takes its time as an argument: a row that can
    only be aged by editing it is a row whose decay cannot be tested without
    breaking the immutability that decay exists to respect.
    """
    if not reason.strip():
        raise NoticeRefused("a notice says why it was worth marking")

    if is_system_output(store, artifact_id):
        raise NoticeRefused(
            "a notice may not arise from NewZ's own output: attention drawn from a "
            "projection is attention feeding on itself"
        )
    if not externally_sighted(store, artifact_id):
        raise NoticeRefused("a notice arises from material that was retrieved and retained")

    span = Span(
        artifact_id=artifact_id,
        segment_id=segment_id,
        start=start,
        end=end,
        quote=quote,
        locator=locator,
    )
    verification = verify_span(span, segments_for(store, artifact_id))
    if not verification:
        raise NoticeRefused(
            f"a notice points at a span that verifies: {verification.failure.value}"
        )

    with store.write() as connection:
        connection.execute(
            "INSERT INTO notices (id, artifact_id, segment_id, quote, offset_start, offset_end, "
            "locator, reason, provenance_kind, noticed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(NULLIF(?, ''), datetime('now')))",
            (
                notice_id,
                artifact_id,
                segment_id,
                quote,
                start,
                end,
                locator,
                reason,
                provenance_kind.value,
                noticed_at,
            ),
        )
    return Notice(
        id=notice_id,
        artifact_id=artifact_id,
        segment_id=segment_id,
        quote=quote,
        locator=locator,
        reason=reason,
        provenance_kind=provenance_kind,
    )


def notice_over_span(
    store: Store, notice_id: str, artifact_id: str, quote: str, reason: str,
    provenance_kind: NoticeProvenanceKind = NoticeProvenanceKind.OBSERVED,
    noticed_at: str = "",
) -> Notice:
    """Convenience: locate the quotation in the artifact's segments and notice it."""
    from newz.parse.spans import locate

    span = locate(quote, segments_for(store, artifact_id), artifact_id)
    if span is None:
        raise NoticeRefused("the quotation does not appear exactly once in this artifact")
    return record_notice(
        store,
        notice_id=notice_id,
        artifact_id=artifact_id,
        segment_id=span.segment_id,
        quote=span.quote,
        start=span.start,
        end=span.end,
        locator=span.locator,
        reason=reason,
        provenance_kind=provenance_kind,
        noticed_at=noticed_at,
    )


def notices(store: Store, include_decayed: bool = True) -> tuple[dict[str, Any], ...]:
    sql = "SELECT * FROM notices"
    if not include_decayed:
        sql += " WHERE superseded_by IS NULL"
    return tuple(dict(row) for row in store.query(sql + " ORDER BY id"))
