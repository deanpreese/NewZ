"""Load a controlled case file into records.

The case files under `tests/fixtures/cases/` are the readable artifact: each one
states a situation and the state it must reach. This module is the only place
that knows how to turn one into records, so a case file stays a description
rather than a program.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from newz.domain.enums import (
    TERMINAL_COMPETENT_STATES,
    AssertionKind,
    ClaimKind,
    EdgeRelation,
    EvidenceLane,
    IndependenceJustification,
    RiskTier,
    SourceRole,
    TaskState,
)
from newz.domain.records import (
    Assertion,
    Basis,
    Claim,
    EdgeEvent,
    IndependenceClaim,
    Span,
    Task,
)
from newz.policy.promotion import EvidenceInput

CASE_DIR = Path(__file__).parent / "fixtures" / "cases"


def case_paths() -> list[Path]:
    return sorted(CASE_DIR.glob("*.json"))


def load_raw(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _risk(value: str | None) -> RiskTier | None:
    return RiskTier(value) if value else None


def build(case: dict[str, Any], *, horizon_reached: bool | None = None) -> EvidenceInput:
    claim_spec = case["claim"]
    claim = Claim(
        id=claim_spec["id"],
        kind=ClaimKind(claim_spec["kind"]),
        wording=claim_spec["wording"],
        risk=_risk(claim_spec.get("risk")),
        resolution_horizon=claim_spec.get("resolution_horizon"),
        resolver=claim_spec.get("resolver"),
        withdrawn=claim_spec.get("withdrawn", False),
    )

    bases = {
        b["id"]: Basis(
            id=b["id"],
            origin_kind=b["origin_kind"],
            origin_identifier=b["origin_identifier"],
            resolved=b.get("resolved", True),
            independence_group=b.get("independence_group"),
        )
        for b in case.get("bases", [])
    }

    assertions: dict[str, Assertion] = {}
    for a in case.get("assertions", []):
        quote = a.get("quote", "")
        spans: tuple[Span, ...] = ()
        if a.get("spans") != []:
            spans = (
                Span(
                    artifact_id=a.get("artifact", f"artifact:{a['id'].split(':')[-1]}"),
                    segment_id=a.get("segment", "p1"),
                    start=0,
                    end=len(quote),
                    quote=quote,
                    locator=a.get("locator", "paragraph 1"),
                    verified=a.get("verified", True),
                ),
            )
        assertions[a["id"]] = Assertion(
            id=a["id"],
            kind=AssertionKind(a["kind"]),
            spans=spans,
            source_revision_id=a["source"],
            role=SourceRole(a["role"]),
            declared_scope=a.get("scope", ""),
            live=a.get("live", True),
        )

    edges: list[EdgeEvent] = []
    for e in case.get("edges", []):
        assertion = assertions[e["assertion"]]
        edges.append(
            EdgeEvent(
                id=e["id"],
                assertion_id=e["assertion"],
                claim_id=claim.id,
                relation=EdgeRelation(e["relation"]),
                basis_id=e["basis"],
                role=assertion.role,
                assertion_kind=assertion.kind,
                risk=_risk(e.get("risk", claim_spec.get("risk"))),
                policy_version=e.get("policy_version", "1.0.0"),
                admitted=True,
                live=e.get("live", True),
                declared_scope=assertion.declared_scope,
                adjudicative_scope_covers_claim=e.get("scope_covers"),
            )
        )

    independence = tuple(
        IndependenceClaim(
            basis_a=i["a"],
            basis_b=i["b"],
            justification=IndependenceJustification(i["justification"]),
            evidence=i.get("evidence", ""),
            operator_actor=i.get("operator_actor"),
            operator_reason=i.get("operator_reason"),
        )
        for i in case.get("independence", [])
    )

    tasks: list[Task] = []
    for t in case.get("tasks", []):
        state = TaskState(t["state"])
        described = t.get("absence", True) and state in TERMINAL_COMPETENT_STATES
        tasks.append(
            Task(
                id=t["id"],
                claim_id=claim.id,
                lane=EvidenceLane(t["lane"]),
                state=state,
                owner=t.get("owner", "worker:evidence"),
                reason=t.get("reason", "controlled case"),
                due=t.get("due", "2026-04-01T00:00:00Z"),
                state_reason=t.get("state_reason", ""),
                expected_record=t.get("expected_record", "the record sought") if described else "",
                repository=t.get("repository", "the competent repository") if described else "",
                query=t.get("query", "the query issued") if described else "",
                time_window=t.get("time_window", "2026-01-01/2026-04-01") if described else "",
                searched_scope=t.get("searched_scope", "the scope searched") if described else "",
            )
        )

    return EvidenceInput(
        claim=claim,
        edges=tuple(edges),
        assertions=assertions,
        bases=bases,
        independence=independence,
        tasks=tuple(tasks),
        horizon_reached=(
            case.get("horizon_reached", False) if horizon_reached is None else horizon_reached
        ),
    )
