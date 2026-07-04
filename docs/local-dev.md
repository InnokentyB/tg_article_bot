# Local Development

## Start API Stack

Run the MVP API, Postgres, and Redis:

```bash
API_KEY=local-dev-key \
JWT_SECRET_KEY=local-jwt \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin-password \
docker compose up -d --build postgres redis api
```

The API is available at:

```text
http://localhost:5001
```

Health check:

```bash
curl http://localhost:5001/api/health
```

Database debug:

```bash
curl http://localhost:5001/debug/database
```

## Run Tests

Fast pytest suite for the local MVP API:

```bash
API_KEY=local-dev-key API_BASE_URL=http://localhost:5001 python -m pytest -q
```

The legacy Railway tests remain available, but they are opt-in:

```bash
RUN_RAILWAY_TESTS=1 python -m pytest tests/test_current_api.py
RUN_LEGACY_API_TESTS=1 python -m pytest tests/test_api.py
```

## Run Smoke Test

```bash
API_KEY=local-dev-key python scripts/mvp_smoke.py
```

This verifies:

- article creation;
- chunk creation on embedding rebuild;
- fake embedding storage;
- topic search;
- critical review draft generation with the fake provider;
- RSS ingestion with feed summary fallback.

## Optional OpenAI Review Generator

The local stack uses a deterministic fake review generator by default. To generate real drafts through an OpenAI-compatible endpoint, start the API with:

```bash
API_KEY=local-dev-key \
JWT_SECRET_KEY=local-jwt \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin-password \
OPENAI_API_KEY=<your-key> \
REVIEW_GENERATOR_PROVIDER=openai \
OPENAI_REVIEW_MODEL=gpt-5.5-mini \
docker compose up -d --build api
```

For OpenAI-compatible gateways, set `OPENAI_BASE_URL`.

## Optional URL Ingestion Test

```bash
curl -X POST http://localhost:5001/ingest/url \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local-dev-key" \
  -d '{
    "url": "https://www.rfc-editor.org/rfc/rfc9110.html",
    "source_name": "RFC Editor",
    "language": "en"
  }'
```

## Stop Stack

```bash
docker compose down
```

To reset local data:

```bash
docker compose down -v
```
