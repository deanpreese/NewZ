"""Canonical serialization and content hashing.

One representation, sorted and compact, so that a hash means the same thing on
every host and in every process. ADR-0003 forbids anything here from depending
on dictionary insertion order, `hash()`, or the locale.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any


def canonical(value: Any) -> Any:
    """Reduce a value to JSON-safe primitives with every mapping key ordered."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): canonical(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (set, frozenset)):
        return sorted((canonical(v) for v in value), key=_sort_key)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [canonical(v) for v in value]
    if hasattr(value, "as_record"):
        return canonical(value.as_record())
    return value


def _sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def dumps(value: Any) -> str:
    """Canonical JSON: sorted keys, no incidental whitespace, UTF-8 text."""
    return json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    """The content hash of a value under its canonical form."""
    return hashlib.sha256(dumps(value).encode("utf-8")).hexdigest()
