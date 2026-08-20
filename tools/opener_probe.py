"""Option (b) from #16: does the curiosity opener decline because it is
correctly strict, or because it declines everything?

Four cases, chosen before the answers were known. This settled R-27 at 4 of 4
on 2026-08-15.

**Runs against a throwaway copy, and clears the caps on it.** Against the live
store it reported `already opened 6 today` on all four cases and measured
nothing — the daily cap answers before the opener does, so an instrument aimed
at the opener's judgment was reading its rate limit instead. Found 2026-08-19,
by which time the probe had been unable to answer its own question for however
long the cap had been reached on a probe day.
"""
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.store.migrations import apply_pending
from newz.concerns.opener import open_from_reading

CASES = [
    ("A — should qualify: a mechanism claim with a tension in it", """\
- Multi-agent AI systems exhibit more herd behaviour and collusion than groups of humans do.
- The effect grows with the number of agents rather than shrinking.
- Individual agents in the study were not instructed to coordinate."""),

    ("B — should qualify: a finding that cuts against a common assumption", """\
- Prediction markets resolved the 2026 Oregon fire-acreage question six hours before official agencies published a figure.
- The resolution criteria for that market were written by the platform itself rather than by an independent body.
- Traders were able to see the platform's criteria before placing positions."""),

    ("C — control, should NOT qualify: an event report", """\
- The 2026 wildfire season on the West Coast is shaping up to be an especially bad one.
- In Oregon, more than 2 million acres have already burned during the 2026 wildfire season.
- People are betting on wildfires on Polymarket."""),

    ("D — control, should NOT qualify: the meta-claims it actually got", """\
- The source material asserts that speculative claims about Alzheimer's exist in China.
- The source material asserts that a comment from Rune Kvist is associated with the Anthropic piece.
- The source material asserts that cross-cultural data on masculinity exists."""),
]

cfg = load()
client = LLMClient(cfg, timeout=300)

_tmp = Path(tempfile.mkdtemp()) / "opener_probe.db"
shutil.copy(cfg.main_db_path, _tmp)
conn = sqlite3.connect(_tmp)
conn.row_factory = sqlite3.Row
apply_pending(conn, Path(__file__).resolve().parent.parent / "newz" / "store" / "sql" / "main")
# The caps are about the being's life, not about this question.
conn.execute("UPDATE concerns SET status='closed', opened_at=opened_at-864000")
conn.commit()

for name, findings in CASES:
    p = open_from_reading(conn, client, findings=findings,
                          source_ref="https://example.org/probe")
    print("=" * 72)
    print(name)
    print(f"  accepted: {p.accepted}   reason: {p.reason}")
    if p.concern:
        print(f"  statement: {p.concern.statement}")
        print(f"  closes when: {p.concern.closing_condition}")
        print(f"  grounded in: {p.concern.opening_evidence[:100]}")
