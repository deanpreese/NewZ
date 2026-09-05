"""The local surface: where cleared output actually lands.

A directory of rendered revisions plus an index. It exists so that confirmation
means something. `SPEC.md` section 10 requires a publication, a correction and a
retraction each to record whether the effect was **confirmed from evidence
outside the renderer's own report**, and a renderer that returns True is not
that evidence. The confirmation path here reads the directory back: the file is
there and holds this revision's hash, or the surface is not serving it whatever
the renderer said.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LocalSurface:
    root: Path

    @property
    def pages(self) -> Path:
        return self.root / "pages"

    @property
    def index_path(self) -> Path:
        return self.root / "index.json"

    def page_path(self, claim_id: str) -> Path:
        return self.pages / f"{claim_id.replace(':', '_')}.json"

    def serve(self, claim_id: str, revision_id: str, content_hash: str, body: dict) -> Path:
        self.pages.mkdir(parents=True, exist_ok=True)
        path = self.page_path(claim_id)
        path.write_text(
            json.dumps(
                {"revision_id": revision_id, "content_hash": content_hash, "card": body},
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        self._reindex()
        return path

    def withdraw(self, claim_id: str, tombstone: dict) -> None:
        """Remove the presentation from navigation and leave the tombstone."""
        path = self.page_path(claim_id)
        if path.exists():
            path.unlink()
        (self.pages / f"{claim_id.replace(':', '_')}.tombstone.json").write_text(
            json.dumps(tombstone, sort_keys=True, indent=2), encoding="utf-8"
        )
        self._reindex()

    def attach_correction(self, claim_id: str, notice: dict) -> None:
        """A correction stays visibly attached to the output it corrects."""
        path = self.page_path(claim_id)
        if not path.exists():
            return
        document = json.loads(path.read_text(encoding="utf-8"))
        document.setdefault("corrections", []).append(notice)
        path.write_text(json.dumps(document, sort_keys=True, indent=2), encoding="utf-8")

    # -- the reading half, which is the half that confirms ------------------

    def serving(self, claim_id: str) -> dict | None:
        path = self.page_path(claim_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def serves_revision(self, claim_id: str, content_hash: str) -> bool:
        document = self.serving(claim_id)
        return bool(document) and document.get("content_hash") == content_hash

    def in_navigation(self, claim_id: str) -> bool:
        index = self.index()
        return any(entry["claim_id"] == claim_id for entry in index)

    def has_tombstone(self, claim_id: str) -> bool:
        return (self.pages / f"{claim_id.replace(':', '_')}.tombstone.json").exists()

    def corrections_on(self, claim_id: str) -> list[dict]:
        document = self.serving(claim_id)
        return list(document.get("corrections", [])) if document else []

    def index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _reindex(self) -> None:
        entries = []
        for path in sorted(self.pages.glob("*.json")):
            if path.name.endswith(".tombstone.json"):
                continue
            document = json.loads(path.read_text(encoding="utf-8"))
            card = document["card"]
            entries.append(
                {
                    "claim_id": card["claim_id"],
                    "revision_id": document["revision_id"],
                    "state": card["state"],
                    "risk": card["risk"],
                    "wording": card["wording"],
                }
            )
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(entries, sort_keys=True, indent=2), encoding="utf-8"
        )
