#!/usr/bin/env python3
"""
Integration checks for the local MVP article intelligence API.
"""
from __future__ import annotations

import os
import time

import httpx
import pytest


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


def test_health(client: httpx.Client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_mvp_article_embedding_search_and_review(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    stamp = int(time.time())
    article_text = (
        "Enterprise AI agents are useful when retrieval, tool execution, "
        "human approval, and audit logs are designed as one controlled workflow. "
        f"Local pytest stamp: {stamp}."
    )

    create_response = client.post(
        "/articles",
        json={
            "title": f"Pytest MVP article {stamp}",
            "text": article_text,
            "source": "pytest-local",
            "language": f"l{stamp % 100000000}",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "created"
    article_id = created["article_id"]

    embed_response = client.post(
        "/embeddings/rebuild",
        json={"article_id": article_id},
        headers=auth_headers,
    )
    assert embed_response.status_code == 200
    embedded = embed_response.json()
    assert embedded["status"] == "rebuilt"
    assert embedded["chunks_count"] >= 1
    assert embedded["embeddings_count"] == embedded["chunks_count"]

    search_response = client.post(
        "/search/topic",
        json={
            "topic": "enterprise AI agents with approval workflows and audit logs",
            "max_sources": 3,
            "language": f"l{stamp % 100000000}",
        },
        headers=auth_headers,
    )
    assert search_response.status_code == 200
    search = search_response.json()
    assert search["mode"] in {"embedding_similarity", "keyword_fallback"}
    assert any(item["article_id"] == article_id for item in search["results"])

    review_response = client.post(
        "/reviews/critical",
        json={
            "topic": "enterprise AI agents with approval workflows and audit logs",
            "max_sources": 3,
            "language": f"l{stamp % 100000000}",
        },
        headers=auth_headers,
    )
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["review_id"]
    assert review["telegram_draft"]
    assert review["selected_articles"]


def test_rss_ingestion_stores_feed_entry(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/ingest/rss",
        json={
            "feed_url": "https://www.rfc-editor.org/rfcrss.xml",
            "source_name": "RFC Editor Recent RFCs",
            "language": "en",
            "limit": 1,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["results"]
    assert data["summary"]["created"] + data["summary"]["duplicates"] >= 1
    assert data["summary"]["failed"] == 0


def test_vector_search_uses_db(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    """Verify that the search path returns a numeric similarity score.

    A float score indicates that the pgvector (or Python-fallback) similarity
    path was used.  A ``None`` score would mean keyword_fallback — which only
    fires when there are zero stored embeddings.
    """
    import time

    stamp = int(time.time())
    article_text = (
        "Vector databases store high-dimensional embeddings for efficient "
        "approximate nearest-neighbour retrieval using cosine distance. "
        f"pgvector test stamp: {stamp}."
    )

    # 1. Create article
    create_resp = client.post(
        "/articles",
        json={
            "title": f"pgvector test article {stamp}",
            "text": article_text,
            "source": "pytest-vector",
            "language": f"v{stamp % 100000000}",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    article_id = create_resp.json()["article_id"]

    # 2. Build embeddings
    embed_resp = client.post(
        "/embeddings/rebuild",
        json={"article_id": article_id},
        headers=auth_headers,
    )
    assert embed_resp.status_code == 200
    assert embed_resp.json()["embeddings_count"] >= 1

    # 3. Search and verify numeric score (pgvector or Python fallback)
    search_resp = client.post(
        "/search/topic",
        json={
            "topic": "vector databases cosine distance embeddings",
            "max_sources": 5,
            "language": f"v{stamp % 100000000}",
        },
        headers=auth_headers,
    )
    assert search_resp.status_code == 200
    search = search_resp.json()

    assert search["mode"] in {"embedding_similarity", "keyword_fallback"}

    # When embeddings exist the score must be a number, not None.
    results_with_score = [r for r in search["results"] if r.get("score") is not None]
    assert results_with_score, "Expected at least one result with a numeric similarity score"

    # Our article must appear somewhere in the results.
    assert any(r["article_id"] == article_id for r in search["results"])


def test_sources_crud(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    stamp = int(time.time())
    feed_url = f"https://example.com/feed-{stamp}.xml"
    source_name = f"Test RSS Feed {stamp}"

    # 1. Create a source
    add_resp = client.post(
        "/sources",
        json={
            "feed_url": feed_url,
            "name": source_name,
            "language": "ru",
            "fetch_interval_hours": 3,
        },
        headers=auth_headers,
    )
    assert add_resp.status_code == 200
    added = add_resp.json()
    assert added["status"] == "created"
    source_id = added["source_id"]
    assert added["feed_url"] == feed_url
    assert added["fetch_interval_hours"] == 3

    # 2. Get list of active sources and check if it's there
    list_resp = client.get("/sources", headers=auth_headers)
    assert list_resp.status_code == 200
    sources_list = list_resp.json()["sources"]
    matched = [s for s in sources_list if s["id"] == source_id]
    assert matched
    assert matched[0]["name"] == source_name
    assert matched[0]["is_active"] is True
    assert matched[0]["fetch_interval_hours"] == 3

    # 3. Soft-delete the source
    delete_resp = client.delete(f"/sources/{source_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deactivated"

    # 4. Check that it's no longer in active list
    list_active_resp = client.get("/sources?active_only=true", headers=auth_headers)
    assert list_active_resp.status_code == 200
    active_sources = list_active_resp.json()["sources"]
    assert not any(s["id"] == source_id for s in active_sources)

    # 5. Check that it IS in the full list with is_active = False
    list_all_resp = client.get("/sources?active_only=false", headers=auth_headers)
    assert list_all_resp.status_code == 200
    all_sources = list_all_resp.json()["sources"]
    matched_all = [s for s in all_sources if s["id"] == source_id]
    assert matched_all
    assert matched_all[0]["is_active"] is False


def test_source_manual_fetch(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    stamp = int(time.time())
    # We use a real valid feed from RFC Editor that we know parser can digest
    feed_url = "https://www.rfc-editor.org/rfcrss.xml"
    source_name = f"Manual Fetch Test {stamp}"

    # 1. Create active source
    add_resp = client.post(
        "/sources",
        json={
            "feed_url": feed_url,
            "name": source_name,
            "language": "en",
        },
        headers=auth_headers,
    )
    assert add_resp.status_code == 200
    source_id = add_resp.json()["source_id"]

    # 2. Trigger manual fetch
    fetch_resp = client.post(f"/sources/{source_id}/fetch", headers=auth_headers)
    assert fetch_resp.status_code == 200
    fetch_data = fetch_resp.json()
    assert fetch_data["status"] == "fetched"
    assert fetch_data["source_id"] == source_id

    # 3. Check list and verify last_fetched_at is set
    list_resp = client.get("/sources?active_only=false", headers=auth_headers)
    assert list_resp.status_code == 200
    sources = list_resp.json()["sources"]
    matched = [s for s in sources if s["id"] == source_id]
    assert matched
    assert matched[0]["last_fetched_at"] is not None
