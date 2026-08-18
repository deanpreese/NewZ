import os
import sqlite3
import stat

import pytest

from newz.store.backup import BackupError, backup_db, prune, run_backup
from newz.store.db import open_db
from newz.store.migrations import apply_pending
from tests.test_migrations import INTERIOR_SQL, MAIN_SQL


def _make_store(tmp_path):
    main = open_db(tmp_path / "newz.db")
    apply_pending(main, MAIN_SQL)
    for i in range(5):
        main.execute(
            "INSERT INTO episodes (ts, kind, provenance, summary) VALUES (?,?,?,?)",
            (float(i), "conversation", "human:dean", f"episode {i}"),
        )
    main.commit()
    interior = open_db(tmp_path / "interior.db", interior=True)
    apply_pending(interior, INTERIOR_SQL)
    interior.execute(
        "INSERT INTO interior_log (ts, tick_id, content, candidate_score_json,"
        " chosen_bucket, never_emitted) VALUES (1.0, 1, 'private', '{}', 'interior', 1)"
    )
    interior.commit()
    return main, interior


def test_backup_is_verified_and_restorable(tmp_path):
    main, interior = _make_store(tmp_path)
    # Live connections stay open — this is the hot-backup case that matters.
    report = run_backup(tmp_path / "newz.db", tmp_path / "interior.db",
                        tmp_path / "backups")
    assert report.ok()
    assert report.counts["main"] == (5, 5)
    assert report.counts["interior"] == (1, 1)

    copy = next((tmp_path / "backups").glob("main-*.db"))
    conn = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
    assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 5
    assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    conn.close()
    main.close()
    interior.close()


def test_backup_captures_uncheckpointed_wal(tmp_path):
    # Rows written but WAL not checkpointed: the failure mode that cost the
    # first import run its interior count.
    main, interior = _make_store(tmp_path)
    main.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary)"
        " VALUES (99.0,'conversation','human:dean','late row')"
    )
    main.commit()
    assert (tmp_path / "newz.db-wal").exists()

    path, src_n, copy_n = backup_db(tmp_path / "newz.db", tmp_path / "backups",
                                    "main", verify_table="episodes")
    assert (src_n, copy_n) == (6, 6)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    summaries = [r[0] for r in conn.execute("SELECT summary FROM episodes")]
    assert "late row" in summaries
    conn.close()
    main.close()
    interior.close()


def test_interior_backup_is_0600(tmp_path):
    main, interior = _make_store(tmp_path)
    run_backup(tmp_path / "newz.db", tmp_path / "interior.db", tmp_path / "backups")
    copy = next((tmp_path / "backups").glob("interior-*.db"))
    assert stat.S_IMODE(os.stat(copy).st_mode) == 0o600
    main.close()
    interior.close()


def test_unverifiable_backup_is_deleted_and_raises(tmp_path):
    (tmp_path / "backups").mkdir()
    bad = tmp_path / "not-a-db.db"
    bad.write_text("this is not a sqlite database at all")
    with pytest.raises(BackupError):
        backup_db(bad, tmp_path / "backups", "main", verify_table="episodes")
    assert list((tmp_path / "backups").glob("main-*.db")) == []


def test_missing_source_raises(tmp_path):
    with pytest.raises(BackupError):
        backup_db(tmp_path / "nope.db", tmp_path / "backups", "main",
                  verify_table="episodes")


def test_prune_keeps_newest(tmp_path):
    d = tmp_path / "backups"
    d.mkdir()
    made = []
    for i in range(5):
        p = d / f"main-2026080{i}-000000.db"
        p.write_text("x")
        os.utime(p, (1000 + i, 1000 + i))
        made.append(p)
    removed = prune(d, "main", keep=2)
    assert len(removed) == 3
    remaining = sorted(p.name for p in d.glob("main-*.db"))
    assert remaining == [made[3].name, made[4].name]


def test_source_is_not_modified(tmp_path):
    main, interior = _make_store(tmp_path)
    before = (tmp_path / "newz.db").stat().st_size
    run_backup(tmp_path / "newz.db", tmp_path / "interior.db", tmp_path / "backups")
    assert main.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 5
    assert (tmp_path / "newz.db").stat().st_size == before
    main.close()
    interior.close()
