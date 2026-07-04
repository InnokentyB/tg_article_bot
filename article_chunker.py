"""
Deterministic article chunking for retrieval and embeddings.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


class ArticleChunker:
    def __init__(self, max_words: int = 450, overlap_words: int = 60):
        if max_words <= 0:
            raise ValueError("max_words must be positive")
        if overlap_words < 0:
            raise ValueError("overlap_words must not be negative")
        if overlap_words >= max_words:
            raise ValueError("overlap_words must be smaller than max_words")

        self.max_words = max_words
        self.overlap_words = overlap_words

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split article text into stable word chunks."""
        words = re.findall(r"\S+", text or "")
        if not words:
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(words):
            end = min(start + self.max_words, len(words))
            chunk_words = words[start:end]
            chunks.append(
                {
                    "chunk_index": index,
                    "text": " ".join(chunk_words),
                    "token_count": len(chunk_words),
                    "metadata": {
                        "start_word": start,
                        "end_word": end,
                    },
                }
            )

            if end == len(words):
                break

            start = end - self.overlap_words
            index += 1

        return chunks
