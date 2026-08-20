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
    measurement code is writable is not frozen."""
    out: set[str] = set()
    try:
        tree = ast.parse((REPO / tool).read_text())
    except (OSError, SyntaxError):
        return out
    for node in ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            mods = [node.module]
        elif isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        for m in mods:
            if m.startswith("newz.evidence."):
                out.add("newz/" + m.split("newz.", 1)[1].replace(".", "/") + ".py")
    return out


def canonical_paths() -> list[str]:
    """The frozen instrument set: canonical tools plus the evidence modules
    that compute their numbers."""
    paths = set(canonical_tools())
    for tool in canonical_tools():
        paths |= _evidence_imports(tool)
    return sorted(p for p in paths if (REPO / p).exists())


def protected_paths() -> list[str]:
    """Everything inside the core: the registry's own paths plus the derived
    instrument set. Section-protected files (PLAN.md) are NOT here — see
    `sections`, and `open_gaps` for why nothing enforces them."""
    return sorted(set(r["path"] for r in registry().get("paths", [])) | set(canonical_paths()))


def contains(path: str | Path) -> bool:
    """Is `path` inside the hard core? Directory entries match by prefix."""
    rel = str(Path(path)).lstrip("./")
    for p in protected_paths():
        if p.endswith("/") and rel.startswith(p):
            return True
        if rel == p.rstrip("/"):
            return True
    return False


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
    for key in ("version", "paths", "derived_from", "sections", "open_gaps", "state"):
        if key not in reg:
            errors.append(f"registry is missing {key!r}")
    for row in reg.get("paths", []):
        if not row.get("path") or not row.get("why"):
            errors.append(f"path row without a path and a why: {row!r}")
            continue
        target = REPO / row["path"]
        if not target.exists():
            errors.append(f"{row['path']} is in the hard core and does not exist")
    for row in reg.get("open_gaps", []):
        if not row.get("what") or not row.get("detail"):
            errors.append(f"open_gaps row without a what and a detail: {row!r}")
    if not canonical_paths():
        errors.append("the derived canonical set is empty")
    return errors
