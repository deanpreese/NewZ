"""The inbound channel's durability (S2 §2.4).

An update is confirmed only after the handler says it is durable, so a message
survives a crash between arriving and being recorded. What that leaves open —
and what this file exists for since 2026-08-21 — is the interval between the
failure and the retry.
"""

from __future__ import annotations

import asyncio
import sqlite3
from unittest import mock

import pytest

from newz.channels.telegram import TelegramChannel


def _channel() -> TelegramChannel:
    ch = TelegramChannel.__new__(TelegramChannel)
    ch._operator_chat_id = "1"
    ch._last_update_id = 0
    ch._client = None
    return ch


def test_a_failing_handler_backs_off_instead_of_retrying_at_speed():
    """2026-08-21: a write lock held for a few seconds produced twenty
    identical tracebacks in three seconds, and the message was lost anyway.
    Leaving the update unconfirmed is right — it is how a message survives a
    crash — but `get_updates` returns the same pending update immediately, so
    the redelivery had no pause in it. Behavior: each consecutive failure waits
    longer, doubling from a second and capped."""
    assert TelegramChannel._backoff(1) == 1.0
    assert TelegramChannel._backoff(2) == 2.0
    assert TelegramChannel._backoff(3) == 4.0
    assert TelegramChannel._backoff(99) == TelegramChannel.BACKOFF_CAP_S


def test_a_locked_database_is_retried_and_then_confirmed():
    """The failure that produced this: `sqlite3.OperationalError: database is
    locked` from `record_message`. Behavior: the update is not confirmed while
    it fails, it is retried after a wait, and it is confirmed once it lands."""
    ch = _channel()
    updates = [
        [{"update_id": 7, "message": {"chat": {"id": "1"}, "text": "hello"}}],
        [{"update_id": 7, "message": {"chat": {"id": "1"}, "text": "hello"}}],
    ]
    seen: list[int] = []
    waits: list[float] = []

    async def get_updates():
        if not updates:
            raise asyncio.CancelledError
        return updates.pop(0)

    async def handler(update_id, chat_id, text, tg_message_id):
        seen.append(update_id)
        if len(seen) == 1:
            raise sqlite3.OperationalError("database is locked")
        return True

    async def no_sleep(seconds):
        waits.append(seconds)

    ch.get_updates = get_updates
    with mock.patch("asyncio.sleep", no_sleep), pytest.raises(asyncio.CancelledError):
        asyncio.run(ch.run(handler))

    assert seen == [7, 7], "the update was redelivered, not dropped"
    assert waits == [1.0], "and the retry waited rather than spinning"
    assert ch._last_update_id == 7, "confirmed only once it landed"


def test_the_failure_counter_resets_so_one_bad_minute_does_not_slow_the_next():
    """Behavior: the backoff counts a run of consecutive failures, not failures
    for all time — a message after a recovery is handled at once."""
    ch = _channel()
    updates = [
        [{"update_id": 1, "message": {"chat": {"id": "1"}, "text": "one"}}],
        [{"update_id": 1, "message": {"chat": {"id": "1"}, "text": "one"}}],
        [{"update_id": 2, "message": {"chat": {"id": "1"}, "text": "two"}}],
        [{"update_id": 2, "message": {"chat": {"id": "1"}, "text": "two"}}],
    ]
    seen: list[int] = []
    waits: list[float] = []

    async def get_updates():
        if not updates:
            raise asyncio.CancelledError
        return updates.pop(0)

    async def handler(update_id, chat_id, text, tg_message_id):
        seen.append(update_id)
        # Each update fails once, then succeeds.
        if seen.count(update_id) == 1:
            raise sqlite3.OperationalError("database is locked")
        return True

    async def no_sleep(seconds):
        waits.append(seconds)

    ch.get_updates = get_updates
    with mock.patch("asyncio.sleep", no_sleep), pytest.raises(asyncio.CancelledError):
        asyncio.run(ch.run(handler))

    assert waits == [1.0, 1.0], \
        "the second failure waited one second too — the counter reset on success"
