from __future__ import annotations

import httpx
import pytest

import api_server
from publisher import TelegramPublisher


@pytest.fixture(autouse=True)
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_KEY", "test-api-key")


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-api-key"}


@pytest.mark.asyncio
async def test_telegram_validate_returns_configuration_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_validate(self: TelegramPublisher) -> tuple[bool, str]:
        return True, "Configuration valid. Bot: @readerbot, Chat: Channel"

    monkeypatch.setattr(TelegramPublisher, "validate_configuration", fake_validate)

    transport = httpx.ASGITransport(app=api_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/telegram/validate", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "configured": True,
        "message": "Configuration valid. Bot: @readerbot, Chat: Channel",
    }


@pytest.mark.asyncio
async def test_telegram_test_sends_message_after_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_validate(self: TelegramPublisher) -> tuple[bool, str]:
        calls.append("validate")
        return True, "ok"

    def fake_send(self: TelegramPublisher) -> bool:
        calls.append("send")
        return True

    monkeypatch.setattr(TelegramPublisher, "validate_configuration", fake_validate)
    monkeypatch.setattr(TelegramPublisher, "send_test_message", fake_send)

    transport = httpx.ASGITransport(app=api_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/telegram/test", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert calls == ["validate", "send"]


@pytest.mark.asyncio
async def test_telegram_test_rejects_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_validate(self: TelegramPublisher) -> tuple[bool, str]:
        return False, "Cannot access specified chat"

    monkeypatch.setattr(TelegramPublisher, "validate_configuration", fake_validate)

    transport = httpx.ASGITransport(app=api_server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/telegram/test", headers=auth_headers())

    assert response.status_code == 503
    assert response.json()["detail"] == "Cannot access specified chat"
