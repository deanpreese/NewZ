"""Proposed URLs pointing at material rather than front doors.

The first live survey found the role heuristic agreeing with the operator's own
review twice in ten, and the cause was not the heuristic. It was reading
homepages. A homepage is navigation: it describes what a publisher is, in the
publisher's own promotional voice, and says almost nothing about what kind of
evidence the pages underneath it carry. The word "archive" in a masthead made
two document collections look like historical context.

So each slot should point at the material — a case index, an article listing, an
issue archive, a document collection — and this proposes one per slot that does.

**They were proposed, then surveyed.** Ten changed paths went through the
ordinary fetcher on 2026-09-05 and `SURVEY` records what came back. Six serve
what was claimed and four do not, and the labels moved with the evidence rather
than the evidence being read to fit them.

The labelling was worth having and was not very good. Two of the four failures
were marked `LIKELY` rather than `GUESS` — the Institute of Noetic Sciences'
publications page returned 404 and Royal Society Open Science answered 403 — so
"likely" was doing less work than it claimed. Two of the four guesses landed;
one of the two that did not was the one it mattered least to get right. A
confidence label is a claim about a claim, and this one was miscalibrated in the
direction that flatters the person making it.

**Two cannot be fixed by changing a path.** The USPTO's Patent Public Search and
NASA's ASRS database are both applications rather than documents: there is no
address that returns the material as text, because the material is assembled by
a script after the page loads. Those need a different endpoint or a different
source, and saying so is more use than proposing a path that will parse to
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: How far the proposal rests on knowing the site rather than guessing at it.
OBSERVED = "observed"  # fetched, and it serves what was claimed
LIKELY = "likely"  # the publisher's conventional layout for this kind of page
GUESS = "guess"  # the shape is right; the exact path needs checking
BLOCKED = "blocked"  # no addressable text exists at any path
REFUTED = "refuted"  # fetched, and it does not


@dataclass(frozen=True, slots=True)
class Repoint:
    publisher: str
    was: str
    now: str
    why: str
    confidence: str = LIKELY

    @property
    def changed(self) -> bool:
        return self.now != self.was

    def as_record(self) -> dict[str, Any]:
        return {
            "publisher": self.publisher,
            "was": self.was,
            "now": self.now,
            "why": self.why,
            "confidence": self.confidence,
            "changed": self.changed,
        }


#: What the fetcher actually got, 2026-09-05. Recorded because the proposals
#: above were written from what these publishers usually do, and this is the
#: thing that checked them.
SURVEY: dict[str, Any] = {
    "when": "2026-09-05",
    "surveyed": 10,
    "confirmed": 6,
    "refuted_count": 4,
    "serves_what_was_claimed": {
        "CIA FOIA Electronic Reading Room (CREST)": "49 segments, text/html — the STARGATE collection reads",
        "LENR-CANR": "175 segments — the richest page in the slate, and it was a guess",
        "Journal of Scientific Exploration": "79 segments — the issue archive reads",
        "NASA Aviation Safety Reporting System": "38 segments — the report sets are documents after all",
        "NOAA National Centers for Environmental Information": "13 segments from 508 KB — reads, but thin for its size",
        "PubPeer": "7 segments from 26 KB — reads, and barely: the feed is assembled client-side",
    },
    "does_not": {
        "Institute of Noetic Sciences": "404. /research/publications/ does not exist; the section page it replaced does",
        "Royal Society Open Science": "403. robots.txt permits both paths and the server declines anyway",
        "New Energy Times": "334 bytes, 0 segments. The path resolves and holds nothing",
        "Skeptical Inquirer (Center for Inquiry)": "robots.txt disallows it — and disallows everything",
    },
    "findings": [
        "Skeptical Inquirer disallows `/` as well as `/articles/`, so the URL already "
        "in the slate is one this system may never read. It was added before the "
        "robots check existed and has never been fetched under it. That slot is "
        "effectively open, the same way the one NUFORC vacated is — and it was open "
        "before this survey, silently.",
        "Royal Society Open Science is a fourth source declining the agent, and a new "
        "kind: robots.txt permits the path and the server refuses anyway. A site's "
        "stated rules and its enforced ones are different facts, and only the second "
        "one is discoverable by asking.",
        "Pointing a slot at its material made the role heuristic worse before it made "
        "it better. The Journal of Scientific Exploration's issue archive was proposed "
        "as historical context because the word 'archive' was in the body — an "
        "empirical journal read as a history shelf. Material listings are archives, so "
        "the better the URL the more often that fired. The marker now has to name a "
        "kind of record rather than a way of organising a page.",
        "Two pages parse thin: PubPeer's feed and NOAA's monthly report are assembled "
        "client-side, so a fetch gets the frame and not the contents. They are "
        "readable rather than useful, which the segment count says and the status "
        "code does not.",
    ],
}


PROPOSALS: tuple[Repoint, ...] = (
    # ---- front doors, which is the whole problem ---------------------------
    Repoint(
        publisher="CIA FOIA Electronic Reading Room (CREST)",
        was="https://www.cia.gov/readingroom/",
        now="https://www.cia.gov/readingroom/collection/stargate",
        why=(
            "the reading room root is a search form; STARGATE is a named collection "
            "of the declassified programme records themselves, and it is the "
            "collection this portfolio actually needs — psi claims assessed by the "
            "agency that funded them"
        ),
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="PubPeer",
        was="https://pubpeer.com/",
        now="https://pubpeer.com/recent",
        why="the recent-comments feed is the material; the root is a search box",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="LENR-CANR",
        was="https://lenr-canr.org/",
        now="https://lenr-canr.org/wordpress/?page_id=952",
        why=(
            "the paper library rather than the front page — this is the claimant's "
            "strongest actual position, and the front page is its case for itself"
        ),
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="Skeptical Inquirer (Center for Inquiry)",
        was="https://skepticalinquirer.org/",
        now="https://skepticalinquirer.org/articles/",
        why="the article index; the root is a magazine cover",
        confidence=REFUTED,
    ),
    Repoint(
        publisher="New Energy Times",
        was="https://newenergytimes.com/",
        now="https://newenergytimes.com/v2/news/news.shtml",
        why="the news index rather than the landing page",
        confidence=REFUTED,
    ),
    # ---- section pages: better than a root, still not the material ---------
    Repoint(
        publisher="Institute of Noetic Sciences",
        was="https://noetic.org/research/",
        now="https://noetic.org/research/publications/",
        why=(
            "the publications listing rather than the research overview: the "
            "overview describes a programme, the listing carries the papers"
        ),
        confidence=REFUTED,
    ),
    Repoint(
        publisher="Royal Society Open Science",
        was="https://royalsocietypublishing.org/journal/rsos",
        now="https://royalsocietypublishing.org/toc/rsos/current",
        why="the current issue's table of contents rather than the journal's home",
        confidence=REFUTED,
    ),
    Repoint(
        publisher="Journal of Scientific Exploration",
        was="https://journalofscientificexploration.org/index.php/jse",
        now="https://journalofscientificexploration.org/index.php/jse/issue/archive",
        why="the issue archive; an OJS journal home is a masthead",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="NOAA National Centers for Environmental Information",
        was="https://www.ncei.noaa.gov/access/monitoring/",
        now="https://www.ncei.noaa.gov/access/monitoring/monthly-report/",
        why="the monthly reports themselves rather than the monitoring index",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="Wikipedia",
        was="https://en.wikipedia.org/wiki/Category:UFOs",
        now="https://en.wikipedia.org/wiki/Category:UFOs",
        why=(
            "left alone. A category is navigation, but for this slot navigation is "
            "the point: the role is general context and the value is the spread of "
            "articles, not any one of them. Repointing it at a single article would "
            "narrow the slot rather than sharpen it"
        ),
        confidence=OBSERVED,
    ),
    # ---- already pointing at material -------------------------------------
    Repoint(
        publisher="Jason Colavito",
        was="https://www.jasoncolavito.com/blog",
        now="https://www.jasoncolavito.com/blog",
        why="already a listing of the material",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="Metabunk",
        was="https://www.metabunk.org/forums/ufos-and-aliens.31/",
        now="https://www.metabunk.org/forums/ufos-and-aliens.31/",
        why="already the thread index for the relevant forum",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="The Conversation",
        was="https://theconversation.com/us/technology",
        now="https://theconversation.com/us/technology",
        why="already a section listing",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="PLOS ONE",
        was="https://journals.plos.org/plosone/browse/paleontology_and_paleobiology",
        now="https://journals.plos.org/plosone/browse/paleontology_and_paleobiology",
        why="already a subject browse listing",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="Information Security Oversight Office (NARA)",
        was="https://www.archives.gov/isoo/reports",
        now="https://www.archives.gov/isoo/reports",
        why="already the reports index",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="National Institute of Standards and Technology",
        was="https://www.nist.gov/publications",
        now="https://www.nist.gov/publications",
        why="already the publications listing",
        confidence=OBSERVED,
    ),
    Repoint(
        publisher="Crossref",
        was="https://api.crossref.org/works",
        now="https://api.crossref.org/works",
        why=(
            "already an API endpoint returning the records themselves. It needs a "
            "query to be useful, which is a lane's business rather than the "
            "catalogue's"
        ),
        confidence=OBSERVED,
    ),
    # ---- not a path problem ------------------------------------------------
    Repoint(
        publisher="United States Patent and Trademark Office",
        was="https://ppubs.uspto.gov/pubwebapp/",
        now="https://ppubs.uspto.gov/pubwebapp/",
        why=(
            "Patent Public Search is an application, not a document: the results are "
            "assembled by a script after the page loads, so no path returns the "
            "material as text. This needs the Open Data API or a different primary "
            "source for filings, and it is a source decision rather than a URL fix"
        ),
        confidence=BLOCKED,
    ),
    Repoint(
        publisher="NASA Aviation Safety Reporting System",
        was="https://asrs.arc.nasa.gov/search/database.html",
        now="https://asrs.arc.nasa.gov/search/reportsets.html",
        why=(
            "the database page is a search application; the published report sets "
            "are files that exist at an address. Weaker than a query but readable, "
            "which is the difference between a source and an intention"
        ),
        confidence=OBSERVED,
    ),
)


def by_publisher() -> dict[str, Repoint]:
    return {proposal.publisher: proposal for proposal in PROPOSALS}


def changes() -> tuple[Repoint, ...]:
    return tuple(proposal for proposal in PROPOSALS if proposal.changed)


def blocked() -> tuple[Repoint, ...]:
    return tuple(proposal for proposal in PROPOSALS if proposal.confidence == BLOCKED)


def needs_checking() -> tuple[Repoint, ...]:
    """The ones that are guesses, and should be read before they are believed."""
    return tuple(proposal for proposal in PROPOSALS if proposal.confidence == GUESS)


def refuted() -> tuple[Repoint, ...]:
    """Proposed, fetched, and wrong. Not to be applied."""
    return tuple(proposal for proposal in PROPOSALS if proposal.confidence == REFUTED)


def applicable() -> tuple[Repoint, ...]:
    """The changes the survey supports: fetched, and serving what was claimed."""
    return tuple(
        proposal
        for proposal in PROPOSALS
        if proposal.changed and proposal.confidence == OBSERVED
    )


def report() -> dict[str, Any]:
    return {
        "proposals": [proposal.as_record() for proposal in PROPOSALS],
        "changed": len(changes()),
        "unchanged": len(PROPOSALS) - len(changes()),
        "guesses": [proposal.publisher for proposal in needs_checking()],
        "blocked": [proposal.publisher for proposal in blocked()],
        "refuted": [proposal.publisher for proposal in refuted()],
        "applicable": [proposal.publisher for proposal in applicable()],
        "survey": SURVEY,
        "note": (
            "Surveyed on 2026-09-05. Six of the ten changes serve what was claimed "
            "and are applicable; four do not and are kept, labelled refuted, because "
            "a proposal that was checked and failed is more use than one that "
            "quietly disappeared."
        ),
    }
