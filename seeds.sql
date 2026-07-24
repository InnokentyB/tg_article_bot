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
  ),
  (
    'Habr All Articles',
    'https://habr.com/ru/rss/articles/all/',
    'rss',
    'ru',
    6,
    TRUE,
    '{"tier": 1, "topics": ["software_engineering", "ai", "product", "ru_context"], "trust_level": "community", "noise_risk": "high", "bias": "mixed", "editorial_role": "Broad Russian-language technology feed; useful for discovery, requires ranking and dedup"}'
  ),
  (
    'Modern Analyst Articles',
    'https://www.modernanalyst.com/Resources/Articles/tabid/115/Default.aspx',
    'modernanalyst_html',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["business_analysis", "requirements", "product", "process"], "trust_level": "expert_community", "noise_risk": "medium", "bias": "professional_community", "editorial_role": "business analysis, requirements, process, UX, and product practice articles"}'
  ),
  (
    'Modern Analyst News',
    'https://www.modernanalyst.com/Resources/News.aspx',
    'modernanalyst_html',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["business_analysis", "requirements", "vendor_news", "tools"], "trust_level": "industry_news", "noise_risk": "medium", "bias": "vendor_press", "editorial_role": "business analysis vendor, requirements management, tooling, and industry announcements"}'
  ),
  (
    'Simon Willison AI Agents',
    'https://simonwillison.net/tags/ai-agents.atom',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["ai", "agents", "llm", "engineering_practice"], "trust_level": "expert", "noise_risk": "low", "bias": "independent_practitioner", "editorial_role": "hands-on AI agent analysis, tooling notes, and critical implementation context"}'
  ),
  (
    'Simon Willison RAG',
    'https://simonwillison.net/tags/rag.atom',
    'rss',
    'en',
    12,
    TRUE,
    '{"tier": 1, "topics": ["rag", "llm", "knowledge_base", "engineering_practice"], "trust_level": "expert", "noise_risk": "low", "bias": "independent_practitioner", "editorial_role": "retrieval, embeddings, and LLM application implementation notes"}'
  ),
  (
    'Eugene Yan',
    'https://eugeneyan.com/rss/',
    'rss',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["ai", "llm", "mlops", "recommendations", "evaluation"], "trust_level": "expert", "noise_risk": "low", "bias": "independent_practitioner", "editorial_role": "production AI, recommender systems, evaluation, and applied ML tradeoffs"}'
  ),
  (
    'Chip Huyen',
    'https://huyenchip.com/feed.xml',
    'rss',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["ai_engineering", "llm", "mlops", "production_ai"], "trust_level": "expert", "noise_risk": "low", "bias": "independent_practitioner", "editorial_role": "AI engineering systems, deployment practice, and production tradeoffs"}'
  ),
  (
    'Atlassian Teamwork',
    'https://www.atlassian.com/blog/teamwork/feed',
    'rss',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["knowledge_management", "collaboration", "team_process", "productivity"], "trust_level": "vendor_editorial", "noise_risk": "medium", "bias": "vendor", "editorial_role": "knowledge sharing, collaboration practice, documentation culture, and team operating patterns"}'
  ),
  (
    'GitLab Blog',
    'https://about.gitlab.com/atom.xml',
    'rss',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["knowledge_management", "software_engineering", "devops", "remote_work"], "trust_level": "company_editorial", "noise_risk": "medium", "bias": "vendor", "editorial_role": "public handbook culture, async work, DevOps practice, and engineering process"}'
  ),
  (
    'Mind the Product',
    'https://www.mindtheproduct.com/feed/',
    'mindtheproduct_json',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["product_management", "discovery", "strategy", "ai_product"], "trust_level": "industry_editorial", "noise_risk": "medium", "bias": "professional_media", "editorial_role": "product strategy, discovery, positioning, AI product practice, and product leadership commentary"}'
  ),
  (
    'Requirements Engineering Magazine',
    'https://re-magazine.ireb.org/articles',
    'ireb_html',
    'en',
    24,
    TRUE,
    '{"tier": 1, "topics": ["requirements", "business_analysis", "product", "quality"], "trust_level": "expert_community", "noise_risk": "low", "bias": "professional_community", "editorial_role": "requirements engineering, elicitation, business analysis, validation, and AI-in-RE practice"}'
  )
ON CONFLICT (url) DO UPDATE SET
    name = EXCLUDED.name,
    source_type = EXCLUDED.source_type,
    language = EXCLUDED.language,
    fetch_interval_hours = EXCLUDED.fetch_interval_hours,
    is_active = EXCLUDED.is_active,
    metadata = EXCLUDED.metadata,
    updated_at = CURRENT_TIMESTAMP;
