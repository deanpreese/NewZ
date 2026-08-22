"""The clean-room rebuild (P4 epic E3.5, as amended 2026-08-19).

The amendment matters as much as the epic. E3.5 originally closed on a restore
to a second machine — a thing R-11 had already deferred as accepted risk, so it
was written unclosable against the plan's own decision. It now closes on a
byte-comparable rebuild into a clean directory from a **verified backup**, and
what that proves is that the surface is a function of the store and nothing else.

A check that cannot fail proves nothing, so three of these tests break the
rebuild deliberately and assert it is caught.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

from newz.store.db import open_db
from newz.store.migrations import apply_pending
from newz.surface import cleanroom as C
from newz.surface.generate import generate

MAIN_SQL = Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main"


@pytest.fixture
def backups(tmp_path):
    """A store with something in it, backed up the way the being backs up."""
    db = tmp_path / "live.db"
    conn = open_db(db)
    apply_pending(conn, MAIN_SQL)
    conn.execute(
        "INSERT INTO works (ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (time.time(), "concern", 1, "Does the index roll over?", "because",
         "On rolling over", "It is rolling over.", 4, "qwen", 100))
    # A backup holds a life, not just a table: `verify` requires an episode
    # because a store with none restores to nothing (R-37e), and a fixture
    # without one is not the thing being backed up.
    conn.execute(
        "INSERT INTO episodes (ts, kind, provenance, summary, digest_eligible)"
        " VALUES (?,?,?,?,1)",
        (time.time(), "reading", "world:arxiv", "something it read"))
    conn.commit()
    conn.close()

    out = tmp_path / "backups"
    out.mkdir()
    import shutil
    shutil.copy(db, out / "main-20260820-120000.db")
    return out


def test_the_rebuild_is_byte_comparable(backups):
    """E3.5's Done-when. Behavior: two generations over the same restored bytes,
    from different working directories, produce identical files."""
    r = C.rebuild(backups, generate_fn=generate)

    assert r.ok, (r.differing, r.leaked_paths, r.unreadable)
    assert r.pages > 0 and not r.differing


def test_it_rebuilds_from_a_backup_and_not_from_the_live_store(backups, tmp_path):
    """The amendment's own clause. Behavior: the restore path is what §7's
    recoverability depends on, and exercising it is the only way to know it
    works before it is needed."""
    r = C.rebuild(backups, generate_fn=generate)

    assert r.source is not None
    assert r.source.parent == backups
    assert r.source.name.startswith("main-")


def test_a_backup_that_does_not_open_is_reported_not_ignored(tmp_path):
    """Behavior: a backup that cannot be read is not a backup, and finding that
    out during a restore is finding out too late."""
    out = tmp_path / "backups"
    out.mkdir()
    (out / "main-20260820-120000.db").write_text("this is not a database")

    r = C.rebuild(out, generate_fn=generate)

    assert not r.ok and "not a restorable backup" in r.unreadable


def test_no_backup_at_all_is_reported_not_passed(tmp_path):
    """INV-044's shape: nothing to rebuild from is unmeasured, never a pass."""
    empty = tmp_path / "backups"
    empty.mkdir()

    r = C.rebuild(empty, generate_fn=generate)

    assert not r.ok and "nothing to rebuild from" in r.unreadable


def test_a_generator_that_is_not_deterministic_is_caught(backups):
    """A check that cannot fail proves nothing. Behavior: a generator whose
    output depends on the clock produces differing files and the rebuild says
    which."""
    def unstable(conn, out_dir, *, now):
        generate(conn, out_dir, now=now)
        (out_dir / "index.md").write_text(f"<p>generated at {now}</p>")

    r = C.rebuild(backups, generate_fn=unstable)

    assert not r.ok
    assert "index.md" in r.differing


def test_a_generator_that_reads_the_working_directory_is_caught(backups):
    """The reason the second run happens elsewhere. Behavior: anything picked
    up from the tree the generator happens to sit in shows as a difference."""
    def nosy(conn, out_dir, *, now):
        generate(conn, out_dir, now=now)
        (out_dir / "index.md").write_text(f"<p>{Path.cwd().name}</p>")

    r = C.rebuild(backups, generate_fn=nosy)

    assert not r.ok and "index.md" in r.differing


def test_an_absolute_path_in_the_output_is_caught(backups):
    """Behavior: a surface carrying /Users/... has been generated somewhere
    rather than from something, and would not survive the move it claims to."""
    def leaky(conn, out_dir, *, now):
        generate(conn, out_dir, now=now)
        (out_dir / "index.md").write_text('<p>built at /Users/dean/x</p>')

    r = C.rebuild(backups, generate_fn=leaky)

    assert not r.ok
    assert any("/Users/dean/x" in leak for leak in r.leaked_paths)


def test_what_it_does_not_prove_is_written_down(backups):
    """R-11's deferral is recorded rather than implied. Behavior: the module
    says which assurances still need the second machine, so a passing rebuild
    is not read as portability proven."""
    doc = C.__doc__ or ""

    assert "does NOT prove" in doc
    assert "filesystem, architecture or locale" in doc
    assert "R-11" in doc


# ── a backup that restores to nothing (R-37e) ───────────────────────────

def test_a_backup_that_restores_to_nothing_is_refused(tmp_path):
    """R-37e. Behavior: `verify` counted a table without asserting anything, so
    a database with zero episodes returned 0 and passed — the one backup worth
    catching was the one it could not see. The clean-room rebuild is built on these
    files."""
    out = tmp_path / "backups"
    out.mkdir()
    empty = out / "main-20260820-120000.db"
    conn = open_db(empty)
    apply_pending(conn, MAIN_SQL)
    conn.close()

    with pytest.raises(C.EmptyBackup, match="restores to nothing"):
        C.verify(empty)

    r = C.rebuild(out, generate_fn=generate)
    assert not r.ok and "not a restorable backup" in r.unreadable


def test_a_backup_that_holds_something_still_verifies(backups):
    """The other direction, because a check that refuses everything is not a
    check."""
    assert C.verify(C.newest_backup(backups)) >= 1


def test_a_corrupt_backup_is_caught_before_it_is_counted(tmp_path):
    """Behavior: quick_check runs first — a file can hold rows and still be
    unrestorable, and counting them would report health it does not have."""
    out = tmp_path / "backups"
    out.mkdir()
    db = out / "main-20260820-120000.db"
    conn = open_db(db)
    apply_pending(conn, MAIN_SQL)
    conn.close()
    with open(db, "r+b") as f:          # scribble on the page after the header
        f.seek(4096)
        f.write(b"\xde\xad\xbe\xef" * 64)

    with pytest.raises(sqlite3.DatabaseError):
        C.verify(db)
