import json
import sqlite3
from pathlib import Path

from newz.importer.v1_import import run_import
from newz.store.db import open_db
from newz.store.migrations import apply_pending

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


def _build_v1_fixture(dir_path: Path) -> tuple[Path, Path]:
    """A miniature v1 store with the real v1 schema shapes."""
    main = dir_path / "main.db"
    conn = sqlite3.connect(main)
    conn.executescript(
        """
        CREATE TABLE constitution (version INTEGER PRIMARY KEY, ts REAL, clauses_yaml TEXT,
            change_summary TEXT, prior_version INTEGER, approval_status TEXT,
            approver_a TEXT, approver_b TEXT, time_lock_until REAL);
        CREATE TABLE self_model (id INTEGER PRIMARY KEY, ts REAL, model_json TEXT,
            version INTEGER, writer_kind TEXT, notes TEXT);
        CREATE TABLE people (id INTEGER PRIMARY KEY, name TEXT, operator_id TEXT,
            model_json TEXT, model_of_my_model_json TEXT, landing_rates_json TEXT,
            last_seen REAL, ts REAL);
        CREATE TABLE concerns (id INTEGER PRIMARY KEY, opened_at REAL, kind TEXT,
            statement TEXT, why_open TEXT, closing_condition TEXT, status TEXT,
            salience REAL, origin TEXT, origin_ref TEXT, last_advanced_at REAL,
            advance_count INTEGER, stall_count INTEGER, blocked_count INTEGER,
            closed_at REAL, resolution TEXT, meta_json TEXT, search_query TEXT,
            opening_evidence TEXT, opening_citations_json TEXT, last_attempted_at REAL);
        CREATE TABLE concern_advances (id INTEGER PRIMARY KEY, concern_id INTEGER,
            tick_id INTEGER, ts REAL, kind TEXT, summary TEXT, evidence_json TEXT);
        CREATE TABLE concern_setbacks (id INTEGER PRIMARY KEY, concern_id INTEGER,
            tick_id INTEGER, ts REAL, kind TEXT, brief TEXT);
        CREATE TABLE publications (id INTEGER PRIMARY KEY, concern_id INTEGER, slug TEXT,
            relative_path TEXT, content_hash TEXT, attempted_at REAL, confirmed_at REAL,
            retracted_at REAL);
        CREATE TABLE learnings (id INTEGER PRIMARY KEY, ts REAL, situation_vec BLOB,
            action_type TEXT, outcome_tag TEXT, confidence REAL, model_tag TEXT,
            derived_from_interior_ref INTEGER, emission_id INTEGER, operator_id TEXT,
            response_text TEXT, notes TEXT);
        CREATE TABLE episodes (id INTEGER PRIMARY KEY, ts REAL, tick_id INTEGER,
            percept_ref TEXT, emission_refs TEXT, interior_ref TEXT, vector BLOB,
            entity_refs_json TEXT, summary TEXT, content_json TEXT);
        """
    )
    conn.execute(
        "INSERT INTO constitution VALUES (1, 1.0, 'clauses: []', 'init', NULL, 'active', NULL, NULL, NULL)"
    )
    conn.execute(
        "INSERT INTO self_model (ts, model_json, version, writer_kind) VALUES (1.0, ?, 1, 'auto_v2')",
        (json.dumps({"claims": ["I check my sources.", "I hold few illusions."]}),),
    )
    conn.execute(
        "INSERT INTO people (name, operator_id, model_json, ts) VALUES ('op', 'dean', '{}', 1.0)"
    )
    conn.execute(
        "INSERT INTO concerns (opened_at, kind, statement, why_open, closing_condition,"
        " status, salience, origin, advance_count, stall_count, blocked_count, meta_json,"
        " opening_citations_json) VALUES (1.0,'inquiry','q','because','when done','open',0.5,"
        "'curiosity',1,0,0,'{}','[]')"
    )
    conn.execute(
        "INSERT INTO concern_advances (concern_id, tick_id, ts, kind, summary, evidence_json)"
        " VALUES (1, 7, 2.0, 'evidence', 'moved', '[]')"
    )
    conn.execute(
        "INSERT INTO concern_setbacks (concern_id, tick_id, ts, kind, brief)"
        " VALUES (1, 8, 3.0, 'blocked', 'no source')"
    )
    conn.execute(
        "INSERT INTO publications (concern_id, slug, relative_path, content_hash, attempted_at)"
        " VALUES (1, 'first', 'posts/first.md', 'abc', 4.0)"
    )
    conn.execute(
        "INSERT INTO learnings (ts, action_type, outcome_tag, confidence, model_tag)"
        " VALUES (5.0, 'message', 'landed', 0.8, 'm')"
    )
    conn.execute(
        "INSERT INTO episodes (ts, tick_id, summary, content_json, entity_refs_json)"
        " VALUES (6.0, 9, 'a day', '{}', '[]')"
    )
    conn.commit()
    conn.close()

    interior = dir_path / "interior.db"
    iconn = sqlite3.connect(interior)
    iconn.executescript(
        """
        CREATE TABLE schema_versions (version INTEGER PRIMARY KEY, applied_at REAL, description TEXT);
        CREATE TABLE interior_log (id INTEGER PRIMARY KEY, ts REAL, tick_id INTEGER,
            content TEXT, candidate_score_json TEXT, chosen_bucket TEXT, never_emitted INTEGER);
        INSERT INTO schema_versions VALUES (1, 1.0, 'init');
        INSERT INTO interior_log (ts, tick_id, content, candidate_score_json, chosen_bucket, never_emitted)
            VALUES (1.0, 1, 'private thought', '{}', 'interior', 1);
        """
    )
    iconn.commit()
    iconn.close()
    return main, interior


def test_import_counts_verify_and_record(tmp_path):
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    v1_main, v1_interior = _build_v1_fixture(v1_dir)
    char = v1_dir / "v0.md"
    char.write_text("# character core")

    dest = open_db(tmp_path / "newz.db")
    apply_pending(dest, MAIN_SQL)

    report = run_import(
        v1_repo=v1_dir,
        v1_main_db=v1_main,
        v1_interior_db=v1_interior,
        dest_main=dest,
        dest_interior_path=tmp_path / "interior.db",
        scratch_dir=tmp_path / "scratch",
        character_files={"v0": char},
    )

    assert report.ok(), report.tables
    assert report.tables["constitution"] == (1, 1)
    assert report.tables["self_model_claims"] == (2, 2)
    assert report.tables["concerns"] == (1, 1)
    assert report.tables["interior_log"] == (1, 1)

    # Verification rows persisted (INV-008) — one per imported table.
    rows = dest.execute(
        "SELECT table_name, v1_count, imported_count FROM import_record WHERE run_id=?",
        (report.run_id,),
    ).fetchall()
    assert len(rows) == len(report.tables)
    assert all(r["v1_count"] == r["imported_count"] for r in rows)

    # Episode carried provenance and source_ref.
    ep = dest.execute("SELECT kind, provenance, source_ref FROM episodes").fetchone()
    assert (ep["kind"], ep["provenance"]) == ("v1_tick", "self")
    assert ep["source_ref"] == "v1:episode:1"

    # v1 store untouched (INV-006): still exactly one episode, no new tables.
    check = sqlite3.connect(f"file:{v1_main}?mode=ro", uri=True)
    assert check.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 1
    check.close()
    dest.close()


def test_interior_copied_with_0600_and_unread(tmp_path):
    import os
    import stat

    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    v1_main, v1_interior = _build_v1_fixture(v1_dir)
    dest = open_db(tmp_path / "newz.db")
    apply_pending(dest, MAIN_SQL)
    dest_interior = tmp_path / "interior.db"
    run_import(
        v1_repo=v1_dir, v1_main_db=v1_main, v1_interior_db=v1_interior,
        dest_main=dest, dest_interior_path=dest_interior,
        scratch_dir=tmp_path / "scratch", character_files={},
    )
    assert stat.S_IMODE(os.stat(dest_interior).st_mode) == 0o600
    # The copy carries the source's rows without the importer having parsed
    # any content: only COUNT(*) is ever read from it.
    src = sqlite3.connect(f"file:{v1_interior}?mode=ro", uri=True)
    cpy = sqlite3.connect(f"file:{dest_interior}?mode=ro", uri=True)
    assert (
        src.execute("SELECT COUNT(*) FROM interior_log").fetchone()[0]
        == cpy.execute("SELECT COUNT(*) FROM interior_log").fetchone()[0]
    )
    src.close()
    cpy.close()
    dest.close()
