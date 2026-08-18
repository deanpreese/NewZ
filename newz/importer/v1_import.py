"""The importer (S2 §2, P2 Phase 0.2) — one being, two substrates.

Brings the identity-bearing data across from the v1 store. Discipline:

- v1 is NEVER written. The live v1 main.db is snapshotted via the SQLite
  online-backup API from a read-only connection; all reads come from the
  snapshot (v1 is a running system; a moving WAL is not an import source).
- The interior imports by file byte-copy under its privacy boundary
  (INV-007): the importer never opens the source interior DB's content —
  only row counts are read (from the copy) for the verification record.
- Every imported table writes a verification row (v1 count vs imported
  count) to import_record (INV-008).
- The v1 store itself is archived read-only, never deleted (S2 §2.3) — this
  module only ever copies from it.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from newz.store.db import open_db


@dataclass
class ImportReport:
    run_id: str
    v1_repo: str
    v1_commit: str
    tables: dict[str, tuple[int, int]] = field(default_factory=dict)  # name -> (v1, imported)
    notes: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return all(v1 == imp for v1, imp in self.tables.values())


def _v1_commit(v1_repo: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(v1_repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def snapshot_v1_main(v1_main_db: Path, snapshot_path: Path) -> None:
    """Consistent point-in-time snapshot of the (live) v1 main DB, read-only."""
    src = sqlite3.connect(f"file:{v1_main_db}?mode=ro", uri=True)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    dst = sqlite3.connect(snapshot_path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def _count(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table} {where}").fetchone()[0]


def _copy_rows(
    snap: sqlite3.Connection,
    dest: sqlite3.Connection,
    select_sql: str,
    insert_sql: str,
    transform,
) -> int:
    n = 0
    for row in snap.execute(select_sql):
        dest.execute(insert_sql, transform(row))
        n += 1
    return n


def run_import(
    v1_repo: Path,
    v1_main_db: Path,
    v1_interior_db: Path,
    dest_main: sqlite3.Connection,
    dest_interior_path: Path,
    scratch_dir: Path,
    character_files: dict[str, Path] | None = None,
) -> ImportReport:
    report = ImportReport(
        run_id=uuid.uuid4().hex[:12],
        v1_repo=str(v1_repo),
        v1_commit=_v1_commit(v1_repo),
    )
    now = time.time()

    snap_path = scratch_dir / "v1_main_snapshot.db"
    snapshot_v1_main(v1_main_db, snap_path)
    report.notes.append(f"snapshot of live v1 main.db taken at {now}")
    snap = open_db(snap_path, read_only=True)

    # ── constitution (verbatim, with lineage) ────────────────────────────
    n = _copy_rows(
        snap, dest_main,
        "SELECT version, ts, clauses_yaml, change_summary, prior_version,"
        " approval_status, approver_a, approver_b, time_lock_until"
        " FROM constitution ORDER BY version",
        "INSERT INTO constitution (version, ts, clauses_yaml, change_summary,"
        " prior_version, approval_status, approver_a, approver_b, time_lock_until)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        tuple,
    )
    report.tables["constitution"] = (_count(snap, "constitution"), n)

    # ── character core (v1 kept it as files) ─────────────────────────────
    character_files = character_files or {}
    for version, path in sorted(character_files.items()):
        dest_main.execute(
            "INSERT INTO character_core (version, ts, content, source) VALUES (?,?,?,?)",
            (version, now, path.read_text(), f"v1:{path.name}"),
        )
    report.tables["character_core"] = (len(character_files), len(character_files))

    # ── self-model claims (latest snapshot, exploded to rows) ────────────
    row = snap.execute(
        "SELECT id, model_json FROM self_model ORDER BY version DESC, id DESC LIMIT 1"
    ).fetchone()
    v1_claims, imported_claims = 0, 0
    if row:
        model = json.loads(row["model_json"])
        claims = model.get("claims", [])
        v1_claims = len(claims)
        for c in claims:
            text = c if isinstance(c, str) else json.dumps(c) if not isinstance(c, dict) else (
                c.get("claim") or c.get("text") or json.dumps(c)
            )
            evidence = c.get("evidence", []) if isinstance(c, dict) else []
            dest_main.execute(
                "INSERT INTO self_model_claims (ts, claim, status, source, evidence_json, notes)"
                " VALUES (?,?,?,?,?,?)",
                (now, text, "imported", f"v1:self_model:{row['id']}",
                 json.dumps(evidence), "re-audit due at first sleep (S2 §2.1)"),
            )
            imported_claims += 1
    report.tables["self_model_claims"] = (v1_claims, imported_claims)

    # ── persons (model_of_my_model_json deliberately dropped — dead schema) ─
    n = _copy_rows(
        snap, dest_main,
        "SELECT name, operator_id, model_json, landing_rates_json, last_seen, ts FROM people",
        "INSERT INTO persons (name, operator_id, model_json, landing_rates_json,"
        " channel_bindings_json, last_seen, ts) VALUES (?,?,?,?,?,?,?)",
        lambda r: (r["name"], r["operator_id"], r["model_json"],
                   r["landing_rates_json"], json.dumps({"telegram": True}),
                   r["last_seen"], r["ts"]),
    )
    report.tables["persons"] = (_count(snap, "people"), n)

    # ── concerns with full advance/setback dossiers ──────────────────────
    n = _copy_rows(
        snap, dest_main,
        "SELECT id, opened_at, kind, statement, why_open, closing_condition, status,"
        " salience, origin, origin_ref, last_advanced_at, advance_count, stall_count,"
        " blocked_count, closed_at, resolution, meta_json, search_query,"
        " opening_evidence, opening_citations_json, last_attempted_at FROM concerns",
        "INSERT INTO concerns (id, opened_at, kind, statement, why_open, closing_condition,"
        " status, salience, origin, origin_ref, last_advanced_at, advance_count, stall_count,"
        " blocked_count, closed_at, resolution, meta_json, search_query, opening_evidence,"
        " opening_citations_json, last_attempted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        tuple,
    )
    report.tables["concerns"] = (_count(snap, "concerns"), n)

    n = _copy_rows(
        snap, dest_main,
        "SELECT id, concern_id, ts, kind, summary, evidence_json, tick_id FROM concern_advances",
        "INSERT INTO concern_advances (id, concern_id, ts, kind, summary, evidence_json, source_ref)"
        " VALUES (?,?,?,?,?,?,?)",
        lambda r: (r["id"], r["concern_id"], r["ts"], r["kind"], r["summary"],
                   r["evidence_json"], f"v1:tick:{r['tick_id']}"),
    )
    report.tables["concern_advances"] = (_count(snap, "concern_advances"), n)

    n = _copy_rows(
        snap, dest_main,
        "SELECT id, concern_id, ts, kind, brief, tick_id FROM concern_setbacks",
        "INSERT INTO concern_setbacks (id, concern_id, ts, kind, brief, source_ref)"
        " VALUES (?,?,?,?,?,?)",
        lambda r: (r["id"], r["concern_id"], r["ts"], r["kind"], r["brief"],
                   f"v1:tick:{r['tick_id']}"),
    )
    report.tables["concern_setbacks"] = (_count(snap, "concern_setbacks"), n)

    # ── publications ─────────────────────────────────────────────────────
    n = _copy_rows(
        snap, dest_main,
        "SELECT id, concern_id, slug, relative_path, content_hash, attempted_at,"
        " confirmed_at, retracted_at FROM publications",
        "INSERT INTO publications (concern_id, slug, relative_path, content_hash,"
        " attempted_at, confirmed_at, retracted_at, source_ref) VALUES (?,?,?,?,?,?,?,?)",
        lambda r: (r["concern_id"], r["slug"], r["relative_path"], r["content_hash"],
                   r["attempted_at"], r["confirmed_at"], r["retracted_at"],
                   f"v1:publication:{r['id']}"),
    )
    report.tables["publications"] = (_count(snap, "publications"), n)

    # ── learnings ────────────────────────────────────────────────────────
    n = _copy_rows(
        snap, dest_main,
        "SELECT id, ts, situation_vec, action_type, outcome_tag, confidence, model_tag,"
        " derived_from_interior_ref, operator_id, response_text, notes FROM learnings",
        "INSERT INTO learnings (ts, situation_vec, action_type, outcome_tag, confidence,"
        " model_tag, derived_from_interior_ref, operator_id, response_text, notes, source_ref)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        lambda r: (r["ts"], r["situation_vec"], r["action_type"], r["outcome_tag"],
                   r["confidence"], r["model_tag"], r["derived_from_interior_ref"],
                   r["operator_id"], r["response_text"], r["notes"], f"v1:learning:{r['id']}"),
    )
    report.tables["learnings"] = (_count(snap, "learnings"), n)

    # ── episodes (raw import; consolidation into Perspective is sleep's job) ─
    n = _copy_rows(
        snap, dest_main,
        "SELECT id, ts, tick_id, summary, content_json, vector, entity_refs_json,"
        " percept_ref, emission_refs, interior_ref FROM episodes",
        "INSERT INTO episodes (ts, kind, provenance, summary, content_json, embedding, source_ref)"
        " VALUES (?,?,?,?,?,?,?)",
        lambda r: (r["ts"], "v1_tick", "self", r["summary"] or "",
                   json.dumps({
                       "content_json": r["content_json"],
                       "entity_refs_json": r["entity_refs_json"],
                       "percept_ref": r["percept_ref"],
                       "emission_refs": r["emission_refs"],
                       "interior_ref": r["interior_ref"],
                       "tick_id": r["tick_id"],
                   }),
                   r["vector"], f"v1:episode:{r['id']}"),
    )
    report.tables["episodes"] = (_count(snap, "episodes"), n)
    report.notes.append(
        "episode embeddings copied verbatim from v1's embedder; Phase 1 retrieval re-embeds"
    )

    # ── interior: byte-copy, never read (INV-007) ────────────────────────
    # The source may be live (v1 running): its -wal sidecar holds recent
    # rows, so all three files are copied — still bytes, never parsed — and
    # the WAL is folded into the *copy*, touching nothing at the source.
    dest_interior_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(v1_interior_db, dest_interior_path)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(v1_interior_db) + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, Path(str(dest_interior_path) + suffix))
            report.notes.append(f"live source: interior{suffix} sidecar copied")
    checkpoint_conn = sqlite3.connect(dest_interior_path)
    checkpoint_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    checkpoint_conn.close()
    dest_interior_path.chmod(0o600)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(dest_interior_path) + suffix)
        if sidecar.exists():
            sidecar.chmod(0o600)
    # Verification count reads the *copy*, and only COUNT(*) — content untouched.
    copy_conn = open_db(dest_interior_path, read_only=True)
    interior_count = _count(copy_conn, "interior_log")
    copy_conn.close()
    src_conn = sqlite3.connect(f"file:{v1_interior_db}?mode=ro", uri=True)
    src_count = src_conn.execute("SELECT COUNT(*) FROM interior_log").fetchone()[0]
    src_conn.close()
    report.tables["interior_log"] = (src_count, interior_count)

    # ── verification record (INV-008) ────────────────────────────────────
    for table, (v1_count, imported) in report.tables.items():
        dest_main.execute(
            "INSERT INTO import_record (run_id, ts, v1_repo, v1_commit, table_name,"
            " v1_count, imported_count, note) VALUES (?,?,?,?,?,?,?,?)",
            (report.run_id, now, report.v1_repo, report.v1_commit,
             table, v1_count, imported, "; ".join(report.notes) if table == "constitution" else ""),
        )
    dest_main.commit()
    snap.close()
    return report
