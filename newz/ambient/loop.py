"""The ambient loop (P2 Phase 0.4) — conversation, operator-only rehearsal.

Durability model (v1's operator_inbox lessons, whole):
- Inbound: normalize → persist as reply_status='pending' (dedup on
  update_id) → only then is Telegram's offset advanced. No window where the
  message exists only in memory.
- Replies: a single durable drainer works the pending queue oldest-first.
  It survives everything the process survives — and what the process does
  not survive, boot replays: any 'pending' message found at startup (a
  crash mid-reply, an LLM timeout, a kill) is answered then.
- Poison-guard: a message that fails composition MAX_ATTEMPTS times is
  marked 'poisoned' and skipped with a loud log and an honest note to the
  operator, so one un-composable message can never wedge the queue.

One drainer means replies are serialized in order and each composition sees
complete thread history."""

from __future__ import annotations

import asyncio
import logging
import sqlite3

from newz.channels.telegram import TelegramChannel
from newz.conversation.composer import (
    compose_reply,
    record_exchange_episode,
    record_message,
)
from newz.gate.outbound import OutboundGate
from newz.llm.client import LLMClient

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_BACKOFF_S = 20.0
IDLE_POLL_S = 5.0


class AmbientLoop:
    def __init__(
        self,
        conn: sqlite3.Connection,
        client: LLMClient,
        gate: OutboundGate,
        channel: TelegramChannel,
        operator_id: str,
        retriever=None,
    ):
        self._conn = conn
        self._client = client
        self._gate = gate
        self._channel = channel
        self._operator_id = operator_id
        self._retriever = retriever
        self._wake = asyncio.Event()

    # ── inbound: persist durable, wake the drainer, confirm to Telegram ──
    async def handle_inbound(
        self, update_id: int, chat_id: str, text: str, tg_message_id: int | None = None,
    ) -> bool:
        if text.startswith("/journal ") or text.startswith("/j "):
            return await self._journal_entry(update_id, text.split(" ", 1)[1].strip())
        msg_id = record_message(
            self._conn, channel="telegram", direction="in",
            person_id=self._operator_id, content=text, update_id=update_id,
            reply_status="pending", tg_message_id=tg_message_id,
        )
        if msg_id is None:
            logger.info("duplicate update %s — already queued", update_id)
            return True
        logger.info("queued inbound message %d (update %s)", msg_id, update_id)
        self._wake.set()
        return True

    async def _journal_entry(self, update_id: int, entry: str) -> bool:
        """P2 Rule 3 — the operator journal. Never reaches the being: no
        messages row, no episode, no prompt. `/journal v1: ...` tags an
        entry about the old system; default tag is v2."""
        import datetime
        import time as _time

        tag = "v2"
        for prefix in ("v1:", "v2:"):
            if entry.lower().startswith(prefix):
                tag = prefix[:2]
                entry = entry[len(prefix):].strip()
        if not entry:
            return True
        try:
            self._conn.execute(
                "INSERT INTO journal (ts, day, system_tag, entry, update_id)"
                " VALUES (?,?,?,?,?)",
                (_time.time(), datetime.date.today().isoformat(), tag, entry, update_id),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            return True  # redelivered — already recorded
        n = self._conn.execute("SELECT COUNT(*) FROM journal").fetchone()[0]
        logger.info("journal entry #%d recorded (%s)", n, tag)
        try:
            await self._channel.send(f"journal noted (#{n}, {tag})")
        except Exception:
            logger.exception("journal ack failed (entry is safe)")
        return True

    # ── the drainer: one worker, oldest-first, replay on boot ────────────
    async def drain_forever(self) -> None:
        pending = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE reply_status='pending'"
        ).fetchone()[0]
        if pending:
            logger.info("boot replay: %d unanswered message(s) in the queue", pending)
        while True:
            # The whole body is guarded: if this task dies, the channel keeps
            # polling and the being goes silently deaf — alive at the
            # transport, answering nothing. A transient store error (lock
            # contention with sleep or a migration, "schema has changed")
            # must cost a retry, never the drainer.
            try:
                rows = self._conn.execute(
                    "SELECT id, content, reply_attempts, tg_message_id FROM messages"
                    " WHERE reply_status='pending' ORDER BY ts"
                ).fetchall()
                if not rows:
                    self._wake.clear()
                    try:
                        await asyncio.wait_for(self._wake.wait(), timeout=IDLE_POLL_S)
                    except TimeoutError:
                        pass
                    continue
                if len(rows) > 1:
                    logger.info("coalescing %d pending messages into one reply", len(rows))
                await self._work_batch(rows)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("drainer error — retrying in %.0fs", RETRY_BACKOFF_S)
                await asyncio.sleep(RETRY_BACKOFF_S)

    async def _typing_forever(self) -> None:
        # Telegram's typing indicator lasts ~5s; refresh while composing so
        # a slow local-model reply never reads as a dead conversation.
        while True:
            await self._channel.send_typing()
            await asyncio.sleep(4.0)

    async def _work_batch(self, rows) -> None:
        msg_ids = [r["id"] for r in rows]
        texts = [r["content"] for r in rows]
        attempts = rows[0]["reply_attempts"]
        anchor = rows[-1]["tg_message_id"]
        typing = asyncio.get_running_loop().create_task(self._typing_forever())
        try:
            reply = await asyncio.to_thread(
                compose_reply, self._conn, self._client, self._gate,
                self._operator_id, texts, self._retriever,
            )
            typing.cancel()
            # Anchor the reply if the thread moved on while composing.
            newer = self._conn.execute(
                "SELECT COUNT(*) FROM messages WHERE direction='in' AND id > ?",
                (msg_ids[-1],),
            ).fetchone()[0]
            sent = await self._channel.send(
                reply.text, reply_to=anchor if newer else None,
            )
            if not sent:
                raise RuntimeError("telegram send failed")
        except Exception as e:
            typing.cancel()
            await self._fail_batch(msg_ids, attempts, e)
            return

        out_msg_id = record_message(
            self._conn, channel="telegram", direction="out",
            person_id=self._operator_id, content=reply.text, verdict=reply.verdict,
        )
        record_exchange_episode(
            self._conn, self._operator_id, "\n".join(texts), reply.text,
            msg_ids[0], out_msg_id,
        )
        await self._maybe_open_concern(texts, reply.text, msg_ids[0])
        # Which reply answered which messages — recorded, not left to be
        # inferred later. The batch is known here and nowhere else, and an
        # instrument that reconstructs it from timestamps counts one reply as
        # many exchanges (R-37d).
        self._conn.executemany(
            "UPDATE messages SET reply_status='replied', reply_attempts=?,"
            " answered_by=? WHERE id=?",
            [(attempts, out_msg_id, mid) for mid in msg_ids],
        )
        self._conn.commit()
        logger.info(
            "exchange complete: msgs=%s verdict=%s attempts=%d",
            msg_ids, reply.verdict, reply.attempts,
        )

    async def _maybe_open_concern(self, texts, reply: str, msg_id: int) -> None:
        """A conversation that surfaces something worth pursuing can open a
        concern (S2 §6.2). Almost never fires; failure costs nothing."""
        from newz.concerns.opener import open_from_conversation
        from newz.concerns.store import create_concern

        exchange = "\n".join(f"[{self._operator_id}] {t}" for t in texts) + f"\n[me] {reply}"
        try:
            proposal = await asyncio.to_thread(
                open_from_conversation, self._conn, self._client,
                person_id=self._operator_id, exchange=exchange,
                source_ref=f"message:{msg_id}",
            )
        except Exception:
            logger.exception("concern opener failed (the exchange is safe)")
            return
        if not proposal.accepted:
            logger.debug("opener: %s", proposal.reason)
            return
        cid = create_concern(self._conn, proposal.concern)
        logger.info("opened concern %d from conversation: %s",
                    cid, proposal.concern.statement[:90])

    async def _fail_batch(self, msg_ids: list[int], attempts: int, e: Exception) -> None:
        attempts += 1
        oldest = msg_ids[0]
        if attempts >= MAX_ATTEMPTS:
            # Poison only the oldest message — the rest of the batch gets
            # another chance without it (it may be the un-composable one).
            self._conn.execute(
                "UPDATE messages SET reply_status='poisoned', reply_attempts=?"
                " WHERE id=?", (attempts, oldest),
            )
            self._conn.commit()
            logger.error(
                "message %d POISONED after %d attempts: %s", oldest, attempts, e,
            )
            try:
                await self._channel.send(
                    "I tried three times to answer your last message and "
                    "couldn't compose a reply. It's recorded; ask me differently "
                    "or check my logs."
                )
            except Exception:
                logger.exception("poison notice also failed to send")
        else:
            self._conn.execute(
                "UPDATE messages SET reply_attempts=? WHERE id=?",
                (attempts, oldest),
            )
            self._conn.commit()
            logger.warning(
                "batch %s attempt %d failed (%s); retrying in %.0fs",
                msg_ids, attempts, e, RETRY_BACKOFF_S,
            )
            await asyncio.sleep(RETRY_BACKOFF_S)

    async def run(self) -> None:
        drainer = asyncio.create_task(self.drain_forever())
        try:
            await self._channel.run(self.handle_inbound)
        finally:
            drainer.cancel()
        # If the drainer ever exits on its own, that is a defect worth a
        # loud death rather than a quiet deafness.
        if drainer.done() and not drainer.cancelled():
            exc = drainer.exception()
            if exc is not None:
                logger.critical("drainer died: %r", exc)
                raise exc
