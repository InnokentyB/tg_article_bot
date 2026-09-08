"""Personal signal inbox for useful unpublished articles."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional

from daily_digest_job import DailyDigestWorker

logger = logging.getLogger(__name__)


DEFAULT_PERSONAL_TOPICS = (
    "ai agents, rag, knowledge base, requirements engineering, business analysis, "
    "product management, engineering practice, telegram, content automation, "
    "summarization, transcription, video, podcast, cloudflare, railway, "
    "ии-агенты, ии-агентов, агентные системы, нейросети, генеративный интеллект, "
    "требования, бизнес-анализ, продуктовая аналитика, транскрибация, саммаризация"
)


@dataclass
class PersonalSignalsConfig:
    period_hours: int = 24
    max_articles: int = 7
    min_score: float = 1.5
    topics: str = DEFAULT_PERSONAL_TOPICS
    language: Optional[str] = None
    publish_enabled: bool = False
    telegram_chat_id: Optional[str] = None
    include_reviewed: bool = False

    @classmethod
    def from_env(cls) -> "PersonalSignalsConfig":
        return cls(
            period_hours=max(1, int(os.getenv("PERSONAL_SIGNALS_PERIOD_HOURS", "24"))),
            max_articles=max(1, int(os.getenv("PERSONAL_SIGNALS_MAX_ARTICLES", "7"))),
            min_score=float(os.getenv("PERSONAL_SIGNALS_MIN_SCORE", "1.5")),
            topics=os.getenv("PERSONAL_SIGNALS_TOPICS", DEFAULT_PERSONAL_TOPICS),
            language=os.getenv("PERSONAL_SIGNALS_LANGUAGE") or None,
            publish_enabled=os.getenv("PERSONAL_SIGNALS_PUBLISH_ENABLED", "false").lower() == "true",
            telegram_chat_id=os.getenv("PERSONAL_SIGNALS_TELEGRAM_CHAT_ID") or None,
            include_reviewed=os.getenv("PERSONAL_SIGNALS_INCLUDE_REVIEWED", "false").lower() == "true",
        )


class PersonalSignalsJob:
    """Select project-relevant materials for a private inbox."""

    def __init__(self, db_manager, config: Optional[PersonalSignalsConfig] = None) -> None:
        self._db = db_manager
        self._config = config or PersonalSignalsConfig.from_env()

    async def run(
        self,
        *,
        publish: Optional[bool] = None,
        dry_run: bool = True,
        now: Optional[datetime] = None,
    ) -> dict[str, Any]:
        if not self._db or not self._db.pool:
            raise RuntimeError("Database pool not initialized")

        now = now or datetime.now(timezone.utc)
        publish = self._config.publish_enabled if publish is None else publish
        candidates = await self._load_candidates(now)
        ranked_articles = self._rank_candidates(candidates)[: self._config.max_articles]

        if not ranked_articles:
            return {
                "status": "skipped",
                "reason": "no personal signals found",
                "period_hours": self._config.period_hours,
                "dry_run": dry_run,
            }

        message = self._build_telegram_message(now=now, ranked_articles=ranked_articles)
        review_id = None
        queued_post_id = None
        if not dry_run:
            review_id = await self._store_signals(
                now=now,
                ranked_articles=ranked_articles,
                message=message,
                publish=publish,
            )
            if publish and self._config.telegram_chat_id:
                queued_post_id = await self._db.enqueue_telegram_post(
                    review_id=review_id,
                    post_type="personal_signals",
                    message=message,
                    scheduled_at=now,
                    metadata={
                        "job": "personal_signals",
                        "target_chat_id": self._config.telegram_chat_id,
                    },
                )
                from telegram_post_worker import TelegramPostDispatcher

                await TelegramPostDispatcher(self._db).process_due_posts(limit=10)

        return {
            "status": "completed",
            "period_hours": self._config.period_hours,
            "review_id": review_id,
            "dry_run": dry_run,
            "publish_requested": publish,
            "queued_telegram_post_id": queued_post_id,
            "signals": [self._public_article(article) for article in ranked_articles],
            "telegram_message": message,
        }

    async def _load_candidates(self, now: datetime) -> list[dict[str, Any]]:
        started_at = now - timedelta(hours=self._config.period_hours)
        query = """
            SELECT
                a.id AS article_id,
                a.title,
                a.summary,
                a.text,
                a.source,
                a.author,
                a.original_link,
                a.canonical_url,
                a.language,
                a.published_at,
                a.created_at,
                a.popularity_score,
                a.views_count,
                a.likes_count,
                a.comments_count,
                a.metadata,
                s.name AS source_name,
                s.metadata AS source_metadata,
                COUNT(DISTINCT c.id) AS chunk_count,
                COUNT(DISTINCT e.id) AS embedding_count
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN article_chunks c ON c.article_id = a.id
            LEFT JOIN article_embeddings e ON e.article_id = a.id
            WHERE COALESCE(a.published_at, a.created_at) >= $1
              AND COALESCE(a.published_at, a.created_at) <= $2
              AND COALESCE(length(a.text), 0) >= 700
        """
        params: list[Any] = [started_at, now]
        param_count = 3

        if self._config.language:
            query += f" AND a.language = ${param_count}"
            params.append(self._config.language)
            param_count += 1

        if not self._config.include_reviewed:
            query += """
              AND NOT EXISTS (
                  SELECT 1
                  FROM review_sources rs
                  JOIN reviews r ON r.id = rs.review_id
                  WHERE rs.article_id = a.id
                    AND COALESCE(r.metadata->>'job', '') IN (
                        'daily_digest',
                        'weekly_thematic_digest',
                        'personal_signals'
                    )
              )
            """

        query += """
            GROUP BY a.id, s.name, s.metadata
            ORDER BY COALESCE(a.published_at, a.created_at) DESC
            LIMIT 500
        """

        async with self._db.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

    def _rank_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ranked = []
        seen_titles: set[str] = set()
        seen_urls: set[str] = set()
        for article in candidates:
            title = (article.get("title") or "").strip()
            title_key = " ".join(title.casefold().split())
            url_key = self._canonical_url_key(article)
            if not title or title_key in seen_titles or url_key in seen_urls:
                continue
            score, reasons, matched_terms = self._score_article(article)
            if score < self._config.min_score:
                continue
            seen_titles.add(title_key)
            if url_key:
                seen_urls.add(url_key)
            article["signal_score"] = round(score, 4)
            article["score"] = article["signal_score"]
            article["selection_reason"] = "; ".join(reasons)
            article["matched_terms"] = matched_terms
            ranked.append(article)

        return sorted(
            ranked,
            key=lambda item: (
                item["signal_score"],
                item.get("embedding_count") or 0,
                item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )

    def _score_article(self, article: dict[str, Any]) -> tuple[float, list[str], list[str]]:
        text = self._signal_surface(article)
        source_metadata = self._metadata_dict(article.get("source_metadata"))
        terms = self._topic_terms(self._config.topics)
        matched_terms = [term for term in terms if self._term_matches(text, term)]

        score = 0.0
        reasons = []
        if not matched_terms:
            return 0.0, ["does not match personal project topics"], []

        score += min(4.0, 0.55 * len(matched_terms))
        reasons.append("matches personal project topics")

        text_len = len(article.get("text") or "")
        if text_len >= 4000:
            score += 1.4
            reasons.append("substantial full text")
        elif text_len >= 1800:
            score += 0.8
            reasons.append("enough text")

        embedding_count = int(article.get("embedding_count") or 0)
        if embedding_count:
            score += min(1.2, 0.2 * embedding_count)
            reasons.append("embedded")

        tier = source_metadata.get("tier")
        if tier == 1:
            score += 1.0
            reasons.append("tier-1 source")
        elif tier == 2:
            score += 0.5
            reasons.append("tier-2 source")

        popularity = float(article.get("popularity_score") or 0)
        engagement = sum(float(article.get(field) or 0) for field in ("views_count", "likes_count", "comments_count"))
        if popularity or engagement:
            score += min(1.0, popularity / 100.0 + engagement / 1000.0)
            reasons.append("has popularity signal")

        return score, reasons or ["recent relevant material"], matched_terms[:8]

    async def _store_signals(
        self,
        *,
        now: datetime,
        ranked_articles: list[dict[str, Any]],
        message: str,
        publish: bool,
    ) -> int:
        run_key = now.strftime("%Y-%m-%dT%H")
        topic_query_id = await self._db.create_topic_query(
            topic=self._config.topics,
            language=self._config.language,
            period_days=max(1, round(self._config.period_hours / 24)),
            max_sources=self._config.max_articles,
            metadata={
                "job": "personal_signals",
                "run_key": run_key,
                "period_hours": self._config.period_hours,
            },
        )
        return await self._db.create_review(
            topic_query_id=topic_query_id,
            title=f"Личные сигналы — {run_key}",
            review_markdown=message,
            telegram_draft=message,
            selected_sources=[
                {
                    "article_id": article["article_id"],
                    "rank": index,
                    "selection_reason": article.get("selection_reason"),
                    "relevance_score": article.get("signal_score"),
                    "critique_summary": ", ".join(article.get("matched_terms") or []),
                }
                for index, article in enumerate(ranked_articles, start=1)
            ],
            status="published" if publish and self._config.telegram_chat_id else "draft",
            metadata={
                "job": "personal_signals",
                "run_key": run_key,
                "period_hours": self._config.period_hours,
                "publish_requested": publish,
                "target": "telegram" if publish and self._config.telegram_chat_id else "database",
            },
        )

    def _build_telegram_message(
        self,
        *,
        now: datetime,
        ranked_articles: list[dict[str, Any]],
    ) -> str:
        lines = [
            "Личные сигналы для проектов",
            f"Окно: последние {self._config.period_hours} ч.",
            "",
        ]
        for index, article in enumerate(ranked_articles, start=1):
            title = article.get("title") or "Без названия"
            url = article.get("canonical_url") or article.get("original_link") or article.get("source") or ""
            terms = ", ".join(article.get("matched_terms") or [])
            note = self._signal_note(article)
            lines.append(f"{index}. {title}")
            if terms:
                lines.append(f"Почему: {terms}")
            if note:
                lines.append(note)
            if url:
                lines.append(url)
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _signal_note(article: dict[str, Any], limit: int = 220) -> str:
        summary = " ".join(str(article.get("summary") or "").split())
        if not summary:
            summary = " ".join(str(article.get("text") or "").split())[:500]
        if not summary:
            return ""
        if len(summary) <= limit:
            return summary
        return summary[: limit - 1].rstrip() + "…"

    @staticmethod
    def _topic_terms(topic: str) -> list[str]:
        raw_terms = re.split(r"[,;\n]+", topic)
        terms = []
        for raw_term in raw_terms:
            term = " ".join(raw_term.strip().casefold().split())
            if len(term) >= 3:
                terms.append(term)
        return sorted(set(terms), key=len, reverse=True)

    @staticmethod
    def _term_matches(text: str, term: str) -> bool:
        escaped = re.escape(PersonalSignalsJob._normalize_for_match(term))
        return bool(
            re.search(
                rf"(?<![0-9a-zа-яё]){escaped}(?![0-9a-zа-яё])",
                text,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def _normalize_for_match(value: str) -> str:
        return (
            " ".join(str(value or "").casefold().split())
            .replace("‑", "-")
            .replace("–", "-")
            .replace("—", "-")
            .replace("ё", "е")
        )

    @staticmethod
    def _metadata_dict(metadata: Any) -> dict:
        if isinstance(metadata, dict):
            return metadata
        if isinstance(metadata, str):
            try:
                parsed = json.loads(metadata)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    @staticmethod
    def _canonical_url_key(article: dict[str, Any]) -> str:
        url = article.get("canonical_url") or article.get("original_link") or ""
        url = url.split("#", 1)[0].split("?", 1)[0].strip().rstrip("/")
        return url.lower()

    @staticmethod
    def _signal_surface(article: dict[str, Any]) -> str:
        source_metadata = PersonalSignalsJob._metadata_dict(article.get("source_metadata"))
        return PersonalSignalsJob._normalize_for_match(
            " ".join(
                [
                    str(article.get("title") or ""),
                    str(article.get("summary") or ""),
                    str(article.get("source_name") or ""),
                    str(article.get("source") or ""),
                    json.dumps(source_metadata, ensure_ascii=False),
                ]
            )
        )

    @staticmethod
    def _public_article(article: dict[str, Any]) -> dict[str, Any]:
        return {
            "article_id": article.get("article_id"),
            "title": article.get("title"),
            "source": article.get("source_name") or article.get("source"),
            "url": article.get("canonical_url") or article.get("original_link"),
            "language": article.get("language"),
            "created_at": article.get("created_at").isoformat() if article.get("created_at") else None,
            "published_at": article.get("published_at").isoformat() if article.get("published_at") else None,
            "signal_score": article.get("signal_score"),
            "selection_reason": article.get("selection_reason"),
            "matched_terms": article.get("matched_terms") or [],
        }


class PersonalSignalsWorker:
    """Periodic scheduler for the personal signal inbox."""

    def __init__(self, db_manager) -> None:
        self._db = db_manager
        self._enabled = os.getenv("PERSONAL_SIGNALS_ENABLED", "false").lower() == "true"
        self._run_at = os.getenv("PERSONAL_SIGNALS_RUN_AT", "")
        self._poll_seconds = int(os.getenv("PERSONAL_SIGNALS_POLL_SECONDS", "300"))
        self._interval_hours = max(1, int(os.getenv("PERSONAL_SIGNALS_INTERVAL_HOURS", "8")))
        self._task: Optional[asyncio.Task] = None
        self._last_run_at: Optional[datetime] = None

    def start(self) -> None:
        if not self._enabled:
            logger.info("[PersonalSignalsWorker] Disabled via PERSONAL_SIGNALS_ENABLED=false.")
            return
        if self._task and not self._task.done():
            logger.warning("[PersonalSignalsWorker] Already running.")
            return
        self._task = asyncio.create_task(self._loop(), name="personal_signals_worker")
        logger.info("[PersonalSignalsWorker] Started. interval_hours=%s run_at=%s", self._interval_hours, self._run_at)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[PersonalSignalsWorker] Cancellation requested.")

    async def _loop(self) -> None:
        while True:
            try:
                await self._maybe_run()
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[PersonalSignalsWorker] Loop cancelled.")
                break
            except Exception as exc:
                logger.exception("[PersonalSignalsWorker] Unexpected error: %s", exc)
                await asyncio.sleep(self._poll_seconds)

    async def _maybe_run(self) -> None:
        now = datetime.now(timezone.utc)
        if self._last_run_at and now - self._last_run_at < timedelta(hours=self._interval_hours):
            return
        if self._run_at and now.time() < DailyDigestWorker._parse_run_time(self._run_at):
            return
        result = await PersonalSignalsJob(self._db).run(dry_run=False, now=now)
        self._last_run_at = now
        logger.info("[PersonalSignalsWorker] Run result: %s", result.get("status"))
