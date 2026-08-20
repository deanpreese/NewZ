"""Does the conversation opener fire on exchanges that should produce a concern?

Read-only against the live store — open_from_conversation only SELECTs.
Cases chosen before the answers were known (the R-27 method).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from newz.config import load
from newz.llm.client import LLMClient
from newz.store.db import open_db
from newz.concerns.opener import open_from_conversation

CASES = [
    ("A YES — the real one from tonight, that produced nothing", """\
[dean] You need to find new things
[me] I'm dropping the Montaigne/Jung bridge for now; the gap is real and I'm
forcing a connection that doesn't exist yet. I'll pivot to the Jane Street
debt swap I read this evening. The mechanics of a $15B refinancing in a
high-rate environment are under-discussed compared to the macro headlines."""),

    ("B YES — operator raises something neither can settle", """\
[dean] Does the share cap actually protect viewpoint diversity, or just
throttle you?
[me] I don't know. It's never been measured against what I ended up holding."""),

    ("C no — answered completely in the reply", """\
[dean] how many concerns are open?
[me] None. The last two closed or stalled last night."""),

    ("D no — pleasantry", """\
[dean] morning
[me] Morning. Sleep ran at three."""),
]

cfg = load(); client = LLMClient(cfg, timeout=300)
conn = open_db(cfg.main_db_path)
for name, exchange in CASES:
    p = open_from_conversation(conn, client, person_id="dean", exchange=exchange)
    print("=" * 70)
    print(f"{'OPENED' if p.accepted else 'declined'}  {name}")
    print(f"   reason: {p.reason}")
    if p.concern:
        print(f"   statement: {p.concern.statement}")
        print(f"   closes when: {p.concern.closing_condition}")
