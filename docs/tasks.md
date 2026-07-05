# MVP Task Breakdown

## Phase 0: Security And Repo Baseline

- [x] Remove hardcoded Telegram tokens.
- [x] Remove committed local SSL private keys.
- [x] Remove default JWT/API secrets.
- [x] Remove public demo credentials from login UI.
- [ ] Rotate exposed Telegram bot tokens in BotFather.
- [x] Decide whether to purge leaked secrets from git history (Purged!).

## Phase 1: Product Skeleton

- [x] Write MVP specification.
- [x] Write implementation task breakdown.
- [x] Mark legacy modules and current entrypoints.
- [x] Decide canonical app entrypoint for the MVP API.
- [x] Add a concise README section for the new product positioning.

## Phase 2: Storage Model

- [x] Add pgvector-ready schema to `init.sql`.
- [x] Add tables for `sources`, `article_chunks`, `article_embeddings`, `topic_queries`, `reviews`, and `review_sources`.
- [x] Preserve existing `articles` compatibility while adding MVP fields.
- [x] Add database methods for sources, chunks, embeddings, and reviews.
- [x] Add local migration/reset instructions.

## Phase 3: Ingestion

- [x] Create `POST /ingest/url`.
- [x] Normalize URL ingestion around existing `TextExtractor`.
- [x] Create source upsert logic.
- [x] Store canonical URL, fingerprint, source metadata, and extracted text.
- [x] Return duplicate status when article already exists.
- [x] Create `POST /ingest/rss`.

## Phase 4: Chunking And Embeddings

- [x] Add deterministic article chunking.
- [x] Add embedding provider abstraction.
- [x] Add OpenAI embedding implementation.
- [x] Store chunk embeddings.
- [x] Add `POST /embeddings/rebuild`.
- [x] Add no-op or hash-based fake embedding provider for tests.

## Phase 5: Retrieval

- [x] Add vector search SQL.
- [x] Add keyword fallback search.
- [x] Add topic search endpoint `POST /search/topic`.
- [x] Add filters for language, period, source, and max sources.
- [x] Add duplicate/similarity grouping.
- [x] Add ranking explanation payload.

## Phase 6: Critical Review

- [x] Add review generator abstraction.
- [x] Add prompt for critical article cards.
- [x] Add prompt for final Telegram draft.
- [x] Add `POST /reviews/critical`.
- [x] Store generated reviews and selected sources.
- [x] Include source links in the output.

## Phase 7: Local Development And Tests

- [x] Fix Dockerfile/compose mismatch for API and bot.
- [x] Add Postgres image with pgvector support.
- [x] Add local `.env` instructions.
- [x] Replace Railway-dependent tests with local API tests.
- [x] Add ingestion tests.
- [x] Add retrieval tests with fake embeddings.
- [x] Add review generation smoke test with fake LLM provider.

## First Vertical Slice

The first implementation slice should be:

1. Schema additions for sources, chunks, embeddings, topic queries, and reviews.
2. URL ingestion endpoint.
3. Chunking without embeddings.
4. Fake embedding provider and stored vectors or placeholders.
5. Topic search skeleton.
6. Critical review endpoint returning a structured draft from retrieved article metadata.
