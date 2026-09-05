"""The versioned parser registry.

Dispatch is on the *normalized* MIME the fetcher produced, never on a file
extension or on what the body looks like. Every parse execution records the
parser's name and version, so a segment set can be attributed to the code that
produced it and a parser upgrade shows up as a new execution rather than as
drift in an old one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Segment:
    """A stable addressable unit within an artifact.

    `id` is stable across parses of the same bytes by the same parser version:
    it is derived from the artifact, the ordinal and the segment's own text, so
    a span recorded today still resolves tomorrow, and a segment whose text
    changed is a different segment rather than the same one saying something
    else.
    """

    id: str
    artifact_id: str
    ordinal: int
    kind: str
    locator: str
    text: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "artifact_id": self.artifact_id,
            "ordinal": self.ordinal,
            "kind": self.kind,
            "locator": self.locator,
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class ParseResult:
    artifact_id: str
    parser_name: str
    parser_version: str
    normalized_mime: str
    segments: tuple[Segment, ...]
    #: A hash over the segmentation, not over the body: two parser versions that
    #: read the same bytes differently produce different text hashes, which is
    #: the point.
    text_hash: str
    failures: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return not self.failures

    def segment(self, segment_id: str) -> Segment | None:
        for segment in self.segments:
            if segment.id == segment_id:
                return segment
        return None

    def text(self) -> str:
        return "\n\n".join(segment.text for segment in self.segments)

    def as_record(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
            "normalized_mime": self.normalized_mime,
            "text_hash": self.text_hash,
            "segments": [segment.as_record() for segment in self.segments],
            "failures": list(self.failures),
        }


class ParserFailure(Exception):
    """The body could not be segmented. Recorded, never guessed around."""


Parser = Callable[[bytes, str], tuple[tuple[Segment, ...], tuple[str, ...]]]

_REGISTRY: dict[str, tuple[str, str, Parser]] = {}


def register(mime: str, name: str, version: str, parser: Parser) -> None:
    _REGISTRY[mime] = (name, version, parser)


def parser_for(normalized_mime: str) -> tuple[str, str] | None:
    entry = _REGISTRY.get(normalized_mime)
    return (entry[0], entry[1]) if entry else None


def registered() -> dict[str, tuple[str, str]]:
    return {mime: (name, version) for mime, (name, version, _) in sorted(_REGISTRY.items())}


def segment_id(artifact_id: str, ordinal: int, text: str) -> str:
    digest = hashlib.sha256(f"{artifact_id}\x1f{ordinal}\x1f{text}".encode()).hexdigest()
    return f"segment:{digest[:24]}"


def parse(artifact_id: str, body: bytes, normalized_mime: str) -> ParseResult:
    """Segment a retained body, or fail with a reason.

    An unregistered MIME is a failure rather than a fallback to plain text: a
    body routed to the wrong parser produces segments that verify perfectly and
    mean nothing.
    """
    entry = _REGISTRY.get(normalized_mime)
    if entry is None:
        raise ParserFailure(f"no parser registered for {normalized_mime!r}")
    name, version, parser = entry

    try:
        segments, failures = parser(body, artifact_id)
    except ParserFailure:
        raise
    except Exception as error:  # a hostile document is not an exception path
        raise ParserFailure(f"{name} {version} failed: {type(error).__name__}: {error}") from error

    if not segments:
        # An empty result is a failure, not an empty success. A truncated HTML
        # document whose unclosed <title> swallows the body parses cleanly and
        # yields nothing, and recording that as a source with no assertions
        # rather than a source that could not be read is the quiet kind of wrong.
        raise ParserFailure(f"{name} {version} found no addressable text")

    text = "\n\n".join(segment.text for segment in segments)
    return ParseResult(
        artifact_id=artifact_id,
        parser_name=name,
        parser_version=version,
        normalized_mime=normalized_mime,
        segments=segments,
        text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        failures=failures,
    )
