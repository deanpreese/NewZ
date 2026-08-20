"""Option (b) from #16: does the curiosity opener decline because it is
correctly strict, or because it declines everything?

Read-only against the live store — open_from_reading only SELECTs; nothing is
created. Four cases, chosen before the answers were known.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.store.db import open_db
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
conn = open_db(cfg.main_db_path)

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
