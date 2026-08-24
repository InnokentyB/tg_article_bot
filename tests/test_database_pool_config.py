from unittest.mock import AsyncMock, patch

import pytest

from database import DatabaseManager


@pytest.mark.asyncio
async def test_database_pool_uses_memory_conscious_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.delenv("DB_POOL_MIN_SIZE", raising=False)
    monkeypatch.delenv("DB_POOL_MAX_SIZE", raising=False)
    pool = object()

    with patch("database.asyncpg.create_pool", new=AsyncMock(return_value=pool)) as create_pool:
        manager = DatabaseManager()
        await manager.initialize()

    assert manager.pool is pool
    create_pool.assert_awaited_once_with(
        "postgresql://example",
        min_size=1,
        max_size=5,
    )


def test_database_pool_never_sets_max_below_min(monkeypatch):
    monkeypatch.setenv("DB_POOL_MIN_SIZE", "4")
    monkeypatch.setenv("DB_POOL_MAX_SIZE", "2")

    manager = DatabaseManager()

    assert manager.pool_min_size == 4
    assert manager.pool_max_size == 4
