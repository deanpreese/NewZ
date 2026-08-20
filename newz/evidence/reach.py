"""Reach, attested against its pin rather than read from a diff (R-37b).

**Why this exists at all.** E3.4 made exposure one config value, and E3.9 froze
what the loop may not touch. Neither reaches the file the value lives in.
`.env` is gitignored, so it appears in neither `git diff` nor `git ls-files
--others --exclude-standard`, and `freeze.changed_paths()` reads exactly those
two. The loop could set `NEWZ_SURFACE_REACH=open` and no freeze check, drift
check or gate would see a diff — because there would not be one.

Every guard built in Phase 3 reads git. The being's most consequential setting
is outside git by design, and secrets belong there; the answer is not to track
`.env` but to stop checking the file and check **the value in effect**.

**So flipping reach takes two acts and one of them is tracked.** The pin lives
in `evolution/hard_core.yaml`, which is protected whole: the loop cannot change
it, and the operator changing it is a diff. Setting the environment variable
alone is no longer sufficient to expose the surface — it produces a refusal
naming what else the operator has to do, which is what makes reach theirs
rather than something that can quietly become true.

**It is checked at process start, not at bind time.** A being that has been
running for a day with an unattested reach has already been reachable for a
day. `serve()` still binds loopback for anything that is not the literal
`open` (INV-069) — that guard is unchanged and this one sits in front of it.
"""

from __future__ import annotations

from newz.evidence.hard_core import pin


class ReachUnattested(PermissionError):
    """The effective reach is not the reach the hard core records."""


def pinned() -> str:
    """What the operator has recorded that reach should be."""
    return str(pin("surface_reach")["value"]).strip().lower()


def breach(effective: str) -> str | None:
    """A description of the mismatch, or None. Never raises for a mismatch —
    callers differ on what to do about one, and `attest` is the strict door."""
    actual = (effective or "").strip().lower()
    want = pinned()
    if actual == want:
        return None
    return (
        f"reach is {actual!r} and the hard core pins it to {want!r}.\n\n"
        "The value comes from NEWZ_SURFACE_REACH in .env, which is gitignored "
        "and therefore invisible to every path-based guard here (R-37b) — this "
        "check exists because a diff cannot see it.\n\n"
        "If this is the operator's decision, change the surface_reach pin in "
        "evolution/hard_core.yaml so the change is recorded where the freeze "
        "can read it. If it is not, something set reach without saying so, and "
        f"the surface is {'exposed' if actual == 'open' else 'not where it was left'}.")


def attest(effective: str) -> str:
    """Return the reach, or refuse to proceed with it.

    Fails closed in both directions: an unpinned registry raises `PinMissing`
    from `pin`, because a guard that cannot find its reference value has not
    checked anything and must not report that it has.
    """
    found = breach(effective)
    if found:
        raise ReachUnattested(found)
    return (effective or "").strip().lower()
