"""The parse worker, and what its boundary is actually worth.

Threat model T-19. The parsers handle hostile input and ran in the interpreter
holding the store handle. These tests are about the boundary rather than about
any parser: that the same bytes give the same segments on either side of it,
that a failure crosses it as a failure, and that the child cannot do the things
the parent could.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from newz.parse.isolate import TIMEOUT_SECONDS, WorkerRefused, parse_isolated
from newz.parse.registry import ParserFailure, parse
from newz.parse.worker import ADDRESS_SPACE_BYTES, CPU_SECONDS, MEMORY_LIMITS, run

HTML = b"<html><body><h1>A heading</h1><p>Some text here.</p></body></html>"


# ---------------------------------------------------------------------------
# The same answer on either side
# ---------------------------------------------------------------------------


def test_the_boundary_does_not_change_the_answer():
    """Otherwise a span recorded before it stops resolving after it."""
    here = parse("artifact:a", HTML, "text/html")
    there = parse_isolated("artifact:a", HTML, "text/html")
    assert there.as_record() == here.as_record()
    assert there.text_hash == here.text_hash
    assert [s.id for s in there.segments] == [s.id for s in here.segments]


def test_a_parser_failure_crosses_as_a_parser_failure():
    """A caller should not have to know which interpreter read the document."""
    with pytest.raises(ParserFailure, match="no parser registered"):
        parse_isolated("artifact:a", HTML, "application/x-nothing")
    with pytest.raises(ParserFailure, match="no parser registered"):
        parse("artifact:a", HTML, "application/x-nothing")


def test_an_empty_document_fails_on_both_sides():
    with pytest.raises(ParserFailure):
        parse_isolated("artifact:a", b"<html><title>unclosed", "text/html")


# ---------------------------------------------------------------------------
# What the child cannot do
# ---------------------------------------------------------------------------


def _in_worker_env(code: str) -> subprocess.CompletedProcess:
    """Run a snippet with the worker's own limits applied first."""
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from newz.parse.worker import limit_self\nlimit_self()\n" + code,
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_the_worker_caps_itself_before_it_parses():
    """A limit applied after the thing it limits has run is a limit in name.

    Asked in a child, never here: `limit_self` constrains whoever calls it, and
    calling it in the test runner caps the test runner.
    """
    probe = subprocess.run(
        [sys.executable, "-c", "from newz.parse.worker import limit_self; print(limit_self())"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    applied = probe.stdout.decode()
    assert "RLIMIT_CPU" in applied, applied
    assert ADDRESS_SPACE_BYTES > 0 and CPU_SECONDS > 0


def test_the_worker_reports_which_limits_it_actually_got():
    """Not which it asked for.

    On macOS neither memory limit can be set — both report as unlimited and
    both raise when set — so the memory cap does not exist on the platform this
    currently runs on. A worker that claimed it regardless would be the same
    shape as one that had it, which is the mistake T-19 exists to record.
    """
    if sys.platform == "darwin":
        assert not _memory_limit_applies(), (
            "if a memory cap now applies on macOS, threat model T-21 is stale and "
            "should be corrected rather than this loosened"
        )


def test_nothing_but_the_worker_calls_the_thing_that_limits_the_caller():
    """`limit_self` caps the process that calls it, whichever process that is.

    Calling it from the test runner capped the runner and killed the suite half
    way through with no failure and no summary — a control that constrained the
    wrong thing and looked like an outage rather than a bug.
    """
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    callers = set()
    for path in sorted([*(root / "newz").rglob("*.py"), *(root / "tests").rglob("*.py")]):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "limit_self"
            ):
                callers.add(path.relative_to(root).as_posix())
    assert callers == {"newz/parse/worker.py"}, callers

    # And within that file, only `main` — the entry point of the child process.
    # `run` is callable from a test in the parent, and limiting there caps the
    # test runner. The first version of this audit checked direct callers by
    # name and missed exactly that, because the call was one function away.
    worker = ast.parse((root / "newz/parse/worker.py").read_text(encoding="utf-8"))
    limiting = {
        node.name
        for node in worker.body
        if isinstance(node, ast.FunctionDef)
        and any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "limit_self"
            for call in ast.walk(node)
        )
    }
    assert limiting == {"main"}, limiting


def _memory_limit_applies() -> bool:
    """Probe in a child, because `limit_self` limits whoever calls it.

    An earlier version of this asked the question by calling `limit_self()` in
    the skip condition, which pytest evaluates at collection — so it capped the
    *test runner's* CPU at thirty seconds and the suite died half way through
    with no failure and no summary. A function whose whole job is to constrain
    the process that calls it must only ever be called by the process meant to
    be constrained.
    """
    probe = subprocess.run(
        [sys.executable, "-c", "from newz.parse.worker import limit_self; print(limit_self())"],
        capture_output=True,
        timeout=30,
        check=False,
    )
    return any(name in probe.stdout.decode() for name in MEMORY_LIMITS)


@pytest.mark.skipif(
    not _memory_limit_applies(),
    reason="no memory limit applies on this platform; see threat model T-21",
)
def test_a_runaway_allocation_dies_where_a_memory_cap_applies():
    """Deliberately just over the cap rather than absurdly over it.

    An earlier version asked for 64 GB, which on a platform where the cap does
    not apply is not a test but an outage: it took the machine down and killed
    the suite. A test of a limit must not depend on the limit working.
    """
    over = ADDRESS_SPACE_BYTES + (64 * 1024 * 1024)
    finished = _in_worker_env(f"b = bytearray({over})\nprint('allocated')")
    assert b"allocated" not in finished.stdout, finished.stdout
    assert finished.returncode != 0


def test_the_worker_answers_one_request_and_stops():
    """One body, one process. A worker that looped would outlive its input."""
    request = json.dumps(
        {"artifact_id": "artifact:a", "normalized_mime": "text/html", "length": len(HTML)},
        sort_keys=True,
    )
    finished = subprocess.run(
        [sys.executable, "-m", "newz.parse.worker"],
        input=request.encode() + b"\n" + HTML + b"\n" + request.encode() + b"\n" + HTML,
        capture_output=True,
        timeout=30,
        check=False,
    )
    answers = finished.stdout.decode().strip()
    assert answers.count('"result"') == 1, answers[:200]


# ---------------------------------------------------------------------------
# Malformed traffic across the boundary
# ---------------------------------------------------------------------------


class _Reader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.at = 0

    def readline(self) -> bytes:
        end = self.payload.find(b"\n", self.at)
        end = len(self.payload) if end < 0 else end + 1
        line, self.at = self.payload[self.at : end], end
        return line

    def read(self, n: int) -> bytes:
        chunk = self.payload[self.at : self.at + n]
        self.at += len(chunk)
        return chunk


class _Writer:
    def __init__(self) -> None:
        self.text = ""

    def write(self, text: str) -> None:
        self.text += text

    def flush(self) -> None:
        pass


def _ask(payload: bytes) -> dict:
    out = _Writer()
    run(_Reader(payload), out)
    return json.loads(out.text)


def test_an_unreadable_request_is_an_error_and_not_a_crash():
    assert "error" in _ask(b"not json at all\n")
    assert "error" in _ask(b'{"artifact_id": "a"}\n')


def test_a_truncated_body_is_refused_rather_than_parsed():
    """Half a document parses to half a meaning, which is worse than none."""
    request = json.dumps(
        {"artifact_id": "artifact:a", "normalized_mime": "text/html", "length": len(HTML) + 500},
        sort_keys=True,
    )
    answer = _ask(request.encode() + b"\n" + HTML)
    assert "truncated body" in answer["error"]


def test_no_request_is_an_error(): 
    assert _ask(b"")["error"] == "no request"


def test_a_worker_that_says_nothing_is_a_parse_failure_not_a_crash(monkeypatch):
    """The document is what could not be read; that is the caller's question."""
    import newz.parse.isolate as isolate

    class Dead:
        stdout = b""
        stderr = b"Killed\n"
        returncode = -9

    monkeypatch.setattr(isolate.subprocess, "run", lambda *a, **k: Dead())
    with pytest.raises(ParserFailure, match="exited with -9"):
        parse_isolated("artifact:a", HTML, "text/html")


def test_a_worker_that_cannot_start_is_not_a_parse_failure(monkeypatch):
    """"Unreadable document" and "we could not run the reader" are different facts."""
    import newz.parse.isolate as isolate

    def refuse(*args, **kwargs):
        raise OSError("no such executable")

    monkeypatch.setattr(isolate.subprocess, "run", refuse)
    with pytest.raises(WorkerRefused, match="could not be started"):
        parse_isolated("artifact:a", HTML, "text/html")


def test_a_hanging_worker_times_out_on_the_wall_clock(monkeypatch):
    """CPU time and wall-clock time are different failures.

    A process blocked on a lock or a pipe burns no CPU and would sit under the
    child's own ceiling indefinitely.
    """
    import newz.parse.isolate as isolate

    def hang(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="worker", timeout=TIMEOUT_SECONDS)

    monkeypatch.setattr(isolate.subprocess, "run", hang)
    with pytest.raises(ParserFailure, match=f"within {TIMEOUT_SECONDS}s"):
        parse_isolated("artifact:a", HTML, "text/html")
    assert TIMEOUT_SECONDS > CPU_SECONDS, "the wall clock must outlast the CPU cap"


# ---------------------------------------------------------------------------
# The environment the child is given
# ---------------------------------------------------------------------------


def test_the_child_inherits_no_credentials(monkeypatch):
    from newz.parse.isolate import _environment

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "a-secret")
    monkeypatch.setenv("GMAIL_PASS", "another-secret")
    monkeypatch.setenv("NEWZ_MODEL_ENDPOINT", "http://10.0.0.1:1234/v1")
    child = _environment()
    assert "TELEGRAM_BOT_TOKEN" not in child
    assert "GMAIL_PASS" not in child
    assert "NEWZ_MODEL_ENDPOINT" not in child
    assert child["LC_ALL"] == "C", "a locale that could change a parse is pinned"
