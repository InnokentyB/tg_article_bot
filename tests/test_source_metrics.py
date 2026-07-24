from __future__ import annotations

import pytest

from database import DatabaseManager
from external_source_tracker import ExternalSourceTracker


def test_detect_source_type_known_and_generic_domains() -> None:
    assert DatabaseManager.detect_source_type("https://habr.com/ru/articles/123/") == "habr"
    assert DatabaseManager.detect_source_type("https://medium.com/example/post") == "medium"
    assert DatabaseManager.detect_source_type("https://dev.to/user/post") == "dev"
    assert DatabaseManager.detect_source_type("https://about.gitlab.com/blog/post/") == "about_gitlab_com"


@pytest.mark.asyncio
async def test_tracker_registers_unsupported_source_without_parser() -> None:
    calls = []

    class FakeDB:
        pool = object()

        @staticmethod
        def detect_source_type(url: str) -> str:
            return DatabaseManager.detect_source_type(url) or "unknown"

        async def register_article_source_tracking(self, **kwargs):
            calls.append(("register", kwargs))
            return 1

        async def save_external_source_stats(self, **kwargs):
            calls.append(("save", kwargs))

    tracker = ExternalSourceTracker(FakeDB())

    await tracker.track_article_source(10, "https://about.gitlab.com/blog/post/")

    assert calls[0][0] == "register"
    assert calls[0][1]["source_type"] == "about_gitlab_com"
    assert calls[1][0] == "save"
    assert calls[1][1]["status"] == "unsupported"
    assert calls[1][1]["metadata"]["reason"] == "no parser for this source type"


def test_parse_count_value_supports_suffixes_and_negative_rating() -> None:
    tracker = ExternalSourceTracker(db_manager=object())

    assert tracker.parse_count_value("1.5K") == 1500
    assert tracker.parse_count_value("2M") == 2000000
    assert tracker.parse_count_value("-5") == 0
    assert tracker.parse_count_value("-5", allow_negative=True) == -5
