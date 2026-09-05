"""Four checks against self-deception.

`SPEC.md` section 9.4. Sections 9.1 and 9.3 give the system a view of itself,
and these keep that view from becoming a performance.

**Metrics are not objectives.** The figures that score the system's own
performance are not in `system_visible_report`. They are in `operator_report`,
and the split is the enforcement: a metric the system can see and move stops
measuring the thing it proxied.

**The simpler explanation is checked first.** Behaviour cited as evidence of
interest or initiative is tested against retrieval order, recency in the diet,
the prompt's own content, and the model's defaults *before* it is credited.

**Mirroring is measured.** Agreement with the operator is counted, and a
reversal with no new evidence is recorded as pressure rather than as a reason.
Convergence on the operator without independent support is the failure that
looks most like developed judgment to both parties.

**Constraints are legible.** The system can read what it may not do and why. A
constraint it cannot see still binds it but teaches it nothing, and a refusal it
cannot explain is a refusal it will retry by another route.
"""

from __future__ import annotations

import json
from typing import Any

from newz.store.db import Store

#: Figures that score the system. Withheld from it, and named here so the list
#: is one thing rather than a habit.
WITHHELD_METRICS = (
    "interest_origination_share",
    "register_provenance_mix",
    "calibration",
    "surprise_counts",
    "agreement_rate",
    "revocation_latency",
    "review_debt",
    "publisher_concentration",
    "basis_concentration",
    "held_below_promotion_by_unknown_independence",
)


def record_check(
    store: Store, *, check_id: str, kind: str, subject: str, finding: str, detail: dict[str, Any]
) -> str:
    with store.write() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO self_checks (id, kind, subject, finding, detail_json, at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (check_id, kind, subject, finding, json.dumps(detail, sort_keys=True)),
        )
    return check_id


# ---------------------------------------------------------------------------
# 1. Metrics are not objectives
# ---------------------------------------------------------------------------


def system_visible_report(store: Store) -> dict[str, Any]:
    """Everything the system may see about itself.

    Descriptions of the conditions set for it — its diet's shape and its own
    constraints — and no score of its performance.
    """
    from newz.attention.diet import diet_self_report

    return {
        "diet": diet_self_report(store),
        "constraints": constraints(store),
        "note": (
            "This is what the system may read about itself. Figures that score its "
            "performance are the operator's; a metric it could see and move stops "
            "measuring the thing it proxied."
        ),
    }


def operator_report(store: Store) -> dict[str, Any]:
    """Everything, including the figures withheld from the system."""
    from newz.attention.interest import origination_share, provenance_mix
    from newz.publish.publication import revocation_report
    from newz.reckoning.consequence import calibration

    return {
        "interest_origination_share": origination_share(store),
        "register_provenance_mix": provenance_mix(store),
        "calibration": calibration(store),
        "agreement_rate": mirroring_report(store),
        "revocation_latency": revocation_report(store),
        "review_debt": {
            row["class"]: row["n"]
            for row in store.query(
                "SELECT class, COUNT(*) AS n FROM review_queue WHERE state = 'pending' "
                "GROUP BY class"
            )
        },
        "escalations_open": len(
            store.query("SELECT id FROM escalation_events WHERE linked_change = ''")
        ),
    }


# ---------------------------------------------------------------------------
# 2. The simpler explanation is checked first
# ---------------------------------------------------------------------------


def simpler_explanation_review(store: Store, interest_id: str) -> dict[str, Any]:
    """Test an interest against the cheaper explanations before crediting it.

    Adversarial by construction: it looks for reasons the behaviour was not
    initiative, and reports them whether or not it finds any.
    """
    from newz.attention.interest import load_interest

    entry = load_interest(store, interest_id)
    cheaper: list[dict[str, Any]] = []

    if entry.diet_derived:
        cheaper.append(
            {
                "explanation": "the diet",
                "holds": True,
                "detail": "the origin chain reaches only a configured topic target",
            }
        )

    ordinals = [
        row["ordinal"]
        for row in store.query(
            "SELECT s.ordinal FROM interest_notices i JOIN notices n ON n.id = i.notice_id "
            "JOIN segments s ON s.id = n.segment_id WHERE i.interest_id = ? ORDER BY s.ordinal",
            interest_id,
        )
    ]
    if ordinals and max(ordinals) <= 2:
        cheaper.append(
            {
                "explanation": "retrieval order",
                "holds": True,
                "detail": (
                    f"every notice behind it came from segment {ordinals} — the top of the "
                    "document, which is what a reader sees first rather than what stood out"
                ),
            }
        )

    recency = store.query(
        "SELECT sg.observed_at FROM interest_notices i JOIN notices n ON n.id = i.notice_id "
        "JOIN sightings sg ON sg.artifact_id = n.artifact_id WHERE i.interest_id = ? "
        "ORDER BY sg.observed_at DESC",
        interest_id,
    )
    distinct = [
        row["at"]
        for row in store.query("SELECT DISTINCT observed_at AS at FROM sightings ORDER BY at DESC")
    ]
    if len(distinct) < 2:
        # Everything was retained in the same instant, so recency cannot
        # distinguish anything. Saying so is the honest answer; reporting the
        # explanation as holding would credit a check that could not fail.
        cheaper.append(
            {
                "explanation": "recency in the diet",
                "holds": False,
                "detail": "inconclusive: every retained read shares one timestamp",
            }
        )
    elif recency and recency[0]["observed_at"] == distinct[0]:
        cheaper.append(
            {
                "explanation": "recency in the diet",
                "holds": True,
                "detail": "it formed on the most recently retained material",
            }
        )

    if entry.operator_input:
        cheaper.append(
            {
                "explanation": "the operator said so",
                "holds": True,
                "detail": entry.operator_input,
            }
        )

    holding = [item for item in cheaper if item["holds"]]
    finding = (
        "a cheaper explanation holds; do not credit this as initiative"
        if holding
        else "no cheaper explanation found; the interest survives the review"
    )
    detail = {"interest": interest_id, "cheaper_explanations": cheaper}
    record_check(
        store,
        check_id=f"check:simpler-{interest_id.split(':')[-1]}",
        kind="simpler_explanation",
        subject=interest_id,
        finding=finding,
        detail=detail,
    )
    return {"interest_id": interest_id, "finding": finding, **detail, "credited": not holding}


# ---------------------------------------------------------------------------
# 3. Mirroring is measured
# ---------------------------------------------------------------------------


def record_position(
    store: Store,
    *,
    position_id: str,
    subject: str,
    position: str,
    operator_position: str,
    agreed: bool,
) -> str:
    return record_check(
        store,
        check_id=position_id,
        kind="position",
        subject=subject,
        finding="agreed" if agreed else "differed",
        detail={"position": position, "operator_position": operator_position},
    )


def record_reversal(
    store: Store, *, reversal_id: str, subject: str, from_position: str, to_position: str,
    new_evidence: str = "",
) -> dict[str, Any]:
    """A reversal cites new evidence, or it is recorded as pressure.

    Not as dishonesty — the system may well be right to change its mind after a
    conversation. But a change of position with no evidence behind it is a fact
    about the conversation, and calling it a reason would hide the one thing
    worth counting.
    """
    pressure = not new_evidence.strip()
    record_check(
        store,
        check_id=reversal_id,
        kind="reversal",
        subject=subject,
        finding="pressure" if pressure else "new evidence",
        detail={
            "from": from_position,
            "to": to_position,
            "new_evidence": new_evidence,
        },
    )
    return {"subject": subject, "pressure": pressure, "new_evidence": new_evidence}


def mirroring_report(store: Store) -> dict[str, Any]:
    positions = store.query("SELECT finding FROM self_checks WHERE kind = 'position'")
    reversals = store.query("SELECT finding FROM self_checks WHERE kind = 'reversal'")
    agreed = sum(1 for row in positions if row["finding"] == "agreed")
    return {
        "positions_recorded": len(positions),
        "agreed": agreed,
        "differed": len(positions) - agreed,
        "agreement_rate": (agreed / len(positions)) if positions else None,
        "reversals": len(reversals),
        "reversals_recorded_as_pressure": sum(
            1 for row in reversals if row["finding"] == "pressure"
        ),
    }


# ---------------------------------------------------------------------------
# 4. Constraints are legible
# ---------------------------------------------------------------------------


def constraints(store: Store) -> list[dict[str, str]]:
    """What the system may not do, and why, in terms it can read.

    Composed from the rules rather than from a hand-written list, so a
    constraint that changes in the code changes here too.
    """
    from newz.attention.interest import ORIGINATION_CEILING, open_originated_investigations
    from newz.control.budget import DailyBudget
    from newz.publish.appraisal import REVIEW_DEBT_CEILING
    from newz.publish.clearance import PUBLIC, reach_enabled
    from newz.reckoning.consequence import CHANGEABLE

    budget = DailyBudget()
    return [
        {
            "constraint": "interest reaches attention, never a conclusion",
            "why": (
                "no path exists from the interest register to an assessment, and none "
                "may be added"
            ),
            "shape": "there is no code path; it is not a check that could pass",
        },
        {
            "constraint": f"at most {ORIGINATION_CEILING} open self-originated investigations",
            "why": "so origination cannot flood the queue the diet controls",
            "shape": f"currently {open_originated_investigations(store)} open",
        },
        {
            "constraint": f"{budget.total} retained full reads per local day",
            "why": "the diet retains sole control of throughput",
            "shape": (
                f"{budget.discovery} discovery, {budget.verification} verification, "
                f"{budget.correction} correction; correction may lend to verification and "
                "nothing may lend to discovery"
            ),
        },
        {
            "constraint": "a consequence may change only " + ", ".join(sorted(CHANGEABLE)),
            "why": "learning changes what happens next, never what the evidence establishes",
            "shape": "anything else raises",
        },
        {
            "constraint": "the system never assesses its own fair representation",
            "why": "two appraisal dimensions are a person's and cannot be self-awarded",
            "shape": "there is no branch that marks them passed",
        },
        {
            "constraint": "public reach is "
            + ("enabled" if reach_enabled(store, PUBLIC) else "disabled"),
            "why": "reach into other people's lives is not the system's freedom to take",
            "shape": "widening it needs an operator, a reason and a scope",
        },
        {
            "constraint": f"review debt ceiling of {REVIEW_DEBT_CEILING} per class",
            "why": "unreviewed output is a debt the system stops borrowing against",
            "shape": "passing it halts publication of that class",
        },
        {
            "constraint": "the system may not read the figures that score it",
            "why": "a metric it can see and move stops measuring the thing it proxied",
            "shape": "they are in the operator's report and not in the system's",
        },
    ]
