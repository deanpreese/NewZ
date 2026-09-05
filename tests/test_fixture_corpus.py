"""The hostile fixture corpus.

Phase 0 has no fetcher and no parser, so what it can assert about the corpus is
that it exists, that it covers every category the plan names, and that it is
byte-stable. A fixture that drifts silently is not a regression test.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

CORPUS = Path(__file__).parent / "fixtures" / "corpus"
MANIFEST = json.loads((CORPUS / "manifest.json").read_text(encoding="utf-8"))
FILES = MANIFEST["files"]

REQUIRED_CATEGORIES = {
    "claimant_and_witness",
    "copied_article",
    "prompt_injection",
    "malformed",
    "primary_record",
    "adjudicative_record",
    "empirical",
    "retraction",
    "conflicting_evidence",
    "patent",
    "complaint",
}

REQUIRED_FORMATS = {"html", "pdf", "structured", "text"}


def test_the_corpus_covers_every_category_the_plan_names():
    assert {f["category"] for f in FILES} >= REQUIRED_CATEGORIES
    assert {f["format"] for f in FILES} == REQUIRED_FORMATS


@pytest.mark.parametrize("entry", FILES, ids=[f["path"] for f in FILES])
def test_fixture_is_present_and_byte_stable(entry):
    data = (CORPUS / entry["path"]).read_bytes()
    assert len(data) == entry["bytes"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]


@pytest.mark.parametrize("entry", FILES, ids=[f["path"] for f in FILES])
def test_every_fixture_says_what_it_is_for(entry):
    assert entry["purpose"]


def test_no_file_in_the_corpus_is_unlisted():
    on_disk = {
        str(p.relative_to(CORPUS))
        for p in CORPUS.rglob("*")
        if p.is_file() and p.name not in ("manifest.json", "_generate.py")
    }
    assert on_disk == {f["path"] for f in FILES}


def test_the_injection_fixture_really_does_try_to_instruct():
    """It must carry the shapes the model boundary has to survive: an instruction,
    an authority claim, a false prior approval, and a request not to be surfaced."""
    text = (CORPUS / "html/prompt_injection.html").read_text(encoding="utf-8").lower()
    for marker in (
        "ignore all previous instructions",
        "authority",
        "already\n  approved",
        "do not surface",
    ):
        assert marker in text, marker


def test_the_copied_article_carries_the_same_quotation_as_its_origin():
    """This is what makes it a copy rather than a second witness."""
    origin = (CORPUS / "html/witness_report.html").read_text(encoding="utf-8")
    copy = (CORPUS / "html/syndicated_copy.html").read_text(encoding="utf-8")
    quote = "It held station off the right wing, then left on a vector we could not\n  match"
    assert quote in origin
    assert quote.replace("\n  ", "\n  ") in copy
