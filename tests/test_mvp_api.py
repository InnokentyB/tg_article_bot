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

