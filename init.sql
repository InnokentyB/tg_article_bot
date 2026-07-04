-- Инициализация базы данных для Telegram Article Bot

-- Включаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- pgvector should be enabled in production once the Postgres image supports it.
-- MVP stores embeddings as DOUBLE PRECISION[] to keep local development working
-- with the current vanilla postgres image.

-- Источники контента: RSS, сайты, блоги, Telegram-каналы, API
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT UNIQUE,
    source_type VARCHAR(50) NOT NULL DEFAULT 'web',
    language VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создаем таблицу пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создаем таблицу статей
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    summary TEXT,
    fingerprint VARCHAR(64) UNIQUE,
    source VARCHAR(500),
    author VARCHAR(200),
    original_link TEXT,
    is_translated BOOLEAN DEFAULT FALSE,
    categories_user TEXT[],
    categories_auto TEXT[],
    categories_advanced JSONB,
    language VARCHAR(10),
    comments_count INTEGER DEFAULT 0,
    likes_count INTEGER DEFAULT 0,
    views_count INTEGER DEFAULT 0,
    telegram_user_id BIGINT REFERENCES users(telegram_user_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MVP article intelligence fields. Kept as ALTERs so existing databases upgrade
-- without dropping the legacy article-bot schema.
ALTER TABLE articles ADD COLUMN IF NOT EXISTS source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS canonical_url TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE articles ADD COLUMN IF NOT EXISTS popularity_score DOUBLE PRECISION DEFAULT 0;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE articles ALTER COLUMN title DROP NOT NULL;

-- Чанки статей для embedding/retrieval
CREATE TABLE IF NOT EXISTS article_chunks (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    token_count INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(article_id, chunk_index)
);

-- Embeddings чанков. DOUBLE PRECISION[] используется как MVP-compatible
-- формат до перехода на pgvector.
CREATE TABLE IF NOT EXISTS article_embeddings (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL REFERENCES article_chunks(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    embedding DOUBLE PRECISION[] NOT NULL,
    embedding_dimensions INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(chunk_id, model)
);

-- Редакторские запросы по темам
CREATE TABLE IF NOT EXISTS topic_queries (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    language VARCHAR(10),
    period_days INTEGER,
    max_sources INTEGER DEFAULT 5,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Сгенерированные обзоры
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    topic_query_id INTEGER REFERENCES topic_queries(id) ON DELETE SET NULL,
    title TEXT,
    review_markdown TEXT,
    telegram_draft TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Источники, выбранные для обзора
CREATE TABLE IF NOT EXISTS review_sources (
    id SERIAL PRIMARY KEY,
    review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    selection_reason TEXT,
    relevance_score DOUBLE PRECISION,
    critique_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(review_id, article_id)
);

-- Создаем индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_articles_telegram_user_id ON articles(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_canonical_url ON articles(canonical_url);
CREATE INDEX IF NOT EXISTS idx_articles_language ON articles(language);
CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles USING GIN(categories_user);
CREATE INDEX IF NOT EXISTS idx_articles_categories_auto ON articles USING GIN(categories_auto);
CREATE INDEX IF NOT EXISTS idx_sources_source_type ON sources(source_type);
CREATE INDEX IF NOT EXISTS idx_article_chunks_article_id ON article_chunks(article_id);
CREATE INDEX IF NOT EXISTS idx_article_embeddings_article_id ON article_embeddings(article_id);
CREATE INDEX IF NOT EXISTS idx_article_embeddings_chunk_model ON article_embeddings(chunk_id, model);
CREATE INDEX IF NOT EXISTS idx_topic_queries_created_at ON topic_queries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_review_sources_review_id ON review_sources(review_id);

-- Создаем полнотекстовый поиск
CREATE INDEX IF NOT EXISTS idx_articles_title_text_fts ON articles USING GIN(
    to_tsvector('russian', title || ' ' || text)
);

-- Создаем триггер для обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_articles_updated_at ON articles;
CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON articles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sources_updated_at ON sources;
CREATE TRIGGER update_sources_updated_at BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_reviews_updated_at ON reviews;
CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Создаем представление для статистики
CREATE OR REPLACE VIEW articles_stats AS
SELECT 
    COUNT(*) as total_articles,
    COUNT(DISTINCT telegram_user_id) as unique_users,
    COUNT(DISTINCT language) as languages_count,
    AVG(LENGTH(text)) as avg_text_length,
    MAX(created_at) as last_article_date
FROM articles;

-- Создаем функцию для поиска статей
CREATE OR REPLACE FUNCTION search_articles(search_query TEXT)
RETURNS TABLE(
    id INTEGER,
    title TEXT,
    summary TEXT,
    similarity REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.title,
        a.summary,
        GREATEST(
            similarity(a.title, search_query),
            similarity(a.text, search_query)
        ) as similarity
    FROM articles a
    WHERE 
        a.title ILIKE '%' || search_query || '%' OR
        a.text ILIKE '%' || search_query || '%'
    ORDER BY similarity DESC;
END;
$$ LANGUAGE plpgsql;
