"""
Background worker for external source engagement metrics.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class SourceMetricsWorker:
    """Periodically refresh comments/likes/views for tracked article sources."""

    def __init__(self, db_manager) -> None:
        self._db = db_manager
        self._enabled = os.getenv("SOURCE_METRICS_ENABLED", "false").lower() == "true"
        self._poll_seconds = int(os.getenv("SOURCE_METRICS_POLL_SECONDS", "3600"))
        self._limit = int(os.getenv("SOURCE_METRICS_LIMIT", "50"))
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if not self._enabled:
            logger.info("[SourceMetricsWorker] Disabled via SOURCE_METRICS_ENABLED=false.")
            return
        if self._task and not self._task.done():
            logger.warning("[SourceMetricsWorker] Already running.")
            return
        self._task = asyncio.create_task(self._loop(), name="source_metrics_worker")
        logger.info("[SourceMetricsWorker] Started. poll_seconds=%d limit=%d", self._poll_seconds, self._limit)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[SourceMetricsWorker] Cancellation requested.")

    async def _loop(self) -> None:
        while True:
            try:
                result = await self.run_once()
                logger.info("[SourceMetricsWorker] Run result: %s", result)
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[SourceMetricsWorker] Loop cancelled.")
                break
            except Exception as exc:
                logger.exception("[SourceMetricsWorker] Unexpected error: %s", exc)
                await asyncio.sleep(self._poll_seconds)

    async def run_once(self) -> dict:
        from external_source_tracker import ExternalSourceTracker

        tracker = ExternalSourceTracker(self._db)
        await tracker.initialize()
        try:
            return await tracker.update_all_tracked_articles(limit=self._limit)
        finally:
            await tracker.close()
