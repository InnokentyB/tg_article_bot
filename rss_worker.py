"""
RSS Worker — background asyncio task for automated source crawling.

Runs inside the API server process, started during the FastAPI lifespan.
Periodically queries active sources that are due for a crawl and ingests
each RSS entry via the shared ingestion logic.

Configuration (environment variables):
    WORKER_ENABLED       – "true" (default) / "false" to disable the worker.
    WORKER_POLL_SECONDS  – How often the worker checks for due sources (default: 60).
    WORKER_FETCH_LIMIT   – Max RSS entries to ingest per source per crawl (default: 20).
"""
import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class RSSWorker:
    """Background RSS crawler that ingests sources on their configured schedule."""

    def __init__(self, db_manager, ingest_fn) -> None:
        """Initialize the worker.

        Args:
            db_manager: A live DatabaseManager instance shared with the API.
            ingest_fn:  The ``ingest_url_payload`` coroutine from api_server.
                        Called for each RSS entry to reuse all existing
                        extraction, dedup and embedding logic.
        """
        self._db = db_manager
        self._ingest_fn = ingest_fn
        self._task: Optional[asyncio.Task] = None

        self._enabled = os.getenv("WORKER_ENABLED", "true").lower() == "true"
        self._poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "60"))
        self._fetch_limit = int(os.getenv("WORKER_FETCH_LIMIT", "20"))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Schedule the worker loop as an asyncio background task."""
        if not self._enabled:
            logger.info("[RSSWorker] Disabled via WORKER_ENABLED=false — skipping start.")
            return
        if self._task and not self._task.done():
            logger.warning("[RSSWorker] Already running, ignoring duplicate start().")
            return

        self._task = asyncio.create_task(self._loop(), name="rss_worker")
        logger.info(
            "[RSSWorker] Started. poll_interval=%ds fetch_limit=%d",
            self._poll_seconds,
            self._fetch_limit,
        )

    def stop(self) -> None:
        """Cancel the background task (called during API shutdown)."""
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[RSSWorker] Cancellation requested.")

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        """Main worker loop — sleeps between polling cycles."""
        logger.info("[RSSWorker] Loop started.")
        while True:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                logger.info("[RSSWorker] Loop cancelled — shutting down gracefully.")
                break
            except Exception as exc:
                logger.exception("[RSSWorker] Unexpected error in poll cycle: %s", exc)

            try:
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[RSSWorker] Sleep interrupted — shutting down gracefully.")
                break

    async def _poll_once(self) -> None:
        """Find sources due for a crawl and fetch each of them."""
        try:
            sources = await self._db.get_sources(active_only=True, due_for_fetch=True)
        except Exception as exc:
            logger.error("[RSSWorker] Failed to fetch due sources: %s", exc)
            return

        if not sources:
            logger.debug("[RSSWorker] No sources due for fetch.")
            return

        rss_sources = [source for source in sources if source.get("source_type") == "rss"]
        skipped = len(sources) - len(rss_sources)
        if skipped:
            logger.info(
                "[RSSWorker] Skipping %d due non-RSS source(s).",
                skipped,
            )
        sources = rss_sources
        if not sources:
            logger.debug("[RSSWorker] No RSS sources due for fetch.")
            return

        logger.info("[RSSWorker] %d source(s) due for crawl.", len(sources))
        for source in sources:
            await self._fetch_source(source)

    async def _fetch_source(self, source: dict) -> None:
        """Crawl a single RSS source and ingest new entries.

        Args:
            source: A row dict from ``get_sources()``.
        """
        source_id: int = source["id"]
        feed_url: str = source.get("url", "")
        source_name: str = source.get("name", feed_url)
        language: Optional[str] = source.get("language")

        if not feed_url:
            logger.warning(
                "[RSSWorker] source_id=%d has no URL — skipping.", source_id
            )
            return

        logger.info(
            "[RSSWorker] Crawling source_id=%d name=%r url=%s",
            source_id,
            source_name,
            feed_url,
        )

        try:
            import feedparser
        except ImportError:
            logger.error(
                "[RSSWorker] feedparser is not installed — cannot crawl source_id=%d.",
                source_id,
            )
            return

        try:
            parsed_feed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.error(
                "[RSSWorker] source_id=%d failed to parse feed %s: %s",
                source_id,
                feed_url,
                exc,
            )
            return

        if parsed_feed.bozo and not parsed_feed.entries:
            logger.warning(
                "[RSSWorker] source_id=%d feed is malformed and has no entries: %s",
                source_id,
                parsed_feed.bozo_exception,
            )
            return

        entries = parsed_feed.entries[: self._fetch_limit]
        created = duplicates = errors = 0

        for entry in entries:
            entry_url = entry.get("link")
            if not entry_url:
                errors += 1
                continue

            # Build fallback text from RSS entry fields (same logic as /ingest/rss).
            fallback_parts = [
                entry.get("title"),
                entry.get("summary"),
                entry.get("description"),
            ]
            for content_item in entry.get("content", []) or []:
                fallback_parts.append(content_item.get("value"))

            fallback_text = "\n\n".join(
                part
                for part in (self._strip_html(p) for p in fallback_parts if p)
                if part
            )

            try:
                result = await self._ingest_fn(
                    {
                        "url": entry_url,
                        "title": entry.get("title"),
                        "source_name": source_name,
                        "source_type": "rss_entry",
                        "language": language,
                        "summary": entry.get("summary"),
                        "fallback_text": fallback_text,
                        "ingestion_method": "rss_worker",
                    }
                )
                status = result.get("status", "unknown")
                if status == "created":
                    created += 1
                elif status == "duplicate":
                    duplicates += 1
                else:
                    errors += 1
            except Exception as exc:
                logger.error(
                    "[RSSWorker] source_id=%d entry %s ingestion failed: %s",
                    source_id,
                    entry_url,
                    exc,
                )
                errors += 1

        # Mark source as crawled regardless of individual entry errors.
        try:
            await self._db.update_source_last_fetched(source_id)
        except Exception as exc:
            logger.error(
                "[RSSWorker] source_id=%d failed to update last_fetched_at: %s",
                source_id,
                exc,
            )

        logger.info(
            "[RSSWorker] source_id=%d done: created=%d duplicates=%d errors=%d",
            source_id,
            created,
            duplicates,
            errors,
        )

    @staticmethod
    def _strip_html(text: str) -> Optional[str]:
        """Remove HTML tags from a string (lightweight, no dependencies)."""
        import re
        import html as html_module

        if not text:
            return None
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = html_module.unescape(clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean or None
