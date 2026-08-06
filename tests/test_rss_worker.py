from __future__ import annotations

import asyncio
import json
import types
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rss_worker import RSSWorker


async def _unused_ingest_fn(payload: dict) -> dict:
    return {"status": "created", "payload": payload}


def test_rss_worker_can_be_disabled_without_starting_task(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "false")

    worker = RSSWorker(db_manager=object(), ingest_fn=_unused_ingest_fn)
    worker.start()

    assert worker._task is None


def test_rss_worker_start_creates_background_task(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "true")
    monkeypatch.setenv("WORKER_POLL_SECONDS", "3600")

    async def run() -> None:
        worker = RSSWorker(db_manager=object(), ingest_fn=_unused_ingest_fn)
        worker.start()
        try:
            assert worker._task is not None
            assert not worker._task.done()
        finally:
            worker.stop()
            await asyncio.sleep(0)

    asyncio.run(run())


def test_rss_worker_poll_only_fetches_rss_sources(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "true")

    class FakeDB:
        async def get_sources(self, active_only: bool, due_for_fetch: bool) -> list[dict]:
            assert active_only is True
            assert due_for_fetch is True
            return [
                {"id": 1, "name": "Email source", "source_type": "email_link"},
                {"id": 2, "name": "RSS source", "source_type": "rss"},
                {"id": 3, "name": "Article source", "source_type": "rss_entry"},
                {"id": 4, "name": "Modern Analyst", "source_type": "modernanalyst_html"},
                {"id": 5, "name": "Mind the Product", "source_type": "mindtheproduct_json"},
                {"id": 6, "name": "IREB", "source_type": "ireb_html"},
                {"id": 7, "name": "Docs", "source_type": "docs_collection"},
                {"id": 8, "name": "Video feed", "source_type": "video_rss"},
                {"id": 9, "name": "Podcast feed", "source_type": "podcast_rss"},
                {"id": 10, "name": "IIBA", "source_type": "iiba_html"},
                {"id": 11, "name": "The BA Guide", "source_type": "thebaguide_html"},
            ]

    async def run() -> None:
        worker = RSSWorker(db_manager=FakeDB(), ingest_fn=_unused_ingest_fn)
        fetched = []

        async def fake_fetch_source(source: dict) -> None:
            fetched.append(source["id"])

        worker._fetch_source = fake_fetch_source
        await worker._poll_once()

        assert fetched == [2, 4, 5, 6, 7, 8, 9, 10, 11]

    asyncio.run(run())


def test_rss_worker_passes_source_id_to_ingestion(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "true")

    class FakeDB:
        async def update_source_last_fetched(self, source_id: int) -> None:
            assert source_id == 42

    captured_payloads = []

    async def fake_ingest_fn(payload: dict) -> dict:
        captured_payloads.append(payload)
        return {"status": "created"}

    async def run() -> None:
        worker = RSSWorker(db_manager=FakeDB(), ingest_fn=fake_ingest_fn)

        class ParsedFeed:
            bozo = False
            entries = [
                {
                    "link": "https://example.com/articles/one",
                    "title": "One",
                    "summary": "<p>Useful article</p>",
                }
            ]

        monkeypatch.setitem(
            __import__("sys").modules,
            "feedparser",
            types.SimpleNamespace(parse=lambda *_args, **_kwargs: ParsedFeed()),
        )

        await worker._fetch_source(
            {
                "id": 42,
                "name": "Example Feed",
                "url": "https://example.com/feed.xml",
                "source_type": "rss",
                "language": "en",
            }
        )

    asyncio.run(run())

    assert captured_payloads[0]["source_id"] == 42


def test_rss_worker_stores_podcast_feed_entries_as_media_links(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "true")

    class FakeDB:
        def __init__(self) -> None:
            self.media_items = []
            self.fetched = []

        async def upsert_media_item(self, **kwargs) -> int:
            self.media_items.append(kwargs)
            return len(self.media_items)

        async def update_source_last_fetched(self, source_id: int) -> None:
            self.fetched.append(source_id)

    db = FakeDB()

    class ParsedFeed:
        bozo = False
        feed = {"title": "Good Podcast"}
        entries = [
            {
                "title": "Episode One",
                "summary": "<p>About product work</p>",
                "link": "https://example.com/episode-one",
                "published": "Wed, 29 Jul 2026 10:00:00 GMT",
                "itunes_duration": "01:02:03",
                "enclosures": [
                    {"href": "https://cdn.example.com/episode-one.mp3", "type": "audio/mpeg"}
                ],
            }
        ]

    async def run() -> None:
        monkeypatch.setitem(
            __import__("sys").modules,
            "feedparser",
            types.SimpleNamespace(parse=lambda *_args, **_kwargs: ParsedFeed()),
        )
        worker = RSSWorker(db_manager=db, ingest_fn=_unused_ingest_fn)
        await worker._fetch_source(
            {
                "id": 77,
                "name": "Good Podcast",
                "url": "https://example.com/feed.xml",
                "source_type": "podcast_rss",
                "language": "en",
            }
        )

    asyncio.run(run())

    assert db.fetched == [77]
    assert db.media_items[0]["url"] == "https://cdn.example.com/episode-one.mp3"
    assert db.media_items[0]["media_type"] == "podcast"
    assert db.media_items[0]["title"] == "Episode One"
    assert db.media_items[0]["duration_seconds"] == 3723


def test_rss_worker_ingests_docs_collection_entries(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_ENABLED", "true")

    class FakeDB:
        def __init__(self) -> None:
            self.updated_source_id = None

        async def update_source_last_fetched(self, source_id: int) -> None:
            self.updated_source_id = source_id

    captured_payloads = []

    async def fake_ingest_fn(payload: dict) -> dict:
        captured_payloads.append(payload)
        return {"status": "created"}

    async def run() -> None:
        db = FakeDB()
        worker = RSSWorker(db_manager=db, ingest_fn=fake_ingest_fn)

        await worker._fetch_source(
            {
                "id": 77,
                "name": "OpenAI Cookbook",
                "url": "https://developers.openai.com/cookbook",
                "source_type": "docs_collection",
                "language": "en",
                "metadata": json.dumps(
                    {
                        "entry_urls": [
                            {
                                "title": "OpenAI Cookbook",
                                "url": "https://developers.openai.com/cookbook",
                                "summary": "Official recipes.",
                            }
                        ]
                    }
                ),
            }
        )

        assert db.updated_source_id == 77

    asyncio.run(run())

    assert captured_payloads == [
        {
            "url": "https://developers.openai.com/cookbook",
            "source_id": 77,
            "title": "OpenAI Cookbook",
            "source_name": "OpenAI Cookbook",
            "source_type": "web",
            "language": "en",
            "summary": "Official recipes.",
            "fallback_text": "OpenAI Cookbook\n\nOfficial recipes.",
            "ingestion_method": "docs_collection_worker",
        }
    ]


def test_rss_worker_parses_modernanalyst_article_listing() -> None:
    html = """
    <html><body>
      <div class="article-list">
        <h2>
          <a href="/Resources/Articles/tabid/115/ID/7209/Stop-Writing-User-Stories-for-AI-Agents-They-Need-Decision-Contracts.aspx">
            Stop Writing User Stories for AI Agents: They Need Decision Contracts
          </a>
        </h2>
        <p>AI agents require decision contracts with clear authority, context, and escalation rules.</p>
        <h2>
          <a href="https://www.modernanalyst.com/Resources/Articles/tabid/115/ID/7199/Design-to-Make-It-Hard-for-Users-to-Make-Mistakes.aspx">
            Design to Make It Hard for Users to Make Mistakes
          </a>
        </h2>
        <p>Good software design helps prevent mistakes and improves recovery.</p>
        <h2>
          <a href="/Resources/News/tabid/177/ID/7200/Modern-Requirements-Ships-Its-Biggest-Update-Modern-Requirements4DevOps-NextGen.aspx">
            Modern Requirements Ships Its Biggest Update: Modern Requirements4DevOps NextGen
          </a>
        </h2>
        <a href="/Resources/News.aspx">News</a>
        <a href="https://example.com/Resources/Articles/tabid/115/ID/1/External.aspx">External</a>
      </div>
    </body></html>
    """

    entries = RSSWorker._parse_modernanalyst_articles(
        html,
        "https://www.modernanalyst.com/Resources/Articles/tabid/115/Default.aspx",
    )

    assert [entry["title"] for entry in entries] == [
        "Stop Writing User Stories for AI Agents: They Need Decision Contracts",
        "Design to Make It Hard for Users to Make Mistakes",
        "Modern Requirements Ships Its Biggest Update: Modern Requirements4DevOps NextGen",
    ]
    assert entries[0]["link"] == (
        "https://www.modernanalyst.com/Resources/Articles/tabid/115/ID/7209/"
        "Stop-Writing-User-Stories-for-AI-Agents-They-Need-Decision-Contracts.aspx"
    )
    assert "decision contracts" in entries[0]["fallback_text"]


def test_rss_worker_parses_mindtheproduct_json_feed() -> None:
    payload = {
        "results": [
            {
                "data": {
                    "title": "Evals are the new PRD",
                    "url": "https://www.mindtheproduct.com/evals-are-the-new-prd",
                    "authors": [
                        {
                            "author": {
                                "value": {
                                    "data": {
                                        "displayName": "Lisa Murkin",
                                    }
                                }
                            }
                        }
                    ],
                }
            },
            {
                "data": {
                    "title": "External",
                    "url": "https://example.com/external",
                }
            },
        ]
    }

    entries = RSSWorker._parse_mindtheproduct_items(payload)

    assert entries == [
        {
            "title": "Evals are the new PRD",
            "link": "https://www.mindtheproduct.com/evals-are-the-new-prd",
            "summary": "Lisa Murkin",
            "fallback_text": "Evals are the new PRD\n\nLisa Murkin",
        }
    ]


def test_rss_worker_parses_ireb_article_listing() -> None:
    html = """
    <html><body>
      <article>
        <h2>Using AI to discover more innovative requirements from documents</h2>
        <p>Revisiting models of creativity for AI.</p>
        <a href="/articles/using-ai-to-discover-more-innovative-requirements-from-documents">
          Read article
        </a>
      </article>
      <article>
        <a href="https://re-magazine.ireb.org/articles/ethics-of-using-llms-in-requirements-engineering">
          Ethics of Using LLMs in Requirements Engineering
        </a>
      </article>
      <a href="https://re-magazine.ireb.org/articles/view:grid/tags:ai">AI</a>
      <a href="https://example.com/articles/external">External</a>
    </body></html>
    """

    entries = RSSWorker._parse_ireb_articles(
        html,
        "https://re-magazine.ireb.org/articles",
    )

    assert [entry["title"] for entry in entries] == [
        "Using AI to discover more innovative requirements from documents",
        "Ethics of Using LLMs in Requirements Engineering",
    ]
    assert entries[0]["link"] == (
        "https://re-magazine.ireb.org/articles/"
        "using-ai-to-discover-more-innovative-requirements-from-documents"
    )
    assert "creativity for AI" in entries[0]["fallback_text"]


def test_rss_worker_parses_iiba_article_listing() -> None:
    html = """
    <section>
      <article>
        <h3>Why Good Decisions Don't Hold: A Hidden Gap in Business Analysis</h3>
        <p>Good decisions often become inconsistent over time because reasoning is not preserved.</p>
        <a href="/business-analysis-blogs/why-good-decisions-dont-hold/">Read to Learn More</a>
      </article>
      <article>
        <h3>Why AI Fluent Business Analysts Matter More Than Ever</h3>
        <a href="https://www.iiba.org/business-analysis-blogs/why-ai-fluent-business-analysts-matter-more-than-ever/">
          Read the Blog
        </a>
      </article>
    </section>
    """

    entries = RSSWorker._parse_iiba_articles(
        html,
        "https://www.iiba.org/business-analysis-blogs/",
    )

    assert [entry["title"] for entry in entries] == [
        "Why Good Decisions Don't Hold: A Hidden Gap in Business Analysis",
        "Why AI Fluent Business Analysts Matter More Than Ever",
    ]
    assert entries[0]["link"] == (
        "https://www.iiba.org/business-analysis-blogs/why-good-decisions-dont-hold/"
    )
    assert "Good decisions" in entries[0]["summary"]


def test_rss_worker_parses_thebaguide_blog_listing() -> None:
    html = """
    <main>
      <a href="/blog/category/businessanalysis/">Business Analysis</a>
      <article>
        <h2>
          <a href="/blog/top-7-reasons-you-should-become-a-business-analyst/">
            Top 7 Reasons You Should Become a Business Analyst
          </a>
        </h2>
        <p>Business analysis is a growing career path with practical impact.</p>
      </article>
      <article>
        <h2>How Do You Start a Business Analysis Project?</h2>
        <p>Start with stakeholders, goals, scope, and useful discovery questions.</p>
        <a href="https://thebaguide.com/blog/how-do-you-start-a-business-analysis-project/">
          Read More
        </a>
      </article>
      <a href="https://example.com/blog/external/">External</a>
    </main>
    """

    entries = RSSWorker._parse_thebaguide_articles(
        html,
        "https://thebaguide.com/blog/",
    )

    assert [entry["title"] for entry in entries] == [
        "Top 7 Reasons You Should Become a Business Analyst",
        "How Do You Start a Business Analysis Project?",
    ]
    assert entries[0]["link"] == (
        "https://thebaguide.com/blog/top-7-reasons-you-should-become-a-business-analyst/"
    )
    assert "growing career path" in entries[0]["fallback_text"]
