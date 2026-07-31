from __future__ import annotations

import pytest

from media_transcription_worker import MediaTranscriptionProcessor


@pytest.mark.asyncio
async def test_media_processor_stores_completed_transcript_as_article(monkeypatch) -> None:
    class FakeClient:
        async def get_transcription(self, transaction_id: str) -> dict:
            assert transaction_id == "tx-1"
            return {
                "status": "completed",
                "text": "AI product transcript. " * 80,
                "language": "en",
                "duration": 1200,
            }

    class FakeDb:
        def __init__(self) -> None:
            self.updated_fields = None
            self.marked = None
            self.embedded = None

        async def get_due_media_items(self, limit: int) -> list[dict]:
            return [
                {
                    "id": 5,
                    "url": "https://youtube.com/watch?v=abc",
                    "title": "Useful Video",
                    "media_type": "video",
                    "platform": "youtube",
                    "language": "en",
                    "status": "processing",
                    "transaction_id": "tx-1",
                    "source_id": 9,
                    "published_at": None,
                }
            ]

        async def save_article(self, **kwargs):
            self.article_kwargs = kwargs
            return 123, "fingerprint"

        async def update_article_intelligence_fields(self, **kwargs) -> None:
            self.updated_fields = kwargs

        async def register_article_source_tracking(self, **kwargs):
            return 1

        async def update_article_categories(self, article_id: int, categories: list[str]) -> None:
            self.categories = categories

        async def replace_article_chunks(self, article_id: int, chunks: list[dict]) -> list[dict]:
            return [{"id": 1, "text": chunks[0]["text"]}]

        async def mark_media_transcribed(self, media_item_id: int, **kwargs) -> None:
            self.marked = {"media_item_id": media_item_id, **kwargs}

        async def mark_media_failed(self, media_item_id: int, error: str) -> None:
            self.failed = {"media_item_id": media_item_id, "error": error}

    async def categorize(text: str) -> list[str]:
        return ["Technology"]

    async def embed(article_id: int, chunks: list[dict]) -> dict:
        db.embedded = {"article_id": article_id, "chunks": chunks}
        return {"embeddings_count": len(chunks)}

    monkeypatch.setattr(
        "transcribeit_client.TranscribeItClient",
        lambda: FakeClient(),
    )
    db = FakeDb()

    result = await MediaTranscriptionProcessor(
        db,
        categorize_fn=categorize,
        embed_fn=embed,
    ).process_due_items(limit=1)

    assert result["completed"] == 1
    assert db.article_kwargs["original_link"] == "https://youtube.com/watch?v=abc"
    assert db.updated_fields["content_type"] == "video"
    assert db.updated_fields["metadata"]["ingestion_method"] == "media_transcription"
    assert db.marked["article_id"] == 123
    assert db.embedded["article_id"] == 123


@pytest.mark.asyncio
async def test_media_processor_only_submits_approved_items(monkeypatch) -> None:
    class FakeClient:
        def is_configured(self) -> bool:
            return True

        async def upload_url(self, url: str, language: str = "auto") -> str:
            return "tx-approved"

    class FakeDb:
        def __init__(self) -> None:
            self.submitted = []

        async def get_due_media_items(self, limit: int) -> list[dict]:
            return [
                {
                    "id": 7,
                    "url": "https://youtube.com/watch?v=approved",
                    "status": "approved",
                    "transaction_id": None,
                    "language": "en",
                }
            ]

        async def mark_media_submitted(self, media_item_id: int, **kwargs) -> None:
            self.submitted.append({"id": media_item_id, **kwargs})

        async def mark_media_failed(self, media_item_id: int, error: str) -> None:
            self.failed = {"id": media_item_id, "error": error}

    monkeypatch.setattr("transcribeit_client.TranscribeItClient", lambda: FakeClient())
    db = FakeDb()

    result = await MediaTranscriptionProcessor(db).process_due_items(limit=1)

    assert result["submitted"] == 1
    assert db.submitted[0]["transaction_id"] == "tx-approved"
