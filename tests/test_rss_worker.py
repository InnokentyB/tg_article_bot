from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rss_worker import RSSWorker


async def _unused_ingest_fn(payload: dict) -> dict:
    return {"status": "created", "payload": payload}


def test_rss_worker_can_be_disabled_without_starting_task(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "false")

    worker = RSSWorker(db_manager=object(), ingest_fn=_unused_ingest_fn)
    worker.start()

    assert worker._task is None


def test_rss_worker_start_creates_background_task(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("WORKER_POLL_SECONDS", "3600")

    async def run() -> None:
        worker = RSSWorker(db_manager=object(), ingest_fn=_unused_ingest_fn)
        worker.start()
        try:
            assert worker._task is not None
            assert not worker._task.done()
        finally:
            worker.stop()
            await asyncio.sleep(0)

    asyncio.run(run())
