"""The one place in the package that starts a process.

Threat model T-19: fetch and parse handle hostile input, and a parser in the
interpreter that holds the store handle is one deserialization bug away from
writing to the ledger. `newz/parse/worker.py` is the other side of that
boundary; this is the door.

Gate 0 forbade starting a process anywhere in the package, and that rule was
right for what it was written against — a system that shells out is a system
whose boundary is wherever the shell is. It is now narrowed rather than dropped:
exactly this module may spawn, it may spawn exactly one thing, and a static test
checks both. A rule with one audited exception is a different object from a rule
with none, and the difference is that the exception is named.

The child is given no shell, no inherited environment beyond what the
interpreter needs, a closed stdin after its one request, and a wall-clock
timeout on top of the CPU limit it sets for itself — because a process blocked
on something is not spending CPU and would sit under that ceiling forever.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass

from newz.parse.registry import ParseResult, ParserFailure, Segment

#: Longer than the worker's own CPU limit, because wall-clock and CPU time are
#: different failures: a parser stuck on a lock or a pipe burns no CPU at all.
TIMEOUT_SECONDS = 45

#: What the child needs to be a Python process and nothing else. No inherited
#: credentials, no proxy settings, no locale that could change a parse.
def _environment() -> dict[str, str]:
    keep = {"PATH", "PYTHONPATH", "PYTHONHOME", "SYSTEMROOT", "LD_LIBRARY_PATH"}
    child = {name: value for name, value in os.environ.items() if name in keep}
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    child["LC_ALL"] = "C"
    return child


@dataclass(frozen=True, slots=True)
class WorkerRefused(Exception):
    """The worker could not be run, which is not the same as a parse failing."""

    detail: str

    def __str__(self) -> str:
        return self.detail


def parse_isolated(
    artifact_id: str,
    body: bytes,
    normalized_mime: str,
    timeout: int = TIMEOUT_SECONDS,
) -> ParseResult:
    """Parse in a child process that cannot reach the store or the network.

    Raises `ParserFailure` where the in-process parser would, so a caller does
    not have to know which side of the boundary it ran on. A worker that could
    not be started at all raises `WorkerRefused`, because "the document is
    unreadable" and "we could not run the reader" are different facts and only
    the first is about the source.
    """
    request = json.dumps(
        {
            "artifact_id": artifact_id,
            "normalized_mime": normalized_mime,
            "length": len(body),
        },
        sort_keys=True,
    )
    try:
        finished = subprocess.run(
            [sys.executable, "-m", "newz.parse.worker"],
            input=request.encode("utf-8") + b"\n" + body,
            capture_output=True,
            timeout=timeout,
            env=_environment(),
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        raise ParserFailure(
            f"the parse worker did not finish within {timeout}s"
        ) from expired
    except OSError as error:
        raise WorkerRefused(f"the parse worker could not be started: {error}") from error

    if not finished.stdout:
        # Killed by a limit, or died before writing. Either way the document is
        # what could not be read, and the child's stderr says how.
        detail = finished.stderr.decode("utf-8", errors="replace").strip()
        raise ParserFailure(
            f"the parse worker exited with {finished.returncode} and said nothing"
            + (f": {detail.splitlines()[-1]}" if detail else "")
        )

    try:
        answer = json.loads(finished.stdout.decode("utf-8"))
    except ValueError as error:
        raise WorkerRefused(f"the parse worker answered unreadably: {error}") from error

    if "error" in answer:
        raise WorkerRefused(answer["error"])
    if "failure" in answer:
        raise ParserFailure(answer["failure"])
    return _as_result(answer["result"])


def _as_result(record: dict) -> ParseResult:
    return ParseResult(
        artifact_id=record["artifact_id"],
        parser_name=record["parser_name"],
        parser_version=record["parser_version"],
        normalized_mime=record["normalized_mime"],
        segments=tuple(
            Segment(
                id=segment["id"],
                artifact_id=record["artifact_id"],
                ordinal=segment["ordinal"],
                kind=segment["kind"],
                locator=segment["locator"],
                text=segment["text"],
            )
            for segment in record["segments"]
        ),
        text_hash=record["text_hash"],
        failures=tuple(record["failures"]),
    )
