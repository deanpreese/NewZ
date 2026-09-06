"""One extraction: prompt, proposal, validation, record.

The raw proposal is retained as an artifact before anything is derived from it,
so what the model actually said survives independently of what the system made
of it. That is the same ordering the acquisition plane uses for a fetched body,
and for the same reason: the record of the input must not depend on the
derivation succeeding.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from newz.acquisition import artifacts
from newz.control.isolation import guard_model_read
from newz.extract.prompts import system_prompt, user_prompt
from newz.extract.proposal import (
    ProposalUnreadable,
    Refusal,
    ValidatedExtraction,
    parse_proposal,
    validate,
)
from newz.model.client import ModelClient, ModelUnavailable
from newz.parse.registry import Segment
from newz.parse.store import segments_for
from newz.store.db import Store


@dataclass(frozen=True, slots=True)
class ExtractionRecord:
    run_id: str
    artifact_id: str
    raw_artifact_id: str
    model: str
    proposed: int
    accepted: int
    refusals: tuple[Refusal, ...]
    assertion_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]


def extract(
    store: Store,
    *,
    run_id: str,
    artifact_id: str,
    parse_execution_id: str,
    source_revision_id: str,
    client: ModelClient,
    segments: tuple[Segment, ...] | None = None,
    source_name: str = "",
    now: datetime | None = None,
) -> ExtractionRecord:
    """Ask the model to propose, keep what verifies, and record all of it."""
    segments = segments if segments is not None else segments_for(store, artifact_id)
    if not segments:
        raise ValueError(f"{artifact_id} has no segments; parse it first")

    # Before the prompt is built, not after. `SPEC.md` section 8 excludes private
    # personal data from prompts unless an operator has recorded that a
    # particular read is strictly necessary, and the point of the rule is that
    # the text never reaches the endpoint — a check that ran after the call
    # would be describing something that had already happened.
    #
    # The model boundary already refused to let a model *grant* capability. It
    # said nothing about what a model is *shown*, and those are different
    # protections: one stops a wrong answer being believed, this stops a right
    # answer being produced somewhere it should not have been asked.
    guard_model_read(store, artifact_id, now or datetime.now())

    system = system_prompt()
    user = user_prompt(segments, source_name)
    prompt_hash = hashlib.sha256(f"{system}\x1f{user}".encode()).hexdigest()

    completion = client.complete(system, user)

    # Retained before it is interpreted, exactly as a fetched body is.
    stored = artifacts.store_bytes(store.artifact_root, completion.text.encode("utf-8"))
    raw_artifact_id = f"artifact:{stored.content_hash[:16]}"

    try:
        proposal = parse_proposal(completion.text)
        result = validate(proposal, segments, artifact_id)
        proposed = len(proposal.assertions) + len(proposal.claims)
    except ProposalUnreadable as error:
        proposal = None
        proposed = 0
        result = ValidatedExtraction(
            refusals=(Refusal("proposal", "unreadable_proposal", str(error)),)
        )

    assertion_ids: list[str] = []
    claim_ids: list[str] = []
    suffix = run_id.split(":", 1)[-1]

    with store.write() as connection:
        raw_artifact_id = artifacts.record_artifact(
            store, connection, raw_artifact_id, stored, "text/plain"
        )
        connection.execute(
            "INSERT INTO extraction_runs (id, artifact_id, parse_execution_id, model, "
            "prompt_hash, raw_artifact_id, proposed, accepted, refusals_json, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (
                run_id,
                artifact_id,
                parse_execution_id,
                completion.model,
                prompt_hash,
                raw_artifact_id,
                proposed,
                result.accepted,
                json.dumps([refusal.as_record() for refusal in result.refusals], sort_keys=True),
            ),
        )

        for index, accepted in enumerate(result.assertions):
            assertion_id = f"assertion:{suffix}-{index}"
            connection.execute(
                "INSERT INTO assertions (id, extraction_run_id, artifact_id, segment_id, "
                "source_revision_id, kind, quote, offset_start, offset_end, locator, summary, "
                "live, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))",
                (
                    assertion_id,
                    run_id,
                    artifact_id,
                    accepted.span.segment_id,
                    source_revision_id,
                    accepted.kind.value,
                    accepted.span.quote,
                    accepted.span.start,
                    accepted.span.end,
                    accepted.span.locator,
                    accepted.summary,
                ),
            )
            assertion_ids.append(assertion_id)
            for name in accepted.entities:
                entity_id = f"entity:{hashlib.sha256(name.lower().encode()).hexdigest()[:16]}"
                connection.execute(
                    "INSERT OR IGNORE INTO entities (id, name, kind, disambiguation, recorded_at) "
                    "VALUES (?, ?, 'unresolved', '', datetime('now'))",
                    (entity_id, name),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO assertion_entities (assertion_id, entity_id) "
                    "VALUES (?, ?)",
                    (assertion_id, entity_id),
                )

        for index, candidate in enumerate(result.claims):
            claim_id = f"claim:{suffix}-{index}"
            connection.execute(
                "INSERT INTO claims (id, kind, wording, risk, resolution_horizon, resolver, "
                "withdrawn, recorded_at) VALUES (?, ?, ?, NULL, NULL, NULL, 0, datetime('now'))",
                (claim_id, candidate.kind.value, candidate.wording),
            )
            connection.execute(
                "INSERT INTO claim_origins (claim_id, extraction_run_id, artifact_id, "
                "segment_id, quote) VALUES (?, ?, ?, ?, ?)",
                (
                    claim_id,
                    run_id,
                    artifact_id,
                    candidate.span.segment_id if candidate.span else None,
                    candidate.span.quote if candidate.span else "",
                ),
            )
            claim_ids.append(claim_id)

    return ExtractionRecord(
        run_id=run_id,
        artifact_id=artifact_id,
        raw_artifact_id=raw_artifact_id,
        model=completion.model,
        proposed=proposed,
        accepted=result.accepted,
        refusals=result.refusals,
        assertion_ids=tuple(assertion_ids),
        claim_ids=tuple(claim_ids),
    )


def raw_proposal(store: Store, run_id: str) -> str:
    """Read back exactly what the model said, from the artifact store."""
    row = store.one(
        "SELECT a.stored_path FROM extraction_runs r JOIN artifacts a ON a.id = r.raw_artifact_id "
        "WHERE r.id = ?",
        run_id,
    )
    if row is None:
        raise KeyError(run_id)
    return (store.artifact_root / row["stored_path"]).read_text(encoding="utf-8")


__all__ = ["ExtractionRecord", "ModelUnavailable", "extract", "raw_proposal"]
