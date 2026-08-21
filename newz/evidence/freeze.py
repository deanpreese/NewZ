"""The canonical freeze (P4 epic E3.9).

**Why the set is frozen at all.** The loop steers by evidence the being
produces while changing the being. At n=1, with no held-out baseline, it cannot
separate *improving the being* from *improving the instrument's view of the
being* — and it has a gradient toward the second, because that is cheaper,
faster and always works. Freezing the instruments removes the cheap path.

**It constrains the loop, not the operator.** `hard_core.yaml` puts it plainly:
a boundary the constrained party can widen is not a boundary. The constrained
party here is the loop. The operator changing an instrument is not a breach —
it is the act the freeze exists to *require*, and E3.9's own words are
"changing any canonical instrument becomes an operator act".

**So the operator path is recorded rather than blocked**, and it carries an
obligation. Changing a canonical instrument is precisely when a metric's meaning
moves, which is E2.8's definition boundary: the series must end and the reason
must be written down. A freeze that only said "no" to an agent would leave the
operator free to change a measurement while its series quietly continued across
the change — the exact silent breakage E2.8 exists to prevent, arriving through
the one door the freeze leaves open.

**The constrained party is the operator's agents** (P4 E3A.4). This was written
against a self-evolving loop and Phase 8 is struck; the sentence that justified
it survives the strike unchanged, because it was never really about a loop — at
n=1 with no held-out baseline, whatever is editing this repo cannot tell
*improving the being* from *improving the instrument's view of the being*, and
has a gradient toward the second because that is cheaper and always works. That
is a true sentence about an agent in a session.

**Nothing calls this automatically, and that is stated rather than implied**
(INV-044's discipline applied to a guard). `tools/gate.py` runs `freeze_check
--operator`, which lists and does not refuse, so the refusing mode has had no
caller from the start — the strike revealed that rather than causing it. This is
a check with a CLI, and a guard that looks enforced and is not is worse than no
guard.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from newz.evidence import hard_core

REPO = Path(__file__).resolve().parent.parent.parent


class FrozenTouched(PermissionError):
    """The loop tried to change something only the operator may change."""


@dataclass(frozen=True)
class Refusal:
    path: str
    why: str

    def __str__(self) -> str:
        return f"{self.path}: {self.why}"


def refusals(paths) -> list[Refusal]:
    """Which of these paths an agent may not touch, and why.

    **The constrained party is not the loop and never really was** (P4 E3A.4).
    §5.2's argument was written about a self-evolving loop: at n=1 with no
    held-out baseline it cannot tell *improving the being* from *improving the
    instrument's view of the being*, and it has a gradient toward the second
    because that is cheaper and always works. Phase 8 is struck and that
    sentence is still true — of an agent editing this repo in a session, at
    speed, which is who actually edits it. The freeze keeps its job and gets an
    honest actor.
    """
    canonical = set(hard_core.canonical_paths())
    out: list[Refusal] = []
    for p in sorted({str(x).lstrip("./") for x in paths}):
        if not hard_core.contains(p):
            continue
        if p in canonical:
            out.append(Refusal(p, (
                "a canonical instrument. Whoever steers by what this measures "
                "cannot tell improving the being from improving its own view "
                "of the being — changing it is an operator act (E3.9)")))
        else:
            out.append(Refusal(p, (
                "inside the hard core. §5's boundary, and a boundary the "
                "constrained party can widen is not one")))
    return out


def enforce(paths, *, actor: str = "agent") -> list[Refusal]:
    """Refuse for an agent; record for the operator.

    The operator's path returns the same list rather than raising, because the
    obligation it carries is E2.8's: a changed instrument is a changed
    definition, and the series has to end at the change with the reason written
    down. Returning the list is how the caller is told which metrics that
    applies to.
    """
    found = refusals(paths)
    if found and actor != "operator":
        raise FrozenTouched(
            "an agent may not change these:\n  "
            + "\n  ".join(str(f) for f in found)
            + "\n\nAn instrument changes when the operator changes it, and when "
              "they do, every metric it emits has a new definition (E2.8): bump "
              "`definition_version` in evolution/instruments.yaml with a "
              "`definition_history` entry saying what changed, or the old series "
              "will be compared against the new one.")
    return found


def changed_paths(base: str = "HEAD") -> list[str]:
    """What the working tree has changed, tracked files only.

    **What this cannot see, stated rather than implied.** Both commands below
    read git, so a gitignored file appears in neither and every guard built on
    this function is blind to it. `.env` is the case that matters: reach lives
    there, and the loop could flip it without producing a diff for anything
    here to refuse (R-37b). `newz.evidence.reach` is the compensating check and
    it compares the effective value against its pin instead of reading a file.

    A clean result from this function means *nothing tracked changed*.
    """
    out = subprocess.run(
        ["git", "diff", "--name-only", base],
        cwd=REPO, capture_output=True, text=True, check=False)
    tracked = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, check=False)
    return tracked + [l.strip() for l in untracked.stdout.splitlines() if l.strip()]


def metrics_affected(paths) -> dict[str, list[str]]:
    """Which registered metrics a change to these files would redefine.

    The operator's obligation, made specific: not "some metrics may be
    affected" but these ones, by name.
    """
    import yaml

    rows = (yaml.safe_load((REPO / "evolution" / "instruments.yaml").read_text())
            or {}).get("metrics") or {}
    touched = {str(p).lstrip("./") for p in paths}
    out: dict[str, list[str]] = {}
    for name, row in rows.items():
        emitter = (row or {}).get("emitted_by")
        if emitter and emitter in touched:
            out.setdefault(emitter, []).append(name)
    return {k: sorted(v) for k, v in out.items()}
