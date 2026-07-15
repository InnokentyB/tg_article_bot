# Source Strategy

## Goal

The source catalog should support the editorial job of "Chitatel Use Case": find strong external materials, compare claims, identify weak assumptions, and prepare critical Telegram reviews.

The MVP source set prioritizes stable RSS feeds and article pages that can be ingested without custom platform integrations.

## Selection Criteria

Use these criteria before adding a source to the active crawler:

- Editorial value: primary research, production engineering, architecture decisions, enterprise AI practice, or strong analytical context.
- Integration cost: RSS or Atom feed exists and returns a successful response.
- Signal density: source produces enough useful material without overwhelming the queue.
- Bias profile: vendor marketing is allowed only when metadata marks it clearly.
- Language coverage: keep both English primary sources and Russian context sources.
- Operational risk: avoid paywalls, social feeds, JS-only pages, and unstable third-party scrapers in the active MVP seed.

## Tiers

### Tier 1: Primary And High-Signal Sources

These are active in the MVP seed:

- OpenAI News
- Google AI
- Google DeepMind Blog
- AWS Machine Learning Blog
- GitHub Engineering Blog
- Netflix TechBlog
- Martin Fowler
- arXiv cs.AI
- arXiv cs.LG
- Habr Artificial Intelligence
- Habr Machine Learning
- Habr Programming

### Tier 2: Useful, But Needs Verification

These are not active by default until their feed URL and extraction quality are verified:

- Anthropic News: no stable RSS endpoint confirmed; use manual URL ingestion for now.
- Microsoft Research: feed endpoint returned access restrictions during verification.
- Thoughtworks Insights: candidate feed URL returned 404 during verification.
- InfoQ AI / Architecture: category RSS URL needs verification.
- Shopify Engineering: candidate Atom URL returned 404 during verification.
- Uber Engineering: candidate RSS URL returned 404 during verification.

### Tier 3: Discovery / Aggregators

Use these for discovery, not as equal editorial sources:

- Hacker News via HNRSS
- TechCrunch
- The Verge
- Ars Technica
- Dev.to
- Medium publications such as Towards Data Science

These sources can help discover popular links, but they should not dominate review generation because they mix strong material with news churn and shallow commentary.

## Current Policy

- Active seed contains only RSS/Atom feeds suitable for automated crawling.
- Discovery aggregators stay out of active seed until ranking and noise controls are stronger.
- Manual URL ingestion remains the path for high-value sources without stable RSS.
- Each source carries metadata: tier, topics, trust level, noise risk, bias, and editorial role.

## Operational Notes

- `seeds.sql` is applied on API startup after `init.sql`.
- `data/sources.seed.json` is the human-readable catalog.
- Keep `seeds.sql` and `data/sources.seed.json` in sync until a dedicated seed loader replaces SQL seeding.
