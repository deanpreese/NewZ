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
        url="https://www.cia.gov/readingroom/",
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
        url="https://asrs.arc.nasa.gov/search/database.html",
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
        url="https://www.ncei.noaa.gov/access/monitoring/",
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
    # ---- claimant and firsthand: five, and the least retainable ------------
    Seed(
        bucket="claimant_or_firsthand",
        topic="uap_and_aerospace_anomalies",
        publisher="National UFO Reporting Center",
        url="https://nuforc.org/subndx/?id=all",
        why_this_role="firsthand sighting reports in the witness's own words, filed at the time",
        terms=UNCLEAR,
    ),
    Seed(
        bucket="claimant_or_firsthand",
        topic="alternative_physics_and_energy",
        publisher="LENR-CANR",
        url="https://lenr-canr.org/",
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
        url="https://pubpeer.com/",
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
    Seed(
        bucket="empirical_or_replication",
        topic="forteana_cryptids_and_anomalous_natural_events",
        publisher="Royal Society Open Science",
        url="https://royalsocietypublishing.org/journal/rsos",
        why_this_role="where environmental-DNA and survey work on disputed species is published, CC BY",
        terms=OPEN_LICENCE,
    ),
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
        url="https://journalofscientificexploration.org/index.php/jse",
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
    Seed(
        bucket="skeptical_or_forensic",
        topic="psi_and_consciousness_claims",
        publisher="Skeptical Inquirer (Center for Inquiry)",
        url="https://skepticalinquirer.org/",
        why_this_role="sustained methodological criticism of psi experiments rather than dismissal of them",
        terms=UNCLEAR,
    ),
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


def gaps() -> dict[str, Any]:
    """What this slate cannot do, stated before the pilot rather than after it.

    Two findings, and neither is a shortcoming of the search — they are what the
    slate is, said out loud.
    """
    roles = {seed.bucket for seed in SEEDS}
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
