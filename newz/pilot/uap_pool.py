"""A reviewed pool of UAP sources, against four slots.

The operator supplied sixty-odd sites. The first thing to say about them is
structural rather than editorial: **the menu gives UAP four slots of twenty**,
so this pool is competing for a fifth of the diet, and sixty candidates for four
places is a selection problem rather than an inclusion one.

The second thing matters more. This field's sources are unusually
**lineage-dense**: a single witness report is filed once and then reappears in a
case database, a map front-end, three aggregators and a blog. `SPEC.md` section
7.2 already refuses to count those as separate bases, but only if the lineage is
recorded — so the review below marks the clusters, and the ones that share an
upstream origin carry it as an independence group or a note about derivation.

The distinction between the two mechanisms is worth stating because this pool
contains both:

- **Independence group** — shared ownership or editorial control. MUFON's case
  system and a map that renders it are one editorial act, so they are grouped.
- **Derivation** — different owners, same upstream origin. Three archives each
  holding the same Project Blue Book document are three publications of one
  record, which is a derivation link per document rather than a group.

Grouping the Blue Book archives would be wrong: they hold distinct originals
too, and the collapse belongs at the basis rather than at the source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CANDIDATE = "candidate"
LEAD_ONLY = "lead_only"
DECLINED = "declined"


@dataclass(frozen=True, slots=True)
class Reviewed:
    name: str
    verdict: str
    bucket: str = ""
    note: str = ""
    url: str = ""
    independence_group: str | None = None
    upstream: str = ""

    def as_record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "verdict": self.verdict,
            "bucket": self.bucket,
            "note": self.note,
            "url": self.url,
            "independence_group": self.independence_group,
            "upstream": self.upstream,
        }


#: Groups where two entries are one editorial act. Membership blocks
#: independence and never establishes it.
GROUP_MUFON = "grp:mufon"
GROUP_NUFORC = "grp:nuforc"

REVIEW: tuple[Reviewed, ...] = (
    # -- primary records and archives: the strongest thing this field has -----
    Reviewed(
        "NICAP",
        CANDIDATE,
        "primary_or_adjudicative",
        "the deepest document archive in the field: case files, correspondence, "
        "and government records held as scans rather than summarised",
        "https://www.nicap.org/",
        upstream="holds Blue Book material other archives also hold; per-document derivation",
    ),
    Reviewed(
        "CUFOS",
        CANDIDATE,
        "primary_or_adjudicative",
        "Hynek's archive; case files and the Journal of UFO Studies back catalogue",
        "https://cufos.org/",
        upstream="overlaps NICAP on Blue Book and on jointly investigated cases",
    ),
    Reviewed(
        "Project 1947",
        CANDIDATE,
        "primary_or_adjudicative",
        "contemporaneous 1947-wave press and government documents, transcribed with sources",
        "https://www.project1947.com/",
        upstream="overlaps NICAP and CUFOS on the 1947 material",
    ),
    Reviewed(
        "National UFO Historical Records Center",
        CANDIDATE,
        "primary_or_adjudicative",
        "explicitly an archival project; the newest and least tested of the four",
        "https://nuhrc.com/",
    ),
    Reviewed(
        "Bruce Maccabee's Website",
        CANDIDATE,
        "primary_or_adjudicative",
        "FOIA'd Navy and FBI documents published by the requester, with his analysis "
        "alongside them — the documents are primary, the analysis is claimant",
        "https://brumac.8k.com/",
    ),
    Reviewed(
        "NIDS",
        LEAD_ONLY,
        "primary_or_adjudicative",
        "defunct; its reports survive mainly through third-party copies, so provenance "
        "is exactly what a primary record cannot be vague about",
    ),
    Reviewed(
        "StealthSkater Archives",
        LEAD_ONLY,
        note="an aggregation of other people's material; every basis under it belongs to "
        "somebody else, which is the definition of a lead",
    ),
    Reviewed(
        "Daniel Tarr's UFO Library",
        LEAD_ONLY,
        note="a library of others' documents; useful for finding a record, not for holding one",
    ),
    Reviewed(
        "NOUFORS",
        LEAD_ONLY,
        note="Canadian archive and case collection; mixed original and republished",
    ),
    # -- instrumented and empirical -------------------------------------------
    Reviewed(
        "The Galileo Project",
        CANDIDATE,
        "empirical_or_replication",
        "instrumented observatories with published hardware papers and stated methods; "
        "the only entry here whose output goes through ordinary peer review",
        "https://projects.iq.harvard.edu/galileo/",
    ),
    Reviewed(
        "Scientific Coalition for UAP Studies",
        CANDIDATE,
        "empirical_or_replication",
        "publishes analyses with methods sections; quality varies by paper, which is what "
        "a per-assertion evidence model is for",
        "https://www.explorescu.org/",
    ),
    Reviewed(
        "UAPX",
        CANDIDATE,
        "empirical_or_replication",
        "instrumented expeditions with at least one peer-reviewed output",
        "https://www.uapexpedition.org/",
    ),
    Reviewed(
        "MADAR",
        CANDIDATE,
        "empirical_or_replication",
        "a distributed magnetometer network publishing its own readings — instrument data "
        "rather than testimony about instruments",
        "https://madar.site/",
    ),
    Reviewed(
        "AIAA UAP",
        CANDIDATE,
        "empirical_or_replication",
        "a professional engineering society's community of interest; institutional standing "
        "and a publication record that predates the subject",
        "https://www.aiaa.org/",
    ),
    Reviewed(
        "UFODATA",
        DECLINED,
        note="a proposed instrument network that appears not to have deployed; nothing to read",
    ),
    Reviewed(
        "UPDB",
        LEAD_ONLY,
        note="a compiled database of other databases; a lineage problem rather than a source",
    ),
    Reviewed(
        "Bobofango's Spreadsheet",
        LEAD_ONLY,
        note="a compilation of cases from other collections; useful as an index, countable as nothing",
    ),
    # -- skeptical and forensic: where this list is unexpectedly strong -------
    Reviewed(
        "Metabunk",
        CANDIDATE,
        "skeptical_or_forensic",
        "already in the slate; reconstructions and measurements that can be checked",
        "https://www.metabunk.org/",
    ),
    Reviewed(
        "Ian Ridpath's UFO Skeptic Pages",
        CANDIDATE,
        "skeptical_or_forensic",
        "an astronomer working case by case with named sources; the Rendlesham work is "
        "the model of what a countable refutation looks like",
        "https://www.ianridpath.com/ufo/",
    ),
    Reviewed(
        "Tim Printy's Website",
        CANDIDATE,
        "skeptical_or_forensic",
        "SUNlite: two decades of sustained, sourced case analysis in one voice",
        "https://www.astronomyufo.com/UFO/sunlite.htm",
    ),
    Reviewed(
        "UFOs at Close Sight",
        CANDIDATE,
        "skeptical_or_forensic",
        "Patrick Gross documents each case with its sources and states where he lands and "
        "why — the rarest thing in this field and the easiest to extract from",
        "http://ufologie.patrickgross.org/",
    ),
    Reviewed(
        "UFO Watchdog",
        LEAD_ONLY,
        "skeptical_or_forensic",
        "investigates credentials and conduct within ufology; often about living people, "
        "which puts it at R2 or above before the evidence rules even start",
    ),
    Reviewed(
        "Hoodwinked By UFOs",
        LEAD_ONLY,
        "skeptical_or_forensic",
        "skeptical commentary; argument rather than method-visible analysis",
    ),
    Reviewed(
        "UFO Skeptic",
        LEAD_ONLY,
        "skeptical_or_forensic",
        "scientists' essays on the subject; positions rather than analyses, so an "
        "`inference` assertion and not a countable one",
    ),
    Reviewed(
        "Isaac Koi",
        CANDIDATE,
        "historical_or_general_context",
        "a lawyer's bibliographic work: what exists, where it is, and who said it first — "
        "provenance and chronology, which is exactly this bucket",
        "http://www.isaackoi.com/",
    ),
    Reviewed(
        "UFOs and Intelligence: A Timeline by George M. Eberhart",
        CANDIDATE,
        "historical_or_general_context",
        "a sourced chronology by a professional librarian",
    ),
    # -- claimant and firsthand ----------------------------------------------
    Reviewed(
        "NUFORC",
        CANDIDATE,
        "claimant_or_firsthand",
        "already in the slate; reports in the witness's own words, filed at the time",
        "https://nuforc.org/",
        independence_group=GROUP_NUFORC,
    ),
    Reviewed(
        "MUFON",
        CANDIDATE,
        "claimant_or_firsthand",
        "the other large case system; field investigator reports as well as raw sightings",
        "https://mufon.com/",
        independence_group=GROUP_MUFON,
    ),
    Reviewed(
        "UFO Stalker",
        DECLINED,
        note="renders MUFON's case data on a map; one editorial act with MUFON, and taking "
        "both would count one report twice",
        independence_group=GROUP_MUFON,
    ),
    Reviewed(
        "BUFORA",
        CANDIDATE,
        "claimant_or_firsthand",
        "British case investigation with its own reports rather than reprints",
        "https://www.bufora.org.uk/",
    ),
    Reviewed(
        "Above Top Secret",
        LEAD_ONLY,
        "claimant_or_firsthand",
        "a forum: firsthand accounts genuinely appear here, and so does everything else, "
        "with no editorial act to attribute",
    ),
    Reviewed(
        "International UFO Congress",
        LEAD_ONLY,
        note="a conference; its value is the speakers, whose own material is the source",
    ),
    # -- journalism: secondary by construction --------------------------------
    Reviewed(
        "The War Zone",
        LEAD_ONLY,
        note="the best-sourced defence reporting on the subject, and still reporting: its "
        "claims rest on documents and officials it names, and those are the bases",
    ),
    Reviewed(
        "The Debrief",
        LEAD_ONLY,
        note="reports the field; a lead to the document rather than the document",
    ),
    Reviewed("Open Minds", LEAD_ONLY, note="media coverage; secondary by construction"),
    Reviewed("The UFO Chronicles", LEAD_ONLY, note="republishes others' reporting"),
    Reviewed("National UFO Center", LEAD_ONLY, note="aggregates NUFORC and press reports",
             independence_group=GROUP_NUFORC),
    Reviewed("UFO Casebook", LEAD_ONLY, note="aggregates case reports from other collections"),
    Reviewed("UFO Info", LEAD_ONLY, note="aggregator"),
    Reviewed("UFO Insight", LEAD_ONLY, note="aggregator with commentary"),
    Reviewed("UFO Encounters", LEAD_ONLY, note="aggregator"),
    Reviewed("World of the Strange", LEAD_ONLY, note="aggregator across several subjects"),
    Reviewed("Saturday Night Uforia", LEAD_ONLY, note="historical essays; sourced but secondary"),
    Reviewed("UFO Theater", LEAD_ONLY, note="commentary"),
    Reviewed("UFO Panel", LEAD_ONLY, note="commentary"),
    Reviewed("UFO Joe", LEAD_ONLY, note="data visualisations built on NUFORC exports",
             independence_group=GROUP_NUFORC),
    Reviewed("What's up with UFOs?", LEAD_ONLY, note="commentary"),
    Reviewed("UPARS LA", LEAD_ONLY, note="local research group; little published material"),
    Reviewed("UFOevidence", LEAD_ONLY, note="a large but static aggregation"),
    Reviewed("Best UFO Evidence", LEAD_ONLY, note="a curated list of other people's cases"),
    # -- advocacy: a claimant with a stated objective -------------------------
    Reviewed(
        "Paradigm Research Group",
        LEAD_ONLY,
        "claimant_or_firsthand",
        "explicit disclosure lobbying; a claimant whose objective is stated, which is "
        "more honest than most, and still a claimant",
    ),
    Reviewed(
        "To the Stars... Academy (TTSA)",
        LEAD_ONLY,
        "claimant_or_firsthand",
        "a commercial entity making claims about its own material; the strongest actual "
        "position is worth recording and nothing here can corroborate it",
    ),
    # -- directories and guides: indexes, not sources --------------------------
    Reviewed("Best UFO Resources", DECLINED, note="a directory of sites, not a source"),
    Reviewed("Key OSINT UAP Resources", DECLINED, note="a directory"),
    Reviewed("UAP Guide", DECLINED, note="a guide to the subject; tertiary"),
    Reviewed("UAP Primer", DECLINED, note="an introduction; tertiary"),
    Reviewed("The 5 Observables", DECLINED, note="a framing device from TTSA material, not a source"),
    Reviewed("The UFO Investigator Starter Kit", DECLINED, note="a how-to"),
    Reviewed("UFO-UAP Connector", DECLINED, note="a directory"),
    Reviewed("UFOSINT", DECLINED, note="a methods guide"),
    Reviewed("UAP Tracker", DECLINED, note="an aggregating front-end"),
    Reviewed("UFO Timeline", DECLINED, note="a chronology compiled from secondary sources"),
    Reviewed("UAP - Scientific Research Blog", DECLINED, note="commentary on others' research"),
    Reviewed("UAP Theory", DECLINED, note="speculation; no evidentiary role in this model"),
    Reviewed("Educating Humanity", DECLINED, note="advocacy blog"),
    Reviewed("Evolve First", DECLINED, note="consciousness advocacy; not this topic's evidence"),
    Reviewed("The Mind Sublime", DECLINED, note="esoteric commentary"),
    Reviewed("Montalk.net", DECLINED, note="esoteric metaphysics; outside the evidence model entirely"),
    Reviewed("Cosmic Pluralism Studies", DECLINED, note="philosophical essays"),
    Reviewed("UFOs as wildlife", DECLINED, note="a single hypothesis argued at length; an inference"),
)


def by_verdict() -> dict[str, list[Reviewed]]:
    out: dict[str, list[Reviewed]] = {CANDIDATE: [], LEAD_ONLY: [], DECLINED: []}
    for entry in REVIEW:
        out[entry.verdict].append(entry)
    return out


def summary() -> dict[str, Any]:
    """What the pool can and cannot do against the four UAP slots."""
    grouped = by_verdict()
    candidates = grouped[CANDIDATE]
    buckets: dict[str, list[str]] = {}
    for entry in candidates:
        buckets.setdefault(entry.bucket, []).append(entry.name)
    lineages = sorted(
        {entry.independence_group for entry in REVIEW if entry.independence_group}
    )
    return {
        "reviewed": len(REVIEW),
        "candidates": len(candidates),
        "lead_only": len(grouped[LEAD_ONLY]),
        "declined": len(grouped[DECLINED]),
        "candidates_by_bucket": {
            bucket: sorted(names) for bucket, names in sorted(buckets.items())
        },
        "uap_slots_available": 4,
        "independence_groups": lineages,
        "derivation_note": (
            "NICAP, CUFOS and Project 1947 each hold Blue Book and 1947-wave material the "
            "others hold. That is a shared basis per document, recorded as a derivation "
            "link — not a shared publisher, and not an independence group."
        ),
        "finding": (
            f"{len(candidates)} of {len(REVIEW)} survive review for four slots. The field's "
            "strength here is not where it is usually looked for: the skeptical and forensic "
            "entries are the most extractable material in the list, because they name their "
            "sources and show their working, and an assertion that cannot be quoted against "
            "a span cannot be counted however true it is."
        ),
    }
