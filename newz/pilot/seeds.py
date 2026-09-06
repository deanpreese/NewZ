"""A specific diet: twenty named sources against the twenty prescribed slots.

This is a **proposal, not a fact**. It was written from what one model knew at a
point in time, without fetching anything, so every URL here is a hypothesis that
`--survey` exists to test and every licence note is a prompt to go and read the
terms rather than a finding about them. A source that has moved, closed, or
changed its terms will show up as a refusal in the survey, which is the correct
outcome and not a failure of the slate.

**Retention is what actually shaped these choices.** Under 17 U.S.C. § 105 a
work of the United States government is not copyrightable, which is a checkable,
durable basis for retaining full text. Almost nothing else is. So the slots that
carry evidentiary weight — primary records and empirical work, ten of the twenty
— are deliberately weighted toward public-domain government sources and
open-licence journals, and the claimant slots are mostly not retainable at all.

That last point is a finding rather than a shortcoming, and it is worth stating
plainly before the pilot starts: **a claimant source that cannot be retained in
full cannot establish even an attribution.** `SPEC.md` section 6 item 8 makes
material without retention rights a lead, and section 7.2 requires a retained
artifact and an exact span for any countable edge. Five of these twenty are
claimant slots, and on current terms most of them will produce leads and
nothing else. The pilot will therefore under-represent what claimants actually
said, in a system whose whole purpose is to represent that fairly. The honest
answers are to seek permission, to prefer claimants who publish under an open
licence, or to accept the gap and report it — and that choice is the operator's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Licence positions, as they need to be read rather than as they are known.
#: Pairings the specification does not settle but domain knowledge does. Several
#: assignments score identically, and the search picks among them arbitrarily —
#: but "a patent is where an energy claim is formally lodged" and "the aviation
#: record is where a UAP sighting first becomes a document" are knowledge rather
#: than arbitrariness. Pinned rather than encoded into the score, so that the
#: scoring function is not quietly rewritten until it produces a wanted answer.
#: What the operator decided about this slate, and when. A gap the operator has
#: weighed and accepted is a different thing from a gap nobody has looked at,
#: and the difference has to survive in the record rather than in a memory of a
#: conversation. Each entry says what was accepted, while it holds, and what
#: would close it — an acceptance with no expiry condition is a requirement
#: quietly deleted.
DECISIONS: tuple[dict[str, str], ...] = (
    {
        "id": "decision:no-adjudicator",
        "on": "2026-09-05",
        "actor": "operator:dean",
        "decision": "accept the gap",
        "subject": "no adjudicator in the slate",
        "holds_while": "the pilot stays at R0-R1 and takes no allegations about living people",
        "closes_when": "R2 intake adds a court, tribunal or regulator",
        "cost": (
            "from this diet a false allegation about a living party cannot reach "
            "`refuted`, which is the only route symmetry leaves open to the accused"
        ),
    },
    {
        "id": "decision:claimant-retention",
        "on": "2026-09-05",
        "actor": "operator:dean",
        "decision": "accept the gap and report it",
        "subject": "claimant slots whose retention terms are not established",
        "holds_while": "every affected slot is reported as lead-only rather than read as retained",
        "closes_when": "the terms are read, or permission is given, per source",
        "cost": (
            "the pilot under-represents what claimants said, and the alternative — "
            "preferring claimants who publish permissively — would bias the slate "
            "toward a property of a claimant's licensing rather than of their claim"
        ),
    },
    {
        "id": "decision:drop-the-unreadable",
        "on": "2026-09-05",
        "actor": "operator:dean",
        "decision": "drop rather than ask",
        "subject": (
            "Skeptical Inquirer, whose robots.txt disallows every path, and Royal "
            "Society Open Science, whose robots.txt permits the path its server "
            "then refuses"
        ),
        "holds_while": "always, unless the operator asks them",
        "closes_when": "a source grants access, which only a person can request",
        "cost": (
            "psi and consciousness claims lose the only source in this diet able to "
            "contradict them, and forteana loses its empirical slot. Three of the "
            "twenty slots are now open"
        ),
    },
    {
        "id": "decision:apply-the-repoints",
        "on": "2026-09-05",
        "actor": "operator:dean",
        "decision": "apply the six that survived the survey",
        "subject": "slot URLs pointing at material rather than front doors",
        "holds_while": "the paths keep serving what the survey observed",
        "closes_when": "a path stops resolving, which the next survey would find",
        "cost": (
            "none observed; the four refuted proposals were not applied and are kept "
            "in `repoint.PROPOSALS` labelled as refuted"
        ),
    },
    {
        "id": "decision:expansion-target",
        "on": "2026-09-05",
        "actor": "operator:dean",
        "decision": "51 slots, at Phase 6",
        "subject": "how far the catalogue grows, and when",
        "holds_while": "Gate 5 has not passed",
        "closes_when": "Gate 5 passes and the mode reaches production",
        "cost": (
            "none taken now, and that is the point: expanding first would replace the "
            "twenty-slot pilot SPEC 5.2 requires, reset Gate 5's route count, and — "
            "at any size between 21 and 50 — leave topics the diet reads seriously "
            "with nothing in it able to contradict them"
        ),
    },
    {
        "id": "decision:drop-the-declined",
        "on": "2026-09-05",
        "actor": "operator:dean",
        "decision": "drop rather than ask",
        "subject": "CUFOS, The Galileo Project and NUFORC, which decline the agent",
        "holds_while": "always, unless the operator asks them",
        "closes_when": "a source grants access, which only a person can request",
        "cost": (
            "one claimant slot on UAP is left open, and the UAP topic loses its "
            "largest firsthand report collection"
        ),
    },
)

PINS: frozenset[tuple[str, str]] = frozenset(
    {
        ("primary_or_adjudicative", "alternative_physics_and_energy"),
        ("primary_or_adjudicative", "uap_and_aerospace_anomalies"),
    }
)

PUBLIC_DOMAIN = "US federal work, 17 U.S.C. 105 — full retention defensible"
OPEN_LICENCE = "open licence claimed by the publisher — confirm the specific terms"
UNCLEAR = "terms not established — a person must read them before retention"


@dataclass(frozen=True, slots=True)
class Seed:
    bucket: str
    topic: str
    publisher: str
    url: str
    why_this_role: str
    terms: str
    independence_group: str | None = None
    caution: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "bucket": self.bucket,
            "topic": self.topic,
            "publisher": self.publisher,
            "url": self.url,
            "why_this_role": self.why_this_role,
            "terms": self.terms,
            "independence_group": self.independence_group,
            "caution": self.caution,
        }


SEEDS: tuple[Seed, ...] = (
    # ---- primary and adjudicative: six, and the evidentiary backbone --------
    Seed(
        bucket="primary_or_adjudicative",
        topic="declassified_material_and_historical_secrecy",
        publisher="CIA FOIA Electronic Reading Room (CREST)",
        url="https://www.cia.gov/readingroom/collection/stargate",
        why_this_role=(
            "the declassified documents themselves, released by the agency that "
            "classified them — the primary record this topic is made of"
        ),
        terms=PUBLIC_DOMAIN,
        caution=(
            "a released document establishes what the document says and that it was "
            "released; redactions are absences the record cannot speak to"
        ),
    ),
    Seed(
        bucket="primary_or_adjudicative",
        topic="alternative_physics_and_energy",
        publisher="United States Patent and Trademark Office",
        url="https://ppubs.uspto.gov/pubwebapp/",
        why_this_role="where an energy claim is formally lodged: the filing itself, exactly",
        terms=PUBLIC_DOMAIN,
        caution="a patent proves a filing and its contents, never performance (SPEC 7.3 rule 3)",
    ),
    Seed(
        bucket="primary_or_adjudicative",
        topic="uap_and_aerospace_anomalies",
        publisher="NASA Aviation Safety Reporting System",
        url="https://asrs.arc.nasa.gov/search/reportsets.html",
        why_this_role="the primary record of what aircrew reported, filed at the time and indexed",
        terms=PUBLIC_DOMAIN,
        caution=(
            "AARO's resolution reports would fill this slot adjudicatively instead; an ASRS "
            "entry and an AARO report on one incident share a basis and need a derivation "
            "link rather than two counts"
        ),
    ),
    Seed(
        bucket="primary_or_adjudicative",
        topic="forteana_cryptids_and_anomalous_natural_events",
        publisher="NOAA National Centers for Environmental Information",
        url="https://www.ncei.noaa.gov/access/monitoring/monthly-report/",
        why_this_role="instrumented records of natural events an anomalous account would have to fit",
        terms=PUBLIC_DOMAIN,
    ),
    Seed(
        bucket="primary_or_adjudicative",
        topic="general_scientific_and_institutional_context",
        publisher="National Institute of Standards and Technology",
        url="https://www.nist.gov/publications",
        why_this_role="the measurement and standards authority a performance claim is checked against",
        terms=PUBLIC_DOMAIN,
    ),
    Seed(
        bucket="primary_or_adjudicative",
        topic="metascience_methods_and_replication",
        publisher="Crossref",
        url="https://api.crossref.org/works",
        why_this_role=(
            "the publication record itself — what was published, corrected, and retracted, "
            "with the retraction notice linked to what it retracts"
        ),
        terms=OPEN_LICENCE,
        caution="metadata is CC0; the articles it points at are not",
    ),
    # ---- claimant and firsthand: four filled, one open ---------------------
    #
    # The fifth was the National UFO Reporting Center, dropped on 2026-09-05
    # when the operator chose not to ask a source that had already declined the
    # agent. Its slot is left open rather than filled from the next candidate
    # down: which source speaks for a topic is a diet decision, and the two that
    # could fill it are named in `gaps()` for the operator to choose between.
    Seed(
        bucket="claimant_or_firsthand",
        topic="alternative_physics_and_energy",
        publisher="LENR-CANR",
        url="https://lenr-canr.org/wordpress/?page_id=952",
        why_this_role="the proponents' own library; the strongest actual position, stated by them",
        terms=UNCLEAR,
        caution="papers are hosted by author permission; retention terms differ per document",
    ),
    Seed(
        bucket="claimant_or_firsthand",
        topic="psi_and_consciousness_claims",
        publisher="Institute of Noetic Sciences",
        url="https://noetic.org/research/",
        why_this_role="a research organisation that is also an advocate; its own account of its work",
        terms=UNCLEAR,
    ),
    Seed(
        bucket="claimant_or_firsthand",
        topic="general_scientific_and_institutional_context",
        publisher="The Conversation",
        url="https://theconversation.com/us/technology",
        why_this_role="academics asserting in their own voice, with their affiliation attached",
        terms=OPEN_LICENCE,
        caution="CC BY-ND is claimed; no-derivatives may bear on quoting at length",
    ),
    Seed(
        bucket="claimant_or_firsthand",
        topic="metascience_methods_and_replication",
        publisher="PubPeer",
        url="https://pubpeer.com/recent",
        why_this_role=(
            "post-publication comments are allegations until adjudicated, which is what a "
            "claimant role is for"
        ),
        terms=UNCLEAR,
        caution="comments name living researchers; this source will sit at R2 or above",
    ),
    # ---- empirical and replication: four ----------------------------------
    Seed(
        bucket="empirical_or_replication",
        topic="declassified_material_and_historical_secrecy",
        publisher="Information Security Oversight Office (NARA)",
        url="https://www.archives.gov/isoo/reports",
        why_this_role=(
            "the awkward pairing has a real answer: ISOO counts classification and "
            "declassification, so secrecy has measured quantities rather than only anecdotes"
        ),
        terms=PUBLIC_DOMAIN,
    ),
    # The empirical slot on forteana was Royal Society Open Science, dropped on
    # 2026-09-05: robots.txt permits the path and the server answers 403 anyway.
    Seed(
        bucket="empirical_or_replication",
        topic="anomalous_history_and_archaeology",
        publisher="PLOS ONE",
        url="https://journals.plos.org/plosone/browse/paleontology_and_paleobiology",
        why_this_role="dating and provenance studies published open, where a chronology claim meets data",
        terms=OPEN_LICENCE,
    ),
    Seed(
        bucket="empirical_or_replication",
        topic="psi_and_consciousness_claims",
        publisher="Journal of Scientific Exploration",
        url="https://journalofscientificexploration.org/index.php/jse/issue/archive",
        why_this_role="peer-reviewed and method-visible on exactly the claims other journals decline",
        terms=OPEN_LICENCE,
    ),
    # ---- skeptical and forensic: three, one per contested topic ------------
    Seed(
        bucket="skeptical_or_forensic",
        topic="uap_and_aerospace_anomalies",
        publisher="Metabunk",
        url="https://www.metabunk.org/forums/ufos-and-aliens.31/",
        why_this_role=(
            "shows its working — reconstructions, parallax, glare analysis — which is what "
            "makes an analysis countable rather than an opinion"
        ),
        terms=UNCLEAR,
    ),
    # The skeptical slot on psi was the Skeptical Inquirer, dropped on 2026-09-05:
    # its robots.txt disallows every path, including the one the slate held, so
    # the slot had been unreadable since before the robots check existed. Losing
    # it leaves psi and consciousness claims with no source in this diet able to
    # contradict them — and psi is one of only three topics the prescription
    # gave a skeptic to at all.
    Seed(
        bucket="skeptical_or_forensic",
        topic="alternative_physics_and_energy",
        publisher="New Energy Times",
        url="https://newenergytimes.com/",
        why_this_role=(
            "investigative work inside the field that has repeatedly contradicted its own "
            "side's claims, which is what a forensic role is for"
        ),
        terms=UNCLEAR,
    ),
    # ---- historical and general context: two -------------------------------
    Seed(
        bucket="historical_or_general_context",
        topic="anomalous_history_and_archaeology",
        publisher="Jason Colavito",
        url="https://www.jasoncolavito.com/blog",
        why_this_role=(
            "traces a claim back through the texts that carried it — provenance and "
            "chronology, which is exactly what this role supplies"
        ),
        terms=UNCLEAR,
    ),
    Seed(
        bucket="historical_or_general_context",
        topic="uap_and_aerospace_anomalies",
        publisher="Wikipedia",
        url="https://en.wikipedia.org/wiki/Category:UFOs",
        why_this_role="chronology and interpretive context, and the one general reference with usable terms",
        terms=OPEN_LICENCE,
        caution=(
            "requires a contactable User-Agent or it returns 403; NEWZ_USER_AGENT already "
            "carries one"
        ),
    ),
)


def seed_adapter(bucket: str, topic: str) -> tuple[tuple[str, str, str], ...]:
    """The candidate adapter: what this slate offers for one prescribed slot."""
    return tuple(
        (seed.url, seed.publisher, seed.why_this_role)
        for seed in SEEDS
        if seed.bucket == bucket and seed.topic == topic
    )


def register() -> None:
    from newz.pilot.slots import register_candidate_adapter

    register_candidate_adapter("seeds", seed_adapter)


def prescribed() -> tuple:
    """The prescription this slate answers, with its pins applied."""
    from newz.pilot.prescription import prescribe

    return prescribe(pins=PINS)


def _decision(subject_id: str) -> dict[str, str] | None:
    return next((entry for entry in DECISIONS if entry["id"] == subject_id), None)


def gaps() -> dict[str, Any]:
    """What this slate cannot do, stated before the pilot rather than after it.

    Neither finding is a shortcoming of the search — they are what the slate is,
    said out loud. Both now carry the operator's answer, because a gap that has
    been weighed and accepted still has to be visible: an accepted gap that
    stopped being reported would be indistinguishable from one nobody found.
    """
    roles = {seed.bucket for seed in SEEDS}
    from newz.pilot.prescription import unmet

    unfilled = unmet(prescribed(), [(seed.bucket, seed.topic) for seed in SEEDS])

    # A topic the slate reads seriously with nothing in the slate able to
    # contradict it. Computed from what the slate holds rather than from what
    # was dropped, so it stays true however the slate next changes.
    from newz.pilot.prescription import CONTESTED_THRESHOLD, SKEPTICAL

    prescribed_per_topic: dict[str, int] = {}
    for spec in prescribed():
        prescribed_per_topic[spec.topic] = prescribed_per_topic.get(spec.topic, 0) + 1
    has_skeptic = {seed.topic for seed in SEEDS if seed.bucket == SKEPTICAL}
    unopposed = {
        topic
        for topic, count in prescribed_per_topic.items()
        if count >= CONTESTED_THRESHOLD and topic not in has_skeptic
    }
    claimant_unclear = [
        seed.publisher
        for seed in SEEDS
        if seed.bucket == "claimant_or_firsthand" and seed.terms == UNCLEAR
    ]
    return {
        "no_adjudicator": {
            "finding": (
                "no source in this slate is an adjudicator. The single-record exception of "
                "SPEC 7.3 fires only on a final adjudicative record within its declared "
                "scope, so from this diet a false allegation about a living party cannot "
                "reach `refuted` — the only route symmetry leaves open for the accused."
            ),
            "acceptable_while": "the pilot stays at R0-R1 and takes no allegations",
            "closes_when": (
                "a court, tribunal or regulator is added, which R2 intake needs anyway"
            ),
            "buckets_present": sorted(roles),
            "operator": _decision("decision:no-adjudicator"),
        },
        "claimant_retention": {
            "finding": (
                f"{len(claimant_unclear)} of 5 claimant slots have unestablished terms. A "
                "claimant source that cannot be retained in full cannot establish even an "
                "attribution, so the pilot will under-represent what claimants said."
            ),
            "sources": sorted(claimant_unclear),
            "answers": [
                "seek permission from each",
                "prefer claimants publishing under an open licence",
                "accept the gap and report it",
            ],
            "operator": _decision("decision:claimant-retention"),
        },
        "open_slots": {
            "finding": (
                f"{len(unfilled)} prescribed slot(s) have no source. Dropping a source "
                "that declines the agent leaves the slot it was filling open, and the "
                "slate proposes rather than fills it: which source speaks for a topic "
                "is a diet decision."
            ),
            "slots": [spec.as_record() for spec in unfilled],
            "candidates": {
                "claimant_or_firsthand/uap_and_aerospace_anomalies": [
                    "MUFON — case management database; terms say all rights reserved",
                    "BUFORA — unsurveyed; the British counterpart, and a distinct basis",
                ]
            },
            "operator": _decision("decision:drop-the-declined"),
        },
        "unopposed_topics": {
            "finding": (
                f"{len(unopposed)} topic(s) hold slots this diet reads seriously and "
                "have no skeptical or forensic source in it. `TRUE_NORTH.md` asks that "
                "support and refutation face the same burden; where a topic has no "
                "source able to contradict it, they cannot. This is a property of the "
                "slate rather than of any claim in it, and it travels with every "
                "conclusion the slate produces on those topics."
            ),
            "topics": sorted(unopposed),
            "why": (
                "the prescription gives three of eight topics a skeptical slot, and "
                "one of the three was filled by a source whose robots.txt disallows "
                "every path — so the slot was unreadable before it was dropped, and "
                "the topic was unopposed before anyone noticed"
            ),
            "closes_when": "a skeptical or forensic source is found for each",
            "operator": _decision("decision:drop-the-unreadable"),
        },
        "applied_repoints": {
            "finding": (
                "six slot URLs now point at material rather than a front door, applied "
                "after the survey observed each one serving what was claimed. Four "
                "further proposals were refuted and not applied."
            ),
            "operator": _decision("decision:apply-the-repoints"),
        },
    }


def retention_summary() -> dict[str, Any]:
    """Which slots this slate can retain, and which produce leads only.

    The figure that matters is the claimant one: a claimant source that cannot
    be retained cannot establish even an attribution, so a slate where four of
    five claimant slots are unresolved is a slate that will under-represent what
    claimants said.
    """
    by_terms: dict[str, list[str]] = {}
    by_bucket: dict[str, dict[str, int]] = {}
    for seed in SEEDS:
        by_terms.setdefault(seed.terms, []).append(seed.publisher)
        by_bucket.setdefault(seed.bucket, {})
        by_bucket[seed.bucket][seed.terms] = by_bucket[seed.bucket].get(seed.terms, 0) + 1
    claimants = by_bucket.get("claimant_or_firsthand", {})
    return {
        "by_terms": {terms: sorted(names) for terms, names in sorted(by_terms.items())},
        "by_bucket": {bucket: dict(sorted(terms.items())) for bucket, terms in sorted(by_bucket.items())},
        "public_domain_slots": len([s for s in SEEDS if s.terms == PUBLIC_DOMAIN]),
        "unclear_slots": len([s for s in SEEDS if s.terms == UNCLEAR]),
        "claimant_slots_unclear": claimants.get(UNCLEAR, 0),
        "finding": (
            f"{claimants.get(UNCLEAR, 0)} of "
            f"{sum(claimants.values())} claimant slots have unestablished terms. "
            "A claimant source that cannot be retained in full cannot establish even an "
            "attribution, so the pilot will under-represent what claimants said unless "
            "permission is sought or open-licence claimants are preferred."
        ),
    }


def render() -> str:
    """The slate as a person reads it before deciding anything."""
    lines = [
        "A specific diet: 20 sources against the 20 slots the prescription asks for.",
        "",
        "Written without fetching anything. Every URL is a hypothesis the survey tests,",
        "and every licence note is a prompt to read the terms rather than a finding.",
        "",
    ]
    for bucket in (
        "primary_or_adjudicative",
        "claimant_or_firsthand",
        "empirical_or_replication",
        "skeptical_or_forensic",
        "historical_or_general_context",
    ):
        lines.append(f"{bucket}:")
        for seed in SEEDS:
            if seed.bucket != bucket:
                continue
            lines.append(f"  {seed.publisher}")
            lines.append(f"    {seed.url}")
            lines.append(f"    for: {seed.topic}")
            lines.append(f"    why: {seed.why_this_role}")
            lines.append(f"    terms: {seed.terms}")
            if seed.caution:
                lines.append(f"    caution: {seed.caution}")
        lines.append("")
    summary = retention_summary()
    lines.append("Retention:")
    lines.append(f"  {summary['public_domain_slots']} of 20 are US federal works")
    lines.append(f"  {summary['unclear_slots']} of 20 have terms nobody has read yet")
    lines.append("")
    for name, gap in sorted(gaps().items()):
        lines.append(f"Gap — {name}:")
        lines.append(f"  {gap['finding']}")
        lines.append("")
    return "\n".join(lines)
