"""Commitment persistence (P4 epic E4.1).

Two of the door's refusals are in the schema (0041) because they are
structural; the rest need the model's answer or the standing rows and live in
the door.

**No episodes are written here**, for the reason `newz/resolutions/store.py`
gives: authoring a commitment is an event of the door, which is the layer that
knows why it happened, and a store that writes episodes turns every future
backfill into a corpus write.
"""

from __future__ import annotations

import logging
import sqlite3
import time

from newz.commitments.model import KINDS, Commitment

logger = logging.getLogger(__name__)

_FIELDS = ("id, ts, kind, statement, falsifier, provenance, status,"
           " constitution_version, perspective_version")


def _row(r: sqlite3.Row) -> Commitment:
    return Commitment(
        id=r["id"], ts=r["ts"], kind=r["kind"], statement=r["statement"],
        falsifier=r["falsifier"], provenance=r["provenance"],
        status=r["status"], constitution_version=r["constitution_version"],
        perspective_version=r["perspective_version"])


def author(conn: sqlite3.Connection, c: Commitment) -> int:
    """Write a commitment. The caller has already passed it through the door."""
    if c.kind not in KINDS:
        raise ValueError(f"unknown commitment kind: {c.kind!r}")
    cur = conn.execute(
        "INSERT INTO commitments (ts, kind, statement, falsifier, provenance,"
        " status, constitution_version, perspective_version)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (c.ts or time.time(), c.kind, c.statement.strip(), c.falsifier.strip(),
         c.provenance, c.status, c.constitution_version, c.perspective_version))
    conn.commit()
    logger.info("commitment %d authored (%s): %s",
                cur.lastrowid, c.kind, c.statement[:90])
    return int(cur.lastrowid)


def standing(conn: sqlite3.Connection) -> list[Commitment]:
    return [_row(r) for r in conn.execute(
        f"SELECT {_FIELDS} FROM commitments WHERE status='standing'"
        " ORDER BY ts DESC")]


def standing_count(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE status='standing'").fetchone()[0]


def authored_since(conn: sqlite3.Connection, since: float) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM commitments WHERE ts > ?", (since,)).fetchone()[0]


def all_commitments(conn: sqlite3.Connection) -> list[Commitment]:
    """Everything, including what E4.2 will later revise or abandon.

    Nothing prunes this table — E1.5's discipline, applied to identity. A
    commitment the being dropped is part of who it was, and a record of
    abandonment that can be tidied away is not a record.
    """
    return [_row(r) for r in conn.execute(
        f"SELECT {_FIELDS} FROM commitments ORDER BY ts DESC")]
