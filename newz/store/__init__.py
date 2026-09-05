"""The durable store: one SQLite file, one content-addressed artifact tree.

ADR-0001. Everything above this package speaks in records, not in SQL.
"""

from newz.store.db import Store, open_store

__all__ = ["Store", "open_store"]
