from quota_alert import QuotaAlertGuard, is_insufficient_quota_error


def test_quota_error_detection() -> None:
    assert is_insufficient_quota_error(
        RuntimeError("429: credit_balance_exhausted")
    ) is True
    assert is_insufficient_quota_error(RuntimeError("connection timeout")) is False


async def test_alert_is_sent_only_once_until_recovery(monkeypatch) -> None:
    sent: list[str] = []

    class FakePublisher:
        def __init__(self, chat_id=None) -> None:
            self.chat_id = chat_id

        def _send_message(self, message: str) -> bool:
            sent.append(message)
            return True

    monkeypatch.setenv("ALERT_TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr("quota_alert.TelegramPublisher", FakePublisher)
    guard = QuotaAlertGuard()

    assert await guard.notify_once("Ежедневный дайджест") is True
    assert await guard.notify_once("Ежедневный дайджест") is False
    guard.mark_recovered()
    assert await guard.notify_once("Ежедневный дайджест") is True
    assert len(sent) == 2
