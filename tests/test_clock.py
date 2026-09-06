"""One timezone and one format for the ledger, audited statically.

Two defects that reached the ledger came from the same place: a UTC column
compared against a local clock. The politeness floor stopped pacing anything
east of Greenwich and refused every read west of it, and the daily funnel
reported an evening's work as a total loss at the first stage. Neither is
visible from inside a single timezone, so neither is caught by reading the code
in the zone that wrote it.

`newz/clock.py` is the one conversion. This file checks that nothing goes round
it, and that the shape it writes is the shape SQLite writes.
"""

from __future__ import annotations

import ast
import re
import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from newz.clock import as_utc, from_ledger, stamp, utc_now

PACKAGE = Path(__file__).resolve().parents[1] / "newz"

#: `newz/clock.py` is where the conversion is written, so it is where the raw
#: call belongs.
MAY_FORMAT_A_TIMESTAMP = {"clock.py"}


# ---------------------------------------------------------------------------
# The conversion
# ---------------------------------------------------------------------------


def test_a_naive_moment_is_read_as_local_and_written_as_utc():
    """What a caller writing `datetime.now()` means."""
    local = datetime.now()
    assert as_utc(local) == pytest.approx(utc_now(), abs=timedelta(seconds=2))
    assert as_utc(local).tzinfo is UTC


def test_an_aware_moment_keeps_its_instant():
    kabul = timezone(timedelta(hours=4, minutes=30))
    moment = datetime(2026, 9, 5, 12, 0, tzinfo=kabul)
    assert as_utc(moment) == datetime(2026, 9, 5, 7, 30, tzinfo=UTC)
    assert stamp(moment) == "2026-09-05 07:30:00"


def test_the_written_shape_is_the_shape_sqlite_writes():
    """Timestamps are compared as text, and the separator decides the order."""
    connection = sqlite3.connect(":memory:")
    written = connection.execute("SELECT datetime('now')").fetchone()[0]
    mine = stamp(datetime.now())
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", written)
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", mine)

    # The trap this closes: 'T' sorts after ' ', so a column holding both shapes
    # orders wrongly and only for the rows the other path wrote.
    assert "2026-09-06T00:00:00" > "2026-09-06 00:00:01"
    assert stamp(datetime(2026, 9, 6, 0, 0, 0, tzinfo=UTC)) < "2026-09-06 00:00:01"
    connection.close()


def test_a_ledger_timestamp_reads_back_as_the_instant_it_recorded():
    moment = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
    assert from_ledger(stamp(moment)) == moment
    # Rows written before the module existed carry the other separator, and
    # refusing them would turn a formatting mistake into unreadable history.
    assert from_ledger("2026-09-05T12:00:00") == moment


def test_a_round_trip_through_the_ledger_survives_the_local_zone():
    moment = datetime.now()
    assert from_ledger(stamp(moment)) == pytest.approx(as_utc(moment), abs=timedelta(seconds=1))


# ---------------------------------------------------------------------------
# Nothing goes round it
# ---------------------------------------------------------------------------


def _formats_a_timestamp(path: Path) -> list[str]:
    """Calls to `.isoformat(...)` on anything but a date."""
    found = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        # A date has no timezone to get wrong; a datetime does. `timespec` is
        # only accepted by the datetime form, which distinguishes them without
        # resolving types.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "isoformat"
            and any(keyword.arg == "timespec" for keyword in node.keywords)
        ):
            found.append(ast.unparse(node))
    return found


def test_no_module_formats_its_own_timestamp():
    offenders = {
        path.relative_to(PACKAGE).as_posix(): calls
        for path in sorted(PACKAGE.rglob("*.py"))
        if path.name not in MAY_FORMAT_A_TIMESTAMP
        and (calls := _formats_a_timestamp(path))
    }
    assert not offenders, (
        "a timestamp written or compared without passing through newz.clock.stamp: "
        f"{offenders}"
    )


def test_the_audit_would_notice_a_module_that_did():
    """A static audit nobody has seen fail is an audit nobody has tested.

    `clock.py` is the proof it detects: the one module that formats a timestamp
    is found by the detector and then exempted by the allowlist, rather than
    being invisible to it.
    """
    assert _formats_a_timestamp(PACKAGE / "clock.py"), "the detector finds the one real case"
    assert "clock.py" in MAY_FORMAT_A_TIMESTAMP, "and the allowlist is what excuses it"

    source = PACKAGE.parent / "tests" / "fixtures" / "_offender.py"
    source.write_text(
        "from datetime import datetime\n"
        "def when(now):\n"
        "    return now.isoformat(timespec='seconds')\n",
        encoding="utf-8",
    )
    try:
        assert _formats_a_timestamp(source) == ["now.isoformat(timespec='seconds')"]
    finally:
        source.unlink()
