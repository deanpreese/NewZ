"""Recording a parse, and reading its segments back.

A parse execution is idempotent per artifact and parser version: running the
same parser over the same bytes twice records one execution and one set of
segments, because the segmentation is a function of the two.
"""

from __future__ import annotations

import json
from pathlib import Path

from newz.parse.registry import ParseResult, Segment, parse
from newz.store.db import Store


def artifact_body(store: Store, artifact_id: str) -> bytes:
    row = store.one("SELECT stored_path FROM artifacts WHERE id = ?", artifact_id)
    if row is None:
        raise KeyError(artifact_id)
    return Path(store.artifact_root / row["stored_path"]).read_bytes()


def parse_artifact(store: Store, artifact_id: str) -> ParseResult:
    """Parse a retained artifact using the MIME its response recorded."""
    row = store.one(
        "SELECT a.media_type FROM artifacts a WHERE a.id = ?", artifact_id
    )
    if row is None:
        raise KeyError(artifact_id)
    return parse(artifact_id, artifact_body(store, artifact_id), row["media_type"])


def record_parse(store: Store, result: ParseResult, execution_id: str) -> str:
    """Write the execution and its segments. Returns the execution id in force."""
    existing = store.one(
        "SELECT id FROM parse_executions WHERE artifact_id = ? AND parser_name = ? "
        "AND parser_version = ?",
        result.artifact_id,
        result.parser_name,
        result.parser_version,
    )
    if existing is not None:
        return existing["id"]

    with store.write() as connection:
        connection.execute(
            "INSERT INTO parse_executions (id, artifact_id, parser_name, parser_version, "
            "normalized_mime, text_hash, segment_count, failures_json, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                execution_id,
                result.artifact_id,
                result.parser_name,
                result.parser_version,
                result.normalized_mime,
                result.text_hash,
                len(result.segments),
                json.dumps(list(result.failures)),
            ),
        )
        connection.executemany(
            "INSERT OR IGNORE INTO segments (id, artifact_id, ordinal, kind, locator, text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    segment.id,
                    segment.artifact_id,
                    segment.ordinal,
                    segment.kind,
                    segment.locator,
                    segment.text,
                )
                for segment in result.segments
            ],
        )
    return execution_id


def segments_for(store: Store, artifact_id: str) -> tuple[Segment, ...]:
    return tuple(
        Segment(
            id=row["id"],
            artifact_id=row["artifact_id"],
            ordinal=row["ordinal"],
            kind=row["kind"],
            locator=row["locator"],
            text=row["text"],
        )
        for row in store.query(
            "SELECT * FROM segments WHERE artifact_id = ? ORDER BY ordinal", artifact_id
        )
    )
