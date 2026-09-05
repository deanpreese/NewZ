"""Plain text: paragraphs separated by blank lines.

The simplest parser in the registry, and the one whose locators are least
useful, which is honest — a text file has no structure to name beyond position.
"""

from __future__ import annotations

from newz.parse.registry import Segment, register, segment_id

NAME = "text.stdlib"
VERSION = "1.0.0"


def parse_text(body: bytes, artifact_id: str) -> tuple[tuple[Segment, ...], tuple[str, ...]]:
    text = body.decode("utf-8", errors="replace")
    segments: list[Segment] = []
    ordinal = 0
    for block in text.split("\n\n"):
        content = " ".join(block.split())
        if not content:
            continue
        segments.append(
            Segment(
                id=segment_id(artifact_id, ordinal, content),
                artifact_id=artifact_id,
                ordinal=ordinal,
                kind="paragraph",
                locator=f"paragraph {ordinal + 1}",
                text=content,
            )
        )
        ordinal += 1
    return tuple(segments), ()


register("text/plain", NAME, VERSION, parse_text)
