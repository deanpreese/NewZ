"""Proposed URLs pointing at material rather than front doors.

The first live survey found the role heuristic agreeing with the operator's own
review twice in ten, and the cause was not the heuristic. It was reading
homepages. A homepage is navigation: it describes what a publisher is, in the
publisher's own promotional voice, and says almost nothing about what kind of
evidence the pages underneath it carry. The word "archive" in a masthead made
two document collections look like historical context.

So each slot should point at the material — a case index, an article listing, an
issue archive, a document collection — and this proposes one per slot that does.

**These are proposals and several are guesses.** A path is proposed from what is
known about how these publishers organise their sites, which is not the same as
having looked. `CONFIDENCE` says which is which, and `survey()` is what turns a
proposal into a finding. A proposal presented at the same confidence as an
observation is how a plausible URL becomes a fact nobody checked.

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
OBSERVED = "observed"  # seen in the first survey, or a documented API
LIKELY = "likely"  # the publisher's conventional layout for this kind of page
GUESS = "guess"  # the shape is right; the exact path needs checking
BLOCKED = "blocked"  # no addressable text exists at any path


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
        confidence=LIKELY,
    ),
    Repoint(
        publisher="PubPeer",
        was="https://pubpeer.com/",
        now="https://pubpeer.com/recent",
        why="the recent-comments feed is the material; the root is a search box",
        confidence=LIKELY,
    ),
    Repoint(
        publisher="LENR-CANR",
        was="https://lenr-canr.org/",
        now="https://lenr-canr.org/wordpress/?page_id=952",
        why=(
            "the paper library rather than the front page — this is the claimant's "
            "strongest actual position, and the front page is its case for itself"
        ),
        confidence=GUESS,
    ),
    Repoint(
        publisher="Skeptical Inquirer (Center for Inquiry)",
        was="https://skepticalinquirer.org/",
        now="https://skepticalinquirer.org/articles/",
        why="the article index; the root is a magazine cover",
        confidence=LIKELY,
    ),
    Repoint(
        publisher="New Energy Times",
        was="https://newenergytimes.com/",
        now="https://newenergytimes.com/v2/news/news.shtml",
        why="the news index rather than the landing page",
        confidence=GUESS,
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
        confidence=LIKELY,
    ),
    Repoint(
        publisher="Royal Society Open Science",
        was="https://royalsocietypublishing.org/journal/rsos",
        now="https://royalsocietypublishing.org/toc/rsos/current",
        why="the current issue's table of contents rather than the journal's home",
        confidence=LIKELY,
    ),
    Repoint(
        publisher="Journal of Scientific Exploration",
        was="https://journalofscientificexploration.org/index.php/jse",
        now="https://journalofscientificexploration.org/index.php/jse/issue/archive",
        why="the issue archive; an OJS journal home is a masthead",
        confidence=LIKELY,
    ),
    Repoint(
        publisher="NOAA National Centers for Environmental Information",
        was="https://www.ncei.noaa.gov/access/monitoring/",
        now="https://www.ncei.noaa.gov/access/monitoring/monthly-report/",
        why="the monthly reports themselves rather than the monitoring index",
        confidence=GUESS,
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
        confidence=GUESS,
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


def report() -> dict[str, Any]:
    return {
        "proposals": [proposal.as_record() for proposal in PROPOSALS],
        "changed": len(changes()),
        "unchanged": len(PROPOSALS) - len(changes()),
        "guesses": [proposal.publisher for proposal in needs_checking()],
        "blocked": [proposal.publisher for proposal in blocked()],
        "note": (
            "Proposals, not findings. A survey is what makes one of these an "
            "observation, and until then a guess that reads like an address is "
            "still a guess."
        ),
    }
