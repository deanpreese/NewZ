"""Reach as one config value (P4 epic E3.4, Rule 3).

Done-when: flipping the setting exposes the surface with **no code change**.

Rule 3: outward capabilities are built public-ready and left unpublished. The
corollary is that one value carries the whole weight of the exposure decision,
so it is built to fail closed — the failure mode here is not a broken page, it
is an unintended reader.
"""

from __future__ import annotations

import socketserver
from pathlib import Path

import pytest
import yaml

from newz.config import load
from newz.surface.serve import LOCAL_HOST, OPEN_HOST, host_for, is_open, serve

REPO = Path(__file__).resolve().parent.parent


def test_the_default_is_local(tmp_path):
    """Behavior: with no setting at all, nothing outside this machine can
    reach the surface. P4 Decision 1 is unmade, so local is the only honest
    default."""
    env = tmp_path / "empty.env"
    env.write_text("")

    cfg = load(repo_root=REPO, env_file=env)

    assert cfg.surface_reach == "local"
    assert host_for(cfg.surface_reach) == LOCAL_HOST


def test_flipping_one_value_changes_reach_with_no_code_change(tmp_path):
    """E3.4's Done-when. Behavior: the same code binds outward when — and only
    when — the setting says so."""
    env = tmp_path / "open.env"
    env.write_text("NEWZ_SURFACE_REACH=open\n")

    cfg = load(repo_root=REPO, env_file=env)

    assert cfg.surface_reach == "open"
    assert host_for(cfg.surface_reach) == OPEN_HOST and is_open(cfg.surface_reach)


def test_anything_that_is_not_the_word_open_is_local(tmp_path):
    """Behavior: a typo must fail closed. "opne", "true", "yes", "1" and an
    empty string all bind the loopback, because the cost of guessing wrong in
    the permissive direction is a reader nobody chose."""
    for value in ("opne", "true", "yes", "1", "OPEN ", "", "public", "local"):
        env = tmp_path / "v.env"
        env.write_text(f"NEWZ_SURFACE_REACH={value}\n")
        cfg = load(repo_root=REPO, env_file=env)
        expected = "open" if value.strip().lower() == "open" else "local"
        assert cfg.surface_reach == expected, value
    assert host_for("opne") == LOCAL_HOST


def test_nothing_in_the_codebase_writes_the_setting():
    """Rule 3, and the hard core's own clause — "reach stays a config value the
    operator sets". Behavior: no module assigns it, so exposure cannot be a
    side effect of anything the system does to itself."""
    offenders = []
    for path in REPO.rglob("*.py"):
        if any(part in path.parts for part in (".git", ".claude", "tests")):
            continue
        for line in path.read_text().splitlines():
            if "NEWZ_SURFACE_REACH" not in line:
                continue
            # Naming it in a message or reading it is fine; writing it is not.
            if any(w in line for w in ("os.environ[", "putenv", "setdefault(",
                                       "environ.update")):
                offenders.append(f"{path.name}: {line.strip()}")

    assert offenders == [], offenders


def test_the_server_has_no_host_parameter_to_get_it_wrong_with():
    """Behavior: the only way to reach 0.0.0.0 is to have written `open` in the
    config. An earlier version took the setting, derived the host, then raised
    if the host was outward without the setting — a check that could never
    fire, because the host came from the setting. A guard that cannot fire
    reads as protection and is not one."""
    import inspect

    sig = inspect.signature(serve)

    assert "host" not in sig.parameters
    assert set(sig.parameters) == {"directory", "reach", "port", "server_factory"}


def test_the_hard_core_records_reach_as_the_operators(tmp_path):
    """Behavior: the boundary is written where its enforcer will read it, not
    only in a proposal, and nothing refuses a diff against it — the gate lists
    rather than refuses (INV-074)."""
    core = yaml.safe_load((REPO / "evolution" / "hard_core.yaml").read_text())

    assert any("reach" in s and "operator" in s for s in core["state"])


def test_the_server_refuses_to_bind_outward_without_the_setting(tmp_path):
    """Behavior: the guard lives at the one door rather than at each caller —
    a caller is a place a mistake can live."""
    captured = {}

    class FakeServer:
        allow_reuse_address = False

        def __init__(self, addr, handler):
            captured["addr"] = addr

    serve(tmp_path, reach="local", port=1, server_factory=FakeServer)
    assert captured["addr"][0] == LOCAL_HOST

    serve(tmp_path, reach="open", port=1, server_factory=FakeServer)
    assert captured["addr"][0] == OPEN_HOST


def test_the_surface_asks_not_to_be_indexed(tmp_path):
    """E3.4 delivers "no index". Behavior: robots.txt disallows everything and
    every page carries noindex.

    Both are requests, not permissions — what actually keeps the surface
    private is the bind address, and the module says so rather than letting a
    robots file read as a control."""
    import sqlite3
    import time

    from newz.store.db import open_db
    from newz.store.migrations import apply_pending
    from newz.surface.generate import generate

    conn = open_db(tmp_path / "s.db")
    apply_pending(conn, REPO / "newz" / "store" / "sql" / "main")
    out = tmp_path / "pub"
    generate(conn, out, now=1.0)
    conn.close()

    assert (out / "robots.txt").read_text() == "User-agent: *\nDisallow: /\n"
    for page in out.glob("*.md"):
        assert "\nrobots: noindex, nofollow\n" in page.read_text(), page.name


def test_a_piece_keeps_its_address_when_it_is_revised(tmp_path):
    """"Stable identifiers". Behavior: the address is the row id, not the
    signature or the title — a revised piece is the same piece and must keep
    its address, or every revision breaks whatever pointed at it."""
    import time

    from newz.store.db import open_db
    from newz.store.migrations import apply_pending
    from newz.surface.generate import generate

    conn = open_db(tmp_path / "s.db")
    apply_pending(conn, REPO / "newz" / "store" / "sql" / "main")
    conn.execute(
        "INSERT INTO works (id, ts, subject_kind, subject_ref, subject_text,"
        " chosen_because, title, body, word_count, model, completion_tokens)"
        " VALUES (1,?,?,?,?,?,?,?,?,?,?)",
        (time.time(), "concern", 1, "q", "because", "First title", "b", 1, "m", 1))
    conn.commit()
    out = tmp_path / "pub"
    generate(conn, out, now=1.0)
    assert (out / "work" / "1.md").exists()

    conn.execute("UPDATE works SET title='Revised title', body='new' WHERE id=1")
    conn.commit()
    generate(conn, out, now=1.0)
    conn.close()

    assert (out / "work" / "1.md").exists()
    assert "Revised title" in (out / "work" / "1.md").read_text()


# ── attested against a pin, not read from a diff (R-37b) ────────────────

def test_the_file_reach_lives_in_is_invisible_to_every_path_guard():
    """R-37b, measured rather than asserted. `.env` is gitignored, so it is in
    neither `git diff` nor `git ls-files --others --exclude-standard` — and
    those two commands are the whole of `freeze.changed_paths()`.

    So the loop could have set NEWZ_SURFACE_REACH=open and no freeze check,
    drift check or gate would have refused anything, because there would have
    been no diff to refuse. This test pins the blindness in place so the
    compensating check below is never mistaken for redundant."""
    import subprocess

    from newz.evidence import freeze, hard_core

    ignored = subprocess.run(["git", "check-ignore", ".env"],
                             cwd=freeze.REPO, capture_output=True, text=True)
    assert ignored.returncode == 0, "this test is about a gitignored .env"
    assert ".env" not in freeze.changed_paths()
    assert not hard_core.contains(".env")
    assert freeze.refusals([".env"]) == []


def test_reach_is_attested_against_the_hard_core_at_process_start():
    """The compensating check: compare the value **in effect** against what the
    operator recorded, since the file it comes from cannot be read by a diff.

    Flipping reach therefore takes two acts and one of them is tracked."""
    from newz.evidence import hard_core
    from newz.evidence.reach import ReachUnattested, attest, breach, pinned

    assert pinned() == "local", "Rule 3: public-ready, left unpublished"
    assert hard_core.contains("evolution/hard_core.yaml"), (
        "the pin is only a boundary because the loop cannot edit the file it "
        "is written in")

    assert attest("local") == "local"
    assert breach("local") is None

    with pytest.raises(ReachUnattested, match="pins it to 'local'"):
        attest("open")
    assert "exposed" in breach("open")


def test_a_guard_that_cannot_find_its_pin_does_not_pass(monkeypatch):
    """INV-044's discipline applied to a guard. A missing reference value means
    nothing was checked, and a check that reports success on no input is worse
    than no check — it is a guard that reads as enforced."""
    from newz.evidence import hard_core, reach

    with monkeypatch.context() as m:
        m.setattr(hard_core, "pins", lambda: [])
        with pytest.raises(hard_core.PinMissing, match="not pinned"):
            reach.attest("local")

