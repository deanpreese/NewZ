"""Source catalog validation.

A source revision is the unit that carries capability. It names one endpoint,
one role, one declared scope, one risk floor and one retention policy, and it is
immutable — because an edge admitted last week was admitted under the terms that
held last week, and rewriting them would rewrite the admission silently.

Validation is deliberately strict and deliberately dumb. It checks that the
catalog says enough to be accountable; it makes no judgment about the source.
`TRUE_NORTH.md` forbids a global reliability score, and the way that boundary is
kept is by never having a field to put one in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newz.acquisition.urlpolicy import UrlPolicy, inspect_url
from newz.domain.enums import DeliveryKind, RetentionPolicy, RiskTier, SourceRole
from newz.domain.ids import is_valid


class CatalogError(ValueError):
    """A catalog entry that could not be accepted, with every reason at once."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True, slots=True)
class Publisher:
    id: str
    name: str
    #: Membership blocks independence; it never establishes it.
    independence_group: str | None = None


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    publisher_id: str
    name: str
    topic: str


@dataclass(frozen=True, slots=True)
class SourceRevision:
    id: str
    source_id: str
    revision: int
    endpoint_url: str
    delivery_kind: DeliveryKind
    role: SourceRole
    declared_scope: str
    risk_floor: RiskTier
    retention_policy: RetentionPolicy
    expected_mime: str

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "revision": self.revision,
            "endpoint_url": self.endpoint_url,
            "delivery_kind": self.delivery_kind,
            "role": self.role,
            "declared_scope": self.declared_scope,
            "risk_floor": self.risk_floor,
            "retention_policy": self.retention_policy,
            "expected_mime": self.expected_mime,
        }

    @property
    def may_retain_evidence(self) -> bool:
        """`SPEC.md` 6.8: where full retention is prohibited the material can
        remain a lead and cannot qualify as evidence."""
        return self.retention_policy is RetentionPolicy.FULL_TEXT


def validate_revision(revision: SourceRevision, policy: UrlPolicy | None = None) -> None:
    """Raise `CatalogError` listing everything wrong, rather than the first thing.

    An operator correcting a catalog entry should learn all of it at once; a
    validator that stops at the first problem trains people to fix by iteration.
    """
    problems: list[str] = []

    for field, value in (("id", revision.id), ("source_id", revision.source_id)):
        if not is_valid(value):
            problems.append(f"{field} is not a well-formed opaque identifier: {value!r}")

    if revision.revision < 1:
        problems.append("revision numbers start at 1")

    if not revision.declared_scope.strip():
        problems.append(
            "declared scope is required: it travels with every edge for audit and "
            "decides the single-record exception"
        )

    if not revision.expected_mime.strip():
        problems.append("expected MIME is required so a mislabeled response is visible as one")

    verdict = inspect_url(revision.endpoint_url, policy or UrlPolicy())
    if not verdict.allowed:
        problems.append(f"endpoint refused by URL policy: {verdict.refusal.value}")

    if revision.role is SourceRole.ADJUDICATOR and len(revision.declared_scope.strip()) < 12:
        problems.append(
            "an adjudicator's declared scope must say what it settles: it is the only "
            "place scope carries decision weight"
        )

    if problems:
        raise CatalogError(problems)
