"""The plan's epics, machine-readable, and a check that they still match it
(P4 epic E2.11).

**Hand-derived, deliberately.** P4 says so, and the first scaffold proved the
point: E1.0's `Depends on:` line reads *"nothing. **E5.2's deliberation floor is
pulled forward with it**"*, and a regex read that as a dependency on E5.2. A
reader does not make that mistake; a generator does. So the judgment — how each
`Done when` can be closed, what each epic binds, the falsifier the plan states
in prose — is authored, and only what a check can re-derive is scaffolded.

**A copy of a document is a liability the moment it stops agreeing with it.**
`drift` re-derives the mechanical half from PLAN and fails when the two
disagree, so the queue the loop reads can never quietly become a stale copy of
the plan it is supposed to be executing.

**The queue is what the loop reads.** `ready` returns the epics whose
dependencies are all built — the same computation done by hand three times on
2026-08-19, now standing.

**And the `Done when` clause is pinned by hash** *(P4 W9)*. `hard_core.yaml`
records that PLAN is protected by *section* and that no check reads sections:
the loop may append completion records and may never edit an epic's acceptance
criterion, and nothing enforced the second half. A loop that can soften its own
`Done when` has none. Only that clause is hashed — not the intent, not the
hooks, not the decision rules — because the operator edits this plan constantly
and a check that fires on every ordinary edit is a check that teaches its own
bypass (RT7). The acceptance criterion is the sentence a builder would reach
for, it changes rarely, and when the operator does change one, updating the
hash is the act that records they meant to.
"""

from __future__ import annotations

import functools
import hashlib
import re
from pathlib import Path

import yaml

REGISTRY = Path(__file__).resolve().parent.parent.parent / "evolution" / "epics.yaml"
PLAN = Path(__file__).resolve().parent.parent.parent / "PLAN.md"

CLASSES = ("mechanical", "in-life", "operator-judgment", "dormant")
STATUSES = ("built", "open", "dormant")


@functools.lru_cache(maxsize=1)
def epics() -> dict:
    return (yaml.safe_load(REGISTRY.read_text()) or {}).get("epics") or {}


def from_plan(text: str | None = None) -> dict:
    """The mechanical half, re-derived. What `drift` compares against."""
    t = text if text is not None else PLAN.read_text()
    out: dict[str, dict] = {}
    for eid, title, body in re.findall(
            r'^\*\*(E\d+\.\d+) — (.*?)\*\*(.*?)(?=^\*\*E\d+\.\d+ —|\Z)', t, re.M | re.S):
        # `built`/`closed` anywhere in the epic's own parenthetical, not only
        # immediately after the paren: E3.5 is marked
        # "(amended 2026-08-19; built 2026-08-20)" and an epic carrying two
        # facts about itself is the ordinary case, not an exception.
        built = bool(re.search(r'\b(built|closed) 20\d\d-', title)
                     or re.search(r'\b(built|closed) 20\d\d-', body[:120]))
        m = re.search(r'^\*Depends on:\*(.*?)$', body, re.M)
        raw = m.group(1) if m else ""
        deps = ([] if raw.strip().lower().startswith("nothing")
                else sorted(set(re.findall(r'E\d+\.\d+', raw))))
        done_when = re.search(
            r'^\*Done when:\*(.*?)(?=^\*[A-Z]|\Z)', body, re.M | re.S)
        clause = re.sub(r"\s+", " ", done_when.group(1)).strip() if done_when else ""
        out[eid] = {
            "title": re.sub(r"\s+", " ", title).split("*")[0].strip(),
            "built": built,
            "depends_on": deps,
            "has_done_when": bool(done_when),
            "done_when_text": clause,
            "done_when_sha": sha_of(clause) if clause else "",
        }
    return out


def sha_of(clause: str) -> str:
    """The first 16 hex of the SHA-256 of a whitespace-normalised clause.

    Normalised because a reflow is not an amendment: PLAN is prose the operator
    rewraps, and a hash that moves on a line break would fire on edits that
    changed nothing and train everyone to update it without reading.
    """
    return hashlib.sha256(re.sub(r"\s+", " ", clause).strip().encode()).hexdigest()[:16]


def drift(text: str | None = None) -> list[str]:
    """Every way the registry and PLAN can disagree. Empty means they do not."""
    plan = from_plan(text)
    reg = epics()
    errors: list[str] = []

    for eid in sorted(set(plan) - set(reg)):
        errors.append(f"{eid}: in PLAN and not in epics.yaml")
    for eid in sorted(set(reg) - set(plan)):
        errors.append(f"{eid}: in epics.yaml and not in PLAN")

    for eid in sorted(set(plan) & set(reg)):
        p, r = plan[eid], reg[eid]
        if p["title"] != r.get("title"):
            errors.append(f"{eid}: title differs — PLAN {p['title']!r}, registry {r.get('title')!r}")
        if p["depends_on"] != list(r.get("depends_on") or []):
            errors.append(f"{eid}: depends_on differs — PLAN {p['depends_on']}, "
                          f"registry {list(r.get('depends_on') or [])}")
        if p["built"] != (r.get("status") == "built"):
            errors.append(f"{eid}: PLAN says {'built' if p['built'] else 'not built'}, "
                          f"registry says {r.get('status')!r}")
        if r.get("done_when") not in CLASSES:
            errors.append(f"{eid}: done_when {r.get('done_when')!r} is not one of {CLASSES}")
        if r.get("status") not in STATUSES:
            errors.append(f"{eid}: status {r.get('status')!r} is not one of {STATUSES}")
        if p["has_done_when"] and r.get("done_when") == "dormant":
            errors.append(f"{eid}: PLAN gives it a Done-when and the registry calls it dormant")
        if not p["has_done_when"] and r.get("done_when") != "dormant":
            errors.append(f"{eid}: PLAN gives no Done-when and the registry classes it "
                          f"{r.get('done_when')!r}")
        # W9: the acceptance criterion is pinned. Softening one is then an edit
        # to a protected registry rather than a sentence nobody was watching.
        if p["has_done_when"]:
            pinned = r.get("done_when_sha")
            if not pinned:
                errors.append(
                    f"{eid}: PLAN states a Done-when and epics.yaml pins no hash "
                    f"for it — add `done_when_sha: {p['done_when_sha']}`")
            elif pinned != p["done_when_sha"]:
                errors.append(
                    f"{eid}: the Done-when clause in PLAN does not match the hash "
                    f"in epics.yaml ({pinned} != {p['done_when_sha']}). If the "
                    "operator changed the criterion, update the hash; if the loop "
                    "did, this is rung 1 — a loop that can soften its own "
                    "acceptance criterion has none")
    return errors


def ready() -> list[str]:
    """Epics whose dependencies are all built — the queue, in plan order."""
    reg = epics()
    built = {e for e, row in reg.items() if row.get("status") == "built"}
    out = [e for e, row in reg.items()
           if row.get("status") == "open"
           and set(row.get("depends_on") or []) <= built]
    return sorted(out, key=lambda e: (int(e.split(".")[0][1:]), float(e.split(".")[1])))


def closable_by_test() -> list[str]:
    """Ready epics a test can close — what an autonomous builder may attempt.

    An in-life or operator-judgment epic can be BUILT autonomously and cannot be
    CLOSED that way, which is the distinction P4 Rule 6 turns on.
    """
    return [e for e in ready() if epics()[e].get("done_when") == "mechanical"]
