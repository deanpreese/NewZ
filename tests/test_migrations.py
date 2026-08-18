from pathlib import Path

import pytest

from newz.store.db import open_db
from newz.store.migrations import MigrationError, apply_pending, current_version

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"
INTERIOR_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "interior"


def test_apply_initial_main_schema(tmp_path):
    conn = open_db(tmp_path / "newz.db")
    applied = apply_pending(conn, MAIN_SQL)
    assert applied[0] == 1 and applied == sorted(applied)
    assert current_version(conn) == applied[-1]
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"constitution", "concerns", "episodes", "perspective", "import_record",
            "messages", "gate_log"} <= tables
    # Idempotent: nothing pending on re-run.
    assert apply_pending(conn, MAIN_SQL) == []
    conn.close()


def test_apply_interior_schema(tmp_path):
    conn = open_db(tmp_path / "interior.db", interior=True)
    assert apply_pending(conn, INTERIOR_SQL) == [1]
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "interior_log" in tables
    conn.close()


def test_failed_migration_rolls_back(tmp_path):
    bad_dir = tmp_path / "migrations"
    bad_dir.mkdir()
    (bad_dir / "0001_bad.sql").write_text("CREATE TABLE ok (x); INSERT INTO missing VALUES (1);")
    conn = open_db(tmp_path / "newz.db")
    with pytest.raises(MigrationError):
        apply_pending(conn, bad_dir)
    assert current_version(conn) == 0
    conn.close()
