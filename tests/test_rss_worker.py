from __future__ import annotations

import asyncio
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
            ]

    async def run() -> None:
        worker = RSSWorker(db_manager=FakeDB(), ingest_fn=_unused_ingest_fn)
        fetched = []

        async def fake_fetch_source(source: dict) -> None:
            fetched.append(source["id"])

        worker._fetch_source = fake_fetch_source
        await worker._poll_once()

        assert fetched == [2, 4]

    asyncio.run(run())


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
