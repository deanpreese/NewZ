"""PDF text extraction, one page per segment.

The one place the package takes a third-party dependency (ADR-0004). The page is
the segment because it is the unit a person can find again: "page 3" is a
locator someone can act on, and a paragraph index into extracted PDF text is
not.
"""

from __future__ import annotations

import io

from newz.parse.registry import ParserFailure, Segment, register, segment_id

NAME = "pdf.pypdf"


def _version() -> str:
    import pypdf

    return f"1.0.0+pypdf{pypdf.__version__}"


def parse_pdf(body: bytes, artifact_id: str) -> tuple[tuple[Segment, ...], tuple[str, ...]]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(body), strict=False)
    except (PdfReadError, ValueError, OSError) as error:
        raise ParserFailure(f"unreadable PDF: {type(error).__name__}: {error}") from error

    segments: list[Segment] = []
    failures: list[str] = []
    for ordinal, page in enumerate(reader.pages):
        try:
            extracted = page.extract_text() or ""
        except Exception as error:  # one bad page is not a bad document
            failures.append(f"page {ordinal + 1}: {type(error).__name__}")
            continue
        content = " ".join(extracted.split())
        if not content:
            failures.append(f"page {ordinal + 1}: no extractable text")
            continue
        segments.append(
            Segment(
                id=segment_id(artifact_id, ordinal, content),
                artifact_id=artifact_id,
                ordinal=ordinal,
                kind="page",
                locator=f"page {ordinal + 1}",
                text=content,
            )
        )

    if not segments:
        raise ParserFailure("no extractable text in any page")
    return tuple(segments), tuple(failures)


register("application/pdf", NAME, _version(), parse_pdf)
