-- Initial RSS sources seed for Chitatel Use Case.
-- Idempotent: existing rows are updated by URL.
-- Keep this file in sync with data/sources.seed.json until a JSON seed loader exists.

INSERT INTO sources (
    name,
    url,
    source_type,
    language,
    fetch_interval_hours,
    is_active,
    metadata
) VALUES
  (
    'OpenAI News',
    'https://openai.com/news/rss.xml',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["ai", "llm", "agents", "product"], "trust_level": "primary", "noise_risk": "medium", "bias": "vendor", "editorial_role": "primary vendor announcements and product/research positioning"}'
  ),
  (
    'Google AI',
    'https://blog.google/innovation-and-ai/technology/ai/rss/',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["ai", "llm", "research", "product"], "trust_level": "primary", "noise_risk": "medium", "bias": "vendor", "editorial_role": "Google AI announcements and ecosystem signals"}'
  ),
  (
    'Google DeepMind Blog',
    'https://deepmind.google/blog/rss.xml',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["ai", "research", "agents", "science"], "trust_level": "primary", "noise_risk": "low", "bias": "vendor_research", "editorial_role": "frontier AI research and model capability context"}'
  ),
  (
    'AWS Machine Learning Blog',
    'https://aws.amazon.com/blogs/machine-learning/feed/',
    'rss',
    'en',
    8,
    TRUE,
    '{"tier": 1, "topics": ["ai", "mlops", "enterprise", "cloud"], "trust_level": "primary", "noise_risk": "medium", "bias": "vendor", "editorial_role": "enterprise AI implementation patterns and AWS service examples"}'
  ),
  (
    'GitHub Engineering',
    'https://github.blog/engineering/feed/',
    'rss',
    'en',
    8,
    TRUE,
    '{"tier": 1, "topics": ["software_engineering", "developer_tools", "ai_coding"], "trust_level": "primary", "noise_risk": "low", "bias": "vendor", "editorial_role": "developer tooling and production engineering"}'
  ),
  (
    'Netflix TechBlog',
    'https://netflixtechblog.com/feed',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["software_architecture", "platform_engineering", "data"], "trust_level": "primary", "noise_risk": "low", "bias": "company_engineering", "editorial_role": "production architecture and platform tradeoffs"}'
  ),
  (
    'Martin Fowler',
    'https://martinfowler.com/feed.atom',
    'rss',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["software_architecture", "engineering_practice", "enterprise"], "trust_level": "expert", "noise_risk": "low", "bias": "independent_consulting", "editorial_role": "architecture framing and conceptual critique"}'
  ),
  (
    'arXiv cs.AI',
    'https://rss.arxiv.org/rss/cs.AI',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["ai", "research"], "trust_level": "preprint", "noise_risk": "high", "bias": "academic_preprint", "editorial_role": "early research signal; requires stronger filtering"}'
  ),
  (
    'arXiv cs.LG',
    'https://rss.arxiv.org/rss/cs.LG',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["machine_learning", "research"], "trust_level": "preprint", "noise_risk": "high", "bias": "academic_preprint", "editorial_role": "machine learning research feed; requires ranking and dedup"}'
  ),
  (
    'Habr Artificial Intelligence',
    'https://habr.com/ru/rss/hubs/artificial_intelligence/articles/all/',
    'rss',
    'ru',
    6,
    TRUE,
    '{"tier": 1, "topics": ["ai", "ru_context"], "trust_level": "community", "noise_risk": "medium", "bias": "mixed", "editorial_role": "Russian-language AI context and practitioner posts"}'
  ),
  (
    'Habr Machine Learning',
    'https://habr.com/ru/rss/hubs/machine_learning/articles/all/',
    'rss',
    'ru',
    6,
    TRUE,
    '{"tier": 1, "topics": ["machine_learning", "ru_context"], "trust_level": "community", "noise_risk": "medium", "bias": "mixed", "editorial_role": "Russian-language ML practice and explanations"}'
  ),
  (
    'Habr Programming',
    'https://habr.com/ru/rss/hubs/programming/articles/all/',
    'rss',
    'ru',
    8,
    TRUE,
    '{"tier": 1, "topics": ["software_engineering", "programming", "ru_context"], "trust_level": "community", "noise_risk": "medium", "bias": "mixed", "editorial_role": "Russian-language software engineering context"}'
  )
ON CONFLICT (url) DO UPDATE SET
    name = EXCLUDED.name,
    source_type = EXCLUDED.source_type,
    language = EXCLUDED.language,
    fetch_interval_hours = EXCLUDED.fetch_interval_hours,
    is_active = EXCLUDED.is_active,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;
