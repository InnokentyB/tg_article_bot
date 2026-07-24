from __future__ import annotations

from datetime import datetime, timezone

from daily_digest_job import DailyDigestConfig, DailyDigestJob


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


def test_daily_digest_message_contains_top_five_and_best_review() -> None:
    job = DailyDigestJob(
        db_manager=object(),
        config=DailyDigestConfig(period_days=3, max_articles=5),
    )
    ranked = [
        _candidate(index, f"Article {index}", text="AI agents " * 300)
        for index in range(1, 6)
    ]
    for article in ranked:
        article["digest_score"] = 5.0
        article["selection_reason"] = "test"

    message = job._build_telegram_message(
        digest_date=datetime(2026, 7, 24, tzinfo=timezone.utc).date(),
        ranked_articles=ranked,
        best_article=ranked[0],
        best_review="Критический разбор лучшей статьи.",
    )

    assert "5 лучших материалов" in message
    assert "1. Article 1" in message
    assert "5. Article 5" in message
    assert "Статья дня" in message
    assert "Критический разбор лучшей статьи." in message


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
