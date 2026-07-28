from __future__ import annotations

from datetime import datetime, timezone

from daily_digest_job import (
    DailyDigestConfig,
    DailyDigestJob,
    WeeklyDigestConfig,
    WeeklyThematicDigestJob,
)


def _candidate(
    article_id: int,
    title: str,
    *,
    text: str,
    source_metadata: dict | None = None,
    embedding_count: int = 0,
    summary: str = "Useful summary",
) -> dict:
    return {
        "article_id": article_id,
        "title": title,
        "summary": summary,
        "text": text,
        "source": "https://example.com",
        "original_link": f"https://example.com/{article_id}",
        "canonical_url": f"https://example.com/{article_id}",
        "language": "en",
        "created_at": datetime(2026, 7, 24, tzinfo=timezone.utc),
        "published_at": None,
        "source_metadata": source_metadata or {},
        "embedding_count": embedding_count,
        "views_count": 0,
        "likes_count": 0,
        "comments_count": 0,
        "popularity_score": 0,
    }


def test_daily_digest_ranks_substantial_tier_one_embedded_articles() -> None:
    job = DailyDigestJob(
        db_manager=object(),
        config=DailyDigestConfig(max_articles=5),
    )
    weak = _candidate(
        1,
        "Weekly product briefing",
        text="short " * 400,
        source_metadata={"tier": 2, "noise_risk": "medium"},
        embedding_count=1,
    )
    strong = _candidate(
        2,
        "AI Assistants in Requirements Engineering",
        text="requirements and AI agents " * 300,
        source_metadata={"tier": 1, "noise_risk": "low"},
        embedding_count=8,
    )

    ranked = job._rank_candidates([weak, strong])

    assert ranked[0]["article_id"] == 2
    assert ranked[0]["digest_score"] > ranked[1]["digest_score"]
    assert "tier-1 source" in ranked[0]["selection_reason"]


def test_daily_digest_messages_split_top_five_and_best_review() -> None:
    job = DailyDigestJob(
        db_manager=object(),
        config=DailyDigestConfig(period_days=3, max_articles=5),
    )
    ranked = [
        _candidate(index, f"Article {index}", text="AI agents " * 300)
        for index in range(1, 7)
    ]
    for article in ranked:
        article["digest_score"] = 5.0
        article["selection_reason"] = "test"
        article["digest_note"] = "Русское пояснение для дайджеста."

    best_article = ranked[0]
    digest_articles = ranked[1:6]
    digest_message = job._build_digest_telegram_message(
        digest_date=datetime(2026, 7, 24, tzinfo=timezone.utc).date(),
        ranked_articles=digest_articles,
    )
    review_message = job._build_review_telegram_message(
        digest_date=datetime(2026, 7, 24, tzinfo=timezone.utc).date(),
        best_article=best_article,
        best_review="Критический разбор лучшей статьи.",
    )

    assert "5 лучших материалов" in digest_message
    assert "Article 1" not in digest_message
    assert "1. Article 2" in digest_message
    assert "5. Article 6" in digest_message
    assert "Дата отбора" not in digest_message
    assert "Источник:" not in digest_message
    assert "Разбор статьи дня выйдет отдельным постом" not in digest_message
    assert "Коротко: Русское пояснение для дайджеста." in digest_message
    assert "Критический разбор лучшей статьи." not in digest_message
    assert "статья дня" in review_message
    assert "Дата отбора" not in review_message
    assert "Article 1" in review_message
    assert "Критический разбор лучшей статьи." in review_message


def test_daily_digest_note_never_falls_back_to_english_summary() -> None:
    article = _candidate(
        2,
        "English source",
        text="This is a long English article about AI engineering." * 50,
        summary="This English summary must not leak into the Telegram digest.",
        source_metadata={"topics": ["ai_engineering", "product"]},
    )

    note = DailyDigestJob._digest_article_note(article)

    assert "This English summary" not in note
    assert "Материал стоит прочитать" in note
    assert DailyDigestJob._is_russian_enough(note)


def test_daily_digest_filters_historical_backfill_by_url_date() -> None:
    job = DailyDigestJob(
        db_manager=object(),
        config=DailyDigestConfig(period_days=3, max_articles=5),
    )
    historical = _candidate(
        1,
        "Old but ingested today",
        text="AI agents " * 500,
        source_metadata={"tier": 1, "noise_risk": "low"},
        embedding_count=8,
    )
    historical["canonical_url"] = "https://example.com/2024/07/25/old-article.html"
    current = _candidate(
        2,
        "Current product article",
        text="AI agents " * 300,
        source_metadata={"tier": 1, "noise_risk": "low"},
        embedding_count=4,
    )

    ranked = job._rank_candidates([historical, current])

    assert [article["article_id"] for article in ranked] == [2]


def test_daily_digest_filters_bad_titles() -> None:
    job = DailyDigestJob(db_manager=object(), config=DailyDigestConfig())
    bad = _candidate(1, "Medium", text="AI agents " * 300)
    good = _candidate(2, "Useful AI article", text="AI agents " * 300)

    ranked = job._rank_candidates([bad, good])

    assert [article["article_id"] for article in ranked] == [2]


def test_daily_digest_deduplicates_by_canonical_url() -> None:
    job = DailyDigestJob(db_manager=object(), config=DailyDigestConfig())
    first = _candidate(1, "First title", text="AI agents " * 300)
    second = _candidate(2, "Second title", text="AI agents " * 300)
    first["canonical_url"] = "https://example.com/same?utm=one"
    second["canonical_url"] = "https://example.com/same#section"

    ranked = job._rank_candidates([first, second])

    assert len(ranked) == 1
    assert ranked[0]["article_id"] == 1


def test_weekly_digest_message_contains_topic_and_articles() -> None:
    job = WeeklyThematicDigestJob(
        db_manager=object(),
        config=WeeklyDigestConfig(topic="RAG and knowledge bases", max_articles=3),
    )
    ranked = [
        _candidate(index, f"RAG article {index}", text="rag knowledge base " * 300)
        for index in range(1, 4)
    ]

    message = job._build_weekly_telegram_message(
        week_start=datetime(2026, 7, 20, tzinfo=timezone.utc).date(),
        ranked_articles=ranked,
        review="Недельный обзор темы.",
    )

    assert "недельный тематический дайджест" in message
    assert "RAG and knowledge bases" in message
    assert "1. RAG article 1" in message
    assert "3. RAG article 3" in message
    assert "Недельный обзор темы." in message


def test_weekly_digest_week_start_is_monday() -> None:
    friday = datetime(2026, 7, 24, tzinfo=timezone.utc)

    assert WeeklyThematicDigestJob._week_start(friday).isoformat() == "2026-07-20"


def test_weekly_digest_topic_terms_boost_relevant_articles() -> None:
    job = WeeklyThematicDigestJob(
        db_manager=object(),
        config=WeeklyDigestConfig(topic="RAG knowledge bases", max_articles=5),
    )
    relevant = _candidate(
        1,
        "Building RAG knowledge bases",
        text="retrieval " * 300,
        source_metadata={"tier": 1, "noise_risk": "low"},
        embedding_count=2,
    )
    generic = _candidate(
        2,
        "Generic engineering post",
        text="engineering " * 300,
        source_metadata={"tier": 1, "noise_risk": "low"},
        embedding_count=2,
    )

    ranked = job._rank_candidates([generic, relevant])

    assert ranked[0]["article_id"] == 1
    assert "matches digest topic" in ranked[0]["selection_reason"]
