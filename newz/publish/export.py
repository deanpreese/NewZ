"""Export: the record, portable and checkable, without a model provider.

`SPEC.md` section 13 requires core data to export to documented, non-proprietary
formats, and names what core data includes. Everything here is JSON and raw
bytes; nothing needs this codebase to be read, and the manifest's checksums let
somebody else verify they got what the manifest says they got.

The exported artifacts are the retained bytes themselves. An export that carried
only the claims would be an export of the conclusions, and the whole argument of
this system is that a conclusion without its artifact is an assertion.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from newz.canonical import dumps
from newz.policy.bundle import BUNDLE
from newz.present.cards import claim_card
from newz.publish.browse import assessment_history_of
from newz.store.db import Store
from newz.version import CODE_VERSION, POLICY_VERSION

EXPORT_FORMAT = "newz-export/1"


@dataclass(frozen=True, slots=True)
class ExportManifest:
    root: Path
    claims: tuple[str, ...]
    artifacts: tuple[str, ...]
    checksums: dict[str, str]

    def as_record(self) -> dict[str, Any]:
        return {
            "format": EXPORT_FORMAT,
            "policy_version": POLICY_VERSION,
            "code_version": CODE_VERSION,
            "policy_digest": BUNDLE.digest,
            "claims": list(self.claims),
            "artifacts": list(self.artifacts),
            "checksums": dict(sorted(self.checksums.items())),
        }


def _write(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def export_claims(store: Store, destination: Path, claim_ids: list[str]) -> ExportManifest:
    """Export these claims with everything under them."""
    destination.mkdir(parents=True, exist_ok=True)
    checksums: dict[str, str] = {}
    artifacts: set[str] = set()

    for claim_id in sorted(claim_ids):
        record: dict[str, Any] = {
            "claim": dict(store.one("SELECT * FROM claims WHERE id = ?", claim_id) or {}),
            "assessments": assessment_history_of(store, claim_id),
            "edges": [
                dict(row)
                for row in store.query(
                    "SELECT * FROM edge_events WHERE claim_id = ? ORDER BY id", claim_id
                )
            ],
            "tasks": [
                dict(row)
                for row in store.query(
                    "SELECT * FROM tasks WHERE claim_id = ? ORDER BY id", claim_id
                )
            ],
            "origins": [
                dict(row)
                for row in store.query(
                    "SELECT * FROM claim_origins WHERE claim_id = ? ORDER BY extraction_run_id",
                    claim_id,
                )
            ],
        }
        assertion_ids = sorted({edge["assertion_id"] for edge in record["edges"]})
        record["assertions"] = []
        for assertion_id in assertion_ids:
            row = store.one("SELECT * FROM assertions WHERE id = ?", assertion_id)
            if row is None:
                continue
            record["assertions"].append(dict(row))
            artifacts.add(row["artifact_id"])
        record["bases"] = [
            dict(row)
            for row in store.query(
                "SELECT * FROM bases WHERE id IN "
                f"({','.join('?' * len(record['edges'])) or 'NULL'}) ORDER BY id",
                *[edge["basis_id"] for edge in record["edges"]],
            )
        ]
        try:
            record["card"] = claim_card(store, claim_id).as_record()
        except ValueError:
            record["card"] = None

        name = f"claims/{claim_id.replace(':', '_')}.json"
        checksums[name] = _write(destination / name, record)

    # The retained bytes themselves, not a description of them.
    for artifact_id in sorted(artifacts):
        row = store.one("SELECT * FROM artifacts WHERE id = ?", artifact_id)
        if row is None:
            continue
        source = store.artifact_root / row["stored_path"]
        if not source.exists():
            continue
        name = f"artifacts/{row['content_hash']}"
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        checksums[name] = row["content_hash"]

    checksums["policy/bundle.json"] = _write(
        destination / "policy/bundle.json", json.loads(dumps(BUNDLE.as_record()))
    )

    manifest = ExportManifest(
        root=destination,
        claims=tuple(sorted(claim_ids)),
        artifacts=tuple(sorted(artifacts)),
        checksums=checksums,
    )
    _write(destination / "manifest.json", manifest.as_record())
    return manifest


def export_corpus(store: Store, destination: Path) -> ExportManifest:
    claim_ids = [row["id"] for row in store.query("SELECT id FROM claims ORDER BY id")]
    return export_claims(store, destination, claim_ids)


def verify_export(destination: Path) -> tuple[bool, tuple[str, ...]]:
    """Check an export against its own manifest, without this codebase's help."""
    manifest_path = destination / "manifest.json"
    if not manifest_path.exists():
        return False, ("no manifest",)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for name, expected in sorted(manifest["checksums"].items()):
        path = destination / name
        if not path.exists():
            problems.append(f"missing: {name}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            problems.append(f"checksum mismatch: {name}")
    return not problems, tuple(problems)
