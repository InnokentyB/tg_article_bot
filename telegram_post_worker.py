"""Durable Telegram publishing worker."""
from __future__ import annotations

import asyncio
import html
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramPostDispatcher:
    """Publishes due Telegram posts from the database queue."""

    def __init__(self, db_manager) -> None:
        self._db = db_manager

    async def process_due_posts(self, *, limit: int = 20) -> int:
        posts = await self._db.get_due_telegram_posts(limit=limit)
        sent = 0
        loop = asyncio.get_running_loop()

        for post in posts:
            try:
                ok = await loop.run_in_executor(None, self._publish_message, post["message"])
                if not ok:
                    raise RuntimeError("Telegram API returned an unsuccessful response")
            except Exception as exc:
                logger.warning(
                    "[TelegramPostDispatcher] Failed to publish post_id=%s type=%s: %s",
                    post["id"],
                    post.get("post_type"),
                    exc,
                )
                await self._db.mark_telegram_post_failed(post["id"], str(exc))
                continue

            await self._db.mark_telegram_post_sent(post["id"])
            sent += 1
            logger.info(
                "[TelegramPostDispatcher] Published post_id=%s type=%s review_id=%s",
                post["id"],
                post.get("post_type"),
                post.get("review_id"),
            )

        return sent

    def _publish_message(self, message: str) -> bool:
        from publisher import TelegramPublisher

        publisher = TelegramPublisher()
        ok = True
        for chunk in self._split_telegram_message(message):
            ok = publisher._send_message(html.escape(chunk), parse_mode="HTML") and ok
        return ok

    @staticmethod
    def _split_telegram_message(message: str, limit: int = 3900) -> list[str]:
        if len(message) <= limit:
            return [message]
        chunks = []
        current = []
        current_len = 0
        for paragraph in message.split("\n\n"):
            paragraph_len = len(paragraph) + 2
            if current and current_len + paragraph_len > limit:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            current.append(paragraph)
            current_len += paragraph_len
        if current:
            chunks.append("\n\n".join(current))
        return chunks


class TelegramPostWorker:
    """Background loop for durable Telegram publishing."""

    def __init__(self, db_manager) -> None:
        self._db = db_manager
        self._enabled = os.getenv("TELEGRAM_POST_WORKER_ENABLED", "true").lower() == "true"
        self._poll_seconds = int(os.getenv("TELEGRAM_POST_WORKER_POLL_SECONDS", "60"))
        self._limit = int(os.getenv("TELEGRAM_POST_WORKER_BATCH_SIZE", "20"))
        self._task: Optional[asyncio.Task] = None
        self._dispatcher = TelegramPostDispatcher(db_manager)

    def start(self) -> None:
        if not self._enabled:
            logger.info("[TelegramPostWorker] Disabled via TELEGRAM_POST_WORKER_ENABLED=false.")
            return
        if self._task and not self._task.done():
            logger.warning("[TelegramPostWorker] Already running.")
            return
        self._task = asyncio.create_task(self._loop(), name="telegram_post_worker")
        logger.info("[TelegramPostWorker] Started. poll_seconds=%s", self._poll_seconds)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[TelegramPostWorker] Cancellation requested.")

    async def _loop(self) -> None:
        while True:
            try:
                sent = await self._dispatcher.process_due_posts(limit=self._limit)
                if sent:
                    logger.info("[TelegramPostWorker] Published %d queued Telegram post(s).", sent)
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[TelegramPostWorker] Loop cancelled.")
                break
            except Exception as exc:
                logger.exception("[TelegramPostWorker] Unexpected error: %s", exc)
                await asyncio.sleep(self._poll_seconds)
