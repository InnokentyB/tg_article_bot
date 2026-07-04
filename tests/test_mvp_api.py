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
