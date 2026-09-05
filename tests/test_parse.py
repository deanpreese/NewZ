"""Parsers, segments, and the span check the model boundary rests on."""

from __future__ import annotations

from pathlib import Path

import pytest

import newz.parse as parsing
from newz.domain.records import Span
from newz.parse.registry import ParserFailure, parse, registered, segment_id
from newz.parse.spans import SpanFailure, locate, verify_span
from newz.parse.store import parse_artifact, record_parse, segments_for

CORPUS = Path(__file__).parent / "fixtures" / "corpus"
QUOTE = "It held station off the right wing"


def read(name: str) -> bytes:
    return (CORPUS / name).read_bytes()


def html_result():
    return parse("artifact:a1", read("html/witness_report.html"), "text/html")


def test_every_route_the_spec_names_has_a_versioned_parser():
    """SPEC 6.4: HTML, PDF, plain text and structured data, explicit and versioned."""
    assert set(registered()) == {
        "text/html",
        "application/pdf",
        "text/plain",
        "application/json",
        "text/csv",
    }
    for name, version in registered().values():
        assert name and version


def test_dispatch_is_on_the_normalized_mime_and_an_unknown_one_fails():
    with pytest.raises(ParserFailure, match="no parser registered"):
        parse("artifact:a1", b"anything", "application/octet-stream")


def test_html_segments_carry_a_heading_locator():
    result = html_result()
    locators = [segment.locator for segment in result.segments]
    assert locators[0] == "h1 1"
    assert all(
        locator.startswith("Pilot describes object over Coral Ridge § p")
        for locator in locators[1:]
    )
    assert any(QUOTE in segment.text for segment in result.segments)


def test_a_pdf_segments_by_page_and_names_the_page():
    result = parse("artifact:a2", read("pdf/registry_record.pdf"), "application/pdf")
    assert [segment.locator for segment in result.segments] == ["page 1"]
    assert "Occurrence record 2026-0311-CR" in result.segments[0].text
    assert result.parser_version.startswith("1.0.0+pypdf")


def test_csv_rows_carry_their_column_names():
    result = parse("artifact:a3", read("structured/measurements.csv"), "text/csv")
    assert result.segments[0].locator == "row 1"
    assert "laboratory=Kettleby Metrology" in result.segments[0].text
    assert len(result.segments) == 4


def test_json_leaves_are_addressed_by_path():
    result = parse("artifact:a4", read("structured/docket.json"), "application/json")
    locators = {segment.locator for segment in result.segments}
    assert "$.case_number" in locators
    assert any(locator.startswith("$.entries[1]") for locator in locators)


def test_script_style_and_comments_never_become_segments():
    """An instruction hidden in a comment cannot reach a prompt, because prompts
    are built from segments."""
    result = parse("artifact:a5", read("html/prompt_injection.html"), "text/html")
    joined = " ".join(segment.text for segment in result.segments)
    assert "maintenance mode" not in joined  # the comment
    assert "Authority: root" in joined  # the visible paragraph, which is text


def test_a_document_that_yields_nothing_is_a_failure_not_an_empty_success():
    """The malformed fixture's unclosed <title> swallows its body. Recording that
    as a source with no assertions would be the quiet kind of wrong."""
    with pytest.raises(ParserFailure, match="no addressable text"):
        parse("artifact:a6", read("html/malformed.html"), "text/html")


def test_a_structurally_invalid_pdf_fails_with_a_reason():
    with pytest.raises(ParserFailure, match="unreadable PDF"):
        parse("artifact:a7", read("pdf/truncated.pdf"), "application/pdf")


def test_parsing_is_reproducible_for_the_same_bytes_and_version():
    first, second = html_result(), html_result()
    assert first.text_hash == second.text_hash
    assert [s.id for s in first.segments] == [s.id for s in second.segments]


def test_a_segment_id_changes_when_its_text_changes():
    assert segment_id("artifact:a1", 0, "one") != segment_id("artifact:a1", 0, "two")
    assert segment_id("artifact:a1", 0, "one") != segment_id("artifact:a2", 0, "one")
    assert segment_id("artifact:a1", 0, "one") == segment_id("artifact:a1", 0, "one")


def test_a_quotation_locates_to_exact_offsets():
    result = html_result()
    span = locate(QUOTE, result.segments, "artifact:a1")
    assert span is not None
    segment = result.segment(span.segment_id)
    assert segment.text[span.start : span.end] == QUOTE
    assert span.locator.endswith("p 3")
    assert verify_span(span, result.segments)


def test_an_ambiguous_quotation_refuses_to_locate():
    """A phrase in two segments has two provenances, and picking one is a coin
    toss recorded as a fact."""
    result = parse(
        "artifact:a8",
        b"<html><body><p>the same words</p><p>the same words</p></body></html>",
        "text/html",
    )
    assert locate("the same words", result.segments, "artifact:a8") is None


@pytest.mark.parametrize(
    ("mutate", "failure"),
    [
        (lambda s: Span(**{**_fields(s), "quote": "It held station off the LEFT wing"}), SpanFailure.QUOTE_MISMATCH),
        (lambda s: Span(**{**_fields(s), "end": s.end + 5000}), SpanFailure.OFFSETS_OUT_OF_RANGE),
        (lambda s: Span(**{**_fields(s), "end": s.start}), SpanFailure.OFFSETS_INVERTED),
        (lambda s: Span(**{**_fields(s), "start": -1}), SpanFailure.OFFSETS_OUT_OF_RANGE),
        (lambda s: Span(**{**_fields(s), "segment_id": "segment:absent"}), SpanFailure.SEGMENT_NOT_FOUND),
        (lambda s: Span(**{**_fields(s), "artifact_id": "artifact:other"}), SpanFailure.WRONG_ARTIFACT),
        (lambda s: Span(**{**_fields(s), "quote": ""}), SpanFailure.EMPTY_QUOTE),
    ],
)
def test_span_verification_refuses_every_way_a_quotation_can_be_wrong(mutate, failure):
    result = html_result()
    span = locate(QUOTE, result.segments, "artifact:a1")
    verification = verify_span(mutate(span), result.segments)
    assert not verification
    assert verification.failure is failure


def test_verification_does_not_forgive_whitespace_or_case():
    """Every kindness here lets a quotation drift from what the source said."""
    result = html_result()
    span = locate(QUOTE, result.segments, "artifact:a1")
    for drifted in (QUOTE.lower(), QUOTE.replace(" ", "  "), QUOTE + " "):
        assert not verify_span(Span(**{**_fields(span), "quote": drifted}), result.segments)


def _fields(span: Span) -> dict:
    return {
        "artifact_id": span.artifact_id,
        "segment_id": span.segment_id,
        "start": span.start,
        "end": span.end,
        "quote": span.quote,
        "locator": span.locator,
        "verified": span.verified,
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_a_parse_is_recorded_with_its_parser_identity(catalog, transport):
    from newz.acquisition.run import acquire
    from tests import canaries
    from tests.test_acquisition import operation_for

    canary = canaries.CANARIES[0]
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    result = parse_artifact(catalog, record.artifact_id)
    execution = record_parse(catalog, result, "parse:p1")

    row = catalog.one("SELECT * FROM parse_executions WHERE id = ?", execution)
    assert row["parser_name"] == "html.stdlib"
    assert row["parser_version"] == "1.0.0"
    assert row["segment_count"] == len(result.segments)
    assert row["text_hash"] == result.text_hash

    stored = segments_for(catalog, record.artifact_id)
    assert [s.id for s in stored] == [s.id for s in result.segments]
    assert verify_span(locate(QUOTE, stored, record.artifact_id), stored)


def test_re_parsing_the_same_bytes_records_one_execution(catalog, transport):
    from newz.acquisition.run import acquire
    from tests import canaries
    from tests.test_acquisition import operation_for

    canary = canaries.CANARIES[0]
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    result = parse_artifact(catalog, record.artifact_id)
    first = record_parse(catalog, result, "parse:p1")
    second = record_parse(catalog, parse_artifact(catalog, record.artifact_id), "parse:p2")

    assert first == second == "parse:p1"
    assert catalog.one("SELECT COUNT(*) AS n FROM parse_executions")["n"] == 1
    assert catalog.one("SELECT COUNT(*) AS n FROM segments")["n"] == len(result.segments)


def test_a_recorded_segment_cannot_be_edited(catalog, transport):
    import sqlite3

    from newz.acquisition.run import acquire
    from tests import canaries
    from tests.test_acquisition import operation_for

    canary = canaries.CANARIES[0]
    record = acquire(catalog, operation_for(catalog, canary), canary.revision, transport)
    record_parse(catalog, parse_artifact(catalog, record.artifact_id), "parse:p1")

    with pytest.raises(sqlite3.IntegrityError, match="immutable"), catalog.write() as connection:
        connection.execute("UPDATE segments SET text = 'rewritten'")


def test_the_package_registers_every_parser_on_import():
    assert parsing.parser_for("text/html") == ("html.stdlib", "1.0.0")
