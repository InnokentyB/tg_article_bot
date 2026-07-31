from __future__ import annotations

import pytest

from media_selection import MediaSelectionPolicy, MediaSelectionProcessor


def test_media_selection_policy_approves_relevant_ai_video() -> None:
    decision = MediaSelectionPolicy().decide(
        {
            "title": "Building production RAG agents for product teams",
            "description": "A practical walkthrough of retrieval, knowledge bases, and engineering workflows.",
            "media_type": "video",
        }
    )

    assert decision.approved is True
    assert decision.score >= 1.5
    assert "rag" in decision.matched_terms


def test_media_selection_policy_rejects_irrelevant_video() -> None:
    decision = MediaSelectionPolicy().decide(
        {
            "title": "Official music trailer",
            "description": "A short entertainment clip.",
            "media_type": "video",
        }
    )

    assert decision.approved is False


@pytest.mark.asyncio
async def test_media_selection_processor_marks_discovered_items() -> None:
    class FakeDb:
        def __init__(self) -> None:
            self.decisions = []

        async def get_media_items_for_decision(self, limit: int) -> list[dict]:
            return [
                {
                    "id": 1,
                    "title": "AI agents for requirements engineering",
                    "description": "How product teams use knowledge bases.",
                    "media_type": "podcast",
                }
            ]

        async def mark_media_decision(self, media_item_id: int, **kwargs) -> None:
            self.decisions.append({"id": media_item_id, **kwargs})

    db = FakeDb()
    result = await MediaSelectionProcessor(db).process_pending(limit=10)

    assert result == {"reviewed": 1, "approved": 1, "rejected": 0}
    assert db.decisions[0]["approved"] is True
