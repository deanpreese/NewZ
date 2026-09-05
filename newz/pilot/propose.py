"""`python -m newz.pilot.propose` — the pilot slate, derived from the diet.

Three commands, all read-only as far as the diet is concerned.

    --prescribe   what the diet asks for: twenty bucket-and-topic slots,
                  derived from the menu targets, with the arithmetic shown
    --survey      fetch each unsurveyed candidate through the ordinary fetcher
                  and record what it actually serves
    (no flag)     solve the prescribed slate from what has been surveyed

None of them enables anything. Activating a diet epoch is a separate operator
act with its own dry run, and that is where a source starts being read.
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

    if "--prescribe" in args:
        from newz.pilot.prescription import render as render_prescription

        print(render_prescription())
        return 0

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
