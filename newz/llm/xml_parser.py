"""XML extraction helpers.

Ported with review from v1 (`ngbeing/llm/xml_parser.py`, S2 §16 allowlist) —
verbatim logic; only this provenance note changed. Models reply with text
that *contains* the XML structure we want. They may wrap it in markdown
fences, add prose around it, or rarely truncate. This module isolates
extraction + validation so the rest of the system works with already-parsed
elements.

We deliberately use stdlib xml.etree (not lxml) — it's available everywhere
and handles every case we care about for narrow schemas. When strict parsing
fails, one repair pass handles common LLM malformations (unescaped `&` in
element values — v1 soak saw this ~5×/3 days on names like `Procter &
Gamble`).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET


class XMLExtractionError(Exception):
    """Raised when XML cannot be extracted or parsed from model output."""


# Match the first top-level element by name. Allows attributes, whitespace,
# and self-closing form <foo/>.
def _build_pattern(root_tag: str) -> re.Pattern[str]:
    return re.compile(
        rf"<{root_tag}\b[^>]*/>|<{root_tag}\b[^>]*>.*?</{root_tag}>",
        re.DOTALL,
    )


# Match an `&` that is NOT part of a valid XML entity reference.
# Recognized entities: &amp; &lt; &gt; &quot; &apos; &#NNN; &#xHHHH;.
# Anything else is a stray `&` the model emitted as a literal — we rewrite
# it to `&amp;` so the strict parser accepts the value.
_STRAY_AMPERSAND = re.compile(
    r"&(?!(?:amp|lt|gt|quot|apos|#\d{1,7}|#x[0-9a-fA-F]{1,6});)"
)


def _repair_xml(xml_str: str) -> str:
    """Best-effort repair of common LLM XML malformations.

    Today: escape stray `&` characters that aren't part of an entity ref.
    The repair is conservative — we'd rather raise a parse error than
    silently mis-parse. Add new rules only when soak surfaces new failure
    modes that pattern-match cleanly.
    """
    return _STRAY_AMPERSAND.sub("&amp;", xml_str)


def extract_xml(text: str, root_tag: str) -> ET.Element:
    """Extract the first <root_tag>...</root_tag> from a model response.

    Strips markdown code fences if present, finds the XML block, parses it.
    If the strict parser fails, runs one repair pass and retries.
    Raises XMLExtractionError with a useful message on any failure.
    """
    if not text or not text.strip():
        raise XMLExtractionError("model returned empty response")

    # Strip surrounding markdown code fences if they wrap the entire response.
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Drop the opening fence (with optional language tag) and trailing fence.
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    pattern = _build_pattern(root_tag)
    match = pattern.search(cleaned)
    if match is None:
        snippet = cleaned[:200]
        raise XMLExtractionError(
            f"could not find <{root_tag}> in model output (first 200 chars): {snippet!r}"
        )

    xml_str = match.group(0)
    try:
        return ET.fromstring(xml_str)
    except ET.ParseError as orig_err:
        repaired = _repair_xml(xml_str)
        if repaired != xml_str:
            try:
                return ET.fromstring(repaired)
            except ET.ParseError:
                pass  # repair didn't help; fall through to the original error
        raise XMLExtractionError(
            f"XML parse error in <{root_tag}>: {orig_err}; raw: {xml_str[:200]!r}"
        ) from orig_err


def require_text(element: ET.Element, child: str) -> str:
    """Return the text of a required child element, stripped.

    Raises XMLExtractionError if the child is missing or empty.
    """
    found = element.find(child)
    if found is None:
        raise XMLExtractionError(
            f"missing required child <{child}> in <{element.tag}>"
        )
    if found.text is None:
        raise XMLExtractionError(
            f"required child <{child}> in <{element.tag}> is empty"
        )
    return found.text.strip()


def optional_text(element: ET.Element, child: str, default: str = "") -> str:
    """Return the text of an optional child element, or the default."""
    found = element.find(child)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def require_float(element: ET.Element, child: str) -> float:
    """Return the float value of a required child element."""
    raw = require_text(element, child)
    try:
        return float(raw)
    except ValueError as e:
        raise XMLExtractionError(
            f"<{child}> in <{element.tag}> is not a float: {raw!r}"
        ) from e


def require_float_in_range(
    element: ET.Element, child: str, lo: float, hi: float
) -> float:
    """Return the float value, clamped to the allowed range.

    Clamp rather than fail — small models occasionally produce slightly
    out-of-range values; clamping is more useful than refusing the whole call.
    """
    val = require_float(element, child)
    return max(lo, min(hi, val))
