import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_invariant_ledger_is_clean():
    proc = subprocess.run(
        [sys.executable, str(REPO / "tools" / "check_invariants.py")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
