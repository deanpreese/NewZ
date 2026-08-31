"""Bounded reachability probe: for each open claim, does ANY adapter in the
real resolution set return a candidate for the resolver text?

Read-only. No model calls. Measures what a door-side reachability check would
refuse, before anything is built."""
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from newz.world.harvest import HarvestAdapter          # noqa: E402
from newz.world.sources import default_adapters        # noqa: E402

DB = Path(__file__).resolve().parent.parent / "data" / "newz.db"
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
adapters = [HarvestAdapter(conn)] + default_adapters()
names = [type(a).__name__ for a in adapters]
print("adapters:", names, file=sys.stderr)

rows = conn.execute(
    "SELECT id, kind, resolver FROM resolutions WHERE status='open' ORDER BY id").fetchall()
out = []
for r in rows:
    q = (r['resolver'] or '').strip()
    hits = {}
    for a in adapters:
        try:
            res = a.search(q, limit=3)
        except Exception as e:
            res = []
            hits[type(a).__name__] = f"ERR {type(e).__name__}"
            continue
        if res:
            hits[type(a).__name__] = len(res)
    out.append({"id": r['id'], "kind": r['kind'], "resolver": q[:70],
                "reachable": bool(hits), "hits": hits})
    print(f"{r['id']:3} {r['kind'][:5]:5} {'REACH' if hits else 'NONE '} "
          f"{ {k: v for k, v in hits.items()} } :: {q[:60]}", flush=True)
    time.sleep(2.0)   # the crawl delay the adapters are built to respect
if len(sys.argv) > 1:
    json.dump(out, open(sys.argv[1], "w"), indent=1)
n = len(out); reach = sum(1 for o in out if o['reachable'])
print(f"\nREACHABLE {reach}/{n}   would-refuse {n-reach}/{n} = {100*(n-reach)/n:.0f}%")
