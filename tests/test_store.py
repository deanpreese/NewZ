import os
import stat

from newz.store.db import boot_checkpoint, open_db


def test_interior_separate_file_and_0600(tmp_path):
    main = open_db(tmp_path / "newz.db")
    interior = open_db(tmp_path / "interior.db", interior=True)
    main.execute("CREATE TABLE t (x)")
    interior.execute("CREATE TABLE t (x)")
    main.commit()
    interior.commit()

    assert (tmp_path / "newz.db").exists()
    assert (tmp_path / "interior.db").exists()
    mode = stat.S_IMODE(os.stat(tmp_path / "interior.db").st_mode)
    assert mode == 0o600
    main.close()
    interior.close()


def test_boot_checkpoint_runs(tmp_path):
    conn = open_db(tmp_path / "newz.db")
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    boot_checkpoint(conn)
    row = conn.execute("PRAGMA journal_mode").fetchone()
    assert row[0] == "wal"
    conn.close()


def test_read_only_open_refuses_writes(tmp_path):
    rw = open_db(tmp_path / "newz.db")
    rw.execute("CREATE TABLE t (x)")
    rw.commit()
    rw.close()

    ro = open_db(tmp_path / "newz.db", read_only=True)
    import sqlite3

    try:
        ro.execute("INSERT INTO t VALUES (1)")
        raised = False
    except sqlite3.OperationalError:
        raised = True
    assert raised
    ro.close()
