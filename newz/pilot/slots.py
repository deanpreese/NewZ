"""Automating the pilot slate, and the one part of it that stays the operator's.

Assembling twenty reviewed sources by hand is mostly mechanical: fetch each
candidate, see what it actually serves, work out whether full text is available,
collect the retention signals it publishes about itself, and then solve a small
constraint problem — five buckets, eight topics, at most two per publisher.
All of that is done here.

Two things are not, and they are different in kind.

**Enabling a source is a diet decision.** `SPEC.md` keeps the diet under the
operator's control and `epochs.activate` already demands an actor and a dry run.
So this module proposes a slate and cannot activate one; the last step is a
command a person runs having read what it would do.

**Role and retention are ratified, not derived.** A role grants capability, and
`SPEC.md` section 2.3 forbids a model from granting one — so the role proposed
here comes from deterministic evidence rather than a model, and it is a
proposal. Retention is a claim about somebody else's rights: what is automated
is gathering the signals a source publishes about itself, and what is not is
concluding from them that retention is permitted.

The survey itself runs through the ordinary spine. A candidate is enabled in a
**survey epoch** with `LEAD_ONLY` retention, so probing consumes a reservation,
obeys the fetcher's limits, and cannot retain anything as evidence — the
chicken-and-egg of "fetch it to review it" is answered by making the fetch a
lead rather than by exempting it from the scheduler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from newz.acquisition.fetcher import FetchPolicy, fetch
from newz.acquisition.transport import Transport
from newz.acquisition.urlpolicy import inspect_url
from newz.domain.enums import DeliveryKind, RetentionPolicy, RiskTier, SourceRole
from newz.parse.registry import ParserFailure, parse
from newz.pilot.catalog_review import (
    REQUIRED_SLOTS,
    REQUIRED_TOPICS,
    SLOT_ROLES,
    CatalogReview,
    ProposedSlot,
    review,
)
from newz.store.db import Store

#: Markers a source publishes about its own terms. Signals, never conclusions:
#: what they establish is what the source says, and whether that permits
#: retention is a judgment with legal weight that belongs to a person.
RETENTION_MARKERS: tuple[tuple[str, str], ...] = (
    ("creativecommons.org/licenses", "a Creative Commons licence is linked"),
    ("creativecommons.org/publicdomain", "a public-domain dedication is linked"),
    ('rel="license"', "the document declares a licence relation"),
    ("all rights reserved", "the document asserts all rights reserved"),
    ("terms of use", "the document links terms of use"),
    ("terms of service", "the document links terms of service"),
    ("noarchive", "the document asks not to be archived"),
    ("public domain", "the document describes itself as public domain"),
)

#: Deterministic role evidence. Each rule says what it saw and what that
#: suggests; none of them decides anything. Ordered by how much the observation
#: constrains the answer.
ROLE_RULES: tuple[tuple[str, SourceRole, str], ...] = (
    ("docket", SourceRole.ADJUDICATOR, "the endpoint is a docket or case index"),
    ("judgment", SourceRole.ADJUDICATOR, "the body speaks of judgments or findings"),
    ("tribunal", SourceRole.ADJUDICATOR, "the body names a tribunal"),
    ("registry", SourceRole.PRIMARY_RECORD, "the endpoint is a registry"),
    ("occurrence record", SourceRole.PRIMARY_RECORD, "the body carries occurrence records"),
    ("patent", SourceRole.PRIMARY_RECORD, "the body is a patent record"),
    ("filing", SourceRole.PRIMARY_RECORD, "the body carries filings"),
    ("doi:", SourceRole.EMPIRICAL_STUDY, "the body cites DOIs"),
    ("preprint", SourceRole.EMPIRICAL_STUDY, "the body is preprint material"),
    ("replication", SourceRole.EMPIRICAL_STUDY, "the body reports replication"),
    ("methods", SourceRole.EMPIRICAL_STUDY, "the body reports methods"),
    ("debunk", SourceRole.SKEPTICAL_INVESTIGATION, "the body is framed as debunking"),
    ("skeptic", SourceRole.SKEPTICAL_INVESTIGATION, "the body describes itself as skeptical"),
    ("forensic", SourceRole.SKEPTICAL_INVESTIGATION, "the body reports forensic analysis"),
    ("i saw", SourceRole.FIRSTHAND_WITNESS, "the body is written in the first person"),
    ("i witnessed", SourceRole.FIRSTHAND_WITNESS, "the body is written in the first person"),
    ("encyclopedia", SourceRole.GENERAL_CONTEXT, "the endpoint is reference material"),
    ("archive", SourceRole.HISTORICAL_CONTEXT, "the endpoint is an archive"),
)

#: What the parsers can turn into addressable segments. A source serving
#: anything else cannot yield evidence, whatever its terms permit.
EVIDENCE_CAPABLE_MIMES = frozenset(
    {"text/html", "application/pdf", "text/plain", "application/json", "text/csv"}
)

#: Below this, a page parsed but had almost nothing in it — a landing page or a
#: paywall stub rather than a document.
MIN_SEGMENTS_FOR_FULL_TEXT = 3


@dataclass(frozen=True, slots=True)
class Candidate:
    id: str
    url: str
    publisher: str
    topic: str
    note: str = ""
    independence_group: str | None = None


@dataclass(frozen=True, slots=True)
class Probe:
    candidate_id: str
    reachable: bool
    observed_mime: str = ""
    byte_size: int = 0
    full_text_capable: bool = False
    segment_count: int = 0
    delivery_kind: str = ""
    retention_signals: tuple[str, ...] = ()
    role_evidence: tuple[str, ...] = ()
    proposed_role: SourceRole | None = None
    refusal: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "reachable": self.reachable,
            "observed_mime": self.observed_mime,
            "byte_size": self.byte_size,
            "full_text_capable": self.full_text_capable,
            "segment_count": self.segment_count,
            "delivery_kind": self.delivery_kind,
            "retention_signals": list(self.retention_signals),
            "role_evidence": list(self.role_evidence),
            "proposed_role": self.proposed_role.value if self.proposed_role else "",
            "refusal": self.refusal,
        }


def add_candidates(store: Store, candidates: list[Candidate], added_by: str) -> int:
    """Record candidates. Cheap by design: a URL, a publisher, a topic guess.

    A URL the fetcher would refuse is refused here, so a slate is never built
    around a place the system can never go.
    """
    added = 0
    with store.write() as connection:
        for candidate in candidates:
            if not inspect_url(candidate.url, FetchPolicy().url).allowed:
                continue
            cursor = connection.execute(
                "INSERT OR IGNORE INTO slot_candidates (id, url, publisher, topic, note, "
                "independence_group, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, "
                "datetime('now'))",
                (
                    candidate.id,
                    candidate.url,
                    candidate.publisher,
                    candidate.topic,
                    candidate.note,
                    candidate.independence_group,
                    added_by,
                ),
            )
            added += cursor.rowcount
    return added


def candidates(store: Store) -> tuple[Candidate, ...]:
    return tuple(
        Candidate(
            id=row["id"],
            url=row["url"],
            publisher=row["publisher"],
            topic=row["topic"],
            note=row["note"],
            independence_group=row["independence_group"],
        )
        for row in store.query("SELECT * FROM slot_candidates ORDER BY id")
    )


def _retention_signals(body: bytes) -> tuple[str, ...]:
    text = body.decode("utf-8", errors="replace").lower()
    return tuple(
        description for marker, description in RETENTION_MARKERS if marker in text
    )


def _role_evidence(url: str, body: bytes) -> tuple[tuple[str, ...], SourceRole | None]:
    """Deterministic role evidence. No model, and no decision.

    Returns everything it saw and the role the most observations point at. A tie
    proposes nothing: an even split is exactly the case a person should look at.
    """
    haystack = (url + "\n" + body.decode("utf-8", errors="replace")[:20_000]).lower()
    seen: list[str] = []
    votes: dict[SourceRole, int] = {}
    for marker, role, description in ROLE_RULES:
        if marker in haystack:
            seen.append(f"{description} ({marker!r})")
            votes[role] = votes.get(role, 0) + 1
    if not votes:
        return tuple(seen), None
    ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0].value))
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        seen.append("the evidence is evenly split; no role proposed")
        return tuple(seen), None
    return tuple(seen), ranked[0][0]


def survey_candidate(
    store: Store, candidate: Candidate, transport: Transport, policy: FetchPolicy | None = None
) -> Probe:
    """Fetch a candidate and record what it actually serves.

    This is a read like any other: the fetcher's scheme, address, size, timeout,
    decompression and MIME rules all apply, and a candidate that trips one of
    them is recorded as refused rather than retried by another route.
    """
    result = fetch(candidate.url, transport, policy)
    if not result.retained:
        probe = Probe(
            candidate_id=candidate.id,
            reachable=False,
            refusal=(result.refusal.value if result.refusal else result.detail) or "unreachable",
        )
        return _record_probe(store, probe)

    segments = 0
    try:
        parsed = parse(f"survey:{candidate.id}", result.body, result.normalized_mime)
        segments = len(parsed.segments)
    except ParserFailure as error:
        probe = Probe(
            candidate_id=candidate.id,
            reachable=True,
            observed_mime=result.normalized_mime,
            byte_size=len(result.body),
            refusal=f"parsed nothing: {error}",
        )
        return _record_probe(store, probe)

    evidence, role = _role_evidence(candidate.url, result.body)
    delivery = (
        DeliveryKind.DOCUMENT
        if result.normalized_mime == "application/pdf"
        else DeliveryKind.DATASET
        if result.normalized_mime in ("application/json", "text/csv")
        else DeliveryKind.FEED
        if result.normalized_mime == "application/xml"
        else DeliveryKind.PAGE
    )
    probe = Probe(
        candidate_id=candidate.id,
        reachable=True,
        observed_mime=result.normalized_mime,
        byte_size=len(result.body),
        full_text_capable=(
            result.normalized_mime in EVIDENCE_CAPABLE_MIMES
            and segments >= MIN_SEGMENTS_FOR_FULL_TEXT
        ),
        segment_count=segments,
        delivery_kind=delivery.value,
        retention_signals=_retention_signals(result.body),
        role_evidence=evidence,
        proposed_role=role,
    )
    return _record_probe(store, probe)


def _record_probe(store: Store, probe: Probe) -> Probe:
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO slot_probes (candidate_id, reachable, observed_mime, "
            "byte_size, full_text_capable, segment_count, delivery_kind, "
            "retention_signals_json, role_evidence_json, proposed_role, refusal, surveyed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                probe.candidate_id,
                int(probe.reachable),
                probe.observed_mime,
                probe.byte_size,
                int(probe.full_text_capable),
                probe.segment_count,
                probe.delivery_kind,
                json.dumps(list(probe.retention_signals)),
                json.dumps(list(probe.role_evidence)),
                probe.proposed_role.value if probe.proposed_role else "",
                probe.refusal,
                ),
        )
    return probe


def survey(store: Store, transport: Transport, policy: FetchPolicy | None = None) -> tuple[Probe, ...]:
    """Survey every candidate that has not been surveyed."""
    done = {row["candidate_id"] for row in store.query("SELECT candidate_id FROM slot_probes")}
    return tuple(
        survey_candidate(store, candidate, transport, policy)
        for candidate in candidates(store)
        if candidate.id not in done
    )


def probes(store: Store) -> dict[str, Probe]:
    out: dict[str, Probe] = {}
    for row in store.query("SELECT * FROM slot_probes ORDER BY candidate_id"):
        out[row["candidate_id"]] = Probe(
            candidate_id=row["candidate_id"],
            reachable=bool(row["reachable"]),
            observed_mime=row["observed_mime"],
            byte_size=row["byte_size"],
            full_text_capable=bool(row["full_text_capable"]),
            segment_count=row["segment_count"],
            delivery_kind=row["delivery_kind"],
            retention_signals=tuple(json.loads(row["retention_signals_json"])),
            role_evidence=tuple(json.loads(row["role_evidence_json"])),
            proposed_role=SourceRole(row["proposed_role"]) if row["proposed_role"] else None,
            refusal=row["refusal"],
        )
    return out


# ---------------------------------------------------------------------------
# Solving the slate
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Slate:
    id: str
    slots: tuple[ProposedSlot, ...]
    review: CatalogReview
    unplaced: tuple[str, ...] = field(default_factory=tuple)
    shortfall: dict[str, int] = field(default_factory=dict)

    @property
    def acceptable(self) -> bool:
        return self.review.acceptable

    def as_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slots": [slot.source_id for slot in self.slots],
            "review": self.review.as_record(),
            "unplaced": list(self.unplaced),
            "shortfall": dict(sorted(self.shortfall.items())),
        }


def _to_slot(candidate: Candidate, probe: Probe) -> ProposedSlot | None:
    if probe.proposed_role is None or not probe.reachable:
        return None
    return ProposedSlot(
        source_id=candidate.id,
        publisher=candidate.publisher,
        topic=candidate.topic,
        role=probe.proposed_role,
        declared_scope=candidate.note or f"material published at {candidate.url}",
        risk_floor=RiskTier.R1,
        retention_policy=(
            RetentionPolicy.FULL_TEXT if probe.full_text_capable else RetentionPolicy.LEAD_ONLY
        ),
        observed_mime=probe.observed_mime,
        full_text_capable=probe.full_text_capable,
        # Deliberately the signals, not a conclusion. `review` will refuse a
        # slate whose slots cannot say their terms, which is the point: the
        # operator fills this in, and the survey tells them what to read.
        retention_rights="; ".join(probe.retention_signals),
        independence_group=candidate.independence_group,
        counterpart_behaviour=(
            "a counterpart task within 72 hours"
            if probe.proposed_role in SLOT_ROLES["claimant_or_firsthand"]
            else ""
        ),
    )


def solve(store: Store, slate_id: str = "slate:proposed") -> Slate:
    """Choose twenty from the surveyed candidates, satisfying every constraint.

    Backtracking over the five buckets. The search is exact rather than greedy
    because the constraints interact — a publisher cap spent early can make a
    topic uncoverable later — and twenty slots from a few dozen candidates is
    small enough that guessing is not worth the ambiguity.
    """
    surveyed = probes(store)
    pool: list[ProposedSlot] = []
    unplaced: list[str] = []
    for candidate in candidates(store):
        probe = surveyed.get(candidate.id)
        slot = _to_slot(candidate, probe) if probe else None
        if slot is None:
            unplaced.append(candidate.id)
        else:
            pool.append(slot)

    by_kind: dict[str, list[ProposedSlot]] = {kind: [] for kind in REQUIRED_SLOTS}
    for slot in pool:
        kind = slot.slot_kind()
        if kind in by_kind:
            by_kind[kind].append(slot)
        else:
            unplaced.append(slot.source_id)

    chosen: list[ProposedSlot] = []
    publisher_counts: dict[str, int] = {}
    # Hardest bucket first: a bucket with barely enough candidates constrains
    # everything after it, and choosing it last is how a solver paints itself
    # into a corner.
    order = sorted(REQUIRED_SLOTS, key=lambda kind: len(by_kind[kind]) - REQUIRED_SLOTS[kind])

    def topics_reachable(remaining_kinds: list[str], covered: set[str]) -> bool:
        available = {
            slot.topic for kind in remaining_kinds for slot in by_kind[kind]
        }
        return set(REQUIRED_TOPICS) <= covered | available

    def place(index: int, kind_index: int) -> bool:
        if kind_index == len(order):
            return set(REQUIRED_TOPICS) <= {slot.topic for slot in chosen}
        kind = order[kind_index]
        needed = REQUIRED_SLOTS[kind]
        picked_here = sum(1 for slot in chosen if slot.slot_kind() == kind)
        if picked_here == needed:
            covered = {slot.topic for slot in chosen}
            if not topics_reachable(order[kind_index + 1 :], covered):
                return False
            return place(0, kind_index + 1)

        # Prefer candidates covering a topic not yet held, then full-text ones.
        covered = {slot.topic for slot in chosen}
        ranked = sorted(
            (slot for slot in by_kind[kind] if slot not in chosen),
            key=lambda slot: (slot.topic in covered, not slot.full_text_capable, slot.source_id),
        )
        for slot in ranked:
            if publisher_counts.get(slot.publisher, 0) >= 2:
                continue
            chosen.append(slot)
            publisher_counts[slot.publisher] = publisher_counts.get(slot.publisher, 0) + 1
            if place(index + 1, kind_index):
                return True
            chosen.pop()
            publisher_counts[slot.publisher] -= 1
        return False

    # A failed search unwinds `chosen` to empty, and the review then reports
    # every bucket that came up short. That is more use than a boolean.
    place(0, 0)
    shortfall = {
        kind: max(REQUIRED_SLOTS[kind] - len(by_kind[kind]), 0) for kind in REQUIRED_SLOTS
    }
    result = review(list(chosen))

    slate = Slate(
        id=slate_id,
        slots=tuple(chosen),
        review=result,
        unplaced=tuple(sorted(unplaced)),
        shortfall={kind: count for kind, count in shortfall.items() if count},
    )
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO slate_proposals (id, slate_json, problems_json, acceptable, "
            "solved_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (
                slate_id,
                json.dumps([slot.source_id for slot in chosen]),
                json.dumps(list(result.problems)),
                int(result.acceptable),
            ),
        )
    return slate


def render(slate: Slate, store: Store) -> str:
    """The slate as the operator reads it before deciding anything."""
    surveyed = probes(store)
    lines = [f"Proposed pilot slate: {len(slate.slots)} of 20 slots", ""]
    for slot in sorted(slate.slots, key=lambda s: (s.slot_kind(), s.source_id)):
        probe = surveyed.get(slot.source_id)
        lines.append(f"  [{slot.slot_kind()}] {slot.source_id} — {slot.publisher}")
        lines.append(f"      topic: {slot.topic}")
        lines.append(
            f"      role proposed: {slot.role.value}"
            + (f" — {probe.role_evidence[0]}" if probe and probe.role_evidence else "")
        )
        lines.append(
            f"      serves {slot.observed_mime}, "
            f"{'full text' if slot.full_text_capable else 'no usable full text'}"
        )
        lines.append(
            "      retention signals: "
            + (slot.retention_rights or "none found — terms must be read by a person")
        )
        lines.append("")

    if slate.shortfall:
        lines.append("Not enough surveyed candidates for:")
        for kind, count in sorted(slate.shortfall.items()):
            lines.append(f"  {kind}: {count} more needed")
        lines.append("")
    if slate.unplaced:
        lines.append(f"Unplaced candidates: {', '.join(slate.unplaced)}")
        lines.append("")
    for problem in slate.review.problems:
        lines.append(f"  REFUSED: {problem}")

    lines.append("")
    lines.append(
        "Two things this proposal does not do. It does not enable anything — "
        "activating a diet epoch is an operator act with its own dry run. And it "
        "does not conclude that retention is permitted: what it gathered is what "
        "each source says about its own terms, and reading them is a person's job."
    )
    return "\n".join(lines)


def accept(store: Store, slate_id: str, actor: str) -> None:
    """Record that a person accepted this slate. Still does not enable it."""
    if not actor:
        raise ValueError("accepting a slate records who accepted it")
    with store.write() as connection:
        connection.execute(
            "UPDATE slate_proposals SET accepted_by = ?, accepted_at = datetime('now') "
            "WHERE id = ?",
            (actor, slate_id),
        )
