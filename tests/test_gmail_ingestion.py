import asyncio
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import DatabaseManager
from gmail_worker import GmailWorker
from api_server import ingest_url_payload

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5001")
API_KEY = os.getenv("API_KEY", "local-dev-key")


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as api_client:
        try:
            response = api_client.get("/api/health")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            pytest.skip(f"Local API is not available at {BASE_URL}: {exc}")
        yield api_client


@pytest.fixture(scope="session")
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


@pytest.fixture(scope="session")
def db_url_setup() -> None:
    # Point host tests to localhost Postgres forward
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://article_bot:article_bot_password@localhost:5432/article_bot"


@pytest.fixture
async def db(db_url_setup) -> DatabaseManager:
    import api_server
    db_mgr = DatabaseManager()
    await db_mgr.initialize()
    # Inject db_mgr into api_server for imports and endpoints to work in the test process
    api_server.db_manager = db_mgr
    yield db_mgr
    await db_mgr.close()
    api_server.db_manager = None


def test_gmail_fetch_endpoint_requires_auth(client: httpx.Client) -> None:
    """Verify that /gmail/fetch requires a valid API key."""
    response = client.post("/gmail/fetch")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gmail_worker_link_extraction() -> None:
    """Verify that email parser extracts links from plain text and HTML bodies."""
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    # 1. HTML body test
    html_body = """
    <html>
        <body>
            <p>Check out this article: <a href="https://example.com/ai-agents">AI Agents</a></p>
            <p>Or read more on <a href="https://medium.com/blog-post">Medium</a></p>
        </body>
    </html>
    """
    links = worker._extract_links(html_body)
    assert "https://example.com/ai-agents" in links
    assert "https://medium.com/blog-post" in links

    # 2. Plain text body test
    text_body = "Hello! Read TLDR at https://tldr.tech/newsletter and search on https://google.com?q=agent"
    links_text = worker._extract_links(text_body)
    assert "https://tldr.tech/newsletter" in links_text
    assert "https://google.com?q=agent" in links_text


@pytest.mark.asyncio
async def test_gmail_worker_normalizes_tracking_and_skips_assets(monkeypatch) -> None:
    """Verify newsletter wrappers are unwrapped and obvious assets/service links are ignored."""
    monkeypatch.setenv("GMAIL_MAX_LINKS_PER_EMAIL", "3")
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    html_body = """
    <html><body>
      <a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fexample.com%2Fpost%3Futm_source=tldrnewsletter%26x=1/1/token">Article</a>
      <a href="https://images.tldr.tech/logo.png">Logo</a>
      <a href="https://example.com/signup?utm_source=email">Signup</a>
      <a href="https://substackcdn.com/image/fetch/foo.png">Icon</a>
      <a href="https://example.com/second?utm_campaign=newsletter">Second</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert "https://example.com/post?x=1" in links
    assert "https://example.com/second" in links
    assert all("images.tldr.tech" not in link for link in links)
    assert all("substackcdn.com" not in link for link in links)
    assert all("signup" not in link for link in links)


def test_gmail_worker_sender_allowlist(monkeypatch) -> None:
    monkeypatch.setenv("GMAIL_ALLOWED_SENDERS", "dan@tldrnewsletter.com,hello@example.com")

    worker = GmailWorker(db_manager=None, ingest_fn=None)

    assert worker._sender_allowed("TLDR <dan@tldrnewsletter.com>") is True
    assert worker._sender_allowed("Other <other@example.net>") is False


@pytest.mark.asyncio
async def test_gmail_worker_filtering_and_autolearn(db: DatabaseManager) -> None:
    """Verify link filtering based on database patterns and auto-learning blocklist additions."""
    stamp = int(time.time())
    worker = GmailWorker(db_manager=db, ingest_fn=ingest_url_payload)
    worker._email = "test@gmail.com"
    worker._app_password = "fake-app-password"

    # Pre-seed dynamic filter in database
    spam_domain = f"spam-domain-{stamp}.com"
    await db.add_email_filter(spam_domain)

    # Verify that get_email_filters contains it
    filters = await db.get_email_filters()
    assert spam_domain in filters

    # Check filter method blocks the domain
    test_links = [
        f"https://{spam_domain}/unsubscribe-me",
        "https://habr.com/ru/post/12345/",
        "https://twitter.com/some-handle",
    ]
    filtered = await worker._filter_links(test_links)

    # habr.com should remain, spam_domain and twitter.com (from default seeds) should be filtered out
    assert "https://habr.com/ru/post/12345/" in filtered
    assert f"https://{spam_domain}/unsubscribe-me" not in filtered
    assert "https://twitter.com/some-handle" not in filtered

    # 2. Test auto-learning
    # If a URL fails ingestion, it should automatically add the domain to the blocklist.
    failed_domain = f"broken-site-{stamp}.com"
    broken_url = f"https://{failed_domain}/non-existent-page"

    # Process url should fail because Broken Site doesn't exist
    success = await worker._process_url(broken_url, f"Broken Test {stamp}")
    assert success is False

    # The domain should be dynamically added to email_filters
    updated_filters = await db.get_email_filters()
    assert failed_domain in updated_filters

    # Re-run filtering to verify that the auto-learned domain is now blocked
    filtered_retest = await worker._filter_links([broken_url])
    assert broken_url not in filtered_retest


@pytest.mark.asyncio
async def test_gmail_worker_fetch_marking_processed(db: DatabaseManager) -> None:
    """Verify that email message ID tracking works and prevents double ingestion."""
    stamp = int(time.time())
    msg_id = f"test-message-id-{stamp}@gmail.com"
    subject = f"Test Subject {stamp}"
    sender = "news@substack.com"

    # Ingest a real article from email body
    article_url = f"https://example-article-{stamp}.com/post"

    # We patch text extraction to return dummy data
    from text_extractor import TextExtractor

    dummy_extracted = {
        "text": f"This is a dummy processed email article text to index in pgvector. Stamp: {stamp}.",
        "title": f"Email Article {stamp}",
        "source": "https://example-article.com"
    }

    with patch.object(TextExtractor, "extract_from_url", return_value=dummy_extracted):
        worker = GmailWorker(db_manager=db, ingest_fn=ingest_url_payload)
        worker._email = "test@gmail.com"
        worker._app_password = "fake-app-password"

        # Mock IMAP fetch to return 1 message containing the link
        worker._sync_fetch_emails = MagicMock(return_value=[
            (msg_id, subject, sender, f"Click here: {article_url}")
        ])
        worker._sync_mark_seen = MagicMock()

        # Run poll cycle
        await worker.poll_once()

        # Verify email marked as processed in DB
        is_processed = await db.is_email_processed(msg_id)
        assert is_processed is True

        # Verify Seen flag method was called
        worker._sync_mark_seen.assert_called_once_with(msg_id)

        # Re-run fetch, should skip processing
        worker._sync_fetch_emails = MagicMock(return_value=[
            (msg_id, subject, sender, f"Click here: {article_url}")
        ])
        worker._sync_mark_seen = MagicMock()

        # Reset ingest mock-like detection by checking DB message tracking
        await worker.poll_once()

        # sync_mark_seen should NOT be called again because the mail is skipped at the start of loop
        worker._sync_mark_seen.assert_not_called()
