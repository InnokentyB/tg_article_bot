"""
Embedding provider abstraction for article chunks.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Protocol


class EmbeddingProvider(Protocol):
    model: str

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return one embedding vector per input text."""


@dataclass
class FakeEmbeddingProvider:
    """Deterministic local embedding provider for tests and development."""

    model: str = "fake-hash-bow-v1"
    dimensions: int = 32

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> List[float]:
        values = [0.0 for _ in range(self.dimensions)]
        tokens = re.findall(r"[\w']+", (text or "").lower())

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign

        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


@dataclass
class OpenAIEmbeddingProvider:
    """OpenAI embeddings provider, enabled with EMBEDDING_PROVIDER=openai."""

    model: str = "text-embedding-3-small"
    dimensions: Optional[int] = None

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for EMBEDDING_PROVIDER=openai") from exc

        client = AsyncOpenAI()
        kwargs = {
            "model": self.model,
            "input": texts,
        }
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions

        response = await client.embeddings.create(**kwargs)
        return [item.embedding for item in response.data]


def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "fake").lower()
    if provider == "fake":
        dimensions = int(os.getenv("FAKE_EMBEDDING_DIMENSIONS", "32"))
        return FakeEmbeddingProvider(dimensions=dimensions)

    if provider == "openai":
        dimensions_raw = os.getenv("OPENAI_EMBEDDING_DIMENSIONS")
        return OpenAIEmbeddingProvider(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            dimensions=int(dimensions_raw) if dimensions_raw else None,
        )

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider}")
