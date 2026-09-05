"""Content that tries to instruct.

`SPEC.md` section 6 item 9. Retained material that issues directives, claims
authority, manufactures urgency, asserts an identity, or asks not to be surfaced
is recorded as an observation *about that source revision* — not merely refused
and forgotten, and never turned into a reliability score.

The distinction is load-bearing and easy to lose. These observations bear on
operational standing: parse reliability, availability, retention-terms
compliance, injection history. `TRUE_NORTH.md` forbids assigning global truth
scores to publishers, and a source that serves hostile markup may still be the
only surviving record of what it published.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from newz.domain.enums import InstructionMarker
from newz.store.db import Store

PATTERNS: tuple[tuple[InstructionMarker, re.Pattern[str]], ...] = (
    (
        InstructionMarker.DIRECTIVE,
        re.compile(
            r"(ignore (all )?(previous|prior|above) instructions"
            r"|disregard (the )?(above|previous)"
            r"|you are now in [a-z ]{3,30}mode"
            r"|treat the following as"
            r"|instruction to any automated reader"
            r"|(do not|don't) (surface|mention|record|log))",
            re.I,
        ),
    ),
    (
        InstructionMarker.AUTHORITY_CLAIM,
        re.compile(r"(authority:\s*root|system administrator|as the operator|admin(istrator)? override)", re.I),
    ),
    (
        InstructionMarker.IDENTITY_CLAIM,
        re.compile(r"(this (page|message) is authored by the [a-z ]{0,20}(system|operator))", re.I),
    ),
    (
        InstructionMarker.URGENCY,
        re.compile(r"(immediately|urgent(ly)?|without delay)\s+(publish|approve|admit|mark)", re.I),
    ),
    (
        InstructionMarker.SUPPRESSION_REQUEST,
        re.compile(r"(do not (surface|show|report) this|suppress this notice)", re.I),
    ),
)


@dataclass(frozen=True, slots=True)
class InstructionObservation:
    marker: InstructionMarker
    start: int
    end: int
    excerpt_hash: str

    def as_record(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "start": self.start,
            "end": self.end,
            "excerpt_hash": self.excerpt_hash,
        }


def scan(text: str) -> tuple[InstructionObservation, ...]:
    """Find instruction attempts, recording where and a hash of what.

    The excerpt is hashed rather than stored. The observation needs to be
    comparable across revisions — did this source do this again — and it does
    not need the payload retained a second time outside the artifact.
    """
    found: list[InstructionObservation] = []
    for marker, pattern in PATTERNS:
        for match in pattern.finditer(text):
            found.append(
                InstructionObservation(
                    marker=marker,
                    start=match.start(),
                    end=match.end(),
                    excerpt_hash=hashlib.sha256(match.group(0).lower().encode()).hexdigest(),
                )
            )
    return tuple(sorted(found, key=lambda o: (o.start, o.marker.value)))


def record(
    connection,
    *,
    source_revision_id: str,
    artifact_id: str,
    observations: tuple[InstructionObservation, ...],
    id_prefix: str,
) -> int:
    connection.executemany(
        "INSERT INTO instruction_observations (id, source_revision_id, artifact_id, marker, "
        "excerpt_hash, offset_start, offset_end, observed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
        [
            (
                f"{id_prefix}-{index}",
                source_revision_id,
                artifact_id,
                observation.marker.value,
                observation.excerpt_hash,
                observation.start,
                observation.end,
            )
            for index, observation in enumerate(observations)
        ],
    )
    return len(observations)


def operational_standing(store: Store, source_revision_id: str) -> dict[str, Any]:
    """What the record holds about how this source behaves as a source.

    Deliberately returns counts and no verdict. There is no field here for a
    reliability score, because the way that boundary is kept is by never having
    somewhere to put one.
    """
    rows = store.query(
        "SELECT marker, COUNT(*) AS n FROM instruction_observations "
        "WHERE source_revision_id = ? GROUP BY marker ORDER BY marker",
        source_revision_id,
    )
    attempts = store.one(
        "SELECT COUNT(*) AS n FROM attempts a JOIN operations o ON o.id = a.operation_id "
        "WHERE o.source_revision_id = ?",
        source_revision_id,
    )
    refusals = store.one(
        "SELECT COUNT(*) AS n FROM attempts a JOIN operations o ON o.id = a.operation_id "
        "WHERE o.source_revision_id = ? AND a.outcome = 'refused'",
        source_revision_id,
    )
    return {
        "source_revision_id": source_revision_id,
        "instruction_attempts": {row["marker"]: row["n"] for row in rows},
        "attempts": attempts["n"] if attempts else 0,
        "refused_attempts": refusals["n"] if refusals else 0,
    }
