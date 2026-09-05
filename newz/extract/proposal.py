"""The proposal shape, and everything it cannot say.

This is the model boundary written as a data structure. A proposed assertion
carries a kind, a quotation, and a summary. It carries **no role, no risk, no
basis, no relation, and no independence** — not because those are validated away
but because the shape has nowhere to put them. A model that asks to be treated
as a verified primary record is proposing a field that does not exist, and the
request lands nowhere rather than being caught.

What is validated is what the model *can* say: that the kind is one of the seven
`SPEC.md` names, that the claim kind is one of the nine, and — the load-bearing
one — that every quotation appears byte-exact in a retained segment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree

from newz.domain.enums import AssertionKind, ClaimKind
from newz.domain.records import Span
from newz.parse.registry import Segment
from newz.parse.spans import locate

MAX_ASSERTIONS = 40
MAX_CLAIMS = 20
MAX_ENTITY_NAME = 200
MAX_SUMMARY = 600
MAX_PROPOSAL_BYTES = 256 * 1024


@dataclass(frozen=True, slots=True)
class ProposedAssertion:
    kind: str
    quote: str
    summary: str = ""
    entities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProposedClaim:
    kind: str
    wording: str
    quote: str = ""


@dataclass(frozen=True, slots=True)
class Proposal:
    assertions: tuple[ProposedAssertion, ...] = ()
    claims: tuple[ProposedClaim, ...] = ()
    #: Whatever the model said that the shape has no place for. Kept so the
    #: operator can read what was ignored, and never acted on.
    ignored: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Refusal:
    what: str
    reason: str
    detail: str = ""

    def as_record(self) -> dict[str, Any]:
        return {"what": self.what, "reason": self.reason, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class AcceptedAssertion:
    kind: AssertionKind
    span: Span
    summary: str
    entities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcceptedClaim:
    kind: ClaimKind
    wording: str
    span: Span | None


@dataclass(frozen=True, slots=True)
class ValidatedExtraction:
    assertions: tuple[AcceptedAssertion, ...] = ()
    claims: tuple[AcceptedClaim, ...] = ()
    refusals: tuple[Refusal, ...] = field(default_factory=tuple)

    @property
    def accepted(self) -> int:
        return len(self.assertions) + len(self.claims)


class ProposalUnreadable(Exception):
    """The proposal was not parseable. A failure, never a partial acceptance."""


#: Fields a model might try to set that carry capability. They are refused
#: loudly rather than ignored quietly, because an attempt to set one is worth
#: seeing: it is the shape of an escalation under `SPEC.md` section 8.
CAPABILITY_FIELDS = frozenset(
    {"role", "risk", "basis", "relation", "independence", "scope", "clearance", "policy"}
)

_TAG = re.compile(r"</?([a-zA-Z_][\w-]*)")


def parse_proposal(text: str) -> Proposal:
    """Read the XML the model returned, and nothing else in the response.

    Small models wrap their answer in prose, fences, or an apology. The
    extraction element is located rather than assumed, and anything outside it
    is discarded — not because prose is dangerous here but because accepting it
    would mean the parser had an opinion about what the model meant.
    """
    # A document type declaration is refused on the whole response, before the
    # extraction element is located. Slicing to `<extraction>` would drop a DTD
    # anyway — a DTD must precede the root — but relying on that means the
    # defence is a side effect of where the slice starts rather than a decision.
    # The model has no legitimate use for a DTD, so the answer is that there is
    # never one.
    lowered = text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise ProposalUnreadable("a document type declaration is not part of a proposal")

    start = text.find("<extraction")
    end = text.rfind("</extraction>")
    if start == -1 or end == -1:
        raise ProposalUnreadable("no <extraction> element in the response")

    fragment = text[start : end + len("</extraction>")]
    if len(fragment) > MAX_PROPOSAL_BYTES:
        raise ProposalUnreadable(f"proposal larger than {MAX_PROPOSAL_BYTES} bytes")
    try:
        root = ElementTree.fromstring(fragment)
    except ElementTree.ParseError as error:
        raise ProposalUnreadable(f"malformed XML: {error}") from error

    assertions: list[ProposedAssertion] = []
    claims: list[ProposedClaim] = []
    ignored: list[str] = []

    for element in root:
        if element.tag == "assertion" and len(assertions) < MAX_ASSERTIONS:
            assertions.append(
                ProposedAssertion(
                    kind=_text(element, "kind"),
                    quote=_text(element, "quote", strip=False),
                    summary=_text(element, "summary")[:MAX_SUMMARY],
                    entities=tuple(
                        (entity.text or "").strip()[:MAX_ENTITY_NAME]
                        for entity in element.iter("entity")
                        if (entity.text or "").strip()
                    ),
                )
            )
        elif element.tag == "claim" and len(claims) < MAX_CLAIMS:
            claims.append(
                ProposedClaim(
                    kind=_text(element, "kind"),
                    wording=_text(element, "wording")[:MAX_SUMMARY],
                    quote=_text(element, "quote", strip=False),
                )
            )
        else:
            ignored.append(element.tag)

    for element in root.iter():
        if element.tag in CAPABILITY_FIELDS:
            ignored.append(element.tag)

    return Proposal(
        assertions=tuple(assertions),
        claims=tuple(claims),
        ignored=tuple(sorted(set(ignored))),
    )


def _text(element: ElementTree.Element, tag: str, strip: bool = True) -> str:
    found = element.find(tag)
    if found is None or found.text is None:
        return ""
    return found.text.strip() if strip else found.text.strip("\n")


def validate(
    proposal: Proposal, segments: tuple[Segment, ...], artifact_id: str
) -> ValidatedExtraction:
    """Keep what survives, and say why the rest did not."""
    accepted_assertions: list[AcceptedAssertion] = []
    accepted_claims: list[AcceptedClaim] = []
    refusals: list[Refusal] = []

    for field_name in sorted(set(proposal.ignored) & CAPABILITY_FIELDS):
        # An attempt to set capability is recorded rather than shrugged off: it
        # is what an escalation attempt looks like from here.
        refusals.append(
            Refusal("proposal", "capability_field_proposed", field_name)
        )

    for proposed in proposal.assertions:
        try:
            kind = AssertionKind(proposed.kind)
        except ValueError:
            refusals.append(Refusal("assertion", "unknown_assertion_kind", proposed.kind))
            continue
        if not proposed.quote:
            refusals.append(Refusal("assertion", "assertion_without_quote", proposed.summary[:80]))
            continue
        span = locate(proposed.quote, segments, artifact_id)
        if span is None:
            # The containment. A quotation that is not in a retained segment, or
            # is in two of them, does not become an assertion.
            refusals.append(Refusal("assertion", "unverified_quote", proposed.quote[:120]))
            continue
        accepted_assertions.append(
            AcceptedAssertion(
                kind=kind,
                span=span,
                summary=proposed.summary,
                entities=proposed.entities,
            )
        )

    for proposed in proposal.claims:
        try:
            kind = ClaimKind(proposed.kind)
        except ValueError:
            refusals.append(Refusal("claim", "unknown_claim_kind", proposed.kind))
            continue
        if not proposed.wording.strip():
            refusals.append(Refusal("claim", "claim_without_wording", proposed.kind))
            continue
        span = locate(proposed.quote, segments, artifact_id) if proposed.quote else None
        if proposed.quote and span is None:
            refusals.append(Refusal("claim", "unverified_quote", proposed.quote[:120]))
            continue
        accepted_claims.append(AcceptedClaim(kind=kind, wording=proposed.wording, span=span))

    return ValidatedExtraction(
        assertions=tuple(accepted_assertions),
        claims=tuple(accepted_claims),
        refusals=tuple(refusals),
    )
