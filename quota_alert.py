"""Owner notifications for exhausted AI provider credits."""
from __future__ import annotations

import asyncio
import logging
import os

from publisher import TelegramPublisher

logger = logging.getLogger(__name__)


def is_insufficient_quota_error(exc: BaseException) -> bool:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("code") in {
            "insufficient_quota",
            "credit_balance_exhausted",
            "billing_hard_limit_reached",
        }:
            return True
    message = str(exc).casefold()
    return any(
        marker in message
        for marker in (
            "insufficient_quota",
            "credit_balance_exhausted",
            "billing_hard_limit_reached",
            "no credits remaining",
        )
    )


class QuotaAlertGuard:
    """Send one private Telegram alert for each continuous quota outage."""

    def __init__(self) -> None:
        self._alerted = False

    async def notify_once(self, context: str) -> bool:
        if self._alerted:
            return False
        chat_id = os.getenv("ALERT_TELEGRAM_CHAT_ID")
        if not chat_id:
            logger.error("ALERT_TELEGRAM_CHAT_ID is missing; quota alert was not delivered")
            return False

        self._alerted = True
        message = (
            "Закончились кредиты OpenAI API. "
            f"{context} временно не работает; материалы не потеряны. "
            "После пополнения баланса сервис попробует снова автоматически."
        )
        publisher = TelegramPublisher(chat_id=chat_id)
        sent = await asyncio.get_running_loop().run_in_executor(
            None,
            publisher._send_message,
            message,
        )
        if not sent:
            self._alerted = False
        return sent

    def mark_recovered(self) -> None:
        self._alerted = False


quota_alert_guard = QuotaAlertGuard()
