-- Инициализация базы данных для Telegram Article Bot

-- Включаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

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

-- Создаем индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_articles_telegram_user_id ON articles(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_language ON articles(language);
CREATE INDEX IF NOT EXISTS idx_articles_categories ON articles USING GIN(categories_user);
CREATE INDEX IF NOT EXISTS idx_articles_categories_auto ON articles USING GIN(categories_auto);

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

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON articles
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
