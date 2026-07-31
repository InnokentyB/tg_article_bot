"""Editorial selection for media links before transcription."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class MediaSelectionDecision:
    approved: bool
    score: float
    reason: str
    matched_terms: list[str]


class MediaSelectionPolicy:
    """Decide whether a video or podcast is worth transcription from metadata."""

    DEFAULT_POSITIVE_TERMS = {
        "ai": 1.0,
        "agent": 1.2,
        "agents": 1.2,
        "llm": 1.0,
        "rag": 1.2,
        "knowledge base": 1.2,
        "retrieval": 0.8,
        "prompt": 0.7,
        "product": 0.8,
        "requirements": 1.1,
        "business analysis": 1.1,
        "engineering": 0.7,
        "architecture": 0.7,
        "automation": 0.8,
        "workflow": 0.6,
        "искусственный интеллект": 1.0,
        "ии": 0.8,
        "агент": 1.0,
        "агенты": 1.0,
        "база знаний": 1.2,
        "продукт": 0.8,
        "требования": 1.1,
        "бизнес-анализ": 1.1,
        "автоматизация": 0.8,
    }
    DEFAULT_NEGATIVE_TERMS = {
        "music": -1.2,
        "trailer": -0.9,
        "gaming": -0.8,
        "sports": -1.0,
        "crypto price": -1.0,
        "celebrity": -1.0,
        "музыка": -1.2,
        "трейлер": -0.9,
        "спорт": -1.0,
    }

    def __init__(self) -> None:
        self.min_score = float(os.getenv("MEDIA_SELECTION_MIN_SCORE", "1.5"))
        self.positive_terms = self._terms_from_env(
            "MEDIA_SELECTION_POSITIVE_TERMS",
            self.DEFAULT_POSITIVE_TERMS,
        )
        self.negative_terms = self._terms_from_env(
            "MEDIA_SELECTION_NEGATIVE_TERMS",
            self.DEFAULT_NEGATIVE_TERMS,
        )

    def decide(self, item: dict[str, Any]) -> MediaSelectionDecision:
        title = item.get("title") or ""
        description = item.get("description") or ""
        media_type = item.get("media_type") or "video"
        text = self._normalize(f"{title}\n{description}")

        score = 0.0
        matched_terms: list[str] = []
        for term, weight in self.positive_terms.items():
            if self._contains_term(text, term):
                score += weight
                matched_terms.append(term)
        for term, weight in self.negative_terms.items():
            if self._contains_term(text, term):
                score += weight
                matched_terms.append(term)

        if media_type == "podcast":
            score += 0.2
        if len(description) >= 120:
            score += 0.2

        approved = score >= self.min_score
        if approved:
            reason = f"Подходит для транскрибации: score={score:.2f}, совпали темы: {', '.join(matched_terms[:6]) or 'общий контекст'}."
        else:
            reason = f"Не транскрибируем автоматически: score={score:.2f}, недостаточно совпадений с темами канала."
        return MediaSelectionDecision(
            approved=approved,
            score=round(score, 3),
            reason=reason,
            matched_terms=matched_terms,
        )

    @classmethod
    def _terms_from_env(cls, name: str, defaults: dict[str, float]) -> dict[str, float]:
        raw = os.getenv(name)
        if not raw:
            return defaults
        terms = dict(defaults)
        for term in raw.split(","):
            clean = term.strip().lower()
            if clean:
                terms[clean] = max(terms.get(clean, 0), 1.0)
        return terms

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        normalized_term = term.lower().strip()
        if " " in normalized_term or "-" in normalized_term:
            return normalized_term in text
        return bool(re.search(rf"(?<![\wа-яё]){re.escape(normalized_term)}(?![\wа-яё])", text))


class MediaSelectionProcessor:
    """Apply the media selection policy to discovered links."""

    def __init__(self, db_manager, policy: MediaSelectionPolicy | None = None) -> None:
        self._db = db_manager
        self._policy = policy or MediaSelectionPolicy()

    async def process_pending(self, *, limit: int = 20) -> dict:
        items = await self._db.get_media_items_for_decision(limit=limit)
        result = {"reviewed": len(items), "approved": 0, "rejected": 0}
        for item in items:
            decision = self._policy.decide(item)
            await self._db.mark_media_decision(
                item["id"],
                approved=decision.approved,
                score=decision.score,
                reason=decision.reason,
                metadata={
                    "media_selection": {
                        "matched_terms": decision.matched_terms,
                        "policy": "heuristic-v1",
                    }
                },
            )
            result["approved" if decision.approved else "rejected"] += 1
        return result
