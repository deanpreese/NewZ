"""The Gate 6 drills that can be run rather than attested.

`PLAN.md` Gate 6 asks for production service objectives, a security review, a
disaster-recovery drill, policy replay and a public correction drill. Two of
those are judgments and one is a commitment; the other three are procedures, and
a procedure that has never been executed is a plan.

So they are executable here, and they are deliberately unkind:

- **Policy replay** re-derives each claim's current assessment from the ledger
  and compares it byte for byte. A divergence is not a replay failure but a
  claim finding: the conclusion on the card no longer follows from the evidence
  under it, and the claim owes a reassessment nobody performed. It refuses to
  replay under a policy or code version other than the one an assessment was
  derived under, because deriving under different rules and calling agreement
  reproduction would report success loudest where the drift was worst.
- **The restore drill** takes a backup, opens it as a store in its own right,
  and rebuilds every claim card and assessment history from it. `PLAN.md` is
  explicit that verifying the service starts is not the drill.
- **The correction drill** publishes, corrects, and confirms the correction by
  reading the surface rather than the renderer's report, within the window.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from newz.canonical import dumps
from newz.evidence.assess import assessment_history, evidence_input, load_assessment
from newz.policy.bundle import BUNDLE
from newz.policy.promotion import assess
from newz.store.backup import back_up, restore_and_verify
from newz.store.db import Store
from newz.version import CODE_VERSION


@dataclass(frozen=True, slots=True)
class DrillResult:
    name: str
    passed: bool
    detail: str = ""
    findings: tuple[str, ...] = field(default_factory=tuple)

    def as_record(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "findings": list(self.findings),
        }


# ---------------------------------------------------------------------------
# What a policy version contained
# ---------------------------------------------------------------------------


def record_policy_version(store: Store) -> str:
    """Record what the running policy version contains, once."""
    existing = store.one("SELECT digest FROM policy_versions WHERE version = ?", BUNDLE.version)
    if existing is not None:
        return existing["digest"]
    with store.write() as connection:
        connection.execute(
            "INSERT INTO policy_versions (version, digest, code_version, recorded_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (BUNDLE.version, BUNDLE.digest, CODE_VERSION),
        )
    return BUNDLE.digest


def policy_drift(store: Store) -> tuple[str, ...]:
    """Recorded versions whose content no longer matches what the code produces.

    The failure this catches is a policy edited without a version bump. Every
    assessment derived under that string would then cite rules that no longer
    exist, and would replay against the wrong ones while reporting success —
    the drift is invisible precisely because the version says nothing changed.
    """
    drifted = []
    for row in store.query("SELECT version, digest FROM policy_versions ORDER BY version"):
        if row["version"] == BUNDLE.version and row["digest"] != BUNDLE.digest:
            drifted.append(
                f"policy {row['version']} was recorded as {row['digest'][:12]} but the code "
                f"now produces {BUNDLE.digest[:12]}: the version was not bumped with the change"
            )
    return tuple(drifted)


# ---------------------------------------------------------------------------
# Policy replay
# ---------------------------------------------------------------------------


def policy_replay(store: Store) -> DrillResult:
    """Re-derive each claim's current assessment from the ledger and compare it.

    Only the current one. An edge is admitted once and immutably, but its
    liveness is a mutable projection over that log, so the graph as it stood at
    an earlier derivation cannot be rebuilt without a snapshot nothing takes.
    Replaying a superseded assessment against today's edges would compare two
    different questions and report the difference as a defect.
    """
    findings: list[str] = list(policy_drift(store))
    drifted = bool(findings)
    reproduced = 0
    diverged: list[str] = []
    unreplayable: list[str] = []

    for row in store.query(
        "SELECT id, claim_id, policy_version, code_version, horizon_reached FROM assessments a "
        "WHERE a.rowid = (SELECT MAX(b.rowid) FROM assessments b WHERE b.claim_id = a.claim_id) "
        "ORDER BY claim_id"
    ):
        if row["policy_version"] != BUNDLE.version or row["code_version"] != CODE_VERSION:
            # Honest rather than convenient. Replaying an assessment derived
            # under a superseded policy needs that policy's bundle, and this
            # store holds only the running one.
            unreplayable.append(
                f"{row['id']}: derived under policy {row['policy_version']} / "
                f"code {row['code_version']}, running {BUNDLE.version} / {CODE_VERSION}"
            )
            continue
        stored = load_assessment(store, row["id"])
        again = assess(
            evidence_input(store, row["claim_id"], horizon_reached=bool(row["horizon_reached"])),
            row["policy_version"],
        )
        if dumps(again) == dumps(stored):
            reproduced += 1
        else:
            diverged.append(f"{row['claim_id']}: {_first_difference(stored, again)}")

    # A divergence is a claim finding, not a replay failure: the rules did not
    # change, the evidence did, and the card on the surface is still showing a
    # conclusion the ledger no longer supports.
    findings.extend(
        f"owes a reassessment, its current one no longer follows — {item}" for item in diverged
    )
    findings.extend(f"needs its own policy bundle: {item}" for item in unreplayable)
    return DrillResult(
        name="policy_replay",
        passed=not drifted and not diverged,
        detail=(
            f"{reproduced} reproduced, {len(diverged)} owe a reassessment, "
            f"{len(unreplayable)} not replayable under the running policy"
        ),
        findings=tuple(findings),
    )


def _first_difference(stored, again) -> str:
    """Name the field that moved, so a divergence is a lead rather than a diff."""
    left, right = stored.as_record(), again.as_record()
    for key in sorted(left):
        if dumps(left[key]) != dumps(right.get(key)):
            return f"{key}: stored {dumps(left[key])}, replayed {dumps(right.get(key))}"
    return "identical fields but different serialization"


# ---------------------------------------------------------------------------
# Disaster recovery
# ---------------------------------------------------------------------------


def restore_drill(
    store: Store, destination: Path, keys_root: Path | None = None
) -> DrillResult:
    """Back up, restore into a clean room, and rebuild everything from the copy.

    `PLAN.md`: the drill verifies byte-exact reproduction of claim cards,
    histories and artifact hashes, not that the service starts.

    Refuses before copying anything if the subject keys sit where a backup would
    pick them up, because the interesting failure is not a bad backup — it is a
    good one that carries the keys erasure destroyed.
    """
    from newz.present.cards import claim_card

    misplaced = _keys_inside_the_backup_set(store, keys_root)
    if misplaced:
        return DrillResult(
            name="restore_drill",
            passed=False,
            detail="refused before taking a backup",
            findings=(misplaced,),
        )

    if destination.exists():
        shutil.rmtree(destination)
    back_up(store, destination)

    claim_ids = [
        row["claim_id"]
        for row in store.query("SELECT DISTINCT claim_id FROM assessments ORDER BY claim_id")
    ]
    live_cards = {claim_id: claim_card(store, claim_id).content_hash for claim_id in claim_ids}
    live_histories = {
        claim_id: dumps(assessment_history(store, claim_id)) for claim_id in claim_ids
    }

    restored, report = restore_and_verify(destination, store.path.name)
    findings: list[str] = []
    try:
        if not report.ok:
            findings.extend(str(line) for line in report.integrity)
            findings.extend(str(line) for line in report.foreign_keys)
            findings.extend(f"missing artifact: {i}" for i in report.missing_artifacts)
            findings.extend(f"corrupted artifact: {i}" for i in report.corrupted_artifacts)
        for claim_id, content_hash in live_cards.items():
            if claim_card(restored, claim_id).content_hash != content_hash:
                findings.append(f"claim card differs after restore: {claim_id}")
        for claim_id, history in live_histories.items():
            if dumps(assessment_history(restored, claim_id)) != history:
                findings.append(f"assessment history differs after restore: {claim_id}")

        # `back_up` copies the database and the artifact tree, so a key
        # directory sitting inside either one travels with them. The first draft
        # of this check scanned the finished backup for key files, which can
        # never fire: the drill wipes the destination before writing it. Where
        # the keys live is the property that decides, so it is checked here.
        keys_in_backup = [path for path in destination.rglob("*.key")]
        if keys_in_backup:
            findings.append(
                f"{len(keys_in_backup)} subject key(s) came through in the backup: restoring "
                "it would un-erase every subject erased since it was taken"
            )
        detail = (
            f"{len(live_cards)} claim cards and histories rebuilt from the restored store; "
            f"{report.counts.get('artifacts', 0)} artifact hashes verified"
        )
    finally:
        restored.close()

    return DrillResult(
        name="restore_drill", passed=not findings, detail=detail, findings=tuple(findings)
    )


def _keys_inside_the_backup_set(store: Store, keys_root: Path | None) -> str:
    """Whether the key directory is somewhere `back_up` would copy it from."""
    if keys_root is None:
        return ""
    keys = keys_root.resolve()
    # Precisely what `back_up` copies, and nothing more. Checking the database's
    # whole directory instead would condemn every ordinary layout that keeps the
    # keys as a sibling of the database, which the backup never touches.
    try:
        keys.relative_to(store.artifact_root.resolve())
    except ValueError:
        return ""
    return (
        f"the subject keys are inside the artifact tree ({keys}), so every backup carries "
        "them: restoring one would un-erase every subject erased since it was taken"
    )


# ---------------------------------------------------------------------------
# Public correction
# ---------------------------------------------------------------------------


def correction_drill(
    store: Store,
    surface,
    *,
    claim_id: str,
    card_revision_id: str,
    now: datetime,
    confirmed_at: datetime | None = None,
) -> DrillResult:
    """Correct a published output and confirm it from the surface, in the window."""
    from newz.publish.publication import (
        CONFIRMED,
        REVOCATION_WINDOW_MINUTES,
        confirm_revocation,
        correct,
        revocation_latency_seconds,
    )

    revocation_id = f"revocation:drill-{card_revision_id.rsplit(':', 1)[-1]}"
    correct(
        store,
        revocation_id=revocation_id,
        claim_id=claim_id,
        card_revision_id=card_revision_id,
        reason="correction drill",
        surface=surface,
        now=now,
    )
    status = confirm_revocation(store, revocation_id, surface, confirmed_at or now)
    latency = revocation_latency_seconds(store, revocation_id)
    window = REVOCATION_WINDOW_MINUTES * 60

    findings: list[str] = []
    if status != CONFIRMED:
        findings.append(f"the surface does not carry the correction: {status}")
    if latency is None:
        findings.append("no confirmation was recorded, so there is no latency to compare")
    elif latency > window:
        findings.append(f"confirmed after {latency:.0f}s, past the {window}s window")
    return DrillResult(
        name="correction_drill",
        passed=not findings,
        detail=f"{status} after {latency:.0f}s against a {window}s window"
        if latency is not None
        else f"{status}, unconfirmed",
        findings=tuple(findings),
    )


def run_drills(
    store: Store, destination: Path, keys_root: Path | None = None
) -> tuple[DrillResult, ...]:
    """The two drills that need nothing but the store itself."""
    record_policy_version(store)
    return (policy_replay(store), restore_drill(store, destination, keys_root))


def gate_6_status(store: Store, drills: tuple[DrillResult, ...] = ()) -> dict[str, Any]:
    """What Gate 6 asks for, and which parts a person still has to supply."""
    return {
        "drills": [drill.as_record() for drill in drills],
        "policy_version": BUNDLE.version,
        "policy_digest": BUNDLE.digest,
        "operator_supplied": [
            "production service objectives — a commitment, not a measurement",
            "security review — a person reads the threat model against the code",
            "catalog expansion beyond the pilot, with the concentration alerts holding",
            "R2 source classes admitted only after direct adversarial review",
            "R3 intake only after the isolated workflow is exercised",
        ],
        "known_limits": [
            "replay covers each claim's current assessment only: edge liveness is a "
            "mutable projection over an immutable log, so the graph as it stood at an "
            "earlier derivation cannot be rebuilt without a snapshot nothing takes",
            "replay under a superseded policy version needs that version's bundle, and "
            "the store records only its digest",
        ],
        "note": (
            "The drills here run. The rest of Gate 6 is judgment and commitment, and a "
            "passing test would not be evidence of either."
        ),
    }
