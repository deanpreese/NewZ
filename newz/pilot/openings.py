"""Candidates for the three slots the slate cannot fill from itself.

Three prescribed slots have no source: claimant on UAP, vacated when NUFORC
declined the agent; empirical on forteana, vacated when Royal Society Open
Science refused a path its own robots.txt permits; and skeptical on psi, vacated
when the Skeptical Inquirer turned out to disallow every path including the one
the slate already held.

The last of those is the one that matters. Psi is one of only three topics the
prescription gives a skeptical source at all, so while that slot is open the
diet has nothing able to contradict a psi claim, and `seeds.gaps()` reports the
topic as unopposed for exactly that reason.

**Proposed, then surveyed.** Nine candidates went through the ordinary fetcher on
2026-09-05 and five more roots after that. Everything here says what came back
rather than what was hoped for.

**Four of the nine first paths were 404s, and all four were mine.** A 404 is a
wrong guess about how a publisher organises its site; a 403 is the publisher
answering. Probing the roots separated them, and three of the four sites were
reachable all along — which is the same lesson the URL repointing produced, in
the same week, from the same habit of proposing a path and reading it back as a
finding.

**Nothing here is chosen.** Which source speaks for a topic is a diet decision.
These are surveyed candidates with a recommendation and the reason for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REACHED = "reached"
DECLINED = "declined"  # the publisher answered 403
WRONG_PATH = "wrong_path"  # a 404: a guess about the site, not the site's answer


@dataclass(frozen=True, slots=True)
class Surveyed:
    publisher: str
    url: str
    slot: str
    outcome: str
    segments: int = 0
    note: str = ""
    recommended: bool = False

    def as_record(self) -> dict[str, Any]:
        return {
            "publisher": self.publisher,
            "url": self.url,
            "slot": self.slot,
            "outcome": self.outcome,
            "segments": self.segments,
            "note": self.note,
            "recommended": self.recommended,
        }


CLAIMANT_UAP = "claimant_or_firsthand/uap_and_aerospace_anomalies"
EMPIRICAL_FORTEANA = "empirical_or_replication/forteana_cryptids_and_anomalous_natural_events"
SKEPTICAL_PSI = "skeptical_or_forensic/psi_and_consciousness_claims"

CANDIDATES: tuple[Surveyed, ...] = (
    # ---- claimant on UAP --------------------------------------------------
    Surveyed(
        "NARCAP",
        "https://www.narcap.org/",
        CLAIMANT_UAP,
        REACHED,
        17,
        note=(
            "aviation-witness reports: pilots and controllers describing what they "
            "saw, which is firsthand testimony from witnesses with instrument "
            "context. A distinct basis from the sighting-report databases, and the "
            "closest thing to what the dropped NUFORC slot held"
        ),
        recommended=True,
    ),
    Surveyed(
        "BUFORA",
        "https://www.bufora.org.uk/",
        CLAIMANT_UAP,
        REACHED,
        56,
        note="the British counterpart; case files from a distinct investigating body",
    ),
    Surveyed("MUFON", "https://mufon.com/mufon-case-management-system/", CLAIMANT_UAP, DECLINED,
             note="403, and its terms already said all rights reserved"),
    Surveyed("NARCAP", "https://www.narcap.org/reports", CLAIMANT_UAP, WRONG_PATH,
             note="404: a guess at the path, not an answer from the site"),
    Surveyed("BUFORA", "https://www.bufora.org.uk/case-files/", CLAIMANT_UAP, WRONG_PATH,
             note="404: the root reads fine"),
    # ---- empirical on forteana --------------------------------------------
    Surveyed(
        "Biodiversity Data Journal",
        "https://bdj.pensoft.net/articles",
        EMPIRICAL_FORTEANA,
        REACHED,
        84,
        note=(
            "open-access, and the place a cryptid claim actually resolves: a new "
            "large vertebrate is either described here or it is not described. An "
            "article listing rather than a front door, and the richest of the three"
        ),
        recommended=True,
    ),
    Surveyed("PeerJ", "https://peerj.com/sections/zoological-science/", EMPIRICAL_FORTEANA,
             REACHED, 5,
             note="reads, but five segments: the listing is assembled client-side"),
    Surveyed("Royal Meteorological Society (Weather)",
             "https://rmets.onlinelibrary.wiley.com/journal/14778696", EMPIRICAL_FORTEANA,
             DECLINED, note="403, like the other Wiley-hosted journal already dropped"),
    # ---- skeptical on psi --------------------------------------------------
    Surveyed(
        "NeuroLogica",
        "https://theness.com/neurologicablog/",
        SKEPTICAL_PSI,
        REACHED,
        390,
        note=(
            "sustained skeptical writing on parapsychology by a working "
            "neurologist, and the richest page surveyed anywhere in this slate. "
            "One author rather than an institution, which is a narrower basis than "
            "the slot lost and is the trade being proposed"
        ),
        recommended=True,
    ),
    Surveyed(
        "The Skeptic (UK)",
        "https://www.skeptic.org.uk/",
        SKEPTICAL_PSI,
        REACHED,
        207,
        note=(
            "an editorial magazine rather than one author, so a broader basis. "
            "Its independence from the dropped Skeptical Inquirer is worth "
            "establishing before it is preferred, not assumed from the country"
        ),
    ),
    Surveyed("The Skeptic's Dictionary", "https://skepdic.com/", SKEPTICAL_PSI, REACHED, 114,
             note="reference rather than investigation, and largely unmaintained since 2015"),
    Surveyed("Center for Inquiry (blog)", "https://centerforinquiry.org/blog/", SKEPTICAL_PSI,
             DECLINED,
             note="403 — the same publisher as the Skeptical Inquirer, which is consistent"),
    Surveyed("The Skeptic (UK)", "https://www.skeptic.org.uk/articles/", SKEPTICAL_PSI,
             WRONG_PATH, note="404: the root reads fine"),
    Surveyed("The Skeptic's Dictionary", "https://skepdic.com/tialpha.html", SKEPTICAL_PSI,
             WRONG_PATH, note="404"),
)

SLOTS = (CLAIMANT_UAP, EMPIRICAL_FORTEANA, SKEPTICAL_PSI)


def for_slot(slot: str) -> tuple[Surveyed, ...]:
    return tuple(c for c in CANDIDATES if c.slot == slot)


def recommended() -> dict[str, Surveyed]:
    return {c.slot: c for c in CANDIDATES if c.recommended}


def reachable(slot: str = "") -> tuple[Surveyed, ...]:
    return tuple(
        c for c in CANDIDATES if c.outcome == REACHED and (not slot or c.slot == slot)
    )


def report() -> dict[str, Any]:
    return {
        "slots": list(SLOTS),
        "surveyed": len(CANDIDATES),
        "reached": len(reachable()),
        "declined": [c.publisher for c in CANDIDATES if c.outcome == DECLINED],
        "wrong_path": [f"{c.publisher} {c.url}" for c in CANDIDATES if c.outcome == WRONG_PATH],
        "recommended": {slot: c.as_record() for slot, c in recommended().items()},
        "findings": [
            "Every 404 was a guess about how a publisher organises its site, and "
            "every one of those sites read fine at its root. A 404 is our error and "
            "a 403 is their answer, and the two must not be reported alike.",
            "The recommended candidate for psi is one author rather than an "
            "institution. That is a narrower basis than the slot lost, and it is the "
            "trade being proposed rather than an equivalent replacement.",
            "Two of the three recommendations still point at a root or a listing "
            "root. Which source speaks for a topic is decided first; where in the "
            "site to read it is refinement after, and the survey is what settles it.",
        ],
        "note": (
            "Surveyed, not chosen. Enabling a source is a diet decision and the "
            "operator's; `review()` still refuses a slate whose slots cannot state "
            "their retention terms, and none of these have been read for terms."
        ),
    }
