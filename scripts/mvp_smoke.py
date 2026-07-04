#!/usr/bin/env python3
"""
Run a local MVP smoke test against the API.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request


BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5001")
API_KEY = os.getenv("API_KEY", "local-dev-key")


def post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    stamp = int(time.time())
    article_text = f"""
    AI agents in enterprise software are moving from demo workflows to constrained production systems.
    The strongest use cases combine retrieval, tool execution, human approval, and audit logs.
    A useful enterprise agent should be judged by reliability, escalation paths, measurable business value,
    and the quality of its failure modes. Local smoke stamp: {stamp}.
    """

    created = post(
        "/articles",
        {
            "title": f"Local MVP smoke article {stamp}",
            "text": article_text,
            "source": "local-smoke-test",
        },
    )
    article_id = created["article_id"]
    print("CREATE", json.dumps(created, ensure_ascii=False))

    embedded = post("/embeddings/rebuild", {"article_id": article_id})
    print("EMBED", json.dumps(embedded, ensure_ascii=False))

    search = post(
        "/search/topic",
        {
            "topic": "enterprise AI agents with human approval and audit logs",
            "max_sources": 3,
        },
    )
    print("SEARCH", json.dumps(search, ensure_ascii=False))

    if not search.get("results"):
        raise SystemExit("Search returned no results")
    if not any(result["article_id"] == article_id for result in search["results"]):
        raise SystemExit("Freshly created article was not present in search results")

    review = post(
        "/reviews/critical",
        {
            "topic": "enterprise AI agents with human approval and audit logs",
            "max_sources": 3,
        },
    )
    print("REVIEW", json.dumps(review, ensure_ascii=False))

    if not review.get("review_id"):
        raise SystemExit("Review was not stored")
    if not review.get("telegram_draft"):
        raise SystemExit("Review did not include a Telegram draft")

    rss = post(
        "/ingest/rss",
        {
            "feed_url": "https://www.rfc-editor.org/rfcrss.xml",
            "source_name": "RFC Editor Recent RFCs",
            "language": "en",
            "limit": 1,
        },
    )
    print("RSS", json.dumps(rss, ensure_ascii=False))

    if rss.get("status") != "completed":
        raise SystemExit("RSS ingestion did not complete")
    if not rss.get("results"):
        raise SystemExit("RSS ingestion returned no entry results")
    rss_summary = rss.get("summary") or {}
    if rss_summary.get("created", 0) + rss_summary.get("duplicates", 0) < 1:
        raise SystemExit("RSS ingestion did not store any feed entries")


if __name__ == "__main__":
    main()
