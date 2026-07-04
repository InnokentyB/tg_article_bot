# MVP: Article Intelligence Pipeline

## Product Positioning

This project is an editorial intelligence pipeline for the Telegram channel "Chitatel Use Case".

The system monitors external expert content, extracts articles and posts, stores them with embeddings, retrieves relevant materials by topic, and helps prepare critical reviews, digests, guides, and translations.

The project is not primarily a Telegram bot. Telegram is a publishing and editorial interface. The core product is the content ingestion, indexing, retrieval, and analysis pipeline.

## MVP Goal

Build the first reliable vertical slice:

1. Add articles from URL and RSS sources.
2. Extract clean text and metadata.
3. Store articles in Postgres.
4. Build embeddings for article chunks.
5. Retrieve relevant articles by topic.
6. Generate a critical review draft for Telegram.
7. Keep human approval before publishing.

## Primary User

The editor of "Chitatel Use Case".

The editor wants to quickly find strong articles on a topic, understand why they matter, see weak arguments and assumptions, and turn the best materials into a thoughtful Telegram post.

## Main User Journey

1. The editor registers or provides sources.
2. The system ingests new articles and posts.
3. The editor asks for a topic, for example: "AI agents in enterprise software".
4. The system retrieves and ranks relevant materials.
5. The system groups duplicates and similar articles.
6. The system selects the strongest candidates.
7. The system generates:
   - selected sources;
   - why each source was selected;
   - the author's core thesis;
   - useful insights;
   - weak arguments and assumptions;
   - practical implications;
   - Telegram draft.
8. The editor reviews, edits, and publishes manually.

## In Scope

- Manual URL ingestion.
- RSS ingestion.
- Article extraction and normalization.
- Deduplication by canonical URL and content fingerprint.
- Postgres storage.
- pgvector-ready schema for embeddings.
- Chunk-level embeddings.
- Hybrid retrieval by topic text, vector similarity, recency, language, and source.
- Critical review draft generation.
- Telegram-ready Markdown output.
- API-first implementation.

## Out Of Scope For MVP

- Automatic Telegram publishing.
- Full web admin redesign.
- Multi-user account management beyond basic admin credentials.
- Scheduled digest automation.
- Translation workflow.
- Long-form guide generation.
- Telegram channel parsing.
- Reddit, Hacker News, arXiv, YouTube ingestion.
- Real-time popularity tracking.
- Complex ML classification service.

## Domain Model

### Source

A content origin such as RSS feed, blog, publication, Telegram channel, or API.

Fields:
- `id`
- `name`
- `url`
- `source_type`
- `language`
- `is_active`
- `created_at`
- `updated_at`

### Article

A normalized article or post.

Fields:
- `id`
- `source_id`
- `url`
- `canonical_url`
- `title`
- `author`
- `published_at`
- `extracted_at`
- `language`
- `text`
- `summary`
- `fingerprint`
- `popularity_score`
- `metadata`
- `created_at`
- `updated_at`

### Article Chunk

A searchable text segment used for embeddings and retrieval.

Fields:
- `id`
- `article_id`
- `chunk_index`
- `text`
- `token_count`
- `metadata`
- `created_at`

### Article Embedding

Embedding for a chunk.

Fields:
- `id`
- `article_id`
- `chunk_id`
- `model`
- `embedding`
- `created_at`

### Topic Query

A saved editorial query.

Fields:
- `id`
- `topic`
- `language`
- `period_days`
- `max_sources`
- `created_at`

### Review

A generated editorial artifact.

Fields:
- `id`
- `topic_query_id`
- `title`
- `review_markdown`
- `telegram_draft`
- `status`
- `created_at`
- `updated_at`

### Review Source

Join table between reviews and selected articles.

Fields:
- `id`
- `review_id`
- `article_id`
- `rank`
- `selection_reason`
- `relevance_score`
- `critique_summary`

## API Surface

### Ingestion

`POST /ingest/url`

Request:

```json
{
  "url": "https://example.com/article",
  "source_name": "Example",
  "language": "en"
}
```

Response:

```json
{
  "article_id": 123,
  "status": "created",
  "fingerprint": "..."
}
```

`POST /ingest/rss`

Request:

```json
{
  "feed_url": "https://example.com/feed.xml",
  "source_name": "Example Feed",
  "limit": 20
}
```

### Embeddings

`POST /embeddings/rebuild`

Request:

```json
{
  "article_id": 123
}
```

### Retrieval

`POST /search/topic`

Request:

```json
{
  "topic": "AI agents in enterprise software",
  "language": "en",
  "period_days": 30,
  "max_sources": 7
}
```

### Review Generation

`POST /reviews/critical`

Request:

```json
{
  "topic": "AI agents in enterprise software",
  "language": "ru",
  "period_days": 30,
  "max_sources": 5,
  "channel_style": "Chitatel Use Case"
}
```

Response:

```json
{
  "review_id": 42,
  "selected_articles": [],
  "review_markdown": "...",
  "telegram_draft": "..."
}
```

## Critical Review Format

For each selected source:

- Core thesis.
- Why it matters.
- Strong arguments.
- Weak arguments.
- Hidden assumptions.
- Practical implications.
- Relevance for "Chitatel Use Case".

Final Telegram draft:

- Hook.
- Context.
- Key observations.
- Critical analysis.
- Practical takeaway.
- Source links.

## Technical Direction

- Python.
- FastAPI.
- Postgres.
- pgvector for embeddings.
- OpenAI-compatible embedding provider behind an abstraction.
- OpenAI-compatible review generator behind an abstraction.
- Background workers can be simple synchronous jobs in MVP, then move to a queue later.

## Success Criteria

MVP is ready when:

- A URL can be ingested and stored.
- An RSS feed can be ingested and deduplicated.
- Article chunks and embeddings are created.
- A topic query returns relevant articles.
- A critical review draft is generated from selected sources.
- The result can be copied into Telegram after human editing.
- The local development environment can be started reproducibly.

