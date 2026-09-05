"""Structured data: JSON and CSV.

A row and a JSON path are segments in the same sense a paragraph is — an
addressable unit a quotation can point at. The locator is the thing that makes
them useful: `row 3` and `$.entries[1].text` are both places a person can go
back to and check.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from newz.parse.registry import ParserFailure, Segment, register, segment_id

JSON_NAME = "json.stdlib"
CSV_NAME = "csv.stdlib"
VERSION = "1.0.0"

#: Structures deeper than this are refused rather than walked. Hostile input is
#: the assumption, and recursion depth is the cheapest way to make a parser fall
#: over.
MAX_DEPTH = 30


def _walk(node: Any, path: str, depth: int, out: list[tuple[str, str]]) -> None:
    if depth > MAX_DEPTH:
        raise ParserFailure(f"structure deeper than {MAX_DEPTH} at {path}")
    if isinstance(node, dict):
        for key in sorted(node):
            _walk(node[key], f"{path}.{key}", depth + 1, out)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk(item, f"{path}[{index}]", depth + 1, out)
    elif node is not None and not isinstance(node, bool):
        text = str(node).strip()
        if text:
            out.append((path, text))


def parse_json(body: bytes, artifact_id: str) -> tuple[tuple[Segment, ...], tuple[str, ...]]:
    try:
        document = json.loads(body.decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ParserFailure(f"unreadable JSON: {error}") from error

    leaves: list[tuple[str, str]] = []
    _walk(document, "$", 0, leaves)
    segments = tuple(
        Segment(
            id=segment_id(artifact_id, ordinal, text),
            artifact_id=artifact_id,
            ordinal=ordinal,
            kind="value",
            locator=path,
            text=text,
        )
        for ordinal, (path, text) in enumerate(leaves)
    )
    return segments, ()


def parse_csv(body: bytes, artifact_id: str) -> tuple[tuple[Segment, ...], tuple[str, ...]]:
    text = body.decode("utf-8", errors="replace")
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as error:
        raise ParserFailure(f"unreadable CSV: {error}") from error
    if not rows:
        return (), ()

    header = rows[0]
    segments: list[Segment] = []
    for ordinal, row in enumerate(rows[1:], start=1):
        # The header travels with every row, because a value without its column
        # name is a number nobody can quote responsibly.
        content = ", ".join(
            f"{name}={value}" for name, value in zip(header, row, strict=False) if value != ""
        )
        if not content:
            continue
        segments.append(
            Segment(
                id=segment_id(artifact_id, ordinal, content),
                artifact_id=artifact_id,
                ordinal=ordinal,
                kind="row",
                locator=f"row {ordinal}",
                text=content,
            )
        )
    return tuple(segments), ()


register("application/json", JSON_NAME, VERSION, parse_json)
register("text/csv", CSV_NAME, VERSION, parse_csv)
