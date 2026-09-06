"""The parse worker: a process that reads bytes and returns segments.

Threat model T-19. `pypdf` and the HTML parser handle hostile input, and until
now they did it in the interpreter holding the store handle — one
deserialization bug away from writing to the ledger. This is the other side of
that boundary.

The worker is deliberately small and deliberately ignorant. It reads a length,
a MIME and a body from standard input, parses, and writes one JSON object to
standard output. It has no store, no network, and no idea what artifact it is
looking at beyond an identifier used to derive segment ids. Everything it can do
is in that description.

**It is enforced by what it can import, not by intention.** A static test walks
the worker's transitive imports and fails if any of them can reach `sqlite3`, a
socket, or `newz.store` — so the isolation cannot be lost by somebody adding a
convenient import to a parser three modules down.

**It limits itself before it parses.** Address space and CPU are capped in the
child, so a decompression bomb that got past the fetcher's ceiling, or a parser
that loops, costs a bounded amount and dies rather than taking the machine. The
caps are set before the parsers are imported, because a limit applied after the
thing it limits has run is a limit in name.
"""

from __future__ import annotations

import json
import resource
import sys

#: A parse is a bounded amount of work on a bounded body. The fetcher already
#: refuses anything over its own ceiling, so these are the second wall rather
#: than the first: they bound what a body that got past it can cost.
ADDRESS_SPACE_BYTES = 1_024 * 1_024 * 1_024
CPU_SECONDS = 30


#: Tried in order, and on macOS **neither works**. Both are reported as
#: unlimited and both raise `ValueError: current limit exceeds maximum limit`
#: when set, so the memory cap this worker asks for does not exist on the
#: platform it currently runs on. `limit_self` returns what actually applied
#: rather than what was attempted, for exactly that reason: a control that
#: silently did not take is the failure this whole boundary was written to
#: answer, and claiming it would repeat the mistake in `ARCHITECTURE.md` that
#: threat model T-19 exists to record.
#:
#: What bounds a runaway parse on macOS is the CPU cap, the caller's wall-clock
#: timeout, and the fetcher's size ceiling upstream. That is weaker than a
#: memory cap and is stated as such in the threat model rather than papered
#: over.
MEMORY_LIMITS = ("RLIMIT_AS", "RLIMIT_DATA")


def limit_self() -> list[str]:
    """Cap this process before it touches anything hostile.

    Returns what actually applied. Resource limits vary by platform in ways
    worth reporting rather than assuming: an isolation whose caps silently did
    not take is an isolation nobody can rely on, and a worker that claimed them
    regardless would be the same shape as one that got them.
    """
    applied: list[str] = []
    for name in (*MEMORY_LIMITS, "RLIMIT_CPU"):
        what = getattr(resource, name, None)
        if what is None:
            continue
        cap = CPU_SECONDS if name == "RLIMIT_CPU" else ADDRESS_SPACE_BYTES
        _soft, hard = resource.getrlimit(what)
        ceiling = cap if hard == resource.RLIM_INFINITY else min(cap, hard)
        try:
            resource.setrlimit(what, (ceiling, ceiling))
        except (ValueError, OSError):
            continue
        applied.append(name)
        if name in MEMORY_LIMITS:
            break  # one memory cap is enough; the rest are the same wall
    return applied


def run(stdin, stdout, applied: list[str] | None = None) -> int:
    """Read one request, write one response. No loop: one body, one process.

    It does not limit anything. `limit_self` constrains whoever calls it, and
    this function is callable from a test in the parent — an earlier version
    limited here, so running it in-process capped the test runner's CPU at
    thirty seconds and the suite died half way through with no failure and no
    summary. The entry point limits; the logic does not.
    """
    applied = [] if applied is None else applied

    # Imported here and only here, so nothing in the parent's import graph pulls
    # a parser in beside the store.
    from newz.parse import registry
    from newz.parse.registry import ParserFailure, parse

    __import__("newz.parse")  # registers every parser
    assert registry.registered(), "no parser registered in the worker"

    header = stdin.readline()
    if not header:
        return _write(stdout, {"error": "no request"})
    try:
        request = json.loads(header)
        body = stdin.read(int(request["length"]))
    except (ValueError, KeyError, TypeError) as error:
        return _write(stdout, {"error": f"unreadable request: {error}"})

    if len(body) != int(request["length"]):
        return _write(
            stdout,
            {"error": f"truncated body: {len(body)} of {request['length']} bytes"},
        )

    try:
        result = parse(request["artifact_id"], body, request["normalized_mime"])
    except ParserFailure as failure:
        return _write(stdout, {"failure": str(failure)})
    except MemoryError:
        # The address-space cap firing. Reported as a parse failure rather than
        # a crash, because from the ledger's side that is what it is.
        return _write(stdout, {"failure": "the parser exceeded its memory limit"})
    return _write(stdout, {"result": result.as_record(), "limits": applied})


def _write(stdout, payload: dict) -> int:
    stdout.write(json.dumps(payload, sort_keys=True))
    stdout.flush()
    return 0 if "error" not in payload else 1


def main() -> int:  # pragma: no cover - exercised through the isolate module
    """The only place that limits: a child process, limiting itself."""
    return run(sys.stdin.buffer, sys.stdout, limit_self())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
