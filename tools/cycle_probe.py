"""Where does a deliberation cycle stop? Timed, against a throwaway copy.

`run_once`'s first action is `_settle_due_claims`, and the last claim_resolver
call in life is the same minute deliberation last ran. This walks the same
stages with a wall clock on each so a stall names itself.

Read-only against the live store: it is copied first, exactly as
resolver_probe.py does, and every write lands on the copy.
"""
import faulthandler
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from newz.config import load                                    # noqa: E402
from newz.store.db import open_db                               # noqa: E402

# If anything blocks for 120s, print every thread's stack and keep going.
faulthandler.dump_traceback_later(120, exit=False)

cfg = load()
tmp = Path(tempfile.mkdtemp(prefix="hang-probe-"))
copy = tmp / "probe.db"
shutil.copy2(cfg.main_db_path, copy)
print(f"copy: {copy}", flush=True)
conn = open_db(copy)


def stage(name, fn):
    t = time.time()
    print(f"  -> {name} …", flush=True)
    try:
        out = fn()
        print(f"     {name}: {time.time()-t:.1f}s  {out!r}"[:200], flush=True)
        return out
    except Exception as e:
        print(f"     {name}: RAISED after {time.time()-t:.1f}s  "
              f"{type(e).__name__}: {e}"[:300], flush=True)
        raise


from newz.deliberation.lite import Deliberator                  # noqa: E402
from newz.llm.client import LLMClient                           # noqa: E402
from newz.resolutions.resolver import workable_claims           # noqa: E402

client = LLMClient(cfg)
d = Deliberator(copy, client, research=True,
                feeds_path=cfg.repo_root / "data" / "feeds.yaml")

stage("spent_today", lambda: d.spent_today(conn))
stage("workable_claims", lambda: [c.id for c in workable_claims(conn)])
stage("_settle_due_claims  <-- the suspect", lambda: d._settle_due_claims(conn))

from newz.concerns.store import load_active                     # noqa: E402
from newz.deliberation.lite import choose_concern               # noqa: E402
cs = stage("load_active", lambda: len(load_active(conn)))
ch = stage("choose_concern",
           lambda: choose_concern(load_active(conn), now=time.time()))
print(f"\nreached concern selection: {getattr(ch.concern, 'id', None)}",
      flush=True)
print(f"copy left at {tmp}")
