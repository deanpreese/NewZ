"""`python -m newz.pilot.propose` — survey candidates and print a slate.

Two commands, both read-only as far as the diet is concerned. `--survey` fetches
each unsurveyed candidate through the ordinary fetcher and records what it
serves. With no flag, it solves a slate from what has been surveyed and prints
it for a person to read.

Neither enables anything. Activating a diet epoch is a separate operator act
with its own dry run, and that is where a source starts being read.
"""

from __future__ import annotations

import sys
from pathlib import Path

from newz.acquisition.transport import SocketTransport
from newz.pilot.slots import render, solve, survey
from newz.store.db import open_store


def main(argv: list[str]) -> int:
    args = argv[1:]
    store_path = Path(args[-1]) if args and args[-1].endswith(".db") else Path("data/newz.db")
    store = open_store(store_path)

    if "--survey" in args:
        probes = survey(store, SocketTransport())
        for probe in probes:
            state = probe.proposed_role.value if probe.proposed_role else "no role proposed"
            print(f"{probe.candidate_id}: {probe.refusal or state}")
        print(f"\n{len(probes)} candidate(s) surveyed.")
        return 0

    slate = solve(store)
    print(render(slate, store))
    return 0 if slate.acceptable else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
