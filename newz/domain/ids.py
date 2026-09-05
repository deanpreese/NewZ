"""Opaque stable identifiers.

`SPEC.md` section 11 requires identifiers to be stable and opaque. Opaque means
nothing downstream may parse meaning out of one: an id that encodes a publisher
or a risk tier becomes a second, unversioned copy of the record.
"""

from __future__ import annotations

import re

_ID = re.compile(r"^[a-z][a-z0-9_]*:[A-Za-z0-9_-]{1,64}$")


def validate(identifier: str) -> str:
    """Return the identifier, or raise if it is not a well-formed opaque id."""
    if not _ID.match(identifier):
        raise ValueError(f"malformed identifier: {identifier!r}")
    return identifier


def is_valid(identifier: str) -> bool:
    return bool(_ID.match(identifier))
