"""Span verification: the mechanism the model boundary rests on.

`SPEC.md` section 13 names this as the primary defence against prompt injection,
and the reason is worth stating plainly. A model cannot introduce a quotation
that is not already present in retained text, because every quotation it
proposes is checked byte-exact against the segment at the recorded offsets. An
injected instruction can at most produce a proposal that fails this check.

The check is deliberately dumb. It does not normalize whitespace, fold case,
strip punctuation, or find the nearest match. Every one of those would be a
kindness that lets a quotation drift from what the source actually said, and the
whole system rests on "a source says X" not silently becoming something else.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum, unique

from newz.domain.records import Span
from newz.parse.registry import Segment


@unique
class SpanFailure(StrEnum):
    SEGMENT_NOT_FOUND = "segment_not_found"
    OFFSETS_OUT_OF_RANGE = "offsets_out_of_range"
    OFFSETS_INVERTED = "offsets_inverted"
    QUOTE_MISMATCH = "quote_mismatch"
    EMPTY_QUOTE = "empty_quote"
    WRONG_ARTIFACT = "wrong_artifact"


@dataclass(frozen=True, slots=True)
class SpanVerification:
    verified: bool
    failure: SpanFailure | None = None
    found: str = ""

    def __bool__(self) -> bool:
        return self.verified


def verify_span(span: Span, segments: Sequence[Segment]) -> SpanVerification:
    """Whether the quotation is there, exactly, at the offsets recorded."""
    if not span.quote:
        return SpanVerification(False, SpanFailure.EMPTY_QUOTE)

    segment = next((s for s in segments if s.id == span.segment_id), None)
    if segment is None:
        return SpanVerification(False, SpanFailure.SEGMENT_NOT_FOUND)
    if segment.artifact_id != span.artifact_id:
        return SpanVerification(False, SpanFailure.WRONG_ARTIFACT)
    if span.start < 0 or span.end < 0:
        return SpanVerification(False, SpanFailure.OFFSETS_OUT_OF_RANGE)
    if span.end <= span.start:
        return SpanVerification(False, SpanFailure.OFFSETS_INVERTED)
    if span.end > len(segment.text):
        return SpanVerification(False, SpanFailure.OFFSETS_OUT_OF_RANGE)

    found = segment.text[span.start : span.end]
    if found != span.quote:
        return SpanVerification(False, SpanFailure.QUOTE_MISMATCH, found=found)
    return SpanVerification(True)


def locate(quote: str, segments: Sequence[Segment], artifact_id: str) -> Span | None:
    """Build a verified span for a quotation, if it appears exactly once.

    Refuses an ambiguous quotation. A phrase appearing in two segments has two
    provenances, and picking the first would attach the claim to whichever the
    parser happened to emit first — a coin toss recorded as a fact.
    """
    if not quote:
        return None
    hits = [
        (segment, segment.text.index(quote))
        for segment in segments
        if quote in segment.text
    ]
    if len(hits) != 1:
        return None
    segment, start = hits[0]
    if segment.text.count(quote) != 1:
        return None
    return Span(
        artifact_id=artifact_id,
        segment_id=segment.id,
        start=start,
        end=start + len(quote),
        quote=quote,
        locator=segment.locator,
        verified=True,
    )
