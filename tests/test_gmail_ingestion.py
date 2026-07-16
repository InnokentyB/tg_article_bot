import asyncio
import base64
import json
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
    text_body = "Hello! Read this article at https://example.com/blog/agent-systems and search on https://google.com?q=agent"
    links_text = worker._extract_links(text_body)
    assert "https://example.com/blog/agent-systems" in links_text
    assert "https://google.com?q=agent" not in links_text


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


def test_gmail_worker_scores_article_candidates_above_newsletter_chrome() -> None:
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    html_body = """
    <html><body>
      <a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fa.tldrnewsletter.com%2Fweb-version%3Fep=1%26utm_source=tldr/1/token">View in browser</a>
      <a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fadvertise.tldr.tech%2F%3Futm_source=tldr/1/token">Advertise</a>
      <a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2F9to5mac.com%2F2026%2F07%2F13%2Fios-27-public-beta%2F%3Futm_source=tldrnewsletter/1/token">Read the full article</a>
      <a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fantirez.com%2Fnews%2F169%3Futm_source=tldrnewsletter/1/token">Control the ideas, not the code</a>
      <a href="https://tracking.tldrnewsletter.com/CL0/https:%2F%2Fget-inscribe.com%2Fblog%2Fapple-speech-api-benchmark.html%3Futm_source=tldrnewsletter/1/token">Apple Speech API Benchmark</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert "https://a.tldrnewsletter.com/web-version?ep=1" not in links
    assert "https://advertise.tldr.tech/" not in links
    assert links[:3] == [
        "https://9to5mac.com/2026/07/13/ios-27-public-beta/",
        "https://antirez.com/news/169",
        "https://get-inscribe.com/blog/apple-speech-api-benchmark.html",
    ]


def test_gmail_worker_rejects_common_promo_candidates() -> None:
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    html_body = """
    <html><body>
      <a href="https://blog.productmanagementsociety.com/r/08346510?m=abc">What Can Product Managers Expect in 2027? How to Stay Ahead</a>
      <a href="https://blog.productmanagementsociety.com/r/160a5aa7?m=abc">The AI workspace that works for you. | Notion</a>
      <a href="https://blog.productmanagementsociety.com/r/1629ac7b?m=abc">#1 Product Manager's Hub | Product Management Society</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert "https://blog.productmanagementsociety.com/r/08346510?m=abc" in links
    assert "https://blog.productmanagementsociety.com/r/160a5aa7?m=abc" not in links
    assert "https://blog.productmanagementsociety.com/r/1629ac7b?m=abc" not in links


def test_gmail_worker_unwraps_producthunt_and_rejects_directories() -> None:
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    category_target = "aHR0cHM6Ly93d3cucHJvZHVjdGh1bnQuY29tL2NhdGVnb3JpZXMvYWktdm9pY2UtYWdlbnRzP3V0bV9zb3VyY2U9Zm9v"
    product_target = "aHR0cHM6Ly93d3cucHJvZHVjdGh1bnQuY29tL3Byb2R1Y3RzL2Z1dG8tc3dpcGU_dXRtX3NvdXJjZT1mb28"
    html_body = f"""
    <html><body>
      <a href="https://s-links.producthunt.com/lnk/foo/bar/{category_target}">AI voice agents</a>
      <a href="https://s-links.producthunt.com/lnk/foo/bar/{product_target}">FUTO Swipe</a>
      <a href="https://www.indiehackers.com/post/side-project-hit-1-7m-users-rC123">Read the story</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert "https://www.producthunt.com/categories/ai-voice-agents" not in links
    assert "https://www.producthunt.com/products/futo-swipe" not in links
    assert "https://www.indiehackers.com/post/side-project-hit-1-7m-users-rC123" in links


def test_gmail_worker_unwraps_convertkit_articles_and_rejects_profiles() -> None:
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    article_target = "aHR0cHM6Ly93d3cuaW5kaWVoYWNrZXJzLmNvbS9wb3N0L3NpZGUtcHJvamVjdC1oaXQtMS03bS11c2Vycy1yQzEyMz91dG1fc291cmNlPWNvbnZlcnRraXQ"
    profile_target = "aHR0cHM6Ly94LmNvbS9jaGFubmluZ2FsbGVuP3V0bV9zb3VyY2U9Y29udmVydGtpdA"
    html_body = f"""
    <html><body>
      <a href="https://indiehackers.click.convertkit-mail4.com/click/abc/{article_target}">Read the full post</a>
      <a href="https://indiehackers.click.convertkit-mail4.com/click/abc/{profile_target}">Channing Allen</a>
      <a href="https://indiehackers.open.convertkit-mail4.com/o/abc.gif">Open pixel</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert "https://www.indiehackers.com/post/side-project-hit-1-7m-users-rC123" in links
    assert "https://x.com/channingallen" not in links
    assert all("convertkit-mail4.com" not in link for link in links)


def test_gmail_worker_rejects_mailchimp_getcourse_and_landing_noise() -> None:
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    html_body = """
    <html><body>
      <a href="https://tocico.us13.list-manage.com/profile?u=abc&id=def">Update profile</a>
      <a href="https://us.list-manage.com/track/click?u=abc&id=def">Webinar: Introduction to Theory of Constraints</a>
      <a href="https://fs-thb02.getcourse.ru/fileservice/file/thumbnail/h/abc.png/s/x50/a/123/sc/1">Image</a>
      <a href="https://universuspro.ru/g/neiro-start">5 простых способов заработка на нейросетях</a>
      <a href="https://www.theguardian.com/technology/2026/jul/01/elon-musk-ai-simulation">Critical article</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert all("list-manage.com" not in link for link in links)
    assert all("getcourse.ru" not in link for link in links)
    assert all("universuspro.ru" not in link for link in links)
    assert "https://www.theguardian.com/technology/2026/jul/01/elon-musk-ai-simulation" in links


def test_gmail_worker_unwraps_customerio_and_rejects_event_social_noise() -> None:
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    def customerio_link(target: str) -> str:
        payload = json.dumps({"href": target}, separators=(",", ":")).encode()
        token = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        return f"https://e.customeriomail.com/e/c/{token}/hash"

    html_body = f"""
    <html><body>
      <a href="{customerio_link('https://simonwillison.net/2026/Jul/8/introducing-gptlive/?utm_source=email')}">Read the article</a>
      <a href="{customerio_link('https://us02web.zoom.us/webinar/register/4417836187912/WN_demo')}">Webinar Registration</a>
      <a href="{customerio_link('https://www.linkedin.com/company/devpost')}">Devpost LinkedIn</a>
      <a href="{customerio_link('https://twitter.com/devpost')}">Devpost Twitter</a>
      <a href="{customerio_link('https://xprize.devpost.com?utm_source=devpost')}">Build with Gemini XPRIZE</a>
      <a href="https://clicks.eventbrite.com/f/a/opaque">Eventbrite event</a>
      <a href="https://apify.intercom-clicks.com/via/e?ob=opaque">Intercom tracking</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert "https://simonwillison.net/2026/Jul/8/introducing-gptlive/" in links
    assert all("customeriomail.com" not in link for link in links)
    assert all("zoom.us" not in link for link in links)
    assert all("linkedin.com" not in link for link in links)
    assert all("twitter.com" not in link for link in links)
    assert all("devpost.com" not in link for link in links)
    assert all("eventbrite.com" not in link for link in links)
    assert all("intercom-clicks.com" not in link for link in links)


def test_gmail_worker_rejects_new_tracking_assets_and_unwraps_geteml() -> None:
    worker = GmailWorker(db_manager=None, ingest_fn=None)

    geteml_target = base64.urlsafe_b64encode(
        "https://dtcenter.ru/tpost/kivach_clinic?utm_source=email".encode()
    ).decode().rstrip("=")
    html_body = f"""
    <html><body>
      <a href="https://media.licdn.com/dms/image/v2/D4D12AQEgVW/article-inline_image-shrink_400_744/B4/foo">LinkedIn image</a>
      <a href="https://static.licdn.com/aero-v1/sc/h/2fp5x7ci191mxbdy1eynscn59">LinkedIn static</a>
      <a href="https://genaiworks.typeform.com/to/uXIl0IFH">B2B form</a>
      <a href="https://xwwdjrm.clicks.mlsend.com/ty/cl/opaque">Telegram channel</a>
      <a href="https://email.akamai.com/NjQyLVNLTi00NDkAAAGi4QFy">Akamai tracking</a>
      <a href="https://u42068088.ct.sendgrid.net/ls/click?upn=u001.opaque">SendGrid tracking</a>
      <a href="https://geteml.com/ru/mail_read_tracker/5705301?hash=abc">Read pixel</a>
      <a href="https://img.hiteml.com/en/v5/user-files?resource=himg&name=abc">Inline image</a>
      <a href="https://geteml.com/ru/mail_link_tracker?hash=abc&url={geteml_target}&uid=1">Кейс Клиника Кивач</a>
    </body></html>
    """

    links = worker._extract_links(html_body)

    assert "https://dtcenter.ru/tpost/kivach_clinic" in links
    assert all("licdn.com" not in link for link in links)
    assert all("typeform.com" not in link for link in links)
    assert all("mlsend.com" not in link for link in links)
    assert all("akamai.com" not in link for link in links)
    assert all("sendgrid.net" not in link for link in links)
    assert all("geteml.com" not in link for link in links)
    assert all("hiteml.com" not in link for link in links)


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
