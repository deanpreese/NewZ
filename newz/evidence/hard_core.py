"""What the loop may never touch, read off `evolution/hard_core.yaml`
(SEL proposal §5).

**The registry is the definition and this is its reader.** §5 enumerated the
hard core in prose and nothing in the repo encoded it, while E8.2's runner,
E8.4's gate and the autonomy stage are all specified in terms of it. PLAN's
Phase 8 never cited §5, so the loop — sent by its own precedence table to read
PLAN — could not find the boundary rung 1 refuses on.

**The canonical instruments are derived, not copied.** §5.2 named ten by hand.
Eight are tools and two are `newz/evidence` modules, and it is the modules that
make the point: freezing `tools/evidence.py` while `newz/evidence/pursuit.py`
stays writable freezes a filename, not a measurement. `canonical_paths` takes
every tool the instrument registry marks canonical and adds every
`newz/evidence` module those tools import, which is a superset of §5.2 —
asserted, not assumed, in tests/test_hard_core.py.

**Nothing here refuses anything.** E8.0's gate is the enforcer and is not
built. This module answers "is this path inside the core?"; acting on the
answer arrives with the gate.
"""

from __future__ import annotations

import ast
import functools
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
REGISTRY = REPO / "evolution" / "hard_core.yaml"
INSTRUMENTS = REPO / "evolution" / "instruments.yaml"


@functools.lru_cache(maxsize=1)
def registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text()) or {}


def _instrument_rows() -> list[dict]:
    d = yaml.safe_load(INSTRUMENTS.read_text()) or {}
    ins = d.get("instruments") or []
    return list(ins.values()) if isinstance(ins, dict) else list(ins)


def canonical_tools() -> list[str]:
    """The tools the instrument registry freezes (`canonical: true`)."""
    return sorted(r["tool"] for r in _instrument_rows() if r.get("canonical"))


def _evidence_imports(tool: str) -> set[str]:
    """`newz/evidence/*.py` modules a tool imports. A frozen tool whose
    measurement code is writable is not frozen.

    **Both import forms.** `from newz.evidence.pursuit import ...` names the
    module and `from newz.evidence import pursuit` names the package, and only
    the first was matched — so a canonical tool written the second way pulled
    nothing into the freeze. Found 2026-08-20 when `tools/pre_loop_baseline.py`
    imported `pre_loop` that way and W8's check noticed the package rather than
    the module: an import style was the difference between measurement code
    being frozen and being writable.
    """
    out: set[str] = set()
    try:
        tree = ast.parse((REPO / tool).read_text())
    except (OSError, SyntaxError):
        return out
    for node in ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            mods = [node.module]
            if node.module == "newz.evidence":
                # the package itself, plus every module named off it
                mods += [f"newz.evidence.{a.name}" for a in node.names]
        elif isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        for m in mods:
            if m == "newz.evidence":
                out.add("newz/evidence/__init__.py")
            elif m.startswith("newz.evidence."):
                rel = "newz/" + m.split("newz.", 1)[1].replace(".", "/") + ".py"
                if (REPO / rel).exists():
                    out.add(rel)
    return out


def _newz_imports(path: str) -> set[str]:
    """Every `newz.*` module a file imports — the whole package, not just
    `newz/evidence`. What `_evidence_imports` is to the freeze, this is to the
    question of what the freeze can even see."""
    out: set[str] = set()
    try:
        tree = ast.parse((REPO / path).read_text())
    except (OSError, SyntaxError):
        return out
    for node in ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            mods = [node.module]
        elif isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        for m in mods:
            if m != "newz" and not m.startswith("newz."):
                continue
            rel = ("newz/__init__.py" if m == "newz" else
                   "newz/" + m.split("newz.", 1)[1].replace(".", "/") + ".py")
            if (REPO / rel).exists():
                out.add(rel)
            elif (REPO / rel[:-3]).is_dir():
                out.add(rel[:-3] + "/__init__.py")
    return out


def _closure(seeds: list[str]) -> set[str]:
    seen: set[str] = set()
    frontier = {m for s in seeds for m in _newz_imports(s)}
    while frontier:
        seen |= frontier
        frontier = {m for f in frontier for m in _newz_imports(f)} - seen
    return seen


def reachable() -> list[str]:
    """Every `newz` module a canonical tool can reach, transitively."""
    return sorted(_closure(canonical_tools()))


def reached_by(module: str) -> list[str]:
    """Which canonical tools reach this module. The consequence of a
    classification, shown to whoever is making it."""
    return sorted(t for t in canonical_tools() if module in _closure([t]))


def mechanisms() -> dict[str, str]:
    """Modules a canonical tool reaches that are **not** measurement, each with
    the reason it is not.

    **The line is that measurement code is frozen wherever it lives and
    mechanisms are not**, and the registry says plainly that an import graph
    cannot draw that line. So it is drawn by hand — and this is what makes the
    hand-drawing checkable: a module in the closure is either inside the core or
    named here, and a new one is neither until somebody decides which it is.
    The registry is protected, so only the operator can add a row.
    """
    return {r["path"]: r.get("why", "") for r in registry().get("mechanisms", [])}


def unclassified() -> list[str]:
    """Modules a canonical tool reaches that nobody has called measurement or
    mechanism. This is the gap `known_incomplete` describes: `telemetry.py` and
    `provenance.py` were found by reading, and nothing would have found the
    next one."""
    named = mechanisms()
    return [m for m in reachable() if not contains(m) and m not in named]


def canonical_paths() -> list[str]:
    """The frozen instrument set: canonical tools plus the evidence modules
    that compute their numbers, **transitively**.

    Widened 2026-08-20 while building E3.9's enforcer, and the widening is the
    finding. One level from the tools left `derived.py`, `agreement.py`,
    `authority.py` and `definitions.py` writable — all measurement code, all
    reached through `baseline.py` and `premises.py` rather than directly. A
    frozen tool whose measurement code is writable is not frozen, and that is
    just as true two hops out as one: the file stays byte-identical while the
    number changes.

    The closure stops at `newz/evidence` by the rule's own boundary. Measurement
    code living elsewhere is still named by hand in `paths`, and nothing detects
    a failure to do so — `known_incomplete` in the registry, unchanged.
    """
    paths = set(canonical_tools())
    frontier = set()
    for tool in canonical_tools():
        frontier |= _evidence_imports(tool)
    while frontier:
        paths |= frontier
        nxt: set[str] = set()
        for mod in frontier:
            nxt |= _evidence_imports(mod)
        frontier = nxt - paths
    return sorted(p for p in paths if (REPO / p).exists())


def protected_paths() -> list[str]:
    """Everything inside the core: the registry's own paths plus the derived
    instrument set. Section-protected files (PLAN.md) are NOT here — see
    `sections`, and `open_gaps` for why nothing enforces them."""
    return sorted(set(r["path"] for r in registry().get("paths", [])) | set(canonical_paths()))


def contains(path: str | Path) -> bool:
    """Is `path` inside the hard core? Directory entries match by prefix.

    `lstrip("./")` was doing the normalising here, and it takes a character
    *set*: `.gitignore` came back as `gitignore` and matched nothing. Every
    dotfile named in the core was silently outside it — found when `.gitignore`
    was added (W8), which is the first dotfile the core has ever held.
    """
    rel = str(Path(path))
    while rel.startswith("./"):
        rel = rel[2:]
    for p in protected_paths():
        if p.endswith("/") and rel.startswith(p):
            return True
        if rel == p.rstrip("/"):
            return True
    return False


class PinMissing(KeyError):
    """A pinned value was asked for and the registry does not carry it."""


def pins() -> list[dict]:
    """Values held by content rather than by path.

    Some of what §5 protects produces no diff. `.env` is gitignored, so a
    change to it is invisible to `changed_paths()`; the disclosure text lives
    in a file that is deliberately not frozen, because freezing the whole
    generator would freeze the surface's markup along with the claim. A pin
    names the value, and the checker compares what is in effect against it.
    """
    return list(registry().get("pins", []))


def pin(what: str) -> dict:
    """One pin, or refuse. Fails closed: a checker that cannot find its pin
    must not conclude the value is fine (INV-044's discipline applied to a
    guard — a missing input is never a passing check)."""
    for row in pins():
        if row.get("what") == what:
            return row
    raise PinMissing(
        f"{what!r} is not pinned in {REGISTRY.name}. A guard whose reference "
        f"value is missing cannot pass; it can only say so.")


def sections() -> list[dict]:
    """Files protected by section rather than by path. Nothing checks these."""
    return list(registry().get("sections", []))


def open_gaps() -> list[dict]:
    """What §5 names that is not yet buildable or not yet enforced. Read this
    before treating `contains` as protection (INV-044)."""
    return list(registry().get("open_gaps", []))


def validate() -> list[str]:
    """Structural errors in the registry. Empty is clean."""
    errors: list[str] = []
    reg = registry()
    for key in ("version", "paths", "derived_from", "pins", "sections", "open_gaps",
                "state"):
        if key not in reg:
            errors.append(f"registry is missing {key!r}")
    for row in reg.get("paths", []):
        if not row.get("path") or not row.get("why"):
            errors.append(f"path row without a path and a why: {row!r}")
            continue
        target = REPO / row["path"]
        if not target.exists():
            errors.append(f"{row['path']} is in the hard core and does not exist")
    for row in reg.get("pins", []):
        held = [k for k in ("sha256", "value") if row.get(k)]
        if not row.get("what") or not row.get("why") or len(held) != 1:
            errors.append(
                "a pin needs a what, a why and exactly one of sha256/value: "
                f"{row!r}")
    for row in reg.get("open_gaps", []):
        if not row.get("what") or not row.get("detail"):
            errors.append(f"open_gaps row without a what and a detail: {row!r}")
    if not canonical_paths():
        errors.append("the derived canonical set is empty")

    # W8: every module a canonical tool reaches is measurement or mechanism,
    # and saying which is an act somebody takes rather than one nobody takes.
    within = set(reachable())
    for module in unclassified():
        errors.append(
            f"{module} is reached by {', '.join(reached_by(module))} and is "
            "classified nowhere — add it to `mechanisms` in hard_core.yaml with "
            "the reason it is not measurement, or name it in `paths` to freeze "
            "it. Measurement code is frozen wherever it lives")
    for path, why in mechanisms().items():
        if not why.strip():
            errors.append(f"{path} is called a mechanism and does not say why")
        if not (REPO / path).exists():
            errors.append(f"{path} is classified as a mechanism and does not exist")
        elif contains(path):
            errors.append(
                f"{path} is both frozen and called a mechanism — one of the two "
                "is wrong, and a contradiction here is a boundary nobody can read")
        elif path not in within:
            errors.append(
                f"{path} is classified as a mechanism and no canonical tool "
                "reaches it any more — a stale row makes the list read as a "
                "survey when it is a decision about live code")
    return errors
