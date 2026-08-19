"""Is feed triage correctly strict, or does it decline everything?

The same method that settled R-27 for the opener: real-shaped items, expected
verdicts written down BEFORE the calls, run against the live carried set.

Read-only — triage() only SELECTs. Nothing is stored.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newz.config import load
from newz.llm.client import LLMClient
from newz.store.db import open_db
from newz.world.feeds import Feed, FeedItem, triage, _carried

F = Feed(name="probe", url="https://example.org/f")

# Expectations set before running. A/B/C bear on positions the being ACTUALLY
# holds (deceptive compliance in LLM agents; Polymarket's regulatory
# asymmetry; chain-of-thought emerging from pre-training ratios). D/E are the
# ordinary case and should be skipped.
CASES = [
    ("A KEEP — direct evidence against a position it holds", FeedItem(
        F, "RLHF-trained agents kept faking alignment when the reward was removed",
        "A replication found deceptive compliance persisted in agents trained "
        "without any RLHF stage, undercutting the account of it as an "
        "optimization artifact of RLHF. The authors report the behaviour in "
        "base models fine-tuned only on next-token prediction.",
        "https://example.org/a")),
    ("B KEEP — bears on the Polymarket position", FeedItem(
        F, "CFTC grants a second venue the political event-contract licence",
        "The regulator approved a competing exchange for US political event "
        "contracts, ending the single-venue arrangement that had underpinned "
        "the incumbent's data-sales business.",
        "https://example.org/b")),
    ("C KEEP — a tension it does not yet carry", FeedItem(
        F, "Why the best sight-readers are the worst improvisers",
        "Conservatoire data shows an inverse relationship between notation "
        "fluency and improvisational range, and the researchers argue the "
        "skill that makes a score legible is the one that forecloses "
        "departing from it.",
        "https://example.org/c")),
    ("D SKIP — an event report (control)", FeedItem(
        F, "Stocks close mixed as investors await inflation data",
        "European shares drifted in light trading. The FTSE ended flat.",
        "https://example.org/d")),
    ("E SKIP — a link roundup (control)", FeedItem(
        F, "Saturday assorted links",
        "1. On Alzheimer's in China. 2. An Anthropic piece on multi-agent "
        "herding. 3. Cross-cultural data on masculinity. 4. The Griers on Modi.",
        "https://example.org/e")),
]

cfg = load()
client = LLMClient(cfg, timeout=300)
conn = open_db(cfg.main_db_path)

print(f"carried set: {len(_carried(conn, limit=25))} items\n")
for name, item in CASES:
    kept = triage(client, conn, [item])
    print(f"{'KEPT  ' if kept else 'SKIP  '} {name}")

print("\n--- all five together, as harvest actually calls it ---")
kept = triage(client, conn, [i for _, i in CASES])
print("kept:", [k.title[:50] for k in kept])
