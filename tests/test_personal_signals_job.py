from __future__ import annotations

import sys
import types
from datetime import datetime, timezone

from personal_signals_job import PersonalSignalsConfig, PersonalSignalsJob
from telegram_post_worker import TelegramPostDispatcher


def _article(article_id: int, title: str, text: str = "AI agents and RAG " * 120) -> dict:
    return {
        "article_id": article_id,
        "title": title,
        "summary": "Short source summary",
        "text": text,
        "source": "https://example.com",
        "original_link": f"https://example.com/{article_id}",
        "canonical_url": f"https://example.com/{article_id}",
        "language": "en",
        "created_at": datetime(2026, 9, 8, tzinfo=timezone.utc),
        "published_at": None,
        "source_metadata": {"tier": 1},
        "embedding_count": 3,
        "views_count": 0,
        "likes_count": 0,
        "comments_count": 0,
        "popularity_score": 0,
    }


def test_personal_signals_rank_by_project_terms() -> None:
    job = PersonalSignalsJob(
        db_manager=object(),
        config=PersonalSignalsConfig(
            topics="transcription, video, product discovery",
            min_score=1.0,
        ),
    )
    relevant = _article(
        1,
        "Video transcription workflow for product discovery",
        text="video transcription product discovery " * 100,
    )
    generic = _article(2, "Generic engineering update", text="kubernetes release notes " * 100)

    ranked = job._rank_candidates([generic, relevant])

    assert [article["article_id"] for article in ranked] == [1]
    assert {"video", "transcription", "product discovery"}.issubset(
        set(ranked[0]["matched_terms"])
    )


def test_personal_signals_do_not_match_terms_inside_other_words() -> None:
    job = PersonalSignalsJob(
        db_manager=object(),
        config=PersonalSignalsConfig(topics="rag", min_score=0.1),
    )

    ranked = job._rank_candidates(
        [
            _article(
                1,
                "For and Against Method",
                text="Arguments against rigid methods " * 100,
            )
        ]
    )

    assert ranked == []


def test_personal_signals_match_russian_ai_agent_terms_with_typographic_hyphen() -> None:
    job = PersonalSignalsJob(
        db_manager=object(),
        config=PersonalSignalsConfig(topics="ии-агентов", min_score=1.0),
    )

    ranked = job._rank_candidates(
        [_article(1, "Архитектура современных ИИ‑агентов")]
    )

    assert [article["article_id"] for article in ranked] == [1]
    assert ranked[0]["matched_terms"] == ["ии-агентов"]


def test_personal_signals_message_contains_private_inbox_context() -> None:
    job = PersonalSignalsJob(
        db_manager=object(),
        config=PersonalSignalsConfig(period_hours=12, topics="rag", min_score=1.0),
    )
    article = _article(1, "RAG for project memory")
    article["signal_score"] = 3.2
    article["matched_terms"] = ["rag"]

    message = job._build_telegram_message(
        now=datetime(2026, 9, 8, tzinfo=timezone.utc),
        ranked_articles=[article],
    )

    assert "Личные сигналы для проектов" in message
    assert "Окно: последние 12 ч." in message
    assert "Почему: rag" in message
    assert "https://example.com/1" in message


async def test_personal_signals_run_stores_database_draft_without_publish() -> None:
    class FakeDb:
        pool = object()

        def __init__(self) -> None:
            self.created_reviews = []

        async def create_topic_query(self, **kwargs):
            self.topic_query = kwargs
            return 11

        async def create_review(self, **kwargs):
            self.created_reviews.append(kwargs)
            return 22

    class TestJob(PersonalSignalsJob):
        async def _load_candidates(self, now):
            return [_article(1, "RAG agent for Telegram summaries")]

    db = FakeDb()
    job = TestJob(
        db_manager=db,
        config=PersonalSignalsConfig(topics="rag, telegram", min_score=1.0),
    )

    result = await job.run(
        dry_run=False,
        publish=False,
        now=datetime(2026, 9, 8, 12, tzinfo=timezone.utc),
    )

    assert result["review_id"] == 22
    assert result["queued_telegram_post_id"] is None
    assert db.created_reviews[0]["status"] == "draft"
    assert db.created_reviews[0]["metadata"]["job"] == "personal_signals"
    assert db.created_reviews[0]["selected_sources"][0]["article_id"] == 1


async def test_telegram_dispatcher_sends_personal_signal_to_target_chat(monkeypatch) -> None:
    sent = []

    class FakePublisher:
        def __init__(self, chat_id=None):
            self.chat_id = chat_id

        def _send_message(self, message, parse_mode="HTML"):
            sent.append((self.chat_id, message, parse_mode))
            return True

    fake_module = types.SimpleNamespace(TelegramPublisher=FakePublisher)
    monkeypatch.setitem(sys.modules, "publisher", fake_module)

    class FakeDb:
        def __init__(self) -> None:
            self.marked_sent = []

        async def get_due_telegram_posts(self, *, limit: int = 20):
            return [
                {
                    "id": 1,
                    "review_id": 10,
                    "post_type": "personal_signals",
                    "message": "Личный сигнал",
                    "metadata": '{"target_chat_id": "private-chat"}',
                }
            ]

        async def mark_telegram_post_sent(self, post_id: int) -> None:
            self.marked_sent.append(post_id)

        async def mark_telegram_post_failed(self, post_id: int, error: str) -> None:
            raise AssertionError(error)

    db = FakeDb()

    sent_count = await TelegramPostDispatcher(db).process_due_posts(limit=1)

    assert sent_count == 1
    assert db.marked_sent == [1]
    assert sent == [("private-chat", "Личный сигнал", "HTML")]
