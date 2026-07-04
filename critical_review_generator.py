"""
Critical review generation for editorial MVP drafts.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Protocol


class CriticalReviewGenerator(Protocol):
    provider_name: str

    async def generate(self, topic: str, selected_articles: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate review_markdown and telegram_draft from selected articles."""


@dataclass
class FakeCriticalReviewGenerator:
    """Deterministic local generator for smoke tests and editorial workflow wiring."""

    provider_name: str = "fake-critical-review-v1"

    async def generate(self, topic: str, selected_articles: List[Dict[str, Any]]) -> Dict[str, str]:
        title = f"Critical review: {topic}"
        article_cards = []
        source_links = []

        for index, article in enumerate(selected_articles, start=1):
            article_title = article.get("title") or f"Source {index}"
            url = article.get("canonical_url") or article.get("original_link") or article.get("source") or ""
            preview = article.get("best_chunk_preview") or article.get("summary") or ""
            preview = " ".join(preview.split())[:420]
            score = article.get("score")
            score_text = f"{score:.3f}" if isinstance(score, (int, float)) else "n/a"

            article_cards.append(
                "\n".join(
                    [
                        f"### {index}. {article_title}",
                        f"- Source: {url or article.get('source') or 'unknown'}",
                        f"- Relevance score: {score_text}",
                        f"- Core thesis: {preview or 'Needs editorial reading.'}",
                        "- Why it matters: Potentially useful for the channel if it changes how practitioners make decisions.",
                        "- Strong argument: The material appears relevant to the requested topic and has enough substance for review.",
                        "- Weak spot: This automated draft has not yet verified evidence quality, data freshness, or author incentives.",
                        "- Practical takeaway: Use as a candidate source, then validate claims before publishing.",
                    ]
                )
            )

            if url:
                source_links.append(f"{index}. {article_title}: {url}")

        review_markdown = "\n\n".join(
            [
                f"# {title}",
                "## Editorial angle",
                f"The selected materials are relevant to `{topic}`. This draft focuses on practical usefulness, assumptions, and weak points rather than simple summarization.",
                "## Source analysis",
                "\n\n".join(article_cards) if article_cards else "No sources selected.",
                "## Synthesis",
                "The topic looks publishable if the editor can identify one concrete tension: what practitioners believe, what the sources actually prove, and where the implementation risk hides.",
                "## Source links",
                "\n".join(source_links) if source_links else "No source links available.",
            ]
        )

        telegram_draft = "\n\n".join(
            [
                f"**{topic}**",
                "Не просто пересказ ссылок, а черновик критического отбора.",
                "Что видно по выбранным материалам:",
                "\n".join(
                    [
                        f"{index}. {article.get('title') or 'Untitled source'} — {article.get('selection_reason', 'selected as relevant')}"
                        for index, article in enumerate(selected_articles, start=1)
                    ]
                ),
                "Редакторская гипотеза: тема стоит публикации, если из источников можно достать практическое противоречие, а не только общий тренд.",
                "Дальше руками: проверить аргументы, свежесть данных и применимость для аудитории Читатель Use Case.",
            ]
        )

        return {
            "title": title,
            "review_markdown": review_markdown,
            "telegram_draft": telegram_draft,
        }


@dataclass
class OpenAICriticalReviewGenerator:
    """OpenAI-compatible critical review generator."""

    model: str = "gpt-5.5-mini"
    provider_name: str = "openai-critical-review-v1"

    async def generate(self, topic: str, selected_articles: List[Dict[str, Any]]) -> Dict[str, str]:
        if not selected_articles:
            raise ValueError("selected_articles must not be empty")

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for REVIEW_GENERATOR_PROVIDER=openai") from exc

        client_kwargs = {}
        if os.getenv("OPENAI_BASE_URL"):
            client_kwargs["base_url"] = os.getenv("OPENAI_BASE_URL")

        client = AsyncOpenAI(**client_kwargs)
        response = await client.chat.completions.create(
            model=self.model,
            temperature=float(os.getenv("OPENAI_REVIEW_TEMPERATURE", "0.3")),
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": self._system_prompt(),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "topic": topic,
                            "selected_articles": self._compact_articles(selected_articles),
                            "output_contract": {
                                "title": "string",
                                "review_markdown": "string",
                                "telegram_draft": "string",
                            },
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )

        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        for field in ("title", "review_markdown", "telegram_draft"):
            if not parsed.get(field):
                raise ValueError(f"OpenAI review response missing field: {field}")
        return {
            "title": parsed["title"],
            "review_markdown": parsed["review_markdown"],
            "telegram_draft": parsed["telegram_draft"],
        }

    def _system_prompt(self) -> str:
        return """
You are an editorial analyst for the Telegram channel "Chitatel Use Case".

Generate a critical review draft, not a neutral summary.

Editorial standards:
- Write primarily in Russian unless source titles require original language.
- Focus on practical value for product, technology, and business readers.
- Identify the core thesis of each source.
- Explain why the material matters now.
- Name strong arguments and weak spots.
- Surface hidden assumptions, missing evidence, incentives, or implementation risks.
- Avoid hype, generic AI enthusiasm, and empty conclusions.
- Keep the Telegram draft concise, sharp, and publishable after human editing.
- Preserve source links.

Return only valid JSON with:
- title
- review_markdown
- telegram_draft
        """.strip()

    def _compact_articles(self, selected_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compacted = []
        for article in selected_articles:
            compacted.append(
                {
                    "article_id": article.get("article_id"),
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "author": article.get("author"),
                    "url": article.get("canonical_url") or article.get("original_link") or article.get("source"),
                    "summary": article.get("summary"),
                    "relevance_score": article.get("score"),
                    "selection_reason": article.get("selection_reason"),
                    "best_chunk_preview": article.get("best_chunk_preview"),
                }
            )
        return compacted


def get_critical_review_generator() -> CriticalReviewGenerator:
    provider = os.getenv("REVIEW_GENERATOR_PROVIDER", "fake").lower()
    if provider == "fake":
        return FakeCriticalReviewGenerator()
    if provider == "openai":
        return OpenAICriticalReviewGenerator(
            model=os.getenv("OPENAI_REVIEW_MODEL", "gpt-5.5-mini"),
        )
    raise ValueError(f"Unsupported REVIEW_GENERATOR_PROVIDER: {provider}")
