"""Telegram channel — ported with review from v1
(`ngbeing/channels/telegram/{inbound,outbound,normalize}.py`, S2 §16
allowlist). Raw Bot API over httpx, no SDK.

The load-bearing ordering lesson (v1, 2026-08-04) is kept whole: Telegram
treats `offset` as confirmation and permanently drops confirmed updates.
Therefore: normalize → persist (durable, deduped on update_id) → THEN
advance the offset. There is no window in which a message exists only in
memory while Telegram has been told to forget it.

Review changes: v1's Percept/queue machinery is replaced by a direct
async callback (Phase 0.4 has one consumer — the conversation handler);
persistence goes to v2's `messages` table via the callback's return
contract rather than a separate operator_inbox store."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# handler(update_id, chat_id, text, tg_message_id) -> True when durably
# persisted (or known duplicate); False/raise when persistence failed →
# offset NOT advanced.
Handler = Callable[[int, str, str, int | None], Awaitable[bool]]


class TelegramChannel:
    def __init__(
        self,
        bot_token: str,
        operator_chat_id: str,
        *,
        long_poll_timeout: int = 30,
    ) -> None:
        self._token = bot_token
        self._operator_chat_id = str(operator_chat_id)
        self._timeout = long_poll_timeout
        self._last_update_id = 0
        self._client: httpx.AsyncClient | None = None

    @property
    def _base(self) -> str:
        return f"https://api.telegram.org/bot{self._token}"

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout + 10)
        return self._client

    async def send(self, text: str, *, reply_to: int | None = None) -> bool:
        client = await self._http()
        # Telegram hard-caps messages at 4096 chars; split on paragraph seams.
        chunks = _split_message(text)
        for i, chunk in enumerate(chunks):
            body: dict[str, Any] = {"chat_id": self._operator_chat_id, "text": chunk}
            if reply_to is not None and i == 0:
                # Anchor a late reply to the message it answers; if that
                # message is gone, send normally rather than fail.
                body["reply_parameters"] = {
                    "message_id": reply_to,
                    "allow_sending_without_reply": True,
                }
            resp = await client.post(f"{self._base}/sendMessage", json=body)
            if resp.status_code != 200 or not resp.json().get("ok"):
                logger.warning("telegram send failed: %s", resp.text[:200])
                return False
        return True

    async def send_typing(self) -> None:
        """Show 'typing…' for ~5s; refresh while composing. Best-effort."""
        try:
            client = await self._http()
            await client.post(
                f"{self._base}/sendChatAction",
                json={"chat_id": self._operator_chat_id, "action": "typing"},
            )
        except httpx.HTTPError:
            pass

    async def get_updates(self) -> list[dict[str, Any]]:
        client = await self._http()
        params: dict[str, Any] = {
            "timeout": self._timeout,
            "allowed_updates": '["message"]',
        }
        if self._last_update_id:
            params["offset"] = self._last_update_id + 1
        try:
            resp = await client.get(f"{self._base}/getUpdates", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("telegram getUpdates failed: %s", e)
            await asyncio.sleep(3)
            return []
        if not data.get("ok"):
            logger.warning("telegram getUpdates not-ok: %s", str(data)[:200])
            return []
        # Offset deliberately NOT advanced here — see module docstring.
        return data.get("result", []) or []

    def _normalize(self, update: dict[str, Any]) -> tuple[int, str, str, int | None] | None:
        msg = update.get("message") or {}
        chat_id = str((msg.get("chat") or {}).get("id", ""))
        text = msg.get("text") or ""
        update_id = update.get("update_id")
        if not isinstance(update_id, int) or not text:
            return None
        if chat_id != self._operator_chat_id:
            # Rehearsal boundary (S2 §2.4): no one but the operator.
            logger.info("telegram: ignoring message from non-operator chat %s", chat_id)
            return None
        raw_mid = msg.get("message_id")
        tg_message_id = raw_mid if isinstance(raw_mid, int) else None
        return update_id, chat_id, text, tg_message_id

    async def run(self, handler: Handler) -> None:
        logger.info("telegram inbound starting (operator chat %s)", self._operator_chat_id)
        try:
            while True:
                for update in await self.get_updates():
                    normalized = self._normalize(update)
                    update_id = update.get("update_id")
                    if normalized is None:
                        # Not for us — advance so we don't refetch forever.
                        if isinstance(update_id, int):
                            self._last_update_id = max(self._last_update_id, update_id)
                        continue
                    try:
                        durable = await handler(*normalized)
                    except Exception:
                        logger.exception(
                            "handler failed for update %s; leaving unconfirmed "
                            "for redelivery", update_id,
                        )
                        break  # do not confirm this one nor later ones in batch
                    if durable:
                        self._last_update_id = max(self._last_update_id, update_id)
                    else:
                        break
        except asyncio.CancelledError:
            logger.info("telegram inbound shutting down")
            raise
        finally:
            if self._client is not None:
                await self._client.aclose()
                self._client = None


def _split_message(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks, current = [], ""
    for para in text.split("\n\n"):
        candidate = (current + "\n\n" + para) if current else para
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            while len(para) > limit:
                chunks.append(para[:limit])
                para = para[limit:]
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
