"""HTML segmentation on the standard library.

Block-level text units become segments, each carrying a locator that names where
in the document it came from — the nearest preceding heading and the unit's
ordinal within it, so a person reading a claim card can find the sentence in the
original without counting paragraphs from the top.

Two exclusions are deliberate. **Script and style content never becomes a
segment**, because it is not text the publisher published. **Comments never
become a segment either**, and that one has a consequence worth stating: an
instruction hidden in an HTML comment cannot reach the model at all, because
prompts are built from segments. The acquisition plane still records it as an
instruction attempt against the source revision — the observation survives even
though the payload never enters the evidence path.
"""

from __future__ import annotations

from html.parser import HTMLParser

from newz.parse.registry import Segment, register, segment_id

NAME = "html.stdlib"
VERSION = "1.0.0"

BLOCK_TAGS = frozenset(
    {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "td", "th", "dd", "dt"}
)
HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg"})

#: A depth past which the document is pathological rather than deep. It bounds
#: work without changing what a well-formed document produces.
MAX_DEPTH = 200


class _Segmenter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str, str]] = []  # kind, heading, text
        self._stack: list[str] = []
        self._buffer: list[str] = []
        self._current: str | None = None
        self._heading = ""
        self._skip_depth = 0
        self.failures: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if len(self._stack) > MAX_DEPTH:
            if "nesting depth exceeded" not in self.failures:
                self.failures.append("nesting depth exceeded")
            return
        self._stack.append(tag)
        if tag in BLOCK_TAGS:
            self._flush()
            self._current = tag

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag in BLOCK_TAGS and self._current == tag:
            self._flush()
        # Unclosed tags are ordinary in the wild; pop to the match if there is
        # one and otherwise leave the stack alone rather than unwinding it.
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data: str) -> None:
        if self._skip_depth or self._current is None:
            return
        self._buffer.append(data)

    def _flush(self) -> None:
        if self._current is None:
            return
        text = " ".join("".join(self._buffer).split())
        if text:
            if self._current in HEADING_TAGS:
                self._heading = text
                self.blocks.append((self._current, "", text))
            else:
                self.blocks.append((self._current, self._heading, text))
        self._buffer.clear()
        self._current = None

    def close(self) -> None:
        super().close()
        self._flush()


def parse_html(body: bytes, artifact_id: str) -> tuple[tuple[Segment, ...], tuple[str, ...]]:
    text = body.decode("utf-8", errors="replace")
    segmenter = _Segmenter()
    segmenter.feed(text)
    segmenter.close()

    segments: list[Segment] = []
    counters: dict[str, int] = {}
    for ordinal, (kind, heading, content) in enumerate(segmenter.blocks):
        counters[heading] = counters.get(heading, 0) + 1
        position = counters[heading]
        locator = f"{kind} {position}" if not heading else f"{heading} § {kind} {position}"
        segments.append(
            Segment(
                id=segment_id(artifact_id, ordinal, content),
                artifact_id=artifact_id,
                ordinal=ordinal,
                kind=kind,
                locator=locator,
                text=content,
            )
        )
    return tuple(segments), tuple(segmenter.failures)


register("text/html", NAME, VERSION, parse_html)
