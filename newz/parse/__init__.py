"""Bytes to addressable segments, and nothing further.

A parser produces text a span can point at. It grants no capability, resolves no
basis, and reaches no assessment: that path runs through span verification and
the capability matrix, neither of which asks which parser ran.
"""

# Importing the package registers every parser: dispatch is by normalized MIME,
# and a registry that is populated by whoever happened to import a module first
# is a registry with a different shape in every process.
from newz.parse import html, pdf, structured, text  # noqa: F401
from newz.parse.registry import (
    ParseResult,
    ParserFailure,
    Segment,
    parse,
    parser_for,
    registered,
)
from newz.parse.spans import SpanFailure, SpanVerification, locate, verify_span

__all__ = [
    "ParseResult",
    "ParserFailure",
    "Segment",
    "SpanFailure",
    "SpanVerification",
    "locate",
    "parse",
    "parser_for",
    "registered",
    "verify_span",
]
