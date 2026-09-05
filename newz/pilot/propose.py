"""`python -m newz.pilot.propose` — the pilot slate, derived from the diet.

Three commands, all read-only as far as the diet is concerned.

    --prescribe   what the diet asks for: twenty bucket-and-topic slots,
                  derived from the menu targets, with the arithmetic shown
    --seeds       the specific slate proposed against those slots, with the
                  terms that need reading and the retention gap it leaves
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
from newz.pilot.slots import propose_candidates, render, solve, survey
from newz.store.db import open_store


def main(argv: list[str]) -> int:
    args = argv[1:]
    store_path = Path(args[-1]) if args and args[-1].endswith(".db") else Path("data/newz.db")
    store = open_store(store_path)

    if "--prescribe" in args:
        from newz.pilot.prescription import render as render_prescription
        from newz.pilot.seeds import prescribed

        print(render_prescription(prescribed()))
        return 0

    if "--seeds" in args:
        from newz.pilot.seeds import render as render_seeds

        print(render_seeds())
        return 0

    if "--survey" in args:
        from newz.pilot.seeds import prescribed
        from newz.pilot.seeds import register as register_seeds

        register_seeds()
        added, unserved = propose_candidates(
            store, specs=prescribed(), added_by="operator"
        )
        if added:
            print(f"{added} candidate(s) proposed from the diet.")
        for spec in unserved:
            print(f"no candidate for {spec.bucket} / {spec.topic}")
        probes = survey(store, SocketTransport())
        for probe in probes:
            state = probe.proposed_role.value if probe.proposed_role else "no role proposed"
            print(f"{probe.candidate_id}: {probe.refusal or state}")
        print(f"\n{len(probes)} candidate(s) surveyed.")
        return 0

    from newz.pilot.seeds import prescribed

    slate = solve(store, specs=prescribed())
    print(render(slate, store))
    return 0 if slate.acceptable else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
