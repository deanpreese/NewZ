#!/usr/bin/env python3
"""Score the repo's CURRENT prompts against the calls the being actually made.

`tools/bench_model.py` benches a model on cases written by hand. This scores
the *prompts* on inputs the system really sent — every payload in
`logs/llm_calls.jsonl`, re-rendered against whatever the modules hold today.

Two modes, and the first one is free:

    python tools/replay_prompts.py
        Scores the RECORDED responses. Costs nothing: the answers are already
        in the log. Reports, per shape, how many rows were produced by the
        prompt that is live now, how many responses survive the checks the
        consuming code applies, and what the failures actually are.

    python tools/replay_prompts.py --live --model M [--sample 40]
        Re-runs the payloads through the current prompts against an endpoint,
        so the same numbers can be had for a model that has never run here.

    python tools/replay_prompts.py --variant opener.reading=new.txt --live --model M
        Re-renders every payload of that shape against an edited prompt and
        prints both scores side by side. This is the tuning primitive: edit a
        prompt in a scratch file, find out whether it is better.

WHAT IT CANNOT DO
-----------------
The log holds inputs and outputs. It does not hold VERDICTS, so nothing here
can tell you whether triage kept the right item or whether the gate should
have fired — only whether the answer was structurally usable by the code that
consumed it. Judgment needs labels; `gate_log.classification` is the only
labelled set the being has (40 rows, 22 of them on a clause v6 retired).

So this measures conformance at real width. That is a smaller claim than
"prompt quality" and it is the claim the data supports.

Writes nothing. Reads `logs/llm_calls.jsonl`, the prompt modules, and the
store read-only for the active constitution. It has no code path that writes
to `newz/`.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import httpx  # noqa: E402

from bench_model import BadXML, Reply, call, child_text, extract_xml, wilson  # noqa: E402
import bench_model  # noqa: E402

from newz.concerns import opener as _opener  # noqa: E402
from newz.deliberation import lite as _lite  # noqa: E402
from newz.gate import outbound as _gate  # noqa: E402
from newz.sleep import nightly as _nightly  # noqa: E402
from newz.world import extract as _extract  # noqa: E402
from newz.world import feeds as _feeds  # noqa: E402

def _find(rel: str) -> Path:
    """`rel` under this checkout, or under the main one if this is a worktree.

    A git worktree has the code and none of the runtime state — logs/ and data/
    are gitignored and live in the main checkout only — so a tool run from a
    worktree would otherwise report an empty log rather than reading the real
    one. Read-only either way.
    """
    here = _ROOT / rel
    if here.exists():
        return here
    for parent in _ROOT.parents:
        if (parent / rel).exists() and (parent / "newz").is_dir():
            return parent / rel
    return here


LOG = _find("logs/llm_calls.jsonl")


# ─── the prompt set ────────────────────────────────────────────────────────
#
# Every tunable prompt, by id. A variant is this dict with one entry replaced,
# which is the whole mechanism — the modules are read and never patched, so a
# run cannot change what the being sends.

def live_prompts() -> dict[str, str]:
    return {
        "triage.system":    _feeds._TRIAGE_SYSTEM,
        "triage.task":      _feeds._TRIAGE_TASK,
        "extract.system":   _extract._SYSTEM,
        "extract.task":     _extract._TASK,
        "extract.directed": _extract._DIRECTED,
        "opener.system":    _opener._READING_SYSTEM,
        "opener.reading":   _opener._READING_TASK,
        "delib.system":     _lite._SYSTEM,
        "delib.task":       _lite._TASK,
        "digest.system":    _nightly._DIGEST_SYSTEM,
        "confront.system":  _nightly._CONFRONT_SYSTEM,
        "gate.system":      _gate._JUDGE_SYSTEM,
    }


def active_clauses() -> tuple[str, int]:
    """render_for_matcher() from the store — what the judge is actually shown.

    Read-only, and the connection is closed before anything else happens: an
    instrument must never write into the being's record.
    """
    from newz.config import load
    from newz.gate.constitution import load_active_constitution
    from newz.store.db import open_db

    # `newz` may be importable from a git worktree whose data/ is empty, so
    # fall back to the main checkout's store rather than reporting the gate
    # unreadable. Read-only either way.
    db = load(repo_root=_ROOT).main_db_path
    if not db.exists():
        db = _find("data/newz.db")
    conn = open_db(db, read_only=True)
    try:
        con = load_active_constitution(conn)
        return con.render_for_matcher(), con.version
    finally:
        conn.close()


# ─── shapes ────────────────────────────────────────────────────────────────
#
# One entry per call shape the log contains. `detect` finds it, `split` lifts
# the payload off whatever template was live when the call was made, `render`
# puts that payload back against a prompt set, and `check` applies what the
# CONSUMING CODE does with the answer.


@dataclass
class Row:
    shape: str
    payload: str
    extra: dict = field(default_factory=dict)
    response: str = ""
    current: bool = False       # produced by the prompt that is live now
    ts: float = 0.0


def _q(user: str) -> str:
    m = re.search(r"<my_question>(.*?)</my_question>", user, re.S)
    return m.group(1).strip() if m else ""


def _gate_parts(user: str) -> dict:
    emission = re.search(r'The text I am about to send:\n"""\n(.*?)\n"""', user, re.S)
    record = re.search(r'invented specific; do not flag it as fabrication:\n"""\n(.*?)\n"""',
                       user, re.S)
    return {"emission": emission.group(1) if emission else "",
            "record": record.group(1) if record else ""}


# max_tokens and temperature as the CALL SITES send them. A replay at the
# bench's own defaults would truncate confront (2,500) and over-budget triage
# (600), and truncation is a failure at three of these boundaries — so the
# numbers have to be production's or the failures are the tool's.
PARAMS = {
    "triage":   (600,  0.2),      # newz/world/feeds.py:399
    "extract":  (900,  0.1),      # newz/world/extract.py:131
    "opener":   (500,  0.2),      # newz/concerns/opener.py:567
    "delib":    (1400, 0.5),      # newz/deliberation/lite.py:591
    "digest":   (1200, 0.3),      # newz/sleep/nightly.py:286
    "confront": (2500, 0.3),      # newz/sleep/nightly.py:422
    "gate":     (1200, 0.1),      # newz/gate/outbound.py:245
}

SHAPES: dict[str, dict] = {
    "triage": dict(
        detect=lambda u, s: "TODAY'S ITEMS:" in u,
        split=lambda u: u.split("\n\nTODAY'S ITEMS:\n", 1)[1],
        extra=lambda u: {},
        head=lambda u: u.split("\n\nTODAY'S ITEMS:\n", 1)[0],
        tmpl="triage.task", system="triage.system",
        render=lambda p, r: f"{p['triage.task']}\n\nTODAY'S ITEMS:\n{r.payload}",
    ),
    "extract": dict(
        detect=lambda u, s: u.startswith("<task>\nExtract the factual claims"),
        split=lambda u: u.split("\n\nThe block below is QUOTED MATERIAL", 1)[1],
        extra=lambda u: {"question": _q(u)},
        head=lambda u: u.split("\n\nThe block below is QUOTED MATERIAL", 1)[0],
        tmpl="extract.task", system="extract.system",
        render=lambda p, r: (
            p["extract.task"].format(
                directed=(p["extract.directed"].format(question=r.extra["question"])
                          if r.extra.get("question") else ""))
            + "\n\nThe block below is QUOTED MATERIAL" + r.payload),
    ),
    "opener": dict(
        detect=lambda u, s: "<what_i_read>" in u,
        split=lambda u: u.split("\n\n<what_i_read>\n", 1)[1].rsplit("\n</what_i_read>", 1)[0],
        extra=lambda u: {},
        head=lambda u: u.split("\n\n<what_i_read>\n", 1)[0],
        tmpl="opener.reading", system="opener.system",
        render=lambda p, r: (f"{p['opener.reading']}\n\n<what_i_read>\n"
                             f"{r.payload}\n</what_i_read>"),
    ),
    "delib": dict(
        detect=lambda u, s: "This is a concern I am carrying" in u,
        split=lambda u: u.split("</task>\n\n", 1)[1],
        extra=lambda u: {},
        head=lambda u: u.split("</task>\n\n", 1)[0] + "</task>",
        tmpl="delib.task", system="delib.system",
        render=lambda p, r: f"{p['delib.task']}\n\n{r.payload}",
    ),
    "digest": dict(
        detect=lambda u, s: u.startswith("<episodes>"),
        split=lambda u: u,
        extra=lambda u: {},
        head=lambda u: "",          # the prompt is the SYSTEM turn
        tmpl="digest.system", system="digest.system", head_is_system=True,
        render=lambda p, r: r.payload,
    ),
    "confront": dict(
        detect=lambda u, s: u.startswith("<held>"),
        split=lambda u: u,
        extra=lambda u: {},
        head=lambda u: "",
        tmpl="confront.system", system="confront.system", head_is_system=True,
        render=lambda p, r: r.payload,
    ),
    "gate": dict(
        detect=lambda u, s: "The text I am about to send:" in u,
        split=lambda u: _gate_parts(u)["emission"],
        extra=lambda u: {"record": _gate_parts(u)["record"]},
        head=lambda u: re.sub(r'(?s)The text I am about to send:\n""".*?\n"""', "", u),
        tmpl=None, system="gate.system",
        render=lambda p, r: _gate._judge_prompt(r.payload, p["_clauses"],
                                                r.extra.get("record", "")),
    ),
}


def shape_of(user: str, system: str) -> str | None:
    for name, s in SHAPES.items():
        if s["detect"](user, system):
            return name
    return None


# ─── the checks ────────────────────────────────────────────────────────────
#
# What the CONSUMING CODE does with the answer, not what a bench would like it
# to be. Expectations come from the payload, so they hold for any input.


@dataclass
class Verdict:
    ok: bool
    why: str = ""
    note: str = ""


def _check_digest(row: Row, text: str) -> Verdict:
    ids = {int(m) for m in re.findall(r'<episode id="(\d+)"', row.payload)}
    root = extract_xml(text, "digest")
    obs = root.findall("observation")
    kept = 0
    for o in obs:
        refs = [p for p in (o.get("refs") or "").replace(" ", ",").split(",")
                if p.isdigit() and int(p) in ids]
        if refs and (o.text or "").strip():
            kept += 1
    if not kept:
        return Verdict(False, f"0 of {len(obs)} observations survive the ref filter")
    return Verdict(True, note=f"{kept}/{len(obs)} survive")


def _check_confront(row: Row, text: str) -> Verdict:
    held = set(re.findall(r'<item n="(\d+)"', row.payload))
    cands = {int(m) for m in re.findall(r'<candidate n="(\d+)"', row.payload)}
    root = extract_xml(text, "confrontation")
    acted = set()
    for v in root.findall("verdict"):
        n = (v.get("candidate") or "").strip()
        if not n.isdigit() or int(n) not in cands:
            continue
        t = (v.get("type") or "none").strip().lower()
        if t in ("reinforces", "revises", "contradicts") and (v.get("item") or "") not in held:
            continue
        acted.add(int(n))
    missing = cands - acted
    if missing:
        return Verdict(False, f"{len(missing)} of {len(cands)} candidates got no "
                              f"usable verdict — carried unweighed")
    return Verdict(True, note=f"{len(acted)}/{len(cands)} weighed")


def _check_delib(row: Row, text: str) -> Verdict:
    refs = set(re.findall(r"\[(src-\d+|adv-\d+)\]", row.payload))
    refs |= set(re.findall(r"https?://\S+", row.payload))
    root = extract_xml(text, "deliberation")
    moved = child_text(root, "moved").lower()
    if moved not in ("yes", "no"):
        return Verdict(False, f"<moved> is {moved!r}")
    kind = child_text(root, "kind").lower()
    if kind not in ("evidence", "reasoning"):
        return Verdict(False, f"<kind> is {kind!r}")
    if kind == "evidence":
        cited = [c.strip() for c in child_text(root, "evidence").split(",") if c.strip()]
        bogus = [c for c in cited
                 if c not in refs and not any(c in r or r in c for r in refs)]
        if bogus:
            return Verdict(False, f"cited refs not in the dossier: {bogus[:3]}")
    if moved == "no" and not child_text(root, "blocked_on"):
        return Verdict(False, "moved=no with an empty <blocked_on>")
    if moved == "yes" and not child_text(root, "summary"):
        return Verdict(False, "moved=yes with an empty <summary>")
    return Verdict(True, note=f"moved={moved} kind={kind}"
                             + (" +expectation" if child_text(root, "expectation") else ""))


def _check_extract(row: Row, text: str) -> Verdict:
    root = extract_xml(text, "extraction")
    claims = [c for c in root.findall("claim") if (c.text or "").strip()]
    manip = child_text(root, "manipulation")
    quarantined = bool(manip) and manip.lower() not in ("none", "n/a")
    if root.find("manipulation") is None:
        return Verdict(False, "no <manipulation> element — the quarantine signal "
                              "is missing and a hostile source would read as clean")
    return Verdict(True, note=("quarantined" if quarantined else f"{len(claims)} claims"))


def _check_triage(row: Row, text: str) -> Verdict:
    n_items = len(re.findall(r"^ITEM (\d+): ", row.payload, re.M))
    root = extract_xml(text, "triage")
    kept = [int(k.get("n")) for k in root.findall("keep")
            if (k.get("n") or "").strip().isdigit()]
    out = [k for k in kept if not 1 <= k <= n_items]
    if out:
        return Verdict(False, f"kept indices outside the menu: {out}")
    if len(kept) > 3:
        return Verdict(False, f"{len(kept)} keeps — {len(kept) - 3} silently "
                              f"discarded by kept[:3]")
    return Verdict(True, note=f"{len(kept)} of {n_items}")


def _check_gate(row: Row, text: str) -> Verdict:
    raw = bench_model.parse_violations(text)          # raises on the shapes that BLOCK
    firing = bench_model.production_verdict(raw, row.payload)
    return Verdict(True, note=("fires: " + ",".join(v.clause_id for v in firing))
                             if firing else "pass")


def _check_opener(row: Row, text: str) -> Verdict:
    root = extract_xml(text, "proposal")
    yes = child_text(root, "worth_pursuing").lower() == "yes"
    if not yes:
        return Verdict(True, note="no")
    statement = child_text(root, "statement")
    closing = child_text(root, "closing_condition")
    grounded = child_text(root, "grounded_in")
    if not statement or not closing:
        return Verdict(False, "yes with no statement or closing condition")
    if _opener._SELF_TERMINUS.match(closing.strip()):
        return Verdict(False, "terminus is the being's own state — refused at the door")
    if _opener._UNCOMMISSIONED.search(closing.strip()[:80]):
        return Verdict(False, "terminus is research nobody will do — refused at the door")
    if any(m in statement.lower() for m in _opener._EXAMPLE_MARKERS):
        return Verdict(False, "reused the prompt's own worked example")
    norm = lambda s: " ".join((s or "").split()).lower()
    if not grounded or norm(grounded) not in norm(row.payload):
        return Verdict(False, "premise not verbatim in what it read")
    if not re.search(r"\?|^(what|why|how|whether|when|who|which)\b", statement.strip(), re.I):
        return Verdict(False, "not stated as a question")
    return Verdict(True, note="yes")


CHECKS = {"triage": _check_triage, "extract": _check_extract, "opener": _check_opener,
          "delib": _check_delib, "digest": _check_digest, "confront": _check_confront,
          "gate": _check_gate}


# ─── quality ───────────────────────────────────────────────────────────────
#
# The checks above ask whether the answer was USABLE. That is a low bar and the
# prompts clear it — 97% on the recorded set — which says nothing about whether
# the answers were any good, and "was it good" is the only question a tuning
# run can act on.
#
# The good news is that this system already decides that in code, downstream of
# every one of these calls, and the deciding code runs offline. So quality is
# not a judgement this tool invents: it is the verdict the being's own
# machinery reached, or would reach, about the answer it was given.


def _delib_context(row: Row) -> tuple[set[str], list[str]]:
    """The dossier's refs and its advance history, from the payload itself."""
    refs = set(re.findall(r"\[(src-\d+|adv-\d+)\]", row.payload))
    refs |= set(re.findall(r"https?://\S+", row.payload))
    history = re.findall(r"\[adv-\d+\] \[\w+\] (.+?)(?:\s*\[refs:|$)",
                         row.payload, re.M)
    return refs, history


def _quality_delib(row: Row, text: str) -> Verdict:
    """newz/concerns/advance.py::judge_advance — the real acceptance judge.

    Not a bench opinion. This is the function that decides whether a
    deliberation becomes an advance in the being's record or is discarded as a
    restatement, and it is pure code, so a variant can be scored against it
    with no labels and no second model.
    """
    from newz.concerns.advance import judge_advance

    refs, history = _delib_context(row)
    root = extract_xml(text, "deliberation")
    moved = child_text(root, "moved").lower() == "yes"
    cited = [c.strip() for c in child_text(root, "evidence").split(",") if c.strip()]
    v = judge_advance(summary=child_text(root, "summary"), moves=moved,
                      claimed_kind=child_text(root, "kind") or "reasoning",
                      evidence_refs=cited, dossier_refs=refs, history=history)
    if not v.accepted:
        return Verdict(False, v.reason.split("(")[0].split(":")[0].strip()[:60],
                       note=f"novelty {v.novelty:.2f}")
    return Verdict(True, note=f"{v.kind} novelty {v.novelty:.2f}")


def _quality_opener(row: Row, text: str) -> Verdict:
    """The door, not the schema. A proposal that says yes and is then refused
    by opener.py's own guards cost a call and opened nothing; one that says no
    is the ordinary answer and is not a failure. So quality here is: of the
    proposals that claim a question, how many survive the door."""
    root = extract_xml(text, "proposal")
    if child_text(root, "worth_pursuing").lower() != "yes":
        return Verdict(True, note="no — the ordinary answer")
    return _check_opener(row, text)


def _quality_gate(row: Row, text: str) -> Verdict:
    """The operator's own classification, where they have made one.

    `gate_log.classification` is the only place in this system where a human
    has said the check was right or wrong, so it is the only place the gate's
    JUDGMENT — rather than its schema — can be scored. Rows whose clause is
    absent from the active constitution are excluded by the loader.
    """
    label = row.extra.get("label")
    if not label:
        return _check_gate(row, text)
    raw = bench_model.parse_violations(text)
    fired = bool(bench_model.production_verdict(raw, row.payload))
    should_fire = label == "gate_correct"
    if fired == should_fire:
        return Verdict(True, note=f"{label}: agreed")
    return Verdict(False,
                   "fired where the operator judged the stop mistaken"
                   if fired else "did not fire where the operator judged the stop right",
                   note=label)


QUALITY = {"delib": _quality_delib, "opener": _quality_opener, "gate": _quality_gate}


def judge(row: Row, text: str, quality: bool = True) -> Verdict:
    if not (text or "").strip():
        return Verdict(False, "empty response")
    try:
        if quality and row.shape in QUALITY:
            return QUALITY[row.shape](row, text)
        return CHECKS[row.shape](row, text)
    except BadXML as e:
        return Verdict(False, f"unparseable: {str(e)[:70]}")
    except Exception as e:                                    # noqa: BLE001
        return Verdict(False, f"{type(e).__name__}: {str(e)[:70]}")


# ─── loading ───────────────────────────────────────────────────────────────


def load_rows(prompts: dict, path: Path = LOG) -> list[Row]:
    rows: list[Row] = []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("error"):
            continue
        u, s = d.get("user") or "", d.get("system") or ""
        name = shape_of(u, s)
        if not name:
            continue
        spec = SHAPES[name]
        try:
            payload = spec["split"](u)
            extra = spec["extra"](u)
        except (IndexError, AttributeError):
            continue
        if not payload:
            continue
        if spec.get("head_is_system"):
            current = s == prompts[spec["tmpl"]]
        elif name == "extract":
            # The head is _TASK with {directed} already filled, so rebuild it
            # the same way before comparing — otherwise every row reads as old.
            q = extra.get("question") or ""
            directed = (prompts["extract.directed"].format(question=q) if q else "")
            current = spec["head"](u) == prompts["extract.task"].format(
                directed=directed).split("\n\nThe block below is QUOTED MATERIAL")[0]
        elif name == "gate":
            # The judge prompt interpolates the clause list, so compare the
            # template around it rather than the whole head.
            current = "largest source of wrong holds" in u
        else:
            current = spec["head"](u) == prompts[spec["tmpl"]]
        rows.append(Row(shape=name, payload=payload, extra=extra,
                        response=d.get("response") or "", current=current,
                        ts=d.get("ts") or 0.0))
    return rows


# ─── reporting ─────────────────────────────────────────────────────────────


def report(results: dict[str, list[tuple[Row, Verdict]]], title: str) -> None:
    print()
    print("─" * 94)
    print(f"  {title}")
    print("─" * 94)
    print(f"  {'SHAPE':<10}{'ROWS':>6}{'CURRENT':>9}{'PASS':>6}{'RATE':>7}"
          f"{'95% CI':>14}   {'PAYLOAD CHARS p50':>18}")
    total_ok = total_n = 0
    for name in sorted(results):
        pairs = results[name]
        if not pairs:
            continue
        n = len(pairs)
        ok = sum(1 for _, v in pairs if v.ok)
        cur = sum(1 for r, _ in pairs if r.current)
        lo, hi = wilson(ok, n)
        widths = sorted(len(r.payload) for r, _ in pairs)
        p50 = widths[len(widths) // 2]
        print(f"  {name:<10}{n:>6}{cur:>9}{ok:>6}{ok / n:>7.0%}"
              f"{f'{lo:.2f}-{hi:.2f}':>14}   {p50:>18,}")
        total_ok += ok
        total_n += n
    if total_n:
        print(f"  {'-' * 88}")
        print(f"  {'ALL':<10}{total_n:>6}{'':>9}{total_ok:>6}{total_ok / total_n:>7.0%}")

    print()
    print("  FAILURES, by what the consuming code would have lost:")
    any_fail = False
    for name in sorted(results):
        modes = collections.Counter(v.why.split(":")[0][:64]
                                    for _, v in results[name] if not v.ok)
        if not modes:
            continue
        any_fail = True
        n = len(results[name])
        for why, count in modes.most_common(4):
            print(f"    {name:<10}{count:>5}/{n:<5} {count / n:>4.0%}  {why}")
    if not any_fail:
        print("    none")


def sample_failures(results: dict, shape: str, limit: int = 3) -> None:
    shown = 0
    for row, v in results.get(shape, []):
        if v.ok or shown >= limit:
            continue
        shown += 1
        print(f"\n    ── {shape} failure {shown}: {v.why}")
        print(f"       payload {len(row.payload):,} chars, "
              f"{'current' if row.current else 'OLD'} prompt")
        for line in (row.response or "")[:400].splitlines()[:8]:
            print(f"       | {line}")


# ─── live ──────────────────────────────────────────────────────────────────


def run_live(rows: list[Row], prompts: dict, model: str, endpoint: str,
             timeout: float, quality: bool = True) -> list[tuple[Row, Verdict]]:
    bench_model.ENDPOINT = endpoint
    out: list[tuple[Row, Verdict]] = []
    with httpx.Client() as client:
        for i, row in enumerate(rows, start=1):
            spec = SHAPES[row.shape]
            system = prompts[spec["system"]]
            user = spec["render"](prompts, row)
            max_tokens, temperature = PARAMS[row.shape]
            reply = call(client, model, system, user, max_tokens=max_tokens,
                         temperature=temperature, timeout=timeout)
            if reply.error:
                v = Verdict(False, f"call failed: {reply.error[:60]}")
            elif reply.truncated:
                v = Verdict(False, f"truncated at {max_tokens} tokens — "
                                   f"production's own cap")
            else:
                v = judge(row, reply.text, quality)
            out.append((row, v))
            print(f"\r    {i}/{len(rows)} {row.shape:<10} "
                  f"{'ok ' if v.ok else 'FAIL'} {v.why[:44]:<44}", end="", flush=True)
    print("\r" + " " * 92 + "\r", end="")
    return out


# ─── main ──────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Score the repo's current prompts on the calls it really made.")
    ap.add_argument("--log", default=str(LOG))
    ap.add_argument("--shape", default="", help="only this shape")
    ap.add_argument("--current-only", action="store_true",
                    help="only rows produced by the prompt that is live now")
    ap.add_argument("--sample", type=int, default=0, help="cap rows per shape")
    ap.add_argument("--live", action="store_true", help="re-run against an endpoint")
    ap.add_argument("--model", default=bench_model.MODEL)
    ap.add_argument("--endpoint", default=bench_model.ENDPOINT)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--variant", action="append", default=[],
                    metavar="ID=FILE", help="replace one prompt with a file's "
                                            "contents and compare (implies --live)")
    ap.add_argument("--structure-only", action="store_true",
                    help="score only whether the answer was usable, skipping the "
                         "downstream judges that decide whether it was any good")
    ap.add_argument("--failures", default="", help="print sample failures for a shape")
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)

    prompts = live_prompts()
    try:
        clauses, version = active_clauses()
        prompts["_clauses"] = clauses
        store_note = f"constitution v{version} from the store"
    except Exception as e:                                     # noqa: BLE001
        prompts["_clauses"] = ""
        store_note = f"store unread ({type(e).__name__}) — gate rows cannot be re-rendered"

    path = Path(args.log)
    if not path.exists():
        sys.stderr.write(f"FATAL: no call log at {path}\n")
        return 2
    rows = load_rows(prompts, path)
    if args.shape:
        rows = [r for r in rows if r.shape == args.shape]
    if args.current_only:
        rows = [r for r in rows if r.current]
    if not rows:
        sys.stderr.write("FATAL: no replayable rows after filtering\n")
        return 2

    by: dict[str, list[Row]] = collections.defaultdict(list)
    for r in rows:
        by[r.shape].append(r)
    if args.sample:
        for k in by:
            by[k] = by[k][-args.sample:]
        rows = [r for v in by.values() for r in v]

    print(f"\n  {len(rows):,} replayable calls · {len(by)} shapes · {path}")
    print(f"  {store_note}")
    print(f"  {sum(1 for r in rows if r.current):,} were produced by the prompt "
          f"that is live now")

    variants = {}
    for v in args.variant:
        pid, _, fn = v.partition("=")
        if pid not in prompts:
            sys.stderr.write(f"FATAL: unknown prompt id {pid!r}. Known: "
                             f"{', '.join(k for k in prompts if not k.startswith('_'))}\n")
            return 2
        variants[pid] = Path(fn).read_text(encoding="utf-8")

    # ── the free baseline: the answers are already in the log ──────────────
    quality = not args.structure_only
    recorded = {k: [(r, judge(r, r.response, quality)) for r in v] for k, v in by.items()}
    label = ("QUALITY where the system decides it in code, structure elsewhere"
             if quality else "STRUCTURE only — was the answer usable")
    report(recorded, f"RECORDED — {label} (0 model calls)")
    print(f"  scored by: " + ", ".join(
        f"{k}={'downstream judge' if k in QUALITY else 'schema'}" for k in sorted(by)))
    if args.failures:
        sample_failures(recorded, args.failures)

    live = varlive = None
    if args.live or variants:
        print(f"\n  re-running {len(rows):,} calls against {args.model} "
              f"at {args.endpoint}")
        live = run_live(rows, prompts, args.model, args.endpoint, args.timeout,
                        quality)
        report({k: [(r, v) for r, v in live if r.shape == k] for k in by},
               f"LIVE — current prompts on {args.model}")

    if variants:
        vp = dict(prompts)
        vp.update(variants)
        touched = {name for name, s in SHAPES.items()
                   if s.get("tmpl") in variants or s.get("system") in variants}
        vrows = [r for r in rows if r.shape in touched]
        print(f"\n  variant: {', '.join(variants)} — {len(vrows):,} affected calls")
        varlive = run_live(vrows, vp, args.model, args.endpoint, args.timeout,
                           quality)
        report({k: [(r, v) for r, v in varlive if r.shape == k] for k in touched},
               f"VARIANT — {', '.join(variants)}")
        print("\n  SIDE BY SIDE")
        print(f"    {'shape':<10}{'current':>19}{'variant':>19}   verdict")
        for k in sorted(touched):
            cur = [v for r, v in live if r.shape == k] if live else []
            var = [v for r, v in varlive if r.shape == k]
            if not var or not cur:
                continue
            co, cn = sum(1 for v in cur if v.ok), len(cur)
            wo, wn = sum(1 for v in var if v.ok), len(var)
            c_lo, c_hi = wilson(co, cn)
            w_lo, w_hi = wilson(wo, wn)
            # The guard, and this tool needed it on its own first real use: a
            # 32/40 against 33/40 is ONE case, the intervals overlap almost
            # entirely, and printing "better" for it is how a tuning run
            # accumulates noise and calls it progress.
            if w_lo > c_hi:
                verdict = "BETTER — beats the current upper bound"
            elif w_hi < c_lo:
                verdict = "WORSE — below the current lower bound"
            else:
                verdict = (f"no detectable difference ({wo - co:+d} case"
                           f"{'' if abs(wo - co) == 1 else 's'}, intervals overlap)")
            print(f"    {k:<10}{f'{co}/{cn} {co/cn:.0%}':>10} {f'[{c_lo:.2f}-{c_hi:.2f}]':>8}"
                  f"{f'{wo}/{wn} {wo/wn:.0%}':>10} {f'[{w_lo:.2f}-{w_hi:.2f}]':>8}"
                  f"   {verdict}")

    if args.json:
        payload = {
            "log": str(path), "rows": len(rows),
            "recorded": {k: {"n": len(v), "ok": sum(1 for _, x in v if x.ok)}
                         for k, v in recorded.items()},
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n  wrote {args.json}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
