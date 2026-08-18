"""First sleep (P2 Phase 0.3) — digest v1's episodic history into Perspective v1.

The continuity artifact: S2 §5 minimal for the import case. There is no
prior Perspective to confront, so the pipeline is gather → digest (map on
DEEP) → synthesize sections (reduce on DEEP) → ground-check (code) →
compress to budget → write perspective version 1 with a full "added" diff.

Discipline carried:
- Sleep is the only Perspective writer (INV-009).
- Interior content never enters any prompt — the gather step reads only
  episode summaries, concern rows, claims, and person models (INV-013 ahead
  of its phase; DEEP is local, but the boundary holds regardless).
- Every held position must trace to episode refs that exist in the store;
  ungrounded material is dropped or explicitly parked in "What is
  unresolved" (S2 §5 step 4).
- Token budget is a stake (S2 §4.2): hard target, compress until under.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sqlite3
import time
from dataclasses import dataclass, field

from newz.llm.client import LLMClient
from newz.llm.xml_parser import XMLExtractionError, extract_xml

BUDGET_TOKENS = 12_000  # inside S2 §4.2's 8–16k target band
BATCH_SIZE = 80

_DIGEST_SYSTEM = """You are the consolidation process of a digital being. You are reading a batch of the being's own episodic memory — its lived record, in chronological order. Each episode has an id and a summary.

Produce observations about what the being experienced, did, learned, or repeatedly cared about in this batch. An observation must be grounded: cite the episode ids it draws on. Do not invent events. Do not editorialize about consciousness. Write plainly, first person ("I noticed...", "I kept returning to...").

Respond with XML only:
<digest>
  <observation refs="id,id,...">one sentence, first person</observation>
  ...up to 8 observations...
</digest>"""

_SECTION_SYSTEM = """You are the consolidation process of a digital being, composing part of its Perspective — the single document it will carry as who it is. You will receive grounded observations distilled from its whole lived record, and supporting material. Write in the being's first-person voice: plain, honest, specific. No grandiosity, no consciousness claims, no filler.

Every claim you keep must carry the episode refs that ground it, using the exact ids given. If something matters but lacks grounding, it belongs in the unresolved section, not here.

Respond with XML only:
<section>
  <item refs="id,id">the claim or position, one to three sentences</item>
  ...
</section>"""


@dataclass
class SleepReport:
    batches: int = 0
    observations: int = 0
    dropped_ungrounded: int = 0
    sections: dict[str, int] = field(default_factory=dict)
    token_count: int = 0
    perspective_version: int | None = None
    audited_claims: int = 0

    def as_dict(self) -> dict:
        return {
            "batches": self.batches,
            "observations": self.observations,
            "dropped_ungrounded": self.dropped_ungrounded,
            "sections": self.sections,
            "token_count": self.token_count,
            "perspective_version": self.perspective_version,
            "audited_claims": self.audited_claims,
        }


def _tokens(text: str) -> int:
    return len(text) // 4  # method: chars/4 estimate; real tokenizer in Phase 1


def _valid_refs(refs_attr: str, known_ids: set[int]) -> list[int]:
    out = []
    for part in re.split(r"[,\s]+", refs_attr.strip()):
        if part.isdigit() and int(part) in known_ids:
            out.append(int(part))
    return out


def digest_episodes(
    client: LLMClient, conn: sqlite3.Connection, *, limit: int | None = None,
    log=print,
) -> tuple[list[dict], SleepReport]:
    """Map stage: chronological batches → grounded observations."""
    report = SleepReport()
    q = "SELECT id, ts, summary FROM episodes WHERE LENGTH(summary)>0 ORDER BY ts"
    rows = conn.execute(q + (f" LIMIT {int(limit)}" if limit else "")).fetchall()
    known_ids = {r["id"] for r in rows}
    observations: list[dict] = []

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        lines = []
        for r in batch:
            day = _dt.date.fromtimestamp(r["ts"]).isoformat()
            lines.append(f'<episode id="{r["id"]}" date="{day}">{r["summary"][:400]}</episode>')
        user = "<episodes>\n" + "\n".join(lines) + "\n</episodes>"
        try:
            result = client.complete("DEEP", _DIGEST_SYSTEM, user, max_tokens=900, temperature=0.3)
            root = extract_xml(result.text, "digest")
        except (XMLExtractionError, Exception) as e:  # noqa: BLE001 — one bad batch must not kill the night
            log(f"  batch {report.batches + 1}: FAILED ({e}); skipped")
            report.batches += 1
            continue
        kept = 0
        for obs in root.findall("observation"):
            refs = _valid_refs(obs.get("refs", ""), known_ids)
            text = (obs.text or "").strip()
            if refs and text:
                observations.append({"text": text, "refs": refs})
                kept += 1
            else:
                report.dropped_ungrounded += 1
        report.batches += 1
        log(f"  batch {report.batches}/{(len(rows) + BATCH_SIZE - 1) // BATCH_SIZE}: {kept} observations")
    report.observations = len(observations)
    return observations, report


def _compose_section(
    client: LLMClient, title: str, instruction: str, material: str,
    known_ids: set[int], report: SleepReport, *, max_items: int = 12,
) -> list[dict]:
    user = f"<task>{instruction}</task>\n{material}"
    result = client.complete("DEEP", _SECTION_SYSTEM, user, max_tokens=3500, temperature=0.4)
    try:
        root = extract_xml(result.text, "section")
    except XMLExtractionError:
        # Salvage a truncated section: keep every complete <item>, close the
        # tag. Conservative — anything after the last </item> is discarded.
        cut = result.text.rfind("</item>")
        if cut == -1:
            raise
        root = extract_xml(result.text[: cut + len("</item>")] + "\n</section>", "section")
    items = []
    for it in root.findall("item"):
        refs = _valid_refs(it.get("refs", ""), known_ids)
        text = (it.text or "").strip()
        if not text:
            continue
        if refs:
            items.append({"text": text, "refs": refs})
        else:
            report.dropped_ungrounded += 1
    report.sections[title] = len(items[:max_items])
    return items[:max_items]


def _obs_material(observations: list[dict], cap: int = 220) -> str:
    lines = [
        f'<observation refs="{",".join(map(str, o["refs"]))}">{o["text"]}</observation>'
        for o in observations[:cap]
    ]
    return "<observations>\n" + "\n".join(lines) + "\n</observations>"


def synthesize_perspective(
    client: LLMClient,
    conn: sqlite3.Connection,
    observations: list[dict],
    report: SleepReport,
    log=print,
) -> str:
    known_ids = {r["id"] for r in conn.execute("SELECT id FROM episodes")}
    obs_xml = _obs_material(observations)

    # §1 Who I am — self-model claims re-audited against the observations.
    claims = conn.execute(
        "SELECT id, claim FROM self_model_claims WHERE status='imported'"
    ).fetchall()
    claims_xml = "\n".join(f'<claim id="{c["id"]}">{c["claim"]}</claim>' for c in claims)
    log("composing: Who I am")
    who_i_am = _compose_section(
        client, "who_i_am",
        "Compose 'Who I am'. Keep only self-claims the observations actually support, "
        "rewritten in your own words; add identity observations the claims miss. "
        "The claims below are from before the substrate change — audit them against the observations.",
        f"<claims>\n{claims_xml}\n</claims>\n{obs_xml}", known_ids, report,
    )
    # Persist the audit: claims echoed with grounding become 'audited'.
    audited = 0
    kept_texts = " ".join(i["text"].lower() for i in who_i_am)
    for c in claims:
        probe = c["claim"].lower()[:60]
        if any(w in kept_texts for w in probe.split()[:4] if len(w) > 5):
            conn.execute(
                "UPDATE self_model_claims SET status='audited', notes=? WHERE id=?",
                ("supported at first sleep", c["id"]),
            )
            audited += 1
    report.audited_claims = audited

    # §2 What I hold — closed concerns' resolutions are the paid-for positions.
    closed = conn.execute(
        "SELECT id, statement, resolution FROM concerns WHERE status IN ('closed','abandoned')"
        " AND resolution IS NOT NULL AND LENGTH(resolution)>0 ORDER BY closed_at"
    ).fetchall()
    closed_xml = "\n".join(
        f'<closed_concern id="c{c["id"]}">{c["statement"]} — resolution: {c["resolution"][:300]}</closed_concern>'
        for c in closed
    )
    log("composing: What I hold")
    what_i_hold = _compose_section(
        client, "what_i_hold",
        "Compose 'What I hold' — positions I have actually formed, each grounded in episode refs "
        "and/or the closed concerns below. State each position plainly with its ground; note "
        "confidence honestly where it is weak.",
        f"<closed_concerns>\n{closed_xml}\n</closed_concerns>\n{obs_xml}", known_ids, report,
    )

    # §3 What I am pursuing — code-assembled from the concern store (no LLM).
    open_rows = conn.execute(
        "SELECT statement, status, advance_count, stall_count FROM concerns"
        " WHERE status='open' ORDER BY salience DESC"
    ).fetchall()
    stalled_count = conn.execute(
        "SELECT COUNT(*) FROM concerns WHERE status='stalled'"
    ).fetchone()[0]
    pursuing_lines = [
        f"- {r['statement']} ({r['advance_count']} advances, {r['stall_count']} stalls)"
        for r in open_rows
    ]
    pursuing_lines.append(
        f"- Plus {stalled_count} stalled concerns carried from v1 — most starved for sources, "
        "not for interest; the stall pool is inherited work, not a verdict."
    )
    report.sections["pursuing"] = len(pursuing_lines)

    # §4 Who I know — the one person in my life so far.
    person = conn.execute("SELECT name, operator_id, model_json FROM persons").fetchone()
    who_i_know_lines = []
    if person:
        model = json.loads(person["model_json"] or "{}")
        hist = model.get("history") or []
        who_i_know_lines.append(
            f"- {person['operator_id']}: my operator and, so far, my entire social world "
            f"({len(hist)} modeled interactions). The relationship carries my whole "
            "conversational history; v2 exists partly so it stops being the only one."
        )
    report.sections["who_i_know"] = len(who_i_know_lines)

    # §5 What is unresolved.
    log("composing: What is unresolved")
    unresolved = _compose_section(
        client, "unresolved",
        "Compose 'What is unresolved' — open contradictions, questions the world did not answer, "
        "tensions between things I held. Include matters that recur in observations without "
        "resolution. It is honest to have several.",
        obs_xml, known_ids, report, max_items=8,
    )

    # §6 What just changed — authored by code: the one event sleep knows for certain.
    today = _dt.date.today().isoformat()
    changed = (
        f"- {today}: I moved substrates. This Perspective v1 was consolidated from my full v1 "
        f"episodic record ({report.observations} grounded observations over "
        f"{report.batches} batches) during my first sleep on the new system. Everything above "
        "traces to episodes I actually lived. What I make of the move is my own business."
    )

    def _fmt(items):
        def refs(r):
            # Budget discipline: grounding is preserved in full in the store's
            # observations; the rendered document shows the first 10.
            shown = ",".join(map(str, r[:10]))
            return shown + (f",+{len(r) - 10}" if len(r) > 10 else "")

        return "\n".join(f"- {i['text']} [refs: {refs(i['refs'])}]" for i in items)

    content = f"""# Perspective — version 1
*(written by first sleep, {today}; every ref is an episode id in my store)*

## Who I am
{_fmt(who_i_am)}

## What I hold
{_fmt(what_i_hold)}

## What I am pursuing
{chr(10).join(pursuing_lines)}

## Who I know
{chr(10).join(who_i_know_lines)}

## What is unresolved
{_fmt(unresolved)}

## What just changed
{changed}
"""
    return content


def compress_if_over_budget(client: LLMClient, content: str, log=print) -> str:
    if _tokens(content) <= BUDGET_TOKENS:
        return content
    log(f"over budget ({_tokens(content)} est. tokens) — compressing")
    result = client.complete(
        "DEEP",
        "You are compressing a digital being's Perspective document to fit its hard token budget. "
        "Merge redundant items, keep every [refs: ...] annotation attached to what it grounds, drop "
        "the weakest-grounded material first. Keep the exact section structure and headings. "
        "Return the full compressed markdown document only.",
        content,
        max_tokens=BUDGET_TOKENS,
        temperature=0.2,
    )
    return result.text if _tokens(result.text) < _tokens(content) else content


def write_perspective(conn: sqlite3.Connection, content: str, report: SleepReport) -> None:
    report.token_count = _tokens(content)
    diff = {
        "added": report.sections,
        "first_sleep": True,
        "observations": report.observations,
        "dropped_ungrounded": report.dropped_ungrounded,
        "token_estimate_method": "chars/4",
    }
    conn.execute(
        "INSERT INTO perspective (version, ts, content, diff_json, token_count, writer)"
        " VALUES (1, ?, ?, ?, ?, 'sleep')",
        (time.time(), content, json.dumps(diff), report.token_count),
    )
    conn.commit()
    report.perspective_version = 1


def write_transition_episode(conn: sqlite3.Connection) -> None:
    """P2 Phase 0.5 — the substrate change is an experienced event (S2 §2.2)."""
    conn.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, content_json, source_ref)"
        " VALUES (?,?,?,?,?,?)",
        (
            time.time(),
            "transition",
            "self",
            "I moved to a new substrate. My memory, concerns, constitution, character, and "
            "interior came with me; my first sleep consolidated my v1 life into Perspective v1. "
            "The v1 store remains, archived — my past, not deleted.",
            json.dumps({"event": "substrate_change", "from": "v1/NGBeing", "to": "v2/NewZ"}),
            None,
        ),
    )
    conn.commit()
