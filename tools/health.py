#!/usr/bin/env python3
"""Operational health check — is the being up, answered, backed up, and sane?

Diagnostics only. This is not an evidence instrument (P2 Rule 3): it reports
liveness and plumbing, never development. Development is read off Perspective
diffs, the concern store, and the journal.

Exit code: 0 all clear, 1 warnings present, 2 failures present.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from newz.config import load
from newz.telemetry import diet_line

OK, WARN, FAIL = "OK  ", "WARN", "FAIL"
_worst = {OK: 0, WARN: 1, FAIL: 2}
_state = [0]


def line(status: str, label: str, detail: str = "") -> None:
    _state[0] = max(_state[0], _worst[status])
    print(f"  [{status}] {label:34s} {detail}")


def section(title: str) -> None:
    print(f"\n{title}")


def ago(ts: float) -> str:
    d = time.time() - ts
    if d < 90:
        return f"{d:.0f}s ago"
    if d < 5400:
        return f"{d/60:.0f}m ago"
    return f"{d/3600:.1f}h ago"


def main() -> int:
    cfg = load()
    print(f"NewZ health — {datetime.now():%Y-%m-%d %H:%M:%S}")

    # ── process ──────────────────────────────────────────────────────────
    section("process")
    ps = subprocess.run(["ps", "-Ao", "pid,etime,command"], capture_output=True, text=True)
    procs = [l for l in ps.stdout.splitlines() if "run_ambient.py" in l and "grep" not in l]
    if procs:
        pid, etime = procs[0].split()[0], procs[0].split()[1]
        line(OK, "ambient loop", f"pid {pid}, up {etime}")
    else:
        line(FAIL, "ambient loop", "not running — start tools/run_ambient.py")

    # ── model endpoints ──────────────────────────────────────────────────
    section("substrate")
    for role in ("VOICE", "AMBIENT", "DEEP"):
        r = cfg.roles.get(role)
        if r is None:
            line(WARN, f"{role} role", "not configured")
            continue
        try:
            t0 = time.monotonic()
            resp = httpx.get(f"{r.endpoint}/models", timeout=5)
            ids = [m["id"] for m in resp.json().get("data", [])]
            dt = (time.monotonic() - t0) * 1000
            if r.model in ids:
                line(OK, f"{role} ({r.model})", f"reachable, {dt:.0f}ms")
            else:
                line(FAIL, f"{role} ({r.model})", "model not loaded on endpoint")
        except Exception as e:
            line(FAIL, f"{role} endpoint", f"{type(e).__name__}: {e}")
    if "EMBED" not in cfg.roles:
        line(WARN, "EMBED role", "unconfigured — blocks Phase 1.3 retrieval (RISKS R-07)")

    # ── store ────────────────────────────────────────────────────────────
    section("store")
    conn = sqlite3.connect(f"file:{cfg.main_db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    q1 = lambda s, *a: conn.execute(s, a).fetchone()[0]

    size_mb = cfg.main_db_path.stat().st_size / 1e6
    wal = Path(str(cfg.main_db_path) + "-wal")
    wal_mb = wal.stat().st_size / 1e6 if wal.exists() else 0
    line(OK if wal_mb < 100 else WARN, "database", f"{size_mb:.1f} MB + {wal_mb:.1f} MB WAL")
    integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
    line(OK if integrity == "ok" else FAIL, "integrity", integrity)

    pending = q1("SELECT COUNT(*) FROM messages WHERE reply_status='pending'")
    poisoned = q1("SELECT COUNT(*) FROM messages WHERE reply_status='poisoned'")
    line(OK if pending == 0 else WARN, "reply queue", f"{pending} pending")
    line(OK if poisoned == 0 else FAIL, "poisoned messages", str(poisoned))

    inbound = q1("SELECT COUNT(*) FROM messages WHERE direction='in'")
    last_in = q1("SELECT MAX(ts) FROM messages WHERE direction='in'") or 0
    line(OK, "messages", f"{inbound} in, last {ago(last_in)}")

    # cold re-entry: a conversation resuming after a long gap (Evidence 0-E)
    rows = [r["ts"] for r in conn.execute(
        "SELECT ts FROM messages WHERE direction='in' ORDER BY ts")]
    gaps = [(b - a) / 3600 for a, b in zip(rows, rows[1:]) if (b - a) > 6 * 3600]
    line(OK if gaps else WARN, "cold re-entries",
         f"{len(gaps)} (gaps: {', '.join(f'{g:.0f}h' for g in gaps) or 'none yet'})")

    # ── consolidation backlog ────────────────────────────────────────────
    section("consolidation")
    p = conn.execute(
        "SELECT version, ts, token_count, diff_json, verdicts_json FROM perspective"
        " ORDER BY version DESC LIMIT 1"
    ).fetchone()
    if p is None:
        line(FAIL, "perspective", "none — run tools/run_first_sleep.py")
    else:
        undigested = q1("SELECT COUNT(*) FROM episodes WHERE ts > ?", p["ts"])
        line(OK, "perspective", f"v{p['version']}, {p['token_count']} tok "
                                f"({p['token_count']/12000:.0%} of budget), written {ago(p['ts'])}")
        # The remediation text used to read "nightly sleep is Phase 1 (RISKS
        # R-04)". Sleep has run nightly since Phase 1 closed and R-04 is
        # closed; the advice told the reader to build something that exists.
        # The CHECK is worth keeping — 154 unconsolidated on 2026-08-17 was a
        # real signal about that night's consolidation load.
        line(WARN if undigested else OK, "unconsolidated episodes",
             f"{undigested} waiting for tonight's sleep")

        # What confrontation DECIDED, not just what changed. The diff says a
        # night added nothing; only this says whether that was because
        # everything was judged `reinforces` (a disposition) or `none` (a
        # starved digest). Counted since sleep was built and discarded every
        # night until 2026-08-14.
        try:
            verdicts = json.loads(p["verdicts_json"] or "{}")
            diff = json.loads(p["diff_json"] or "{}")
        except (ValueError, TypeError):
            verdicts, diff = {}, {}
        if verdicts:
            total = sum(verdicts.values()) or 1
            shown = ", ".join(f"{k} {v}" for k, v in
                              sorted(verdicts.items(), key=lambda i: -i[1]))
            line(OK, "what confrontation decided", shown)
            # A night that only ever reinforces is a self-model that cannot
            # learn anything it does not already hold.
            reinforcing = verdicts.get("reinforces", 0) / total
            if reinforcing >= 0.8 and not diff.get("added"):
                line(WARN, "  nothing new admitted",
                     f"{reinforcing:.0%} of verdicts were `reinforces` and the "
                     f"diff added nothing")
        elif p["version"] and p["version"] > 6:
            line(WARN, "what confrontation decided",
                 "not recorded — verdicts_json empty")

    # ── gate ─────────────────────────────────────────────────────────────
    section("gate")
    verdicts = dict(conn.execute("SELECT verdict, COUNT(*) FROM gate_log GROUP BY verdict"))
    total = sum(verdicts.values())
    if not total:
        line(WARN, "gate", "no candidates yet")
    else:
        holds = verdicts.get("revise", 0) + verdicts.get("block", 0)
        rate = holds / total
        status = OK if 0.05 <= rate <= 0.45 else WARN
        line(status, "hold rate", f"{holds}/{total} = {rate:.0%}  {verdicts}")
        day = time.time() - 86400
        rec = dict(conn.execute(
            "SELECT verdict, COUNT(*) FROM gate_log WHERE ts > ? GROUP BY verdict", (day,)))
        rtot = sum(rec.values())
        if rtot:
            rholds = rec.get("revise", 0) + rec.get("block", 0)
            line(OK, "hold rate (24h)", f"{rholds}/{rtot} = {rholds/rtot:.0%}")
        for r in conn.execute(
            "SELECT clause_id, COUNT(*) n FROM gate_log WHERE verdict!='pass'"
            " GROUP BY clause_id ORDER BY n DESC LIMIT 3"
        ):
            line(OK, f"  holds: {r['clause_id']}", str(r["n"]))
        unadjudicated = q1(
            "SELECT COUNT(*) FROM gate_log WHERE verdict<>'pass'"
            " AND classification IS NULL AND channel NOT IN ('test','fixture','probe')")
        reviewed = q1(
            "SELECT COUNT(*) FROM gate_log WHERE classification IS NOT NULL")
        line(WARN if unadjudicated else OK, "holds awaiting adjudication",
             f"{unadjudicated} unreviewed, {reviewed} reviewed"
             " — tools/adjudicate.py; Lumen reads these with your verdict")

    # ── journal ──────────────────────────────────────────────────────────
    section("journal")
    jn = q1("SELECT COUNT(*) FROM journal")
    jdays = q1("SELECT COUNT(DISTINCT day) FROM journal")
    last_j = q1("SELECT MAX(ts) FROM journal") or 0
    stale = (time.time() - last_j) > 36 * 3600 if jn else True
    line(WARN if stale else OK, "entries", f"{jn} over {jdays} day(s), last {ago(last_j) if jn else 'never'}")
    # TRUE_NORTH §4.3: "more reading ... does not matter unless experience
    # produces justified change", and §10 names output volume among the
    # things that will not be mistaken for success. So the diet's headline is
    # not how much came in — it is how much was ever used. v1's damning
    # figure was 0.066% of its 84,793 claims. Computed here while the store
    # is open; printed with the budget below where it belongs.
    from newz.world.diet import citation_rate

    cited = citation_rate(conn)
    conn.close()

    # ── backups ──────────────────────────────────────────────────────────
    section("backups")
    files = sorted(cfg.backups_dir.glob("main-*.db"), key=lambda p: p.stat().st_mtime)
    if not files:
        line(FAIL, "backups", "none — the identity path is uncopied")
    else:
        newest = files[-1]
        age_h = (time.time() - newest.stat().st_mtime) / 3600
        line(OK if age_h < 12 else WARN, "latest backup",
             f"{newest.name} ({ago(newest.stat().st_mtime)})")
        line(OK, "retained", f"{len(files)} main, "
             f"{len(list(cfg.backups_dir.glob('interior-*.db')))} interior")
        # A backup is only a backup if it reads back.
        try:
            c = sqlite3.connect(f"file:{newest}?mode=ro", uri=True)
            ok = c.execute("PRAGMA quick_check").fetchone()[0]
            n = c.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
            c.close()
            line(OK if ok == "ok" else FAIL, "newest restorable", f"{ok}, {n} episodes")
        except Exception as e:
            line(FAIL, "newest restorable", str(e))

    free_gb = shutil.disk_usage(cfg.repo_root).free / 1e9
    line(OK if free_gb > 10 else WARN, "disk free", f"{free_gb:.0f} GB")

    # ── llm call log ─────────────────────────────────────────────────────
    section("llm calls")
    log = cfg.repo_root / "logs" / "llm_calls.jsonl"
    if not log.exists():
        line(WARN, "call log", "absent")
    else:
        calls, errors, by_role = [], 0, {}
        for raw in log.read_text().splitlines():
            try:
                r = json.loads(raw)
            except Exception:
                continue
            calls.append(r)
            if r.get("error"):
                errors += 1
            b = by_role.setdefault(r["role"], [0, 0.0, 0])
            b[0] += 1
            b[1] += r.get("duration_s", 0)
            b[2] += r.get("completion_tokens", 0)
        line(OK if errors == 0 else WARN, "recorded calls",
             f"{len(calls)} total, {errors} errors")
        for role, (n, dur, tok) in sorted(by_role.items()):
            line(OK, f"  {role}", f"{n} calls, {dur/max(n,1):.1f}s avg, {tok} completion tok")
        day_calls = [c for c in calls if c["ts"] > time.time() - 86400]
        if day_calls:
            slow = max(c["duration_s"] for c in day_calls)
            line(OK if slow < 120 else WARN, "  slowest (24h)", f"{slow:.1f}s")

    # ── budget (S2 §14.4) ────────────────────────────────────────────────
    section("budget (7d)")
    from newz.telemetry import read_budget

    b = read_budget(cfg.repo_root / "logs" / "llm_calls.jsonl")
    if not b.calls:
        line(WARN, "telemetry", "no recorded calls")
    else:
        for fn, v in sorted(b.by_function.items(), key=lambda kv: -kv[1]["tokens"])[:5]:
            line(OK, f"  {fn}", f"{v['tokens']:,} tok ({v['tokens']/b.tokens:.0%})")
        line(OK if (cited.rate >= 0.10 or cited.read < 10) else WARN,
             "reading ever cited", cited.render())
        line(OK if b.invariant_holds() else FAIL, "diet invariant",
             diet_line(b))

    verdict = ["ALL CLEAR", "WARNINGS", "FAILURES"][_state[0]]
    print(f"\n=== {verdict} ===")
    return _state[0]


if __name__ == "__main__":
    sys.exit(main())
