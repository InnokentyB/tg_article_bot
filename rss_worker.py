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
import json
import logging
import os
from urllib.parse import urljoin, urlparse
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

        supported_source_types = {
            "rss",
            "video_rss",
            "podcast_rss",
            "modernanalyst_html",
            "mindtheproduct_json",
            "ireb_html",
            "docs_collection",
        }
        supported_sources = [
            source for source in sources if source.get("source_type") in supported_source_types
        ]
        skipped = len(sources) - len(supported_sources)
        if skipped:
            logger.info(
                "[RSSWorker] Skipping %d due unsupported source(s).",
                skipped,
            )
        sources = supported_sources
        if not sources:
            logger.debug("[RSSWorker] No supported sources due for fetch.")
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
        source_type: str = source.get("source_type") or "rss"
        feed_url: str = source.get("url", "")
        source_name: str = source.get("name", feed_url)
        language: Optional[str] = source.get("language")

        if not feed_url:
            logger.warning(
                "[RSSWorker] source_id=%d has no URL — skipping.", source_id
            )
            return

        if source_type == "modernanalyst_html":
            await self._fetch_modernanalyst_source(source)
            return
        if source_type == "mindtheproduct_json":
            await self._fetch_mindtheproduct_source(source)
            return
        if source_type == "ireb_html":
            await self._fetch_ireb_source(source)
            return
        if source_type == "docs_collection":
            await self._fetch_docs_collection_source(source)
            return
        if source_type in {"video_rss", "podcast_rss"}:
            await self._fetch_media_feed_source(source)
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
                        "source_id": source_id,
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

    async def _fetch_media_feed_source(self, source: dict) -> None:
        """Crawl an RSS/Atom feed and store entries as media links."""
        source_id: int = source["id"]
        source_type: str = source.get("source_type") or "video_rss"
        feed_url: str = source.get("url", "")
        source_name: str = source.get("name", feed_url)
        language: Optional[str] = source.get("language")

        try:
            import feedparser
        except ImportError:
            logger.error("[RSSWorker] feedparser is not installed — cannot crawl media source_id=%d.", source_id)
            return

        try:
            parsed_feed = feedparser.parse(feed_url)
        except Exception as exc:
            logger.error("[RSSWorker] media source_id=%d failed to parse feed %s: %s", source_id, feed_url, exc)
            return

        if parsed_feed.bozo and not parsed_feed.entries:
            logger.warning(
                "[RSSWorker] media source_id=%d feed is malformed and has no entries: %s",
                source_id,
                parsed_feed.bozo_exception,
            )
            return

        media_type = "podcast" if source_type == "podcast_rss" else "video"
        created = duplicates = errors = 0
        for entry in parsed_feed.entries[: self._fetch_limit]:
            media_url = self._media_entry_url(entry)
            if not media_url:
                errors += 1
                continue

            metadata = {
                "ingestion_method": "media_rss_worker",
                "feed_url": feed_url,
                "feed_title": parsed_feed.feed.get("title"),
                "entry_id": entry.get("id") or entry.get("guid"),
                "entry_link": entry.get("link"),
                "source_name": source_name,
            }
            try:
                media_item_id = await self._db.upsert_media_item(
                    url=media_url,
                    title=entry.get("title"),
                    description=self._strip_html(entry.get("summary") or entry.get("description") or ""),
                    source_id=source_id,
                    media_type=media_type,
                    platform=self._platform(media_url),
                    language=language,
                    published_at=self._entry_published_at(entry),
                    duration_seconds=self._entry_duration_seconds(entry),
                    metadata=metadata,
                )
                if media_item_id:
                    created += 1
            except Exception as exc:
                logger.error(
                    "[RSSWorker] media source_id=%d entry %s failed: %s",
                    source_id,
                    media_url,
                    exc,
                )
                errors += 1

        try:
            await self._db.update_source_last_fetched(source_id)
        except Exception as exc:
            logger.error("[RSSWorker] media source_id=%d failed to update last_fetched_at: %s", source_id, exc)

        logger.info(
            "[RSSWorker] media source_id=%d done: stored=%d duplicates_or_updates=%d errors=%d",
            source_id,
            created,
            duplicates,
            errors,
        )

    async def _fetch_modernanalyst_source(self, source: dict) -> None:
        """Crawl Modern Analyst article listings that do not expose stable RSS XML."""
        source_id: int = source["id"]
        listing_url: str = source.get("url", "")
        source_name: str = source.get("name", listing_url)
        language: Optional[str] = source.get("language")

        logger.info(
            "[RSSWorker] Crawling Modern Analyst source_id=%d name=%r url=%s",
            source_id,
            source_name,
            listing_url,
        )

        try:
            html = await asyncio.get_running_loop().run_in_executor(
                None,
                self._fetch_html,
                listing_url,
            )
            entries = self._parse_modernanalyst_articles(html, listing_url)[: self._fetch_limit]
        except Exception as exc:
            logger.error(
                "[RSSWorker] source_id=%d failed to parse Modern Analyst listing %s: %s",
                source_id,
                listing_url,
                exc,
            )
            return

        created = duplicates = errors = 0
        for entry in entries:
            try:
                result = await self._ingest_fn(
                    {
                        "url": entry["link"],
                        "source_id": source_id,
                        "title": entry.get("title"),
                        "source_name": source_name,
                        "source_type": "web",
                        "language": language,
                        "summary": entry.get("summary"),
                        "fallback_text": entry.get("fallback_text"),
                        "ingestion_method": "modernanalyst_html_worker",
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
                    "[RSSWorker] source_id=%d Modern Analyst entry %s ingestion failed: %s",
                    source_id,
                    entry.get("link"),
                    exc,
                )
                errors += 1

        try:
            await self._db.update_source_last_fetched(source_id)
        except Exception as exc:
            logger.error(
                "[RSSWorker] source_id=%d failed to update last_fetched_at: %s",
                source_id,
                exc,
            )

        logger.info(
            "[RSSWorker] Modern Analyst source_id=%d done: created=%d duplicates=%d errors=%d",
            source_id,
            created,
            duplicates,
            errors,
        )

    async def _fetch_mindtheproduct_source(self, source: dict) -> None:
        """Crawl Mind the Product's JSON feed endpoint."""
        source_id: int = source["id"]
        feed_url: str = source.get("url", "")
        source_name: str = source.get("name", feed_url)
        language: Optional[str] = source.get("language")

        logger.info(
            "[RSSWorker] Crawling Mind the Product source_id=%d name=%r url=%s",
            source_id,
            source_name,
            feed_url,
        )

        try:
            payload = await asyncio.get_running_loop().run_in_executor(
                None,
                self._fetch_json,
                feed_url,
            )
            entries = self._parse_mindtheproduct_items(payload)[: self._fetch_limit]
        except Exception as exc:
            logger.error(
                "[RSSWorker] source_id=%d failed to parse Mind the Product feed %s: %s",
                source_id,
                feed_url,
                exc,
            )
            return

        await self._ingest_entries(source_id, source_name, language, entries, "mindtheproduct_json_worker")

    async def _fetch_ireb_source(self, source: dict) -> None:
        """Crawl Requirements Engineering Magazine listings."""
        source_id: int = source["id"]
        listing_url: str = source.get("url", "")
        source_name: str = source.get("name", listing_url)
        language: Optional[str] = source.get("language")

        logger.info(
            "[RSSWorker] Crawling IREB source_id=%d name=%r url=%s",
            source_id,
            source_name,
            listing_url,
        )

        try:
            html = await asyncio.get_running_loop().run_in_executor(
                None,
                self._fetch_html,
                listing_url,
            )
            entries = self._parse_ireb_articles(html, listing_url)[: self._fetch_limit]
        except Exception as exc:
            logger.error(
                "[RSSWorker] source_id=%d failed to parse IREB listing %s: %s",
                source_id,
                listing_url,
                exc,
            )
            return

        await self._ingest_entries(source_id, source_name, language, entries, "ireb_html_worker")

    async def _fetch_docs_collection_source(self, source: dict) -> None:
        """Crawl a fixed list of official documentation pages from source metadata."""
        source_id: int = source["id"]
        source_name: str = source.get("name", "")
        language: Optional[str] = source.get("language")
        metadata = self._metadata_dict(source.get("metadata"))
        entry_urls = metadata.get("entry_urls") or []

        entries = [
            {
                "title": item.get("title") or source_name,
                "link": item.get("url"),
                "summary": item.get("summary"),
                "fallback_text": "\n\n".join(
                    part for part in (item.get("title"), item.get("summary")) if part
                ),
            }
            for item in entry_urls
            if isinstance(item, dict) and item.get("url")
        ]
        if not entries and source.get("url"):
            entries = [
                {
                    "title": source_name,
                    "link": source["url"],
                    "summary": metadata.get("editorial_role"),
                    "fallback_text": "\n\n".join(
                        part for part in (source_name, metadata.get("editorial_role")) if part
                    ),
                }
            ]

        entries = entries[: self._fetch_limit]
        logger.info(
            "[RSSWorker] Crawling docs collection source_id=%d name=%r entries=%d",
            source_id,
            source_name,
            len(entries),
        )
        await self._ingest_entries(source_id, source_name, language, entries, "docs_collection_worker")

    @staticmethod
    def _metadata_dict(metadata) -> dict:
        if isinstance(metadata, dict):
            return metadata
        if isinstance(metadata, str):
            try:
                parsed = json.loads(metadata)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    async def _ingest_entries(
        self,
        source_id: int,
        source_name: str,
        language: Optional[str],
        entries: list[dict],
        ingestion_method: str,
    ) -> None:
        created = duplicates = errors = 0
        for entry in entries:
            try:
                result = await self._ingest_fn(
                    {
                        "url": entry["link"],
                        "source_id": source_id,
                        "title": entry.get("title"),
                        "source_name": source_name,
                        "source_type": "web",
                        "language": language,
                        "summary": entry.get("summary"),
                        "fallback_text": entry.get("fallback_text"),
                        "ingestion_method": ingestion_method,
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
                    entry.get("link"),
                    exc,
                )
                errors += 1

        try:
            await self._db.update_source_last_fetched(source_id)
        except Exception as exc:
            logger.error(
                "[RSSWorker] source_id=%d failed to update last_fetched_at: %s",
                source_id,
                exc,
            )

        logger.info(
            "[RSSWorker] source_id=%d done: created=%d duplicates=%d errors=%d method=%s",
            source_id,
            created,
            duplicates,
            errors,
            ingestion_method,
        )

    @staticmethod
    def _fetch_html(url: str) -> str:
        import requests

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; TGArticlesBot/1.0; "
                    "+https://github.com/InnokentyB/tg_article_bot)"
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        return response.text

    @staticmethod
    def _fetch_json(url: str) -> dict:
        import requests

        response = requests.get(
            url,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; TGArticlesBot/1.0; "
                    "+https://github.com/InnokentyB/tg_article_bot)"
                ),
                "Accept": "application/json,text/plain,*/*",
            },
        )
        response.raise_for_status()
        return response.json()

    @classmethod
    def _parse_mindtheproduct_items(cls, payload: dict) -> list[dict]:
        """Extract article candidates from Mind the Product's JSON feed."""
        entries: list[dict] = []
        seen_urls: set[str] = set()

        for item in payload.get("results", []) or []:
            data = item.get("data") or {}
            title = cls._strip_html(data.get("title"))
            link = (data.get("url") or "").strip()
            if not title or not link or link in seen_urls:
                continue
            parsed = urlparse(link)
            if parsed.netloc.lower() not in {"www.mindtheproduct.com", "mindtheproduct.com"}:
                continue

            authors = cls._parse_mindtheproduct_authors(data)
            summary = ", ".join(authors) if authors else None
            entries.append(
                {
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "fallback_text": "\n\n".join(part for part in (title, summary) if part),
                }
            )
            seen_urls.add(link)

        return entries

    @staticmethod
    def _parse_mindtheproduct_authors(data: dict) -> list[str]:
        authors: list[str] = []
        for item in data.get("authors", []) or []:
            display_name = (
                ((item.get("author") or {}).get("value") or {})
                .get("data", {})
                .get("displayName")
            )
            if display_name:
                authors.append(str(display_name).strip())
        return [author for author in authors if author]

    @classmethod
    def _parse_ireb_articles(cls, html: str, listing_url: str) -> list[dict]:
        """Extract article candidates from Requirements Engineering Magazine HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html or "", "html.parser")
        entries_by_url: dict[str, dict] = {}

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            absolute_url = urljoin(listing_url, href)
            parsed = urlparse(absolute_url)
            if parsed.netloc.lower() != "re-magazine.ireb.org":
                continue
            if not parsed.path.startswith("/articles/"):
                continue
            if any(marker in parsed.path for marker in ("/view:", "/tags:", "/author:", "/sort:")):
                continue

            title = cls._strip_html(anchor.get_text(" ", strip=True))
            if not title or title.lower() == "read article":
                title = cls._find_ireb_article_title(anchor)
            if not title or absolute_url in entries_by_url:
                continue

            summary = cls._find_nearby_summary(anchor)
            entries_by_url[absolute_url] = {
                "title": title,
                "link": absolute_url,
                "summary": summary,
                "fallback_text": "\n\n".join(part for part in (title, summary) if part),
            }

        return list(entries_by_url.values())

    @classmethod
    def _find_ireb_article_title(cls, anchor) -> Optional[str]:
        card = anchor.find_parent(["article", "li", "div"])
        if not card:
            return None
        for selector in ("h1", "h2", "h3", ".h1", ".h2", ".h3"):
            element = card.select_one(selector)
            if element:
                title = cls._strip_html(element.get_text(" ", strip=True))
                if title and title.lower() != "read article":
                    return title
        return None

    @classmethod
    def _parse_modernanalyst_articles(cls, html: str, listing_url: str) -> list[dict]:
        """Extract article candidates from Modern Analyst article listing HTML."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html or "", "html.parser")
        entries_by_url: dict[str, dict] = {}

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            title = cls._strip_html(anchor.get_text(" ", strip=True))
            if not title:
                continue

            absolute_url = urljoin(listing_url, href)
            parsed = urlparse(absolute_url)
            if parsed.netloc.lower() not in {"www.modernanalyst.com", "modernanalyst.com"}:
                continue
            is_supported_modernanalyst_path = (
                "/Resources/Articles/" in parsed.path
                or "/Resources/News/" in parsed.path
            )
            if not is_supported_modernanalyst_path or "/ID/" not in parsed.path:
                continue
            if absolute_url in entries_by_url:
                continue

            summary = cls._find_nearby_summary(anchor)
            entries_by_url[absolute_url] = {
                "title": title,
                "link": absolute_url,
                "summary": summary,
                "fallback_text": "\n\n".join(part for part in (title, summary) if part),
            }

        return list(entries_by_url.values())

    @staticmethod
    def _find_nearby_summary(anchor) -> Optional[str]:
        container = anchor
        for _ in range(4):
            container = container.parent
            if container is None:
                return None
            text = RSSWorker._strip_html(container.get_text(" ", strip=True))
            if not text:
                continue
            title = RSSWorker._strip_html(anchor.get_text(" ", strip=True)) or ""
            if len(text) > len(title) + 40:
                summary = text.replace(title, "", 1).strip()
                return summary[:600] if summary else None
        return None

    @staticmethod
    def _media_entry_url(entry: dict) -> Optional[str]:
        for enclosure in entry.get("enclosures", []) or []:
            href = enclosure.get("href") or enclosure.get("url")
            if href:
                return href

        links = entry.get("links", []) or []
        for link in links:
            href = link.get("href")
            mime_type = str(link.get("type") or "").lower()
            rel = str(link.get("rel") or "").lower()
            if href and (mime_type.startswith(("audio/", "video/")) or rel == "enclosure"):
                return href

        return entry.get("link")

    @staticmethod
    def _entry_published_at(entry: dict):
        published = entry.get("published") or entry.get("updated")
        if not published:
            return None
        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(published)
        except Exception:
            return None

    @staticmethod
    def _entry_duration_seconds(entry: dict) -> Optional[int]:
        raw_duration = (
            entry.get("itunes_duration")
            or entry.get("duration")
            or entry.get("media_duration")
        )
        if raw_duration is None:
            return None
        text = str(raw_duration).strip()
        if text.isdigit():
            return int(text)
        parts = text.split(":")
        if not all(part.isdigit() for part in parts):
            return None
        seconds = 0
        for part in parts:
            seconds = seconds * 60 + int(part)
        return seconds

    @staticmethod
    def _platform(url: str) -> str:
        host = urlparse(url).netloc.lower()
        if "youtube.com" in host or "youtu.be" in host:
            return "youtube"
        if "spotify.com" in host:
            return "spotify"
        if "apple.com" in host:
            return "apple_podcasts"
        return host[:80] or "media"

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
