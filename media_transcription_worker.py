"""Background processing for video and podcast transcription links."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Awaitable, Callable, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

CategorizeFn = Callable[[str], Awaitable[list[str]]]
EmbedFn = Callable[[int, list], Awaitable[dict]]


class MediaTranscriptionProcessor:
    """Submits media URLs to TranscribeIt and stores completed transcripts."""

    def __init__(
        self,
        db_manager,
        *,
        categorize_fn: Optional[CategorizeFn] = None,
        embed_fn: Optional[EmbedFn] = None,
    ) -> None:
        self._db = db_manager
        self._categorize_fn = categorize_fn
        self._embed_fn = embed_fn

    async def process_due_items(self, *, limit: int = 5) -> dict:
        items = await self._db.get_due_media_items(limit=limit)
        result = {"due": len(items), "submitted": 0, "completed": 0, "failed": 0, "processing": 0}

        for item in items:
            try:
                status = item.get("status")
                if status in ("discovered", "queued") or not item.get("transaction_id"):
                    submitted = await self._submit_item(item)
                    result["submitted" if submitted else "failed"] += 1
                    continue

                completed = await self._poll_item(item)
                if completed == "completed":
                    result["completed"] += 1
                elif completed == "processing":
                    result["processing"] += 1
                else:
                    result["failed"] += 1
            except Exception as exc:
                logger.exception("[MediaTranscriptionProcessor] item_id=%s failed: %s", item.get("id"), exc)
                await self._db.mark_media_failed(item["id"], str(exc))
                result["failed"] += 1

        return result

    async def _submit_item(self, item: dict) -> bool:
        from transcribeit_client import TranscribeItClient

        client = TranscribeItClient()
        if not client.is_configured():
            await self._db.mark_media_failed(item["id"], "TRANSCRIBEIT_API_KEY is not configured")
            return False

        transaction_id = await client.upload_url(
            item["url"],
            language=item.get("language") or "auto",
        )
        if not transaction_id:
            await self._db.mark_media_failed(item["id"], "TranscribeIt did not accept media URL")
            return False

        await self._db.mark_media_submitted(item["id"], transaction_id=transaction_id)
        logger.info(
            "[MediaTranscriptionProcessor] Submitted media item_id=%s transaction_id=%s",
            item["id"],
            transaction_id,
        )
        return True

    async def _poll_item(self, item: dict) -> str:
        from transcribeit_client import TranscribeItClient

        client = TranscribeItClient()
        response = await client.get_transcription(item["transaction_id"])
        if not response:
            await self._db.mark_media_processing(
                item["id"],
                next_check_minutes=int(os.getenv("MEDIA_TRANSCRIPTION_RETRY_MINUTES", "15")),
            )
            return "processing"

        status = str(response.get("status") or "").lower()
        if status in ("queued", "processing", "in_progress"):
            await self._db.mark_media_processing(
                item["id"],
                next_check_minutes=int(os.getenv("MEDIA_TRANSCRIPTION_POLL_MINUTES", "10")),
                metadata={"last_transcribeit_status": status},
            )
            return "processing"

        if status == "failed":
            await self._db.mark_media_failed(item["id"], response.get("error") or "TranscribeIt failed")
            return "failed"

        if status not in ("completed", "done", "success"):
            await self._db.mark_media_processing(
                item["id"],
                next_check_minutes=int(os.getenv("MEDIA_TRANSCRIPTION_POLL_MINUTES", "10")),
                metadata={"last_transcribeit_status": status or "unknown"},
            )
            return "processing"

        transcript = self._extract_transcript(response)
        if len(transcript) < int(os.getenv("MEDIA_TRANSCRIPTION_MIN_TEXT_LENGTH", "900")):
            await self._db.mark_media_failed(item["id"], "Completed transcription text is too short")
            return "failed"

        article_id = await self._store_transcript_article(item, transcript, response)
        await self._db.mark_media_transcribed(
            item["id"],
            article_id=article_id,
            transcript_text=transcript,
            metadata={"transcribeit_status": status},
        )
        logger.info(
            "[MediaTranscriptionProcessor] Completed media item_id=%s article_id=%s",
            item["id"],
            article_id,
        )
        return "completed"

    async def _store_transcript_article(self, item: dict, transcript: str, response: dict) -> int:
        from article_chunker import ArticleChunker

        title = item.get("title") or f"Транскрипт: {self._hostname(item.get('url') or '')}"
        summary = self._summary(transcript)
        categories = await self._categorize(transcript)
        language = item.get("language")
        if language == "auto":
            language = None

        article_id, fingerprint = await self._db.save_article(
            title=title,
            text=transcript,
            summary=summary,
            source=item.get("platform") or self._hostname(item.get("url") or ""),
            author=None,
            original_link=item["url"],
            categories_user=categories,
            language=language,
        )

        if article_id is None:
            duplicate = await self._db.get_article_by_fingerprint(fingerprint)
            return int(duplicate["id"]) if duplicate else 0

        await self._db.update_article_intelligence_fields(
            article_id=article_id,
            source_id=item.get("source_id"),
            canonical_url=item["url"],
            published_at=item.get("published_at"),
            extracted_at=datetime.now(),
            content_type=item.get("media_type") or "video",
            metadata={
                "ingestion_method": "media_transcription",
                "media_item_id": item["id"],
                "media_type": item.get("media_type"),
                "transcribeit_transaction_id": item.get("transaction_id"),
                "transcribeit_metadata": self._compact_transcribeit_metadata(response),
            },
        )
        await self._db.register_article_source_tracking(
            article_id=article_id,
            source_url=item["url"],
            source_type=item.get("platform"),
            metadata={"registered_by": "media_transcription"},
        )
        await self._db.update_article_categories(article_id, categories)

        chunks = ArticleChunker().chunk_text(transcript)
        inserted_chunks = await self._db.replace_article_chunks(article_id, chunks)
        if self._embed_fn:
            await self._embed_fn(article_id, inserted_chunks)
        return article_id

    async def _categorize(self, text: str) -> list[str]:
        if not self._categorize_fn:
            return []
        return await self._categorize_fn(text)

    @staticmethod
    def _extract_transcript(response: dict) -> str:
        text = response.get("text") or response.get("transcript") or response.get("transcription") or ""
        if text:
            return " ".join(str(text).split())
        segments = response.get("segments") or []
        if isinstance(segments, list):
            return " ".join(
                str(segment.get("text") or "").strip()
                for segment in segments
                if isinstance(segment, dict) and segment.get("text")
            ).strip()
        return ""

    @staticmethod
    def _summary(text: str, limit: int = 500) -> str:
        compact = " ".join(text.split())
        return compact[:limit].rstrip()

    @staticmethod
    def _hostname(url: str) -> str:
        return urlparse(url).netloc or url

    @staticmethod
    def _compact_transcribeit_metadata(response: dict) -> dict:
        return {
            key: response.get(key)
            for key in ("id", "transaction_id", "status", "language", "duration")
            if response.get(key) is not None
        }


class MediaTranscriptionWorker:
    """Polling loop for media transcription."""

    def __init__(
        self,
        db_manager,
        *,
        categorize_fn: Optional[CategorizeFn] = None,
        embed_fn: Optional[EmbedFn] = None,
    ) -> None:
        self._enabled = os.getenv("MEDIA_TRANSCRIPTION_ENABLED", "false").lower() == "true"
        self._poll_seconds = int(os.getenv("MEDIA_TRANSCRIPTION_WORKER_POLL_SECONDS", "120"))
        self._limit = int(os.getenv("MEDIA_TRANSCRIPTION_WORKER_BATCH_SIZE", "5"))
        self._task: Optional[asyncio.Task] = None
        self._processor = MediaTranscriptionProcessor(
            db_manager,
            categorize_fn=categorize_fn,
            embed_fn=embed_fn,
        )

    def start(self) -> None:
        if not self._enabled:
            logger.info("[MediaTranscriptionWorker] Disabled via MEDIA_TRANSCRIPTION_ENABLED=false.")
            return
        if self._task and not self._task.done():
            logger.warning("[MediaTranscriptionWorker] Already running.")
            return
        self._task = asyncio.create_task(self._loop(), name="media_transcription_worker")
        logger.info("[MediaTranscriptionWorker] Started. poll_seconds=%s", self._poll_seconds)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[MediaTranscriptionWorker] Cancellation requested.")

    async def _loop(self) -> None:
        while True:
            try:
                result = await self._processor.process_due_items(limit=self._limit)
                if result["due"]:
                    logger.info("[MediaTranscriptionWorker] Run result: %s", result)
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[MediaTranscriptionWorker] Loop cancelled.")
                break
            except Exception as exc:
                logger.exception("[MediaTranscriptionWorker] Unexpected error: %s", exc)
                await asyncio.sleep(self._poll_seconds)
