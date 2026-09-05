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
        topic="uap_and_aerospace_anomalies",
        publisher="All-domain Anomaly Resolution Office (US DoD)",
        url="https://www.aaro.mil/Reports/",
        why_this_role="the office of record for US government UAP resolution; publishes findings",
        terms=PUBLIC_DOMAIN,
        caution="a resolution report is a finding within AARO's scope, not a finding about the world",
    ),
    Seed(
        bucket="primary_or_adjudicative",
        topic="uap_and_aerospace_anomalies",
        publisher="NASA Aviation Safety Reporting System",
        url="https://asrs.arc.nasa.gov/search/database.html",
        why_this_role="the primary record of what aircrew actually reported, filed at the time",
        terms=PUBLIC_DOMAIN,
        caution=(
            "an ASRS entry and an AARO report can rest on one incident; that is a shared "
            "basis and needs a derivation link, not two counts"
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
        topic="psi_and_consciousness_claims",
        publisher="OSF Registries (Center for Open Science)",
        url="https://osf.io/registries/discover",
        why_this_role=(
            "a preregistration is the primary record of what was predicted before the data, "
            "which is the single most useful document in this field"
        ),
        terms=OPEN_LICENCE,
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
        topic="alternative_physics_and_energy",
        publisher="United States Patent and Trademark Office",
        url="https://ppubs.uspto.gov/pubwebapp/",
        why_this_role="grants and their examination record; the filing itself, exactly",
        terms=PUBLIC_DOMAIN,
        caution="a patent proves a filing and its contents, never performance (SPEC 7.3 rule 3)",
    ),
    # ---- claimant and firsthand: five, and the least retainable ------------
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
        topic="general_scientific_and_institutional_context",
        publisher="The Conversation",
        url="https://theconversation.com/us/technology",
        why_this_role="academics asserting in their own voice, with their affiliation attached",
        terms=OPEN_LICENCE,
        caution="CC BY-ND is claimed; no-derivatives may bear on quoting at length",
    ),
    Seed(
        bucket="claimant_or_firsthand",
        topic="anomalous_history_and_archaeology",
        publisher="Graham Hancock",
        url="https://grahamhancock.com/",
        why_this_role="the best-known claimant in the field, in his own words rather than paraphrased",
        terms=UNCLEAR,
    ),
    Seed(
        bucket="claimant_or_firsthand",
        topic="metascience_methods_and_replication",
        publisher="PubPeer",
        url="https://pubpeer.com/",
        why_this_role="post-publication comments are allegations until adjudicated, which is what a claimant role is for",
        terms=UNCLEAR,
        caution="comments name living researchers; this source will sit at R2 or above",
    ),
    Seed(
        bucket="claimant_or_firsthand",
        topic="psi_and_consciousness_claims",
        publisher="Institute of Noetic Sciences",
        url="https://noetic.org/research/",
        why_this_role="a research organisation that is also an advocate; its own account of its work",
        terms=UNCLEAR,
    ),
    # ---- empirical and replication: four ----------------------------------
    Seed(
        bucket="empirical_or_replication",
        topic="psi_and_consciousness_claims",
        publisher="Journal of Scientific Exploration",
        url="https://journalofscientificexploration.org/index.php/jse",
        why_this_role="peer-reviewed and method-visible on exactly the claims other journals decline",
        terms=OPEN_LICENCE,
    ),
    Seed(
        bucket="empirical_or_replication",
        topic="metascience_methods_and_replication",
        publisher="Royal Society Open Science",
        url="https://royalsocietypublishing.org/journal/rsos",
        why_this_role="publishes replications and null results as first-class research",
        terms=OPEN_LICENCE,
    ),
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
        topic="uap_and_aerospace_anomalies",
        publisher="arXiv",
        url="https://arxiv.org/list/astro-ph.IM/recent",
        why_this_role="where instrumented observation work in this area is actually posted",
        terms=OPEN_LICENCE,
        caution="licences are per-article on arXiv; some are not redistributable",
    ),
    # ---- skeptical and forensic: three ------------------------------------
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
        topic="anomalous_history_and_archaeology",
        publisher="Jason Colavito",
        url="https://www.jasoncolavito.com/blog",
        why_this_role="traces claims to their sources, which is the specific work this bucket needs",
        terms=UNCLEAR,
    ),
    Seed(
        bucket="skeptical_or_forensic",
        topic="forteana_cryptids_and_anomalous_natural_events",
        publisher="Skeptical Inquirer (CSI)",
        url="https://skepticalinquirer.org/",
        why_this_role="sustained investigative coverage of cryptid and Fortean claims",
        terms=UNCLEAR,
    ),
    # ---- historical and general context: two -------------------------------
    Seed(
        bucket="historical_or_general_context",
        topic="declassified_material_and_historical_secrecy",
        publisher="National Security Archive (George Washington University)",
        url="https://nsarchive.gwu.edu/",
        why_this_role="FOIA'd documents published with the provenance and chronology around them",
        terms=UNCLEAR,
        caution="the documents are usually public domain; the Archive's own commentary is not",
    ),
    Seed(
        bucket="historical_or_general_context",
        topic="alternative_physics_and_energy",
        publisher="Wikipedia",
        url="https://en.wikipedia.org/wiki/Category:Fringe_physics",
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
    lines.append(f"  {summary['finding']}")
    return "\n".join(lines)
