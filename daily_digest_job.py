"""
Daily editorial digest job for Chitatel Use Case.
"""
from __future__ import annotations

import asyncio
import html
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class DailyDigestConfig:
    period_days: int = 3
    max_articles: int = 5
    topic: str = "AI agents, knowledge bases, requirements, product and engineering practice"
    language: Optional[str] = None
    publish_enabled: bool = False

    @classmethod
    def from_env(cls) -> "DailyDigestConfig":
        return cls(
            period_days=int(os.getenv("DAILY_DIGEST_PERIOD_DAYS", "3")),
            max_articles=int(os.getenv("DAILY_DIGEST_MAX_ARTICLES", "5")),
            topic=os.getenv(
                "DAILY_DIGEST_TOPIC",
                "AI agents, knowledge bases, requirements, product and engineering practice",
            ),
            language=os.getenv("DAILY_DIGEST_LANGUAGE") or None,
            publish_enabled=os.getenv("DAILY_DIGEST_PUBLISH_ENABLED", "false").lower() == "true",
        )


@dataclass
class WeeklyDigestConfig:
    period_days: int = 7
    max_articles: int = 7
    topic: str = "AI agents and knowledge base systems"
    language: Optional[str] = None
    publish_enabled: bool = False

    @classmethod
    def from_env(cls) -> "WeeklyDigestConfig":
        return cls(
            period_days=int(os.getenv("WEEKLY_DIGEST_PERIOD_DAYS", "7")),
            max_articles=int(os.getenv("WEEKLY_DIGEST_MAX_ARTICLES", "7")),
            topic=os.getenv("WEEKLY_DIGEST_TOPIC", "AI agents and knowledge base systems"),
            language=os.getenv("WEEKLY_DIGEST_LANGUAGE") or None,
            publish_enabled=os.getenv("WEEKLY_DIGEST_PUBLISH_ENABLED", "false").lower() == "true",
        )


class DailyDigestJob:
    """Select recent articles, generate a daily review, and optionally publish it."""

    def __init__(self, db_manager, config: Optional[DailyDigestConfig] = None) -> None:
        self._db = db_manager
        self._config = config or DailyDigestConfig.from_env()

    async def run(
        self,
        *,
        publish: Optional[bool] = None,
        dry_run: bool = True,
        now: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Run one digest cycle.

        Args:
            publish: Override publishing. If omitted, uses config.publish_enabled.
            dry_run: When True, do not store a review or send Telegram messages.
            now: Optional timestamp for tests.
        """
        if not self._db or not self._db.pool:
            raise RuntimeError("Database pool not initialized")

        now = now or datetime.now(timezone.utc)
        publish = self._config.publish_enabled if publish is None else publish
        digest_date = now.date()

        if not dry_run and await self._digest_exists(digest_date):
            return {
                "status": "skipped",
                "reason": "daily digest already exists",
                "digest_date": digest_date.isoformat(),
            }

        candidates = await self._load_recent_candidates(now)
        ranked_articles = self._rank_candidates(candidates)[: self._config.max_articles]
        if not ranked_articles:
            return {
                "status": "skipped",
                "reason": "no recent articles found",
                "digest_date": digest_date.isoformat(),
            }

        best_article = ranked_articles[0]
        generated = await self._generate_best_article_review(best_article)
        telegram_message = self._build_telegram_message(
            digest_date=digest_date,
            ranked_articles=ranked_articles,
            best_article=best_article,
            best_review=generated["telegram_draft"],
        )

        review_id = None
        if not dry_run:
            review_id = await self._store_review(
                digest_date=digest_date,
                ranked_articles=ranked_articles,
                best_article=best_article,
                generated=generated,
                telegram_message=telegram_message,
                publish=publish,
            )

        published = False
        if publish and not dry_run:
            published = await asyncio.get_running_loop().run_in_executor(
                None,
                self._publish_message,
                telegram_message,
            )

        return {
            "status": "completed",
            "digest_date": digest_date.isoformat(),
            "period_days": self._config.period_days,
            "review_id": review_id,
            "dry_run": dry_run,
            "publish_requested": publish,
            "published": published,
            "best_article": self._public_article(best_article),
            "digest_articles": [self._public_article(article) for article in ranked_articles],
            "telegram_message": telegram_message,
            "review_markdown": generated["review_markdown"],
        }

    async def _load_recent_candidates(self, now: datetime) -> list[dict[str, Any]]:
        started_at = now - timedelta(days=self._config.period_days)
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
              AND COALESCE(length(a.text), 0) >= 900
        """
        params: list[Any] = [started_at, now]
        if self._config.language:
            query += " AND a.language = $3"
            params.append(self._config.language)
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

        for article in candidates:
            title = (article.get("title") or "").strip()
            title_key = " ".join(title.lower().split())
            if not title or title_key in seen_titles or self._looks_like_bad_title(title):
                continue
            if self._looks_like_historical_backfill(article):
                continue
            seen_titles.add(title_key)

            score, reasons = self._score_article(article)
            article["digest_score"] = round(score, 4)
            article["score"] = article["digest_score"]
            article["selection_reason"] = "; ".join(reasons)
            article["best_chunk_preview"] = self._preview(article)
            ranked.append(article)

        return sorted(
            ranked,
            key=lambda item: (
                item["digest_score"],
                item.get("embedding_count") or 0,
                item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc),
            ),
            reverse=True,
        )

    def _score_article(self, article: dict[str, Any]) -> tuple[float, list[str]]:
        text_len = len(article.get("text") or "")
        source_metadata = article.get("source_metadata") or {}
        if isinstance(source_metadata, str):
            source_metadata = {}

        score = 0.0
        reasons: list[str] = []

        if text_len >= 4000:
            score += 2.0
            reasons.append("substantial full text")
        elif text_len >= 1800:
            score += 1.0
            reasons.append("enough text for review")

        if article.get("summary"):
            score += 0.6
            reasons.append("has summary")

        embedding_count = int(article.get("embedding_count") or 0)
        if embedding_count:
            score += min(2.0, 0.25 * embedding_count)
            reasons.append("embedded")

        tier = source_metadata.get("tier")
        if tier == 1:
            score += 1.5
            reasons.append("tier-1 source")
        elif tier == 2:
            score += 0.8
            reasons.append("tier-2 source")

        noise_risk = source_metadata.get("noise_risk")
        if noise_risk == "low":
            score += 0.7
            reasons.append("low-noise source")
        elif noise_risk == "high":
            score -= 0.7
            reasons.append("high-noise source")

        title_and_summary = f"{article.get('title') or ''} {article.get('summary') or ''}".lower()
        focus_terms = [
            "agent",
            "ai",
            "rag",
            "knowledge",
            "requirements",
            "product",
            "evaluation",
            "evals",
            "business analysis",
            "engineering",
        ]
        matched_terms = [term for term in focus_terms if term in title_and_summary]
        if matched_terms:
            score += min(1.5, 0.35 * len(matched_terms))
            reasons.append("matches editorial focus")

        topic_terms = self._topic_terms(self._config.topic)
        matched_topic_terms = [term for term in topic_terms if term in title_and_summary]
        if matched_topic_terms:
            score += min(1.2, 0.3 * len(matched_topic_terms))
            reasons.append("matches digest topic")

        popularity = float(article.get("popularity_score") or 0)
        engagement = sum(float(article.get(field) or 0) for field in ("views_count", "likes_count", "comments_count"))
        if popularity or engagement:
            score += min(1.0, popularity / 100.0 + engagement / 1000.0)
            reasons.append("has popularity signal")

        title = (article.get("title") or "").lower()
        if any(marker in title for marker in ("weekly product briefing", "conference", "speakers", "company card")):
            score -= 1.0
            reasons.append("possible event/newsletter noise")

        return score, reasons or ["recent article"]

    def _looks_like_historical_backfill(self, article: dict[str, Any]) -> bool:
        article_date = article.get("published_at") or article.get("created_at")
        url_date = self._extract_date_from_url(
            article.get("canonical_url") or article.get("original_link") or ""
        )
        if not article_date or not url_date:
            return False
        if isinstance(article_date, datetime):
            article_date = article_date.date()
        return url_date < article_date - timedelta(days=self._config.period_days)

    @staticmethod
    def _looks_like_bad_title(title: str) -> bool:
        normalized = " ".join(title.lower().split())
        return normalized in {"medium", "untitled", "home"}

    @staticmethod
    def _extract_date_from_url(url: str) -> Optional[date]:
        match = re.search(r"/(20\d{2})/([01]\d)/([0-3]\d)(?:/|$)", url or "")
        if not match:
            return None
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    @staticmethod
    def _topic_terms(topic: str) -> list[str]:
        terms = []
        for raw_term in re.split(r"[^a-zA-Z0-9а-яА-ЯёЁ]+", topic.lower()):
            term = raw_term.strip()
            if len(term) >= 3 and term not in {"and", "the", "for", "with", "или", "для"}:
                terms.append(term)
        return sorted(set(terms))

    async def _generate_best_article_review(self, best_article: dict[str, Any]) -> dict[str, str]:
        from critical_review_generator import get_critical_review_generator

        generator = get_critical_review_generator()
        generated = await generator.generate(
            f"Разбор лучшей статьи дня: {best_article.get('title')}",
            [best_article],
        )
        generated["generator"] = generator.provider_name
        return generated

    async def _store_review(
        self,
        *,
        digest_date: date,
        ranked_articles: list[dict[str, Any]],
        best_article: dict[str, Any],
        generated: dict[str, str],
        telegram_message: str,
        publish: bool,
    ) -> int:
        topic_query_id = await self._db.create_topic_query(
            topic=self._config.topic,
            language=self._config.language,
            period_days=self._config.period_days,
            max_sources=self._config.max_articles,
            metadata={
                "job": "daily_digest",
                "digest_date": digest_date.isoformat(),
                "best_article_id": best_article["article_id"],
            },
        )
        return await self._db.create_review(
            topic_query_id=topic_query_id,
            title=f"Читатель Use Case: дайджест за {self._config.period_days} дня — {digest_date.isoformat()}",
            review_markdown=generated["review_markdown"],
            telegram_draft=telegram_message,
            selected_sources=[
                {
                    "article_id": article["article_id"],
                    "rank": index,
                    "selection_reason": article.get("selection_reason"),
                    "relevance_score": article.get("digest_score"),
                    "critique_summary": article.get("best_chunk_preview"),
                }
                for index, article in enumerate(ranked_articles, start=1)
            ],
            status="published" if publish else "draft",
            metadata={
                "job": "daily_digest",
                "digest_date": digest_date.isoformat(),
                "period_days": self._config.period_days,
                "best_article_id": best_article["article_id"],
                "generator": generated.get("generator"),
                "publish_requested": publish,
            },
        )

    async def _digest_exists(self, digest_date: date) -> bool:
        async with self._db.pool.acquire() as conn:
            return bool(
                await conn.fetchval(
                    """
                    SELECT 1
                    FROM reviews
                    WHERE metadata->>'job' = 'daily_digest'
                      AND metadata->>'digest_date' = $1
                    LIMIT 1
                    """,
                    digest_date.isoformat(),
                )
            )

    def _build_telegram_message(
        self,
        *,
        digest_date: date,
        ranked_articles: list[dict[str, Any]],
        best_article: dict[str, Any],
        best_review: str,
    ) -> str:
        lines = [
            f"Читатель Use Case: дайджест за {self._config.period_days} дня",
            f"Дата отбора: {digest_date.isoformat()}",
            "",
            "5 лучших материалов:",
        ]
        for index, article in enumerate(ranked_articles, start=1):
            title = article.get("title") or "Без названия"
            url = article.get("canonical_url") or article.get("original_link") or article.get("source") or ""
            lines.append(f"{index}. {title}")
            if url:
                lines.append(url)

        lines.extend(
            [
                "",
                "Статья дня:",
                best_article.get("title") or "Без названия",
                best_article.get("canonical_url") or best_article.get("original_link") or "",
                "",
                "Разбор:",
                best_review,
            ]
        )
        return "\n".join(line for line in lines if line is not None).strip()

    def _publish_message(self, message: str) -> bool:
        from publisher import TelegramPublisher

        publisher = TelegramPublisher()
        ok = True
        for chunk in self._split_telegram_message(message):
            ok = publisher._send_message(html.escape(chunk), parse_mode="HTML") and ok
        return ok

    @staticmethod
    def _split_telegram_message(message: str, limit: int = 3900) -> list[str]:
        if len(message) <= limit:
            return [message]
        chunks = []
        current = []
        current_len = 0
        for paragraph in message.split("\n\n"):
            paragraph_len = len(paragraph) + 2
            if current and current_len + paragraph_len > limit:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            current.append(paragraph)
            current_len += paragraph_len
        if current:
            chunks.append("\n\n".join(current))
        return chunks

    @staticmethod
    def _preview(article: dict[str, Any]) -> str:
        text = article.get("summary") or article.get("text") or ""
        return " ".join(text.split())[:500]

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
            "digest_score": article.get("digest_score"),
            "selection_reason": article.get("selection_reason"),
        }


class DailyDigestWorker:
    """Small daily scheduler for the digest job."""

    def __init__(self, db_manager) -> None:
        self._db = db_manager
        self._enabled = os.getenv("DAILY_DIGEST_ENABLED", "false").lower() == "true"
        self._run_at = os.getenv("DAILY_DIGEST_RUN_AT", "09:00")
        self._poll_seconds = int(os.getenv("DAILY_DIGEST_POLL_SECONDS", "60"))
        self._task: Optional[asyncio.Task] = None
        self._last_run_date: Optional[date] = None

    def start(self) -> None:
        if not self._enabled:
            logger.info("[DailyDigestWorker] Disabled via DAILY_DIGEST_ENABLED=false.")
            return
        if self._task and not self._task.done():
            logger.warning("[DailyDigestWorker] Already running.")
            return
        self._task = asyncio.create_task(self._loop(), name="daily_digest_worker")
        logger.info("[DailyDigestWorker] Started. run_at=%s", self._run_at)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[DailyDigestWorker] Cancellation requested.")

    async def _loop(self) -> None:
        while True:
            try:
                await self._maybe_run()
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[DailyDigestWorker] Loop cancelled.")
                break
            except Exception as exc:
                logger.exception("[DailyDigestWorker] Unexpected error: %s", exc)
                await asyncio.sleep(self._poll_seconds)

    async def _maybe_run(self) -> None:
        now = datetime.now(timezone.utc)
        if self._last_run_date == now.date():
            return
        if now.time() < self._parse_run_time(self._run_at):
            return
        result = await DailyDigestJob(self._db).run(dry_run=False, now=now)
        self._last_run_date = now.date()
        logger.info("[DailyDigestWorker] Run result: %s", result.get("status"))

    @staticmethod
    def _parse_run_time(value: str) -> time:
        try:
            hours, minutes = value.split(":", 1)
            return time(int(hours), int(minutes))
        except Exception:
            logger.warning("[DailyDigestWorker] Invalid DAILY_DIGEST_RUN_AT=%r, using 09:00.", value)
            return time(9, 0)


class WeeklyThematicDigestJob(DailyDigestJob):
    """Generate a weekly thematic digest draft."""

    def __init__(self, db_manager, config: Optional[WeeklyDigestConfig] = None) -> None:
        weekly_config = config or WeeklyDigestConfig.from_env()
        super().__init__(
            db_manager,
            config=DailyDigestConfig(
                period_days=weekly_config.period_days,
                max_articles=weekly_config.max_articles,
                topic=weekly_config.topic,
                language=weekly_config.language,
                publish_enabled=weekly_config.publish_enabled,
            ),
        )
        self._weekly_config = weekly_config

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
        publish = self._weekly_config.publish_enabled if publish is None else publish
        week_start = self._week_start(now)
        topic_slug = self._slugify(self._weekly_config.topic)

        if not dry_run and await self._weekly_digest_exists(week_start, topic_slug):
            return {
                "status": "skipped",
                "reason": "weekly thematic digest already exists",
                "week_start": week_start.isoformat(),
                "topic": self._weekly_config.topic,
            }

        candidates = await self._load_recent_candidates(now)
        ranked_articles = self._rank_candidates(candidates)[: self._weekly_config.max_articles]
        if not ranked_articles:
            return {
                "status": "skipped",
                "reason": "no recent articles found",
                "week_start": week_start.isoformat(),
                "topic": self._weekly_config.topic,
            }

        generated = await self._generate_weekly_review(ranked_articles)
        telegram_message = self._build_weekly_telegram_message(
            week_start=week_start,
            ranked_articles=ranked_articles,
            review=generated["telegram_draft"],
        )

        review_id = None
        if not dry_run:
            review_id = await self._store_weekly_review(
                week_start=week_start,
                topic_slug=topic_slug,
                ranked_articles=ranked_articles,
                generated=generated,
                telegram_message=telegram_message,
                publish=publish,
            )

        published = False
        if publish and not dry_run:
            published = await asyncio.get_running_loop().run_in_executor(
                None,
                self._publish_message,
                telegram_message,
            )

        return {
            "status": "completed",
            "week_start": week_start.isoformat(),
            "period_days": self._weekly_config.period_days,
            "topic": self._weekly_config.topic,
            "review_id": review_id,
            "dry_run": dry_run,
            "publish_requested": publish,
            "published": published,
            "digest_articles": [self._public_article(article) for article in ranked_articles],
            "telegram_message": telegram_message,
            "review_markdown": generated["review_markdown"],
        }

    async def _generate_weekly_review(self, ranked_articles: list[dict[str, Any]]) -> dict[str, str]:
        from critical_review_generator import get_critical_review_generator

        generator = get_critical_review_generator()
        generated = await generator.generate(
            f"Еженедельный тематический дайджест: {self._weekly_config.topic}",
            ranked_articles,
        )
        generated["generator"] = generator.provider_name
        return generated

    async def _store_weekly_review(
        self,
        *,
        week_start: date,
        topic_slug: str,
        ranked_articles: list[dict[str, Any]],
        generated: dict[str, str],
        telegram_message: str,
        publish: bool,
    ) -> int:
        topic_query_id = await self._db.create_topic_query(
            topic=self._weekly_config.topic,
            language=self._weekly_config.language,
            period_days=self._weekly_config.period_days,
            max_sources=self._weekly_config.max_articles,
            metadata={
                "job": "weekly_thematic_digest",
                "week_start": week_start.isoformat(),
                "topic_slug": topic_slug,
            },
        )
        return await self._db.create_review(
            topic_query_id=topic_query_id,
            title=f"Читатель Use Case: недельный дайджест — {self._weekly_config.topic}",
            review_markdown=generated["review_markdown"],
            telegram_draft=telegram_message,
            selected_sources=[
                {
                    "article_id": article["article_id"],
                    "rank": index,
                    "selection_reason": article.get("selection_reason"),
                    "relevance_score": article.get("digest_score"),
                    "critique_summary": article.get("best_chunk_preview"),
                }
                for index, article in enumerate(ranked_articles, start=1)
            ],
            status="published" if publish else "draft",
            metadata={
                "job": "weekly_thematic_digest",
                "week_start": week_start.isoformat(),
                "topic": self._weekly_config.topic,
                "topic_slug": topic_slug,
                "period_days": self._weekly_config.period_days,
                "generator": generated.get("generator"),
                "publish_requested": publish,
            },
        )

    async def _weekly_digest_exists(self, week_start: date, topic_slug: str) -> bool:
        async with self._db.pool.acquire() as conn:
            return bool(
                await conn.fetchval(
                    """
                    SELECT 1
                    FROM reviews
                    WHERE metadata->>'job' = 'weekly_thematic_digest'
                      AND metadata->>'week_start' = $1
                      AND metadata->>'topic_slug' = $2
                    LIMIT 1
                    """,
                    week_start.isoformat(),
                    topic_slug,
                )
            )

    def _build_weekly_telegram_message(
        self,
        *,
        week_start: date,
        ranked_articles: list[dict[str, Any]],
        review: str,
    ) -> str:
        lines = [
            f"Читатель Use Case: недельный тематический дайджест",
            f"Тема: {self._weekly_config.topic}",
            f"Неделя от: {week_start.isoformat()}",
            "",
            "Материалы выпуска:",
        ]
        for index, article in enumerate(ranked_articles, start=1):
            title = article.get("title") or "Без названия"
            url = article.get("canonical_url") or article.get("original_link") or article.get("source") or ""
            lines.append(f"{index}. {title}")
            if url:
                lines.append(url)

        lines.extend(["", "Обзор:", review])
        return "\n".join(line for line in lines if line is not None).strip()

    @staticmethod
    def _week_start(value: datetime) -> date:
        return (value - timedelta(days=value.weekday())).date()

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ]+", "-", value.lower()).strip("-")
        return slug[:80] or "weekly"


class WeeklyDigestWorker:
    """Small weekly scheduler for thematic digest drafts."""

    def __init__(self, db_manager) -> None:
        self._db = db_manager
        self._enabled = os.getenv("WEEKLY_DIGEST_ENABLED", "false").lower() == "true"
        self._run_at = os.getenv("WEEKLY_DIGEST_RUN_AT", "10:00")
        self._weekday = int(os.getenv("WEEKLY_DIGEST_WEEKDAY", "0"))
        self._poll_seconds = int(os.getenv("WEEKLY_DIGEST_POLL_SECONDS", "300"))
        self._task: Optional[asyncio.Task] = None
        self._last_run_week: Optional[date] = None

    def start(self) -> None:
        if not self._enabled:
            logger.info("[WeeklyDigestWorker] Disabled via WEEKLY_DIGEST_ENABLED=false.")
            return
        if self._task and not self._task.done():
            logger.warning("[WeeklyDigestWorker] Already running.")
            return
        self._task = asyncio.create_task(self._loop(), name="weekly_digest_worker")
        logger.info("[WeeklyDigestWorker] Started. weekday=%d run_at=%s", self._weekday, self._run_at)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("[WeeklyDigestWorker] Cancellation requested.")

    async def _loop(self) -> None:
        while True:
            try:
                await self._maybe_run()
                await asyncio.sleep(self._poll_seconds)
            except asyncio.CancelledError:
                logger.info("[WeeklyDigestWorker] Loop cancelled.")
                break
            except Exception as exc:
                logger.exception("[WeeklyDigestWorker] Unexpected error: %s", exc)
                await asyncio.sleep(self._poll_seconds)

    async def _maybe_run(self) -> None:
        now = datetime.now(timezone.utc)
        week_start = WeeklyThematicDigestJob._week_start(now)
        if self._last_run_week == week_start:
            return
        if now.weekday() != self._weekday:
            return
        if now.time() < DailyDigestWorker._parse_run_time(self._run_at):
            return
        result = await WeeklyThematicDigestJob(self._db).run(dry_run=False, now=now)
        self._last_run_week = week_start
        logger.info("[WeeklyDigestWorker] Run result: %s", result.get("status"))
